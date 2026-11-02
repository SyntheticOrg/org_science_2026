"""Model adapter: one isolated conversation per player against the OpenAI Responses API (stdlib only).

Adapted from second-test/harness/agent.py. Changes: xhigh effort (chosen after the pilots, APPROACH.md); section names may contain '/' and '-';
an invalid, truncated or refused reply is re-asked once with the problem shown, and a second one raises
GroupFailed (the runner stops the group); no personas, memory window or reasoning summaries.
"""

import http.client
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "gpt-6-luna"
EFFORT = "xhigh"
API_URL = "https://api.openai.com/v1/responses"
ZERO_USAGE = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}


# --- instructions --------------------------------------------------------------

def load_sections(path=HERE / "instructions.md"):
    """Text under each `## name` heading, verbatim."""
    parts = re.split(r"^## (\S+)\s*$", path.read_text(), flags=re.M)
    return {name: body.strip() for name, body in zip(parts[1::2], parts[2::2])}


SECTIONS = load_sections()


def fill(name, **values):
    text = SECTIONS[name]
    missing = set(re.findall(r"\{(\w+)\}", text)) - set(values)
    assert not missing, f"unfilled placeholders in {name}: {missing}"
    for k, v in values.items():
        text = text.replace("{" + k + "}", str(v))
    return text


# --- model backends --------------------------------------------------------------

def _api_key():
    if "OPENAI_API_KEY" not in os.environ:
        env = next((p / ".env" for p in HERE.parents if (p / ".env").exists()), None)
        if env:
            for line in env.read_text().splitlines():
                k, sep, v = line.strip().partition("=")
                if sep and not k.startswith("#"):
                    os.environ.setdefault(k.strip().removeprefix("export "), v.strip().strip("'\""))
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found in the environment or in .env at the repo root.")
    return key


class ModelError(RuntimeError):
    """The API could not be reached or kept failing."""


class InvalidReply(ModelError):
    """A reply came back but cannot be used: truncated, refused, no text, or not valid JSON."""


class GroupFailed(RuntimeError):
    pass


class OpenAIModel:
    def __init__(self, model=MODEL, effort=EFFORT):
        self.model, self.effort, self.key = model, effort, _api_key()

    def __call__(self, messages, schema_name, schema):
        """Returns (output text, usage)."""
        body = {
            "model": self.model,
            "input": messages,
            "reasoning": {"effort": self.effort},
            "text": {"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": True}},
            "store": False,
        }
        data = self._post(body)
        u = data.get("usage") or {}
        usage = {
            "input_tokens": u.get("input_tokens", 0),
            "cached_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens", 0),
            "output_tokens": u.get("output_tokens", 0),
            "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0),
        }
        if data.get("status") != "completed":
            raise InvalidReply(f"response status {data.get('status')}: {data.get('incomplete_details')}", usage)
        text = None
        for item in data.get("output", []):
            for c in item.get("content") or []:
                if c.get("type") == "refusal":
                    raise InvalidReply(f"refusal: {c.get('refusal')}", usage)
                if c.get("type") == "output_text":
                    text = c["text"]
        if text is None:
            raise InvalidReply("no output text", usage)
        return text, usage

    def _post(self, body, attempts=8):
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(req, timeout=180) as r:  # calls take ~3 s; a stalled request is retried
                    return json.load(r)
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                if e.code not in (408, 409, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524) or attempt == attempts - 1:
                    raise ModelError(f"HTTP {e.code}: {detail}") from e
                e.close()
                err = f"HTTP {e.code}"
            except (OSError, http.client.HTTPException) as e:  # URLError, timeouts, dropped connections
                if attempt == attempts - 1:
                    raise ModelError(f"network error: {e}") from e
                err = repr(e)[:120]
            print(f"retry {attempt + 1} after {err}", file=sys.stderr, flush=True)
            time.sleep(2 ** attempt + random.random())


class FakeModel:
    """Schema-conforming random answers, for checking the pipeline without API calls."""

    PHRASES = ("It is game 2.", "Let's both play 3.", "Which game is it?", "I agree.", "Game 4, play f4 and c4.")

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.model, self.effort = "fake", None

    def __call__(self, messages, schema_name, schema):
        return json.dumps(self._value(schema)), dict(ZERO_USAGE)

    def _value(self, s):
        if "anyOf" in s:
            return self._value(self.rng.choice(s["anyOf"]))
        if "enum" in s:
            return self.rng.choice(s["enum"])
        t = s["type"]
        if t == "object":
            return {k: self._value(v) for k, v in s["properties"].items()}
        if t == "string":
            return self.rng.choice(self.PHRASES)
        if t == "null":
            return None
        raise ValueError(s)


# --- schemas ---------------------------------------------------------------------

def obj(props, note=False):
    """A strict object schema; with note, a private note on the reason comes first."""
    props = ({"note": {"type": "string"}} if note else {}) | props
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def enum(values):
    return {"type": "string", "enum": list(values)}


def nullable(s):
    return {"anyOf": [s, {"type": "null"}]}


# --- agent -----------------------------------------------------------------------

class Agent:
    """One player: a private message history; sees only what the runner sends it."""

    def __init__(self, role, model):
        self.role, self.model = role, model
        self.messages = [{"role": "system", "content": fill("system", role=role)}]
        self.usage = {"calls": 0, **ZERO_USAGE}
        self.failures = []  # every unusable reply, kept for the record

    def tell(self, text):
        """Information without a decision (the last period's result); it reaches the model with the next prompt."""
        self.messages.append({"role": "user", "content": text})

    def ask(self, prompt, schema_name, schema):
        self.messages.append({"role": "user", "content": prompt})
        for attempt in range(2):
            self.usage["calls"] += 1
            try:
                text, usage = self.model(self.messages, schema_name, schema)
                answer = json.loads(text)
            except InvalidReply as e:
                text, usage, error = None, e.args[1] if len(e.args) > 1 else {}, e.args[0]
            except json.JSONDecodeError:
                error = "the reply was not valid JSON"
            else:
                error = None
            for k, v in usage.items():
                self.usage[k] += v
            if error is None:
                self.messages.append({"role": "assistant", "content": text})
                return answer
            self.failures.append({"schema": schema_name, "attempt": attempt + 1, "error": error, "text": (text or "")[:500]})
            if attempt:
                raise GroupFailed(f"player {self.role}: unusable reply twice for {schema_name}: {error}")
            self.messages.append({"role": "user", "content": fill("retry", error=error)})

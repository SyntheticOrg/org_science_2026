"""Model adapters and agents: one isolated conversation per participant (standard library only).

Kit file of the synthetic-organisations plugin: copy it into the study's harness/ and adapt it there. Merged from
the Brandts & Cooper replication's agent (an unusable reply is re-asked once with the problem shown, a second one raises
GroupFailed), second-test/harness/agent.py (memory window with pinned instructions, persona, reasoning summaries)
and first-test/harness/vllm_model.py (ChatModel for OpenAI-compatible endpoints such as vLLM or Modal).

Every backend returns (text, usage, meta). meta holds the model identifier the server reported, the latency and the
number of retries; Agent keeps one entry per call, so a record shows which model actually answered.
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
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

KIT_VERSION = "0.1.0"
ZERO_USAGE = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
RETRY = "Your last reply could not be used ({error}). Please answer again in the required format."
RETRYABLE = (408, 409, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- instructions ----------------------------------------------------------------

def load_sections(path):
    """Text under each `## name` heading of an instructions file, verbatim."""
    parts = re.split(r"^## (\S+)\s*$", Path(path).read_text(), flags=re.M)
    return {name: body.strip() for name, body in zip(parts[1::2], parts[2::2])}


def fill(template, **values):
    """Fill {placeholders}. Every placeholder of the template must be given; the check runs on the template, so the
    values may contain braces (agents' messages often do)."""
    missing = set(re.findall(r"\{(\w+)\}", template)) - set(values)
    assert not missing, f"unfilled placeholders: {sorted(missing)}"
    for k, v in values.items():
        template = template.replace("{" + k + "}", str(v))
    return template


# --- errors and transport --------------------------------------------------------

class ModelError(RuntimeError):
    """The API could not be reached or kept failing."""


class InvalidReply(ModelError):
    """A reply came back but cannot be used: truncated, refused, empty or not valid JSON. args: (message, usage, meta)."""


class GroupFailed(RuntimeError):
    """A participant gave an unusable reply twice; the study records the group as incomplete."""


def env_key(name="OPENAI_API_KEY", required=True):
    """The key from the environment, or from the nearest .env in the working directory or above it."""
    if name not in os.environ:
        here = Path.cwd().resolve()
        env = next((p / ".env" for p in (here, *here.parents) if (p / ".env").exists()), None)
        if env:
            for line in env.read_text().splitlines():
                k, sep, v = line.strip().partition("=")
                if sep and not k.startswith("#"):
                    os.environ.setdefault(k.strip().removeprefix("export "), v.strip().strip("'\""))
    if required and not os.environ.get(name):
        raise RuntimeError(f"{name} not found in the environment or in a .env file.")
    return os.environ.get(name)


def post_json(url, body, headers, attempts=8, timeout=300):
    """POST with exponential back-off on transient errors. Returns (data, retries)."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r), attempt
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code not in RETRYABLE or attempt == attempts - 1:
                raise ModelError(f"HTTP {e.code}: {detail}") from e
            err = f"HTTP {e.code}"
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as e:  # timeouts, dropped connections
            if attempt == attempts - 1:
                raise ModelError(f"network error: {e}") from e
            err = repr(e)[:120]
        print(f"retry {attempt + 1} after {err}", file=sys.stderr, flush=True)
        time.sleep(2 ** attempt + random.random())


# --- backends --------------------------------------------------------------------

class OpenAIModel:
    """OpenAI Responses API with strict JSON-schema replies. Earlier reasoning is not carried over (store: false)."""

    url = "https://api.openai.com/v1/responses"

    def __init__(self, model, effort=None, summary=None, key=None):
        assert summary in (None, "auto", "concise", "detailed"), summary
        self.model, self.effort, self.summary, self.key = model, effort, summary, key or env_key()

    def with_effort(self, effort):
        return OpenAIModel(self.model, effort, self.summary, self.key)

    def describe(self):
        return {"backend": "openai-responses", "model": self.model, "effort": self.effort, "summary": self.summary}

    def __call__(self, messages, schema_name, schema):
        reasoning = {k: v for k, v in (("effort", self.effort), ("summary", self.summary)) if v}
        body = {"model": self.model, "input": messages, "store": False,
                "text": {"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": True}},
                **({"reasoning": reasoning} if reasoning else {})}
        t0 = time.time()
        data, retries = post_json(self.url, body, {"Authorization": f"Bearer {self.key}"})
        u = data.get("usage") or {}
        usage = {"input_tokens": u.get("input_tokens", 0),
                 "cached_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens", 0),
                 "output_tokens": u.get("output_tokens", 0),
                 "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0)}
        meta = {"returned_model": data.get("model"), "seconds": round(time.time() - t0, 2), "retries": retries}
        if data.get("status") != "completed":
            raise InvalidReply(f"response status {data.get('status')}: {data.get('incomplete_details')}", usage, meta)
        text, summary = None, []
        for item in data.get("output", []):
            if item.get("type") == "reasoning":
                summary += [s["text"] for s in item.get("summary") or [] if s.get("type") == "summary_text"]
            for c in item.get("content") or []:
                if c.get("type") == "refusal":
                    raise InvalidReply(f"refusal: {c.get('refusal')}", usage, meta)
                if c.get("type") == "output_text":
                    text = c["text"]
        if text is None:
            raise InvalidReply("no output text", usage, meta)
        if self.summary:
            meta["summary"] = "\n\n".join(summary)
        return text, usage, meta


class ChatModel:
    """OpenAI-compatible chat completions (local vLLM, a Modal endpoint, other providers) with JSON-schema replies.
    settings go into every request (temperature, top_p, max_tokens, chat_template_kwargs ...). revision names the
    pinned checkpoint the server loads; it is recorded for replicability, not sent."""

    def __init__(self, model, url="http://127.0.0.1:8000/v1/chat/completions", settings=None, key=None, revision=None):
        if key and urlparse(url).scheme != "https":
            raise ValueError("Send a key only over HTTPS.")
        self.model, self.url, self.settings, self.key, self.revision = model, url, dict(settings or {}), key, revision
        self.effort = None

    def with_effort(self, effort):
        return self  # thinking on open models is a server or template setting, fixed in `settings`

    def describe(self):
        return {"backend": "chat-completions", "model": self.model, "url": self.url, "revision": self.revision,
                "settings": self.settings}

    def __call__(self, messages, schema_name, schema):
        body = {"model": self.model, "messages": messages, **self.settings,
                "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "schema": schema, "strict": True}}}
        t0 = time.time()
        data, retries = post_json(self.url, body, {"Authorization": f"Bearer {self.key}"} if self.key else {})
        meta = {"returned_model": data.get("model"), "seconds": round(time.time() - t0, 2), "retries": retries}
        try:
            choice, u = data["choices"][0], data.get("usage") or {}
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ModelError("malformed chat completion") from e
        usage = {"input_tokens": u.get("prompt_tokens", 0), "cached_tokens": 0, "output_tokens": u.get("completion_tokens", 0),
                 "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)}
        if choice.get("finish_reason") != "stop" or not isinstance(text, str) or not text.strip():
            raise InvalidReply(f"finish_reason {choice.get('finish_reason')}; no usable text", usage, meta)
        return text, usage, meta


class FakeModel:
    """Schema-valid replies without API calls, for pipeline checks. With `script`, a function
    (messages, schema_name) -> reply dict gives fixed replies instead, for checks whose results are known in advance."""

    model, effort = "fake", None

    def __init__(self, seed=0, script=None, words=("yes", "no", "It is 3.", "I agree.")):
        self.rng, self.script, self.words = random.Random(seed), script, list(words)

    def with_effort(self, effort):
        return self

    def describe(self):
        return {"backend": "fake", "scripted": self.script is not None}

    def __call__(self, messages, schema_name, schema):
        reply = self.script(messages, schema_name) if self.script else self._value(schema)
        return json.dumps(reply), dict(ZERO_USAGE), {"returned_model": "fake", "seconds": 0.0, "retries": 0}

    def _value(self, s):
        if "anyOf" in s:
            return self._value(self.rng.choice(s["anyOf"]))
        if "enum" in s:
            return self.rng.choice(s["enum"])
        t = s["type"]
        if t == "object":
            return {k: self._value(v) for k, v in s["properties"].items()}
        if t == "array":
            return [self._value(s["items"]) for _ in range(self.rng.randint(0, 2))]
        if t == "integer":
            return self.rng.randint(0, 100)
        if t == "number":
            return round(self.rng.uniform(0, 100), 2)
        if t == "boolean":
            return self.rng.random() < 0.5
        if t == "string":
            return self.rng.choice(self.words)
        if t == "null":
            return None
        raise ValueError(s)


# --- schemas -----------------------------------------------------------------------

def obj(props, note=False):
    """A strict object schema; with note, a private note on the reason comes first (pilots only, module B7)."""
    props = ({"note": {"type": "string"}} if note else {}) | props
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def enum(values):
    values = list(values)
    return {"type": "integer" if all(isinstance(v, int) for v in values) else "string", "enum": values}


def nullable(s):
    return {"anyOf": [s, {"type": "null"}]}


# --- participants ----------------------------------------------------------------------

class Agent:
    """One participant: a private message history; it sees only what the study sends it.
    persona: text appended to the system message. memory: if set, the model sees the system message, the pinned
    prompt and the last `memory` turns; the full history is still recorded (module B1)."""

    def __init__(self, role, model, system, persona=None, memory=None, retry=RETRY):
        self.role, self.model, self.memory, self.retry, self.pin = role, model, memory, retry, None
        self.messages = [{"role": "system", "content": system + (f"\n\n{persona}" if persona else "")}]
        self.usage = {"calls": 0, **ZERO_USAGE}
        self.calls, self.failures = [], []

    def context(self):
        if not self.memory or self.pin is None:
            return self.messages
        window = self.messages[self.pin + 1:][-(2 * self.memory + 1):]
        if window and window[0]["role"] == "assistant":
            window = window[1:]
        return [self.messages[0], self.messages[self.pin]] + window

    def tell(self, text):
        """Information without a decision; it reaches the model with the next prompt."""
        self.messages.append({"role": "user", "content": text})

    def ask(self, prompt, schema_name, schema, pin=False):
        """pin: keep this prompt in view for the rest of the session when memory is limited."""
        self.messages.append({"role": "user", "content": prompt})
        if pin:
            self.pin = len(self.messages) - 1
        for attempt in range(2):
            self.usage["calls"] += 1
            text, usage, meta, error = None, {}, {}, None
            try:
                text, usage, meta = self.model(self.context(), schema_name, schema)
                answer = json.loads(text)
            except InvalidReply as e:
                error = e.args[0]
                usage, meta = (e.args[1], e.args[2]) if len(e.args) > 2 else ({}, {})
            except json.JSONDecodeError:
                error = "the reply was not valid JSON"
            for k, v in usage.items():
                self.usage[k] += v
            self.calls.append({"schema": schema_name, "time": now(), **meta, "usage": usage, "ok": error is None})
            if error is None:
                self.messages.append({"role": "assistant", "content": text})
                return answer
            self.failures.append({"schema": schema_name, "attempt": attempt + 1, "error": error, "text": (text or "")[:500]})
            if attempt:
                raise GroupFailed(f"{self.role}: unusable reply twice for {schema_name}: {error}")
            self.messages.append({"role": "user", "content": fill(self.retry, error=error)})

    def record(self):
        return {"messages": self.messages, "usage": self.usage, "calls": self.calls, "failures": self.failures}


class Notepad:
    """A notepad a participant adds to each turn and sees with every prompt (module B1). Add FIELD to the turn
    schema and pass the reply's text to add(); entries beyond `words` words are cut."""

    FIELD = {"scribble": {"type": "string"}}

    def __init__(self, words):
        self.words, self.entries = words, []

    def add(self, when, text):
        """Returns a problem message for the participant when the entry was cut, else None."""
        w = text.split()
        if w:
            self.entries.append((when, " ".join(w[: self.words])))
        return f"Only {self.words} words per entry; the rest was not written down." if len(w) > self.words else None

    def text(self):
        return "\n".join(f"- {when}: {t}" for when, t in self.entries) or "(empty)"

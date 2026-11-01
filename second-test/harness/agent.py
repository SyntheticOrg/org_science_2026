"""Agent adapter: one isolated conversation per agent against the OpenAI Responses API (stdlib only).

Adapted from first-test/harness/agent.py (kept separate so each experiment stays reproducible on its own).
Changes: placeholders are checked in the template rather than the filled text (agents' messages may contain
braces), the fake model draws search terms from a vocabulary, the turn schema is built per agent, and an optional
reasoning summary is requested and returned with each answer (the raw reasoning is never returned by the API).
"""

import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "gpt-6-luna"
EFFORT = "high"
API_URL = "https://api.openai.com/v1/responses"
ZERO_USAGE = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
SUMMARY_MODES = ("auto", "concise", "detailed")


# --- instructions --------------------------------------------------------------

def load_sections(path=HERE / "instructions.md"):
    """Text under each `## name` heading, verbatim."""
    parts = re.split(r"^## (\w+)\s*$", path.read_text(), flags=re.M)
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
    pass


class OpenAIModel:
    def __init__(self, model=MODEL, effort=EFFORT, summary=None):
        """summary: None, or one of SUMMARY_MODES to request a reasoning summary with every answer."""
        assert summary in (None, *SUMMARY_MODES), summary
        self.model, self.effort, self.summary, self.key = model, effort, summary, _api_key()

    def with_effort(self, effort):
        return OpenAIModel(self.model, effort, self.summary)

    def __call__(self, messages, schema_name, schema):
        """Returns (output text, usage, reasoning summary or None)."""
        reasoning = {"effort": self.effort, **({"summary": self.summary} if self.summary else {})}
        body = {
            "model": self.model,
            "input": messages,
            "reasoning": reasoning,
            "text": {"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": True}},
            "store": False,
        }
        data = self._post(body)
        if data.get("status") != "completed":
            raise ModelError(f"response status {data.get('status')}: {data.get('incomplete_details')}")
        text, summary = None, []
        for item in data.get("output", []):
            if item.get("type") == "reasoning":
                summary += [s["text"] for s in item.get("summary") or [] if s.get("type") == "summary_text"]
            for c in item.get("content") or []:
                if c.get("type") == "refusal":
                    raise ModelError(f"refusal: {c.get('refusal')}")
                if c.get("type") == "output_text":
                    text = c["text"]
        if text is None:
            raise ModelError("no output_text in response")
        u = data.get("usage") or {}
        usage = {
            "input_tokens": u.get("input_tokens", 0),
            "cached_tokens": (u.get("input_tokens_details") or {}).get("cached_tokens", 0),
            "output_tokens": u.get("output_tokens", 0),
            "reasoning_tokens": (u.get("output_tokens_details") or {}).get("reasoning_tokens", 0),
        }
        return text, usage, "\n\n".join(summary) if self.summary else None

    def _post(self, body, attempts=8):
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(req, timeout=900) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:500]
                if e.code not in (408, 409, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524) or attempt == attempts - 1:
                    raise ModelError(f"HTTP {e.code}: {detail}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == attempts - 1:
                    raise ModelError(f"network error: {e}") from e
            time.sleep(2 ** attempt + random.random())


class FakeModel:
    """Schema-conforming random answers, for checking the pipeline without API calls.
    Strings are drawn from `vocabulary` plus the capitalised words of the latest prompt, so that fake searches
    can hit. Not thread-safe across agents in a way that matters: only the pipeline is under test."""

    def __init__(self, seed=0, vocabulary=("Hall",), summary=None):
        self.rng = random.Random(seed)
        self.vocabulary = list(vocabulary)
        self.model, self.effort, self.summary = "fake", None, summary

    def with_effort(self, effort):
        return self

    def __call__(self, messages, schema_name, schema):
        words = re.findall(r"\b[A-Z][a-z]{2,}\b", messages[-1]["content"]) if messages else []
        self._words = self.vocabulary + words
        summary = f"(fake reasoning summary) Considering {', '.join(self.rng.sample(words, min(3, len(words))))}." if self.summary else None
        return json.dumps(self._value(schema)), dict(ZERO_USAGE), summary

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
        if t == "string":
            return self.rng.choice(getattr(self, "_words", self.vocabulary))
        if t == "null":
            return None
        if t == "boolean":
            return self.rng.random() < 0.3
        raise ValueError(s)


# --- schemas ---------------------------------------------------------------------

def _obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def _nullable(s):
    return {"anyOf": [s, {"type": "null"}]}


def turn_schema(suspects, names, recipients, ask_victim=True, inbox=False, notepad=False):
    """One turn: searches, messages (only if the agent has followers), and answer changes.
    Limits on the number of searches and messages are enforced by the engine, not the schema."""
    label = {"type": "string"}
    props = {
        "notes": {"type": "string"},  # private scratchpad, never shown to other players
        "searches": {"type": "array", "items": {"type": "string"}},
    }
    if recipients:
        props["messages"] = {"type": "array", "items": _obj({
            "to": {"type": "array", "items": {"type": "string", "enum": list(recipients)}},
            "text": {"type": "string"},
            "share_clues": {"type": "array", "items": label},
            "reply_to": _nullable(label),
            "forward": _nullable(label),
        })}
    if inbox:
        props["open_messages"] = {"type": "boolean"}
    if notepad:
        props["scribble"] = {"type": "string"}  # words added to the notepad; the engine enforces the word limit
    if ask_victim:
        props["victim"] = _nullable({"type": "string", "enum": list(names)})
    props["murderer"] = _nullable(_obj({
        "name": {"type": "string", "enum": list(suspects)},
        "confidence": {"type": "integer"},
    }))
    return _obj(props)


# --- agent -----------------------------------------------------------------------

class Agent:
    """One participant: a private message history; sees only what the engine sends it."""

    def __init__(self, player, model, persona=None, memory=None):
        """persona: optional description from personas.describe, added to the system message.
        memory: if set, after the pinned main-game instructions the model sees only the last `memory` turns
        (the full conversation is still recorded in self.messages)."""
        self.player, self.model, self.memory, self.pin = player, model, memory, None
        system = fill("system", player=player) + ("\n\n" + fill("persona", description=persona) if persona else "")
        self.messages = [{"role": "system", "content": system}]
        self.usage = {"calls": 0, **ZERO_USAGE}
        self.failures = []
        self.reasoning = []  # one reasoning summary (or None) per assistant message, in order

    def context(self):
        """What the model sees: everything, or with limited memory the system message, the pinned instructions
        and the last `memory` turns (each a user prompt and the reply), ending with the current prompt."""
        if not self.memory or self.pin is None:
            return self.messages
        after = self.messages[self.pin + 1:]
        window = after[-(2 * self.memory + 1):]
        if window and window[0]["role"] == "assistant":
            window = window[1:]
        return [self.messages[0], self.messages[self.pin]] + window

    def ask(self, prompt, schema_name, schema, pin=False):
        """pin: keep this prompt (the main-game instructions) in view for the rest of the game."""
        self.messages.append({"role": "user", "content": prompt})
        if pin:
            self.pin = len(self.messages) - 1
        for attempt in range(2):
            text, usage, summary = self.model(self.context(), schema_name, schema)
            self.usage["calls"] += 1
            for k, v in usage.items():
                self.usage[k] += v
            try:
                answer = json.loads(text)
                break
            except json.JSONDecodeError:
                self.failures.append({"kind": "invalid_json", "schema": schema_name, "text": text[:500]})
                if attempt:
                    raise ModelError(f"agent {self.player}: invalid JSON twice for {schema_name}")
        self.messages.append({"role": "assistant", "content": text})
        self.reasoning.append(summary)
        return answer

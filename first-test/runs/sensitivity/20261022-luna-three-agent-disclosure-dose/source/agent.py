"""Agent adapter: one isolated conversation per agent against the OpenAI Responses API (stdlib only)."""

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


# --- instructions --------------------------------------------------------------

def load_sections(path=HERE / "instructions.md"):
    """Text under each `## name` heading, verbatim."""
    parts = re.split(r"^## (\w+)\s*$", path.read_text(), flags=re.M)
    return {name: body.strip() for name, body in zip(parts[1::2], parts[2::2])}


SECTIONS = load_sections()


def fill(name, **values):
    text = SECTIONS[name]
    for k, v in values.items():
        text = text.replace("{" + k + "}", str(v))
    assert "{" not in text, f"unfilled placeholder in {name}"
    return text


def parse_quiz(name, **values):
    """[{question, options, answer, explanation}] from a quiz section."""
    items = []
    for block in re.split(r"^\d+\. ", fill(name, **values), flags=re.M)[1:]:
        body, answer = block.split("Answer:")
        letter, explanation = re.match(r"\s*(\w)\. Explanation: (.*)", answer, flags=re.S).groups()
        items.append({
            "question": " ".join(body.split()),
            "options": re.findall(r"\(([a-z])\)", body),
            "answer": letter,
            "explanation": explanation.strip(),
        })
    return items


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
    def __init__(self, model=MODEL, effort=EFFORT):
        self.model, self.effort, self.key = model, effort, _api_key()

    def __call__(self, messages, schema_name, schema):
        body = {
            "model": self.model,
            "input": messages,
            "reasoning": {"effort": self.effort},
            "text": {"format": {"type": "json_schema", "name": schema_name, "schema": schema, "strict": True}},
            "store": False,
        }
        data = self._post(body)
        if data.get("status") != "completed":
            raise ModelError(f"response status {data.get('status')}: {data.get('incomplete_details')}")
        text = None
        for item in data.get("output", []):
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
        return text, usage

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
                if e.code not in (408, 409, 429, 500, 502, 503, 504) or attempt == attempts - 1:
                    raise ModelError(f"HTTP {e.code}: {detail}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt == attempts - 1:
                    raise ModelError(f"network error: {e}") from e
            time.sleep(2 ** attempt + random.random())


class FakeModel:
    """Schema-conforming random answers, for checking the pipeline without API calls."""

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.model, self.effort = "fake", None

    def __call__(self, messages, schema_name, schema):
        return json.dumps(self._value(schema)), {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}

    def _value(self, s):
        if "anyOf" in s:
            return self._value(self.rng.choice(s["anyOf"]))
        if "enum" in s:
            return self.rng.choice(s["enum"])
        t = s["type"]
        if t == "object":
            return {k: self._value(v) for k, v in s["properties"].items()}
        if t == "integer":
            return self.rng.randint(0, 200)
        if t == "string":
            return "I think we should compare what each of us knows."
        if t == "null":
            return None
        if t == "boolean":
            return self.rng.random() < 0.5
        raise ValueError(s)


# --- schemas ---------------------------------------------------------------------

def _obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


RANKING = _obj({k: {"type": "string", "enum": ["A", "B", "C"]} for k in ("first", "second", "third")})
MESSAGE = _obj({"message": {"type": "string"}, "note": {"type": "string"}})
MARKET_ACTION = _obj({
    "action": {"type": "string", "enum": ["bid", "ask", "buy", "sell", "cancel", "pass"]},
    "applicant": {"anyOf": [{"type": "string", "enum": ["A", "B", "C"]}, {"type": "null"}]},
    "price": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
    "order_id": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
    "note": {"type": "string"},
})


def quiz_schema(items):
    return _obj({f"q{i + 1}": {"type": "string", "enum": it["options"]} for i, it in enumerate(items)})


# --- agent -----------------------------------------------------------------------

class Agent:
    """One participant: a private message history; sees only what the runner sends it."""

    def __init__(self, role, model, system_section="system"):
        self.role, self.model = role, model
        self.messages = [{"role": "system", "content": fill(system_section, role=role)}]
        self.usage = {"calls": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
        self.failures = []

    def ask(self, prompt, schema_name, schema):
        self.messages.append({"role": "user", "content": prompt})
        for attempt in range(2):
            text, usage = self.model(self.messages, schema_name, schema)
            self.usage["calls"] += 1
            for k, v in usage.items():
                self.usage[k] += v
            try:
                answer = json.loads(text)
                break
            except json.JSONDecodeError:
                self.failures.append({"kind": "invalid_json", "schema": schema_name, "text": text[:500]})
                if attempt:
                    raise ModelError(f"agent {self.role}: invalid JSON twice for {schema_name}")
        self.messages.append({"role": "assistant", "content": text})
        return answer

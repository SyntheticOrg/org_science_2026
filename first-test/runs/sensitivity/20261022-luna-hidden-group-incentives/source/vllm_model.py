"""Schema-constrained chat adapter for local vLLM or an authenticated Modal endpoint."""

import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from agent import ModelError

DEFAULT_SETTINGS = {"temperature": 0.6, "top_p": 0.95, "top_k": 20, "max_tokens": 8192, "enable_thinking": True}


class VLLMModel:
    def __init__(self, model, settings, api_url="http://127.0.0.1:8000/v1/chat/completions", authorization=None):
        self.model, self.settings = model, DEFAULT_SETTINGS | settings
        self.effort = "thinking" if self.settings["enable_thinking"] else None
        if model == "cmu-lti/osim-8b" and self.settings["enable_thinking"]:
            raise ValueError("OSim thinking has not passed preflight: its published template has no thinking switch, "
                             "and the Qwen3 template override did not produce reliable reasoning plus JSON. "
                             "Use Qwen for thinking, or explicitly set enable_thinking=false for native OSim.")
        if authorization and urlparse(api_url).scheme != "https":
            raise ValueError("Authenticated endpoints require HTTPS.")
        self.api_url = api_url
        self.headers = {"Content-Type": "application/json"}
        if authorization:
            self.headers["Authorization"] = authorization

    def __call__(self, messages, schema_name, schema):
        body = {"model": self.model, "messages": messages,
                **{key: self.settings[key] for key in ("temperature", "top_p", "top_k", "max_tokens")},
                "chat_template_kwargs": {"enable_thinking": self.settings["enable_thinking"]},
                "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "schema": schema, "strict": True}}}
        request = urllib.request.Request(self.api_url, data=json.dumps(body).encode(), headers=self.headers)
        try:
            with urllib.request.urlopen(request, timeout=900) as response:
                data = json.load(response)
        except urllib.error.HTTPError as error:
            raise ModelError(f"vLLM HTTP {error.code}: {error.read().decode(errors='replace')[:500]}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ModelError(f"vLLM request failed: {error}") from error
        try:
            choice = data["choices"][0]
            if choice["finish_reason"] != "stop":
                raise ModelError(f"vLLM completion ended with {choice['finish_reason']}")
            text = choice["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise ModelError("vLLM returned no final text content; reasoning may not have terminated")
            usage = data["usage"]
            return text, {"input_tokens": usage["prompt_tokens"], "cached_tokens": 0,
                          "output_tokens": usage["completion_tokens"],
                          "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)}
        except (KeyError, IndexError, TypeError) as error:
            raise ModelError("Malformed vLLM response") from error

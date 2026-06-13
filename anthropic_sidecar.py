"""
anthropic_sidecar.py  —  OPTIONAL DEV TOOL, NOT PART OF THE ASSIGNMENT

Runs FitFindr against a personal Anthropic API key instead of Groq, for when
Groq's free-tier daily token cap is exhausted during development. It does NOT
modify tools.py, agent.py, or app.py — it monkeypatches the client factory at
runtime, in memory only. The graded code stays exactly as the autograder
expects.

It is a sidecar, not a key swap: Groq speaks the OpenAI chat-completions shape,
Anthropic's Messages API uses tool_use/tool_result blocks, a top-level system
prompt, a required max_tokens, and rejects temperature on Opus/Fable. The shim
below exposes the same `client.chat.completions.create(...)` the code already
calls and translates both directions.

USAGE
    pip install anthropic
    # put ANTHROPIC_API_KEY=... in your .env (or export it)
    python anthropic_sidecar.py            # Gradio app on Anthropic
    python anthropic_sidecar.py agent      # agent.py CLI on Anthropic
    FITFINDR_ANTHROPIC_MODEL=claude-haiku-4-5 python anthropic_sidecar.py
        # override the model (default: claude-opus-4-8; Haiku is far cheaper)

TO REVERSE (no-nonsense)
    Run the app the normal way: `python app.py` or `python agent.py`.
    That path never imports this file. To remove it entirely, delete this one
    file. Nothing else references it.
"""
import json
import os
import sys
from types import SimpleNamespace

_DEFAULT_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 4096


# ── OpenAI-shape <-> Anthropic Messages API translation ───────────────────────

def _to_anthropic(messages, tools):
    system_parts, conv, pending = [], [], []

    def flush():
        if pending:
            conv.append({"role": "user", "content": list(pending)})
            pending.clear()

    for m in messages:
        role = m.get("role")
        if role == "system":
            if m.get("content"):
                system_parts.append(m["content"])
        elif role == "tool":
            pending.append({
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id"),
                "content": m.get("content") or "",
            })
        elif role == "user":
            flush()
            conv.append({"role": "user", "content": m.get("content") or ""})
        elif role == "assistant":
            flush()
            blocks = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m.get("tool_calls") or []:
                blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"] or "{}"),
                })
            conv.append({"role": "assistant", "content": blocks or ""})
    flush()

    anth_tools = None
    if tools:
        anth_tools = [{
            "name": t["function"]["name"],
            "description": t["function"].get("description", ""),
            "input_schema": t["function"]["parameters"],
        } for t in tools]
    return "\n\n".join(system_parts), conv, anth_tools


def _from_anthropic(response):
    text_parts, tool_calls = [], []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(SimpleNamespace(
                id=block.id,
                type="function",
                function=SimpleNamespace(
                    name=block.name,
                    arguments=json.dumps(block.input),
                ),
            ))
    message = SimpleNamespace(
        content="".join(text_parts) or None,
        tool_calls=tool_calls or None,
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class _AnthropicChatShim:
    """Stand-in for the Groq client, exposing chat.completions.create."""

    def __init__(self, client, model):
        self._client = client
        self._model = model
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create))

    def _create(self, *, messages, tools=None, tool_choice=None,
                temperature=None, model=None, max_tokens=_MAX_TOKENS, **kwargs):
        # temperature is dropped (Opus/Fable reject it); the Groq model id
        # passed by callers is ignored in favor of self._model.
        system, conv, anth_tools = _to_anthropic(messages, tools)
        params = {"model": self._model, "max_tokens": max_tokens,
                  "messages": conv}
        if system:
            params["system"] = system
        if anth_tools:
            params["tools"] = anth_tools
            params["tool_choice"] = {"type": "auto"}
        print(f"[sidecar] anthropic call: model={self._model} "
              f"turns={len(conv)} tools={len(anth_tools or [])}",
              file=sys.stderr, flush=True)
        try:
            response = self._client.messages.create(**params)
        except Exception as exc:
            # agent.py catches this and shows a generic message, so surface the
            # real Anthropic error here for diagnosis (rate limit, bad request).
            print(f"[sidecar] ANTHROPIC CALL FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr, flush=True)
            raise
        stop = getattr(response, "stop_reason", None)
        print(f"[sidecar] anthropic ok: stop_reason={stop} "
              f"blocks={len(response.content)}", file=sys.stderr, flush=True)
        return _from_anthropic(response)


def _build_client():
    """No-arg factory matching tools._get_groq_client's signature."""
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit("Install the Anthropic SDK first: pip install anthropic") from exc
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY not set. Add it to .env or export it.")
    model = os.environ.get("FITFINDR_ANTHROPIC_MODEL", _DEFAULT_MODEL)
    return _AnthropicChatShim(anthropic.Anthropic(api_key=key), model)


def main():
    # Default the trace flag ON for sidecar runs so you always see the stream.
    os.environ.setdefault("FITFINDR_LOG", "1")

    from dotenv import load_dotenv
    load_dotenv()

    # Patch the factory in tools BEFORE app/agent import it, so their
    # `from tools import _get_groq_client` binds to the patched version.
    import tools
    tools._get_groq_client = _build_client

    model = os.environ.get("FITFINDR_ANTHROPIC_MODEL", _DEFAULT_MODEL)
    print(f"[sidecar] Provider: Anthropic, model: {model}. "
          f"Graded code untouched. Run `python app.py` for the normal Groq path.",
          file=sys.stderr)

    target = sys.argv[1] if len(sys.argv) > 1 else "app"
    if target == "agent":
        import runpy
        runpy.run_module("agent", run_name="__main__")
    elif target == "app":
        import app
        app.build_interface().launch()
    else:
        raise SystemExit(f"Unknown target '{target}'. Use 'app' or 'agent'.")


if __name__ == "__main__":
    main()

"""Agent-level tests for the planning loop's terminal states.

These mock the Groq client so they are deterministic and keyless. They pin
the behavior added for non-shoppable input: a router final message with no
tool call is a conversational answer (session["response"]), a success path,
not an error. Genuine dead-ends still fall back to session["error"].
"""
from types import SimpleNamespace

import agent
from utils.data_loader import get_example_wardrobe


def _completion(content=None, tool_calls=None):
    """Fake one Groq chat completion (router turn)."""
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class ScriptedClient:
    """Returns pre-scripted completions in order, one per router iteration."""

    def __init__(self, completions):
        self._completions = list(completions)
        self.calls = 0
        outer = self

        def create(**kwargs):
            c = outer._completions[outer.calls]
            outer.calls += 1
            return c

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_info_answer_is_response_not_error(monkeypatch):
    # Router answers a standalone question directly, no tool call.
    answer = "Trending in tops right now: y2k, crochet, dark academia."
    monkeypatch.setattr(agent, "_get_groq_client",
                        lambda: ScriptedClient([_completion(content=answer)]))
    s = agent.run_agent("what's trending in tops?", get_example_wardrobe())
    assert s["response"] == answer
    assert s["error"] is None
    assert s["fit_card"] is None


def test_greeting_is_response_not_error(monkeypatch):
    redirect = ("FitFindr finds and styles secondhand fashion. Try: vintage "
                "graphic tee under $30, size M.")
    monkeypatch.setattr(agent, "_get_groq_client",
                        lambda: ScriptedClient([_completion(content=redirect)]))
    s = agent.run_agent("hey", get_example_wardrobe())
    assert s["response"] == redirect
    assert s["error"] is None


def test_empty_final_message_falls_back_to_error(monkeypatch):
    # A truly empty final message is not a usable answer, so it is an error.
    monkeypatch.setattr(agent, "_get_groq_client",
                        lambda: ScriptedClient([_completion(content="")]))
    s = agent.run_agent("???", get_example_wardrobe())
    assert s["response"] is None
    assert "stopped without producing" in s["error"]


def test_missing_api_key_is_error_not_crash(monkeypatch):
    def boom():
        raise ValueError("GROQ_API_KEY not set.")
    monkeypatch.setattr(agent, "_get_groq_client", boom)
    s = agent.run_agent("vintage tee", get_example_wardrobe())
    assert s["error"] == "GROQ_API_KEY not set."
    assert s["response"] is None
    assert s["fit_card"] is None

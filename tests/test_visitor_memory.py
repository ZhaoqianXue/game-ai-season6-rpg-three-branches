"""Regression tests for a promise that crosses visits, and for pausing a reply."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from agent import Agent, CHAT_PAUSE_TICKS
from sandbox.env import META, make_env
from sandbox.harness.environment import resolve_parameters
from sandbox.village import me


@pytest.fixture(scope="module", params=[17, 31, 53])
def village(request):
    seed = request.param
    params = resolve_parameters(META, {"seat_plan": "cast_10", "daynight": True})
    env = make_env(params)
    try:
        observations, _ = env.reset(seed=seed)
        yield seed, observations
    finally:
        env.close()


def scene(village):
    seed, observations = village
    obs = deepcopy(observations["player_1"])
    keeper = Agent()
    keeper.reset(seed, obs)
    return keeper, obs


def visit(keeper, obs, phase, tick, present):
    obs["phase"] = phase
    obs["tick"] = tick
    # Supply the one observation the keeper would get when the visitor is in earshot.
    obs["nearby"] = ({"id": "player_0", "position": dict(me.position(obs))},) if present else ()
    return keeper.act(obs)


def question(keeper, text, recipient="player_1"):
    return keeper.chat([{"from": "player_0", "to": recipient, "text": text}])


def test_only_a_keeper_that_promised_can_resume_the_tour(village):
    keeper, obs = scene(village)
    control, control_obs = scene(village)
    for resident, sight in ((keeper, obs), (control, control_obs)):
        visit(resident, sight, "midday", 500, True)
    offered = question(keeper, "Show me your workplace")
    assert "after lunch" in offered[0]["text"]
    assert keeper.memory.get("guide_until") is None
    visit(keeper, obs, "midday", 533, False)
    visit(keeper, obs, "midday", 550, True)
    assert keeper.chat([]) == []
    visit(keeper, obs, "midday", 560, False)
    visit(control, control_obs, "midday", 560, False)

    visit(keeper, obs, "evening", 760, True)
    visit(control, control_obs, "evening", 760, True)
    assert any("promised" in line["text"] for line in keeper.chat([]))
    assert keeper.memory["routine"] == "guide"
    assert control.chat([]) == []
    assert control.memory["routine"] != "guide"

    visit(keeper, obs, "night", 1000, True)
    assert keeper.memory["routine"] == "sleep_at"
    assert not keeper.memory.get("tour_offer")


def test_named_reply_pauses_routine_and_survives_a_model_failure(village):
    keeper, obs = scene(village)
    keeper.memory["visitor_handled"] = True
    visit(keeper, obs, "morning", 300, True)

    def unavailable(**kwargs):
        raise RuntimeError("no model response")

    keeper.dialogue.llm = SimpleNamespace(requesting=False, error=None, request=unavailable)
    reply = question(keeper, "What is your occupation?")
    assert "Mira" in reply[0]["text"]
    assert visit(keeper, obs, "morning", 301, True)["speed"] == 0.0
    assert keeper.memory["routine"] == "talk"
    visit(keeper, obs, "morning", 300 + CHAT_PAUSE_TICKS, True)
    assert keeper.memory["routine"] == "tend"

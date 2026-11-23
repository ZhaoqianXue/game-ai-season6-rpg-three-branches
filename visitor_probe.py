"""Make a midday request, leave hearing range, and revisit in complete seeded days."""

import argparse
import json
from pathlib import Path

import routines
import routing
from agent import Agent, RESIDENTS
from sandbox.env import META, default_action, extract_overlay, extract_overlay_static, make_env
from sandbox.harness.environment import EnvironmentEntry, resolve_layout, resolve_parameters
from sandbox.harness.session import AgentPlayer, run_episode
from sandbox.season import load_season_settings
from sandbox.village import action, day, geometry, me, people, props


ROOT = Path(__file__).resolve().parent


class Visitor:
    def reset(self, seed, observation):
        graph = routing.build_graph(observation)
        self.memory = {"graph": graph, "components": routing.components(graph), "routines": {}}
        self.start = dict(me.position(observation))
        self.latest = observation
        self.requested = False
        self.target = None
        self.workplace = None
        self.offer_tick = None
        self.left_tick = None
        self.return_tick = None
        self.resume_tick = None
        self.arrival_tick = None
        self.lines = []

    def act(self, observation):
        self.latest = observation
        tick = day.tick(observation)
        here = me.position(observation)
        heard = [person for person in people.nearby(observation) if people.is_npc(person["id"])]
        partner = next((person for person in heard if person["id"] == self.target), None)
        if self.offer_tick is None:
            if self.requested:
                return action.stand(me.heading(observation))
            if 520 <= tick <= 650 and heard:
                best = min(heard, key=lambda person: geometry.distance(here, person["position"]))
                self.target = best["id"]
                slot = int(self.target.split("_")[-1]) - 1
                kind = RESIDENTS[slot].work
                workplaces = [prop for prop in props.all(observation) if prop["type"] == kind]
                nearest = min(workplaces, key=lambda prop: geometry.distance(
                    here, routines.goal_point(observation, prop["id"])
                ))
                self.workplace = nearest["id"]
                return action.stand(me.heading(observation))
            return routines.go_to(observation, self.memory, "inn")
        if self.left_tick is None and partner is None:
            self.left_tick = tick
        if tick < 729 or self.left_tick is None:
            return routines.go_to(observation, self.memory, self.start)
        if tick >= 960 or self.arrival_tick is not None:
            return action.stand(me.heading(observation))
        if partner is not None:
            self.return_tick = tick if self.return_tick is None else self.return_tick
            if geometry.distance(here, partner["position"]) <= 2.4:
                return action.stand(geometry.heading_to(here, partner["position"]))
            return routines.go_to(observation, self.memory, partner["position"])
        visible_partner = people.find(observation, self.target)
        goal = visible_partner["position"] if visible_partner is not None else self.workplace
        return routines.go_to(observation, self.memory, goal)

    def chat(self, inbox):
        tick = day.tick(self.latest)
        for item in inbox:
            if item["from"] != self.target:
                continue
            line = item["text"]
            self.lines.append({"tick": tick, "speaker": item["from"], "text": line})
            if "after lunch" in line:
                self.offer_tick = tick
            if "promised" in line:
                self.resume_tick = tick
            if "Here we are" in line:
                self.arrival_tick = tick
        if self.target is not None and not self.requested:
            self.requested = True
            return [{"to": self.target, "text": "Could you show me where you work?"}]
        return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[17, 31, 53])
    args = parser.parse_args()
    season = load_season_settings(ROOT, META)
    parameters = resolve_parameters(META, season.parameters)
    layout = resolve_layout(META, parameters)
    entry = EnvironmentEntry(META, make_env, default_action, extract_overlay, extract_overlay_static)
    results = []
    for seed in args.seeds:
        guest = Visitor()
        cast = {player: AgentPlayer(guest if player == "player_0" else Agent())
                for player in layout.players}
        result = run_episode(entry, cast, seed=seed, parameters=parameters,
                             step_limit_ms=META.step_limit_ms, episode_limit_ms=META.episode_limit_ms)
        row = {"seed": seed, "ticks": result.ticks, "reason": result.reason, "scores": result.scores,
               "timeouts": sum(result.step_timeouts.values()), "error": result.error,
               "resident": guest.target, "offer_tick": guest.offer_tick, "left_tick": guest.left_tick,
               "return_tick": guest.return_tick, "resume_tick": guest.resume_tick,
               "arrival_tick": guest.arrival_tick, "lines": guest.lines}
        results.append(row)
        print(json.dumps(row), flush=True)
    (ROOT / "evidence" / "season6-visitor.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()

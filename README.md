# Season 6 — RPG: The Living Village

Zhaoqian Xue / purpleman / GitHub @ZhaoqianXue

## Design goal

A visitor should have time to finish a conversation. If a villager offers a workplace tour during a midday break, the visitor should be able to leave, come back in the evening, and see that same villager remember the offer.

**Rating question (1–5):** How well do villagers pause for conversation and follow through on a workplace tour when you return after lunch? To try the tour, ask a villager “Could you show me where you work?” during midday, leave hearing range, and return in the evening.

## Changes after Season 5

Season 5 averaged 3.8/5 from four peers. Reviewers could ask about props and jobs, but reported villagers walking off mid-conversation, multiple replies to one question, and player IDs breaking immersion. A resident now faces the visitor and pauses for 28 ticks after a question, with a 64-tick cap per visit. To answer a broadcast, it compares its distance with residents it currently knows can hear the visitor. A direct message can reach a different resident. Walls and limited awareness mean the local choice does not guarantee a single reply in every crowd. Replies name visible characters instead of printing their IDs.

At midday, a workplace request records a private offer. It can start a tour in the evening after the visitor has left hearing range and returned. The resident waits when its guest falls behind in earshot. It reports arrival only when it can interact with the workplace. If the guest leaves during the walk or the tour runs out of time, regular work resumes. At night, the resident goes home and clears the offer. Another resident does not inherit it.

The Season 5 model is retained for broad questions. It selects one intent label, and the script writes the reply from current observations and authored character facts. It uses the small tier with at most three attempts per resident per day, a 15-second request timeout, and one request in flight. The offer, continuation, and known world facts use scripts, so they survive an unavailable model. This keeps timing and commitments predictable, at the cost of a narrower conversation than open-ended text generation.

## Verification

`season.json` uses the downloaded ten-villager, day/night settings. In Python 3.12, install the provided requirements and run:

```sh
python -m sandbox test
python -m sandbox eval --seeds 17 31 53
python visitor_probe.py
```

- **132 project checks passed**, with seven Gymnasium casting warnings. Targeted tests cover requesting a tour, leaving, returning at the wrong and right times, a resident who never made the offer, night, a conversation pause, and a failed model request.
- The three standard evaluation days scored 100.00 each. That score measures episode completion.
- Three full scripted visitor days took the agent through an actual direct request, departure, and return. The same villager remembered the offer on all three seeds. The arrival line was observed on seeds 17 and 53. On seed 31, the villager remembered the offer but the probe did not observe arrival. No decision timed out. The observed chat and ticks are in `evidence/season6-visitor.json`.
- Local runs used no model credentials. They establish scripted follow-through and fallback behavior. They do not test upstream response quality.

## AI use and reflection

OpenAI Codex read the brief and peer feedback, wrote the conversation and memory changes, adapted the visitor probe, ran the tests, and drafted this README. The course template supplies the environment and observation helpers. A complete day alone did not establish that a promise was kept. Testing a return visit separately showed the difference between remembering an offer and getting the visitor all the way to the workplace. Codex operated the local tests.

# New Haven · The Living Valley

[Play in your browser](https://new-haven-bafjr8dqjy7ntdystyayut.streamlit.app/) · [How the model works](docs/MODEL.md)

A small artificial society you can watch, explore, interrupt, and compare. Follow a citizen from their morning walk to their next friendship, inspect the businesses behind the town, or change one policy and see two possible futures.

## Play

Open the browser link; no installation or API key is needed. Press **Play**, click a resident, and watch their activity and memories change. Drag the isometric map to pan; use the zoom buttons, mouse wheel, or arrow keys. All residents are also selectable through the searchable Citizens page.

Try a storm, a festival, food relief, education, a different income tax, or better farm tools. Every council action has a recorded consequence; funded actions require enough treasury. Save your world as JSON and load it later to resume the same random sequence. Refreshing the browser or a server restart can end an unsaved session, so save before leaving.

## Included

- A high-contrast interface with a detailed voxel-style Canvas valley: terraced hills, forests, timber houses, council tower, market, school, mine, farms, windmill and river crossing.
- Persistent flood damage, disrupted production and trade, funded building repairs, timber and stone, and daily food/money ledgers. Damaged buildings and scaffolding appear in the world.
- Limited relief, cooldowns, scaled upgrade costs and diminishing benefits. Citizens sacrifice wages to forage or participate in recovery.
- A deterministic Python engine with personality, goals/progress, needs/rest, work, wages, taxes, business accounts, food purchases, and public meal support.
- Directional friendships/rivalries, adult marriages, children with parents, ageing, deaths and bereavement. Event-driven memories preserve personal context.
- World, Citizens, Economy, Chronicle, Experiments and Field Guide views. Charts give each metric its own scale.
- Browser save/load with versioned JSON and random-generator state; validation rejects malformed worlds. Saves never contain API credentials.
- Paired-seed experiments: baseline versus intervention, or rules versus explicitly requested AI reflection. Aggregate differences, per-seed outcomes and variation are shown separately.
- Optional OpenAI Responses API cognition with constrained actions, no automatic retries, an explicit call limit, and recorded decisions. Off by default.
- Automated engine, replay, lifecycle, input-validation, cognition and experiment checks; GitHub Actions runs them for every push.

## Optional AI

**Default citizens are rule-based agents, not autonomous language models.** Personality, needs and memories influence programmed responses. The interface labels these decisions RULES, and completed model decisions AI, with their actual effects. Graphics are not intelligence.

Expand **Optional AI cognition** below the interface, enable it, and enter your own OpenAI API key and a model supporting structured outputs. Keys stay in the current server session and are not sent to the Canvas component or included in saves. Use **Forget API key** to clear it. No shared owner key is exposed to public visitors.

Only **Reflect on an event** or an explicitly selected **AI comparison** makes paid requests. Eligible events include loss, conflict, friendship, marriage and civic petitions. The model can propose `seek_work`, `help_neighbor`, `rest`, or `organize`; the engine validates the action and applies bounded changes. Plain simulation ticks never make API calls.

The call limit defaults to 10 and counts failed requests. Responses are capped at 400 output tokens. This is a request limit, not a guaranteed currency budget; provider prices and model token use vary. AI comparisons assign the same available call allowance to each seed and report actual use. AI outputs themselves are not deterministic, but their applied decisions are recorded in saves. The provider adapter is covered with mocked responses; live paid calls require your key.

Implementation follows the [official structured outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs).

## Develop

Python 3.10+; no frontend build step or Node runtime is needed to serve the app.

```bash
git clone https://github.com/ompranush/new-haven.git
cd new-haven
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

On Streamlit Community Cloud, deploy branch `main`, entrypoint `app.py`. Keep the `frontend/` directory alongside it.

```bash
python -m unittest discover -s tests -v
python -m src.civilisation --seed 7 --population 100 --days 365
python -m src.civilisation --compare education --seeds 3 --days 90
node --check frontend/app.js  # optional frontend development checks
node --check frontend/world.js
```

## Structure

```text
app.py                          Session host and validated action dispatch
frontend/index.html             Interface structure
frontend/style.css              High-contrast responsive layout
frontend/app.js                 Interactions, ledgers and inspection
frontend/world.js               State-driven voxel-style diorama
src/civilisation/models.py      Citizen and world records
src/civilisation/sim.py         Economy, social/life rules, save/load
src/civilisation/cognition.py   Optional constrained event reflection
src/civilisation/experiments.py Isolated paired-seed experiments
src/civilisation/__main__.py    Headless runs
tests/                          Regression and independent review tests
docs/MODEL.md                   Assumptions, units, limits and interpretation
```

## Scope and next research steps

This is an interactive toy society, not a validated model of real economies or population dynamics. The browser starts with 20–250 citizens and caps experiments at 10 seeds and 365 days. The engine supports up to 1,000 initial citizens and 2,000 lifetime citizen records. It has not been validated for 10,000 agents over 1,000 years.

Businesses currently have a fixed roster; nonfarm revenue represents outside trade. New firms, bankruptcy, autonomous political movements, housing markets, richer inheritance, persistent hosted accounts, and research-scale batch scheduling are future work. Event/history retention is bounded for browser performance. See MODEL.md for exact assumptions. These boundaries are deliberate and visible rather than implied as completed research features.

## Try the consequences

Apply **River flood**, then inspect the farm: food falls immediately, buildings lose condition and a 14-day disruption begins. Advance one day at a time to see repair costs and material use. Request one relief convoy: transport costs money, food is imported, and another convoy needs 30 days. In Research, the day-17 checkpoint exposes first-week damage that final outcomes can hide. Unavailable interventions are reported per seed rather than forced.

Hills and vegetation are scenery. Building condition, repairs, residents and crisis effects come from the simulation. This is a 2.5D voxel-style diorama, not a photorealistic reproduction of the concept image. Ambient movement does not advance time. Save before leaving: the world does not run after the browser closes.

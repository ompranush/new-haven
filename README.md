# New Haven

New Haven is a local-first, deterministic AI civilisation simulator. A town of autonomous residents works, socialises, accumulates wealth, forms partnerships, remembers notable experiences, and responds to food, weather, and shared events.

The MVP deliberately has **no LLM or API dependency**. The inexpensive rules engine makes runs reproducible and inspectable; a future cognition layer can be reserved for high-salience moments rather than every citizen action.

## What is in v0.3

- Seeded, reproducible worlds (same seed + same actions = same result)
- Citizens with jobs, goals, wealth, happiness, sociability, relationships, locations, and short memories
- Balanced food production and consumption, local food pricing, employment, daily needs, weather, a town treasury, births, and deaths
- Town events and user-led council interventions: harvest rain, trade caravans, cold snaps, festivals, relief, price caps, and food shortages
- A game-like Streamlit control room with an original SVG isometric town, resident inspector, town chronicle, responsive HUD, and separate analytics
- Automated tests for reproducibility, history, boundaries, memory, and invalid actions

## Run it

Requires Python 3.10+.

```bash
git clone https://github.com/ompranush/new-haven.git
cd new-haven
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown by Streamlit. Select a seed, create a world, then advance one or ten days at a time.

## Test it

```bash
python -m unittest discover -s tests
```

## Project layout

```text
app.py                       Streamlit control room
src/civilisation/models.py   Citizen and world state
src/civilisation/sim.py      Deterministic simulation engine
tests/test_sim.py            Engine contracts
```

## Design principle

The simulation owns state transitions. Any future LLM component should receive a compact account of an important event, return a constrained decision, and let the engine validate and apply that decision. This keeps costs controlled and experiments repeatable.

## Next experiments

1. Persist simulation runs and event logs to SQLite.
2. Add businesses, housing, beliefs, policies, migration, and a save/load run archive.
3. Run scenario batches to compare inequality, food shocks, or automation policies.
4. Add optional, rate-limited LLM reflection only for significant social events.

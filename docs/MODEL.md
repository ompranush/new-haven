# Model assumptions and interpretation

## Time and reproducibility

One tick represents one day. Ages advance by 1/365; seasons change every 90 days. Citizens move one grid step toward a workplace, school, home or crossing each day. Animation interpolates those positions; it does not run a separate hidden simulation.

The engine owns one `random.Random(seed)` instance. The same seed, engine version and ordered actions reproduce the same result. Saves store its full state as JSON, never pickle. Load validates schema, resource ranges, employment, partnership reciprocity and event identity before replacing a live world. Version 1 saves belong to this engine; the old dashboard had no compatible save format.

## Money, food and businesses

Coins are arbitrary simulation units, displayed with £ for convenience. Eight businesses have cash, workers, capacity and daily profit. Nonfarm production earns outside export revenue before wages are paid. Farmers produce food which earns revenue when residents buy meals. Wages move business cash to citizens and income tax to the treasury. Unpaid wages cause discontent and events. Public funds can pay for meals when citizens cannot afford them.

Adults eat one food unit daily; children eat 0.6. Meals are allocated in seeded shuffled order to avoid systematically favouring lower citizen IDs. Food is capped by storage capacity. Weather and winter affect production; storms can damage food and personal wealth. Hunger harms health and happiness; exhausted or unwell residents rest and recover. This is intentionally a simplified open economy, not a closed-money or market-clearing model.

Education affects wage skills. Farm automation improves yield. Income tax toggles between two flat rates; it is not a progressive tax model. Price caps persist until toggled off. Festivals cost treasury and raise happiness. Relief is explicitly externally funded, and is a sandbox intervention rather than an internally financed policy.

## Citizens and life events

Five personality values shape social interaction. Relationships are directional; friendship and rivalry thresholds generate memories. Adult reciprocal relationships can become marriages; minors and close family cannot marry. Partners are paired by citizen ID, including ID zero. Children have two parent IDs; they attend school, do not work, and draw food support from parents or public funds. Death removes workers and clears a surviving partner's marriage link.

Births and age-related deaths are probabilistic. Short runs may have no births or marriages. Births, politics and business behaviour are deliberately modest: there are civic petitions, not autonomous parties/elections, and no dynamic business founding or bankruptcy yet.

## Experiments and cognition

Intervention experiments start two worlds from each seed and apply one action to treatment on day 10 (or the last day for shorter horizons). The baseline remains untouched. Different actions may cause random paths to diverge. Mean paired differences and their standard deviation describe only these runs; they are not significance tests.

AI comparisons use the same starting seeds with no council intervention. Treatment may reflect on eligible events, within an equal per-seed call allowance. The selected council scenario is ignored in this mode. Some seeds may produce fewer eligible events. Actual AI calls are listed per run. External outputs are variable; recorded decisions explain resulting differences but do not establish causation about human societies.

## Storage and scale

Each browser session has an independent world. Save files are the persistence mechanism; there is no account database or shared multiplayer world. The interface accepts save files up to 8 MB. The engine retains at most 30 memories per citizen, 200 town events, 2,000 metric records, 20 pending reflections and 100 AI decisions. It caps lifetime citizen records at 2,000.

Browser controls start 20–250 citizens. Headless construction permits 2–1,000. Automated checks include multiple seeds over years of simulated time, but do not establish performance or scientific validity at 10,000 citizens and 1,000 years.

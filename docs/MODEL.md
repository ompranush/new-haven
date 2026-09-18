# Model assumptions and interpretation

## Time and reproducibility

One tick represents one day. Ages advance by 1/365; seasons change every 90 days. Citizens move one grid step toward a workplace, school, home or crossing each day. Animation interpolates those positions; it does not run a separate hidden simulation.

The engine owns one `random.Random(seed)` instance. The same seed, engine version and ordered actions reproduce the same result. Saves store its full state as JSON, never pickle. Load validates schema, resource ranges, employment, partnership reciprocity and event identity before replacing a live world. Version 1 saves belong to this engine; the old dashboard had no compatible save format.

## Money, food and businesses

Coins are arbitrary simulation units, displayed with £ for convenience. Eight businesses have cash, workers, capacity and daily profit. Nonfarm production earns outside export revenue, bounded by finite seasonal orders, workplace condition and flooded roads. Local purchases circulate existing money. Farmers produce food which earns revenue when residents buy meals. Wages move business cash to citizens and income tax to the treasury. Unpaid wages cause discontent and events. Public funds can pay for meals when citizens cannot afford them.

Adults eat one food unit daily; children eat 0.6. Meals are allocated in seeded shuffled order to avoid systematically favouring lower citizen IDs. Food is constrained by storage capacity and spoilage. Weather and winter affect production; floods destroy food, damage buildings and charge emergency response. Hunger harms health and happiness; exhausted or unwell residents rest and recover. This is intentionally a simplified open economy, not a closed-money or market-clearing model.

Education affects wage skills. Farm automation improves yield with square-root diminishing returns. Investments cost more per level, have a 30-day cooldown and five-level cap. Income tax toggles between two flat rates; it is not a progressive tax model. Price caps persist until toggled off. Festivals cost treasury, have a 30-day cooldown and give less benefit to already-happy citizens. Relief requires a shortage or active disaster, imports two days of food, charges transport and has a 30-day cooldown. Food remains external aid, not domestic production; no money is granted.

## Damage, recovery and accounting

Severe floods destroy 28% of stored food, charge response up to 1.2 coins per living citizen, and damage buildings (farm 36 condition points, eastern buildings 24, others 12). Harvests and trade suffer for 14 days with severity decaying daily. Lesser storms reduce that day's output without structural damage. Active floods cannot stack; structural damage remains after water recedes.

Repairs require eligible builders. Each restored condition point consumes two treasury coins, 0.5 wood and 0.3 stone. Foresters and miners replenish materials. Scarcity can cause citizens to give up paid work and forage. These responses are labelled RULES; they are not LLM outputs. Decision logging is capped and has cooldowns to avoid repetitive spam.

The food ledger reconciles opening + production + imports − consumption − losses = closing. The money ledger covers the **entire economy**, not only council funds: treasury + citizens + business balances. Trade adds money; upkeep, interventions and repairs remove it. Taxes, wages, gifts and purchases transfer existing funds. Deceased citizens retain estates; inheritance is not modelled. Multi-year treasury accumulation remains possible—this is not a calibrated equilibrium.

## Citizens and life events

Five personality values shape social interaction. Relationships are directional; friendship and rivalry thresholds generate memories. Adult reciprocal relationships can become marriages; minors and close family cannot marry. Partners are paired by citizen ID, including ID zero. Children have two parent IDs; they attend school, do not work, and draw food support from parents or public funds. Death removes workers and clears a surviving partner's marriage link.

Births and age-related deaths are probabilistic. Short runs may have no births or marriages. Births, politics and business behaviour are deliberately modest: there are civic petitions, not autonomous parties/elections, and no dynamic business founding or bankruptcy yet.

## Experiments and cognition

Intervention experiments start two worlds from each seed and attempt one action on day 10 (or the last day for shorter horizons). Unavailable actions (for example, a flood already active or insufficient funds) are reported per seed instead of forced. Those runs remain in the aggregate. Emergency relief is excluded from experiments. A day-17 checkpoint exposes first-week differences. The baseline remains untouched. Different actions may cause random paths to diverge. Mean paired differences and their standard deviation describe only these runs; they are not significance tests.

AI comparisons use the same starting seeds with no council intervention. Treatment may reflect on eligible events, within an equal per-seed call allowance. The selected council scenario is ignored in this mode. Some seeds may produce fewer eligible events. Actual AI calls are listed per run. External outputs are variable; recorded decisions explain resulting differences but do not establish causation about human societies.

## Village indicators and God Mode

Political preferences are fictional economic and social axes, not real party affiliations. Scarcity, tax and education influence explicit toy rules; these are not autonomous elections. Wealth inequality uses living citizens' balances: Gini ranges from 0 to 1, alongside median wealth and the richest tenth's share. Friendship/rivalry counts use unique pairs and their mean directional score; isolation means no strong friendship or spouse.

Crime records simulated theft, transferring existing money from victim to offender. The dashboard reports up to 30 observed days and incidents per 1,000 citizen-days, not a fabricated annual crime percentage. No observation is shown as “Not observed”, not zero. Gender comparisons report adult employment, wealth and observed wages by group; there is no invented composite equality score. Gender does not affect hiring, pay, political updates or crime selection. Small-group differences are descriptive random outcomes, not evidence about real populations. Identity and political initialization use independent seeded randomness; observations survive save/load.

God Mode translates text into a strict, bounded action schema. The server validates identifiers, amounts, affordability and cooldowns, previews effects on a cloned world, then requires confirmation against the exact unchanged world state. It never executes model-generated code. Resource overrides are explicitly external additions/removals in the ledger. Building repair consumes the usual coins and materials. Relationship changes cannot force marriage or rewrite identity. Refused, incomplete, malformed or unaffordable plans leave the world unchanged; requests still count toward the API call limit.

## Session persistence

Each browser session has an independent world. Save files are the persistence mechanism; there is no account database or shared multiplayer world. The interface accepts save files up to 8 MB. The engine retains at most 30 memories per citizen, 200 town events, 2,000 metric records, 20 pending reflections and 100 combined rules/AI decisions. It caps lifetime citizen records at 2,000.

Browser controls start 20–250 citizens. Headless construction permits 2–1,000. Automated checks include multiple seeds over years of simulated time, but do not establish performance or scientific validity at 10,000 citizens and 1,000 years.

"""Transparent fictional social rules, not estimates of real human behaviour.

Identity and initial preferences use a separate seeded stream. Gender never
enters hiring, pay, political shifts, or offending decisions.
"""
import math
import random
from statistics import mean, median

GENDERS = ("woman", "man", "nonbinary")


def initialise_citizen(citizen, seed):
    rng = random.Random(f"new-haven-society:{seed}:{citizen.id}")
    citizen.gender = rng.choices(GENDERS, weights=(47, 47, 6))[0]
    citizen.political_economic = round(rng.uniform(-1, 1), 4)
    citizen.political_social = round(rng.uniform(-1, 1), 4)


def advance_society(sim):
    people = sim.living
    day = sim.world.day
    sim.society_observations.append({"day": day, "population": len(people)})
    sim.society_observations = [r for r in sim.society_observations if day-r["day"] < 30]
    sim.crime_events = [r for r in sim.crime_events if day-r["day"] < 30]
    shortage = min(1., max(0., 1-sim.world.food/max(1, len(people))))
    # These are designed rules: scarcity nudges support for collective provision;
    # higher tax with secure food nudges towards markets. No election is implied.
    for c in people:
        if c.age < 18:
            continue
        c.political_economic = max(-1., min(1., c.political_economic - shortage*.006 + (0.001 if sim.policies["tax_rate"] > .1 and shortage == 0 else 0)))
        # School investment slowly broadens openness on the fictional social axis.
        c.political_social = max(-1., c.political_social - sim.policies["education"]*.0001)
    # At most one incident per day. Local RNG preserves the economy's random
    # stream, and the probability scales by population and observed scarcity.
    rng = random.Random(f"new-haven-crime:{sim.seed}:{day}")
    candidates = [c for c in people if c.age >= 18]
    if len(candidates) < 2 or rng.random() >= min(.65, len(candidates)*(.0004+.004*shortage)):
        return
    offender = rng.choices(candidates, weights=[.1 + (1-c.personality["agreeableness"]) + c.hunger/100 for c in candidates])[0]
    victims = [c for c in people if c.id != offender.id and c.wealth > 0]
    if not victims:
        return
    victim = rng.choice(victims)
    amount = min(victim.wealth, round(rng.uniform(.5, 4.), 2))
    if amount <= 0:
        return
    victim.wealth -= amount
    offender.wealth += amount
    victim.happiness = max(0, victim.happiness-2)
    victim.relationships[str(offender.id)] = max(-100, victim.relationships.get(str(offender.id), 0)-15)
    sim.crime_events.append({"day":day, "offender_id":offender.id, "victim_id":victim.id, "amount":amount})
    sim._event("crime", "Theft reported", f"{victim.name} lost £{amount:.2f} to theft; the money remains within the village.", victim)


def situation(sim):
    people = sim.living
    wealth = sorted(c.wealth for c in people)
    total = sum(wealth)
    n = len(wealth)
    gini = (sum((2*i-n-1)*v for i,v in enumerate(wealth,1))/(n*total)) if n and total else 0.
    alive = {c.id for c in people}
    pairs = {}
    for c in people:
        for key, score in c.relationships.items():
            other = int(key)
            if other in alive and other != c.id:
                pairs.setdefault(tuple(sorted((c.id,other))), []).append(score)
    scores = [mean(values) for values in pairs.values()]
    connected = {i for pair, values in pairs.items() if mean(values) >= 40 for i in pair}
    adults = [c for c in people if c.age >= 18]
    def groups(field, labels):
        return {label: sum((getattr(c,field)<-.25 if idx==0 else getattr(c,field)>.25 if idx==2 else -.25<=getattr(c,field)<=.25) for c in adults) for idx,label in enumerate(labels)}
    equality = []
    for gender in GENDERS:
        members = [c for c in people if c.gender == gender]
        grown = [c for c in members if c.age >= 18]
        equality.append({"gender":gender,"population":len(members),"adults":len(grown),"employment_rate":100*sum(c.job is not None for c in grown)/len(grown) if grown else None,"mean_wealth":mean(c.wealth for c in grown) if grown else None,"mean_daily_wage":mean(c.daily_wage for c in grown) if grown else None})
    observed = sum(r["population"] for r in sim.society_observations)
    eligible = [g for g in equality if g["adults"]]
    means = [g["mean_wealth"] for g in eligible]
    employment = [g["employment_rate"] for g in eligible]
    return {
        "wealth":{"total":total,"mean":mean(wealth) if n else 0,"median":median(wealth) if n else 0,"gini":gini,"top10_share":100*sum(wealth[-max(1,math.ceil(n*.1)):])/total if total else 0},
        "relationships":{"friendships":sum(s>=40 for s in scores),"rivalries":sum(s<=-20 for s in scores),"marriages":sum(c.partner_id is not None for c in people)//2,"isolated":sum(c.id not in connected and c.partner_id is None for c in people),"mean_trust":mean(scores) if scores else None},
        "politics":{"economic_mean":mean(c.political_economic for c in adults) if adults else None,"social_mean":mean(c.political_social for c in adults) if adults else None,"groups":{"economic":groups("political_economic",("collective","balanced","market")),"social":groups("political_social",("liberal","moderate","traditional"))},"adult_population":len(adults),"explanation":"Fictional adult preferences, not votes: -1 collective/liberal; +1 market/traditional. Scarcity encourages collective provision; secure food with higher tax nudges toward markets; education gradually shifts the social axis toward liberal."},
        "crime":{"incidents_30d":len(sim.crime_events),"rate_per_1000_citizen_days":1000*len(sim.crime_events)/observed if observed else None,"observation_days":len(sim.society_observations),"citizen_days":observed,"stolen_30d":sum(r["amount"] for r in sim.crime_events),"explanation":"Simulated theft only, at most one incident/day. Rate = incidents / observed living citizen-days × 1,000 (last 30 days). Scarcity and individual traits affect risk; gender does not."},
        "equality":{"groups":equality,"policy_equal_pay":True,"employment_gap":max(employment)-min(employment) if len(eligible)>1 else None,"wealth_ratio":min(means)/max(means) if len(means)>1 and max(means)>0 else None,"explanation":"Adult group comparisons; wages are actual gross pay on the latest day, including zero for non-workers. Employment gap is max minus min percentage points; wealth ratio is lowest/highest group mean. Gender is independently seeded and never affects pay or hiring. Small-group differences are descriptive, not evidence of discrimination."},
    }


def validate_society(sim):
    for c in sim.world.citizens:
        if c.gender not in GENDERS or any(type(v) not in (int,float) or not math.isfinite(v) or not -1<=v<=1 for v in (c.political_economic,c.political_social)) or type(c.daily_wage) not in (int,float) or not 0<=c.daily_wage<1e12:
            raise ValueError("Invalid citizen society state")
    records = sim.society_observations
    if not isinstance(records,list) or len(records)>30:
        raise ValueError("Invalid society observations")
    days=[]
    for r in records:
        if set(r)!={"day","population"} or type(r["day"]) is not int or not max(1,sim.world.day-29)<=r["day"]<=sim.world.day or type(r["population"]) is not int or not 0<=r["population"]<=2000:
            raise ValueError("Invalid society exposure")
        days.append(r["day"])
    if days and days != list(range(days[0],sim.world.day+1)):
        raise ValueError("Nonconsecutive society exposure")
    if not isinstance(sim.crime_events,list) or len(sim.crime_events)>30:
        raise ValueError("Invalid crime history")
    incident_days=[]
    for r in sim.crime_events:
        if set(r)!={"day","offender_id","victim_id","amount"} or type(r["day"]) is not int or r["day"] not in days or any(type(r[k]) is not int or not 0<=r[k]<len(sim.world.citizens) for k in ("offender_id","victim_id")) or r["offender_id"]==r["victim_id"] or type(r["amount"]) not in (int,float) or not 0<r["amount"]<=4:
            raise ValueError("Invalid crime incident")
        incident_days.append(r["day"])
    if len(set(incident_days))!=len(incident_days):
        raise ValueError("Duplicate crime day")

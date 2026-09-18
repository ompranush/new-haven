"""Deterministic daily simulation with explicit external trade and relief funding."""
import json
import math
import random
from dataclasses import asdict
from statistics import mean
from .models import Citizen, World
from .society import initialise_citizen, advance_society, situation, validate_society

NAMES = ["Maya", "Theo", "Iris", "Noah", "Ava", "Leo", "Sana", "Finn", "Nia", "Owen", "Arjun", "Ada"]
SURNAMES = ["Carter", "Singh", "Rivera", "Chen", "Okafor", "Reed", "Park", "Silva"]
TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
GOALS = ["save for a home", "make a close friend", "master a craft", "start a family", "help the town"]
JOBS = {"Farmer": 2., "Baker": 2.2, "Builder": 2.4, "Teacher": 2.3, "Medic": 2.5, "Merchant": 2.2, "Miner": 2.5, "Forester": 2.1}
SITES = [("Sunfield Farm", "farm", "Farmer", 5, 14), ("Hearth Bakery", "bakery", "Baker", 11, 10), ("Stone & Timber", "workshop", "Builder", 15, 13), ("New Haven School", "school", "Teacher", 9, 6), ("River Clinic", "clinic", "Medic", 14, 6), ("Market Exchange", "market", "Merchant", 12, 9), ("Copper Ridge", "mine", "Miner", 20, 4), ("Greenwood", "forest", "Forester", 4, 4)]

def clamp(v, low=0, high=100):
    return max(low, min(high, v))

class Simulation:
    VERSION = 1

    def __init__(self, seed=7, population=100):
        if type(seed) is not int or type(population) is not int or not 2 <= population <= 1000:
            raise ValueError("Use an integer seed and population between 2 and 1000")
        self.seed, self.rng = seed, random.Random(seed)
        self.policies = {"tax_rate": 0.08, "education": 0, "automation": 0, "price_cap": False}
        self.pending_decisions, self.decision_log = [], []
        self.event_counter = 0
        self.active_effects = []
        self.resources = {"wood": population*1.5, "stone": population*1.0}
        self.cooldowns = {}
        self.ledger = {}
        self.crime_events = []
        self.society_observations = []
        self.businesses = [{"id": i, "name": name, "kind": kind, "job": job, "x": x, "y": y, "workers": [], "cash": population*8., "profit": 0., "capacity": max(1, math.ceil(population*(0.27 if i == 0 else 0.115)))} for i, (name, kind, job, x, y) in enumerate(SITES)]
        self.buildings = [{k: b[k] for k in ("id", "name", "kind", "x", "y")} for b in self.businesses]
        self.buildings += [{"id": 8, "name": "Council Hall", "kind": "council", "x": 12, "y": 5}]
        self.buildings += [{"id": 9+i, "name": f"House {i+1}", "kind": "home", "x": x, "y": y} for i, (x,y) in enumerate([(7,8),(7,11),(9,14),(13,16),(16,10),(17,7),(10,17),(15,17)])]
        for building in self.buildings:
            building.update(condition=100., level=1, construction=False)
        self.terrain = [{"x": x, "y": y, "kind": "road" if y == 9 or x == 12 else "water" if x == 19 else "farm" if 2 <= x <= 7 and 12 <= y <= 17 else "forest" if x < 6 and y < 7 else "grass"} for y in range(20) for x in range(24)]
        people = []
        for i in range(population):
            home = self.buildings[9+i%8]
            c = Citizen(i, f"{self.rng.choice(NAMES)} {self.rng.choice(SURNAMES)} {i+1}", self.rng.randint(18,62), None, self.rng.uniform(35,140), self.rng.uniform(55,80), {t: round(self.rng.random(),3) for t in TRAITS}, self.rng.choice(GOALS), x=home["x"], y=home["y"])
            c.remember("Arrived in New Haven, ready to begin again.")
            initialise_citizen(c, self.seed)
            people.append(c)
        self.world = World(0, population*4., people, treasury=population*6.)
        self.ledger = {"food_opening":self.world.food,"food_produced":0.,"food_consumed":0.,"food_lost":0.,"food_imported":0.,"food_closing":self.world.food,"money_opening":self._money(),"trade_income":0.,"maintenance_cost":0.,"repair_cost":0.,"relief_cost":0.,"local_spending":0.,"money_closing":self._money()}
        for i,c in enumerate(people):
            if i < math.ceil(population*0.25):
                self._hire(c,self.businesses[0])
            elif self.rng.random() > 0.1:
                options = [b for b in self.businesses[1:] if len(b["workers"]) < b["capacity"]]
                if options:
                    self._hire(c,self.rng.choice(options))
        self._event("founding", "A new beginning", f"{population} citizens founded New Haven.")
        self._record()

    @property
    def living(self):
        return [c for c in self.world.citizens if c.alive]

    @property
    def season(self):
        return ["Spring","Summer","Autumn","Winter"][(self.world.day//90)%4]

    def _hire(self,c,b):
        if c.age < 18 or c.job is not None or len(b["workers"]) >= b["capacity"]:
            return False
        c.job = b["job"]
        b["workers"].append(c.id)
        return True

    def _event(self,kind,title,text,citizen=None):
        self.event_counter += 1
        self.world.events.append({"id":self.event_counter,"day":self.world.day,"kind":kind,"title":title,"text":text})
        del self.world.events[:-200]
        if citizen is not None:
            citizen.remember(text,self.world.day)
            self.pending_decisions.append({"id":self.event_counter,"citizen_id":citizen.id,"event":text,"day":self.world.day})
            del self.pending_decisions[:-20]

    def step(self,days=1):
        if type(days) is not int or not 1 <= days <= 365:
            raise ValueError("days must be an integer from 1 to 365")
        for _ in range(days):
            self._day()

    def _day(self):
        w = self.world
        self.ledger = {"food_opening":w.food,"food_produced":0.,"food_consumed":0.,"food_lost":0.,"food_imported":0.,"money_opening":self._money(),"trade_income":0.,"maintenance_cost":0.,"repair_cost":0.,"relief_cost":0.,"local_spending":0.}
        w.day += 1
        w.weather = self.rng.choices(["Clear","Rain","Wind","Storm"],[60,25,13,2])[0]
        # Most bad weather hurts today's harvest; only severe storms breach the river.
        if w.weather == "Storm" and self.rng.random()<0.5:
            self._storm()
        people = self.living
        flood = max((e["severity"] for e in self.active_effects if e["kind"] == "flood"),default=0.)
        self._repair_buildings()
        for b in self.businesses:
            b["profit"] = 0.
            b["workers"] = [i for i in b["workers"] if self.world.citizens[i].alive]
            # Export orders are finite, seasonal and disrupted by flooded roads.
            demand = (0.92+0.14*math.sin(w.day/19+b["id"]))*(1-flood*0.6)
            b["demand"] = round(clamp(demand,0.15,1.2),3)
            b["orders_remaining"] = len(people)*2.1/7*b["demand"]
        for c in people:
            if c.age >= 18 and c.job is None and self.rng.random() < 0.12:
                options = [b for b in self.businesses if len(b["workers"]) < b["capacity"] and b["cash"] > 5]
                if options:
                    self._hire(c,min(options,key=lambda b:len(b["workers"])/b["capacity"]))
                    self._event("work","A fresh start",f"{c.name} found work as a {c.job}.",c)
        for c in people:
            c.daily_wage = 0.
            c.age += 1/365
            home = self.buildings[9+c.id%8]
            target = (home["x"],home["y"])
            if c.age < 18:
                c.activity = "learning at school"
                c.energy = clamp(c.energy+12)
                target = (9,6)
            elif c.energy < 28 or c.health < 35:
                c.activity = "resting at home"
                c.energy = clamp(c.energy+48)
                c.health = clamp(c.health+4)
            elif w.food<len(people) and c.job!="Farmer" and c.personality["agreeableness"]>0.65:
                c.activity = "foraging instead of paid work during the shortage"
                target = (4,4)
                c.energy = clamp(c.energy-8)
                w.food += 1.2
                self.ledger["food_produced"] += 1.2
                if w.day%7==c.id%7:
                    c.remember("Gave up a day's wages to gather food for hungry neighbours.",w.day)
                    self._rule_decision(c,"forage","Food reserves fell below one day; helping neighbours outweighed today's wages.","Gathered 1.2 meals instead of collecting wages.")
            elif c.job:
                b = next(b for b in self.businesses if b["job"] == c.job)
                condition = self.buildings[b["id"]]["condition"]/100
                wage = JOBS[c.job]*(1+0.02*self.policies["education"])
                if b["kind"] != "farm":
                    revenue = min(b["orders_remaining"],wage*(1.12+c.personality["conscientiousness"]*0.12)*condition)
                    b["orders_remaining"] -= revenue
                    b["cash"] += revenue
                    b["profit"] += revenue
                    self.ledger["trade_income"] += revenue
                    upkeep = min(b["cash"],wage*0.13)
                    b["cash"] -= upkeep
                    b["profit"] -= upkeep
                    self.ledger["maintenance_cost"] += upkeep
                paid = min(wage,b["cash"])
                c.daily_wage = paid
                b["cash"] -= paid
                b["profit"] -= paid
                c.wealth += paid*(1-self.policies["tax_rate"])
                w.treasury += paid*self.policies["tax_rate"]
                if paid < wage:
                    c.happiness = clamp(c.happiness-1.5)
                    if w.day % 7 == 0:
                        self._event("work","Unpaid wages",f"{c.name} could not collect their full wage from {b['name']}.",c)
                c.energy = clamp(c.energy-11)
                c.activity = f"working as a {c.job.lower()}"
                target = (b["x"],b["y"])
                if c.job == "Farmer":
                    factor = {"Clear":1,"Rain":1.12,"Wind":0.9,"Storm":0.5}[w.weather]
                    produced = 5.9*factor*(0.9 if self.season == "Winter" else 1)*(1+0.1*math.sqrt(self.policies["automation"]))*max(0.25,condition)*(1-flood*0.55)
                    w.food += produced
                    self.ledger["food_produced"] += produced
                    if flood:
                        c.activity = "salvaging the flooded harvest"
                elif c.job in ("Forester","Miner"):
                    resource = "wood" if c.job == "Forester" else "stone"
                    self.resources[resource] = min(len(people)*5,self.resources[resource]+0.5*condition)
                elif c.job == "Builder" and any(x["construction"] for x in self.buildings):
                    damaged = min(self.buildings,key=lambda x:x["condition"])
                    target = (damaged["x"],damaged["y"])
                    c.activity = f"rebuilding {damaged['name']}"
                    if w.day%7==c.id%7:
                        c.remember(f"Worked on the recovery of {damaged['name']} after the flood.",w.day)
                        self._rule_decision(c,"repair",f"{damaged['name']} is damaged and the town funded recovery.","Joined the construction crew; repairs consume council money, timber and stone.")
            else:
                c.activity = "looking for work in the square"
                c.energy = clamp(c.energy+12)
                target = (12,9)
                if w.food < len(people)*2:
                    c.activity = "foraging to feed the town"
                    target = (4,4)
                    w.food += 0.7
                    self.ledger["food_produced"] += 0.7
                    if w.day%7 == c.id%7:
                        c.remember("Chose to forage because town food reserves were low.",w.day)
                        self._rule_decision(c,"forage","No paid work and food reserves below two days.","Gathered 0.7 meals for the town.")
            self._move(c,target)
        # Spoilage and finite granaries prevent limitless free stockpiles.
        lost = max(0,w.food-max(20,len(people)*10))+min(w.food,max(0,w.food-len(people)*3))*0.007
        lost = min(w.food,lost)
        w.food -= lost
        self.ledger["food_lost"] += lost
        w.food_price = round(clamp(1.25-w.food/max(1,len(people))*0.07,0.55,2.5),2)
        if self.policies["price_cap"]:
            w.food_price = min(w.food_price,0.8)
        meals = people[:]
        self.rng.shuffle(meals)
        for c in meals:
            c.hunger = clamp(c.hunger+18)
            quantity = 0.6 if c.age < 18 else 1.
            cost,payer = w.food_price*quantity,c
            if c.age < 18:
                parents = [self.world.citizens[i] for i in c.parent_ids if self.world.citizens[i].alive]
                if parents:
                    payer = max(parents,key=lambda p:p.wealth)
            if w.food >= quantity and (payer.wealth >= cost or w.treasury >= cost):
                if payer.wealth >= cost:
                    payer.wealth -= cost
                else:
                    w.treasury -= cost
                w.food -= quantity
                self.ledger["food_consumed"] += quantity
                self.businesses[0]["cash"] += cost
                self.businesses[0]["profit"] += cost
                c.hunger = clamp(c.hunger-30)
            c.health = clamp(c.health+(0.25 if c.hunger < 45 else -1.5-c.hunger/100))
            # Local purchases circulate existing citizen money instead of minting sales.
            if c.hunger<35 and c.wealth>30:
                spending=min(0.4,c.wealth-30)
                shop=self.businesses[1+(c.id+w.day)%7]
                c.wealth-=spending
                shop["cash"]+=spending
                shop["profit"]+=spending
                self.ledger["local_spending"]+=spending
            c.happiness = clamp(c.happiness+(65-c.happiness)*0.015+(0.2 if c.hunger < 35 else -1.8)+self.rng.uniform(-0.4,0.4))
            c.goal_progress = self._goal_progress(c)
        self._socialise()
        self._life_events()
        advance_society(self)
        if w.day%30 == 0 and self.living:
            c = min(self.living,key=lambda c:c.happiness)
            self._event("politics","Citizens petition the council",f"{c.name} asked for {'food security' if w.food < len(people) else 'better schools and fair wages'}.",c)
        if w.food < len(self.living) and w.day%7 == 0 and self.living:
            self._event("shortage","Food is running low","Residents are debating how to protect the next harvest.",self.rng.choice(self.living))
        self.pending_decisions = [d for d in self.pending_decisions if w.day-d["day"] <= 30 and self.world.citizens[d["citizen_id"]].alive]
        for effect in self.active_effects:
            effect["days_remaining"] -= 1
            effect["severity"] *= 0.95
            if effect["days_remaining"] == 0:
                self._event("recovery","The floodwaters recede","Roads are open again; damaged buildings still need funded repairs.")
        self.active_effects = [e for e in self.active_effects if e["days_remaining"]>0]
        self.ledger.update(food_closing=w.food,money_closing=self._money())
        self._record()

    def _money(self):
        return self.world.treasury+sum(c.wealth for c in self.world.citizens)+sum(b["cash"] for b in self.businesses)

    def _rule_decision(self,c,action,reason,effect):
        recent=[d for d in self.decision_log if d.get("source")=="rules"]
        if sum(d["day"]==self.world.day for d in recent)>=3 or any(d["citizen_id"]==c.id and d["action"]==action and self.world.day-d["day"]<14 for d in recent):
            return
        self.event_counter += 1
        self.decision_log.append({"id":self.event_counter,"citizen_id":c.id,"day":self.world.day,"event":"Adaptive response to local conditions","action":action,"reason":reason,"source":"rules","effect":effect})
        del self.decision_log[:-100]

    def _repair_buildings(self):
        builders = sum(c.job == "Builder" and c.energy>=28 for c in self.living)
        budget = builders*0.8
        for b in sorted(self.buildings,key=lambda b:b["condition"]):
            b["construction"] = False
            if b["condition"]>=100 or budget<=0:
                continue
            points = min(100-b["condition"],budget,self.world.treasury/2,self.resources["wood"]/0.5,self.resources["stone"]/0.3)
            if points<=0:
                continue
            self.world.treasury -= points*2
            self.resources["wood"] -= points*0.5
            self.resources["stone"] -= points*0.3
            self.ledger["repair_cost"] += points*2
            b["condition"] += points
            b["construction"] = True
            budget -= points
            if b["condition"]>=100:
                self._event("recovery","Rebuilding complete",f"{b['name']} reopened at full capacity after publicly funded repairs.")

    def _goal_progress(self,c):
        values = {"save for a home":c.wealth/5,"make a close friend":max(c.relationships.values(),default=0),"master a craft":self.world.day/3 if c.job else 0,"start a family":100 if c.partner_id is not None else max(c.relationships.values(),default=0)/2,"help the town":self.world.day/2+self.policies["education"]*5}
        return round(clamp(values[c.goal]),1)

    def _move(self,c,target):
        if (c.x < 19 <= target[0]) or (target[0] < 19 <= c.x):
            if c.y != 9:
                c.y += (9>c.y)-(9<c.y)
                return
        c.x += (target[0]>c.x)-(target[0]<c.x)
        if c.x != 19:
            c.y += (target[1]>c.y)-(target[1]<c.y)

    def _socialise(self):
        people = self.living
        if len(people)<2:
            return
        for c in people:
            if self.rng.random() > 0.2+c.personality["extraversion"]*0.4:
                continue
            known = [self.world.citizens[int(i)] for i in c.relationships if self.world.citizens[int(i)].alive and int(i)!=c.id]
            other = self.rng.choice(known) if known and self.rng.random()<0.7 else self.rng.choice(people)
            if other.id == c.id:
                continue
            harmony = (c.personality["agreeableness"]+other.personality["agreeableness"])/2
            change = self.rng.uniform(1,5) if self.rng.random()<0.62+harmony*0.25 else -self.rng.uniform(2,6)
            key,reverse = str(other.id),str(c.id)
            before = c.relationships.get(key,0)
            c.relationships[key] = clamp(before+change,-100,100)
            other.relationships[reverse] = clamp(other.relationships.get(reverse,0)+change*(0.6+other.personality["agreeableness"]),-100,100)
            if before<50<=c.relationships[key]:
                self._event("friendship","A friendship blossoms",f"{c.name} and {other.name} became close friends.",c)
                other.remember(f"Became close friends with {c.name}.",self.world.day)
            if before>-30>=c.relationships[key]:
                self._event("conflict","A growing rivalry",f"{c.name} fell out with {other.name} over town priorities.",c)
            related = other.id in c.parent_ids or c.id in other.parent_ids or bool(set(c.parent_ids)&set(other.parent_ids))
            if c.relationships[key]>=70 and other.relationships[reverse]>=60 and c.partner_id is None and other.partner_id is None and min(c.age,other.age)>=18 and not related:
                c.partner_id,other.partner_id = other.id,c.id
                self._event("marriage","Wedding bells",f"{c.name} married {other.name}.",c)
                other.remember(f"Married {c.name}.",self.world.day)

    def _life_events(self):
        for c in list(self.living):
            if c.health<=0 or self.rng.random()<0.000005+max(0,c.age-70)*0.000015:
                c.alive = False
                c.activity = "deceased"
                for b in self.businesses:
                    if c.id in b["workers"]:
                        b["workers"].remove(c.id)
                partner = self.world.citizens[c.partner_id] if c.partner_id is not None else None
                if partner is not None and partner.alive:
                    partner.partner_id = None
                    partner.happiness = clamp(partner.happiness-20)
                    self._event("bereavement","A household in mourning",f"{partner.name} lost their partner {c.name}.",partner)
                c.partner_id = None
                self._event("death","Remembering a citizen",f"{c.name} died at age {int(c.age)}.")
        if len(self.world.citizens)>=2000:
            return
        for c in list(self.living):
            if len(self.world.citizens)>=2000:
                break
            if c.partner_id is None or c.id>c.partner_id or not 22<=c.age<=42 or c.hunger>30:
                continue
            partner = self.world.citizens[c.partner_id]
            if not partner.alive or not 22<=partner.age<=50 or self.rng.random()>=0.0005:
                continue
            baby = Citizen(len(self.world.citizens),f"{self.rng.choice(NAMES)} {c.name.split()[1]} {len(self.world.citizens)+1}",0,None,0,75,{t:round(self.rng.random(),3) for t in TRAITS},self.rng.choice(GOALS),x=c.x,y=c.y,parent_ids=[c.id,partner.id])
            initialise_citizen(baby, self.seed)
            baby.remember(f"Born into the household of {c.name} and {partner.name}.",self.world.day)
            self.world.citizens.append(baby)
            self._event("birth","A new life",f"{c.name} and {partner.name} welcomed {baby.name}.",c)
            partner.remember(f"Welcomed {baby.name} into the family.",self.world.day)

    def _storm(self):
        if any(e["kind"]=="flood" for e in self.active_effects):
            return
        loss = self.world.food*0.28
        self.world.food -= loss
        self.ledger["food_lost"] = self.ledger.get("food_lost",0)+loss
        self.active_effects.append({"kind":"flood","label":"Flooded roads and fields","days_remaining":14,"severity":0.85})
        for b in self.buildings:
            damage = 36 if b["kind"]=="farm" else 24 if b["x"]>=14 else 12
            b["condition"] = max(15,b["condition"]-damage)
        expense = min(self.world.treasury,len(self.living)*1.2)
        self.world.treasury -= expense
        self.ledger["repair_cost"] = self.ledger.get("repair_cost",0)+expense
        self.world.weather = "Storm"
        if self.living:
            c = self.rng.choice(self.living)
            c.happiness = clamp(c.happiness-8)
            self._event("disaster","The river breaks its banks",f"Flooding destroyed {loss:.0f} meals. Emergency response cost {expense:.0f} coins; fields, buildings and trade roads face two weeks of disruption.",c)

    def intervention_options(self):
        costs = {"festival":40,"storm":0,"aid":max(10,len(self.living)*0.3),"education":80*(1+self.policies["education"]),"tax":0,"automation":120*(1+self.policies["automation"]),"market":0}
        labels = {"festival":"Lantern festival","storm":"Introduce flood","aid":"Emergency food convoy","education":"Fund education","tax":"Change income tax","automation":"Upgrade farm tools","market":"Toggle food price cap"}
        result=[]
        for action,cost in costs.items():
            remaining=max(0,self.cooldowns.get(action,0)-self.world.day)
            reason = f"Available in {remaining} days" if remaining else ""
            if action=="storm" and self.active_effects:
                reason="A flood is already active"
            elif action=="aid" and self.world.food>=len(self.living)*2 and not self.active_effects:
                reason="Relief requires a food shortage or active disaster"
            elif action in ("education","automation") and self.policies[action]>=5:
                reason="Maximum investment level reached"
            if self.world.treasury<cost:
                reason=f"Requires {cost:g} council coins"
            result.append({"id":action,"label":labels[action],"cost":cost,"cooldown_remaining":remaining,"available":not reason,"description":reason or "Ready"})
        return result

    def intervene(self,action):
        option = next((o for o in self.intervention_options() if o["id"]==action),None)
        if option is None:
            raise ValueError("Unknown intervention")
        if not option["available"]:
            raise ValueError(option["description"])
        self.world.treasury -= option["cost"]
        cooldown = {"festival":30,"aid":30,"education":30,"automation":30,"storm":14,"tax":7,"market":7}[action]
        self.cooldowns[action] = self.world.day+cooldown
        self.ledger["relief_cost" if action=="aid" else "maintenance_cost"] = self.ledger.get("relief_cost" if action=="aid" else "maintenance_cost",0)+option["cost"]
        messages = {"festival":"The council funded a lantern festival; another can be held in 30 days.","storm":"A severe storm was introduced into the world.","aid":"A relief convoy delivered two days of food, with council-paid transport. No money was granted; another convoy needs 30 days.","education":"The council invested in skills and education.","tax":"The council changed the income tax rate.","automation":"The council upgraded farm tools to improve harvests.","market":"The council toggled the food price cap."}
        if action=="festival":
            for c in self.living:
                c.happiness = clamp(c.happiness+max(1,(100-c.happiness)*0.12))
                c.remember("Celebrated the lantern festival.",self.world.day)
        elif action=="storm":
            self._storm()
        elif action=="aid":
            imported = len(self.living)*2
            self.world.food += imported
            self.ledger["food_imported"] = self.ledger.get("food_imported",0)+imported
        elif action in ("education","automation"):
            self.policies[action] = min(10,self.policies[action]+1)
            self.buildings[3 if action=="education" else 0]["level"] = 1+self.policies[action]
        elif action=="tax":
            self.policies["tax_rate"] = 0.15 if self.policies["tax_rate"]==0.08 else 0.08
        else:
            self.policies["price_cap"] = not self.policies["price_cap"]
        self._event("council","Council decision",messages[action])
        self.ledger.update(food_closing=self.world.food,money_closing=self._money())
        self._record(replace=True)

    def apply_decision(self,decision_id,action,reason):
        if action not in {"seek_work","help_neighbor","rest","organize"} or not isinstance(reason,str) or len(reason)>500:
            raise ValueError("Invalid decision action or reason")
        item = next((d for d in self.pending_decisions if d["id"]==decision_id),None)
        if item is None:
            raise ValueError("Decision is missing or already processed")
        c = self.world.citizens[item["citizen_id"]]
        if not c.alive:
            raise ValueError("Citizen is no longer alive")
        if action=="seek_work":
            effect="No job change: already employed or no suitable vacancy."
            for b in self.businesses:
                if self._hire(c,b):
                    effect=f"Hired as a {c.job} at {b['name']}."
                    break
        elif action=="rest":
            before=c.energy
            c.energy = clamp(c.energy+15)
            effect=f"Recovered {c.energy-before:g} energy points."
        elif action=="help_neighbor":
            effect="No living neighbour was available to help."
            neighbors = [p for p in self.living if p.id!=c.id]
            if neighbors:
                other = min(neighbors,key=lambda p:p.wealth)
                gift = min(5,c.wealth)
                c.wealth -= gift
                other.wealth += gift
                other.relationships[str(c.id)] = clamp(other.relationships.get(str(c.id),0)+5,-100,100)
                effect=f"Transferred {gift:g} existing coins to {other.name} and improved their regard."
        else:
            before=c.happiness
            c.happiness = clamp(c.happiness+3)
            effect=f"Gained {c.happiness-before:g} happiness points; no council policy was enacted."
        c.remember(f"Chose to {action.replace('_',' ')}: {reason}",self.world.day)
        self.pending_decisions.remove(item)
        self.decision_log.append({**item,"day":self.world.day,"trigger_day":item["day"],"action":action,"reason":reason,"source":"ai","effect":effect})
        del self.decision_log[:-100]
        self._record(replace=True)

    def summary(self):
        people = self.living
        adults = [c for c in people if c.age>=18]
        return {"day":self.world.day,"population":len(people),"wealth":round(sum(c.wealth for c in people),2),"happiness":round(mean(c.happiness for c in people),1) if people else 0,"food":round(self.world.food,2),"food_price":self.world.food_price,"treasury":round(self.world.treasury,2),"weather":self.world.weather,"season":self.season,"unemployment":round(100*sum(c.job is None for c in adults)/len(adults),1) if adults else 0,"health":round(mean(c.health for c in people),1) if people else 0,"relationships":sum(len(c.relationships) for c in people),"marriages":sum(c.partner_id is not None for c in people)//2}

    def _record(self,replace=False):
        if replace and self.world.history and self.world.history[-1]["day"]==self.world.day:
            self.world.history[-1] = self.summary()
        else:
            self.world.history.append(self.summary())
        del self.world.history[:-2000]

    def snapshot(self):
        return json.loads(json.dumps({**self.summary(),"situation":situation(self),"seed":self.seed,"width":24,"height":20,"citizens":[asdict(c) for c in self.world.citizens],"businesses":self.businesses,"buildings":self.buildings,"terrain":self.terrain,"events":self.world.events,"history":self.world.history,"policies":self.policies,"pending_decisions":self.pending_decisions,"cognition_events":self.pending_decisions,"decision_log":self.decision_log,"active_effects":self.active_effects,"resources":self.resources,"ledger":self.ledger,"cooldowns":self.cooldowns,"interventions":self.intervention_options()}))

    def save(self):
        return json.dumps({"version":self.VERSION,"seed":self.seed,"rng":self.rng.getstate(),"world":asdict(self.world),"crime_events":self.crime_events,"society_observations":self.society_observations,"businesses":self.businesses,"buildings":self.buildings,"active_effects":self.active_effects,"resources":self.resources,"ledger":self.ledger,"cooldowns":self.cooldowns,"policies":self.policies,"pending_decisions":self.pending_decisions,"decision_log":self.decision_log,"event_counter":self.event_counter},allow_nan=False)

    @classmethod
    def load(cls,text):
        try:
            if not isinstance(text,str) or len(text)>15_000_000:
                raise ValueError("Save is too large")
            data = json.loads(text,parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite number")))
            def finite(value):
                if isinstance(value,float) and not math.isfinite(value):
                    raise ValueError("Non-finite number")
                if isinstance(value,dict):
                    for child in value.values():
                        finite(child)
                elif isinstance(value,list):
                    for child in value:
                        finite(child)
            finite(data)
            if data["version"]!=cls.VERSION:
                raise ValueError("Unsupported save version")
            w = data["world"]
            if not 2<=len(w["citizens"])<=2000 or type(w["day"]) is not int or w["day"]<0:
                raise ValueError("Invalid world")
            sim = cls(data["seed"],2)
            citizens = [Citizen(**record) for record in w["citizens"]]
            for c, record in zip(citizens, w["citizens"]):
                fields = {"gender","political_economic","political_social","daily_wage"}
                if not fields.intersection(record):
                    initialise_citizen(c, sim.seed)
                elif not fields.issubset(record):
                    raise ValueError("Incomplete citizen society state")
            for i,c in enumerate(citizens):
                if c.id!=i or not isinstance(c.alive,bool) or c.job not in {None,*JOBS} or c.goal not in GOALS or not isinstance(c.name,str) or len(c.name)>200:
                    raise ValueError("Invalid citizen")
                if not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=100 for v in (c.happiness,c.health,c.energy,c.hunger,c.goal_progress)) or not 0<=c.wealth<1e12 or not 0<=c.age<=10000:
                    raise ValueError("Invalid needs")
                if type(c.x) is not int or type(c.y) is not int or not 0<=c.x<24 or not 0<=c.y<20:
                    raise ValueError("Invalid location")
                if set(c.personality)!=set(TRAITS) or not all(0<=v<=1 for v in c.personality.values()):
                    raise ValueError("Invalid personality")
                if len(c.memories)>30 or not all(isinstance(m["text"],str) and type(m["day"]) is int for m in c.memories):
                    raise ValueError("Invalid memories")
                if any(not str(k).isdigit() or not 0<=int(k)<len(citizens) or not -100<=v<=100 for k,v in c.relationships.items()):
                    raise ValueError("Invalid relationship")
                if any(type(p) is not int or not 0<=p<len(citizens) or p==i for p in c.parent_ids):
                    raise ValueError("Invalid parent")
                if c.partner_id is not None:
                    if type(c.partner_id) is not int or not 0<=c.partner_id<len(citizens) or c.partner_id==i or not c.alive or c.age<18:
                        raise ValueError("Invalid partnership")
                    p = citizens[c.partner_id]
                    if not p.alive or p.partner_id!=i or p.age<18:
                        raise ValueError("Nonreciprocal partnership")
            if not all(isinstance(w[k],(int,float)) and math.isfinite(w[k]) and 0<=w[k]<1e12 for k in ("food","treasury","food_price")) or (w["width"],w["height"])!=(24,20):
                raise ValueError("Invalid resources")
            businesses = data["businesses"]
            if len(businesses)!=8:
                raise ValueError("Invalid businesses")
            workers = []
            for b,expected in zip(businesses,sim.businesses):
                if any(b[k]!=expected[k] for k in ("id","name","kind","job","x","y")) or not 0<=b["cash"]<1e12 or not math.isfinite(b["profit"]) or type(b["capacity"]) is not int or not 1<=b["capacity"]<=2000:
                    raise ValueError("Invalid business")
                for i in b["workers"]:
                    if type(i) is not int or not 0<=i<len(citizens) or not citizens[i].alive or citizens[i].job!=b["job"] or citizens[i].age<18:
                        raise ValueError("Invalid worker")
                    workers.append(i)
            if len(workers)!=len(set(workers)) or set(workers)!={c.id for c in citizens if c.alive and c.job is not None}:
                raise ValueError("Inconsistent employment")
            p = data["policies"]
            if set(p)!=set(sim.policies) or p["tax_rate"] not in (0.08,0.15) or type(p["price_cap"]) is not bool or any(type(p[k]) is not int or not 0<=p[k]<=10 for k in ("education","automation")):
                raise ValueError("Invalid policies")
            if len(data["pending_decisions"])>20 or len(data["decision_log"])>100 or len(w["history"])>2000 or len(w["events"])>200:
                raise ValueError("Invalid history length")
            for d in data["pending_decisions"]:
                if type(d["citizen_id"]) is not int or not 0<=d["citizen_id"]<len(citizens) or not citizens[d["citizen_id"]].alive or type(d["id"]) is not int or not isinstance(d["event"],str) or type(d["day"]) is not int or not 0<=d["day"]<=w["day"]:
                    raise ValueError("Invalid decision")
            for d in data["decision_log"]:
                source=d.get("source","ai")
                allowed={"forage","repair"} if source=="rules" else {"seek_work","help_neighbor","rest","organize"}
                if source not in {"rules","ai"} or type(d["id"]) is not int or type(d["citizen_id"]) is not int or not 0<=d["citizen_id"]<len(citizens) or type(d["day"]) is not int or not 0<=d["day"]<=w["day"] or d["action"] not in allowed or not isinstance(d["reason"],str) or len(d["reason"])>500 or not isinstance(d.get("effect",""),str) or len(d.get("effect",""))>500:
                    raise ValueError("Invalid decision log")
                if "trigger_day" in d and (type(d["trigger_day"]) is not int or not 0<=d["trigger_day"]<=d["day"]):
                    raise ValueError("Invalid decision trigger day")
            if len({d["id"] for d in data["pending_decisions"]}) != len(data["pending_decisions"]):
                raise ValueError("Duplicate decision")
            for event in w["events"]:
                if type(event["id"]) is not int or type(event["day"]) is not int or not 0 <= event["day"] <= w["day"] or not all(isinstance(event[k],str) and len(event[k]) <= 2000 for k in ("kind","title","text")):
                    raise ValueError("Invalid event")
            for record in w["history"]:
                if type(record["day"]) is not int or not 0 <= record["day"] <= w["day"] or not all(isinstance(record[k],(int,float)) for k in ("population","wealth","happiness","food","treasury","unemployment")):
                    raise ValueError("Invalid history")
            def tuples(value):
                return tuple(tuples(v) for v in value) if isinstance(value,list) else value
            sim.rng.setstate(tuples(data["rng"]))
            sim.world = World(**{**w,"citizens":citizens})
            sim.crime_events = data.get("crime_events", [])
            sim.society_observations = data.get("society_observations", [])
            validate_society(sim)
            sim.businesses,sim.policies = businesses,p
            # Version-one saves predate physical damage; migrate them as intact worlds.
            buildings = data.get("buildings",sim.buildings)
            if len(buildings)!=len(sim.buildings):
                raise ValueError("Invalid buildings")
            for b,expected in zip(buildings,sim.buildings):
                if any(b[k]!=expected[k] for k in ("id","name","kind","x","y")) or not isinstance(b["condition"],(int,float)) or not 0<=b["condition"]<=100 or type(b["level"]) is not int or not 1<=b["level"]<=6 or type(b["construction"]) is not bool:
                    raise ValueError("Invalid building condition")
            resources=data.get("resources",{"wood":len(citizens)*1.5,"stone":len(citizens)})
            if set(resources)!={"wood","stone"} or any(not isinstance(v,(int,float)) or not 0<=v<1e12 for v in resources.values()):
                raise ValueError("Invalid materials")
            effects=data.get("active_effects",[])
            if len(effects)>1 or any(e["kind"]!="flood" or not isinstance(e["label"],str) or type(e["days_remaining"]) is not int or not 1<=e["days_remaining"]<=14 or not isinstance(e["severity"],(int,float)) or not 0<=e["severity"]<=1 for e in effects):
                raise ValueError("Invalid active effects")
            cooldowns=data.get("cooldowns",{})
            if any(k not in {"festival","storm","aid","education","tax","automation","market"} or type(v) is not int or not 0<=v<=w["day"]+30 for k,v in cooldowns.items()):
                raise ValueError("Invalid intervention cooldown")
            ledger=data.get("ledger",{})
            if not isinstance(ledger,dict) or any(not isinstance(v,(int,float)) or not 0<=v<1e15 for v in ledger.values()):
                raise ValueError("Invalid ledger")
            sim.buildings,sim.resources,sim.active_effects,sim.cooldowns,sim.ledger=buildings,resources,effects,cooldowns,ledger
            sim.pending_decisions,sim.decision_log = data["pending_decisions"],data["decision_log"]
            sim.event_counter = data["event_counter"]
            if type(sim.event_counter) is not int or sim.event_counter<0:
                raise ValueError("Invalid event counter")
            if any(e["id"] > sim.event_counter or e["id"] < 1 for e in sim.world.events + sim.pending_decisions + sim.decision_log):
                raise ValueError("Invalid event identity")
            return sim
        except (KeyError,TypeError,IndexError,OverflowError,AttributeError,RecursionError) as exc:
            raise ValueError("Malformed New Haven save") from exc

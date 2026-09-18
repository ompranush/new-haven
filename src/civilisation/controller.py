"""Session actions: credentials never enter simulation snapshots or model context."""
import re
from uuid import uuid4

from .sim import Simulation
from .cognition import reflect
from .experiments import compare
from .godmode import interpret_command, dry_run, apply_plan, plan_fingerprint


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be a whole number from {low} to {high}.")
    return value


def clear_plan(state):
    state["god_pending"] = None


def public_ai(state):
    budget = state["budget"]
    return {"enabled": bool(state.get("ai_enabled") and state.get("api_key")),
            "configured": bool(state.get("api_key")), "model": state.get("ai_model", "gpt-4.1-mini"),
            "calls": budget.calls, "max_calls": budget.max_calls, "tokens": budget.tokens,
            "settings_notice": state.get("settings_notice", ""),
            "status": "Only explicit AI requests use paid calls. Play remains rules-only."}


def require_ai(state):
    if not state.get("ai_enabled") or not state.get("api_key"):
        raise ValueError("Open Settings, add your API key and enable explicitly requested AI calls first.")


def handle_action(state, message):
    sim, action = state["sim"], message.get("action")
    if action == "configure_ai":
        model, key, enabled = message.get("model"), message.get("api_key", ""), message.get("enabled")
        maximum = integer(message.get("max_calls"), 1, 50, "Call limit")
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9._:\-]{1,120}", model):
            raise ValueError("Enter a valid model ID (letters, numbers, dots, dashes or colons).")
        if not isinstance(key, str) or len(key) > 500 or (key.strip() and not re.fullmatch(r"[!-~]+", key.strip())):
            raise ValueError("Enter a valid API key without embedded whitespace.")
        if type(enabled) is not bool:
            raise ValueError("Choose whether explicitly requested AI calls are enabled.")
        if enabled and not (key.strip() or state.get("api_key")):
            raise ValueError("An API key is required to enable AI calls.")
        if key.strip():
            state["api_key"] = key.strip()
        state["ai_model"], state["ai_enabled"] = model, enabled
        state["budget"].max_calls = maximum
        state["settings_notice"] = "Settings saved. Key/model access is checked only when you make an AI request."
        clear_plan(state)
    elif action == "forget_ai":
        state["api_key"], state["ai_enabled"] = "", False
        state["settings_notice"] = "Key removed from this session. AI requests are disabled."
        clear_plan(state)
    elif action == "settings_ack":
        pass  # Replaces the component's last submitted value with a key-free message.
    elif action == "god_interpret":
        require_ai(state)
        clear_plan(state)
        state["god_result"] = None
        plan = interpret_command(sim, message.get("command"), state["api_key"], state["ai_model"], state["budget"])
        preview = dry_run(sim, plan)
        state["god_pending"] = {"id": uuid4().hex, "fingerprint": plan_fingerprint(sim), "plan": plan, "preview": preview}
    elif action == "god_apply":
        pending = state.get("god_pending")
        if not pending or message.get("plan_id") != pending["id"]:
            raise ValueError("This preview is no longer available. Interpret the command again.")
        if plan_fingerprint(sim) != pending["fingerprint"]:
            clear_plan(state)
            raise ValueError("The world changed since this preview. Interpret the command again before applying it.")
        state["sim"] = apply_plan(sim, pending["plan"])
        state["god_result"] = {"summary": pending["plan"]["summary"], "effects": pending["preview"]["effects"], "day": state["sim"].world.day}
        clear_plan(state)
    elif action == "god_cancel":
        clear_plan(state)
        state["god_result"] = None
    elif action == "step":
        sim.step(integer(message.get("days", 1), 1, 30, "Days"))
        clear_plan(state)
    elif action == "reset":
        state["sim"] = Simulation(integer(message.get("seed", 7), 0, 2**31-1, "Seed"), integer(message.get("population", 100), 20, 250, "Population"))
        state["experiment"] = state["save_data"] = state["god_result"] = None
        clear_plan(state)
    elif action == "intervene":
        sim.intervene(message.get("scenario"))
        clear_plan(state)
    elif action == "save":
        state["save_data"], state["save_id"] = sim.save(), message["id"]
    elif action == "load":
        raw = message.get("data")
        if not isinstance(raw, str) or len(raw.encode()) > 8_000_000:
            raise ValueError("Choose a New Haven save file smaller than 8 MB.")
        state["sim"] = Simulation.load(raw)
        state["experiment"] = state["save_data"] = state["god_result"] = None
        clear_plan(state)
    elif action == "reflect":
        require_ai(state)
        reflect(sim, state["api_key"], state["ai_model"], state["budget"])
        clear_plan(state)
    elif action == "experiment":
        mode = message.get("mode", "rules")
        if mode not in ("rules", "ai"):
            raise ValueError("Unknown experiment mode.")
        seeds = integer(message.get("seeds", 3), 1, 10, "Seeds")
        cognition = None
        if mode == "ai":
            require_ai(state)
            allowance = min(5, (state["budget"].max_calls-state["budget"].calls)//seeds)
            if allowance < 1:
                raise ValueError("Not enough calls remain for an equal per-seed allowance.")
            used_by_seed = {}
            def cognition(world):
                used = used_by_seed.get(world.seed, 0)
                if state["budget"].calls < state["budget"].max_calls and used < allowance:
                    reflect(world, state["api_key"], state["ai_model"], state["budget"])
                    used_by_seed[world.seed] = used+1
                    return True
                return False
        state["experiment"] = compare(seed=sim.seed, population=min(250, max(20, len(sim.living))), seeds=seeds,
            horizon=message.get("horizon", 30), scenario=message.get("scenario", "storm"), cognition=cognition)
    else:
        raise ValueError("That action is not supported.")

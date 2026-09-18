"""Streamlit host for the interactive New Haven canvas application."""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from src.civilisation.sim import Simulation
from src.civilisation.cognition import Budget, reflect
from src.civilisation.experiments import compare

VERSION = "1.0"
st.set_page_config(page_title="New Haven · A living world", page_icon="🌳", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{max-width:none;padding:0.6rem 0.7rem 2rem;}
[data-testid="stHeader"]{height:0;background:transparent;}
[data-testid="stMainBlockContainer"]{padding-top:0.4rem;}
[data-testid="stAppViewContainer"]{background:#f4f6ef;}
[data-testid="stElementContainer"] iframe{border:0;}
</style>""", unsafe_allow_html=True)
if st.session_state.get("app_version") != VERSION:
    st.session_state.clear()
    st.session_state.update(app_version=VERSION, sim=Simulation(7, 100), budget=Budget(), ack=None,
                            error=None, experiment=None, save_data=None, save_id=None)


def bounded_integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be a whole number from {low} to {high}.")
    return value


def dispatch(message):
    sim = st.session_state.sim
    action = message.get("action")
    if action == "step":
        sim.step(bounded_integer(message.get("days", 1), 1, 30, "Days"))
    elif action == "reset":
        seed = bounded_integer(message.get("seed", 7), 0, 2**31 - 1, "Seed")
        population = bounded_integer(message.get("population", 100), 20, 250, "Population")
        st.session_state.sim = Simulation(seed, population)
        st.session_state.experiment = None
        st.session_state.save_data = None
    elif action == "intervene":
        sim.intervene(message.get("scenario"))
    elif action == "save":
        st.session_state.save_data = sim.save()
        st.session_state.save_id = message["id"]
    elif action == "load":
        raw = message.get("data")
        if not isinstance(raw, str) or len(raw.encode()) > 8_000_000:
            raise ValueError("Choose a New Haven save file smaller than 8 MB.")
        st.session_state.sim = Simulation.load(raw)
        st.session_state.experiment = None
        st.session_state.save_data = None
    elif action == "reflect":
        if not st.session_state.get("ai_enabled"):
            raise ValueError("Enable optional AI below the app before requesting a reflection.")
        reflect(sim, st.session_state.get("api_key", ""), st.session_state.get("ai_model", ""), st.session_state.budget)
    elif action == "experiment":
        cognition = None
        if message.get("mode") == "ai":
            if not st.session_state.get("ai_enabled") or not st.session_state.get("api_key"):
                raise ValueError("AI comparison needs optional AI enabled and your own key configured below the app.")
            seeds = bounded_integer(message.get("seeds", 3), 1, 10, "Seeds")
            allowance = min(5, (st.session_state.budget.max_calls - st.session_state.budget.calls) // seeds)
            if allowance < 1:
                raise ValueError("Not enough calls remain to give each seed an equal AI allowance. Reduce the number of seeds or increase your explicit call limit.")
            used_by_seed = {}
            def cognition(world):
                budget = st.session_state.budget
                used = used_by_seed.get(world.seed, 0)
                if budget.calls < budget.max_calls and used < allowance:
                    reflect(world, st.session_state.api_key, st.session_state.ai_model, budget)
                    used_by_seed[world.seed] = used + 1
                    return True
                return False
        with st.spinner("Running isolated worlds across paired seeds…"):
            st.session_state.experiment = compare(seed=sim.seed, population=min(250, max(20, len(sim.living))),
                seeds=message.get("seeds", 3), horizon=message.get("horizon", 90),
                scenario=message.get("scenario", "education"), cognition=cognition)
            if cognition:
                st.session_state.experiment["note"] += f" Each seed received an equal allowance of up to {allowance} event reflections. Actual calls are reported per run; worlds without eligible events use none."
    else:
        raise ValueError("That action is not supported.")


town = components.declare_component("new_haven_world", path=str(Path(__file__).parent / "frontend"))
budget = st.session_state.budget
message = town(state=st.session_state.sim.snapshot(), experiment=st.session_state.experiment,
    error=st.session_state.error, ack=st.session_state.ack,
    save_data=st.session_state.save_data, save_id=st.session_state.save_id,
    ai={"enabled": bool(st.session_state.get("ai_enabled") and st.session_state.get("api_key")),
        "calls": budget.calls, "max_calls": budget.max_calls, "tokens": budget.tokens,
        "status": "Optional AI is off. Rules run without API costs." if not st.session_state.get("ai_enabled") else "AI runs only when explicitly requested."},
    key="world", default=None)
with st.expander("Optional AI cognition · bring your own key"):
    st.caption("The simulation is free without AI. Enabling this sends fictional citizen/event context to OpenAI only when you request a reflection or AI experiment. Your provider charges for those calls. Your key stays in this server session and is never included in world saves or the town interface.")
    st.checkbox("Enable explicitly requested AI decisions", key="ai_enabled", value=False)
    st.text_input("OpenAI API key", type="password", key="api_key")
    st.text_input("Structured-output capable model ID", value="gpt-4.1-mini", key="ai_model")
    limit = st.number_input("Maximum calls this session (failed attempts count)", min_value=1, max_value=50, value=10, step=1)
    budget.max_calls = int(limit)
    st.caption(f"Used {budget.calls} calls · {budget.tokens:,} reported tokens. World resets do not reset this counter. No automatic retries. This is a call limit, not a guaranteed currency budget.")
    def forget_key():
        st.session_state.api_key = ""
        st.session_state.ai_enabled = False
    st.button("Forget API key", on_click=forget_key)

# Register settings widgets before rerunning so Streamlit preserves their state.
if isinstance(message, dict) and isinstance(message.get("id"), (str, int)) and message["id"] != st.session_state.ack:
    st.session_state.ack = message["id"]
    st.session_state.error = None
    try:
        dispatch(message)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        st.session_state.error = str(error)[:350]
    st.rerun()

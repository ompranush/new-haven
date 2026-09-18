"""Streamlit session host; all credentials remain outside world state."""
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
from src.civilisation.sim import Simulation
from src.civilisation.cognition import Budget
from src.civilisation.controller import handle_action, public_ai

VERSION = "3.0"
st.set_page_config(page_title="New Haven · A living world", page_icon="🌳", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{max-width:none;padding:0.6rem 0.7rem 2rem;}
[data-testid="stHeader"]{height:0;background:transparent;}
[data-testid="stMainBlockContainer"]{padding-top:0.4rem;}
[data-testid="stAppViewContainer"]{background:#101a25;}
[data-testid="stElementContainer"] iframe{border:0;}
</style>""", unsafe_allow_html=True)
if st.session_state.get("app_version") != VERSION:
    st.session_state.clear()
    st.session_state.update(app_version=VERSION, sim=Simulation(7, 100), budget=Budget(), ack=None,
        error=None, experiment=None, save_data=None, save_id=None, api_key="", ai_model="gpt-4.1-mini",
        ai_enabled=False, god_pending=None, god_result=None, settings_notice="")

town = components.declare_component("new_haven_world", path=str(Path(__file__).parent / "frontend"))
pending = st.session_state.god_pending
message = town(state=st.session_state.sim.snapshot(), experiment=st.session_state.experiment,
    error=st.session_state.error, ack=st.session_state.ack, save_data=st.session_state.save_data,
    save_id=st.session_state.save_id, ai=public_ai(st.session_state),
    god={"pending": {k: pending[k] for k in ("id", "plan", "preview")} if pending else None,
         "result": st.session_state.god_result}, key="world", default=None)
if isinstance(message, dict) and isinstance(message.get("id"), (str, int)) and message["id"] != st.session_state.ack:
    st.session_state.ack = message["id"]
    if message.get("action") != "settings_ack":
        st.session_state.error = None
    try:
        with st.spinner("Processing your request…"):
            handle_action(st.session_state, message)
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        st.session_state.error = str(error)[:350]
    finally:
        # Do not retain the submitted secret in the message object.
        message.pop("api_key", None)
    st.rerun()

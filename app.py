import pandas as pd
import streamlit as st
from src.civilisation.sim import Simulation

st.set_page_config(page_title="New Haven", page_icon="🏘️", layout="wide")
st.title("🏘️ New Haven")
st.caption("A local-first AI civilisation simulator — v0.1")
with st.sidebar:
    seed = st.number_input("World seed", min_value=0, value=7)
    population = st.slider("Starting population", 20, 250, 100)
    reset = st.button("Create new world")
    advance = st.button("Advance one day", type="primary")
if "sim" not in st.session_state or reset:
    st.session_state.sim = Simulation(seed, population)
sim = st.session_state.sim
if advance: sim.step()

summary = sim.summary()
for col, (label, value) in zip(st.columns(5), [("Day", summary["day"]), ("Population", summary["population"]), ("Average happiness", f'{summary["happiness"]}%'), ("Food", summary["food"]), ("Unemployment", f'{summary["unemployment"]}%')]):
    col.metric(label, value)
history = pd.DataFrame(sim.world.history).set_index("day")
left, right = st.columns(2)
with left:
    st.subheader("Settlement pulse")
    st.line_chart(history[["population", "food"]])
with right:
    st.subheader("Prosperity & mood")
    st.line_chart(history[["wealth", "happiness"]])
st.subheader("Recent world events")
st.write("• " + "\n• ".join(sim.world.events[-8:][::-1]) if sim.world.events else "The settlement is quiet. Advance a day to begin its story.")
st.subheader("Citizens")
rows = [{"name": c.name, "age": round(c.age, 1), "job": c.job or "Unemployed", "wealth": round(c.wealth, 1), "happiness": round(c.happiness, 1), "goal": c.goal} for c in sim.living]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

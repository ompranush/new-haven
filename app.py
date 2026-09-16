import html

import pandas as pd
import streamlit as st

from src.civilisation.sim import Simulation

st.set_page_config(page_title="New Haven", page_icon="🏘️", layout="wide")
st.title("🏘️ New Haven")
st.caption("A local-first, deterministic civilisation simulator — v0.2")

with st.sidebar:
    seed = st.number_input("World seed", min_value=0, value=7)
    population = st.slider("Starting population", 20, 250, 100)
    reset = st.button("Create new world")
    advance = st.button("Advance one day", type="primary")
    advance_ten = st.button("Advance ten days")

if "sim" not in st.session_state or reset:
    st.session_state.sim = Simulation(seed, population)
sim = st.session_state.sim
if advance:
    sim.step()
if advance_ten:
    sim.step(10)

summary = sim.summary()
for column, (label, value) in zip(
    st.columns(6),
    [
        ("Day", summary["day"]),
        ("Population", summary["population"]),
        ("Average happiness", f'{summary["happiness"]}%'),
        ("Food", summary["food"]),
        ("Unemployment", f'{summary["unemployment"]}%'),
        ("Weather", summary["weather"]),
    ],
):
    column.metric(label, value)

history = pd.DataFrame(sim.world.history).set_index("day")
left, right = st.columns(2)
with left:
    st.subheader("Settlement pulse")
    st.line_chart(history[["population", "food"]])
with right:
    st.subheader("Prosperity & mood")
    st.line_chart(history[["wealth", "happiness"]])

st.subheader("Voxel-inspired town")
tile_icons = {
    "water": "🟦", "road": "🟫", "farm": "🌾", "house": "🏠",
    "market": "🏪", "workshop": "⚒️", "grass": "🟩",
}
landmarks = {(1, y): "water" for y in range(9)}
landmarks.update({(x, 4): "road" for x in range(3, 10)})
landmarks.update({(4, 2): "house", (7, 2): "house", (9, 5): "house", (5, 6): "house", (3, 6): "farm", (8, 3): "market", (10, 6): "workshop"})
positions = {(citizen.x, citizen.y) for citizen in sim.living}
rows = []
for y in range(sim.world.height):
    row = []
    for x in range(sim.world.width):
        if (x, y) in positions:
            row.append("🧑")
        else:
            row.append(tile_icons[landmarks.get((x, y), "grass")])
    rows.append(" ".join(row))
st.code("\n".join(rows), language=None)
st.caption("🧑 residents move each day; 🟦 river; 🌾 farm; 🏠 homes; 🏪 market; ⚒️ workshop.")

left, right = st.columns(2)
with left:
    st.subheader("Recent world events")
    st.write("• " + "\n• ".join(sim.world.events[-8:][::-1]) if sim.world.events else "The settlement is quiet. Advance a day to begin its story.")
with right:
    st.subheader("Citizen memories")
    memorable = [citizen for citizen in sim.living if citizen.memories][-8:]
    if memorable:
        for citizen in memorable:
            st.write(f"**{citizen.name}** — {citizen.memories[-1]}")
    else:
        st.caption("Residents will form memories as the town evolves.")

st.subheader("Citizens")
rows = [
    {
        "name": citizen.name,
        "age": round(citizen.age, 1),
        "job": citizen.job or "Unemployed",
        "wealth": round(citizen.wealth, 1),
        "happiness": round(citizen.happiness, 1),
        "goal": citizen.goal,
        "latest memory": citizen.memories[-1] if citizen.memories else "—",
    }
    for citizen in sim.living
]
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

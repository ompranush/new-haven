import html

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.civilisation.sim import LANDMARKS, Simulation

st.set_page_config(page_title="New Haven", page_icon="🏘️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp {background: radial-gradient(circle at 20% 0%, #173e4b 0, #0a1720 48%, #071116 100%); color: #eff7f1;}
.block-container {max-width: 1450px; padding-top: 1.5rem;}
[data-testid="stMetric"] {background: rgba(21, 42, 48, .82); border: 1px solid rgba(151, 210, 185, .18); border-radius: 15px; padding: 14px; box-shadow: 0 10px 30px rgba(0,0,0,.15);}
[data-testid="stMetricValue"] {color: #f6cf7d;}
[data-testid="stSidebar"] {background: #0a161d;}
h1, h2, h3 {letter-spacing: -.03em;}
div[data-testid="stTabs"] button {font-weight: 700;}
</style>
""", unsafe_allow_html=True)


def iso_point(x: int, y: int) -> tuple[int, int]:
    return 420 + (x - y) * 31, 42 + (x + y) * 16


def town_svg(sim: Simulation) -> str:
    world = sim.world
    weather = {"Clear": "#84d2e2", "Rain": "#658ca8", "Wind": "#90b3ae", "Storm": "#435474"}.get(world.weather, "#84d2e2")
    tiles, objects, citizens = [], [], []
    for y in range(world.height):
        for x in range(world.width):
            px, py = iso_point(x, y)
            terrain = "#4a8b62"
            if x == 1:
                terrain = "#2d7797"
            elif y == 4 and 3 <= x <= 9:
                terrain = "#9b8158"
            points = f"{px},{py} {px+31},{py+16} {px},{py+32} {px-31},{py+16}"
            tiles.append(f'<polygon points="{points}" fill="{terrain}" stroke="#214d47" stroke-width="1"/>')
    buildings = {
        (3, 6): ("farm", "#d8b653"), (8, 3): ("market", "#d07845"),
        (10, 6): ("workshop", "#8296a1"), (4, 2): ("home", "#c16a52"),
        (7, 2): ("home", "#c16a52"), (9, 5): ("home", "#c16a52"), (5, 6): ("home", "#c16a52"),
    }
    for (x, y), (kind, color) in buildings.items():
        px, py = iso_point(x, y)
        if kind == "farm":
            objects.append(f'<path d="M {px-20} {py+14} L {px+20} {py+14} M {px-15} {py+7} L {px-10} {py+21} M {px-4} {py+7} L {px+1} {py+21} M {px+8} {py+7} L {px+13} {py+21}" stroke="#e6d86d" stroke-width="3"/>')
        else:
            objects.append(f'<path d="M {px-19} {py+9} L {px} {py-1} L {px+19} {py+9} L {px+19} {py-12} L {px} {py-22} L {px-19} {py-12} Z" fill="{color}" stroke="#263d42" stroke-width="2"/>')
            objects.append(f'<path d="M {px-19} {py+9} L {px} {py+19} L {px+19} {py+9} L {px} {py-1} Z" fill="#253c40" opacity=".35"/>')
            objects.append(f'<text x="{px}" y="{py-27}" text-anchor="middle" fill="#f9e5b1" font-size="10" font-family="sans-serif">{kind.upper()}</text>')
    for citizen in sim.living:
        px, py = iso_point(citizen.x, citizen.y)
        mood = "#f4cb6d" if citizen.happiness >= 60 else "#e68b69" if citizen.happiness < 40 else "#b9dc91"
        citizens.append(f'<g><circle cx="{px}" cy="{py+10}" r="7" fill="{mood}" stroke="#17272c" stroke-width="2"/><path d="M {px-5} {py+17} Q {px} {py+25} {px+5} {py+17}" fill="{mood}" stroke="#17272c" stroke-width="2"/></g>')
    overlay = "" if world.weather == "Clear" else f'<rect width="840" height="410" fill="{weather}" opacity=".13"/>'
    return f"""<html><body style="margin:0;background:#10242b"><svg viewBox="0 0 840 410" width="100%" height="410" role="img" aria-label="Isometric view of New Haven">
    <defs><filter id="shadow"><feDropShadow dx="0" dy="5" stdDeviation="4" flood-opacity=".35"/></filter></defs>
    <rect width="840" height="410" fill="{weather}"/><g filter="url(#shadow)">{''.join(tiles)}{''.join(objects)}{''.join(citizens)}</g>{overlay}
    <text x="22" y="28" fill="#f7e4ae" font-family="sans-serif" font-size="16" font-weight="700">DAY {world.day} · {html.escape(world.weather).upper()}</text>
    </svg></body></html>"""


st.title("New Haven")
st.caption("An inspectable artificial civilisation — where people, resources, weather, and memories shape the next day.")

with st.sidebar:
    st.header("World controls")
    seed = st.number_input("World seed", min_value=0, value=7)
    population = st.slider("Starting population", 20, 250, 100)
    if st.button("Create new world", use_container_width=True):
        st.session_state.sim = Simulation(seed, population)
    if "sim" not in st.session_state:
        st.session_state.sim = Simulation(seed, population)
    st.divider()
    st.caption("Time")
    one, ten = st.columns(2)
    advance_one = one.button("＋1 day", use_container_width=True, type="primary")
    advance_ten = ten.button("＋10 days", use_container_width=True)
    st.divider()
    st.caption("Council actions")
    scenario = st.selectbox("Intervention", ["festival", "storm", "aid", "market"], format_func=lambda x: {"festival": "Fund a festival", "storm": "Trigger a river storm", "aid": "Send relief convoy", "market": "Set food-price cap"}[x])
    intervene = st.button("Apply intervention", use_container_width=True)

sim = st.session_state.sim
if advance_one:
    sim.step()
if advance_ten:
    sim.step(10)
if intervene:
    sim.intervene(scenario)

summary = sim.summary()
food_state = "normal" if summary["food"] > summary["population"] else "inverse"
st.markdown("### Settlement HUD")
metric_values = [
    ("Day", summary["day"]), ("Residents", summary["population"]), ("Food stores", f'{summary["food"]:.0f}'),
    ("Food price", f'£{summary["food_price"]:.2f}'), ("Town treasury", f'£{summary["treasury"]:.0f}'),
    ("Happiness", f'{summary["happiness"]:.0f}%'), ("Unemployed", f'{summary["unemployment"]:.0f}%'), ("Weather", summary["weather"]),
]
for row in (metric_values[:4], metric_values[4:]):
    for column, (label, value) in zip(st.columns(4), row):
        column.metric(label, value)

town_tab, residents_tab, analytics_tab = st.tabs(["Town", "Residents", "Analytics"])

with town_tab:
    scene, story = st.columns([1.75, 0.85], gap="large")
    with scene:
        st.subheader("New Haven, at a glance")
        components.html(town_svg(sim), height=425, scrolling=False)
        st.caption("Gold residents are thriving; green residents are steady; coral residents need support. Buildings and terrain are generated from the same seeded world.")
    with story:
        st.subheader("Town chronicle")
        if sim.world.events:
            for event in sim.world.events[-9:][::-1]:
                st.markdown(f"▸ {event}")
        else:
            st.info("The settlement is quiet. Advance a day to begin its story.")
        st.subheader("Legend")
        st.caption("Blue river · tan road · gold farm · orange market · slate workshop · coral homes")

with residents_tab:
    people = sim.living
    selected_name = st.selectbox("Inspect a resident", [citizen.name for citizen in people])
    resident = next(citizen for citizen in people if citizen.name == selected_name)
    inspector, memories = st.columns([0.85, 1.15])
    with inspector:
        st.subheader(resident.name)
        st.write(f"**{resident.job or 'Unemployed'}** · age {resident.age:.0f}")
        st.progress(int(resident.happiness), text=f"Happiness {resident.happiness:.0f}%")
        st.progress(int(resident.energy), text=f"Energy {resident.energy:.0f}%")
        st.progress(int(100 - resident.hunger), text=f"Food security {100-resident.hunger:.0f}%")
        st.caption(f"Current activity: {resident.activity}")
        st.caption(f"Goal: {resident.goal}")
    with memories:
        st.subheader("Memory journal")
        if resident.memories:
            for memory in resident.memories[::-1]:
                st.write(f"• {memory}")
        else:
            st.info("No notable memory yet.")
        connections = sorted(resident.relationships.items(), key=lambda item: item[1], reverse=True)[:4]
        if connections:
            lookup = {citizen.id: citizen.name for citizen in people}
            st.caption("Closest connections: " + ", ".join(f"{lookup.get(person_id, 'Unknown')} ({bond:.0f})" for person_id, bond in connections))
    st.subheader("All residents")
    rows = [{"name": c.name, "job": c.job or "Unemployed", "activity": c.activity, "wealth": round(c.wealth, 1), "mood": round(c.happiness, 1), "energy": round(c.energy, 1), "food security": round(100-c.hunger, 1), "goal": c.goal} for c in people]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

with analytics_tab:
    st.subheader("Civilisation trends")
    history = pd.DataFrame(sim.world.history).set_index("day")
    if len(history) < 2:
        st.info("Advance at least one day to reveal trends.")
    else:
        a, b = st.columns(2)
        a.line_chart(history[["population", "food"]])
        b.line_chart(history[["wealth", "happiness"]])
        st.caption("Charts are intentionally separated so wealth does not obscure happiness.")

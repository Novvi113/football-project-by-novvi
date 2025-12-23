import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from scipy.spatial import ConvexHull
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as path_effects
from utils.data import get_competitions, get_matches, get_events

st.set_page_config(page_title="Match Dashboard", layout="wide")

# --- CSS (Светлый стиль для дашборда, но на темном фоне) ---
st.markdown("""
<style>
    .stApp { background-color: #121212; }
    h1, h2, h3, h4 { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏟️ MATCH DAY DASHBOARD")

# --- DATA LOADING ---
comps = get_competitions()
comp_name = st.sidebar.selectbox("Competition", comps['competition_name'].unique())
comp_id = comps[comps['competition_name'] == comp_name]['competition_id'].values[0]
seasons = comps[comps['competition_name'] == comp_name]
season_name = st.sidebar.selectbox("Season", seasons['season_name'].unique())
season_id = seasons[seasons['season_name'] == season_name]['season_id'].values[0]
matches = get_matches(comp_id, season_id)
match_list = matches['home_team'] + " vs " + matches['away_team']
selected_match = st.sidebar.selectbox("Match", match_list)
match_id = matches[match_list == selected_match]['match_id'].values[0]

with st.spinner('Loading tactical data...'):
    events = get_events(match_id)

players = sorted(events['player'].dropna().unique())
player_name = st.selectbox("Select Player to Analyze", players)

# Filter Data
p_df = events[events['player'] == player_name].copy()
if p_df.empty:
    st.error("No data for this player.")
    st.stop()

# --- DASHBOARD LAYOUT (3 COLUMNS) ---
col1, col2, col3 = st.columns(3)

# ================= FIELD 1: OFFENSIVE ACTIONS =================
with col1:
    st.markdown("<h4 style='text-align: center; color: #E63946;'>Offensive Actions</h4>", unsafe_allow_html=True)
    pitch = VerticalPitch(pitch_type='statsbomb', line_color='#444444', pitch_color='#1a1a1a')
    fig, ax = pitch.draw(figsize=(10, 14))

    # 1. Passes (Arrows)
    passes = p_df[p_df['type'] == 'Pass']
    # Successful
    succ_pass = passes[passes['pass_outcome'].isna()]
    if not succ_pass.empty and 'pass_end_location' in succ_pass.columns:
        pitch.arrows(succ_pass.x, succ_pass.y,
                     succ_pass['pass_end_location'].apply(lambda x: x[0] if isinstance(x, list) else 0),
                     succ_pass['pass_end_location'].apply(lambda x: x[1] if isinstance(x, list) else 0),
                     ax=ax, width=2, headwidth=8, color='#00b4d8', alpha=0.7, label='Succ. Pass')
    
    # Key Passes (Purple)
    key_passes = passes[passes.get('pass_shot_assist', False) == True]
    if not key_passes.empty:
        pitch.lines(key_passes.x, key_passes.y,
                    key_passes['pass_end_location'].apply(lambda x: x[0]),
                    key_passes['pass_end_location'].apply(lambda x: x[1]),
                    ax=ax, lw=4, color='#9d4edd', transparent=True, comet=True, label='Key Pass')

    # 2. Shots (Circles)
    shots = p_df[p_df['type'] == 'Shot']
    goals = shots[shots['shot_outcome'] == 'Goal']
    no_goals = shots[shots['shot_outcome'] != 'Goal']
    
    pitch.scatter(no_goals.x, no_goals.y, ax=ax, s=100, c='none', edgecolors='#E63946', hatch='///', label='Shot')
    pitch.scatter(goals.x, goals.y, ax=ax, s=200, c='#E63946', edgecolors='white', marker='football', label='Goal')

    # 3. Dribbles (Hexagons)
    dribbles = p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')]
    pitch.scatter(dribbles.x, dribbles.y, ax=ax, s=150, marker='h', c='#ffba08', edgecolors='black', label='Dribble')

    # Legend
    ax.legend(facecolor='#1a1a1a', edgecolor='none', labelcolor='white', loc='lower center', fontsize=9)
    st.pyplot(fig)

# ================= FIELD 2: DEFENSIVE ACTIONS =================
with col2:
    st.markdown("<h4 style='text-align: center; color: #E63946;'>Defensive Actions</h4>", unsafe_allow_html=True)
    pitch = VerticalPitch(pitch_type='statsbomb', line_color='#444444', pitch_color='#1a1a1a')
    fig, ax = pitch.draw(figsize=(10, 14))

    # 1. Tackles
    tackles = p_df[p_df['type'] == 'Duel'] # Statsbomb generic
    # Это упрощение, в реальном SB надо смотреть duel_type
    pitch.scatter(tackles.x, tackles.y, ax=ax, s=150, marker='x', c='#ef233c', linewidth=3, label='Duel/Tackle')

    # 2. Interceptions
    interceptions = p_df[p_df['type'] == 'Interception']
    pitch.scatter(interceptions.x, interceptions.y, ax=ax, s=150, marker='D', c='#3a86ff', edgecolors='white', label='Interception')

    # 3. Recoveries
    recoveries = p_df[p_df['type'] == 'Ball Recovery']
    pitch.scatter(recoveries.x, recoveries.y, ax=ax, s=120, marker='o', c='none', edgecolors='#ffbe0b', linewidth=2, label='Recovery')
    
    # 4. Clearances
    clearances = p_df[p_df['type'] == 'Clearance']
    pitch.scatter(clearances.x, clearances.y, ax=ax, s=120, marker='^', c='#8338ec', label='Clearance')

    ax.legend(facecolor='#1a1a1a', edgecolor='none', labelcolor='white', loc='lower center', fontsize=9)
    st.pyplot(fig)

# ================= FIELD 3: TERRITORY & HULL =================
with col3:
    st.markdown("<h4 style='text-align: center; color: #E63946;'>Touches & Territory</h4>", unsafe_allow_html=True)
    pitch = VerticalPitch(pitch_type='statsbomb', line_color='#444444', pitch_color='#1a1a1a')
    fig, ax = pitch.draw(figsize=(10, 14))

    # Все касания с координатами
    touches = p_df[p_df['x'].notna()]
    
    # 1. Точки касаний (мелкие)
    pitch.scatter(touches.x, touches.y, ax=ax, s=20, c='#E63946', alpha=0.3)

    # 2. Convex Hull (Зона обитания)
    if len(touches) > 4:
        # Берем точки X и Y
        points = touches[['x', 'y']].values
        hull = ConvexHull(points)
        # Рисуем полигон
        path = ''
        for vertex in hull.vertices:
            path += f"{points[vertex, 0]},{points[vertex, 1]} "
        
        # Используем mplsoccer polygon
        pitch.polygon([points[hull.vertices]], ax=ax, facecolor='#E63946', alpha=0.2, edgecolor='#E63946', lw=2)

    # 3. Статистика внизу поля
    ax.text(40, 125, f"Total Touches: {len(touches)}", color='white', ha='center', fontsize=12, fontweight='bold')
    
    # Final Third Touches
    ft_touches = len(touches[touches['x'] > 80])
    ax.text(40, 122, f"Final 3rd: {ft_touches}", color='#ffba08', ha='center', fontsize=10)

    # Box Touches
    box_touches = len(touches[(touches['x'] > 102) & (touches['y'] > 18) & (touches['y'] < 62)])
    ax.text(40, 119, f"Box: {box_touches}", color='#3a86ff', ha='center', fontsize=10)

    st.pyplot(fig)

# --- FOOTER STATS ---
st.markdown("---")
col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
col_s1.metric("Minutes", "90'") # Хардкод для примера, можно вытащить из substitution
col_s2.metric("Passes", f"{len(succ_pass)}/{len(passes)}")
col_s3.metric("Shots", len(shots))
col_s4.metric("Key Passes", len(key_passes))
col_s5.metric("xG", round(p_df['shot_statsbomb_xg'].sum(), 2) if 'shot_statsbomb_xg' in p_df.columns else 0)
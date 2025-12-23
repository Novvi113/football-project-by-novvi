import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Radar
from statsbombpy import sb
import os

st.set_page_config(page_title="Season Battle", layout="wide")

# --- СТИЛИ ---
st.markdown("""
<style>
    .stApp { background-color: #121212; }
    h1, h2, h3 { color: #fff !important; }
    .stButton>button {
        color: #ffffff;
        background-color: #ff006e;
        border-radius: 10px;
        height: 50px;
        width: 100%;
        font-weight: bold;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚔️ ULTIMATE SEASON BATTLE")

# --- ТУРБО-ДВИЖОК ---
@st.cache_data(show_spinner=False)
def get_season_matches_c(competition_id, season_id):
    return sb.matches(competition_id=competition_id, season_id=season_id)

def load_battle_data_turbo(season_id):
    filename = f"season_{season_id}_data.csv"
    
    if os.path.exists(filename):
        return pd.read_csv(filename, low_memory=False)
    
    st.toast("⏳ Скачиваем сезон... Подождите...", icon="🌍")
    
    matches = get_season_matches_c(11, season_id)
    team_matches = matches[(matches['home_team'] == 'Barcelona') | (matches['away_team'] == 'Barcelona')]
    ids = team_matches['match_id'].tolist()
    
    all_events = []
    bar = st.progress(0, text="Загрузка матчей...")
    
    for i, m_id in enumerate(ids):
        try:
            ev = sb.events(match_id=m_id)
            ev['match_id'] = m_id
            all_events.append(ev)
        except: pass
        bar.progress(int(((i+1)/len(ids))*100))
        
    bar.empty()
        
    if all_events:
        df = pd.concat(all_events, ignore_index=True)
        # Фикс координат
        if 'location' in df.columns:
            df['x'] = df['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
            df['y'] = df['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
        df.to_csv(filename, index=False)
        return df
        
    return pd.DataFrame()

def calc_p90(df, player_name):
    p_df = df[df['player'] == player_name]
    if p_df.empty: return [0]*6
    
    matches = p_df['match_id'].nunique()
    minutes_est = matches * 90 
    scale = 90 / minutes_est if minutes_est > 0 else 0
    
    g = len(p_df[p_df['shot_outcome'] == 'Goal']) * scale
    a = (len(p_df[p_df['pass_goal_assist'] == True]) if 'pass_goal_assist' in p_df.columns else 0) * scale
    s = len(p_df[p_df['type'] == 'Shot']) * scale
    kp = (len(p_df[p_df['pass_shot_assist'] == True]) if 'pass_shot_assist' in p_df.columns else 0) * scale
    dr = len(p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')]) * scale
    xg = (p_df['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in p_df.columns else 0) * scale
    
    return [g, a, s, kp, dr, xg]

# --- ИНТЕРФЕЙС ---
season_map = {
    "2014/15 (The Treble)": 26,
    "2015/16 (MSN Peak)": 27,
    "2010/11": 21,
    "2011/12": 22
}

s_choice = st.selectbox("Select Season", list(season_map.keys()))
s_id = season_map[s_choice]

df = load_battle_data_turbo(s_id)

if not df.empty:
    counts = df['player'].value_counts()
    top_players = sorted(counts[counts > 300].index.tolist())
    
    idx_m = top_players.index("Lionel Andrés Messi Cuccittini") if "Lionel Andrés Messi Cuccittini" in top_players else 0
    idx_s = top_players.index("Luis Alberto Suárez Díaz") if "Luis Alberto Suárez Díaz" in top_players else min(1, len(top_players)-1)
    
    c1, c2 = st.columns(2)
    p1 = c1.selectbox("Player 1", top_players, index=idx_m)
    p2 = c2.selectbox("Player 2", top_players, index=idx_s)
    
    if st.button("FIGHT! 🥊"):
        vals1 = calc_p90(df, p1)
        vals2 = calc_p90(df, p2)
        
        params = ["Goals", "Assists", "Shots", "Key Passes", "Dribbles", "xG"]
        # Исправленные списки
        min_v = [0, 0, 0, 0, 0, 0]
        max_v = [1.2, 0.8, 6.0, 4.0, 6.0, 1.2]
        
        radar = Radar(params, min_range=min_v, max_range=max_v, round_int=[False]*6, num_rings=4)
        fig, ax = radar.setup_axis()
        
        radar.draw_radar(vals1, ax=ax, kwargs_radar={'facecolor': '#00b4d8', 'alpha': 0.6}, kwargs_rings={'edgecolor': '#555'})
        radar.draw_radar(vals2, ax=ax, kwargs_radar={'facecolor': '#ff006e', 'alpha': 0.5}, kwargs_rings={'edgecolor': '#555'})
        
        line1, = ax.plot([], [], color='#00b4d8', linewidth=3, label=p1)
        line2, = ax.plot([], [], color='#ff006e', linewidth=3, label=p2)
        ax.legend(handles=[line1, line2], loc='upper center', bbox_to_anchor=(0.5, 1.15), frameon=False, labelcolor='white')
        
        fig.set_facecolor('#121212')
        ax.set_facecolor('#121212')
        
        st.pyplot(fig)
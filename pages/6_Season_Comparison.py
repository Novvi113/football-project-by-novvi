import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import PyPizza
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

st.title("⚔️ ELITE COMPARISON (PIZZA STYLE)")

# --- ТУРБО-ДВИЖОК ---
@st.cache_data(show_spinner=False)
def get_matches_data(comp_id, season_id):
    return sb.matches(competition_id=comp_id, season_id=season_id)

def load_data_turbo(season_id):
    filename = f"season_{season_id}_data.csv"
    if os.path.exists(filename):
        return pd.read_csv(filename, low_memory=False)
    
    # Если нет файла - качаем
    st.toast("⏳ Скачиваем сезон... (Один раз)", icon="💾")
    matches = get_matches_data(11, season_id)
    # Качаем только Барсу для скорости
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

def calc_pizza_stats(df, player_name):
    p_df = df[df['player'] == player_name]
    if p_df.empty: return [0]*12
    
    # Считаем "per 90"
    matches = p_df['match_id'].nunique()
    minutes = matches * 90
    scale = 90 / minutes if minutes > 0 else 0
    
    # 1. Non-Penalty Goals
    goals = len(p_df[(p_df['shot_outcome'] == 'Goal') & (p_df['shot_type'] != 'Penalty')]) * scale
    # 2. npxG
    npxg = (p_df[p_df['shot_type'] != 'Penalty']['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in p_df.columns else 0) * scale
    # 3. Shots
    shots = len(p_df[p_df['type'] == 'Shot']) * scale
    # 4. Assists
    assists = (len(p_df[p_df['pass_goal_assist'] == True]) if 'pass_goal_assist' in p_df.columns else 0) * scale
    # 5. xA
    xa = (p_df['pass_shot_assist'].sum() if 'pass_shot_assist' in p_df.columns else 0) * scale # Упрощенно xA
    # 6. Shot Creating Actions (SCA) - упрощенно Key Passes + Dribbles
    kp = len(p_df[p_df.get('pass_shot_assist', pd.Series(0)) == True]) * scale
    dr = len(p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')]) * scale
    sca = kp + dr
    
    # 7. Passes into Box
    p_box = 0
    passes = p_df[(p_df['type'] == 'Pass') & (p_df['pass_outcome'].isna())]
    if not passes.empty and 'pass_end_location' in passes.columns:
        p_box = len(passes[passes['pass_end_location'].apply(lambda x: x[0] >= 102 and 18 <= x[1] <= 62 if isinstance(x, list) else False)]) * scale
        
    # 8. Progressive Carries (Упрощенно)
    carries = len(p_df[p_df['type'] == 'Carry']) * scale * 0.5 # Коэффициент для реализма
    
    # 9. Successful Dribbles
    dribbles = dr # Уже посчитано выше
    
    # 10. Touches (in box) - Упрощенно берем все касания в атаке
    touches = len(p_df[p_df['x'] > 80]) * scale
    
    # 11. Pressures
    pressures = len(p_df[p_df['type'] == 'Pressure']) * scale
    
    # 12. Turnovers (Dispossessed)
    turnovers = len(p_df[p_df['type'] == 'Dispossessed']) * scale
    
    return [goals, npxg, shots, assists, xa, sca, p_box, carries, dribbles, touches, pressures, turnovers]

# --- ИНТЕРФЕЙС ---
season_map = {
    "2014/15 (The Treble)": 26,
    "2015/16 (MSN Peak)": 27,
    "2010/11 (Pep Era)": 21,
    "2011/12 (Messi 50 goals)": 22
}

s_choice = st.selectbox("Select Season", list(season_map.keys()))
s_id = season_map[s_choice]

df = load_data_turbo(s_id)

if not df.empty:
    counts = df['player'].value_counts()
    top_players = sorted(counts[counts > 500].index.tolist()) # Только основные
    
    # Дефолтный выбор
    idx1 = top_players.index("Lionel Andrés Messi Cuccittini") if "Lionel Andrés Messi Cuccittini" in top_players else 0
    idx2 = top_players.index("Neymar da Silva Santos Junior") if "Neymar da Silva Santos Junior" in top_players else 1
    
    c1, c2 = st.columns(2)
    p1 = c1.selectbox("Player 1", top_players, index=idx1)
    p2 = c2.selectbox("Player 2", top_players, index=idx2)
    
    if st.button("GENERATE PIZZA COMPARISON 🍕"):
        
        # --- ПАРАМЕТРЫ ДЛЯ ГРАФИКА ---
        params = [
            "Non-Pen Goals", "npxG", "Shots", "Assists", "xA", "SCA", 
            "Passes to Box", "Prog. Carries", "Dribbles", "Touches Att 3rd", 
            "Pressures", "Turnovers"
        ]
        
        # ЭТАЛОННЫЕ ЗНАЧЕНИЯ (Максимумы для 100% графика)
        # Подбираем так, чтобы Месси не вылезал за края слишком сильно :)
        max_ranges = [
            1.0, 1.0, 6.0, 0.8, 0.6, 10.0,
            10.0, 15.0, 6.0, 50.0,
            25.0, 5.0 
        ]
        # Для Turnovers: чем меньше, тем лучше. PyPizza не умеет инвертировать сама красиво,
        # поэтому оставим как "Количество потерь" (меньше закрашено = меньше потерь)
        
        min_ranges = [0] * 12
        
        vals1 = calc_pizza_stats(df, p1)
        vals2 = calc_pizza_stats(df, p2)
        
        # --- РИСУЕМ ДВЕ ПИЦЦЫ РЯДОМ ---
        col_graph1, col_graph2 = st.columns(2)
        
        # Функция рисования
        def draw_pizza(values, name, color_main):
            slice_colors = [color_main] * 6 + ["#FF9300"] * 4 + ["#999999"] * 2
            text_colors = ["#F2F2F2"] * 12
            
            baker = PyPizza(
                params=params,
                min_range=min_ranges,
                max_range=max_ranges,
                background_color="#121212",
                straight_line_color="#333",
                last_circle_lw=1,
                other_circle_lw=1,
                inner_circle_size=20
            )
            
            fig, ax = baker.make_pizza(
                values,
                figsize=(8, 8),
                color_blank_space="same",
                slice_colors=slice_colors,
                value_colors=text_colors,
                value_bck_colors=slice_colors,
                blank_alpha=0.2,
                kwargs_slices=dict(edgecolor="#121212", zorder=2, linewidth=2),
                kwargs_params=dict(color="#aaaaaa", fontsize=9, va="center"),
                kwargs_values=dict(color="#ffffff", fontsize=11, zorder=3,
                                   bbox=dict(edgecolor=color_main, facecolor=color_main, boxstyle="round,pad=0.2", lw=1))
            )
            # Заголовок
            fig.text(0.515, 0.975, name, size=20, ha="center", color=color_main, fontweight='bold')
            return fig

        with col_graph1:
            st.pyplot(draw_pizza(vals1, p1, "#1E88E5")) # Синий
            
        with col_graph2:
            st.pyplot(draw_pizza(vals2, p2, "#D81B60")) # Розовый (как Мбаппе)

        # Таблица сравнения
        st.markdown("### 📊 Head-to-Head Data (Per 90)")
        res_df = pd.DataFrame({p1: vals1, p2: vals2}, index=params)
        # Подсветка победителя
        st.dataframe(res_df.style.highlight_max(axis=1, color='#333333'))

else:
    st.info("Waiting for data...")
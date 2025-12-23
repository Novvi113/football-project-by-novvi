import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import PyPizza
from matplotlib.font_manager import FontProperties
from utils.data import get_competitions, get_matches, get_events

st.set_page_config(page_title="Elite Profile", layout="wide")

# --- CSS ДЛЯ КРАСОТЫ ---
st.markdown("""
<style>
    .stApp { background-color: #121212; }
    h1, h2, h3 { color: #ffffff !important; font-family: 'Roboto', sans-serif; }
    .stat-box { background-color: #1e1e1e; padding: 10px; border-radius: 5px; border: 1px solid #333; }
    .stat-value { font-size: 24px; font-weight: bold; color: #E63946; }
    .stat-label { font-size: 12px; color: #aaaaaa; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ ELITE PLAYER PROFILE")

# --- 1. ЗАГРУЗКА ДАННЫХ ---
st.sidebar.header("Scouting Settings")
comps = get_competitions()
comp_name = st.sidebar.selectbox("Competition", comps['competition_name'].unique())
comp_id = comps[comps['competition_name'] == comp_name]['competition_id'].values[0]

seasons = comps[comps['competition_name'] == comp_name]
season_name = st.sidebar.selectbox("Season", seasons['season_name'].unique())
season_id = seasons[seasons['season_name'] == season_name]['season_id'].values[0]

matches = get_matches(comp_id, season_id)
# Фильтр матча не нужен для "сезонной" статистики, но мы берем матч для примера или агрегации
match_list = matches['home_team'] + " vs " + matches['away_team']
selected_match = st.sidebar.selectbox("Select Match (creates profile for players in this game)", match_list)
match_id = matches[match_list == selected_match]['match_id'].values[0]

with st.spinner('Scraping advanced data...'):
    events = get_events(match_id)

# --- 2. РАСЧЕТ МЕТРИК (КАК НА ФОТО) ---
def calculate_elite_stats(player_name, df):
    p_df = df[df['player'] == player_name].copy()
    if p_df.empty: return [0]*15

    # 1. Shots
    shots = len(p_df[p_df['type'] == 'Shot'])
    
    # 2. Non-penalty Goals
    np_goals = len(p_df[(p_df['shot_outcome'] == 'Goal') & (p_df['shot_type'] != 'Penalty')])
    
    # 3. Non-penalty xG
    npxg = p_df[p_df['shot_type'] != 'Penalty']['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in p_df.columns else 0
    
    # 4. Passes into Final Third
    # Логика: пас начался до 80м, закончился после 80м
    passes = p_df[p_df['type'] == 'Pass']
    completed = passes[passes['pass_outcome'].isna()]
    final_third_passes = 0
    if not completed.empty and 'pass_end_location' in completed.columns:
        final_third_passes = len(completed[completed.apply(lambda x: x['x'] < 80 and x['pass_end_location'][0] >= 80 if isinstance(x['pass_end_location'], list) else False, axis=1)])
    
    # 5. Passes into Box
    box_passes = 0
    if not completed.empty:
        box_passes = len(completed[completed['pass_end_location'].apply(lambda x: x[0] >= 102 and 18 <= x[1] <= 62 if isinstance(x, list) else False)])
    
    # 6. xA (Expected Assists)
    xa = p_df['pass_shot_assist'].sum() if 'pass_shot_assist' in p_df.columns else 0
    
    # 7. SCA (Shot Creating Actions)
    sca = len(p_df.get('pass_shot_assist', pd.Series(0)) == True) + \
          len(p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')])
          
    # 8. Successful Dribbles
    dribbles = len(p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')])
    
    # 9. Dribble Success %
    total_dribbles = len(p_df[p_df['type'] == 'Dribble'])
    dribble_pct = (dribbles / total_dribbles * 100) if total_dribbles > 0 else 0
    
    # 10. Carries into Final Third
    carries = p_df[p_df['type'] == 'Carry']
    carries_ft = 0
    if not carries.empty and 'carry_end_location' in carries.columns:
        carries_ft = len(carries[carries.apply(lambda x: x['x'] < 80 and x['carry_end_location'][0] >= 80 if isinstance(x['carry_end_location'], list) else False, axis=1)])

    # 11. Carries into Box
    carries_box = 0
    if not carries.empty:
        carries_box = len(carries[carries['carry_end_location'].apply(lambda x: x[0] >= 102 and 18 <= x[1] <= 62 if isinstance(x, list) else False)])
        
    # 12. Progressive Passes Received
    # Это сложно без контекста всех пасов, возьмем Ball Receipt в финальной трети
    prog_rec = len(p_df[(p_df['type'] == 'Ball Receipt*') & (p_df['x'] > 80)])
    
    # 13. Progressions (Passes + Carries into FT)
    progressions = final_third_passes + carries_ft
    
    # 14. Pressures (PAdj сложно, берем просто Pressures)
    pressures = len(p_df[p_df['type'] == 'Pressure'])
    
    # 15. Turnovers (Dispossessed + Miscontrols)
    turnovers = len(p_df[p_df['type'].isin(['Dispossessed', 'Miscontrol'])])

    return [shots, np_goals, round(npxg, 2), final_third_passes, box_passes, round(xa, 2), sca, 
            dribbles, round(dribble_pct, 1), carries_ft, carries_box, prog_rec, progressions, pressures, turnovers]

# Параметры как на фото
params = [
    "Shots", "Non-penalty goals", "npxG", "Passes into final third", "Passes into box", "xA", "Shot-creating actions",
    "Successful dribbles", "Dribble Success %", "Carries into final third", "Carries into box", "Prog. passes received",
    "Progressions", "Pressures", "Turnovers"
]

# --- 3. ИНТЕРФЕЙС ---
all_players = sorted(events['player'].dropna().unique())
player = st.selectbox("Select Player", all_players)

values = calculate_elite_stats(player, events)

# ЭТАЛОНЫ (Для расчета "процентилей" на глаз)
# Мы берем эти цифры как "100-й перцентиль" для одного матча.
# Для сезона цифры были бы другими (в среднем за 90 мин).
max_ranges = [
    6, 2, 1.5, 10, 5, 1.0, 10,
    8, 100, 8, 5, 15,
    15, 30, 8
]
# Для Turnovers чем МЕНЬШЕ, тем ЛУЧШЕ, поэтому инвертируем логику визуально в голове
# Но PyPizza требует min/max.

# --- 4. VISUALIZATION (Split Columns) ---
col_graph, col_table = st.columns([2, 1])

with col_graph:
    # Шрифты
    font_normal = FontProperties(family='sans-serif', weight='normal')
    font_bold = FontProperties(family='sans-serif', weight='bold')

    # Цвета (Как на фото: Красный, Темный фон)
    slice_colors = ["#D70232"] * 7 + ["#D70232"] * 6 + ["#1A1A1A"] * 2 # Последние 2 темнее (или другой цвет)
    # На фото Turnovers - это "плохо", выделим черным
    slice_colors[-1] = "#1A1A1A" # Turnover
    slice_colors[-2] = "#D70232" # Pressure
    
    text_colors = ["#F2F2F2"] * 15

    # Создаем Пиццу
    baker = PyPizza(
        params=params,
        min_range=[0]*15,
        max_range=max_ranges,
        background_color="#121212", # Темный фон
        straight_line_color="#333333", # Линии сетки
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
        blank_alpha=0.2, # Прозрачность незаполненного
        kwargs_slices=dict(edgecolor="#121212", zorder=2, linewidth=2), # Разделители
        kwargs_params=dict(color="#aaaaaa", fontsize=9, fontproperties=font_normal, va="center"),
        kwargs_values=dict(color="#ffffff", fontsize=11, fontproperties=font_bold, zorder=3,
                           bbox=dict(edgecolor="#D70232", facecolor="#D70232", boxstyle="round,pad=0.2", lw=1))
    )
    
    # Тексты
    fig.text(0.515, 0.97, f"{player}", size=24, ha="center", fontproperties=font_bold, color="#ffffff")
    fig.text(0.515, 0.93, f"{selected_match}", size=12, ha="center", fontproperties=font_normal, color="#aaaaaa")
    
    st.pyplot(fig)

with col_table:
    st.markdown("### 📊 Player Stats")
    st.markdown("<div style='background-color: #1e1e1e; padding: 15px; border-radius: 10px;'>", unsafe_allow_html=True)
    
    # Создаем красивую таблицу вручную
    for i in range(len(params)):
        # Считаем "виртуальный процентиль" (просто % заполнения от максимума)
        percentile = int((values[i] / max_ranges[i]) * 100)
        if percentile > 99: percentile = 99
        
        # Цвет процентиля
        p_color = "#D70232" if percentile > 70 else "#aaaaaa"
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #333; padding: 8px 0;">
            <span style="color: #ddd; font-size: 14px;">{i+1}: {params[i]}</span>
            <div style="text-align: right;">
                <span style="color: #fff; font-weight: bold; font-size: 16px;">{values[i]}</span>
                <span style="color: {p_color}; font-size: 12px; margin-left: 5px;">({percentile})</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
    st.caption("Data: StatsBomb Open Data. Percentiles are simulated based on match maximums.")
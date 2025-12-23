import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from statsbombpy import sb
import os

# --- CONFIG & STYLES ---
st.set_page_config(page_title="Deep Dive Metrics", layout="wide", page_icon="🧬")

st.markdown("""
<style>
    .stApp { background-color: #0e0e0e; }
    h1, h2, h3 { color: #00ff87 !important; font-family: 'Consolas', monospace; }
    .metric-container {
        border: 1px solid #333;
        background: #111;
        padding: 20px;
        border-radius: 10px;
    }
    .highlight { color: #00ff87; font-weight: bold; }
    .stProgress > div > div > div > div { background-color: #00ff87; }
</style>
""", unsafe_allow_html=True)

st.title("🧬 DEEP METRICS: MONEYBALL LEVEL")
st.caption("Вычисляем xG Chain, xG Buildup и PPDA из сырых событий.")

# --- ENGINE: ТУРБО ЗАГРУЗКА ---
@st.cache_data(show_spinner=False)
def load_match_deep(match_id):
    # Нам нужны 360-degree data если есть, но в open data их мало.
    # Берем обычные события, но вытаскиваем ВСЁ.
    events = sb.events(match_id=match_id)
    
    # Фикс координат
    if 'location' in events.columns:
        events['x'] = events['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
        events['y'] = events['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
    
    return events

# --- 1. АЛГОРИТМ xG CHAIN ---
def calculate_xg_chain(df):
    # xG Chain: Присваиваем xG удара ВСЕМ игрокам, участвовавшим во владении до удара.
    
    # 1. Оставляем только события с владением (pass, carry, shot, dribble)
    poss_actions = ['Pass', 'Carry', 'Dribble', 'Shot']
    df_poss = df[df['type'].isin(poss_actions)].copy()
    
    # 2. Находим удары с xG > 0
    shots = df[df['type'] == 'Shot'].dropna(subset=['shot_statsbomb_xg'])
    
    # Создаем словарь: {possession_id: xG}
    # possession - это ID конкретной атаки в данных StatsBomb
    poss_xg_map = shots.set_index('possession')['shot_statsbomb_xg'].to_dict()
    
    # 3. Присваиваем xG каждому событию на основе possession_id
    df_poss['possession_xg'] = df_poss['possession'].map(poss_xg_map).fillna(0)
    
    # 4. xG Buildup: То же самое, но исключая тех, кто бил или отдавал последний пас
    # Это сложно отфильтровать идеально, поэтому сделаем упрощенный Chain
    
    # Группируем по игрокам
    xg_chain = df_poss.groupby(['player', 'team'])['possession_xg'].sum().reset_index()
    xg_chain = xg_chain.rename(columns={'possession_xg': 'xG Chain'})
    
    return xg_chain.sort_values('xG Chain', ascending=False)

# --- 2. АЛГОРИТМ PPDA (INTENSITY) ---
def calculate_ppda(df, team_name):
    # PPDA = (Оборонительные действия в атакующей трети) / (Пасы соперника в их защитной трети)
    # Чем НИЖЕ число, тем ИНТЕНСИВНЕЕ прессинг.
    
    # Соперник
    opponent = df[df['team'] != team_name]['team'].iloc[0]
    
    # 1. Оборонительные действия команды (Tackle, Interception, Foul, Challenge)
    # В зоне атаки (x > 60 для нас)
    def_actions = ['Pressure', 'Duel', 'Interception', 'Block', 'Foul Committed']
    our_defense = df[
        (df['team'] == team_name) & 
        (df['type'].isin(def_actions)) & 
        (df['x'] > 60) # На чужой половине
    ]
    def_count = len(our_defense)
    
    # 2. Пасы соперника (на их половине, x < 60 для них)
    # Важно: координаты соперника перевернуты? В StatsBomb обычно все играют слева направо в сырых данных,
    # но 'x' всегда 0-120. Если соперник делает пас на своей половине, это x < 60 (если мы не нормализовали).
    # StatsBomb хранит координаты относительно атакующей команды.
    # Значит пас соперника на ЕГО половине - это x < 60.
    opp_passes = df[
        (df['team'] == opponent) & 
        (df['type'] == 'Pass') & 
        (df['x'] < 60)
    ]
    pass_count = len(opp_passes)
    
    ppda = pass_count / def_count if def_count > 0 else 0
    return ppda, def_count, pass_count

# --- ИНТЕРФЕЙС ---

# Выбор матча
matches = sb.matches(competition_id=11, season_id=27) # Ла Лига 15/16
match_list = matches['home_team'] + " vs " + matches['away_team']
selected_match = st.sidebar.selectbox("Выберите матч для вскрытия", match_list)
match_id = matches[match_list == selected_match]['match_id'].values[0]

with st.spinner("Взламываем тактику матча..."):
    events = load_match_deep(match_id)

home_team = matches[matches['match_id'] == match_id]['home_team'].values[0]
away_team = matches[matches['match_id'] == match_id]['away_team'].values[0]

# === 1. xG CHAIN ANALYSIS ===
st.header("1. xG Chain (Вклад в атаку)")
st.caption("Кто создает моменты, но остается в тени? (Сумма xG атак, в которых участвовал игрок)")

chain_stats = calculate_xg_chain(events)

c1, c2 = st.columns(2)
with c1:
    st.subheader(f"{home_team}")
    st.dataframe(chain_stats[chain_stats['team'] == home_team].head(10)[['player', 'xG Chain']], use_container_width=True)

with c2:
    st.subheader(f"{away_team}")
    st.dataframe(chain_stats[chain_stats['team'] == away_team].head(10)[['player', 'xG Chain']], use_container_width=True)

# === 2. PPDA (PRESSING) ===
st.markdown("---")
st.header("2. PPDA & Pressing Intensity")
st.caption("Passes Allowed Per Defensive Action. Меньше = Лучше прессинг.")

ppda_home, def_h, pass_h = calculate_ppda(events, home_team)
ppda_away, def_a, pass_a = calculate_ppda(events, away_team)

k1, k2 = st.columns(2)
with k1:
    st.metric(f"PPDA {home_team}", f"{ppda_home:.2f}", help=f"Оборонительных действий: {def_h}, Пасов соперника: {pass_h}")
    # Визуализация прессинга
    st.write(f"Карта прессинга {home_team}:")
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e0e0e', line_color='#444')
    fig, ax = pitch.draw(figsize=(8, 5))
    press_ev = events[(events['team'] == home_team) & (events['type'] == 'Pressure')]
    pitch.kdeplot(press_ev.x, press_ev.y, ax=ax, cmap='Greens', fill=True, alpha=0.6)
    st.pyplot(fig)

with k2:
    st.metric(f"PPDA {away_team}", f"{ppda_away:.2f}", help=f"Оборонительных действий: {def_a}, Пасов соперника: {pass_a}")
    st.write(f"Карта прессинга {away_team}:")
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#0e0e0e', line_color='#444')
    fig, ax = pitch.draw(figsize=(8, 5))
    press_ev = events[(events['team'] == away_team) & (events['type'] == 'Pressure')]
    pitch.kdeplot(press_ev.x, press_ev.y, ax=ax, cmap='Reds', fill=True, alpha=0.6)
    st.pyplot(fig)

# === 3. SHOT FREEZE FRAMES (GLAZA VRATARYA) ===
st.markdown("---")
st.header("3. Shot Freeze Frames")
st.caption("Расположение всех игроков в момент удара. Данные, которые обычно скрыты в JSON.")

# Находим удары, где есть freeze_frame
shots_with_freeze = events[events['shot_freeze_frame'].notna()]
goals_with_freeze = shots_with_freeze[shots_with_freeze['shot_outcome'] == 'Goal']

if not goals_with_freeze.empty:
    # Выбор гола
    goal_opts = [f"{row['minute']}' - {row['player']} (xG: {row['shot_statsbomb_xg']:.2f})" for i, row in goals_with_freeze.iterrows()]
    selected_goal_str = st.selectbox("Выберите гол для анализа:", goal_opts)
    
    # Получаем индекс выбранного гола
    sel_idx = goal_opts.index(selected_goal_str)
    shot_event = goals_with_freeze.iloc[sel_idx]
    
    # Достаем Freeze Frame
    frame = pd.DataFrame(shot_event['shot_freeze_frame'])
    # location в frame это список [x, y], разбиваем
    frame['x'] = frame['location'].apply(lambda x: x[0])
    frame['y'] = frame['location'].apply(lambda x: x[1])
    
    # Рисуем
    pitch = VerticalPitch(pitch_type='statsbomb', half=True, pitch_color='#0e0e0e', line_color='#444')
    fig, ax = pitch.draw(figsize=(10, 8))
    
    # 1. Рисуем всех игроков из фрейма
    # Teammates
    teammates = frame[frame['teammate'] == True]
    pitch.scatter(teammates.x, teammates.y, ax=ax, c='#00b4d8', s=100, label='Teammate')
    
    # Opponents
    opponents = frame[frame['teammate'] == False]
    # Находим вратаря (обычно он 'Keeper', но в freeze frame это позиция)
    keeper = opponents[opponents['position.name'] == 'Goalkeeper']
    field_opp = opponents[opponents['position.name'] != 'Goalkeeper']
    
    pitch.scatter(field_opp.x, field_opp.y, ax=ax, c='#ff006e', s=100, label='Opponent')
    pitch.scatter(keeper.x, keeper.y, ax=ax, c='#ffbe0b', s=150, marker='s', label='Goalkeeper')
    
    # 2. Рисуем бьющего (shot_event)
    pitch.scatter(shot_event.x, shot_event.y, ax=ax, c='white', s=200, marker='football', label='Shooter')
    
    # 3. Линия удара
    pitch.lines(shot_event.x, shot_event.y, 120, 40, color='white', linestyle='--', alpha=0.5, ax=ax)
    # Треугольник видимости (Goal Cone) - упрощенно
    pitch.polygon([[shot_event.x, shot_event.y], [120, 36], [120, 44]], color='white', alpha=0.1, ax=ax)
    
    ax.legend(facecolor='#111', labelcolor='white')
    ax.set_title(f"Freeze Frame: {shot_event['player']} vs {shot_event['opponent']}", color='white', fontsize=15)
    
    st.pyplot(fig)
else:
    st.info("В этом матче нет данных Freeze Frame для голов (обычно они есть в новых сезонах).")
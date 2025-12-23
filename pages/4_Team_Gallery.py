import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch, Pitch
from matplotlib.colors import LinearSegmentedColormap
from utils.data import get_competitions, get_matches, get_events

st.set_page_config(page_title="Team Gallery", layout="wide")

# --- ВОДЯНОЙ ЗНАК (By Novvi) ---
def add_watermark(fig):
    fig.text(0.5, 0.5, "By Novvi", fontsize=50, color='white', 
             ha='center', va='center', alpha=0.08, rotation=30, weight='bold')

# --- СТИЛИ ---
st.markdown("""
    <style>
    h1 {color: #00e676; font-family: 'Arial Black';}
    .stApp {background-color: #1a1a1a;}
    </style>
    """, unsafe_allow_html=True)

st.title("🎨 Визуальная Галерея Матча")
st.markdown("### Продвинутые тактические карты")

# --- 1. ВЫБОР МАТЧА ---
st.sidebar.header("Настройки")
comps = get_competitions()
comp_name = st.sidebar.selectbox("Турнир", comps['competition_name'].unique())
comp_id = comps[comps['competition_name'] == comp_name]['competition_id'].values[0]

seasons = comps[comps['competition_name'] == comp_name]
season_name = st.sidebar.selectbox("Сезон", seasons['season_name'].unique())
season_id = seasons[seasons['season_name'] == season_name]['season_id'].values[0]

matches = get_matches(comp_id, season_id)
match_list = matches['home_team'] + " vs " + matches['away_team']
selected_match = st.sidebar.selectbox("Матч", match_list)
match_id = matches[match_list == selected_match]['match_id'].values[0]

with st.spinner('Рисуем тактику...'):
    events = get_events(match_id)

# Выбор команды
teams = events['team'].unique()
selected_team = st.sidebar.radio("Выберите команду для анализа", teams)

# Фильтруем данные по команде
team_events = events[events['team'] == selected_team]

# --- ТАБЫ (ВКЛАДКИ) ---
tab1, tab2, tab3 = st.tabs(["⚽ xG Shot Map", "🕸️ Passing Network", "🛡️ Defense Map"])

# ==========================================
# 1. xG SHOT MAP (Карта ударов)
# ==========================================
with tab1:
    st.subheader(f"Карта ударов (xG): {selected_team}")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Берем удары
        shots = team_events[team_events['type'] == 'Shot'].copy()
        
        # Если нет xG, ставим заглушку
        if 'shot_statsbomb_xg' not in shots.columns:
            shots['shot_statsbomb_xg'] = 0.1

        pitch = VerticalPitch(pitch_type='statsbomb', half=True, goal_type='box', 
                              line_color='white', pitch_color='#1a1a1a')
        fig, ax = pitch.draw(figsize=(10, 8))
        
        # 1. Рисуем ГОЛЫ (Зеленые)
        goals = shots[shots['shot_outcome'] == 'Goal']
        pitch.scatter(goals.x, goals.y, ax=ax, 
                      s=goals['shot_statsbomb_xg'] * 900 + 100, # Размер зависит от xG
                      edgecolors='#00e676', c='None', hatch='///', marker='o', label='Гол')
        
        # 2. Рисуем ПРОМАХИ/СЕЙВЫ (Красные/Серые)
        no_goals = shots[shots['shot_outcome'] != 'Goal']
        pitch.scatter(no_goals.x, no_goals.y, ax=ax, 
                      s=no_goals['shot_statsbomb_xg'] * 900 + 100, 
                      c='#ff5252', alpha=0.5, edgecolors='white', label='Удар')

        add_watermark(fig)
        ax.legend(facecolor='#1a1a1a', edgecolor='white', labelcolor='white', loc='lower right')
        st.pyplot(fig)
    
    with col2:
        st.write("#### Легенда")
        st.info("""
        - **Размер круга** = xG (Опасность момента). Чем больше круг, тем убойнее позиция.
        - **Штриховка** = Гол.
        - **Красный** = Сейв или Промах.
        """)
        st.metric("Всего ударов", len(shots))
        st.metric("xG (Ожидаемые голы)", round(shots['shot_statsbomb_xg'].sum(), 2))

# ==========================================
# 2. PASSING NETWORK (Средние позиции)
# ==========================================
with tab2:
    st.subheader(f"Средние позиции и Пасы: {selected_team}")
    
    # Считаем средние позиции
    passes = team_events[team_events['type'] == 'Pass']
    successful = passes[passes['pass_outcome'].isna()]
    
    # Группируем по игрокам (берем среднее X и Y)
    avg_loc = successful.groupby('player').agg({'x': ['mean'], 'y': ['mean', 'count']})
    avg_loc.columns = ['x', 'y', 'count']
    
    # Оставляем только тех, кто сделал больше 10 пасов (чтобы убрать замены)
    avg_loc = avg_loc[avg_loc['count'] > 10]
    
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1a1a1a', line_color='#c7d5cc')
    fig, ax = pitch.draw(figsize=(12, 8))
    
    # Рисуем связи (Стрелки пасов) - упрощенно: просто плотность пасов
    # kdeplot для красоты "потока" пасов
    pitch.kdeplot(successful.x, successful.y, ax=ax, levels=50, shade=True, 
                  cmap='magma', alpha=0.4, thresh=0.05)
    
    # Рисуем точки игроков
    pitch.scatter(avg_loc.x, avg_loc.y, ax=ax, s=avg_loc['count']*10, 
                  c='#00e676', edgecolors='black', linewidth=2, zorder=2)
    
    # Подписываем игроков
    for name, row in avg_loc.iterrows():
        # Берем только фамилию, чтобы не загромождать
        short_name = name.split(" ")[-1]
        pitch.annotate(short_name, xy=(row.x, row.y), ax=ax, 
                       color='white', va='center', ha='center', size=10, weight='bold', zorder=3)
    
    add_watermark(fig)
    st.pyplot(fig)
    st.caption("🔥 Фон (Heatmap) показывает зоны активного владения мячом. Точки — средние позиции игроков.")

# ==========================================
# 3. DEFENSE MAP (Оборона)
# ==========================================
with tab3:
    st.subheader(f"Карта оборонительных действий: {selected_team}")
    
    # Отборы, перехваты, блоки
    def_actions = team_events[team_events['type'].isin(['Pressure', 'Duel', 'Interception', 'Block', 'Ball Recovery'])]
    
    col_d1, col_d2 = st.columns([3, 1])
    
    with col_d1:
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#1a1a1a', line_color='white')
        fig, ax = pitch.draw(figsize=(12, 8))
        
        # Прессинг (желтый)
        pressures = def_actions[def_actions['type'] == 'Pressure']
        pitch.scatter(pressures.x, pressures.y, ax=ax, s=50, c='yellow', alpha=0.6, label='Прессинг')
        
        # Отборы/Дуэли (красный)
        tackles = def_actions[def_actions['type'].isin(['Duel', 'Tackle'])]
        pitch.scatter(tackles.x, tackles.y, ax=ax, s=100, marker='x', c='red', alpha=0.8, label='Отбор/Дуэль')
        
        # Перехваты (синий)
        interceptions = def_actions[def_actions['type'] == 'Interception']
        pitch.scatter(interceptions.x, interceptions.y, ax=ax, s=80, marker='D', c='#29b6f6', edgecolors='white', label='Перехват')
        
        ax.legend(facecolor='#1a1a1a', edgecolor='white', labelcolor='white', loc='upper left')
        add_watermark(fig)
        st.pyplot(fig)
        
    with col_d2:
        st.write("#### Статистика обороны")
        st.metric("Прессинг действий", len(pressures))
        st.metric("Вступления в отбор", len(tackles))
        st.metric("Перехваты", len(interceptions))
        
        # Рассчитываем среднюю высоту обороны (средний X всех действий)
        avg_def_height = def_actions['x'].mean()
        st.metric("Средняя линия обороны (м)", f"{round(avg_def_height, 1)} м")
        st.progress(int(avg_def_height))
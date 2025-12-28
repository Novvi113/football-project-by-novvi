import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from statsbombpy import sb
import os

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Minimalist Tactical Art", layout="wide", page_icon="🎨")

# --- СТИЛЬ (СВЕТЛЫЙ ДЛЯ КОНТРАСТА) ---
# Мы делаем страницу светлой, чтобы график смотрелся органично, как на бумаге
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #000000; }
    h1, h2, h3 { color: #000000 !important; font-family: 'Times New Roman', serif; }
    .stSelectbox > div > div { background-color: #f0f0f0; color: black; }
</style>
""", unsafe_allow_html=True)

st.title("The Art of Passing")
st.caption("Minimalist visualization of completed passes into the box.")

# --- ТУРБО-ДВИЖОК (ПОВТОРЯЕМ ДЛЯ СТАБИЛЬНОСТИ) ---
@st.cache_data(show_spinner=False)
def get_match_data(match_id):
    ev = sb.events(match_id=match_id)
    if 'location' in ev.columns:
        ev['x'] = ev['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
        ev['y'] = ev['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
    if 'pass_end_location' in ev.columns:
        ev['end_x'] = ev['pass_end_location'].apply(lambda x: x[0] if isinstance(x, list) else None)
        ev['end_y'] = ev['pass_end_location'].apply(lambda x: x[1] if isinstance(x, list) else None)
    return ev

# --- ВЫБОР МАТЧА ---
st.sidebar.header("Settings")
# Ла Лига 20/21 (Последний сезон Месси) - там много красивых пасов
matches = sb.matches(competition_id=11, season_id=90) 
match_list = matches['home_team'] + " vs " + matches['away_team']
selected_match = st.sidebar.selectbox("Select Match", match_list)
match_id = matches[match_list == selected_match]['match_id'].values[0]

# Загрузка
with st.spinner("Drawing canvas..."):
    events = get_match_data(match_id)

# Выбор команды и игрока
team = st.sidebar.radio("Team", [matches[matches['match_id']==match_id]['home_team'].values[0], 
                                 matches[matches['match_id']==match_id]['away_team'].values[0]])

players = sorted(events[events['team'] == team]['player'].dropna().unique())
# Пытаемся найти Месси по умолчанию
default_idx = players.index("Lionel Andrés Messi Cuccittini") if "Lionel Andrés Messi Cuccittini" in players else 0
player = st.sidebar.selectbox("Player", players, index=default_idx)

# --- ФИЛЬТР ПАСОВ В ШТРАФНУЮ (BOX PASSES) ---
# Логика: 
# 1. Это пас.
# 2. Он точный (outcome is NaN).
# 3. Конец паса (end_x, end_y) находится внутри штрафной.
# Координаты штрафной StatsBomb: x >= 102, y от 18 до 62.

mask_pass = (events['player'] == player) & (events['type'] == 'Pass') & (events['pass_outcome'].isna())
df_pass = events[mask_pass].copy()

# Фильтруем попадание в штрафную
# Условие: Конец паса X >= 102 И (Y >= 18 И Y <= 62)
box_passes = df_pass[
    (df_pass['end_x'] >= 102) & 
    (df_pass['end_y'] >= 18) & 
    (df_pass['end_y'] <= 62)
]

# --- РИСУЕМ (MINIMALIST STYLE) ---
st.markdown("---")

col1, col2 = st.columns([3, 1])

with col1:
    # 1. Создаем поле: Белое, вертикальное, половина поля
    pitch = VerticalPitch(
        pitch_type='statsbomb',
        half=True,              # Только половина поля (как на фото)
        pitch_color='white',    # Белый фон
        line_color='black',     # Черные линии
        linewidth=1.5,          # Тонкие линии
        spot_scale=0.0          # Убираем жирные точки пенальти
    )
    
    fig, ax = pitch.draw(figsize=(10, 12))
    
    # 2. Рисуем стрелки
    if not box_passes.empty:
        pitch.arrows(
            box_passes.x, box_passes.y,
            box_passes.end_x, box_passes.end_y,
            ax=ax,
            width=2,            # Толщина стрелки (тонкая)
            headwidth=4,        # Ширина наконечника (аккуратная)
            headlength=4,       # Длина наконечника
            color='black',      # Цвет стрелок
            alpha=0.9,          # Непрозрачность
            zorder=2
        )
        
        # 3. Добавляем точки начала (для красоты, маленькие)
        pitch.scatter(
            box_passes.x, box_passes.y,
            ax=ax,
            s=20, 
            c='black', 
            marker='o'
        )
        
        # ЗАГОЛОВОК ПРЯМО НА ГРАФИКЕ (Как в R)
        ax.text(40, 123, f"{player}", fontsize=20, ha='center', va='bottom', fontfamily='serif', color='black')
        ax.text(40, 121, f"Completed Box Passes ({len(box_passes)})", fontsize=14, ha='center', va='bottom', fontfamily='serif', color='gray')
        
    else:
        ax.text(40, 90, "No completed box passes in this match.", ha='center', fontsize=15, color='gray')

    st.pyplot(fig)

with col2:
    st.markdown("### 📜 Details")
    st.write(f"**Player:** {player}")
    st.write(f"**Match:** {selected_match}")
    st.metric("Box Passes", len(box_passes))
    
    if not box_passes.empty:
        st.write("Match Minute:")
        st.write(box_passes['minute'].tolist())
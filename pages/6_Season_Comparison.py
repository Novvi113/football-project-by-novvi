import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Radar, FontManager, grid
from statsbombpy import sb
import os

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Pro Comparison", layout="wide", page_icon="⚖️")

# --- СТИЛИ (DARK & NEON) ---
st.markdown("""
<style>
    .stApp { background-color: #121212; }
    h1, h2, h3 { color: #fff !important; font-family: 'Arial', sans-serif; font-weight: bold; }
    div[data-testid="stSelectbox"] > div > div { background-color: #1e1e1e; color: white; }
    .stDataFrame { border: 1px solid #333; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ ELITE PLAYER COMPARISON")
st.caption("Сравнение показателей Per 90 (в среднем за матч).")

# ==========================================
# 1. ТУРБО-ДВИЖОК (ЗАГРУЗКА ДАННЫХ)
# ==========================================
@st.cache_data(show_spinner=False)
def get_matches_data(comp_id, season_id):
    return sb.matches(competition_id=comp_id, season_id=season_id)

def load_data_turbo(season_id):
    filename = f"season_{season_id}_data.csv"
    
    # 1. Если файл есть - читаем мгновенно
    if os.path.exists(filename):
        return pd.read_csv(filename, low_memory=False)
    
    # 2. Если нет - качаем (займет минуту)
    st.toast("⏳ Скачиваем сезон для анализа...", icon="💾")
    
    # Качаем матчи Ла Лиги (ID 11)
    matches = get_matches_data(11, season_id)
    # Фильтруем Барсу (можно убрать фильтр, если хочешь всю лигу, но будет дольше)
    team_matches = matches[(matches['home_team'] == 'Barcelona') | (matches['away_team'] == 'Barcelona')]
    ids = team_matches['match_id'].tolist()
    
    all_events = []
    bar = st.progress(0, text="Обработка матчей...")
    
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
        # Фикс координат для графиков
        if 'location' in df.columns:
            df['x'] = df['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
            df['y'] = df['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
        
        # Сохраняем на диск
        df.to_csv(filename, index=False)
        return df
        
    return pd.DataFrame()

# ==========================================
# 2. МАТЕМАТИКА (PER 90)
# ==========================================
def calculate_stats(df, player_name):
    p_df = df[df['player'] == player_name]
    if p_df.empty: return None
    
    # Считаем сыгранные матчи и коэффициент 90 минут
    matches = p_df['match_id'].nunique()
    # Грубая оценка минут (Матчи * 90). Для идеальной точности нужен парсинг замен.
    scale = 1.0 / matches if matches > 0 else 0
    
    # Сбор метрик
    stats = {}
    stats['Goals'] = len(p_df[p_df['shot_outcome'] == 'Goal']) * scale
    stats['Assists'] = (len(p_df[p_df['pass_goal_assist'] == True]) if 'pass_goal_assist' in p_df.columns else 0) * scale
    stats['Shots'] = len(p_df[p_df['type'] == 'Shot']) * scale
    stats['Key Passes'] = (len(p_df[p_df.get('pass_shot_assist', pd.Series(0)) == True])) * scale
    stats['Dribbles'] = len(p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')]) * scale
    stats['xG'] = (p_df['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in p_df.columns else 0) * scale
    
    # Доп метрики
    stats['Ball Recovery'] = len(p_df[p_df['type'] == 'Ball Recovery']) * scale
    stats['Interceptions'] = len(p_df[p_df['type'] == 'Interception']) * scale
    
    return stats

# ==========================================
# 3. ИНТЕРФЕЙС
# ==========================================

# Выбор сезона
season_map = {
    "2014/15 (MSN Treble)": 26,
    "2015/16 (League Win)": 27,
    "2010/11 (Prime Pep)": 21,
    "2011/12 (Messi 50 goals)": 22
}
s_name = st.sidebar.selectbox("Выберите Сезон", list(season_map.keys()))
s_id = season_map[s_name]

# Загрузка
df = load_data_turbo(s_id)

if not df.empty:
    # Фильтр игроков (>500 событий, чтобы убрать запасных)
    counts = df['player'].value_counts()
    valid_players = counts[counts > 300].index.tolist()
    valid_players = sorted(valid_players)
    
    # Выбор игроков
    c1, c2 = st.columns(2)
    
    # Автовыбор (Месси и Суарес/Неймар)
    def_idx1 = valid_players.index("Lionel Andrés Messi Cuccittini") if "Lionel Andrés Messi Cuccittini" in valid_players else 0
    def_idx2 = valid_players.index("Neymar da Silva Santos Junior") if "Neymar da Silva Santos Junior" in valid_players else 1
    
    p1 = c1.selectbox("Игрок 1 (Синий)", valid_players, index=def_idx1)
    p2 = c2.selectbox("Игрок 2 (Розовый)", valid_players, index=def_idx2)
    
    if st.button("ПОСТРОИТЬ СРАВНЕНИЕ 🚀"):
        
        # Считаем
        s1 = calculate_stats(df, p1)
        s2 = calculate_stats(df, p2)
        
        # Настраиваем параметры для радара
        # Выбираем атакующие метрики
        params = ['Goals', 'xG', 'Shots', 'Assists', 'Key Passes', 'Dribbles']
        
        values1 = [s1[p] for p in params]
        values2 = [s2[p] for p in params]
        
        # Настраиваем границы (Min/Max) вручную, чтобы график был красивым
        # [Goals, xG, Shots, Assists, Key Passes, Dribbles]
        min_range = [0, 0, 0, 0, 0, 0]
        max_range = [1.2, 1.2, 6.0, 0.8, 4.0, 6.0] 
        
        # --- РИСУЕМ РАДАР ---
        radar = Radar(params, min_range=min_range, max_range=max_range,
                      round_int=[False]*6, num_rings=4, ring_width=1, center_circle_radius=1)
        
        fig, ax = radar.setup_axis(figsize=(10, 10))
        
        # Заливка Игрок 1
        radar.draw_radar(values1, ax=ax, kwargs_radar={'facecolor': '#00b4d8', 'alpha': 0.6}, kwargs_rings={'edgecolor': '#555'})
        # Заливка Игрок 2
        radar.draw_radar(values2, ax=ax, kwargs_radar={'facecolor': '#ff006e', 'alpha': 0.5}, kwargs_rings={'edgecolor': '#555'})
        
        # Линии обводки
        radar.draw_range_labels(ax=ax, fontsize=10, color='#999')
        
        # --- ГЛАВНОЕ: ДОБАВЛЯЕМ ЦИФРЫ НА ГРАФИК ---
        # Мы проходимся по каждому углу радара и пишем число
        # vertices - это координаты углов
        vertices1 = radar.radar_polygon(values1).vertices
        vertices2 = radar.radar_polygon(values2).vertices
        
        # Пишем цифры Игрока 1 (Синий)
        for i, (x, y) in enumerate(vertices1):
            # Немного сдвигаем текст, чтобы не наезжал
            ax.text(x, y, f"{values1[i]:.2f}", color="cyan", fontsize=14, fontweight='bold', ha='center', va='center', 
                    bbox=dict(facecolor='#121212', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.2'))

        # Пишем цифры Игрока 2 (Розовый)
        for i, (x, y) in enumerate(vertices2):
            # Сдвигаем, если точки слишком близко (простая эвристика)
            shift = 0.1 if abs(values1[i] - values2[i]) < 0.5 else 0
            ax.text(x, y-shift, f"{values2[i]:.2f}", color="#ff006e", fontsize=14, fontweight='bold', ha='center', va='center',
                    bbox=dict(facecolor='#121212', edgecolor='none', alpha=0.7, boxstyle='round,pad=0.2'))

        # Легенда
        line1, = ax.plot([], [], color='#00b4d8', linewidth=4, label=p1)
        line2, = ax.plot([], [], color='#ff006e', linewidth=4, label=p2)
        ax.legend(handles=[line1, line2], loc='upper center', bbox_to_anchor=(0.5, 1.1), 
                  frameon=False, labelcolor='white', fontsize=14)
        
        # Фон
        fig.set_facecolor('#121212')
        ax.set_facecolor('#121212')
        
        col_chart, col_empty = st.columns([3, 1])
        with col_chart:
            st.pyplot(fig)
            
        # --- ТАБЛИЦА СРАВНЕНИЯ (HEATMAP) ---
        st.markdown("### 📊 Детальная статистика")
        
        # Создаем DataFrame
        comp_df = pd.DataFrame([values1, values2], columns=params, index=[p1, p2])
        
        # Функция для раскраски
        def highlight_winner(data):
            # Создаем пустую таблицу стилей
            styles = pd.DataFrame('', index=data.index, columns=data.columns)
            # Проходим по колонкам
            for col in data.columns:
                v1 = data.iloc[0][col]
                v2 = data.iloc[1][col]
                
                if v1 > v2:
                    styles.iloc[0][col] = 'background-color: #004d40; color: #00e676; font-weight: bold' # Зеленый для победителя
                    styles.iloc[1][col] = 'color: #ef5350' # Красный для проигравшего
                elif v2 > v1:
                    styles.iloc[0][col] = 'color: #ef5350'
                    styles.iloc[1][col] = 'background-color: #3e2723; color: #ff4081; font-weight: bold'
            return styles

        st.dataframe(comp_df.style.apply(highlight_winner, axis=None).format("{:.2f}"), use_container_width=True)

else:
    st.info("Загрузка данных...")
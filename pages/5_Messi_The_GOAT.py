import streamlit as st
import sys
import os

# Фикс путей (на всякий случай)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from statsbombpy import sb

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Messi Season Analysis", layout="wide", page_icon="👑")

# --- CSS СТИЛИ ---
st.markdown("""
<style>
    .stApp { background-color: #000000; }
    h1 { color: #D4AF37 !important; text-transform: uppercase; font-weight: 800; letter-spacing: 2px; }
    h2, h3, h4 { color: #f0f0f0 !important; }
    .metric-card {
        background: linear-gradient(135deg, #111, #222);
        border: 1px solid #D4AF37;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.15);
        margin-bottom: 10px;
    }
    .metric-big { font-size: 36px; font-weight: bold; color: #fff; text-shadow: 0 0 10px rgba(255,255,255,0.3); }
    .metric-small { font-size: 12px; color: #D4AF37; letter-spacing: 1px; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- ТУРБО-ДВИЖОК (С СОХРАНЕНИЕМ В CSV) ---
@st.cache_data(show_spinner=False)
def get_season_matches(competition_id, season_id):
    return sb.matches(competition_id=competition_id, season_id=season_id)

def load_full_season_turbo(competition_id, season_id, team_name="Barcelona"):
    # 1. Проверяем, есть ли уже файл на компьютере
    filename = f"season_{season_id}_data.csv"
    
    if os.path.exists(filename):
        st.toast(f"🚀 Загрузка сезона с диска (Мгновенно!)", icon="⚡")
        # Читаем CSV быстро
        df = pd.read_csv(filename, low_memory=False)
        return df
    
    # 2. Если файла нет - качаем (Долго, но один раз)
    st.toast("⏳ Первый запуск сезона... Скачиваем данные...", icon="🌍")
    
    matches = get_season_matches(competition_id, season_id)
    team_matches = matches[(matches['home_team'] == team_name) | (matches['away_team'] == team_name)]
    match_ids = team_matches['match_id'].tolist()
    
    all_events = []
    
    # Прогресс бар
    progress_bar = st.progress(0, text="Скачиваем матчи из StatsBomb...")
    total = len(match_ids)
    
    for i, m_id in enumerate(match_ids):
        try:
            ev = sb.events(match_id=m_id)
            ev['match_id'] = m_id
            # Добавляем дату, чтобы сортировать хронологически
            match_date = team_matches[team_matches['match_id'] == m_id]['match_date'].values[0]
            ev['match_date'] = match_date
            all_events.append(ev)
        except:
            pass
        # Обновляем бар
        progress_bar.progress(int(((i + 1) / total) * 100))
    
    progress_bar.empty()
    
    if all_events:
        full_df = pd.concat(all_events, ignore_index=True)
        
        # Исправляем координаты перед сохранением
        if 'location' in full_df.columns:
            full_df['x'] = full_df['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
            full_df['y'] = full_df['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
        
        # 3. СОХРАНЯЕМ В ФАЙЛ НА БУДУЩЕЕ!
        full_df.to_csv(filename, index=False)
        st.success(f"✅ Сезон сохранен! В следующий раз откроется за 1 секунду.")
        
        return full_df
        
    return pd.DataFrame()

def get_messi_stats(df):
    # Фильтр Месси (ID 5503)
    p_df = df[df['player_id'] == 5503].copy()
    if p_df.empty: return None

    # Метрики
    matches_played = p_df['match_id'].nunique()
    goals = len(p_df[p_df['shot_outcome'] == 'Goal'])
    assists = len(p_df[p_df['pass_goal_assist'] == True]) if 'pass_goal_assist' in p_df.columns else 0
    shots = len(p_df[p_df['type'] == 'Shot'])
    
    key_passes = 0
    if 'pass_shot_assist' in p_df.columns:
        key_passes = len(p_df[p_df['pass_shot_assist'] == True])
        
    dribbles = len(p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')])
    xg = p_df['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in p_df.columns else 0
    
    return {
        "Matches": matches_played, "Goals": goals, "Assists": assists,
        "Shots": shots, "Key Passes": key_passes, "Dribbles": dribbles,
        "xG": xg, "df": p_df
    }

# --- ИНТЕРФЕЙС ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b4/Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg", width=200)
st.sidebar.header("Season Selection")

season_options = {
    "2014/2015 (The Treble)": 26,
    "2010/2011 (Prime Pep)": 21,
    "2011/2012 (91 Goals Year)": 22,
    "2015/2016 (MSN Peak)": 27
}

s_name = st.sidebar.selectbox("Choose Era", list(season_options.keys()))
s_id = season_options[s_name]

# ЗАГРУЗКА (ТУРБО)
df = load_full_season_turbo(11, s_id, "Barcelona")

if not df.empty:
    data = get_messi_stats(df)
    
    if data:
        st.title(f"👑 LEO MESSI: {s_name.split('(')[0]}")
        
        # KPI
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.markdown(f"<div class='metric-card'><div class='metric-big'>{data['Matches']}</div><div class='metric-small'>Games</div></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-card'><div class='metric-big'>{data['Goals']}</div><div class='metric-small'>Goals</div></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-card'><div class='metric-big'>{data['Assists']}</div><div class='metric-small'>Assists</div></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='metric-card'><div class='metric-big'>{round(data['xG'], 1)}</div><div class='metric-small'>Total xG</div></div>", unsafe_allow_html=True)
        c5.markdown(f"<div class='metric-card'><div class='metric-big'>{data['Dribbles']}</div><div class='metric-small'>Dribbles</div></div>", unsafe_allow_html=True)
        c6.markdown(f"<div class='metric-card'><div class='metric-big'>{data['Key Passes']}</div><div class='metric-small'>Key Passes</div></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # ГРАФИКИ
        tab1, tab2 = st.tabs(["🎯 Shot Map & Hexbins", "📈 Goals vs xG Timeline"])
        
        messi_df = data['df']
        
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Shot Map (Size = xG)")
                pitch = VerticalPitch(pitch_type='statsbomb', half=True, pitch_color='#0e0e0e', line_color='#444')
                fig, ax = pitch.draw(figsize=(10, 10))
                
                shots = messi_df[messi_df['type'] == 'Shot']
                goals = shots[shots['shot_outcome'] == 'Goal']
                non_goals = shots[shots['shot_outcome'] != 'Goal']
                
                pitch.scatter(non_goals.x, non_goals.y, ax=ax, s=non_goals['shot_statsbomb_xg']*500+20, c='#333', alpha=0.6, edgecolors='#555')
                pitch.scatter(goals.x, goals.y, ax=ax, s=goals['shot_statsbomb_xg']*500+50, marker='*', c='#D4AF37', edgecolors='white', zorder=2)
                
                ax.set_title(f"Goals: {len(goals)} | xG: {round(data['xG'], 2)}", color='white')
                st.pyplot(fig)
            
            with col2:
                st.subheader("Activity Heatmap (Hexbin)")
                pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#0e0e0e', line_color='#444')
                fig, ax = pitch.draw(figsize=(10, 7))
                
                touches = messi_df[['x', 'y']].dropna()
                bin_statistic = pitch.bin_statistic(touches.x, touches.y, statistic='count', bins=(25, 25))
                pitch.heatmap(bin_statistic, ax=ax, cmap='gist_heat', edgecolors='#000')
                st.pyplot(fig)

        with tab2:
            st.subheader("The 'Alien' Chart: Overperformance")
            # Сортировка по дате для правильного графика
            shots_tl = messi_df[messi_df['type'] == 'Shot'].sort_values('match_date')
            
            shots_tl['is_goal'] = shots_tl['shot_outcome'].apply(lambda x: 1 if x == 'Goal' else 0)
            shots_tl['cum_goals'] = shots_tl['is_goal'].cumsum()
            shots_tl['cum_xg'] = shots_tl['shot_statsbomb_xg'].cumsum()
            shots_tl['shot_id'] = range(len(shots_tl))
            
            fig, ax = plt.subplots(figsize=(12, 5))
            fig.set_facecolor('#0e0e0e')
            ax.set_facecolor('#0e0e0e')
            
            ax.plot(shots_tl['shot_id'], shots_tl['cum_goals'], color='#D4AF37', linewidth=3, label='Actual Goals')
            ax.plot(shots_tl['shot_id'], shots_tl['cum_xg'], color='#666', linestyle='--', label='Expected Goals (xG)')
            ax.fill_between(shots_tl['shot_id'], shots_tl['cum_goals'], shots_tl['cum_xg'], where=(shots_tl['cum_goals']>shots_tl['cum_xg']), color='#D4AF37', alpha=0.2)
            
            ax.tick_params(colors='white')
            ax.legend(facecolor='#111', labelcolor='white')
            st.pyplot(fig)
            
    else:
        st.warning("Data loaded, but Messi stats not found for this season.")
else:
    st.error("Failed to load data.")
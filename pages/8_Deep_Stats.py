import streamlit as st
import sys
import os

# --- ФИКС ПУТЕЙ (Чтобы работало всегда) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsbombpy import sb

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Deep Stats Season", layout="wide", page_icon="🧬")

# --- СТИЛИ (MONEYBALL GREEN) ---
st.markdown("""
<style>
    .stApp { background-color: #0e0e0e; }
    h1, h2, h3 { color: #00ff87 !important; font-family: 'Consolas', monospace; }
    .metric-card {
        border: 1px solid #00ff87;
        background: rgba(0, 255, 135, 0.05);
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    .metric-val { font-size: 28px; font-weight: bold; color: #fff; }
    .metric-lbl { font-size: 12px; color: #aaa; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

st.title("🧬 SEASON DEEP DIVE: xG CHAIN & BUILDUP")
st.caption("Moneyball Metrics: Поиск игроков, которые влияют на игру, но не всегда забивают.")

# --- ДВИЖОК: xG CHAIN CALCULATOR ---
def process_match_xg_chain(match_id):
    """Считает xG Chain для одного матча"""
    try:
        events = sb.events(match_id=match_id)
        # Нам нужны только события с владением
        poss_actions = ['Pass', 'Carry', 'Dribble', 'Shot']
        df = events[events['type'].isin(poss_actions)].copy()
        
        # 1. Находим удары с xG
        shots = df[df['type'] == 'Shot'].dropna(subset=['shot_statsbomb_xg'])
        poss_xg_map = shots.set_index('possession')['shot_statsbomb_xg'].to_dict()
        
        # 2. Присваиваем xG владению
        df['possession_xg'] = df['possession'].map(poss_xg_map).fillna(0)
        
        # Оставляем только те владения, где был удар (xG > 0)
        df_chain = df[df['possession_xg'] > 0].copy()
        
        if df_chain.empty: return pd.DataFrame()

        # 3. Считаем Chain (Все участники)
        # Группируем по игроку и владению, чтобы не считать одного игрока дважды за одну атаку
        player_chain = df_chain.groupby(['player', 'team', 'possession'])['possession_xg'].max().reset_index()
        # Суммируем по игрокам
        xg_chain_sum = player_chain.groupby(['player', 'team'])['possession_xg'].sum().reset_index()
        xg_chain_sum.rename(columns={'possession_xg': 'xG Chain'}, inplace=True)
        
        # 4. Считаем Buildup (Без бьющего и ассистента)
        # Находим тех, кто бил или давал пас под удар
        shooters = df_chain[df_chain['type'] == 'Shot']['player'].unique()
        key_passers = df_chain[df_chain.get('pass_shot_assist', False) == True]['player'].unique()
        exclude_players = np.union1d(shooters, key_passers)
        
        # Фильтруем
        df_buildup = df_chain[~df_chain['player'].isin(exclude_players)]
        
        player_buildup = df_buildup.groupby(['player', 'team', 'possession'])['possession_xg'].max().reset_index()
        xg_buildup_sum = player_buildup.groupby(['player', 'team'])['possession_xg'].sum().reset_index()
        xg_buildup_sum.rename(columns={'possession_xg': 'xG Buildup'}, inplace=True)
        
        # Объединяем
        final_df = pd.merge(xg_chain_sum, xg_buildup_sum, on=['player', 'team'], how='left').fillna(0)
        return final_df
        
    except:
        return pd.DataFrame()

# --- ТУРБО ЗАГРУЗКА СЕЗОНА ---
def load_season_deep_stats(competition_id, season_id):
    filename = f"deep_stats_comp_{competition_id}_season_{season_id}.csv"
    
    if os.path.exists(filename):
        st.toast("⚡ Данные xG Chain загружены с диска!", icon="🚀")
        return pd.read_csv(filename)
    
    st.info("⚠️ Первый запуск: Анализируем каждое владение мячом в сезоне. Это займет 1-3 минуты.")
    
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    match_ids = matches['match_id'].tolist()
    
    all_stats = []
    bar = st.progress(0, text="Вычисляем xG Chain...")
    
    for i, m_id in enumerate(match_ids):
        match_stats = process_match_xg_chain(m_id)
        if not match_stats.empty:
            match_stats['match_id'] = m_id # Для отладки
            all_stats.append(match_stats)
        
        bar.progress(int(((i+1)/len(match_ids))*100))
    
    bar.empty()
    
    if all_stats:
        full_df = pd.concat(all_stats, ignore_index=True)
        # Агрегируем по всему сезону (Сумма)
        season_total = full_df.groupby(['player', 'team']).agg({
            'xG Chain': 'sum',
            'xG Buildup': 'sum',
            'match_id': 'nunique' # Кол-во матчей
        }).reset_index()
        
        season_total.rename(columns={'match_id': 'Matches'}, inplace=True)
        
        # Нормализуем Per 90 (упрощенно)
        season_total['xG Chain p90'] = season_total['xG Chain'] / season_total['Matches']
        season_total['xG Buildup p90'] = season_total['xG Buildup'] / season_total['Matches']
        
        season_total.to_csv(filename, index=False)
        return season_total
    
    return pd.DataFrame()

# --- САЙДБАР ---
st.sidebar.header("Фильтры")

# Выбор Лиги (Кэшируем список)
@st.cache_data
def get_comps(): return sb.competitions()

comps = get_comps()
# Берем популярные
pop_comps = comps[comps['competition_name'].isin(['La Liga', 'Premier League', 'Champions League'])]

c_name = st.sidebar.selectbox("Лига", pop_comps['competition_name'].unique())
c_id = pop_comps[pop_comps['competition_name'] == c_name]['competition_id'].values[0]

seasons = pop_comps[pop_comps['competition_name'] == c_name]
s_name = st.sidebar.selectbox("Сезон", seasons['season_name'].unique())
s_id = seasons[seasons['season_name'] == s_name]['season_id'].values[0]

# --- ЗАГРУЗКА ---
df = load_season_deep_stats(c_id, s_id)

if not df.empty:
    # Фильтры отображения
    min_matches = st.sidebar.slider("Минимум матчей", 1, 38, 5)
    df_filtered = df[df['Matches'] >= min_matches].copy()
    
    teams = sorted(df_filtered['team'].unique())
    sel_teams = st.sidebar.multiselect("Команда", teams)
    if sel_teams:
        df_filtered = df_filtered[df_filtered['team'].isin(sel_teams)]

    # --- ВИЗУАЛИЗАЦИЯ ---
    
    # 1. SCATTER PLOT (Chain vs Buildup)
    st.subheader("🕵️ Finding Hidden Gems (Buildup vs Chain)")
    st.caption("Игроки справа внизу (Высокий Buildup, Низкий Chain) — это 'серые кардиналы' (Бускетс, Кроос). Игроки справа вверху — суперзвезды (Месси).")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.set_facecolor('#0e0e0e')
    ax.set_facecolor('#0e0e0e')
    
    # Рисуем точки
    sns.scatterplot(data=df_filtered, x='xG Buildup', y='xG Chain', hue='team', s=100, palette='bright', legend=False, ax=ax)
    
    # Подписываем топов
    # Берем топ-10 по Chain и топ-5 по Buildup
    top_chain = df_filtered.nlargest(10, 'xG Chain')
    top_buildup = df_filtered.nlargest(5, 'xG Buildup')
    to_label = pd.concat([top_chain, top_buildup]).drop_duplicates()
    
    for i, row in to_label.iterrows():
        ax.text(row['xG Buildup']+0.02, row['xG Chain'], row['player'].split()[-1], color='white', fontsize=9)
        
    ax.set_xlabel("xG Buildup (Вклад без ударов/ассистов)", color='white')
    ax.set_ylabel("xG Chain (Общий вклад)", color='white')
    ax.tick_params(colors='white')
    ax.grid(color='#333', alpha=0.3)
    
    st.pyplot(fig)
    
    # 2. LEADERBOARD
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top xG Chain")
        top_c = df_filtered.sort_values('xG Chain', ascending=False).head(15)
        st.dataframe(top_c[['player', 'team', 'Matches', 'xG Chain']].style.background_gradient(cmap='Greens'), use_container_width=True)
        
    with col2:
        st.subheader("🧱 Top xG Buildup")
        top_b = df_filtered.sort_values('xG Buildup', ascending=False).head(15)
        st.dataframe(top_b[['player', 'team', 'Matches', 'xG Buildup']].style.background_gradient(cmap='Blues'), use_container_width=True)
        
    # 3. PLAYER CARD
    st.markdown("---")
    st.subheader("👤 Player Deep Profile")
    
    player_list = sorted(df_filtered['player'].unique())
    sel_player = st.selectbox("Выберите игрока", player_list)
    
    p_stats = df_filtered[df_filtered['player'] == sel_player].iloc[0]
    
    # Метрики
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Matches", int(p_stats['Matches']))
    k2.metric("Total xG Chain", f"{p_stats['xG Chain']:.2f}")
    k3.metric("Total xG Buildup", f"{p_stats['xG Buildup']:.2f}")
    
    # % Buildup Ratio (Насколько игрок зависит от голов?)
    ratio = (p_stats['xG Buildup'] / p_stats['xG Chain'] * 100) if p_stats['xG Chain'] > 0 else 0
    k4.metric("Buildup Ratio %", f"{ratio:.1f}%", help="100% = Игрок никогда не бьет и не ассистирует, только строит игру.")
    
else:
    st.write("Выберите данные слева.")
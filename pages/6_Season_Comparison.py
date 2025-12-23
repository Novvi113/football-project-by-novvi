import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Radar
from statsbombpy import sb
import soccerdata as sd
import os

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Ultimate Comparison", layout="wide", page_icon="⚔️")

# --- СТИЛИ ---
st.markdown("""
<style>
    .stApp { background-color: #121212; }
    h1, h2, h3 { color: #fff !important; }
    .stRadio > label { color: #fff; font-weight: bold; }
    .metric-card { background: #1e1e1e; border-left: 5px solid #39ff14; padding: 10px; margin-bottom: 5px; }
    .metric-val { color: #fff; font-weight: bold; font-size: 18px; }
    .metric-lbl { color: #aaa; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("⚔️ ULTIMATE PLAYER BATTLE")

# --- ГЛАВНЫЙ ПЕРЕКЛЮЧАТЕЛЬ ---
st.sidebar.header("⚙️ Настройки")
data_source = st.sidebar.radio(
    "Выберите источник данных:",
    ("StatsBomb (Open Data)", "FBref (Scouting Report)")
)

# =================================================================================
# ЛОГИКА 1: STATSBOMB (Тот самый Turbo Mode, который у нас был)
# =================================================================================
if data_source == "StatsBomb (Open Data)":
    st.subheader("📊 Анализ на базе StatsBomb (Бесплатные исторические данные)")
    
    # --- ДВИЖОК STATSBOMB ---
    @st.cache_data(show_spinner=False)
    def get_season_matches_sb(competition_id, season_id):
        return sb.matches(competition_id=competition_id, season_id=season_id)

    def load_sb_turbo(season_id):
        filename = f"season_{season_id}_data.csv"
        if os.path.exists(filename):
            st.toast("⚡ Данные StatsBomb загружены с диска!", icon="🚀")
            return pd.read_csv(filename, low_memory=False)
        
        st.toast("⏳ Скачиваем сезон StatsBomb...", icon="🌍")
        matches = get_season_matches_sb(11, season_id) # 11 = La Liga
        # Качаем Барсу для скорости (можно убрать фильтр)
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
        scale = 90 / (matches * 90) if matches > 0 else 0
        
        g = len(p_df[p_df['shot_outcome'] == 'Goal']) * scale
        a = (len(p_df[p_df['pass_goal_assist'] == True]) if 'pass_goal_assist' in p_df.columns else 0) * scale
        s = len(p_df[p_df['type'] == 'Shot']) * scale
        kp = (len(p_df[p_df['pass_shot_assist'] == True]) if 'pass_shot_assist' in p_df.columns else 0) * scale
        dr = len(p_df[(p_df['type'] == 'Dribble') & (p_df['dribble_outcome'] == 'Complete')]) * scale
        xg = (p_df['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in p_df.columns else 0) * scale
        return [g, a, s, kp, dr, xg]

    # --- ИНТЕРФЕЙС STATSBOMB ---
    sb_seasons = {"2014/15 (The Treble)": 26, "2015/16 (MSN Peak)": 27, "2010/11 (Pep Era)": 21}
    s_choice = st.sidebar.selectbox("Сезон (StatsBomb)", list(sb_seasons.keys()))
    df_sb = load_sb_turbo(sb_seasons[s_choice])

    if not df_sb.empty:
        counts = df_sb['player'].value_counts()
        top_players = sorted(counts[counts > 300].index.tolist())
        
        c1, c2 = st.columns(2)
        idx_m = top_players.index("Lionel Andrés Messi Cuccittini") if "Lionel Andrés Messi Cuccittini" in top_players else 0
        p1 = c1.selectbox("Игрок 1", top_players, index=idx_m)
        p2 = c2.selectbox("Игрок 2", top_players, index=min(1, len(top_players)-1))
        
        if st.button("Построить Радар"):
            vals1 = calc_p90(df_sb, p1)
            vals2 = calc_p90(df_sb, p2)
            params = ["Goals", "Assists", "Shots", "Key Passes", "Dribbles", "xG"]
            min_v, max_v = [0]*6, [1.2, 0.8, 6.0, 4.0, 6.0, 1.2]
            
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

# =================================================================================
# ЛОГИКА 2: FBREF (Продвинутый Скаутинг)
# =================================================================================
elif data_source == "FBref (Scouting Report)":
    st.subheader("🌍 Скаутинг FBref (Сравнение с лигой)")
    st.caption("Здесь мы сравниваем игроков по перцентилям (как на сайте FBref).")

    # --- ДВИЖОК FBREF ---
    def load_fbref_cached(league, season):
        filename = f"fbref_{league}_{season}.csv"
        if os.path.exists(filename):
            st.toast("🚀 Данные FBref загружены с диска!", icon="💾")
            return pd.read_csv(filename)
        
        st.info("⚠️ Скачиваем данные с FBref. Это займет ~2 минуты. Пожалуйста, не обновляй страницу.")
        try:
            fb = sd.FBref(leagues=[league], seasons=[season])
            # Качаем кусками
            dfs = []
            for t in ["shooting", "passing", "defense", "possession", "misc"]:
                d = fb.read_player_season_stats(stat_type=t).reset_index()
                d.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in d.columns.values]
                dfs.append(d)
            
            full = dfs[0]
            for d in dfs[1:]:
                full = pd.merge(full, d, on=['league', 'season', 'team', 'player'], how='outer', suffixes=('', '_dup'))
            full = full.loc[:, ~full.columns.str.endswith('_dup')]
            full.to_csv(filename, index=False)
            return full
        except Exception as e:
            st.error(f"Ошибка FBref: {e}")
            return pd.DataFrame()

    def get_percentile(df, player_name, metric_col, min_col):
        # Считаем ранг игрока среди всех в лиге (>500 мин)
        df_f = df[df[min_col] > 500].copy()
        if player_name not in df_f['player'].values: return 0, 0
        
        p_row = df_f[df_f['player'] == player_name].iloc[0]
        # p90
        val = float(p_row[metric_col]) / (float(p_row[min_col]) / 90)
        # Массив всех p90
        all_vals = df_f[metric_col] / (df_f[min_col] / 90)
        pct = (all_vals < val).mean() * 100
        return val, int(pct)

    # --- ИНТЕРФЕЙС FBREF ---
    st.sidebar.markdown("---")
    fb_league = st.sidebar.selectbox("Лига", ['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A', 'FRA-Ligue 1'])
    fb_season = st.sidebar.selectbox("Сезон (Год начала)", ['2324', '2223', '2122'])

    df_fb = load_fbref_cached(fb_league, fb_season)

    if not df_fb.empty:
        # Ищем колонку с минутами
        min_col = [c for c in df_fb.columns if 'min' in c.lower()][0]
        
        all_p = sorted(df_fb[df_fb[min_col] > 500]['player'].unique())
        
        c1, c2 = st.columns(2)
        p1 = c1.selectbox("Игрок 1 (Зеленый)", all_p, index=0)
        p2 = c2.selectbox("Игрок 2 (Синий)", all_p, index=min(1, len(all_p)-1))
        
        # Метрики для сравнения (Ключевые слова для поиска колонок)
        metrics_dict = {
            "Non-Penalty xG": ['npxg', 'expected_npxg'],
            "Shots": ['shots_total'],
            "Assists": ['ast'],
            "xA": ['xg_assist'],
            "Prog. Passes": ['progressive_passes'],
            "Prog. Carries": ['carries_prog'],
            "Dribbles Succ": ['dribbles_succ'],
            "Tackles": ['tackles_won'],
            "Interceptions": ['interceptions']
        }
        
        if st.button("Сравнить Скаутские Отчеты"):
            st.subheader(f"Head-to-Head: {p1} vs {p2}")
            
            # Строим таблицу сравнения
            data = []
            for label, keys in metrics_dict.items():
                # Ищем точное имя колонки
                col = next((c for c in df_fb.columns for k in keys if k in c.lower()), None)
                if col:
                    v1, pct1 = get_percentile(df_fb, p1, col, min_col)
                    v2, pct2 = get_percentile(df_fb, p2, col, min_col)
                    data.append([label, v1, pct1, v2, pct2])
            
            # Визуализация (Сравнение баров)
            fig, ax = plt.subplots(figsize=(10, len(data)*0.8))
            fig.set_facecolor('#121212')
            ax.set_facecolor('#121212')
            
            y_pos = np.arange(len(data))
            pcts1 = [d[2] for d in data]
            pcts2 = [d[4] for d in data]
            labels = [d[0] for d in data]
            
            # Рисуем
            ax.barh(y_pos + 0.2, pcts1, height=0.4, label=p1, color='#39ff14')
            ax.barh(y_pos - 0.2, pcts2, height=0.4, label=p2, color='#00b4d8')
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, color='white', fontsize=12)
            ax.set_xlabel("Percentile Rank (vs League)", color='white')
            ax.set_xlim(0, 100)
            
            # Подписи
            for i, (p_v, p_pct) in enumerate(zip(pcts1, pcts1)):
                ax.text(p_v + 1, i + 0.2, f"{p_pct}", va='center', color='#39ff14', fontweight='bold')
            for i, (p_v, p_pct) in enumerate(zip(pcts2, pcts2)):
                ax.text(p_v + 1, i - 0.2, f"{p_pct}", va='center', color='#00b4d8', fontweight='bold')

            ax.legend(facecolor='#121212', labelcolor='white', loc='upper center', bbox_to_anchor=(0.5, 1.1))
            ax.spines['bottom'].set_color('white')
            ax.spines['left'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.tick_params(axis='x', colors='white')
            ax.grid(axis='x', color='#333', linestyle='--')
            
            st.pyplot(fig)
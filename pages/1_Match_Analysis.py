import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import Pitch, VerticalPitch, FontManager
from scipy.ndimage import gaussian_filter
from utils.data import get_competitions, get_matches, get_events

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="Pro Match Analysis", layout="wide", page_icon="🏟️")

# --- CSS СТИЛИ (ТЕМНАЯ ТЕМА) ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { color: #ffffff !important; font-family: 'Roboto', sans-serif; }
    .metric-box {
        background-color: #1c1c1c;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-value { font-size: 28px; font-weight: bold; color: #4CC9F0; }
    .metric-label { font-size: 14px; color: #aaaaaa; text-transform: uppercase; letter-spacing: 1px; }
    .score-board {
        background: linear-gradient(90deg, #1c1c1c 0%, #2d2d2d 50%, #1c1c1c 100%);
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        border: 1px solid #444;
    }
    .team-name { font-size: 32px; font-weight: bold; color: white; }
    .score { font-size: 48px; font-weight: 900; color: #E63946; margin: 0 20px; }
</style>
""", unsafe_allow_html=True)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_team_color(team_name, home_team):
    if team_name == home_team:
        return '#4CC9F0' # Cyan for Home
    else:
        return '#F72585' # Pink for Away

# --- 1. ЗАГРУЗКА ДАННЫХ ---
st.sidebar.title("🛠️ Match Control")
comps = get_competitions()
comp_name = st.sidebar.selectbox("Competition", comps['competition_name'].unique())
comp_id = comps[comps['competition_name'] == comp_name]['competition_id'].values[0]

seasons = comps[comps['competition_name'] == comp_name]
season_name = st.sidebar.selectbox("Season", seasons['season_name'].unique())
season_id = seasons[seasons['season_name'] == season_name]['season_id'].values[0]

matches = get_matches(comp_id, season_id)
match_list = matches['home_team'] + " vs " + matches['away_team']
selected_match = st.sidebar.selectbox("Select Match", match_list)
match_data = matches[match_list == selected_match].iloc[0]
match_id = match_data['match_id']

with st.spinner('Loading Advanced Metrics...'):
    events = get_events(match_id)

# Подготовка базовых переменных
home_team = match_data['home_team']
away_team = match_data['away_team']
home_score = match_data['home_score']
away_score = match_data['away_score']

# --- 2. HEADER (СЧЕТ И МЕТРИКИ) ---
st.markdown(f"""
<div class="score-board">
    <span class="team-name">{home_team}</span>
    <span class="score">{home_score} - {away_score}</span>
    <span class="team-name">{away_team}</span>
</div>
""", unsafe_allow_html=True)

# Расчет общей статистики
home_events = events[events['team'] == home_team]
away_events = events[events['team'] == away_team]

# xG (если есть, иначе 0)
hxG = home_events['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in home_events.columns else 0
axG = away_events['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in away_events.columns else 0

# Shots
h_shots = len(home_events[home_events['type'] == 'Shot'])
a_shots = len(away_events[away_events['type'] == 'Shot'])

# Passes & Accuracy
h_pass = len(home_events[home_events['type'] == 'Pass'])
h_pass_acc = len(home_events[(home_events['type'] == 'Pass') & (home_events['pass_outcome'].isna())])
h_acc_rate = int(h_pass_acc / h_pass * 100) if h_pass > 0 else 0

a_pass = len(away_events[away_events['type'] == 'Pass'])
a_pass_acc = len(away_events[(away_events['type'] == 'Pass') & (away_events['pass_outcome'].isna())])
a_acc_rate = int(a_pass_acc / a_pass * 100) if a_pass > 0 else 0

# Possession (Простое приближение по количеству пасов)
total_pass = h_pass + a_pass
h_poss = int(h_pass / total_pass * 100) if total_pass > 0 else 50
a_poss = 100 - h_poss

# Визуализация метрик в 4 колонки
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="metric-box"><div class="metric-value">{round(hxG, 2)} : {round(axG, 2)}</div><div class="metric-label">Expected Goals (xG)</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="metric-box"><div class="metric-value">{h_shots} : {a_shots}</div><div class="metric-label">Total Shots</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="metric-box"><div class="metric-value">{h_poss}% : {a_poss}%</div><div class="metric-label">Possession</div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="metric-box"><div class="metric-value">{h_acc_rate}% : {a_acc_rate}%</div><div class="metric-label">Pass Accuracy</div></div>""", unsafe_allow_html=True)

# --- 3. ВКЛАДКИ АНАЛИЗА ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Game Momentum", 
    "🕸️ Passing Networks", 
    "🎯 Shot Maps", 
    "🔥 Heatmaps & Tactics",
    "🛡️ Defensive Pressure"
])

# === TAB 1: GAME MOMENTUM (xG Timeline) ===
with tab1:
    st.subheader("📊 Match Story: Cumulative xG")
    
    # Подготовка данных для графика
    shots = events[events['type'] == 'Shot'][['minute', 'team', 'shot_statsbomb_xg', 'player', 'shot_outcome']].copy()
    shots['shot_statsbomb_xg'] = shots['shot_statsbomb_xg'].fillna(0)
    
    # Разделяем по командам
    h_shots_df = shots[shots['team'] == home_team].sort_values('minute')
    a_shots_df = shots[shots['team'] == away_team].sort_values('minute')
    
    # Кумулятивная сумма
    h_shots_df['xG_cum'] = h_shots_df['shot_statsbomb_xg'].cumsum()
    a_shots_df['xG_cum'] = a_shots_df['shot_statsbomb_xg'].cumsum()
    
    # Добавляем начальную точку 0:0
    h_timeline = pd.concat([pd.DataFrame({'minute': [0], 'xG_cum': [0]}), h_shots_df])
    a_timeline = pd.concat([pd.DataFrame({'minute': [0], 'xG_cum': [0]}), a_shots_df])
    
    # Добавляем конечную точку (90+ мин)
    max_min = events['minute'].max()
    h_timeline = pd.concat([h_timeline, pd.DataFrame({'minute': [max_min], 'xG_cum': [h_timeline['xG_cum'].iloc[-1]]})])
    a_timeline = pd.concat([a_timeline, pd.DataFrame({'minute': [max_min], 'xG_cum': [a_timeline['xG_cum'].iloc[-1]]})])
    
    # Рисуем график
    fig, ax = plt.subplots(figsize=(16, 6))
    plt.style.use('dark_background')
    ax.set_facecolor('#121212')
    fig.set_facecolor('#121212')
    
    # Линии
    ax.step(h_timeline['minute'], h_timeline['xG_cum'], where='post', color='#4CC9F0', linewidth=3, label=home_team)
    ax.step(a_timeline['minute'], a_timeline['xG_cum'], where='post', color='#F72585', linewidth=3, label=away_team)
    
    # Закрашиваем области
    ax.fill_between(h_timeline['minute'], h_timeline['xG_cum'], step='post', alpha=0.1, color='#4CC9F0')
    ax.fill_between(a_timeline['minute'], a_timeline['xG_cum'], step='post', alpha=0.1, color='#F72585')
    
    # Отмечаем голы
    h_goals = h_shots_df[h_shots_df['shot_outcome'] == 'Goal']
    a_goals = a_shots_df[a_shots_df['shot_outcome'] == 'Goal']
    
    ax.scatter(h_goals['minute'], h_goals['xG_cum'], s=200, c='#4CC9F0', edgecolors='white', zorder=5, marker='*', label='Home Goal')
    ax.scatter(a_goals['minute'], a_goals['xG_cum'], s=200, c='#F72585', edgecolors='white', zorder=5, marker='*', label='Away Goal')
    
    ax.set_ylabel("Cumulative xG", color='white', fontsize=14)
    ax.set_xlabel("Minute", color='white', fontsize=14)
    ax.legend(facecolor='#1c1c1c', edgecolor='none', labelcolor='white')
    ax.grid(color='#333', linestyle='--', alpha=0.5)
    
    st.pyplot(fig)

# === TAB 2: PASSING NETWORKS ===
with tab2:
    st.subheader("🕸️ Passing Networks & Average Positions")
    st.info("Толщина линий = количество пасов. Размер точки = количество касаний.")

    def draw_pass_network(team_name, ax, color):
        # 1. Фильтруем пасы команды
        team_pass = events[(events['team'] == team_name) & (events['type'] == 'Pass') & (events['pass_outcome'].isna())]
        
        # 2. Средние позиции игроков (до первой замены для чистоты, но можно и за весь матч)
        # Здесь берем за весь матч для упрощения
        avg_loc = team_pass.groupby('player').agg({'x': 'mean', 'y': 'mean', 'minute': 'count'}).reset_index()
        avg_loc.rename(columns={'minute': 'pass_count'}, inplace=True)
        
        # 3. Связи (Пас от игрока А к игроку Б)
        # Нам нужно знать получателя. В StatsBomb это 'pass_recipient' (в statsbombpy иногда не парсится напрямую, проверяем)
        if 'pass_recipient' in team_pass.columns:
            pass_connections = team_pass.groupby(['player', 'pass_recipient']).count().reset_index()
            pass_connections = pass_connections[['player', 'pass_recipient', 'minute']]
            pass_connections.rename(columns={'minute': 'count'}, inplace=True)
            
            # Фильтруем слабые связи (меньше 3 пасов)
            pass_connections = pass_connections[pass_connections['count'] > 2]
            
            # Рисуем поле
            pitch = Pitch(pitch_type='statsbomb', pitch_color='#121212', line_color='#555')
            pitch.draw(ax=ax)
            
            # Рисуем линии
            for idx, row in pass_connections.iterrows():
                p1 = avg_loc[avg_loc['player'] == row['player']]
                p2 = avg_loc[avg_loc['player'] == row['pass_recipient']]
                
                if not p1.empty and not p2.empty:
                    width = row['count'] * 0.5 # Толщина зависит от количества
                    pitch.lines(p1.x.values[0], p1.y.values[0],
                                p2.x.values[0], p2.y.values[0],
                                ax=ax, lw=width, color=color, alpha=0.4, zorder=1)
            
            # Рисуем узлы (игроков)
            pitch.scatter(avg_loc.x, avg_loc.y, ax=ax, s=avg_loc['pass_count']*5, color=color, edgecolors='white', zorder=2)
            
            # Подписи игроков (фамилии)
            for idx, row in avg_loc.iterrows():
                name = row['player'].split(" ")[-1] # Только фамилия
                pitch.annotate(name, xy=(row.x, row.y), ax=ax, color='white', va='center', ha='center', size=10, weight='bold')
                
            ax.set_title(f"{team_name}", color='white', fontsize=20)
            
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig, ax = plt.subplots(figsize=(10, 8))
        draw_pass_network(home_team, ax, '#4CC9F0')
        st.pyplot(fig)
    with col_p2:
        fig, ax = plt.subplots(figsize=(10, 8))
        draw_pass_network(away_team, ax, '#F72585')
        st.pyplot(fig)

# === TAB 3: SHOT MAPS ===
with tab3:
    st.subheader("🎯 Shot Maps (Size = xG Quality)")
    
    col_s1, col_s2 = st.columns(2)
    
    def draw_shots_advanced(team_name, ax, color):
        team_shots = events[(events['team'] == team_name) & (events['type'] == 'Shot')]
        
        pitch = VerticalPitch(pitch_type='statsbomb', half=True, pitch_color='#121212', line_color='#555')
        pitch.draw(ax=ax)
        
        # Голы
        goals = team_shots[team_shots['shot_outcome'] == 'Goal']
        # Не голы
        no_goals = team_shots[team_shots['shot_outcome'] != 'Goal']
        
        # Рисуем промахи (круги)
        # Размер зависит от xG: s = xG * 500
        xg_no_goals = no_goals['shot_statsbomb_xg'].fillna(0) * 500
        pitch.scatter(no_goals.x, no_goals.y, ax=ax, s=xg_no_goals, c=color, alpha=0.3, edgecolors=color)
        
        # Рисуем голы (звезды)
        xg_goals = goals['shot_statsbomb_xg'].fillna(0) * 500
        pitch.scatter(goals.x, goals.y, ax=ax, s=xg_goals, c=color, marker='*', edgecolors='white', zorder=3)
        
        ax.set_title(f"{team_name} Shots", color='white', fontsize=18)
        
    with col_s1:
        fig, ax = plt.subplots(figsize=(8, 8))
        draw_shots_advanced(home_team, ax, '#4CC9F0')
        st.pyplot(fig)
    with col_s2:
        fig, ax = plt.subplots(figsize=(8, 8))
        draw_shots_advanced(away_team, ax, '#F72585')
        st.pyplot(fig)

# === TAB 4: HEATMAPS & TACTICS ===
with tab4:
    st.subheader("🔥 Heatmaps & Danger Zones")
    
    option = st.radio("Choose Analysis Type", ["Activity Heatmap", "Passes into the Box"])
    
    col_h1, col_h2 = st.columns(2)
    
    if option == "Activity Heatmap":
        def draw_heatmap(team_name, ax, cmap):
            # Берем все действия с координатами (Pressure, Pass, Carry, etc.)
            team_ev = events[(events['team'] == team_name) & (events['x'].notna())]
            
            pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#121212', line_color='#555')
            pitch.draw(ax=ax)
            
            # KDE Plot (Плотность)
            pitch.kdeplot(team_ev.x, team_ev.y, ax=ax, cmap=cmap, fill=True, levels=50, alpha=0.7, thresh=0.05)
            ax.set_title(f"{team_name}", color='white', fontsize=20)
            
        with col_h1:
            fig, ax = plt.subplots(figsize=(10, 7))
            draw_heatmap(home_team, ax, 'Blues')
            st.pyplot(fig)
        with col_h2:
            fig, ax = plt.subplots(figsize=(10, 7))
            draw_heatmap(away_team, ax, 'Reds')
            st.pyplot(fig)
            
    elif option == "Passes into the Box":
        def draw_box_passes(team_name, ax, color):
            # Фильтр: Пасы, которые заканчиваются в штрафной (x > 102, 18 < y < 62)
            team_pass = events[(events['team'] == team_name) & (events['type'] == 'Pass') & (events['pass_outcome'].isna())]
            if team_pass.empty: return
            
            # Логика box passes
            box_passes = team_pass[team_pass['pass_end_location'].apply(
                lambda loc: loc[0] >= 102 and 18 <= loc[1] <= 62 if isinstance(loc, list) else False
            )]
            
            pitch = VerticalPitch(pitch_type='statsbomb', half=True, pitch_color='#121212', line_color='#555')
            pitch.draw(ax=ax)
            
            if not box_passes.empty:
                pitch.lines(box_passes.x, box_passes.y,
                            box_passes['pass_end_location'].apply(lambda x: x[0]),
                            box_passes['pass_end_location'].apply(lambda x: x[1]),
                            ax=ax, color=color, comet=True, lw=3, alpha=0.6)
                
                pitch.scatter(box_passes['pass_end_location'].apply(lambda x: x[0]),
                              box_passes['pass_end_location'].apply(lambda x: x[1]),
                              ax=ax, s=50, c=color)
            
            ax.set_title(f"{team_name}: Passes into Box ({len(box_passes)})", color='white', fontsize=18)

        with col_h1:
            fig, ax = plt.subplots(figsize=(8, 8))
            draw_box_passes(home_team, ax, '#4CC9F0')
            st.pyplot(fig)
        with col_h2:
            fig, ax = plt.subplots(figsize=(8, 8))
            draw_box_passes(away_team, ax, '#F72585')
            st.pyplot(fig)

# === TAB 5: DEFENSIVE PRESSURE ===
with tab5:
    st.subheader("🛡️ Defensive Pressure Zones")
    
    col_d1, col_d2 = st.columns(2)
    
    def draw_pressure(team_name, ax, color):
        # События Pressure
        pressures = events[(events['team'] == team_name) & (events['type'] == 'Pressure')]
        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='#121212', line_color='#555')
        pitch.draw(ax=ax)
        
        # Просто точки прессинга
        pitch.scatter(pressures.x, pressures.y, ax=ax, s=40, c=color, alpha=0.6, edgecolors='none')
        
        # Можно добавить Convex Hull (зону активного прессинга)
        if len(pressures) > 10:
            pitch.kdeplot(pressures.x, pressures.y, ax=ax, cmap='magma', shade=True, shade_lowest=False, alpha=0.3)
        
        ax.set_title(f"{team_name} Pressure Events ({len(pressures)})", color='white', fontsize=18)
        
    with col_d1:
        fig, ax = plt.subplots(figsize=(10, 7))
        draw_pressure(home_team, ax, '#4CC9F0')
        st.pyplot(fig)
    with col_d2:
        fig, ax = plt.subplots(figsize=(10, 7))
        draw_pressure(away_team, ax, '#F72585')
        st.pyplot(fig)

# --- FOOTER ---
st.markdown("---")
st.markdown("<center>Analytics powered by <b>Mplsoccer</b>, <b>StatsBomb</b> & <b>Streamlit</b></center>", unsafe_allow_html=True)
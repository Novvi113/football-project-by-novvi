import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch
from statsbombpy import sb
import os

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Season xT Analysis", layout="wide", page_icon="🧠")

# --- СТИЛИ (MATRIX STYLE) ---
st.markdown("""
<style>
    .stApp { background-color: #050505; }
    h1, h2, h3 { color: #00ff41 !important; font-family: 'Courier New', monospace; text-transform: uppercase; font-weight: bold; }
    .metric-card {
        background: rgba(0, 255, 65, 0.05);
        border: 1px solid #00ff41;
        border-radius: 5px;
        padding: 15px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-val { font-size: 24px; font-weight: bold; color: #fff; }
    .metric-lbl { font-size: 10px; color: #aaa; letter-spacing: 2px; }
</style>
""", unsafe_allow_html=True)

st.title("🧠 GLOBAL xT RANKINGS (SEASON)")

# --- 1. xT GRID (МАТРИЦА УГРОЗЫ) ---
xT_grid = np.array([
    [0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126277, 0.01248344, 0.01473596, 0.01745064, 0.02122129, 0.02756312, 0.03485072, 0.0379259 ],
    [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719, 0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272, 0.04066992, 0.04647721],
    [0.00887958, 0.00977745, 0.01001304, 0.01110462, 0.01269174, 0.01429128, 0.01685614, 0.01935132, 0.0241224 , 0.02855202, 0.0449146 , 0.06942984],
    [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646, 0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326, 0.08833026, 0.2574518 ],
    [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646, 0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326, 0.08833026, 0.2574518 ],
    [0.00887958, 0.00977745, 0.01001304, 0.01110462, 0.01269174, 0.01429128, 0.01685614, 0.01935132, 0.0241224 , 0.02855202, 0.0449146 , 0.06942984],
    [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719, 0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272, 0.04066992, 0.04647721],
    [0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126277, 0.01248344, 0.01473596, 0.01745064, 0.02122129, 0.02756312, 0.03485072, 0.0379259 ]
])

def get_xt(x, y):
    y_idx = int(np.clip(y / 80 * 8, 0, 7))
    x_idx = int(np.clip(x / 120 * 12, 0, 11))
    return xT_grid[y_idx][x_idx]

# --- 2. ТУРБО-ЛОАДЕР СЕЗОНА ---
@st.cache_data
def get_competitions_cached():
    return sb.competitions()

def load_season_xt(competition_id, season_id):
    # Уникальное имя файла для xT статистики
    filename = f"xt_stats_comp_{competition_id}_season_{season_id}.csv"
    
    # 1. Если файл есть - грузим моментально
    if os.path.exists(filename):
        st.toast("⚡ xT Данные загружены с диска!", icon="🚀")
        return pd.read_csv(filename)
    
    # 2. Если нет - качаем и считаем (ДОЛГО, но один раз)
    st.info("⚠️ Первый запуск: Скачиваем весь сезон и считаем xT для 100,000+ событий. Это займет 1-2 минуты.")
    
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    # Берем ВСЕ матчи лиги (а не только Барсы), чтобы рейтинг был честным
    match_ids = matches['match_id'].tolist()
    
    all_events = []
    bar = st.progress(0, text="Анализ матчей...")
    
    for i, m_id in enumerate(match_ids):
        try:
            ev = sb.events(match_id=m_id)
            # Оставляем только Пасы и Проходы (чтобы файл не был огромным)
            ev = ev[ev['type'].isin(['Pass', 'Carry'])].copy()
            
            # Чистим координаты
            if 'location' in ev.columns:
                ev['x'] = ev['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
                ev['y'] = ev['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
            
            # Координаты конца
            ev['end_x'] = np.nan
            ev['end_y'] = np.nan
            
            # Для пасов
            if 'pass_end_location' in ev.columns:
                mask_pass = ev['type'] == 'Pass'
                ev.loc[mask_pass, 'end_x'] = ev.loc[mask_pass, 'pass_end_location'].apply(lambda x: x[0] if isinstance(x, list) else None)
                ev.loc[mask_pass, 'end_y'] = ev.loc[mask_pass, 'pass_end_location'].apply(lambda x: x[1] if isinstance(x, list) else None)
                
            # Для проходов
            if 'carry_end_location' in ev.columns:
                mask_carry = ev['type'] == 'Carry'
                ev.loc[mask_carry, 'end_x'] = ev.loc[mask_carry, 'carry_end_location'].apply(lambda x: x[0] if isinstance(x, list) else None)
                ev.loc[mask_carry, 'end_y'] = ev.loc[mask_carry, 'carry_end_location'].apply(lambda x: x[1] if isinstance(x, list) else None)
            
            # Удаляем мусор без координат
            ev = ev.dropna(subset=['x', 'y', 'end_x', 'end_y'])
            
            # --- СЧИТАЕМ xT ПРЯМО ЗДЕСЬ ---
            # Это быстрее, чем потом
            ev['xT_start'] = ev.apply(lambda r: get_xt(r['x'], r['y']), axis=1)
            ev['xT_end'] = ev.apply(lambda r: get_xt(r['end_x'], r['end_y']), axis=1)
            ev['xT_added'] = ev['xT_end'] - ev['xT_start']
            
            # Оставляем только нужные колонки
            keep_cols = ['player', 'team', 'type', 'xT_added', 'x', 'y', 'end_x', 'end_y']
            all_events.append(ev[keep_cols])
            
        except: pass
        
        bar.progress(int(((i+1)/len(match_ids))*100))
        
    bar.empty()
    
    if all_events:
        full_df = pd.concat(all_events, ignore_index=True)
        # Сохраняем результат
        full_df.to_csv(filename, index=False)
        st.success("✅ Анализ сезона завершен! Данные сохранены.")
        return full_df
        
    return pd.DataFrame()

# --- 3. ИНТЕРФЕЙС ---
st.sidebar.header("Фильтры")

# Выбор Лиги
comps = get_competitions_cached()
# Популярные лиги
pop_comps = comps[comps['competition_name'].isin(['La Liga', 'Premier League', 'Champions League', 'FIFA World Cup'])]
comp_name = st.sidebar.selectbox("Лига", pop_comps['competition_name'].unique())
comp_id = pop_comps[pop_comps['competition_name'] == comp_name]['competition_id'].values[0]

# Выбор Сезона
seasons = pop_comps[pop_comps['competition_name'] == comp_name]
season_name = st.sidebar.selectbox("Сезон", seasons['season_name'].unique())
season_id = seasons[seasons['season_name'] == season_name]['season_id'].values[0]

# ЗАГРУЗКА
df = load_season_xt(comp_id, season_id)

if not df.empty:
    # --- 4. АНАЛИТИКА ---
    
    # Группируем по игрокам
    # Считаем сумму xT, но только положительную (не штрафуем за пасы назад)
    df_pos = df[df['xT_added'] > 0]
    
    leaderboard = df_pos.groupby(['player', 'team']).agg({
        'xT_added': 'sum',
        'type': 'count' # кол-во действий
    }).reset_index()
    
    leaderboard = leaderboard.rename(columns={'xT_added': 'Total xT', 'type': 'Actions'})
    leaderboard['Total xT'] = leaderboard['Total xT'].round(2)
    leaderboard = leaderboard.sort_values('Total xT', ascending=False).reset_index(drop=True)
    leaderboard.index = leaderboard.index + 1
    
    # ТОП ИГРОКИ (ГРАФИК)
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"🏆 Top xT Generators: {season_name}")
        
        # Фильтр по команде (опционально)
        teams = sorted(df['team'].unique())
        filter_team = st.multiselect("Фильтр по команде (пусто = все)", teams)
        
        if filter_team:
            plot_data = leaderboard[leaderboard['team'].isin(filter_team)].head(15)
        else:
            plot_data = leaderboard.head(15)
            
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.set_facecolor('#050505')
        ax.set_facecolor('#050505')
        
        # Бар чарт
        bars = ax.barh(plot_data['player'], plot_data['Total xT'], color='#00ff41')
        ax.invert_yaxis() # Чтобы 1 место было сверху
        
        ax.tick_params(colors='white', labelsize=10)
        ax.set_xlabel("Cumulative Expected Threat", color='white')
        
        # Подписи значений
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                    f'{width}', ha='left', va='center', color='white', fontweight='bold')
            
        st.pyplot(fig)
        
    with col2:
        st.subheader("📋 Leaderboard")
        st.dataframe(leaderboard[['player', 'team', 'Total xT']].head(20), use_container_width=True)

    # --- 5. DRILL DOWN (ДЕТАЛИ ИГРОКА) ---
    st.markdown("---")
    st.subheader("🕵️ Player Deep Dive")
    
    selected_player = st.selectbox("Выберите игрока для анализа зон", sorted(leaderboard['player'].unique()))
    
    p_events = df_pos[df_pos['player'] == selected_player]
    
    c_map1, c_map2 = st.columns(2)
    
    with c_map1:
        st.markdown("**Pass Threat Map**")
        pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#050505', line_color='#333')
        fig, ax = pitch.draw(figsize=(8, 6))
        
        pass_ev = p_events[p_events['type'] == 'Pass']
        # Рисуем соты (hexbin), откуда игрок создает угрозу пасами
        pitch.hexbin(pass_ev.x, pass_ev.y, gridsize=15, ax=ax, cmap='Greens', edgecolors='#000', mincnt=1)
        st.pyplot(fig)
        
    with c_map2:
        st.markdown("**Carry Threat Map**")
        pitch = Pitch(pitch_type='statsbomb', line_zorder=2, pitch_color='#050505', line_color='#333')
        fig, ax = pitch.draw(figsize=(8, 6))
        
        carry_ev = p_events[p_events['type'] == 'Carry']
        # Рисуем соты для дриблинга
        pitch.hexbin(carry_ev.x, carry_ev.y, gridsize=15, ax=ax, cmap='Blues', edgecolors='#000', mincnt=1)
        st.pyplot(fig)
        
    # Метрики игрока
    total_xt = p_events['xT_added'].sum()
    pass_xt = p_events[p_events['type'] == 'Pass']['xT_added'].sum()
    carry_xt = p_events[p_events['type'] == 'Carry']['xT_added'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"<div class='metric-card'><div class='metric-val'>{total_xt:.2f}</div><div class='metric-lbl'>TOTAL xT</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='metric-card'><div class='metric-val'>{pass_xt:.2f}</div><div class='metric-lbl'>PASS xT</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='metric-card'><div class='metric-val'>{carry_xt:.2f}</div><div class='metric-lbl'>CARRY xT</div></div>", unsafe_allow_html=True)

else:
    st.write("Выберите лигу и сезон в меню слева.")
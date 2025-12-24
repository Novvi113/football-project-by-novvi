import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, PyPizza

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(page_title="Scout Master Pro", page_icon="⚽", layout="wide")
st.markdown("<style>.stApp {background-color: #0E1117; color: white;}</style>", unsafe_allow_html=True)

# --- 1. ФУНКЦИЯ ЗАГРУЗКИ (УМНАЯ) ---
@st.cache_data
def load_data(use_real_data):
    if use_real_data:
        # Ссылка на файл с ударами из твоего датасета (Parquet!)
        url = "https://huggingface.co/datasets/fadhilra101/xg-thesis/resolve/main/data/shots.parquet"
        
        try:
            # Грузим только нужные колонки, чтобы не убить память (там миллионы строк)
            # В датасете fadhilra101/xg-thesis используются эти колонки:
            columns = [
                'player_name', 'team_name', 'location', # location обычно массив [x, y]
                'shot_statsbomb_xg', 'outcome_name'
            ]
            
            # Читаем parquet
            df = pd.read_parquet(url, columns=columns)
            
            # Обработка координат (в parquet они часто массивом array([100, 40]))
            # Нам нужно разделить их на X и Y
            # Берем первые 50 000 строк для быстродействия (можно увеличить, если сервер мощный)
            df = df.sample(n=50000, random_state=42).copy()
            
            # Разделяем колонку location на X и Y
            # (Если location записан как string или list)
            def parse_loc(loc):
                try:
                    return loc[0], loc[1]
                except:
                    return 0, 0
            
            df[['x', 'y']] = df['location'].apply(lambda x: pd.Series(parse_loc(x)))
            
            # Переименовываем для удобства
            df = df.rename(columns={
                'player_name': 'player',
                'team_name': 'team',
                'shot_statsbomb_xg': 'xg',
                'outcome_name': 'result'
            })
            
            # Определяем гол (в statsbomb это 'Goal')
            df['is_goal'] = df['result'].apply(lambda x: 1 if x == 'Goal' else 0)
            
            return df
            
        except Exception as e:
            st.error(f"Ошибка загрузки реальных данных: {e}")
            st.warning("Загружаю демо-данные вместо них...")
            return generate_dummy_data()
    else:
        return generate_dummy_data()

def generate_dummy_data():
    # Фейковые данные, чтобы приложение всегда работало
    players = ['K. Mbappé', 'E. Haaland', 'H. Kane', 'Vinícius Jr.', 'M. Salah']
    teams = ['Real Madrid', 'Man City', 'Bayern', 'Real Madrid', 'Liverpool']
    
    data = []
    for _ in range(500):
        idx = np.random.randint(0, 5)
        # Симуляция: чем ближе к воротам (x=120), тем больше xG
        x = np.random.normal(100, 15)
        y = np.random.normal(40, 15)
        xg = np.clip((x - 60) / 100 * np.random.random(), 0.01, 0.99)
        is_goal = 1 if np.random.random() < xg else 0
        
        data.append({
            'player': players[idx],
            'team': teams[idx],
            'x': np.clip(x, 60, 120),
            'y': np.clip(y, 0, 80),
            'xg': xg,
            'result': 'Goal' if is_goal else 'Miss',
            'is_goal': is_goal
        })
    return pd.DataFrame(data)

# --- ИНТЕРФЕЙС ---
st.sidebar.title("🎛 Настройки")

# ГЛАВНЫЙ ПЕРЕКЛЮЧАТЕЛЬ
use_real = st.sidebar.checkbox("Использовать HuggingFace Data (Heavy)", value=False)
if use_real:
    st.sidebar.info("Загружаем данные с сервера... Это может занять 30-60 сек.")

df = load_data(use_real)

if df.empty:
    st.stop()

# Фильтры
teams = sorted(df['team'].astype(str).unique())
selected_team = st.sidebar.selectbox("Команда", teams)

team_data = df[df['team'] == selected_team]
players = sorted(team_data['player'].astype(str).unique())
selected_player = st.sidebar.selectbox("Игрок", players)

# --- ВИЗУАЛИЗАЦИЯ ---
st.title(f"Scout Report: {selected_player}")

# Данные игрока
p_data = df[df['player'] == selected_player]

if p_data.empty:
    st.warning("Нет данных по ударам для этого игрока.")
else:
    # Метрики
    goals = p_data['is_goal'].sum()
    xg_total = p_data['xg'].sum()
    shots_count = len(p_data)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Goals", int(goals))
    c2.metric("Total xG", f"{xg_total:.2f}")
    c3.metric("Shots", int(shots_count))

    # КАРТА УДАРОВ
    st.subheader("Shot Map (StatsBomb Style)")
    
    # Рисуем поле (StatsBomb использует размер 120x80)
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#0E1117', line_color='#c7d5cc')
    fig, ax = pitch.draw(figsize=(10, 6))
    
    # Промахи
    misses = p_data[p_data['is_goal'] == 0]
    pitch.scatter(misses['x'], misses['y'], ax=ax, s=(misses['xg']*500)+20, 
                  edgecolors='#606060', c='None', hatch='////', label='Miss')
    
    # Голы
    goals_df = p_data[p_data['is_goal'] == 1]
    pitch.scatter(goals_df['x'], goals_df['y'], ax=ax, s=(goals_df['xg']*500)+20, 
                  edgecolors='white', c='#d62728', marker='football', label='Goal')
    
    ax.legend(facecolor='#0E1117', edgecolor='white', labelcolor='white')
    st.pyplot(fig)

    # РАДАР (Если достаточно данных)
    if shots_count > 2:
        st.subheader("Efficiency Radar")
        # Считаем перцентили (фейковые для примера, для реальных нужно считать по всей базе)
        params = ["Goals", "xG", "Shots", "xG/Shot"]
        values = [goals, xg_total, shots_count, xg_total/shots_count]
        
        # Границы для радара
        min_vals = [0, 0, 0, 0]
        max_vals = [max(15, goals*1.5), max(10, xg_total*1.5), max(50, shots_count*1.5), 0.5]
        
        baker = PyPizza(params=params, min_range=min_vals, max_range=max_vals,
                        background_color="#0E1117", straight_line_color="#0E1117")
        fig_rad, ax_rad = baker.make_pizza(values, slice_colors=["#1A78CF"]*4,
                                           color_blank_space="same")
        fig_rad.set_facecolor('#0E1117')
        st.pyplot(fig_rad)
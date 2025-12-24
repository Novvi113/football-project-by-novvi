import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch, VerticalPitch, PyPizza

# ==========================================
# ⚙️ НАСТРОЙКИ (КОНФИГУРАЦИЯ)
# ==========================================
# Если в твоем файле другие названия колонок, поменяй их здесь!
DATA_URL = "https://huggingface.co/datasets/fadhilra101/xg-thesis/resolve/main/data/data_karyajasa.csv" # Пример прямой ссылки

COLS = {
    "player": "player_name",  # Как называется колонка с именем игрока
    "team": "team_name",      # Команда
    "x": "x",                 # Координата X (обычно 0-100 или 0-120)
    "y": "y",                 # Координата Y
    "xg": "xg",               # Значение xG
    "result": "result",       # Результат (Goal, Miss, Saved)
    "is_goal_value": "Goal"   # Как в колонке result обозначен гол?
}

# Настройка страницы
st.set_page_config(page_title="Scout Master Pro", page_icon="⚽", layout="wide")
st.markdown("<style>.stApp {background-color: #0E1117; color: white;}</style>", unsafe_allow_html=True)

# ==========================================
# 📥 ЗАГРУЗКА ДАННЫХ
# ==========================================
@st.cache_data
def load_data(url):
    try:
        # Пытаемся загрузить данные
        df = pd.read_csv(url)
        # Если координаты в формате StatsBomb (120x80), а нам нужно 100x100, можно нормализовать здесь
        # Но пока оставим как есть.
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()

# Боковая панель для загрузки своего файла (если ссылка не сработает)
st.sidebar.title("🎛 Панель управления")
user_url = st.sidebar.text_input("Вставь ссылку на CSV (или оставь пустой)", "")
actual_url = user_url if user_url else DATA_URL

df = load_data(actual_url)

if df.empty:
    st.warning("⏳ Ожидание данных... Вставьте прямую ссылку на .csv файл в меню слева.")
    st.info("Пример ссылки: https://raw.githubusercontent.com/user/repo/main/data.csv")
    st.stop() # Останавливаем выполнение, пока нет данных

# ==========================================
# 🧠 ОБРАБОТКА ДАННЫХ
# ==========================================
# Создаем колонку 'is_goal' (1 если гол, 0 если нет) для удобства
df['is_goal'] = df[COLS['result']].apply(lambda x: 1 if x == COLS['is_goal_value'] else 0)

# Фильтры
teams = sorted(df[COLS['team']].unique())
selected_team = st.sidebar.selectbox("Выберите команду", teams)

team_data = df[df[COLS['team']] == selected_team]
players = sorted(team_data[COLS['player']].unique())
selected_player = st.sidebar.selectbox("Выберите игрока", players)

# ==========================================
# 📊 ВИЗУАЛИЗАЦИЯ 1: ПРОФИЛЬ ИГРОКА (KPI)
# ==========================================
st.title(f"📊 Анализ: {selected_player}")

# Считаем статистику
p_data = df[df[COLS['player']] == selected_player]
total_goals = p_data['is_goal'].sum()
total_xg = p_data[COLS['xg']].sum()
total_shots = len(p_data)
xg_per_shot = total_xg / total_shots if total_shots > 0 else 0

# Красивые метрики в ряд
col1, col2, col3, col4 = st.columns(4)
col1.metric("Голы", total_goals)
col2.metric("Total xG", f"{total_xg:.2f}")
col3.metric("Разница (Goals - xG)", f"{total_goals - total_xg:.2f}", 
            delta_color="normal" if total_goals >= total_xg else "inverse")
col4.metric("xG на удар", f"{xg_per_shot:.2f}")

# ==========================================
# ⚽ ВИЗУАЛИЗАЦИЯ 2: КАРТА УДАРОВ (MPLSOCCER)
# ==========================================
st.subheader("📍 Карта ударов (Shot Map)")

col_viz1, col_viz2 = st.columns([2, 1])

with col_viz1:
    # Создаем футбольное поле
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#0E1117', line_color='#c7d5cc')
    fig, ax = pitch.draw(figsize=(10, 7))

    # Рисуем промахи/сейвы (полупрозрачные)
    no_goals = p_data[p_data['is_goal'] == 0]
    pitch.scatter(no_goals[COLS['x']], no_goals[COLS['y']],
                  s=(no_goals[COLS['xg']] * 700) + 50, # Размер зависит от xG
                  edgecolors='#606060', c='None', hatch='///', marker='o', 
                  alpha=0.6, ax=ax, label='Промах/Сейв')

    # Рисуем голы (яркие)
    goals = p_data[p_data['is_goal'] == 1]
    pitch.scatter(goals[COLS['x']], goals[COLS['y']],
                  s=(goals[COLS['xg']] * 700) + 50,
                  edgecolors='white', c='#d62728', marker='football', 
                  ax=ax, label='ГОЛ')

    # Легенда
    ax.legend(facecolor='#0E1117', edgecolor='white', labelcolor='white', loc='lower left')
    st.pyplot(fig)

with col_viz2:
    st.write("### Описание")
    st.write("""
    - **Красный мяч**: Гол
    - **Круг**: Удар без гола
    - **Размер круга**: Чем больше круг, тем выше xG (опасность момента).
    """)
    st.write("Последние 5 ударов:")
    st.dataframe(p_data[[COLS['result'], COLS['xg'], COLS['x'], COLS['y']]].tail(5))

# ==========================================
# 🕸 ВИЗУАЛИЗАЦИЯ 3: РАДАР (PYPIZZA)
# ==========================================
st.subheader("⚔️ Сравнение с лигой (Radar)")

# Подготовка данных для радара
# Считаем средние показатели по всем игрокам в датасете (у кого > 5 ударов)
all_stats = df.groupby(COLS['player']).agg({
    COLS['xg']: 'sum',
    'is_goal': 'sum',
    COLS['result']: 'count' # кол-во ударов
}).rename(columns={COLS['result']: 'shots'})
all_stats = all_stats[all_stats['shots'] > 5] # Отсекаем тех, кто сыграл мало

# Параметры для радара
params = ["Голы", "xG", "Удары", "xG/Удар"]
# Значения выбранного игрока
player_vals = [total_goals, total_xg, total_shots, xg_per_shot]

# Минимум и максимум по лиге (для шкал)
min_vals = [all_stats['is_goal'].min(), all_stats[COLS['xg']].min(), all_stats['shots'].min(), (all_stats[COLS['xg']]/all_stats['shots']).min()]
max_vals = [all_stats['is_goal'].max(), all_stats[COLS['xg']].max(), all_stats['shots'].max(), (all_stats[COLS['xg']]/all_stats['shots']).max()]

# Рисуем пиццу
baker = PyPizza(
    params=params,
    min_range=min_vals, max_range=max_vals,
    background_color="#0E1117", straight_line_color="#0E1117",
    last_circle_lw=0, other_circle_lw=0,
)

fig_pizza, ax_pizza = baker.make_pizza(
    player_vals,
    figsize=(6, 6),
    color_blank_space="same",
    slice_colors=["#1A78CF"] * 4,
    value_colors=["white"] * 4,
    value_bck_colors=["#1A78CF"] * 4,
    kwargs_slices=dict(edgecolor="#0E1117", zorder=2, linewidth=1),
    kwargs_params=dict(color="white", fontsize=12),
    kwargs_values=dict(color="white", fontsize=10, zorder=3, bbox=dict(edgecolor="#0E1117", facecolor="#1A78CF", boxstyle="round,pad=0.2", lw=1))
)
fig_pizza.set_facecolor('#0E1117')
st.pyplot(fig_pizza)
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import PyPizza # Это библиотека для тех самых "Пицца-чартов"

# --- 1. ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ ---
@st.cache_data
def load_and_prep_data():
    # Замените на вашу ссылку с Hugging Face
    url = "https://huggingface.co/datasets/fadhilra101/xg-thesis/resolve/main/data/data_karyajasa.csv" # Пример (проверьте точный URL файла)
    
    # Если ссылка не работает, создадим фейковые данные для теста
    try:
        df = pd.read_csv(url)
    except:
        # Фейковые данные, если файл не подгрузился
        data = {
            'player_name': ['Mbappe', 'Haaland', 'Mbappe', 'Haaland', 'Messi', 'Messi', 'Ronaldo'],
            'result': ['Goal', 'Goal', 'Saved', 'Goal', 'Goal', 'Miss', 'Goal'],
            'xg': [0.4, 0.6, 0.1, 0.8, 0.3, 0.05, 0.75]
        }
        df = pd.DataFrame(data)
        # Добавим колонку is_goal для подсчета
        df['is_goal'] = df['result'].apply(lambda x: 1 if x == 'Goal' else 0)

    # ВАЖНО: Превращаем "события" в "статистику игрока"
    # Группируем по имени игрока
    player_stats = df.groupby('player_name').agg({
        'xg': ['sum', 'mean', 'count'], # Сумма xG, средний xG, кол-во ударов
        'result': lambda x: (x == 'Goal').sum() # Сумма голов
    }).reset_index()

    # Убираем мульти-индекс колонок
    player_stats.columns = ['Player', 'Total_xG', 'xG_per_Shot', 'Shots', 'Goals']
    
    # Добавляем метрику "Финишинг" (Голы минус xG)
    player_stats['G_minus_xG'] = player_stats['Goals'] - player_stats['Total_xG']
    
    # Оставляем только тех, у кого больше 2 ударов (чтобы отсеять шум)
    player_stats = player_stats[player_stats['Shots'] > 2]
    
    return player_stats

df_stats = load_and_prep_data()

# --- 2. ИНТЕРФЕЙС ---
st.title("⚔️ Player Comparison (Radar)")

col1, col2 = st.columns(2)

# Выбор игроков
players_list = df_stats['Player'].unique().tolist()
player1 = col1.selectbox("Выберите Игрока 1", players_list, index=0)
# Пытаемся выбрать второго игрока автоматически, если он есть
idx_2 = 1 if len(players_list) > 1 else 0
player2 = col2.selectbox("Выберите Игрока 2", players_list, index=idx_2)

# --- 3. ПОСТРОЕНИЕ ГРАФИКА (PYPIZZA) ---

if player1 and player2:
    # Получаем данные для выбранных игроков
    p1_data = df_stats[df_stats['Player'] == player1].iloc[0]
    p2_data = df_stats[df_stats['Player'] == player2].iloc[0]

    # Параметры для сравнения
    params = ["Goals", "Total_xG", "Shots", "xG_per_Shot", "G_minus_xG"]
    
    # Значения
    values_p1 = [p1_data[p] for p in params]
    values_p2 = [p2_data[p] for p in params]

    # РАСЧЕТ МИНИМУМОВ И МАКСИМУМОВ (ДЛЯ НОРМАЛИЗАЦИИ)
    # Чтобы график был честным, нужно знать границы (минимум и максимум по всей лиге)
    min_range = [df_stats[p].min() for p in params]
    max_range = [df_stats[p].max() for p in params]

    # Создаем объект PyPizza
    # Это настройки цветов и стиля как в крутых приложениях
    baker = PyPizza(
        params=params,                  # Названия метрик
        min_range=min_range,            # Минимальные значения в лиге
        max_range=max_range,            # Максимальные значения в лиге
        background_color="#0E1117",     # Темный фон (под Streamlit)
        straight_line_color="#0E1117",  
        last_circle_lw=1,               # Толщина линий
        other_circle_lw=1,
        inner_circle_size=20            # Размер дырки в центре
    )

    # Рисуем график
    fig, ax = baker.make_pizza(
        values_p1,                     # Значения игрока 1
        compare_values=values_p2,      # Значения игрока 2 (для сравнения)
        figsize=(8, 8),                # Размер картинки
        color_blank_space="same",      # Заливка пустоты
        slice_colors=["#1A78CF"] * 5,  # Цвет игрока 1 (Синий)
        blank_alpha=0.4,
        
        # Настройки подписей
        kwargs_slices=dict(edgecolor="#0E1117", zorder=2, linewidth=1),
        kwargs_compare=dict(facecolor="#FF9300", edgecolor="#0E1117", zorder=2, linewidth=1, alpha=0.7), # Цвет игрока 2 (Оранжевый)
        kwargs_params=dict(color="#F2F2F2", fontsize=12, va="center"), # Цвет текста параметров
        kwargs_values=dict(color="#F2F2F2", fontsize=11, zorder=3, 
                           bbox=dict(edgecolor="#0E1117", facecolor="cornflowerblue", boxstyle="round,pad=0.2", lw=1))
    )
    
    # Добавляем легенду и заголовки вручную, так как mplsoccer рисует на Matplotlib
    fig.text(0.515, 0.975, f"{player1} vs {player2}", size=20, ha="center", color="#F2F2F2")
    
    # Легенда цветов
    fig.text(0.25, 0.93, f"🟦 {player1}", size=14, color="#1A78CF", ha="center")
    fig.text(0.75, 0.93, f"🟧 {player2}", size=14, color="#FF9300", ha="center")

    # Устанавливаем цвет фона для всей фигуры
    fig.set_facecolor('#0E1117')

    # Выводим в Streamlit
    st.pyplot(fig)

    # --- 4. ТАБЛИЦА ДЛЯ ДЕТАЛЕЙ ---
    st.markdown("### 📊 Детальные цифры")
    comparison_df = pd.DataFrame([p1_data, p2_data])
    st.dataframe(comparison_df.set_index('Player'), use_container_width=True)

else:
    st.warning("Выберите игроков для сравнения")
import streamlit as st
import pandas as pd
from statsbombpy import sb
from mplsoccer import Pitch, VerticalPitch

# --- КЭШИРОВАНИЕ ГИГАБАЙТОВ ДАННЫХ ---
@st.cache_data(ttl=3600) # Кэш живет 1 час
def load_season_data(competition_id, season_id, team_name="Barcelona"):
    # 1. Получаем список всех матчей сезона
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    
    # Фильтруем матчи только нашей команды (чтобы ускорить загрузку в 2 раза)
    team_matches = matches[(matches['home_team'] == team_name) | (matches['away_team'] == team_name)]
    
    match_ids = team_matches['match_id'].tolist()
    
    # 2. Скачиваем события ВСЕХ матчей (Это долгий процесс)
    all_events = []
    
    # Используем мультипроцессинг StatsBombPy, если доступен, или цикл
    # Для надежности делаем цикл с прогресс-баром
    progress_text = "Анализируем сезон... Скачиваем матчи..."
    my_bar = st.progress(0, text=progress_text)
    
    total = len(match_ids)
    for i, m_id in enumerate(match_ids):
        try:
            ev = sb.events(match_id=m_id)
            ev['match_id'] = m_id # Запоминаем ID матча
            
            # Добавляем инфо о сопернике и дате
            match_meta = team_matches[team_matches['match_id'] == m_id].iloc[0]
            opponent = match_meta['away_team'] if match_meta['home_team'] == team_name else match_meta['home_team']
            ev['opponent'] = opponent
            ev['match_date'] = match_meta['match_date']
            
            all_events.append(ev)
        except:
            pass # Если матч битый, пропускаем
        
        # Обновляем бар
        percent = int(((i + 1) / total) * 100)
        my_bar.progress(percent, text=f"Загрузка матча {i+1} из {total} ({opponent})")
    
    my_bar.empty() # Убираем бар
    
    # Соединяем все в один огромный DataFrame
    if all_events:
        full_df = pd.concat(all_events, ignore_index=True)
        
        # Исправляем координаты
        if 'location' in full_df.columns:
            full_df['x'] = full_df['location'].apply(lambda x: x[0] if isinstance(x, list) else None)
            full_df['y'] = full_df['location'].apply(lambda x: x[1] if isinstance(x, list) else None)
            
        return full_df
    else:
        return pd.DataFrame()

def calculate_per_90(df, player_name):
    # Считаем сыгранные минуты
    # В StatsBomb нет простой колонки "minutes played", нужно считать разницу time
    # Упростим: считаем количество матчей в старте * 90 + замены
    # Для точности возьмем просто: (Кол-во матчей * 90) - это грубо, но работает для демо
    # В идеале нужно парсить события Substitution
    
    p_events = df[df['player'] == player_name]
    matches_played = p_events['match_id'].nunique()
    minutes = matches_played * 90 # Грубая оценка
    n90 = minutes / 90.0
    
    if n90 < 1: n90 = 1.0
    
    stats = {
        "Goals": len(p_events[p_events['shot_outcome'] == 'Goal']),
        "Assists": len(p_events[p_events['pass_goal_assist'] == True]) if 'pass_goal_assist' in p_events.columns else 0,
        "Shots": len(p_events[p_events['type'] == 'Shot']),
        "Key Passes": len(p_events[p_events.get('pass_shot_assist', pd.Series(0)) == True]),
        "Dribbles": len(p_events[(p_events['type'] == 'Dribble') & (p_events['dribble_outcome'] == 'Complete')]),
        "xG": p_events['shot_statsbomb_xg'].sum() if 'shot_statsbomb_xg' in p_events.columns else 0
    }
    
    # Добавляем per 90
    stats_per_90 = {k + " p90": round(v / n90, 2) for k, v in stats.items()}
    stats.update(stats_per_90)
    stats['Matches'] = matches_played
    
    return stats
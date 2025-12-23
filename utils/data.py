import streamlit as st
from statsbombpy import sb
import pandas as pd

@st.cache_data
def get_competitions():
    return sb.competitions()

@st.cache_data
def get_matches(competition_id, season_id):
    return sb.matches(competition_id=competition_id, season_id=season_id)

@st.cache_data
def get_events(match_id):
    events = sb.events(match_id=match_id)
    
    # --- ИСПРАВЛЕНИЕ ---
    # Мы аккуратно проверяем: если это список [x, y], то берем координаты.
    # Если нет - ставим пустоту (None).
    if 'location' in events.columns:
        events['x'] = events['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else None)
        events['y'] = events['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else None)
    # -------------------
        
    return events
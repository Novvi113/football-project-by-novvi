#!/usr/bin/env python
# coding: utf-8

# In[ ]:

import os
import io

import streamlit as st
import requests
import json
import re
import matplotlib.pyplot as plt
import warnings
from pandas.errors import SettingWithCopyWarning
warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
import pandas as pd
import numpy as np
from matplotlib.colors import to_rgba
from mplsoccer import Pitch, VerticalPitch
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as path_effects
import matplotlib.patches as patches
from PIL import Image
from matplotlib import colors as mcolors

wtaimaged = Image.open("wtatransnew.png")
st.set_page_config(page_title="WT Analysis - Match Visuals", layout="wide")
st.title("WT Analysis - Match Visuals")
schedule_df = pd.DataFrame()
selected_description = None
matchlink = None
# Inputs
import pandas as pd
from datetime import datetime
matchlink = None
playername = None

# Load match schedule
import requests
import json
import re
import pandas as pd

league_dict = pd.read_excel("league_dict.xlsx")
color_options = sorted(mcolors.CSS4_COLORS.keys())

# Add four new dropdowns for home/away colors
homecolor1 = st.selectbox("Home Colour 1", color_options, index=color_options.index('red') if 'red' in color_options else 0)
homecolor2 = st.selectbox("Home Colour 2", color_options, index=color_options.index('orange') if 'orange' in color_options else 0)
awaycolor1 = st.selectbox("Away Colour 1", color_options, index=color_options.index('blue') if 'blue' in color_options else 0)
awaycolor2 = st.selectbox("Away Colour 2", color_options, index=color_options.index('yellow') if 'yellow' in color_options else 0)
# Ensure columns are strings
league_dict['Season'] = league_dict['Season'].astype(str)
league_dict['Competition'] = league_dict['Competition'].astype(str)

# Dropdown to select Season
season_options = sorted(league_dict['Season'].dropna().unique())
selected_season = st.selectbox("Select Season", ["-- Select Season --"] + season_options)

# Conditional dropdown for Competition
if selected_season != "-- Select Season --":
    competitions = league_dict[league_dict['Season'] == selected_season]['Competition'].dropna().unique()
    selected_competition = st.selectbox("Select Competition", ["-- Select Competition --"] + sorted(competitions))
else:
    selected_competition = "-- Select Competition --"

# Get the seasonid based on selected values
dataafterleague = None
if selected_season != "-- Select Season --" and selected_competition != "-- Select Competition --":
    filtered_row = league_dict[
        (league_dict['Season'] == selected_season) & 
        (league_dict['Competition'] == selected_competition)
    ]
    if not filtered_row.empty:
        dataafterleague = filtered_row.iloc[0]['seasonid']
        st.success(f"Selected competition ID: {dataafterleague}")
    else:
        st.warning("No matching competition found.")
        
headers = {
    'Referer': 'https://www.scoresway.com/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
}

schedule_df = pd.DataFrame()
selected_description = None
matchlink = None

if dataafterleague:
    # Fetch matches
    all_matches = []
    page = 1
    page_size = 400

    while True:
        callback = "W385e5c699195bebaec15e4789d8caa477937fcb98"
        schedule_url = (
            f"https://api.performfeeds.com/soccerdata/match/ft1tiv1inq7v1sk3y9tv12yh5/"
            f"?_rt=c&tmcl={dataafterleague}&live=yes&_pgSz={page_size}&_pgNm={page}"
            f"&_lcl=en&_fmt=jsonp&sps=widgets&_clbk={callback}"
        )
        response = requests.get(schedule_url, headers=headers)
        if response.status_code != 200:
            st.warning(f"Failed to retrieve page {page}. Status code: {response.status_code}")
            break

        try:
            jsonp_data = response.text
            json_str = re.search(r'\((.*)\)', jsonp_data).group(1)
            schedule_data = json.loads(json_str)
            matches = schedule_data.get('match', [])
            if not matches:
                break

            if not isinstance(matches, list):
                matches = [matches]

            for match in matches:
                match_info = match.get('matchInfo', {})
                if match_info:
                    all_matches.append({
                        'id': match_info.get('id'),
                        'description': match_info.get('description'),
                        'date': match_info.get('date'),
                        'time': match_info.get('time')
                    })
            page += 1

        except Exception as e:
            st.warning(f"Error parsing page {page}: {e}")
            break

    schedule_df = pd.DataFrame(all_matches)

# Only proceed if schedule_df is valid and has 'description'
if not schedule_df.empty and 'description' in schedule_df.columns:
    schedule_df[['Home_Team', 'Away_Team']] = schedule_df['description'].str.split(' vs ', expand=True)
    schedule_df['date'] = schedule_df['date'].str.replace('Z', '', regex=False)
    schedule_df['date'] = pd.to_datetime(schedule_df['date'], errors='coerce')
    schedule_df = schedule_df.dropna(subset=["description"])
    
    today = pd.to_datetime(datetime.today().date())
    ten_days_ago = today - pd.Timedelta(days=14)
    schedule_df = schedule_df[(schedule_df["date"] >= ten_days_ago) & (schedule_df["date"] <= today)]
    schedule_df = schedule_df.sort_values(by="date", ascending=False)

    schedule_df['formatted_date'] = schedule_df['date'].dt.strftime('%d/%m/%y')
    schedule_df['display'] = schedule_df['Home_Team'] + ' v ' + schedule_df['Away_Team'] + ' - ' + schedule_df['formatted_date']

    match_dict = dict(zip(schedule_df['display'], schedule_df['id']))
    options = ["-- Select a match --"] + schedule_df["display"].tolist()
    selected_description = st.selectbox("Select a Match", options=options)

    if selected_description != "-- Select a match --":
        if 'description' in schedule_df.columns and 'id' in schedule_df.columns:
            match_row = schedule_df[schedule_df['display'] == selected_description]
            if not match_row.empty:
                matchlink = match_row["id"].values[0]
                st.info(f"Analyzing match: {selected_description} - If error, try again later in the match! If error remains, contact WT_Analysis on Twitter/X")
            else:
                st.warning("Selected match not found in data.")
        else:
            st.error("Match data is incomplete. Please check API response or retry.")
else:
    st.info("Please select a Season and Competition to continue.")
    


if matchlink:
    #st.info(f"Analyzing {matchlink}...")

    url = f'https://api.performfeeds.com/soccerdata/matchevent/ft1tiv1inq7v1sk3y9tv12yh5/{matchlink}?_rt=c&_lcl=en&_fmt=jsonp&sps=widgets&_clbk=W351bc3acc0d0c4e5b871ac99dfbfeb44bb58ba1dc'
    headers = {
        'Referer': 'https://www.scoresway.com/',
        'User-Agent': 'Mozilla/5.0',
        'Access-Control-Allow-Origin': '*',
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        st.error("Failed to fetch match data.")
    else:
        # Clean JSONP
        cleaned_text = re.sub(r'^.*?\(', '', response.text)[:-1]
        data = json.loads(cleaned_text)
        import requests
        import json
        import re
        import matplotlib.pyplot as plt
        import warnings
        from pandas.errors import SettingWithCopyWarning
        warnings.simplefilter(action="ignore", category=SettingWithCopyWarning)
        import pandas as pd
        import numpy as np 
        from matplotlib.colors import to_rgba
        from mplsoccer import Pitch, VerticalPitch
        from matplotlib.colors import LinearSegmentedColormap
        import matplotlib.patheffects as path_effects
        import matplotlib.patches as patches

        url = f'https://api.performfeeds.com/soccerdata/matchevent/ft1tiv1inq7v1sk3y9tv12yh5/{matchlink}?_rt=c&_lcl=en&_fmt=jsonp&sps=widgets&_clbk=W351bc3acc0d0c4e5b871ac99dfbfeb44bb58ba1dc'
        headers = {
            'Referer': 'https://www.scoresway.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Expose-Headers': 'x-ms-request-id,Server,x-ms-version,Content-Type,Content-Encoding,Cache-Control,Last-Modified,ETag,Content-MD5,x-ms-lease-status,x-ms-blob-type,Content-Length,Date,Transfer-Encoding',
            'Cache-Control': 'public, max-age=14400',
            'Content-Encoding': 'gzip',
            'Content-Length': '15009',
            'Content-MD5': 'EKgP/FP+tjg8GdZEthy+Uw==',
            'Content-Type': 'application/json',
            'Cross-Origin-Resource-Policy': 'cross-origin',
            'ETag': '0x8D9DFE097F952DE',
            'Last-Modified': 'Tue, 25 Jan 2022 08:56:36 GMT',
            'Server': 'cloudflare',
            'Vary': 'Accept-Encoding',
            'X-Content-Type-Options': 'nosniff',
            'x-ms-blob-type': 'BlockBlob',
            'x-ms-lease-status': 'unlocked',
            'x-ms-request-id': '5cbacc11-901e-00a3-1e31-355feb000000',
            'x-ms-version': '2009-09-19',
        }

        # Make the request to the API
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Since it's JSONP, we need to extract the JSON content
            jsonp_data = response.text
            json_str = re.search(r'\((.*)\)', jsonp_data).group(1)  # Extract JSON part within parentheses
            data = json.loads(json_str)  # Convert JSON string to dictionary

            # Now `data` contains the JSON content from the response
            print(data)
        else:
            print(f"Failed to retrieve data. Status code: {response.status_code}")

        # Make sure you have the JSON data loaded as a dictionary in `data`
        if 'liveData' in data:
            matchevents = data['liveData']
            print(matchevents)
        else:
            print("The key 'liveData' was not found in the JSON response.")
        # Make sure you have the JSON data loaded as a dictionary in `data`
        if 'matchInfo' in data:
            matchinfo = data['matchInfo']
            print(matchinfo)
        else:
            print("The key 'liveData' was not found in the JSON response.")
        matchinfo_df = pd.json_normalize(matchinfo)
        teamdata = pd.json_normalize(matchinfo_df['contestant'].explode())
        # Select only the 'id' and 'name' columns
        teamdata = teamdata[['id', 'name']]

        # Display the resulting DataFrame

        hometeamid = teamdata.iloc[0, 0]
        awayteamid = teamdata.iloc[1, 0]
        print(hometeamid)
        print(awayteamid)
        matchevents_df = pd.json_normalize(matchevents)
        import pandas as pd
        events_expanded = pd.json_normalize(matchevents_df['event'].explode())
        def expand_qualifiers(row):
            # Each qualifier in the list will be expanded with index-based column names
            if isinstance(row, list):
                qualifiers_dict = {}
                for idx, qualifier in enumerate(row):
                    for key, value in qualifier.items():
                        qualifiers_dict[f'qualifier/{idx}/{key}'] = value
                return pd.Series(qualifiers_dict)
            return pd.Series()  # Return an empty series if there are no qualifiers
        qualifiers_expanded = events_expanded['qualifier'].apply(expand_qualifiers)
        events_expanded = events_expanded.drop(columns=['qualifier']).join(qualifiers_expanded)
        df = events_expanded
        formation_dict = pd.read_excel("formation_dict.xlsx")

        import pandas as pd
        formation_rows = df[df['typeId'] == 34]
        formation_dfs = []
        for _, row in formation_rows.iterrows():
            row_data = row.to_dict()
            contestant_id = row_data.get('contestantId', None)
            qualifier_cols = [col for col in row.index if 'qualifierId' in col]
            formation_code = None
            player_ids = []
            squad_numbers = []
            formation_positions = []
            for col in qualifier_cols:
                try:
                    qualifier_id = row[col]
                    value_col = df.columns[df.columns.get_loc(col) + 1]
                    value = row[value_col]
                    if qualifier_id == 130:
                        formation_code = value
                    elif qualifier_id == 30:
                        player_ids = str(value).split(',')
                    elif qualifier_id == 59:
                        squad_numbers = str(value).split(',')
                    elif qualifier_id == 131:
                        formation_positions = str(value).split(',')
                except:
                    continue
            num_players = len(player_ids)
            data = {
                'formation_code': [formation_code] * num_players,
                'player_id': player_ids,
                'squad_number': squad_numbers,
                'formation_position': formation_positions,
                'is_starter': ['yes' if i < 11 else 'no' for i in range(num_players)],
                'contestant_id': [contestant_id] * num_players
            }
            formation_df = pd.DataFrame(data)
            formation_dfs.append(formation_df)
        formation_dfs = pd.concat(formation_dfs, ignore_index=True)
        player_lookup = df[['playerId', 'playerName']].dropna().drop_duplicates()
        formation_dfs['player_id'] = formation_dfs['player_id'].astype(str).str.strip()
        player_lookup['playerId'] = player_lookup['playerId'].astype(str).str.strip()
        formation_dfs = formation_dfs.merge(
            player_lookup,
            left_on='player_id',
            right_on='playerId',
            how='left'
        ).drop(columns=['playerId'])
        formation_dict['formation_code'] = formation_dict['formation_code'].astype(str).str.strip()
        formation_dict_melted = formation_dict.melt(
            id_vars='formation_code',
            var_name='formation_position',
            value_name='position'
        )
        formation_dfs = formation_dfs[formation_dfs['formation_position'].notna()].copy()
        formation_dfs['formation_position'] = formation_dfs['formation_position'].astype(float).astype(int).astype(str)
        formation_dict_melted['formation_position'] = formation_dict_melted['formation_position'].astype(str)
        formation_dfs = formation_dfs.merge(
            formation_dict_melted,
            on=['formation_code', 'formation_position'],
            how='left'
        )
        formation_dfs['match_id'] = matchlink
        formation_dfs.rename(columns={'playerName': 'player_name'}, inplace=True)
        starting_lineups = formation_dfs[
            [
                'match_id',
                'contestant_id',
                'player_name',
                'squad_number',
                'position',
                'is_starter',
                'formation_position',
                'player_id'
            ]
        ]
        ## STEP 5 - subs off
        subs_off = df[df['typeId'] == 18][['playerName', 'timeMin']].dropna()
        subs_off['playerName'] = subs_off['playerName'].astype(str).str.strip()
        starting_lineups['player_name'] = starting_lineups['player_name'].astype(str).str.strip()
        starting_lineups = starting_lineups.merge(
            subs_off,
            left_on='player_name',
            right_on='playerName',
            how='left'
        ).drop(columns=['playerName'])  # drop extra merge column
        starting_lineups.rename(columns={'timeMin': 'minutes_played'}, inplace=True)
        starting_lineups['subbed_off'] = starting_lineups['minutes_played'].apply(
            lambda x: 'yes' if pd.notna(x) else 'no'
        )

        ## STEP 6 - subs on
        subs_on = df[df['typeId'] == 19][['playerName', 'timeMin']].dropna()
        subs_on['playerName'] = subs_on['playerName'].astype(str).str.strip()
        max_time = df['timeMin'].max()
        subs_on['minutes_played'] = max_time - subs_on['timeMin']
        subs_on['subbed_on'] = 'yes'
        starting_lineups['player_name'] = starting_lineups['player_name'].astype(str).str.strip()
        starting_lineups = starting_lineups.merge(
            subs_on,
            left_on='player_name',
            right_on='playerName',
            how='left'
        ).drop(columns=['playerName'])
        starting_lineups['subbed_on'] = starting_lineups['subbed_on'].fillna('no')
        starting_lineups['minutes_played'] = starting_lineups['minutes_played_x'].combine_first(starting_lineups['minutes_played_y'])
        starting_lineups.drop(columns=['minutes_played_x', 'minutes_played_y'], inplace=True)

        ################### NEW STEP
        subs_on_events = df[df['typeId'] == 19][['playerId', 'playerName']].dropna().copy()
        subs_on_events['playerId'] = subs_on_events['playerId'].astype(str).str.strip()
        subs_on_events['playerName'] = subs_on_events['playerName'].astype(str).str.strip()
        subs_on_events['event_index'] = subs_on_events.index
        formation_changes = df[df['typeId'] == 40].copy()
        formation_updates = []

        if not formation_changes.empty:
            for _, row in formation_changes.iterrows():
                row_data = row.to_dict()
                contestant_id = row_data.get('contestantId', None)
                qualifier_cols = [col for col in row.index if 'qualifierId' in col]
                formation_code = None
                player_ids = []
                formation_positions = []

                for col in qualifier_cols:
                    try:
                        qualifier_id = row[col]
                        value_col = df.columns[df.columns.get_loc(col) + 1]
                        value = row[value_col]
                        if qualifier_id == 130:
                            formation_code = str(value).strip()
                        elif qualifier_id == 30:
                            player_ids = str(value).split(',')
                        elif qualifier_id == 131:
                            formation_positions = str(value).split(',')
                    except:
                        continue

                if formation_code and player_ids and formation_positions:
                    for i, pid in enumerate(player_ids):
                        pid = pid.strip()
                        formation_position = str(i + 1)
                        formation_updates.append({
                            'player_id': pid,
                            'formation_code': formation_code,
                            'formation_position': formation_position
                        })

            if formation_updates:
                sub_positions_df = pd.DataFrame(formation_updates)
                sub_positions_df = sub_positions_df.merge(
                    formation_dict_melted,
                    on=['formation_code', 'formation_position'],
                    how='left'
                )
            else:
                print("⚠ Formation changes found but no valid updates extracted.")
                sub_positions_df = pd.DataFrame(columns=['player_id', 'formation_code', 'formation_position', 'position'])
        else:
            print("⚠ No formation changes (typeId == 40) found. Skipping formation update handling.")
            sub_positions_df = pd.DataFrame(columns=['player_id', 'formation_code', 'formation_position', 'position'])


        # Update starting_lineups with new positions (but only where position is missing)
        starting_lineups = starting_lineups.merge(
            sub_positions_df[['player_id', 'position']],
            on='player_id',
            how='left',
            suffixes=('', '_new')
        )
        starting_lineups['position'] = starting_lineups['position'].combine_first(starting_lineups['position_new'])
        starting_lineups.drop(columns=['position_new'], inplace=True)
        subs_on_events = df[df['typeId'] == 19][['playerId', 'playerName', 'contestantId']].dropna().copy()
        subs_on_events['playerId'] = subs_on_events['playerId'].astype(str).str.strip()
        subs_on_events['playerName'] = subs_on_events['playerName'].astype(str).str.strip()
        subs_on_events['event_index'] = subs_on_events.index

        for _, sub_on_row in subs_on_events.iterrows():
            idx = sub_on_row['event_index']
            team_id = sub_on_row['contestantId']
            sub_on_name = sub_on_row['playerName']

            # Find the immediately previous row with a sub-off event (typeId 18) from the same team
            for lookback in range(1, 6):
                if idx - lookback < 0:
                    break
                prev_row = df.iloc[idx - lookback]
                if prev_row['typeId'] == 18 and prev_row['contestantId'] == team_id:
                    sub_off_name = str(prev_row['playerName']).strip()

                    # Find that subbed-off player in the starting lineup
                    sub_off_row = starting_lineups[
                        (starting_lineups['player_name'] == sub_off_name) &
                        (starting_lineups['position'].notna())
                    ]
                    if sub_off_row.empty:
                        break

                    inherited_position = sub_off_row.iloc[0]['position']

                    # Assign to the subbed-on player if not already assigned
                    mask = (
                        (starting_lineups['player_name'] == sub_on_name) &
                        (starting_lineups['subbed_on'] == 'yes') &
                        (starting_lineups['position'].isna())
                    )
                    if mask.any():
                        starting_lineups.loc[mask, 'position'] = inherited_position
                    break  # stop after the first match
        ## STEP 7 - minute calc
        max_time = df['timeMin'].max()
        starting_lineups.loc[
            (starting_lineups['is_starter'] == 'yes') & (starting_lineups['subbed_off'] == 'no'),
            'minutes_played'
        ] = max_time
        starting_lineups = starting_lineups.loc[starting_lineups['player_name'] != 'nan']

        ## STEP 8 - sendings off
        cards = df[df['typeId'] == 17].copy()
        qualifier_cols = [col for col in cards.columns if 'qualifierId' in col]

        if not cards.empty:
            cards['is_sent_off'] = cards[qualifier_cols].apply(
                lambda row: any(q in [32, 33] for q in row.values if pd.notna(q)), axis=1
            )

            sent_off = cards[cards['is_sent_off']][['playerName', 'timeMin']].dropna().copy()
            sent_off.rename(columns={'playerName': 'player_name', 'timeMin': 'sent_off_min'}, inplace=True)
            sent_off['player_name'] = sent_off['player_name'].astype(str).str.strip()
        else:
            sent_off = pd.DataFrame(columns=['player_name', 'sent_off_min'])
        starting_lineups['player_name'] = starting_lineups['player_name'].astype(str).str.strip()
        starting_lineups = starting_lineups.merge(
            sent_off,
            on='player_name',
            how='left'
        )
        starting_lineups.loc[
            (starting_lineups['sent_off_min'].notna()) & (starting_lineups['is_starter'] == 'yes'),
            'minutes_played'
        ] = starting_lineups['sent_off_min']
        starting_lineups.loc[
            (starting_lineups['sent_off_min'].notna()) & (starting_lineups['is_starter'] == 'no'),
            'minutes_played'
        ] = starting_lineups['sent_off_min'] - starting_lineups['minutes_played']
        starting_lineups.drop(columns=['sent_off_min'], inplace=True)

        ## STEP 9 - player position changes
        from collections import defaultdict
        player_position_changes = defaultdict(set)
        formation_changes = df[df['typeId'] == 40].copy()
        for _, row in formation_changes.iterrows():
            row_data = row.to_dict()
            contestant_id = row_data.get('contestantId', None)
            qualifier_cols = [col for col in row.index if 'qualifierId' in col]
            formation_code = None
            player_ids = []
            formation_positions = []
            for col in qualifier_cols:
                try:
                    qualifier_id = row[col]
                    value_col = df.columns[df.columns.get_loc(col) + 1]
                    value = row[value_col]
                    if qualifier_id == 130:
                        formation_code = str(value).strip()
                    elif qualifier_id == 30:
                        player_ids = str(value).split(',')
                    elif qualifier_id == 131:
                        formation_positions = str(value).split(',')
                except:
                    continue
            if not (formation_code and player_ids and formation_positions):
                continue
            formation_snapshot = pd.DataFrame({
                'formation_code': [formation_code] * len(player_ids),
                'player_id': [pid.strip() for pid in player_ids],
                'formation_position': [str(i + 1) for i in range(len(player_ids))],
                'contestant_id': [contestant_id] * len(player_ids)
            })
            formation_snapshot = formation_snapshot.merge(
                formation_dict_melted,
                on=['formation_code', 'formation_position'],
                how='left'
            )
            for _, player_row in formation_snapshot.iterrows():
                pid = player_row['player_id']
                new_pos = player_row['position']
                if pd.isna(new_pos):
                    continue
                match = starting_lineups[
                    (starting_lineups['player_id'] == pid) &
                    (starting_lineups['contestant_id'] == contestant_id)
                ]
                if match.empty:
                    continue
                current_pos = match.iloc[0]['position']
                if pd.isna(current_pos):
                    continue
                if new_pos != current_pos:
                    player_position_changes[pid].add(new_pos)
        starting_lineups['other_positions'] = starting_lineups['player_id'].apply(
            lambda pid: ', '.join(sorted(player_position_changes[pid])) if pid in player_position_changes else None
        )
        player_position_change_times = defaultdict(dict)
        for _, row in formation_changes.iterrows():
            row_data = row.to_dict()
            contestant_id = row_data.get('contestantId', None)
            time_min = row_data.get('timeMin', None)
            time_sec = row_data.get('timeSec', None)
            period_id = row_data.get('periodId', None)
            qualifier_cols = [col for col in row.index if 'qualifierId' in col]
            formation_code = None
            player_ids = []
            formation_positions = []
            for col in qualifier_cols:
                try:
                    qualifier_id = row[col]
                    value_col = df.columns[df.columns.get_loc(col) + 1]
                    value = row[value_col]
                    if qualifier_id == 130:
                        formation_code = str(value).strip()
                    elif qualifier_id == 30:
                        player_ids = str(value).split(',')
                    elif qualifier_id == 131:
                        formation_positions = str(value).split(',')
                except:
                    continue
            if not (formation_code and player_ids and formation_positions):
                continue
            formation_snapshot = pd.DataFrame({
                'formation_code': [formation_code] * len(player_ids),
                'player_id': [pid.strip() for pid in player_ids],
                'formation_position': [str(i + 1) for i in range(len(player_ids))],
                'contestant_id': [contestant_id] * len(player_ids)
            })
            formation_snapshot = formation_snapshot.merge(
                formation_dict_melted,
                on=['formation_code', 'formation_position'],
                how='left'
            )
            for _, player_row in formation_snapshot.iterrows():
                pid = player_row['player_id']
                new_pos = player_row['position']

                if pd.isna(new_pos):
                    continue
                match = starting_lineups[
                    (starting_lineups['player_id'] == pid) &
                    (starting_lineups['contestant_id'] == contestant_id)
                ]
                if match.empty or pd.isna(match.iloc[0]['position']):
                    continue
                current_pos = match.iloc[0]['position']
                if new_pos != current_pos:
                    if new_pos not in player_position_change_times[pid]:
                        player_position_change_times[pid][new_pos] = {
                            'periodId': period_id,
                            'timeMin': time_min,
                            'timeSec': time_sec
                        }
        initial_position_lookup = starting_lineups.set_index('player_id')['position'].dropna().to_dict()
        def is_before_or_equal(change_time, row_time):
            return (
                change_time['periodId'] < row_time['periodId'] or
                (
                    change_time['periodId'] == row_time['periodId'] and
                    (
                        change_time['timeMin'] < row_time['timeMin'] or
                        (
                            change_time['timeMin'] == row_time['timeMin'] and
                            change_time['timeSec'] <= row_time['timeSec']
                        )
                    )
                )
            )
        def resolve_position(row):
            pid = str(row.get('playerId')).strip()
            if pid not in initial_position_lookup:
                return None
            current_time = {
                'periodId': row.get('periodId'),
                'timeMin': row.get('timeMin'),
                'timeSec': row.get('timeSec')
            }
            if pid not in player_position_change_times:
                return initial_position_lookup[pid]
            changes = player_position_change_times[pid]
            valid_changes = []
            for pos, change_time in changes.items():
                if is_before_or_equal(change_time, current_time):
                    valid_changes.append((change_time, pos))
            if not valid_changes:
                return initial_position_lookup[pid]
            valid_changes.sort(key=lambda x: (x[0]['periodId'], x[0]['timeMin'], x[0]['timeSec']), reverse=True)
            return valid_changes[0][1]
        df['playing_position'] = df.apply(resolve_position, axis=1)
        max_match_time = starting_lineups['minutes_played'].max()

        position_change_rows = []
        player_name_map = starting_lineups.set_index('player_id')['player_name'].to_dict()
        team_name_map = starting_lineups.set_index('player_id')['contestant_id'].to_dict()

        # Loop through position changes and create new rows
        for pid, changes in player_position_change_times.items():
            player_name = player_name_map.get(pid, None)
            team_name = team_name_map.get(pid, None)
            for pos, time_info in changes.items():
                position_change_rows.append({
                    'timeMin': time_info['timeMin'],
                    'timeSec': time_info['timeSec'],
                    'playerId': pid,
                    'playerName': player_name,
                    #'team_name': team_name,
                    'typeId': 'position_change',
                    'playing_position': pos,
                    'periodId': time_info['periodId']
                })

        # Convert to DataFrame and append to df
        position_change_df = pd.DataFrame(position_change_rows)



        # Calculate time_on for subbed-on players
        # Detect red card events using typeId == 32 or 33 in any of the columns from 17th onward
        red_card_events = df.iloc[:, 16:]
        is_red_card = red_card_events.apply(lambda row: 32 in row.values or 33 in row.values, axis=1)
        red_card_df = df[is_red_card & (df['typeId'] == 'Card')]

        # Get red card minute for each player
        red_card_times = red_card_df.groupby('playerId')['timeMin'].min().to_dict()

        # Overwrite minutes_played with red card time for those players
        for idx, row in starting_lineups.iterrows():
            player_id = row['player_id']
            if player_id in red_card_times:
                starting_lineups.at[idx, 'minutes_played'] = red_card_times[player_id]
        starting_lineups['time_on'] = starting_lineups.apply(
            lambda row: max_match_time - row['minutes_played'] if row['subbed_on'] == 'yes' and pd.notna(row['minutes_played']) else None,
            axis=1
        )
        starting_lineups['time_off'] = starting_lineups.apply(
            lambda row: row['minutes_played']
            if row['is_starter'] == 'yes' and pd.notna(row['minutes_played']) and row['minutes_played'] != max_match_time
            else None,
            axis=1
        )
        starting_lineups['time_on'] = starting_lineups['time_on'].fillna(0)
        starting_lineups['time_off'] = starting_lineups['time_off'].fillna(max_match_time)

        red_card_events = df.iloc[:, 16:]  # 0-based index, so 16 is column 17
        is_red_card = red_card_events.apply(lambda row: 32 in row.values or 33 in row.values, axis=1)
        red_card_df = df[is_red_card & (df['typeId'] == 'Card')]

        # Get first red card time per player
        red_card_times = red_card_df[['playerId', 'timeMin']].groupby('playerId').min().to_dict()['timeMin']

        # Override time_off for red-carded players
        for idx, row in starting_lineups.iterrows():
            player_id = row['player_id']
            if player_id in red_card_times:
                starting_lineups.at[idx, 'time_off'] = red_card_times[player_id]

        starting_lineups.loc[(starting_lineups['time_on'] == 0) & (starting_lineups['subbed_off'] == 'yes'), 'time_off'] = starting_lineups['minutes_played']
        # New Step: Track duration in each position per player
        from collections import defaultdict

        # Collect all changes including the initial position
        position_timeline = defaultdict(list)

        for player_id, changes in player_position_change_times.items():
            # Add initial position and time 0
            initial_pos = initial_position_lookup.get(player_id)
            if initial_pos:
                position_timeline[player_id].append((0, initial_pos))  # Assume minute 0

            # Add sorted change times
            for pos, time_data in sorted(
                changes.items(),
                key=lambda x: (x[1]['periodId'], x[1]['timeMin'], x[1]['timeSec'])
            ):
                if time_data['timeMin'] is not None:
                    position_timeline[player_id].append((time_data['timeMin'], pos))

        # Add end of match to each player's timeline
        for player_id, timeline in position_timeline.items():
            # Sort timeline just to be safe
            timeline = sorted(timeline, key=lambda x: x[0])
            updated = []
            for i in range(len(timeline)):
                start_time, pos = timeline[i]
                end_time = (
                    timeline[i+1][0] if i+1 < len(timeline)
                    else starting_lineups[starting_lineups['player_id'] == player_id]['minutes_played'].max()
                )
                duration = end_time - start_time
                updated.append((pos, duration))
            position_timeline[player_id] = updated[:5]  # Limit to 5 entries

        # Add to starting_lineups
        for i in range(5):
            pos_col = f'position{i+1}'
            min_col = f'position{i+1}mins'
            starting_lineups[pos_col] = None
            starting_lineups[min_col] = None

        for idx, row in starting_lineups.iterrows():
            player_id = row['player_id']
            match_id = row['match_id']
            player_changes = [r for r in position_change_rows if r['playerId'] == player_id]

            # Add initial position if not explicitly in change list
            if row['position'] and not any((r['timeMin'] == 0 and r['timeSec'] == 0) for r in player_changes):
                player_changes.insert(0, {
                    'playerId': player_id,
                    'playerName': row['player_name'],
                    'typeId': 'position_change',
                    'playing_position': row['position'],
                    'timeMin': row['time_on'],  # use actual time on
                    'timeSec': 0,
                    'periodId': 1
                })

            # Sort chronologically
            player_changes.sort(key=lambda r: (r['periodId'], r['timeMin'], r['timeSec']))

            # Build list of minute marks
            change_times = [r['timeMin'] + r['timeSec'] / 60 for r in player_changes]
            end_min = row['time_off']
            change_times.append(end_min)

            # Assign positions and durations
            for i in range(min(5, len(change_times) - 1)):
                pos_col = f'position{i+1}'
                mins_col = f'position{i+1}mins'
                starting_lineups.at[idx, pos_col] = player_changes[i]['playing_position']
                starting_lineups.at[idx, mins_col] = round(change_times[i+1] - change_times[i], 1)

        ## EXTRA POSITION CODE

        df = df.sort_values(by=['periodId', 'timeMin', 'timeSec']).reset_index(drop=True)

        # Group changes per player
        from collections import defaultdict
        from datetime import timedelta

        player_changes = defaultdict(list)
        for row in position_change_rows:
            pid = row['playerId']
            player_changes[pid].append({
                'timeMin': row['timeMin'],
                'timeSec': row['timeSec'],
                'periodId': row['periodId'],
                'position': row['playing_position']
            })

        # Sort each player's changes by time
        for pid in player_changes:
            player_changes[pid].sort(key=lambda x: (x['periodId'], x['timeMin'], x['timeSec']))

        # Assign positions to df rows
        for pid, changes in player_changes.items():
            player_mask = df['playerId'] == pid
            player_df = df[player_mask]

            # Get the initial position from starting_lineups
            initial_pos = starting_lineups[starting_lineups['player_id'] == pid]['position']
            if initial_pos.empty or pd.isna(initial_pos.iloc[0]):
                continue
            initial_pos = initial_pos.iloc[0]

            # First period: from time_on or period start up to first change
            first_change = changes[0]
            condition = (
                player_mask &
                (
                    (df['periodId'] < first_change['periodId']) |
                    ((df['periodId'] == first_change['periodId']) & (
                        (df['timeMin'] < first_change['timeMin']) |
                        ((df['timeMin'] == first_change['timeMin']) & (df['timeSec'] < first_change['timeSec']))
                    ))
                )
            )
            df.loc[condition, 'playing_position'] = initial_pos

            # Fill between changes
            for i in range(1, len(changes)):
                prev = changes[i-1]
                curr = changes[i]
                condition = (
                    player_mask &
                    (
                        (df['periodId'] > prev['periodId']) |
                        ((df['periodId'] == prev['periodId']) & (
                            (df['timeMin'] > prev['timeMin']) |
                            ((df['timeMin'] == prev['timeMin']) & (df['timeSec'] >= prev['timeSec']))
                        ))
                    ) &
                    (
                        (df['periodId'] < curr['periodId']) |
                        ((df['periodId'] == curr['periodId']) & (
                            (df['timeMin'] < curr['timeMin']) |
                            ((df['timeMin'] == curr['timeMin']) & (df['timeSec'] < curr['timeSec']))
                        ))
                    )
                )
                df.loc[condition, 'playing_position'] = prev['position']

            # Fill from last change to end of match
            last = changes[-1]
            condition = (
                player_mask &
                (
                    (df['periodId'] > last['periodId']) |
                    ((df['periodId'] == last['periodId']) & (
                        (df['timeMin'] > last['timeMin']) |
                        ((df['timeMin'] == last['timeMin']) & (df['timeSec'] >= last['timeSec']))
                    ))
                )
            )
            df.loc[condition, 'playing_position'] = last['position']


        #DF WORK
        import os
        import streamlit as st
        import pandas as pd
        
        # Show current directory contents for debugging
        
        # Safe load for 'Opta Events.xlsx'
        try:
            events = pd.read_excel("Opta Events.xlsx")
            #st.success("✅ Loaded 'Opta Events.xlsx'")
            event_map = dict(zip(events["Code"], events["Event"]))
        except FileNotFoundError:
            st.error("❌ File 'Opta Events.xlsx' not found. Please upload or check your repo.")
            events = pd.DataFrame()
            event_map = {}
        except Exception as e:
            st.error(f"⚠️ Error loading 'Opta Events.xlsx': {e}")
            events = pd.DataFrame()
            event_map = {}
        qualifiers = pd.read_excel("Opta Qualifiers.xlsx")
        #teamdata = pd.read_csv(r"C:\Users\will-\OneDrive\Documents\WT Analysis\Scoresway\Team Log\teamlog.csv")
        event_map = dict(zip(events["Code"], events["Event"]))
        qualifier_map = dict(zip(qualifiers["Code"], qualifiers["Qualifier"]))
        df = df.iloc[:, :100]
        if 'assist' not in df.columns:
            df['assist'] = 0  # or np.nan if you prefer missing values
        df["typeId"] = df["typeId"].map(event_map).fillna(df["typeId"])
        
        # Build the requested qualifier column names (0..15), then keep only those present
        qualifier_columns_requested = [f"qualifier/{i}/qualifierId" for i in range(16)]
        qualifier_cols = [c for c in qualifier_columns_requested if c in df.columns]
        
        # Map qualifier ids -> names only on existing columns
        if qualifier_cols:
            df[qualifier_cols] = df[qualifier_cols].applymap(lambda x: qualifier_map.get(x, x))
        
        # The rest of your transformations
        df["outcome"] = df["outcome"].replace({0: "Unsuccessful", 1: "Successful"})
        df.rename(columns={"contestantId": "team_name"}, inplace=True)
        df = df.merge(teamdata[["id", "name"]], how="left", left_on="team_name", right_on="id")
        df.drop(columns=["team_name", "id_y"], inplace=True)
        df.rename(columns={"name": "team_name", "id_x": "id"}, inplace=True)
        
        # -------- Pass End X / Y extraction (robust to missing qualifier slots) --------
        # Ensure end_x/end_y exist
        if "end_x" not in df.columns:
            df["end_x"] = pd.NA
        if "end_y" not in df.columns:
            df["end_y"] = pd.NA
        
        # Dynamically determine max qualifier index from existing columns
        qualifier_indices = [
            int(m.group(1)) for col in df.columns
            if (m := re.match(r"qualifier/(\d+)/", col))
        ]
        max_index = max(qualifier_indices, default=-1)  # -1 so the loop is skipped if none
        
        # Loop over present qualifier slots
        for i in range(max_index + 1):
            value_col = f"qualifier/{i}/value"
            id_col = f"qualifier/{i}/qualifierId"
            if value_col not in df.columns or id_col not in df.columns:
                continue
        
            end_x_mask = df[id_col] == "Pass End X"
            end_y_mask = df[id_col] == "Pass End Y"
        
            df.loc[end_x_mask, "end_x"] = pd.to_numeric(df.loc[end_x_mask, value_col], errors="coerce")
            df.loc[end_y_mask, "end_y"] = pd.to_numeric(df.loc[end_y_mask, value_col], errors="coerce")
        
        # Final clean up for end coords
        df["end_x"] = df["end_x"].fillna(0)
        df["end_y"] = df["end_y"].fillna(0)
        
        # -------- Qualifier-driven flags (safe even if no qualifier columns exist) --------
        def has_qual(label: str) -> pd.Series:
            if qualifier_cols:
                # vectorized: check if any qualifier col equals the label on each row
                return df[qualifier_cols].eq(label).any(axis=1).astype(int)
            else:
                return pd.Series(0, index=df.index, dtype=int)
        
        df["throwin"]       = has_qual("Throw-in")
        df["corner"]        = has_qual("Corner taken")
        df["freekick"]      = has_qual("Free-kick taken")
        df["goalkick"]      = has_qual("Goal Kick")
        df["cross"]         = has_qual("Cross")
        df["longball"]      = has_qual("Long ball")
        df["switch"]        = has_qual("Switch of play")
        df["launch"]        = has_qual("Launch")
        df["secondassist"]  = has_qual("2nd assist")
        df["head"]          = has_qual("Head")
        df["leftfoot"]      = has_qual("Left footed")
        df["rightfoot"]     = has_qual("Right footed")
        df["otherbody"]     = has_qual("Other body part")
        df["fastbreakshot"] = has_qual("Fast break")
        df["setpieceshot"]  = has_qual("Set piece")
        df["freekickshot"]  = has_qual("Free kick")
        df["cornershot"]    = has_qual("From corner")
        df["throwinshot"]   = has_qual("Throw-in set piece")
        df["dfreekickshot"] = has_qual("Direct free")
        df["penaltyshot"]   = has_qual("Penalty")
        df["bigchance"]     = has_qual("Big chance")
        df["hitwoodwork"]   = has_qual("Hit woodwork")
        df["lastman"]       = has_qual("Last line")
        df["errorshot"]     = has_qual("Leading to attempt")
        df["errorgoal"]     = has_qual("Leading to goal")
        df["yellowcard"]    = has_qual("Yellow Card")
        df["yellowcard2"]   = has_qual("Second yellow")
        df["redcard"]       = has_qual("Red Card")
        df["shotblocked"]   = has_qual("Blocked")
        
        # Own goal detection (same logic as before, but scoped to qualifier cols)
        if qualifier_cols:
            df["owngoal"] = df[qualifier_cols].apply(
                lambda row: any(
                    isinstance(v, str) and v.strip().lower() in {"own goal", "own_goal"}
                    for v in row.values
                ),
                axis=1
            ).astype(int)
        else:
            df["owngoal"] = 0
        
        df.loc[df["owngoal"] == 1, "typeId"] = "Own Goal"
        df = df.loc[df['typeId'] !=40]
        df = df.loc[df['typeId'] !="Deleted event"]

        values_to_remove = ['Collection End', 'End', 'Team set up', 'Start']
        df = df[~df['typeId'].isin(values_to_remove)]
        columns_to_keep = ['id', 'eventId', 'typeId', 'periodId', 'timeMin', 'timeSec',
                           'team_name', 'outcome', 'x', 'y', 'end_x', 'end_y', 
                           'playerName','playing_position', 'keyPass', 'secondassist','assist',
                          'throwin','corner','freekick','goalkick','cross','longball','switch','launch',
                          'head','leftfoot','rightfoot','otherbody',
                          'fastbreakshot','setpieceshot','freekickshot','cornershot','throwinshot','dfreekickshot','penaltyshot','owngoal',
                           'bigchance','hitwoodwork','lastman','errorshot','errorgoal', 'yellowcard','yellowcard2','redcard','shotblocked']
        df = df[columns_to_keep]
        df['end_x'] = ((df['end_x'] - df['end_x'].min()) / (df['end_x'].max() - df['end_x'].min())) * 100
        df['end_y'] = ((df['end_y'] - df['end_y'].min()) / (df['end_y'].max() - df['end_y'].min())) * 100
        df.loc[df['owngoal'] == 1, 'typeId'] = 'Own Goal'
        # Shift playerName and team_name columns by -1 (next row)
        df['next_player'] = df['playerName'].shift(-1)
        df['next_team'] = df['team_name'].shift(-1)
        df['next_position'] = df['playing_position'].shift(-1)
                # Create pass_recipient only for successful passes to same team
        df['pass_recipient'] = np.where(
            (df['typeId'] == 'Pass') & 
            (df['outcome'] == 'Successful') & 
            (df['team_name'] == df['next_team']),
            df['next_player'],
            np.nan
            )
        df['pass_recipient_position'] = np.where(
            (df['typeId'] == 'Pass') & 
            (df['outcome'] == 'Successful') & 
            (df['team_name'] == df['next_team']),
            df['next_position'],
            np.nan
            )
        df = df[df['typeId'].notna()].reset_index(drop=True)
        mask = df['typeId'] == 'Ball recovery'
        df.loc[mask, 'end_x'] = df.loc[mask, 'x']
        df.loc[mask, 'end_y'] = df.loc[mask, 'y']
        ##CARRY
        df['event_time'] = df['timeMin'] * 60 + df['timeSec']
        df = df.sort_values(by=['event_time', 'id']).reset_index(drop=True)
        df = df.loc[df['periodId'] != 5]
        carry_rows = []
        for i in range(len(df) - 1):
            current = df.iloc[i]
            current_team = current['team_name']
            current_player = current['playerName']
            end_x = current['end_x']
            end_y = current['end_y']
            current_type = current['typeId']
            current_outcome = current['outcome']
            is_pass = (current_type == 'Pass' and current_outcome == 'Successful')
            is_recovery = (current_type == 'Ball recovery' and current_outcome == 'Successful')
            is_interception = (current_type == 'Interception')
            is_take_on = (current_type == 'Take on' and current_outcome == 'Successful')
            if not (is_pass or is_recovery or is_interception or is_take_on):
                continue
            for j in range(i + 1, len(df)):
                next_row = df.iloc[j]
                if next_row['team_name'] != current_team:
                    continue
                if (end_x == next_row['x']) and (end_y == next_row['y']):
                    break
                if next_row['typeId'] == 'Aerial':
                    break
                if (is_recovery or is_interception or is_take_on) and current_player != next_row['playerName']:
                    break
                carry_row = current.copy()
                carry_row['id'] = current['id'] + 0.5
                carry_row['eventId'] = current['eventId'] + 0.5
                carry_row['typeId'] = 'Carry'
                carry_row['x'] = end_x
                carry_row['y'] = end_y
                carry_row['end_x'] = next_row['x']
                carry_row['end_y'] = next_row['y']
                carry_row['playerName'] = next_row['playerName']
                carry_row['playing_position'] = next_row['playing_position']
                carry_row['outcome'] = 'Successful'
                carry_rows.append(carry_row)
                break
        df = pd.concat([df, pd.DataFrame(carry_rows)], ignore_index=True)
        df = df.sort_values(by=['timeMin', 'timeSec', 'periodId']).reset_index(drop=True)
        df = df[~((df['typeId'] == 'Carry') & (df['x'] == 0) & (df['y'] == 0))].reset_index(drop=True)
        df = df[~((df['typeId'] == 'Carry') & (df['end_x'] == 0) & (df['end_y'] == 0))].reset_index(drop=True)
        #to_delete = []
        #for i in range(len(df) - 1):
        #    if df.iloc[i]['typeId'] == 'Carry' and df.iloc[i + 1]['typeId'] == 'Ball recovery':
        #        to_delete.append(i)  # Add the index of the 'Carry' row to delete
        #df = df.drop(index=to_delete).reset_index(drop=True)
        df.loc[df['typeId'] == 'Carry', 'pass_recipient'] = np.nan
        carry_filter = ~(
            (df['typeId'] == 'Carry') &
            ((df['x'] - df['end_x']).abs() < 1.5) &
            ((df['y'] - df['end_y']).abs() < 2.5)
        )
        df = df[carry_filter]
        df.loc[df['typeId'] == 'Carry', ['keyPass', 'assist']] = np.nan
        #XTHREAT
        xT = np.array([[0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ]])
        xT_rows, xT_cols = xT.shape
        x_bins = np.linspace(0, 100, xT_cols + 1)  # 12 bins for x-axis
        y_bins = np.linspace(0, 100, xT_rows + 1)  # 8 bins for y-axis
        df['x1_bin'] = pd.cut(df['x'], bins=x_bins, labels=False)
        df['y1_bin'] = pd.cut(df['y'], bins=y_bins, labels=False)
        df['x2_bin'] = pd.cut(df['end_x'], bins=x_bins, labels=False)
        df['y2_bin'] = pd.cut(df['end_y'], bins=y_bins, labels=False)
        passingthreat = df.loc[(df['typeId'] == 'Pass') & (df['outcome'] == 'Successful')]
        passingthreat = passingthreat.loc[passingthreat['x'] < 99.49]
        passingthreat = passingthreat.dropna(subset=['x1_bin', 'y1_bin', 'x2_bin', 'y2_bin'])
        passingthreat['x1_bin'] = passingthreat['x1_bin'].astype(int)
        passingthreat['y1_bin'] = passingthreat['y1_bin'].astype(int)
        passingthreat['x2_bin'] = passingthreat['x2_bin'].astype(int)
        passingthreat['y2_bin'] = passingthreat['y2_bin'].astype(int)
        passingthreat['xT_value'] = passingthreat.apply(
            lambda row: xT[row['y2_bin']][row['x2_bin']] - xT[row['y1_bin']][row['x1_bin']], 
            axis=1
        )
        passthreattotal = passingthreat.groupby('playerName')['xT_value'].sum().reset_index()
        carrythreat = df.loc[df['typeId'] == 'Carry']
        carrythreat['y_diff'] = carrythreat['y'] - carrythreat['end_y']
        carrythreat['x_diff'] = carrythreat['x'] - carrythreat['end_x']

        carrythreat = carrythreat.dropna(subset=['x1_bin', 'y1_bin', 'x2_bin', 'y2_bin'])
        carrythreat['x1_bin'] = carrythreat['x1_bin'].astype(int)
        carrythreat['y1_bin'] = carrythreat['y1_bin'].astype(int)
        carrythreat['x2_bin'] = carrythreat['x2_bin'].astype(int)
        carrythreat['y2_bin'] = carrythreat['y2_bin'].astype(int)
        carrythreat['xT_value'] = carrythreat.apply(
            lambda row: xT[row['y2_bin']][row['x2_bin']] - xT[row['y1_bin']][row['x1_bin']], 
            axis=1
        )
        carrythreattotal = carrythreat.groupby('playerName')['xT_value'].sum().reset_index()
        df['id'] = df['id'].astype(str)
        passingthreat['id'] = passingthreat['id'].astype(str)
        df = df.merge(
            passingthreat[['id', 'xT_value']],
            on='id',
            how='left'
        )
        carrythreat['id'] = carrythreat['id'].astype(str)
        carrythreat['eventId'] = carrythreat['eventId'].astype(str)
        df['id'] = df['id'].astype(str)
        df['eventId'] = df['eventId'].astype(str)
        df = df.merge(
            carrythreat[['id', 'eventId', 'xT_value']],
            on=['id', 'eventId'],
            how='left',
            suffixes=('', '_carry')
        )
        df['xT_value'] = df['xT_value'].combine_first(df['xT_value_carry'])
        df.drop(columns=['xT_value_carry'], inplace=True)
        df['assist_xt'] = 0
        df.loc[df['keyPass'] == 1, 'assist_xt'] = 0.1
        df.loc[df['assist'] == 1, 'assist_xt'] = 0.6
        shotassisttotal = df.groupby('playerName', as_index=False)['assist_xt'].sum()
        shotassisttotal.rename(columns={'assist_xt': 'xT_value'}, inplace=True)
        shotassisttotal = shotassisttotal.loc[shotassisttotal['xT_value']>0]
        teamname = teamdata.iloc[0, 1]
        opponentname = teamdata.iloc[1,1]
        RPxT = np.array([[0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ]])
        RPxT_rows, RPxT_cols = RPxT.shape
        distinct_teams = df['team_name'].dropna().unique()
        teamsinmatch = teamdata[teamdata['name'].isin(distinct_teams)].copy()
        teamsinmatch.rename(columns={'name': 'team'}, inplace=True)
        teamsinmatch = teamsinmatch[['id', 'team']]
        teamname = teamsinmatch.iloc[0, 1]
        recthreattest = df.loc[df['team_name']==teamname]
        recthreattest = recthreattest.loc[recthreattest['end_x']>50]
        receivedpasshome = recthreattest[(recthreattest['typeId'] == 'Pass') & (recthreattest['outcome'] == 'Successful')]
        receivedpasshome['recipient'] = recthreattest['playerName'].shift(-1)
        receivedpasshome['x2_bin'] = pd.cut(receivedpasshome['end_x'], bins=RPxT_cols, labels=False)
        receivedpasshome['y2_bin'] = pd.cut(receivedpasshome['end_y'], bins=RPxT_rows, labels=False)
        receivedpasshome['xT_value'] = receivedpasshome[['x2_bin', 'y2_bin']].apply(lambda x: RPxT[x[1]][x[0]], axis=1)
        recpassh = receivedpasshome.groupby('recipient')['xT_value'].sum().reset_index()
        recpassh.rename(columns={'recipient': 'playerName'}, inplace=True)
        recthreattest = df.loc[df['team_name']!=teamname]
        recthreattest = recthreattest.loc[recthreattest['end_x']>50]
        receivedpassaway = recthreattest[(recthreattest['typeId'] == 'Pass') & (recthreattest['outcome'] == 'Successful')]
        receivedpassaway['recipient'] = recthreattest['playerName'].shift(-1)
        receivedpassaway['x2_bin'] = pd.cut(receivedpassaway['end_x'], bins=RPxT_cols, labels=False)
        receivedpassaway['y2_bin'] = pd.cut(receivedpassaway['end_y'], bins=RPxT_rows, labels=False)
        receivedpassaway['xT_value'] = receivedpassaway[['x2_bin', 'y2_bin']].apply(lambda x: RPxT[x[1]][x[0]], axis=1)
        recpassa = receivedpassaway.groupby('recipient')['xT_value'].sum().reset_index()
        recpassa.rename(columns={'recipient': 'playerName'}, inplace=True)
        receivedpasses = pd.concat([recpassh, recpassa], ignore_index=True)
        receivedpassestotal = receivedpasses.groupby('playerName')['xT_value'].sum().reset_index()
        RPxT = np.array([[0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ]])
        RPxT_rows, RPxT_cols = RPxT.shape
        recthreattest = df.loc[df['team_name']==teamname]
        recthreattest = recthreattest.loc[recthreattest['end_x']>50]
        receivedpasshome = recthreattest[(recthreattest['typeId'] == 'Pass') & (recthreattest['outcome'] == 'Successful')]
        receivedpasshome['x2_bin'] = pd.cut(receivedpasshome['end_x'], bins=RPxT_cols, labels=False)
        receivedpasshome['y2_bin'] = pd.cut(receivedpasshome['end_y'], bins=RPxT_rows, labels=False)
        receivedpasshome['xT_value'] = receivedpasshome[['x2_bin', 'y2_bin']].apply(lambda x: RPxT[x[1]][x[0]], axis=1)
        recpassh = receivedpasshome.groupby('pass_recipient')['xT_value'].sum().reset_index()
        recpassh.rename(columns={'pass_recipient': 'playerName'}, inplace=True)
        recthreattest = df.loc[df['team_name']!=teamname]
        recthreattest = recthreattest.loc[recthreattest['end_x']>50]
        receivedpassaway = recthreattest[(recthreattest['typeId'] == 'Pass') & (recthreattest['outcome'] == 'Successful')]
        receivedpassaway['x2_bin'] = pd.cut(receivedpassaway['end_x'], bins=RPxT_cols, labels=False)
        receivedpassaway['y2_bin'] = pd.cut(receivedpassaway['end_y'], bins=RPxT_rows, labels=False)
        receivedpassaway['xT_value'] = receivedpassaway[['x2_bin', 'y2_bin']].apply(lambda x: RPxT[x[1]][x[0]], axis=1)
        recpassa = receivedpassaway.groupby('pass_recipient')['xT_value'].sum().reset_index()
        recpassa.rename(columns={'pass_recipient': 'playerName'}, inplace=True)
        receivedpasses = pd.concat([recpassh, recpassa], ignore_index=True)
        receivedpassestotal = receivedpasses.groupby('playerName')['xT_value'].sum().reset_index()
        eventstoinclude = ['Tackle',
                           'Aerial',
                           'Challenge',
                           'Interception',
                           'Blocked Pass',
                           'Clearance',
                           'Ball recovery'
                          ]
        df_events_def = df[df['typeId'].isin(eventstoinclude)]
        xT = np.array([[0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.00941056, 0.01082722, 0.01016549, 0.01132376, 0.01262646,
                                0.01484598, 0.01689528, 0.0199707 , 0.02385149, 0.03511326,
                                0.10805102, 0.25745362],
                               [0.0088799 , 0.00977745, 0.01001304, 0.01110462, 0.01269174,
                                0.01429128, 0.01685596, 0.01935132, 0.0241224 , 0.02855202,
                                0.05491138, 0.06442595],
                               [0.00750072, 0.00878589, 0.00942382, 0.0105949 , 0.01214719,
                                0.0138454 , 0.01611813, 0.01870347, 0.02401521, 0.02953272,
                                0.04066992, 0.04647721],
                               [0.00638303, 0.00779616, 0.00844854, 0.00977659, 0.01126267,
                                0.01248344, 0.01473596, 0.0174506 , 0.02122129, 0.02756312,
                                0.03485072, 0.0379259 ]])
        xT_rows, xT_cols = xT.shape
        df_events_def['x'] = 105 - df_events_def['x']
        df_events_def['end_x'] = 105 - df_events_def['end_x']
        df_events_def['x1_bin'] = pd.cut(df_events_def['x'], bins=xT_cols, labels=False)
        df_events_def['y1_bin'] = pd.cut(df_events_def['y'], bins=xT_rows, labels=False)
        df_events_def['xT_value'] = df_events_def[['x1_bin', 'y1_bin']].apply(lambda x: xT[x[1]][x[0]], axis=1)
        df_events_def['xT_value'] = df_events_def.apply(lambda row: row['xT_value'] * -1 if row['outcome'] == 'Unsuccessful' else row['xT_value'], axis=1)
        defthreattotal = df_events_def.groupby('playerName')['xT_value'].sum().reset_index()
        df = df.merge(
            df_events_def[['id', 'xT_value']],
            on='id',
            how='left',
            suffixes=('', '_carry')
        )
        df['xT_value'] = df['xT_value'].combine_first(df['xT_value_carry'])
        df.drop(columns=['xT_value_carry'], inplace=True)
        IPxT = np.array([[0.01, 0.012, 0.013, 0.015, 0.017,
                        0.018, 0.02, 0.022 , 0.025, 0.02756312,
                        0.03485072, 0.0379259 ],
                       [0.012, 0.01378589, 0.01442382, 0.0155949 , 0.01714719,
                        0.0188454 , 0.02111813, 0.02370347, 0.02701521, 0.02953272,
                        0.04066992, 0.04647721],
                       [0.01388799 , 0.01477745, 0.01501304, 0.01610462, 0.01869174,
                        0.020, 0.02285596, 0.02535132, 0.031224 , 0.0455202,
                        0.05491138, 0.06442595],
                       [0.02941056, 0.03082722, 0.03216549, 0.03432376, 0.0462646,
                        0.04784598, 0.0589528, 0.0699707 , 0.07385149, 0.08511326,
                        0.10805102, 0.25745362],
                       [0.02941056, 0.03082722, 0.03216549, 0.03432376, 0.0462646,
                        0.04784598, 0.0589528, 0.0699707 , 0.07385149, 0.08511326,
                        0.10805102, 0.25745362],
                       [0.01388799 , 0.01477745, 0.01501304, 0.01610462, 0.01869174,
                        0.020, 0.02285596, 0.02535132, 0.031224 , 0.0455202,
                        0.05491138, 0.06442595],
                       [0.012, 0.01378589, 0.01442382, 0.0155949 , 0.01714719,
                        0.0188454 , 0.02111813, 0.02370347, 0.02701521, 0.02953272,
                        0.04066992, 0.04647721],
                       [0.01, 0.012, 0.013, 0.015, 0.017,
                        0.018, 0.02, 0.022 , 0.025, 0.02756312,
                        0.03485072, 0.0379259 ]])
        IPxT_rows, IPxT_cols = IPxT.shape
        incompletepasses = df.loc[(df['typeId'] == 'Pass') & (df['outcome'] == 'Unsuccessful')]
        incompletepasses['x'] = 105 - incompletepasses['x']
        incompletepasses['end_x'] = 105 - incompletepasses['end_x']
        incompletepasses['x1_bin'] = pd.cut(incompletepasses['x'], bins=IPxT_cols, labels=False)
        incompletepasses['y1_bin'] = pd.cut(incompletepasses['y'], bins=IPxT_rows, labels=False)
        incompletepasses['xT_value'] = incompletepasses[['x1_bin', 'y1_bin']].apply(lambda x: IPxT[x[1]][x[0]], axis=1)
        incompletepasses['xT_value'] = incompletepasses['xT_value']*-1
        incomppasstotal = incompletepasses.groupby('playerName')['xT_value'].sum().reset_index()
        df = df.merge(
            incompletepasses[['id', 'xT_value']],
            on='id',
            how='left',
            suffixes=('', '_carry')
        )
        df['xT_value'] = df['xT_value'].combine_first(df['xT_value_carry'])
        df.drop(columns=['xT_value_carry'], inplace=True)
        df['card_value'] = 0
        df.loc[df['yellowcard'] == 1, 'card_value'] = -0.275
        df.loc[df['yellowcard2'] == 1, 'card_value'] = -0.525
        df.loc[df['redcard'] == 1, 'card_value'] = -0.8
        cards_df = df.groupby('playerName', as_index=False)['card_value'].sum()
        cards_df = cards_df.rename(columns={'card_value': 'xT_value'})

        #### SHOTS

        shotstaken = df[df['typeId'].isin(['Miss', 'Goal', 'Attempt Saved'])]

        # Optionally reset the index
        shotstaken = shotstaken.reset_index(drop=True)
        # Make sure shotstaken DataFrame already exists as per your previous step

        # Add a new column 'xT_value' with default NaN (optional)
        # Make sure shotstaken DataFrame already exists as per your previous step

        # Add a new column 'xT_value' with default NaN (optional)
        shotstaken['xT_value'] = None

        # Assign values based on typeId
        shotstaken.loc[shotstaken['typeId'] == 'Goal', 'xT_value'] = 0.95
        shotstaken.loc[shotstaken['typeId'] == 'Attempt Saved', 'xT_value'] = 0.2
        shotstaken.loc[shotstaken['typeId'] == 'Miss', 'xT_value'] = 0.05
        shotstaken.loc[shotstaken['shotblocked'] == 1, 'xT_value'] = 0.05

        # Optionally convert xT_value to float type
        shotstaken['xT_value'] = shotstaken['xT_value'].astype(float)

        shotstakentotal = shotstaken.groupby('playerName')['xT_value'].sum().reset_index()
        df = df.merge(
            shotstaken[['id', 'xT_value']],
            on='id',
            how='left',
            suffixes=('', '_carry')
        )
        df['xT_value'] = df['xT_value'].combine_first(df['xT_value_carry'])
        df.drop(columns=['xT_value_carry'], inplace=True)

        ##GOALS CONCEDED
        starting_lineups = starting_lineups.merge(teamdata, left_on='contestant_id', right_on='id', how='left')
        starting_lineups.rename(columns={'name': 'team_name'}, inplace=True)

        # Ensure numeric columns for time comparisons
        starting_lineups['time_on'] = pd.to_numeric(starting_lineups['time_on'])
        starting_lineups['time_off'] = pd.to_numeric(starting_lineups['time_off'])

        # Step 1: Add goal event info from df
        goal_events = df[df['typeId'].isin(['Goal', 'Own Goal'])].copy()
        goal_events['minute'] = pd.to_numeric(goal_events['timeMin'], errors='coerce')

        # Step 2: Identify the two team names in the match
        team_names = df['team_name'].dropna().unique()

        # Step 3: Assign team_goal column
        goal_events['team_goal'] = goal_events.apply(
            lambda row: row['team_name'] if row['typeId'] == 'Goal'
            else (
                [team for team in team_names if team != row['team_name']][0]
                if row['typeId'] == 'Own Goal' else None
            ),
            axis=1
        )

        # Step 4: Calculate goals scored/conceded per player
        def get_goals_for_and_against(player_row):
            time_on = player_row['time_on']
            time_off = player_row['time_off']
            player_team = player_row['team_name']

            active_goals = goal_events[
                (goal_events['minute'] >= time_on) &
                (goal_events['minute'] <= time_off)
            ]

            goals_for = (active_goals['team_goal'] == player_team).sum()
            goals_against = (active_goals['team_goal'] != player_team).sum()

            return pd.Series({'goals_scored': goals_for, 'goals_conceded': goals_against})

        # Apply the goal calculations to starting_lineups
        starting_lineups[['goals_scored', 'goals_conceded']] = starting_lineups.apply(get_goals_for_and_against, axis=1)
        def calculate_xt_value(row):
            pos = row['position']
            mins = row['minutes_played']
            goals_conceded = row['goals_conceded']
            if any(p in pos for p in ['LB', 'CB', 'RB', 'RWB', 'LWB']):
                if mins > 60 and goals_conceded == 0:
                    return 0.4
                else:
                    return goals_conceded * -0.2
            elif 'M' in pos:
                if mins > 60 and goals_conceded == 0:
                    return 0.1
                else:
                    return goals_conceded * -0.05
            return 0  # or you can set to None if not applicable





        goal_conceded_rows = []

        # Create player lookup maps
        player_name_map = starting_lineups.set_index('player_id')['player_name'].to_dict()
        team_name_map = starting_lineups.set_index('player_id')['team_name'].to_dict()

        # Get the two teams in the match
        team_names = df['team_name'].dropna().unique()

        # Identify the team that conceded each goal
        goal_events = goal_events.copy()
        goal_events['conceding_team'] = goal_events.apply(
            lambda row: (
                [team for team in team_names if team != row['team_name']][0]
                if row['typeId'] == 'Goal'
                else row['team_name']  # for Own Goal, the team credited with the own goal conceded it
            ),
            axis=1
        )

        # Iterate through each goal
        for _, goal_row in goal_events.iterrows():
            conceded_team = goal_row['conceding_team']
            goal_minute = goal_row['timeMin']
            goal_sec = goal_row['timeSec']
            goal_period = goal_row['periodId']

            # Get all players from the conceding team who were on the pitch at the time
            active_players = starting_lineups[
                (starting_lineups['team_name'] == conceded_team) &
                (starting_lineups['time_on'] <= goal_minute) &
                (starting_lineups['time_off'] >= goal_minute)
            ]

            for _, player in active_players.iterrows():
                pid = player['player_id']
                player_name = player['player_name']
                team_name = player['team_name']

                # Get most recent position using the resolve_position function
                playing_pos = resolve_position({
                    'playerId': pid,
                    'periodId': goal_period,
                    'timeMin': goal_minute,
                    'timeSec': goal_sec
                })

                # Fallback if position is not found
                if pd.isna(playing_pos) or not playing_pos:
                    xt_val = 0
                else:
                    if any(p in playing_pos for p in ['LB', 'CB', 'RB', 'RWB', 'LWB']):
                        xt_val = -0.2
                    elif 'M' in playing_pos:
                        xt_val = -0.05
                    else:
                        xt_val = 0

                goal_conceded_rows.append({
                    'playerName': player_name,
                    'team_name': team_name,
                    'timeMin': goal_minute,
                    'timeSec': goal_sec,
                    'periodId': goal_period,
                    'playing_position': playing_pos,
                    'typeId': 'goal_conceded',
                    'xT_value': xt_val
                })

        # Convert and deduplicate
        goal_conceded_df = pd.DataFrame(goal_conceded_rows)
        goal_conceded_df = goal_conceded_df.drop_duplicates(
            subset=['periodId', 'timeMin', 'timeSec', 'playerName', 'team_name']
        )

        # Ensure all columns match df
        for col in df.columns:
            if col not in goal_conceded_df.columns:
                goal_conceded_df[col] = None

        # Append to main df
        df = pd.concat([df, goal_conceded_df], ignore_index=True)
        df = df.sort_values(by=['periodId', 'timeMin', 'timeSec']).reset_index(drop=True)

        # =========================
        # CLEAN SHEET LOGIC BELOW
        # =========================

        # Get teams that actually conceded (from corrected logic)
        teams_conceded = goal_events['conceding_team'].unique()

        # Only allow clean sheets for players on teams that did NOT concede
        clean_sheet_eligible = starting_lineups[
            (starting_lineups['minutes_played'] > 60) &
            (starting_lineups['goals_conceded'] == 0) &
            (~starting_lineups['team_name'].isin(teams_conceded))
        ]

        clean_sheet_rows = []

        for _, player in clean_sheet_eligible.iterrows():
            pos = player['position']
            if pd.isna(pos):
                continue

            if any(p in pos for p in ['LB', 'CB', 'RB', 'RWB', 'LWB']):
                xt_val = 0.4
            elif 'M' in pos:
                xt_val = 0.1
            else:
                xt_val = None

            clean_sheet_rows.append({
                'playerName': player['player_name'],
                'team_name': player['team_name'],
                'typeId': 'clean_sheet',
                'playing_position': pos,
                'xT_value': xt_val
            })

        clean_sheet_df = pd.DataFrame(clean_sheet_rows)

        # Ensure all columns match df
        for col in df.columns:
            if col not in clean_sheet_df.columns:
                clean_sheet_df[col] = None

        # Append and sort
        df = pd.concat([df, clean_sheet_df], ignore_index=True)
        df = df.sort_values(by=['periodId', 'timeMin', 'timeSec'], na_position='last').reset_index(drop=True)


        clean_sheet_mask = df['typeId'] == 'clean_sheet'
        df = pd.concat([
            df[~clean_sheet_mask],
            df[clean_sheet_mask].drop_duplicates(subset=['playerName', 'playing_position'])
        ]).reset_index(drop=True)

        starting_lineups = starting_lineups[starting_lineups['minutes_played'].notna()]

        starting_lineups['xT_value'] = starting_lineups.apply(calculate_xt_value, axis=1)
        goalsconcededtotal = df[df['typeId'].isin(['goal_conceded', 'clean_sheet'])][['playerName', 'xT_value']].copy()
        goalsconcededtotal = goalsconcededtotal.groupby('playerName', as_index=False)['xT_value'].sum()
        ##TAKE ON
        takeondf = df[df['typeId'] == 'Take On'].copy()
        takeondf['x'] = pd.to_numeric(takeondf['x'], errors='coerce')
        def assign_xt(row):
            if row['x'] < 33.33:
                return -0.15 if row['outcome'] == 'Unsuccessful' else 0.05
            elif row['x'] < 66.66:
                return -0.1 if row['outcome'] == 'Unsuccessful' else 0.1
            else:
                return -0.05 if row['outcome'] == 'Unsuccessful' else 0.15
        takeondf['xT_value'] = takeondf.apply(assign_xt, axis=1)
        takeontotal = takeondf.groupby('playerName')['xT_value'].sum().reset_index()
        df = df.merge(
            takeondf[['id', 'xT_value']],
            on='id',
            how='left',
            suffixes=('', '_carry')
        )
        df['xT_value'] = df['xT_value'].combine_first(df['xT_value_carry'])
        df.drop(columns=['xT_value_carry'], inplace=True)
        #ERRORS
        errorsdf = df[(df['errorshot'] == 1) | (df['errorgoal'] == 1)].copy()
        def assign_error_xt(row):
            if row.get('errorgoal') == 1:
                return -0.5
            elif row.get('errorshot') == 1:
                return -0.1
            return 0  # fallback (shouldn't occur with current filter)
        errorsdf['xT_value'] = errorsdf.apply(assign_error_xt, axis=1)
        errorstotal = errorsdf.groupby('playerName')['xT_value'].sum().reset_index()
        df = df.merge(
            errorsdf[['id', 'xT_value']],
            on='id',
            how='left',
            suffixes=('', '_carry')
        )
        df['xT_value'] = df['xT_value'].combine_first(df['xT_value_carry'])
        df.drop(columns=['xT_value_carry'], inplace=True)
        #DISPOSSESSED
        dispossdf = df[df['typeId'] == 'Dispossessed'].copy()
        def assign_disposs_xt(x):
            if x < 33.3:
                return -0.15
            elif 33.3 <= x < 66.6:
                return -0.01
            else:  # x >= 66.6
                return -0.05
        dispossdf['xT_value'] = dispossdf['x'].apply(assign_disposs_xt)
        disposstotal = dispossdf.groupby('playerName')['xT_value'].sum().reset_index()
        df = df.merge(
            errorsdf[['id', 'xT_value']],
            on='id',
            how='left',
            suffixes=('', '_carry')
        )
        df['xT_value'] = df['xT_value'].combine_first(df['xT_value_carry'])
        df.drop(columns=['xT_value_carry'], inplace=True)
        dataframes = [
            shotstakentotal,
            defthreattotal,
            incomppasstotal,
            passthreattotal,
            carrythreattotal,
            cards_df,
            shotassisttotal,
            receivedpassestotal,
            goalsconcededtotal,
            takeontotal,
            errorstotal,
            disposstotal
        #    keepertotals
        ]
        valid_dataframes = [df for df in dataframes if isinstance(df, pd.DataFrame) and not df.empty]


        totalxt = pd.concat(dataframes)
        totalxt = totalxt.groupby('playerName', as_index=False).sum()
        totalxt = totalxt.sort_values(by='xT_value', ascending=False)
        goalkeepers = starting_lineups[starting_lineups['position'] == 'GK']['player_name'].unique()
        totalxt = totalxt[~totalxt['playerName'].isin(goalkeepers)].reset_index(drop=True)
        trimmed_xt = totalxt.iloc[1:-1]
        mean_xt = trimmed_xt['xT_value'].mean()
        totalxt['Player Impact'] = totalxt['xT_value'] - mean_xt
        totalxt['Player Impact'] = totalxt['Player Impact'].round(2)
        totalxt['Player Impact'] = totalxt['Player Impact'].apply(
            lambda x: f"+{x:.2f}" if x > 0 else f"-{abs(x):.2f}"
        )
        totalxt['Match Rank'] = totalxt['xT_value'].rank(method='max', ascending=False)
        totalxt['Match Rank'] = totalxt['Match Rank'].astype(int)
        totalxt.rename(columns={'xT_value': 'Threat Value'}, inplace=True)
        starting_lineups = starting_lineups.merge(
            totalxt,
            how='left',
            left_on='player_name',
            right_on='playerName'
        )
        starting_lineups = starting_lineups.drop_duplicates(subset=['player_id', 'match_id'], keep='first')
        for col in df.columns:
            if col not in position_change_df.columns:
                position_change_df[col] = None
        df = pd.concat([df, position_change_df], ignore_index=True)
                # Calculate distance to goal for all rows
        df['start_distance'] = ((df['x'] - 100) ** 2 + (df['y'] - 50) ** 2) ** 0.5
        df['end_distance'] = ((df['end_x'] - 100) ** 2 + (df['end_y'] - 50) ** 2) ** 0.5

                # -------- Progressive Carry Logic --------
                # Progressive if Carry and at least 20% closer to goal
        df['progressive_carry'] = 'No'
        carry_mask = (df['typeId'] == 'Carry') & (df['end_distance'] < 0.8 * df['start_distance'])
        df.loc[carry_mask, 'progressive_carry'] = 'Yes'

                # -------- Progressive Pass Logic --------
                # Define pass zones and thresholds
        pass_conditions = [
            (df['x'] <= 50) & (df['end_x'] <= 50),      # Defensive third
            (df['x'] <= 50) & (df['end_x'] >= 50),      # From defensive to middle
            (df['x'] > 50) & (df['x'] <= 75),           # Middle third
            (df['x'] > 75)                                        # Final third
            ]
        pass_percentages = [0.65, 0.80, 0.85, 1.00]

                # Initialize column
        df['progressive_pass'] = 'No'

                # Apply conditions only to Successful Passes
        is_pass = (df['typeId'] == 'Pass') & (df['outcome'] == 'Successful')
        for cond, threshold in zip(pass_conditions, pass_percentages):
            pass_mask = is_pass & cond & (df['end_distance'] < threshold * df['start_distance'])
            df.loc[pass_mask, 'progressive_pass'] = 'Yes'
        df['xT_value'] = df.apply(lambda row: 0.6 if row['assist'] == 1 else row['xT_value'] + 0.1 if row['keyPass'] == 1 else row['xT_value'], axis=1)


        starting_lineups = starting_lineups.drop_duplicates(subset=['player_id', 'match_id'], keep='first')

        league = selected_competition
        league_colors = {
            "FA Cup": {
                "TextColor": "white",
                "BackgroundColor": "red",
                "PitchColor": "#e5e1e0",
                "PitchLineColor": "black",
                "SonarPass": "#e5e1e0",
                "SonarCarry": "darkblue",
                "HullColor": "red"
            },
            "INT-FIFACWC": {
                "TextColor": "white",
                "BackgroundColor": "black",
                "PitchColor": "#e5e6b1",
                "PitchLineColor": "white",
                "SonarPass": "red",
                "SonarCarry": "yellow",
                "HullColor": "black"
            },
            "Carabao Cup": {
                "TextColor": "black",
                "BackgroundColor": "#fc957e",
                "PitchColor": "#c4f0e1",
                "PitchLineColor": "black",
                "SonarPass": "#c4f0e1",
                "SonarCarry": "#178fce",
                "HullColor": "red"
            },
            "Premier League": {
                "TextColor": "white",
                "BackgroundColor": "#381d54",
                "PitchColor": "#f5f6fc",
                "PitchLineColor": "black",
                "SonarPass": "#f5f6fc",
                "SonarCarry": "yellow",
                "HullColor": "#381d54"
            },
            "World Cup Qualifiers (UEFA)": {
                "TextColor": "white",
                "BackgroundColor": "#973d52",
                "PitchColor": "#e2e2e3",
                "PitchLineColor": "black",
                "SonarPass": "#e2e2e3",
                "SonarCarry": "#f3da15",
                "HullColor": "#973d52"
            },
            "League One": {
                "TextColor": "black",
                "BackgroundColor": "#ede6cf",
                "PitchColor": "#d4d6e3",
                "PitchLineColor": "black",
                "SonarPass": "#d4d6e3",
                "SonarCarry": "red",
                "HullColor": "darkblue"
            },
            "Championship": {
                "TextColor": "black",
                "BackgroundColor": "#ede6cf",
                "PitchColor": "#d4d6e3",
                "PitchLineColor": "black",
                "SonarPass": "#d4d6e3",
                "SonarCarry": "red",
                "HullColor": "darkblue"
            },
            "Serie A": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "Serie B": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "League Two": {
                "TextColor": "black",
                "BackgroundColor": "#ede6cf",
                "PitchColor": "#d4d6e3",
                "PitchLineColor": "black",
                "SonarPass": "#d4d6e3",
                "SonarCarry": "red",
                "HullColor": "darkblue"
            },
            "EFL Trophy": {
                "TextColor": "black",
                "BackgroundColor": "#ede6cf",
                "PitchColor": "#d4d6e3",
                "PitchLineColor": "black",
                "SonarPass": "#d4d6e3",
                "SonarCarry": "red",
                "HullColor": "darkblue"
            },
            "Scottish Premiership": {
                "TextColor": "white",
                "BackgroundColor": "#212b5a",
                "PitchColor": "#f1e5bd",
                "PitchLineColor": "black",
                "SonarPass": "#f1e5bd",
                "SonarCarry": "pink",
                "HullColor": "#212b5a"
            },
            "MLS": {
                "TextColor": "white",
                "BackgroundColor": "#d92419",
                "PitchColor": "#68a7c8",
                "PitchLineColor": "black",
                "SonarPass": "#68a7c8",
                "SonarCarry": "white",
                "HullColor": "#d92419"
            },
            "Champions League": {
                "TextColor": "white",
                "BackgroundColor": "#00106f",
                "PitchColor": "#62c6dd",
                "PitchLineColor": "black",
                "SonarPass": "#62c6dd",
                "SonarCarry": "yellow",
                "HullColor": "#00106f"
            },
            "UEFA Super Cup": {
                "TextColor": "white",
                "BackgroundColor": "#00106f",
                "PitchColor": "#62c6dd",
                "PitchLineColor": "black",
                "SonarPass": "#62c6dd",
                "SonarCarry": "yellow",
                "HullColor": "#00106f"
            },
            "Champions League Qualifiers": {
                "TextColor": "white",
                "BackgroundColor": "#00106f",
                "PitchColor": "#62c6dd",
                "PitchLineColor": "black",
                "SonarPass": "#62c6dd",
                "SonarCarry": "yellow",
                "HullColor": "#00106f"
            },
            "Europa Conference League": {
                "TextColor": "black",
                "BackgroundColor": "#da9240",
                "PitchColor": "#b9b9bb",
                "PitchLineColor": "black",
                "SonarPass": "#b9b9bb",
                "SonarCarry": "blue",
                "HullColor": "#da9240"
            },
            "Europa Conference League Qualifiers": {
                "TextColor": "black",
                "BackgroundColor": "#da9240",
                "PitchColor": "#b9b9bb",
                "PitchLineColor": "black",
                "SonarPass": "#b9b9bb",
                "SonarCarry": "blue",
                "HullColor": "#da9240"
            },
            "Europa League": {
                "TextColor": "black",
                "BackgroundColor": "#da9240",
                "PitchColor": "#b9b9bb",
                "PitchLineColor": "black",
                "SonarPass": "#b9b9bb",
                "SonarCarry": "blue",
                "HullColor": "#da9240"
            },
            "Europa League Qualifiers": {
                "TextColor": "black",
                "BackgroundColor": "#da9240",
                "PitchColor": "#b9b9bb",
                "PitchLineColor": "black",
                "SonarPass": "#b9b9bb",
                "SonarCarry": "blue",
                "HullColor": "#da9240"
            },
            "WSL": {
                "TextColor": "white",
                "BackgroundColor": "#ad2eaf",
                "PitchColor": "#f1c6d2",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "#ad2eaf"
            },
            "WSL2": {
                "TextColor": "white",
                "BackgroundColor": "#ad2eaf",
                "PitchColor": "#f1c6d2",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "#ad2eaf"
            },
            "La Liga": {
                "TextColor": "#ff4b44",
                "BackgroundColor": "white",
                "PitchColor": "white",
                "PitchLineColor": "#ff4b44",
                "SonarPass": "#ff4b44",
                "SonarCarry": "#178fce",
                "HullColor": "blue"
            },
            "Bundesliga": {
                "TextColor": "white",
                "BackgroundColor": "#d10214",
                "PitchColor": "white",
                "PitchLineColor": "black",
                "SonarPass": "white",
                "SonarCarry": "yellow",
                "HullColor": "#d10214"
            },
            "2. Bundesliga": {
                "TextColor": "white",
                "BackgroundColor": "#d10214",
                "PitchColor": "white",
                "PitchLineColor": "black",
                "SonarPass": "white",
                "SonarCarry": "yellow",
                "HullColor": "#d10214"
            },
            "Ligue 1": {
                "TextColor": "white",
                "BackgroundColor": "#091c3d",
                "PitchColor": "#E7F5AC",
                "PitchLineColor": "black",
                "SonarPass": "#E7F5AC",
                "SonarCarry": "red",
                "HullColor": "#091c3d"
            },             
            "Brasilerao": {
                "TextColor": "white",
                "BackgroundColor": "black",
                "PitchColor": "#dcfc30",
                "PitchLineColor": "white",
                "SonarPass": "red",
                "SonarCarry": "blue",
                "HullColor": "black"

            },
            "Pro League": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "Liga Portugal": {
                "TextColor": "white",
                "BackgroundColor": "#001e50",
                "PitchColor": "#f5f6fc",
                "PitchLineColor": "black",
                "SonarPass": "#f5f6fc",
                "SonarCarry": "yellow",
                "HullColor": "#001e50"
            },
            "TUR-SuperLig": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "Friendly": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "International Friendly": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "Superligaen": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "Austrian Bundesliga": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "A-League": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#c2c5f3",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "yellow"
            },
            "A-League Women": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#c2c5f3",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "yellow"
            },
            "Swiss Super League": {
                "TextColor": "black",
                "BackgroundColor": "#f5f2f3",
                "PitchColor": "#ffe3e9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "#87cbfc",
                "HullColor": "darkblue"
            },
            "INT-NationsLeagueA": {
                "TextColor": "black",
                "BackgroundColor": "#ebf3fc",
                "PitchColor": "#c9def9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "yellow",
                "HullColor": "#ebf3fc"
            },
            "INT-NationsLeagueB": {
                "TextColor": "black",
                "BackgroundColor": "#ebf3fc",
                "PitchColor": "#c9def9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "yellow",
                "HullColor": "#ebf3fc"
            },
            "INT-NationsLeagueC": {
                "TextColor": "black",
                "BackgroundColor": "#ebf3fc",
                "PitchColor": "#c9def9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "yellow",
                "HullColor": "#ebf3fc"
            },
            "INT-FIFAWCQ": {
                "TextColor": "white",
                "BackgroundColor": "#a8161c",
                "PitchColor": "#cecccd",
                "PitchLineColor": "black",
                "SonarPass": "#cecccd",
                "SonarCarry": "#f8ca0f",
                "HullColor": "#a8161c"
            },
            "INT-NationsLeagueD": {
                "TextColor": "black",
                "BackgroundColor": "#ebf3fc",
                "PitchColor": "#c9def9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "yellow",
                "HullColor": "#ebf3fc"
            },
            "AFCON": {
                "TextColor": "white",
                "BackgroundColor": "#800000",
                "PitchColor": "#e9fdf0",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "yellow",
                "HullColor": "#800000"
            },
            "INT-NationsLeagueAQ": {
                "TextColor": "black",
                "BackgroundColor": "#ebf3fc",
                "PitchColor": "#c9def9",
                "PitchLineColor": "black",
                "SonarPass": "red",
                "SonarCarry": "yellow",
                "HullColor": "#ebf3fc"
            }

        }

        # Define the league you are working with
        # Retrieve the color properties for the specified league
        league_colors_properties = league_colors.get(league, {
            "TextColor": "default",
            "BackgroundColor": "default",
            "PitchColor": "default",
            "PitchLineColor": "default",
            "SonarPass": "default",
            "SonarCarry": "default",
            "HullColor": "default"
        })
        
        # Define theme with safe fallbacks (treat "" as missing too)
        def _val(key, default):
            v = league_colors_properties.get(key)
            if not v:  # None or ""
                v = st.session_state.get(key, default)
            return v or default
        
        TextColor       = _val("TextColor", "black")
        BackgroundColor = _val("BackgroundColor", "white")
        PitchColor      = _val("PitchColor", "white")
        PitchLineColor  = _val("PitchLineColor", "black")
        
        # (Optional) pick a default font now or don’t store it yet
        from matplotlib.font_manager import FontProperties
        title_font = FontProperties(family="Tahoma", size=15)
        
        st.session_state.update({
            "TextColor": TextColor,
            "BackgroundColor": BackgroundColor,
            "PitchColor": PitchColor,
            "PitchLineColor": PitchLineColor,
            "title_font": title_font,
        })

        
        tab1, tab2, tab3, tab4 = st.tabs(["Player Overview", "Match Momentum", "Average Positions", "Custom Player Actions"])

        
        # --- Build a safe players_list for selectors (Overview + others) ---
        def _safe_series(frame, col):
            try:
                if frame is not None and col in frame.columns:
                    return frame[col].dropna().astype(str)
            except Exception:
                pass
            return pd.Series(dtype=str)
        
        players_list = (
            pd.concat(
                [
                    _safe_series(df, "playerName"),
                    _safe_series(starting_lineups, "player_name"),
                ],
                ignore_index=True,
            )
            .dropna()
            .drop_duplicates()
            .sort_values()
            .tolist()
        )

        # Output the result
        print(f"Color properties for {league}: {league_colors_properties}")
        player_list = starting_lineups["player_name"].dropna().unique().tolist()

        player_options = ["-- Select a player --"] + sorted(player_list)
        
        # Player dropdown
        with tab1:
            import matplotlib.pyplot as plt
            plt.close('all')  # reset any prior figs tied to other tabs
        
            # Build player list safely (use whatever you already have if defined)
            try:
                player_options = ["-- Select a player --"] + sorted(
                    pd.Series(
                        list(
                            set(
                                (df["playerName"].dropna().astype(str).tolist() if "playerName" in df.columns else [])
                                + (starting_lineups["player_name"].dropna().astype(str).tolist() if "player_name" in starting_lineups.columns else [])
                            )
                        )
                    ).drop_duplicates().tolist()
                )
            except Exception:
                player_options = ["-- Select a player --"]
        
            # ▼ Keep the selector INSIDE Tab 1 and give it a unique key
            playername = st.selectbox("Select Player Name", options=player_options, key="tab1_player_select")
        
            if playername != "-- Select a player --":
                anderson = starting_lineups[starting_lineups["player_name"] == playername] if "player_name" in starting_lineups.columns else pd.DataFrame()
                if not anderson.empty:
                    teamname = anderson.iloc[0]['team_name'] if 'team_name' in anderson.columns else "N/A"
                    st.info(f"{playername} plays for {teamname}")
        
                    TextColor = league_colors_properties["TextColor"]
                    BackgroundColor = league_colors_properties["BackgroundColor"]
                    PitchColor = league_colors_properties["PitchColor"]
                    PitchLineColor = league_colors_properties["PitchLineColor"]
                    SonarPass = league_colors_properties["SonarPass"]
                    SonarCarry = league_colors_properties["SonarCarry"]
                    HullColor = league_colors_properties["HullColor"]
                    print(f"TextColor: {TextColor}, BackgroundColor: {BackgroundColor}")
                    player_impact = totalxt.loc[totalxt['playerName'] == playername, 'Player Impact']
                    match_rank = totalxt.loc[totalxt['playerName'] == playername, 'Match Rank']
            
                    # Display the result
                    player_impact_value = player_impact.iloc[0] if not player_impact.empty else None
                    match_rank_value = match_rank.iloc[0] if not match_rank.empty else None
                    anderson = df.loc[df['playerName']== playername]
                    anderson = anderson.loc[anderson['typeId']!='Out']
                    anderson = anderson.loc[anderson['typeId']!='Player off']
                    anderson = anderson.loc[anderson['typeId']!='Player on']
                    anderson = anderson[~((anderson['x'] == 0) & (anderson['y'] == 0))]
                    prf3comp = anderson.loc[(anderson['outcome']=='Successful') & (anderson['typeId']=='Pass')]
                    prf3incomp = anderson.loc[(anderson['outcome']=='Unsuccessful') & (anderson['typeId']=='Pass') ]
                    shotassist = anderson.loc[anderson['keyPass']==1]
                    shotassist = shotassist.loc[shotassist['typeId']=='Pass']
                    goalassist = anderson.loc[anderson['assist']==1]
                    goalassist = goalassist.loc[goalassist['typeId']=='Pass']
            
                    takeon = anderson.loc[(anderson['typeId']=='Take On')]
                    takeont = takeon.loc[takeon['outcome'] == 'Successful']
                    takeonf = takeon.loc[takeon['outcome'] != 'Successful']
                    tackle = anderson.loc[(anderson['typeId']=='Tackle')]
                    tacklet = tackle.loc[tackle['outcome'] == 'Successful']
                    tacklef = tackle.loc[tackle['outcome'] != 'Successful']
                    aerial = anderson.loc[(anderson['typeId']=='Aerial')]
                    aerialt = aerial.loc[aerial['outcome'] == 'Successful']
                    aerialf = aerial.loc[aerial['outcome'] != 'Successful']
                    fouls = anderson.loc[anderson['typeId'] == 'Foul']
                    fouls = fouls.loc[fouls['outcome'] == 'Unsuccessful']
            
            
                    ballrec = anderson.loc[(anderson['typeId']=='Ball recovery')]
                    clearance = anderson.loc[(anderson['typeId']=='Clearance')]
                    interception = anderson.loc[(anderson['typeId']=='Interception') ]
                    shotblocked = anderson.loc[(anderson['typeId']=='Save')]
            
                    disposs = anderson.loc[(anderson['typeId']=='Dispossessed')]
                    playercarry = anderson.loc[anderson['typeId']=='Carry']
            
                    #shotblock = anderson.loc[(anderson['shot']==True) & (anderson['82']==True) & (anderson['player_name'] == playerrequest)]
                    shotoff = anderson.loc[(anderson['typeId'] == 'Miss')]
                    shoton = anderson.loc[(anderson['typeId'] == 'Attempt Saved')]
                    shotgoal = anderson.loc[(anderson['typeId'] == 'Goal')]
                    playertouchmap = anderson.loc[anderson['typeId']!='Player on']
                    playertouchmap = playertouchmap.loc[playertouchmap['typeId']!='Player off']
                    ## IMPORT RELEVANT LIBRARIES
            
                    import pandas as pd
                    import numpy as np
                    import mplsoccer as mpl
                    from mplsoccer import Pitch, add_image
                    import matplotlib.pyplot as plt
                    from matplotlib.patches import Arc
                    from urllib.request import urlopen
                    from PIL import Image
                    import matplotlib.patheffects as path_effects
                    from matplotlib.colors import LinearSegmentedColormap
                    from scipy.ndimage import gaussian_filter
                    from mplsoccer import Pitch, VerticalPitch, FontManager, Sbopen
                    from datetime import datetime
                    import matplotlib.font_manager as font_manager
                    from matplotlib.font_manager import FontProperties
                    playerrequest = playername
                    #teamname = 'England U21'
                    #opponentname = 'Azerbaijan U21'
                    title_font = FontProperties(family='Tahoma', size=15)
                    #playercarry = playercarry.loc[playercarry['team_name']=='Bradford']
                    playercarry = playercarry.loc[playercarry['end_y']> 0]
                    playercarry = playercarry.loc[playercarry['end_x']> 0]
                    playercarry = playercarry.loc[playercarry['x']> 2.5]
            
                    playercarry = playercarry.loc[playercarry['end_y']< 100]
                    playercarry = playercarry.loc[playercarry['end_x']< 100]
                    playercarry = playercarry.loc[playercarry['end_x'] < 99.5]
            
                    playercarry['y_diff'] = playercarry['y'] - playercarry['end_y']
                    playercarry['x_diff'] = playercarry['x'] - playercarry['end_x']

                    playercarry = playercarry.loc[playercarry['y_diff']>-25]
                    playercarry = playercarry.loc[playercarry['y_diff']<25]
                    playercarry = playercarry.loc[playercarry['x_diff']<25]
                    playercarry = playercarry.loc[playercarry['x_diff']>-25]

                    playercarry = playercarry[~(((playercarry['x'] == 0) & (playercarry['end_x'] == 0)) | ((playercarry['y'] == 0) & (playercarry['end_y'] == 0)))]
            
                    #teamname = anderson.iloc[0]['team_name']
                    teamlogoid = teamdata.loc[teamdata['name'] == teamname, 'id'].values[0]
                    opponentname2 = teamdata.loc[teamdata['name'] != teamname, 'name'].values[0]
                    if teamlogoid == "cpxv65ua10liq2k8ovsezf7ox":
                        teamlogoid = "1qtaiy11gswx327s0vkibf70n"  
                    if teamlogoid == "7ft9s47h5gbc35sbndoswkdwl":
                        teamlogoid = "1qtaiy11gswx327s0vkibf70n"  
                    URL = f"https://omo.akamai.opta.net/image.php?h=www.scoresway.com&sport=football&entity=team&description=badges&dimensions=150&id={teamlogoid}"
                    # EFFIONG https://cdn5.wyscout.com/photos/players/public/g144828_100x130.png
                    teamimage = Image.open(urlopen(URL))
                    from PIL import Image
            
                    wtaimaged = Image.open("wtatransnew.png")
                    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
                    import matplotlib.pyplot as plt
                    import numpy as np
                    from scipy.stats import gaussian_kde
                    from scipy.spatial import ConvexHull
            
                    # Create a figure with three subplots side by side
                    fig, axes = plt.subplots(1, 3, figsize=(24, 8.25), facecolor=BackgroundColor)  # Adjust the figsize as needed
                    plt.subplots_adjust(wspace=-0.5)
            
                    # Define the pitch dimensions and other options
                    pitch_arrows = VerticalPitch(pitch_type='opta', pitch_color=PitchColor, line_color=PitchLineColor)
                    pitch_bins = VerticalPitch(pitch_type='opta', pitch_color=PitchColor, line_color=PitchLineColor)
                    pitch_third = VerticalPitch(pitch_type='opta', pitch_color=PitchColor, line_color=PitchLineColor)  # New pitch instance
            
                    # Draw the first pitch with comet-like lines
                    pitch_arrows.draw(ax=axes[0], figsize=(8, 8.25), constrained_layout=True, tight_layout=False)  # Adjust figsize if needed
                    axes[0].set_title(f'{playerrequest} - Passes & Carries', fontproperties=title_font, color=TextColor)
            
                    # Plot comet-like lines on the first pitch subplot (axes[0])
                    def plot_comet_line(ax, x_start, y_start, x_end, y_end, color='green', num_segments=20):
                        dx = (x_end - x_start) / num_segments
                        dy = (y_end - y_start) / num_segments
                        alphas = np.linspace(1, 0, num_segments)
                        for i in range(num_segments):
                            ax.plot([x_start + i*dx, x_start + (i+1)*dx], 
                                    [y_start + i*dy, y_start + (i+1)*dy], 
                                    color=color, alpha=alphas[i])
            
                    # Plot comet-like lines
                    plot_comet_line(axes[0], prf3comp.end_y, prf3comp.end_x,
                                    prf3comp.y, prf3comp.x, color='green', num_segments=20)
            
                    plot_comet_line(axes[0], prf3incomp.end_y, prf3incomp.end_x,
                                    prf3incomp.y, prf3incomp.x, color='red', num_segments=20)
            
                    plot_comet_line(axes[0], shotassist.end_y, shotassist.end_x,
                                    shotassist.y, shotassist.x, color='orange', num_segments=20)
            
                    plot_comet_line(axes[0], playercarry.end_y, playercarry.end_x,
                                    playercarry.y, playercarry.x, color='purple', num_segments=20)
            
                    def plot_comet_line2(ax, x_start, y_start, x_end, y_end, color='blue', num_segments=10, linewidth=1.0):
                        dx = (x_end - x_start) / num_segments
                        dy = (y_end - y_start) / num_segments
                        alphas = np.linspace(1, 0, num_segments)
                        for i in range(num_segments):
                            ax.plot([x_start + i*dx, x_start + (i+1)*dx], 
                                    [y_start + i*dy, y_start + (i+1)*dy], 
                                    color=color, alpha=alphas[i], linewidth=2)
            
                    plot_comet_line2(axes[0], goalassist.end_y, goalassist.end_x,
                                    goalassist.y, goalassist.x, color='blue', num_segments=10)
            
                    # Draw the second pitch on the second subplot
                    pitch_bins.draw(ax=axes[1], figsize=(8, 8.25), constrained_layout=True, tight_layout=False)  # Adjust figsize if needed
                    axes[1].set_title(f'{playerrequest} - Touch Map', fontproperties=title_font, color=TextColor)
            
            
                    # Plotting small round dots for each row in the DataFrame on the second pitch subplot (axes[1])
                    for index, row in playertouchmap.iterrows():
                        x = row['y']  # Assuming 'y' is the column name for x-coordinate
                        y = row['x']  # Assuming 'x' is the column name for y-coordinate
                        axes[1].plot(x, y, marker='o', markeredgecolor=HullColor, markerfacecolor='none', markersize=5)  # Adjust marker size, color, and transparency as needed
            
                    x_coords = playertouchmap['y']  # Assuming 'y' is the column name for x-coordinate
                    y_coords = playertouchmap['x']  # Assuming 'x' is the column name for y-coordinate
            
                    # Combining x and y coordinates into a single array
                    points = np.column_stack((x_coords, y_coords))
            
                    # Perform kernel density estimation
                    #kde = gaussian_kde(points.T)
            
                    # Evaluate the KDE on a grid
                    #x_grid, y_grid = np.meshgrid(np.linspace(0, 120, 100), np.linspace(0, 80, 100))
                    #density = kde(np.vstack([x_grid.ravel(), y_grid.ravel()]))
            
                    # Find the point with the highest density
                    #max_density_index = np.argmax(density)
                    #max_density_x = x_grid.ravel()[max_density_index]
                    #max_density_y = y_grid.ravel()[max_density_index]
            
                    # Define a radius around the point with the highest density
                    radius = 20  # Adjust as needed
            
                    # Filter points within the radius
                    #points_within_radius = points[((points[:, 0] - max_density_x) ** 2 + (points[:, 1] - max_density_y) ** 2) < radius ** 2]
            
                    # Compute convex hull around points within the radius
                    #hull = ConvexHull(points_within_radius)
            
                    # Plotting the convex hull on the second pitch subplot (axes[1])
                    #x_hull = points_within_radius[hull.vertices, 0]
                    #y_hull = points_within_radius[hull.vertices, 1]
            
                    #axes[1].fill(x_hull, y_hull, color=BackgroundColor, alpha=0.25, edgecolor=BackgroundColor)
            
                    # Draw the third pitch on the third subplot
                    pitch_third.draw(ax=axes[2], figsize=(8, 8.25), constrained_layout=True, tight_layout=False)  # Adjust figsize if needed
                    axes[2].set_title(f'{playerrequest} - Event Map', fontproperties=title_font, color=TextColor)  # Add a suitable title
            
                    scatter1 = pitch_third.scatter(tacklet.x, tacklet.y, ax=axes[2], facecolor='green', edgecolor='green', marker='>', label='Tackle', s=40)
                    scatter2 = pitch_third.scatter(tacklef.x, tacklef.y, ax=axes[2], facecolor='red', edgecolor='red',marker='>', s=40)
                    #scatter15 = pitch_third.scatter(foulsl.x, foulsl.y, ax=axes[2], facecolor='red', edgecolor='red',marker='>', s=40)
                    scatter3 = pitch_third.scatter(aerialt.x, aerialt.y, ax=axes[2], facecolor='green',edgecolor='green', marker='s', label='Aerial', s=40)
                    scatter4 = pitch_third.scatter(aerialf.x, aerialf.y, ax=axes[2], facecolor='red',edgecolor='red', marker='s', s=40)
                    scatter5 = pitch_third.scatter(shotblocked.x, shotblocked.y, ax=axes[2], facecolor='green',edgecolor='green', marker='p', label='Attempts Blocked', s=40)
                    scatter6 = pitch_third.scatter(ballrec.x, ballrec.y, ax=axes[2], facecolor='green',edgecolor='green', marker='d', label='Ball Recoveries', s=40)
                    scatter7 = pitch_third.scatter(clearance.x, clearance.y, ax=axes[2], facecolor='green',edgecolor='green', marker='^', label='Clearance', s=40)
                    scatter8 = pitch_third.scatter(takeont.x, takeont.y, ax=axes[2], facecolor='green',edgecolor='green', marker='P', label='Take On', s=40)
                    scatter9 = pitch_third.scatter(takeonf.x, takeonf.y, ax=axes[2], facecolor='red',edgecolor='red', marker='P', s=40)
                    scatter10 = pitch_third.scatter(disposs.x, disposs.y, ax=axes[2], facecolor='red',edgecolor='red', marker='x', s=40, label = 'Dispossesed')
                    #scatter11 = pitch_third.scatter(shotblock.x, shotblock.y, ax=axes[2], facecolor='yellow',edgecolor='yellow', marker='o', s=40, label = 'Shot Blocked')
                    scatter12 = pitch_third.scatter(shotoff.x, shotoff.y, ax=axes[2], facecolor='red', marker='o',edgecolor='red', label='Shot Off Target', s=40)
                    scatter13 = pitch_third.scatter(shoton.x, shoton.y, ax=axes[2], facecolor='green', marker='o',edgecolor='green', label='Shot On Target', s=40)
                    scatter14 = pitch_third.scatter(shotgoal.x, shotgoal.y, ax=axes[2], facecolor='green', marker='*',edgecolor='green', label='Goal', s=100)
                    scatter15 = pitch_third.scatter(fouls.x, fouls.y, ax=axes[2], facecolor='red', marker='>',edgecolor='red',s=40)
            
                    # Add legend
                    legend = axes[2].legend(handles=[scatter1, scatter3, scatter5, scatter6,
                                                     scatter7, scatter8, #scatter11, 
                                                     scatter10,
                                                     scatter13, scatter14
                                                    ], 
                                                     loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=2, facecolor='silver', frameon=False,labelcolor =TextColor)
                    # Legend for the first subplot (axes[0])
                    # Add text under the first pitch subplot (axes[0])
            
                    #axes[0].text(91.65, -5, 'Completed Pass', ha='center', fontsize=9, color='green')
                    #axes[0].text(62, -5, 'Incompleted Pass', ha='center', fontsize=9, color='red')
                    #axes[0].text(37, -5, 'Shot Assist', ha='center', fontsize=9, color='orange')
                    #axes[0].text(21, -5, 'Assist', ha='center', fontsize=9, color='blue')
                    #axes[0].text(5, -5, 'Ball Carry', ha='center', fontsize=9, color='#f4ffb5')
                    from matplotlib.lines import Line2D
            
                    legend_labels = ['Completed Pass', 'Incompleted Pass', 'Shot Assist', 'Assist', 'Ball Carry']
                    legend_colors = ['green', 'red', 'orange', 'blue', 'purple']
                    
                    # Create Line2D handles for legend
                    legend_lines = [Line2D([0], [0], color=color, linewidth=3) for color in legend_colors]
                    
                    # Add legend under pitch 1
                    axes[0].legend(legend_lines, legend_labels,
                                   loc='upper center',
                                   bbox_to_anchor=(0.22, -0.02),  # Adjust vertical position as needed
                                   ncol=1,
                                   facecolor=BackgroundColor,
                                   frameon=False,
                                   labelcolor=TextColor)
            
                    axes[0].text(50, -5, 'Data from Opta', ha='center', fontsize=9, color=TextColor)
                    axes[0].text(25, -9, 'Opponent:', ha='center', fontsize=14, color=TextColor)
                    axes[0].text(25, -13, f'{opponentname2}', ha='center', fontsize=14, color=TextColor, fontweight='bold')
            
                    axes[0].text(25, -19, 'Player Impact Score:', ha='center', fontsize=14, color=TextColor)
                    axes[0].text(25, -23, f'{player_impact_value} (#{match_rank_value})', ha='center', fontsize=14, color=TextColor, fontweight='bold')
            
            
            
                    axes[1].text(50, -5, 'All events plotted', ha='center', fontsize=9, color=TextColor)
            
                    axes[2].text(50, -5, 'Green shows successful action, red shows unsuccessful', ha='center', fontsize=9, color=TextColor)
            
                    #ax_image = add_image(playerimage, fig, left=0.4225, bottom=-0.04, width=0.04,
                    #                    alpha=1, interpolation='hanning')
            
                    #ax_image = add_image(playerimage, fig, left=0.45, bottom=-0.045, width=0.03,
                    #                     alpha=1, interpolation='hanning')
                    ax_image = add_image(teamimage, fig, left=0.5375, bottom=-0.049, width=0.055,
                                         alpha=1, interpolation='hanning')
            
                    ax_image = add_image(wtaimaged, fig, left=0.4375, bottom=-0.029, width=0.055,
                                         alpha=1, interpolation='hanning')
                    #ax_image = add_image(leagueimage, fig, left=0.565, bottom=-0.03175, width=0.03,
                    #                     alpha=1, interpolation='hanning')
                    dpi = 600
                    st.pyplot(fig)
                    st.success("Analysis Complete!")
                    plt.close(fig)
                    

        
        with tab2:
            st.header("Match Momentum Visual")
        
            import numpy as np
            import matplotlib.pyplot as plt
            from matplotlib.offsetbox import OffsetImage, AnnotationBbox
            from scipy.interpolate import make_interp_spline
            from urllib.request import urlopen
            from PIL import Image
        
            # ---------- data prep ----------
            pivot_df = df.pivot_table(index='timeMin', columns='team_name',
                                      values='xT_value', aggfunc='sum').reset_index()
            for column in pivot_df.columns:
                pivot_df[column].fillna(0, inplace=True)
            pivot_df['score_difference'] = pivot_df[teamname] - pivot_df[opponentname]
            pivot_df['rolling_avg_score_difference'] = (
                pivot_df['score_difference'].rolling(window=5, min_periods=1).mean()
            )
        
            goals = df[df['typeId'].isin(['Goal', 'Own Goal'])]
            goal_time = goals['timeMin']
        
            halftime = df[df['periodId'] == 1]['timeMin'].max()
            fulltime  = df[df['periodId'] == 2]['timeMin'].max()
        
            # ---------- images ----------
            hometeamlogo = teamdata.iloc[0, 0]
            awayteamlogo = teamdata.iloc[1, 0]
            if hometeamlogo == "cpxv65ua10liq2k8ovsezf7ox":
                hometeamlogo = "1qtaiy11gswx327s0vkibf70n"
            if hometeamlogo == "7ft9s47h5gbc35sbndoswkdwl":
                hometeamlogo = "1qtaiy11gswx327s0vkibf70n"  
            if awayteamlogo == "cpxv65ua10liq2k8ovsezf7ox":
                awayteamlogo = "1qtaiy11gswx327s0vkibf70n"  
            if awayteamlogo == "7ft9s47h5gbc35sbndoswkdwl":
                awayteamlogo = "1qtaiy11gswx327s0vkibf70n"  
            HOMEURL = f"https://omo.akamai.opta.net/image.php?h=www.scoresway.com&sport=football&entity=team&description=badges&dimensions=150&id={hometeamlogo}"
            AWAYURL = f"https://omo.akamai.opta.net/image.php?h=www.scoresway.com&sport=football&entity=team&description=badges&dimensions=150&id={awayteamlogo}"
        
            # Ensure RGBA so numpy arrays are (H, W, 4)
            homeimage = Image.open(urlopen(HOMEURL)).convert("RGBA")
            awayimage = Image.open(urlopen(AWAYURL)).convert("RGBA")
            footballimage = Image.open('football.png')
        
            # ---------- watermark helper ----------
            def prepare_watermark(pil_img, *, opacity=0.14, bg_threshold=0.985, min_keep_ratio=0.15):
                """
                Return RGBA ndarray with a single, scaled alpha channel.
                - If the image already has alpha: just scale the alpha.
                - If no alpha: try to remove near-white background; if that removes too much,
                  fall back to keeping all pixels and just apply opacity.
                """
                arr = np.array(pil_img).astype(np.float32) / 255.0
        
                if arr.ndim == 2:  # grayscale to RGB
                    arr = np.repeat(arr[..., None], 3, axis=-1)
        
                if arr.shape[-1] == 4:
                    # scale existing alpha
                    arr[..., 3] *= opacity
                    return arr
        
                # add alpha and try to drop near-white
                alpha = np.ones(arr.shape[:2], dtype=np.float32)
        
                rgb = arr[..., :3]
                bright = rgb.max(axis=-1)
                spread = rgb.ptp(axis=-1)  # max-min across channels
                near_white = (bright > bg_threshold) & (spread < 0.06)
        
                removed_ratio = near_white.mean()
                if 1.0 - removed_ratio < min_keep_ratio:
                    # too destructive; keep all pixels
                    alpha[:] = 1.0
                else:
                    alpha[near_white] = 0.0
        
                alpha *= opacity
                return np.dstack([rgb, alpha])
        
            # ---------- plot ----------
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.set_facecolor(BackgroundColor)
            ax.set_facecolor(PitchColor)
        
            x = pivot_df['timeMin']
            y = pivot_df['rolling_avg_score_difference']
            spl = make_interp_spline(x, y, k=3)
            x_smooth = np.linspace(x.min(), x.max(), 300)
            y_smooth = spl(x_smooth)
        
            ax.fill_between(
                x_smooth, y_smooth, where=(y_smooth >= 0), interpolate=True,
                color=homecolor1, alpha=0.45, edgecolor=homecolor2
            )
            ax.fill_between(
                x_smooth, y_smooth, where=(y_smooth < 0), interpolate=True,
                color=awaycolor1, alpha=0.45, edgecolor=awaycolor2
            )
        
            for goal_min in goal_time:
                closest_idx = (pivot_df['timeMin'] - goal_min).abs().idxmin()
                y_value = pivot_df.loc[closest_idx, 'rolling_avg_score_difference']
                img_y_pos = y_value + 0.115 if y_value >= 0 else y_value - 0.115
                imagebox_goal = OffsetImage(footballimage, zoom=0.035, alpha=0.75)
                ax.add_artist(AnnotationBbox(imagebox_goal, (goal_min, img_y_pos), frameon=False))
        
            if pd.notna(halftime):
                ax.axvline(x=halftime, color='green', linestyle='--', linewidth=1)
            if pd.notna(fulltime) and fulltime >= 90:
                ax.axvline(x=fulltime, color='green', linestyle='--', linewidth=1)
        
            ax.set_title(f'{teamname} v {opponentname} Match Momentum', color=TextColor)
            ax.set_xlabel('Minute')
            ax.set_ylabel('')
            ax.set_ylim(-1.5, 1.5)
            ax.set_yticks([])
            ax.axhline(y=0, color='black', linewidth=0.8)
            ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='gray')
            ax.tick_params(colors=TextColor)
            ax.xaxis.label.set_color(TextColor)
            ax.yaxis.label.set_color(TextColor)
            # ---------- logos (clean & add) ----------
            home_img_wm = prepare_watermark(homeimage, opacity=0.12)
            away_img_wm = prepare_watermark(awayimage, opacity=0.12)
        
            ax.add_artist(AnnotationBbox(OffsetImage(home_img_wm, zoom=0.5), (5, 1),
                                         frameon=False, zorder=0))
            ax.add_artist(AnnotationBbox(OffsetImage(away_img_wm, zoom=0.5),
                                         (pivot_df['timeMin'].max() - 5, -1),
                                         frameon=False, zorder=0))
        
            # WTA logo (keep as you had it)
            ax.add_artist(AnnotationBbox(OffsetImage(wtaimaged, zoom=0.1, alpha=0.25),
                                         (5, -1), frameon=False, zorder=0))
        
            st.pyplot(fig)
            plt.close(fig)

        with tab3:
            st.header("Average Positions")
        
            import numpy as np
            import pandas as pd
        
            # ---- find a usable minute column ----
            if "minute" in df.columns:
                minute_col = "minute"
            elif "timeMin" in df.columns:
                minute_col = "timeMin"
            else:
                st.info("No 'minute' or 'timeMin' column found.")
                st.stop()
        
            # ---- colours fallback ----
            try:
                _hc1, _hc2, _ac1, _ac2 = homecolor1, homecolor2, awaycolor1, awaycolor2
            except NameError:
                _hc1, _hc2, _ac1, _ac2 = "red", "white", "blue", "white"
        
            # ---- base guard ----
            if df.empty:
                st.info("Not enough event data to compute average positions for this match.")
                st.stop()
        
            # ---- coerce minutes to numeric & guard ----
            minutes = pd.to_numeric(df[minute_col], errors="coerce")
            if minutes.notna().sum() == 0:
                st.info("No valid minute data available for this match.")
                st.stop()
        
            # Work on a copy to keep things clean
            df = df.copy()
            df["_minutes"] = minutes
        
            # ---- compute slider bounds ----
            min_minute = int(np.nanmin(df["_minutes"]))
            max_minute = int(np.nanmax(df["_minutes"]))
            if min_minute == max_minute:
                max_minute = min_minute + 1
        
            # ---- compute half-time (max minute in period 1, if present) ----
            ht_minute, ht_label, ht_pos_pct = None, "(HT unknown)", None
            if "periodId" in df.columns:
                mask_p1 = (df["periodId"] == 1) & df["_minutes"].notna()
                if mask_p1.any():
                    ht_val = df.loc[mask_p1, "_minutes"].max()
                    if pd.notna(ht_val):
                        ht_minute = int(ht_val)
                        ht_label = f"(HT at {ht_minute}’)"
                        rng = (max_minute - min_minute)
                        ht_pos_pct = 0 if rng == 0 else 100 * (ht_minute - min_minute) / rng
        
            # ---- slider ----
            minute_range = st.slider(
                f"Select Minute Range {ht_label}",
                min_value=min_minute,
                max_value=max_minute,
                value=(min_minute, max_minute),
                step=1,
                key="avgpos_minute_range",
            )
        
            # ---- visual HT marker under the slider (simple ruler) ----
            if ht_minute is not None and ht_pos_pct is not None:
                st.markdown(
                    f"""
                    <div style="position:relative;height:10px;margin-top:-6px;margin-bottom:10px;
                                background:#e5e7eb;border-radius:6px;">
                      <div style="position:absolute;left:{ht_pos_pct:.2f}%;top:-6px;width:2px;height:22px;background:#ef4444;"></div>
                    </div>
                    <div style="font-size:12px;opacity:0.8;">HT at {ht_minute}’</div>
                    """,
                    unsafe_allow_html=True,
                )
        
            # ---- filter df by selected range (using numeric minutes) ----
            df_filtered = df[df["_minutes"].between(minute_range[0], minute_range[1], inclusive="both")].copy()
            if df_filtered.empty:
                st.info("Not enough data in the selected range to compute average positions.")
                st.stop()
        
            # ---- NEW: exclude sub on/off events from the calculation ----
            # Robust to casing and non-strings; if typeId missing, we just keep everything.
            if "typeId" in df_filtered.columns:
                _type = df_filtered["typeId"].astype(str).str.lower()
                df_calc = df_filtered[~_type.isin(["player on", "player off"])].copy()
            else:
                df_calc = df_filtered
        
            # ---- build lineups (starters only) ----
            homelineup = starting_lineups[
                (starting_lineups["team_name"] == teamname) &
                (starting_lineups["is_starter"] == "yes")
            ].copy()
        
            awaylineup = starting_lineups[
                (starting_lineups["team_name"] != teamname) &
                (starting_lineups["is_starter"] == "yes")
            ].copy()
        
            if homelineup.empty or awaylineup.empty:
                st.info("Starting lineups are missing; cannot compute average positions.")
                st.stop()
        
            # ---- ensure x/y are numeric before averaging ----
            df_calc["x"] = pd.to_numeric(df_calc.get("x"), errors="coerce")
            df_calc["y"] = pd.to_numeric(df_calc.get("y"), errors="coerce")
        
            # ---- averages (home) ----
            df_averages_home = (
                df_calc[df_calc["playerName"].isin(homelineup["player_name"])]
                .dropna(subset=["x", "y"])
                .groupby("playerName", as_index=False)
                .agg({"x": "mean", "y": "mean"})
                .rename(columns={"playerName": "player_name"})
            )
            homeresult = pd.merge(homelineup, df_averages_home, on="player_name", how="left").dropna(subset=["x", "y"])
        
            # ---- averages (away) ----
            df_averages_away = (
                df_calc[df_calc["playerName"].isin(awaylineup["player_name"])]
                .dropna(subset=["x", "y"])
                .groupby("playerName", as_index=False)
                .agg({"x": "mean", "y": "mean"})
                .rename(columns={"playerName": "player_name"})
            )
            awayresult = pd.merge(awaylineup, df_averages_away, on="player_name", how="left").dropna(subset=["x", "y"])
        
            if homeresult.empty and awayresult.empty:
                st.info("No positional events available for starters in the selected range.")
                st.stop()
        
            # ---- draw pitch ----
            from mplsoccer import Pitch, add_image
            from matplotlib.font_manager import FontProperties
            import matplotlib.pyplot as plt
        
            # optional theme vars if defined elsewhere
            _pitch_color = "white"; _line_color = "black"; _bg_color = "white"; _text_color = "black"
            try:
                _pitch_color = PitchColor or _pitch_color
                _line_color  = PitchLineColor or _line_color
                _bg_color    = BackgroundColor or _bg_color
                _text_color  = TextColor or _text_color
            except NameError:
                pass
        
            pitch = Pitch(pitch_type="opta", pitch_color=_pitch_color, line_color=_line_color)
            fig, ax = pitch.draw(figsize=(12, 8.25), constrained_layout=True, tight_layout=False)
            fig.set_facecolor(_bg_color)
        
            # ---- plot home ----
            for _, r in homeresult.iterrows():
                pitch.scatter(r["x"], r["y"], s=425, color=_hc1, edgecolors=_hc2, linewidth=1, alpha=1, ax=ax)
                if pd.notna(r.get("squad_number")):
                    pitch.annotate(str(int(r["squad_number"])),
                                   xy=(r["x"] - 0.15, r["y"] - 0.15),
                                   color=_hc2, va="center", ha="center", size=8, weight="bold", ax=ax)
        
            # ---- plot away (flipped to the other half) ----
            for _, r in awayresult.iterrows():
                px, py = (100 - r["x"], 100 - r["y"])
                pitch.scatter(px, py, s=425, color=_ac1, edgecolors=_ac2, linewidth=1, alpha=1, ax=ax)
                if pd.notna(r.get("squad_number")):
                    pitch.annotate(str(int(r["squad_number"])),
                                   xy=(px - 0.15, py - 0.15),
                                   color=_ac2, va="center", ha="center", size=8, weight="bold", ax=ax)
        
            # ---- title ----
            title_font = FontProperties(family="Tahoma", size=15)
            ax.set_title(
                f"{teamname} vs {opponentname} — Average Positions {minute_range[0]}’–{minute_range[1]}’",
                fontproperties=title_font, color=_text_color
            )
        
            # (optional) logos if those images are loaded above
            try:
                add_image(homeimage, fig, left=0.155, bottom=0.15, width=0.1, alpha=0.5, interpolation='hanning')
                add_image(awayimage, fig, left=0.765, bottom=0.15, width=0.1, alpha=0.5, interpolation='hanning')
                add_image(wtaimaged, fig, left=0.462, bottom=0.45, width=0.1, alpha=0.25, interpolation='hanning')
            except Exception:
                pass
        
            st.pyplot(fig)
            plt.close(fig)
        with tab4:
            st.subheader("Player Actions")
        
            # left = pitch, right = controls
            left_col, right_col = st.columns([2, 1], gap="large")
        
            # ---------------- CONTROLS (RIGHT) ----------------
            with right_col:
                players = (
                    df["playerName"].dropna().drop_duplicates().sort_values().tolist()
                    if "playerName" in df.columns else []
                )
                player_choice = st.selectbox("Player", ["— Select —"] + players, index=0, key="pa_player")
        
                passes = df.iloc[0:0]         # default empty
                receiver_choice = "— All —"   # default
                carries = df.iloc[0:0]         # default empty

                if player_choice != "— Select —":
                    needed = {"typeId", "playerName", "x", "y", "end_x", "end_y"}
                    missing = [c for c in needed if c not in df.columns]
                    if missing:
                        st.warning(f"Missing columns for plotting: {', '.join(missing)}")
                    else:
                        passes = df[(df["typeId"] == "Pass") & (df["playerName"] == player_choice)].copy()
                        carries = df[(df["typeId"] == "Carry") & (df["playerName"] == player_choice)].copy()
                        if "pass_recipient" in passes.columns:
                            rx_options = passes["pass_recipient"].dropna().drop_duplicates().sort_values().tolist()
                            receiver_choice = st.selectbox(
                                "Pass Receiver",
                                ["— All —"] + rx_options,
                                index=0,
                                key="pa_receiver"
                            )
                            if receiver_choice != "— All —":
                                passes = passes[passes["pass_recipient"] == receiver_choice]
        
                        st.caption(f"{len(passes)} pass(es) selected.")
        
                        # -------- tick boxes to control which actions to plot --------
                        st.markdown("**Show on pitch:**")
                        select_all_actions = st.checkbox("Select All Actions", False, key="select_all_actions")
                        col_ck1, col_ck2 = st.columns(2)
                        with col_ck1:
                            show_tackles       = st.checkbox("Tackles", value=select_all_actions, key="show_tackles")
                            show_aerials       = st.checkbox("Aerials", value=select_all_actions, key="show_aerials")
                            show_blocks        = st.checkbox("Blocks", value=select_all_actions, key="show_blocks")
                            show_ballrec       = st.checkbox("Ball Recoveries", value=select_all_actions, key="show_ballrec")
                            show_clearances    = st.checkbox("Clearances", value=select_all_actions, key="show_clearances")
                            show_interceptions = st.checkbox("Interceptions", value=select_all_actions, key="show_interceptions")
                        with col_ck2:
                            show_carries      = st.checkbox("Carries", value=select_all_actions, key="show_carries")
                            show_dribbles      = st.checkbox("Dribbles", value=select_all_actions, key="show_dribbles")
                            show_dispossessed  = st.checkbox("Dispossessed", value=select_all_actions, key="show_dispos")
                            show_shot_off      = st.checkbox("Shots Off Target", value=select_all_actions, key="show_off")
                            show_shot_blocked  = st.checkbox("Shots Blocked", value=select_all_actions, key="show_blocked")
                            show_shot_on       = st.checkbox("Shots On Target", value=select_all_actions, key="show_on")
                            show_goals         = st.checkbox("Goals", value=select_all_actions, key="show_goals")

                else:
                    st.caption("Select a player to show their passes.")
                    # defaults if no player chosen (won't be used)
                    show_tackles = show_aerials = show_blocks = show_ballrec = show_clearances = False
                    show_dribbles = show_dispossessed = show_shot_off = show_shot_blocked = show_shot_on = show_goals = False
                    show_interceptions = False
                    show_carries = False

            # ---------------- PLOT (LEFT) ----------------
            with left_col:
                pitch = VerticalPitch(
                    pitch_type='opta',
                    goal_type='box',
                    line_color=PitchLineColor,
                    pitch_color=PitchColor
                )
                fig, ax = pitch.draw(figsize=(7, 10.5))
                fig.set_facecolor(BackgroundColor)
        
                # comet helpers
                def plot_comet_line(ax, x_start, y_start, x_end, y_end, color="green", num_segments=20, linewidth=1.5):
                    for xs, ys, xe, ye in zip(np.asarray(x_start), np.asarray(y_start),
                                              np.asarray(x_end), np.asarray(y_end)):
                        dx = (xe - xs) / num_segments
                        dy = (ye - ys) / num_segments
                        alphas = np.linspace(1, 0, num_segments)
                        for i in range(num_segments):
                            ax.plot([xs + i*dx, xs + (i+1)*dx],
                                    [ys + i*dy, ys + (i+1)*dy],
                                    color=color, alpha=float(alphas[i]), linewidth=linewidth, zorder=3)
        
                def plot_comet_line2(ax, x_start, y_start, x_end, y_end, color="blue", num_segments=10, linewidth=2.0):
                    for xs, ys, xe, ye in zip(np.asarray(x_start), np.asarray(y_start),
                                              np.asarray(x_end), np.asarray(y_end)):
                        dx = (xe - xs) / num_segments
                        dy = (ye - ys) / num_segments
                        alphas = np.linspace(1, 0, num_segments)
                        for i in range(num_segments):
                            ax.plot([xs + i*dx, xs + (i+1)*dx],
                                    [ys + i*dy, ys + (i+1)*dy],
                                    color=color, alpha=float(alphas[i]), linewidth=linewidth, zorder=4)
        
                # plot passes (comets)
                if not passes.empty:
                    outcome_col = "outcome" if "outcome" in passes.columns else None
                    keypass_col = "keyPass" if "keyPass" in passes.columns else None
                    assist_col = "assist" if "assist" in passes.columns else None
                
                    def is_true(s):  # handles 1/0, True/False, "1"/"True"
                        return s.astype(str).str.lower().isin(["1", "true", "yes"]).fillna(False)
                
                    playercomp = passes[passes[outcome_col].eq("Successful")] if outcome_col else passes.iloc[0:0]
                    playerincomp = passes[passes[outcome_col].eq("Unsuccessful")] if outcome_col else passes.iloc[0:0]
                    #playersa = passes[is_true(passes[keypass_col])] if keypass_col in passes.columns else passes.iloc[0:0]
                    #playera = passes[is_true(passes[assist_col])] if assist_col in passes.columns else passes.iloc[0:0]
                    playersa = passes.loc[passes['keyPass']==1]
                    playersa = playersa.loc[playersa['typeId']=='Pass']
                    playera = passes.loc[passes['assist']==1]
                    playera = playera.loc[playera['typeId']=='Pass']
                    # --- Remove overlaps ---
                    if not playersa.empty:
                        playercomp = playercomp[~playercomp["id"].isin(playersa["id"])]
                    if not playera.empty:
                        playersa = playersa[~playersa["id"].isin(playera["id"])]
                
                    # --- Plot ---
                    if not playercomp.empty:
                        plot_comet_line(ax, playercomp["end_y"], playercomp["end_x"],
                                            playercomp["y"],     playercomp["x"],
                                            color="green", num_segments=20, linewidth=1.5)
                    if not playerincomp.empty:
                        plot_comet_line(ax, playerincomp["end_y"], playerincomp["end_x"],
                                            playerincomp["y"],     playerincomp["x"],
                                            color="red", num_segments=20, linewidth=1.5)
                    if not playersa.empty:
                        plot_comet_line(ax, playersa["end_y"], playersa["end_x"],
                                            playersa["y"],     playersa["x"],
                                            color="orange", num_segments=20, linewidth=1.8)
                    if not playera.empty:
                        plot_comet_line2(ax, playera["end_y"], playera["end_x"],
                                             playera["y"],     playera["x"],
                                             color="blue", num_segments=10, linewidth=2.0)
                    if show_carries and not carries.empty:
                        plot_comet_line2(ax, carries["end_y"], carries["end_x"],
                                            carries["y"],     carries["x"],
                                            color="purple", num_segments=10, linewidth=2.0)
                # title
                if player_choice != "— Select —":
                    title_text = f"{player_choice} Actions & Passes"
                    if receiver_choice != "— All —":
                        title_text += f" to {receiver_choice}"
                opponent_name = None
                if (
                    player_choice != "— Select —"
                    and "team_name" in starting_lineups.columns
                    and "name" in teamdata.columns
                ):
                    try:
                        teamname = (
                            starting_lineups.loc[starting_lineups["playerName"] == player_choice, "team_name"]
                            .iloc[0]
                        )
                        opponent_candidates = teamdata.loc[teamdata["name"] != teamname, "name"]
                        if not opponent_candidates.empty:
                            opponent_name = opponent_candidates.iloc[0]
                    except Exception:
                        opponent_name = None
                
                if player_choice != "— Select —":
                    # First line
                    title_main = f"{player_choice} – Actions & Passes"
                    if receiver_choice != "— All —":
                        title_main += f" to {receiver_choice}"
                
                    # Second line (if opponent found)
                    if opponent_name:
                        title_sub = f"vs {opponent_name}"
                    else:
                        title_sub = ""
                
                    # Combine into one multi-line title
                    full_title = title_main if not title_sub else f"{title_main}\n{title_sub}"
                
                    fig.suptitle(
                        full_title,
                        fontproperties=title_font,
                        color=TextColor,
                        ha="center",
                        y=0.865,        # bring closer to the pitch
                        linespacing=1.1 # tighter spacing between lines
                    )
                
                    ax.set_title("")  # clear axes title
                if player_choice != "— Select —" and "player_name" in starting_lineups.columns:
                    try:
                        row = starting_lineups.loc[starting_lineups["player_name"] == player_choice].iloc[0]
                    except Exception:
                        row = None
                
                    def pick(col, default="N/A"):
                        return (row[col] if (row is not None and col in starting_lineups.columns and pd.notna(row[col])) else default)
                
                    minutes_played = pick("minutes_played")
                    try:
                        if minutes_played != "N/A":
                            minutes_played = int(float(minutes_played))
                    except Exception:
                        pass
                
                    position_val   = pick("position")
                    player_impact  = pick("Player Impact")
                    match_rank     = pick("Match Rank")
                    
                    # Ensure match_rank is a whole number if possible
                    try:
                        if match_rank != "N/A":
                            match_rank = int(float(match_rank))
                    except Exception:
                        pass
                    
                    # New compact Player Impact format
                    if player_impact != "N/A" and match_rank != "N/A":
                        impact_str = f"{player_impact} (#{match_rank})"
                    elif player_impact != "N/A":
                        impact_str = f"{player_impact}"
                    else:
                        impact_str = "N/A"
                
                    # Tighter spacing between separators
                    def _mt_escape(s: str) -> str:
                        for ch in r"\^_{}%#&$":
                            s = s.replace(ch, "\\" + ch)
                        return s.replace(" ", r"\ ")
                    
                    def _bold_val(v) -> str:
                        s = _mt_escape(str(v))
                        return rf"$\mathbf{{{s}}}$"
                    
                    footer_parts = [
                        f"Minutes Played: {_bold_val(minutes_played)}",
                        f"Position: {_bold_val(position_val)}",
                        f"Player Impact: {_bold_val(impact_str)}",
                    ]
                    footer_text = " | ".join(footer_parts)
                    
                    bbox = ax.get_position()
                    fig.text(
                        0.5,
                        bbox.y0 - 0.0075,
                        footer_text,
                        ha="center",
                        va="top",
                        fontproperties=title_font,
                        color=TextColor,
                    )  # ← no math_fontfamily here

                # -------- ACTION MARKERS (non-passes), gated by checkboxes --------
                if player_choice != "— Select —":
                    needed_xy = {"x", "y"}
                    if needed_xy.issubset(df.columns):
                        player_events = df[df["playerName"] == player_choice].copy()
        
                        # convenient getters
                        def col(name):      return player_events[name] if name in player_events.columns else None
                        def is_type(t):     return col("typeId").eq(t) if col("typeId") is not None else None
                        def is_outcome(o):  return col("outcome").eq(o) if col("outcome") is not None else None
                        def flag_true(s):   return s.astype(str).str.lower().isin(["1", "true", "yes"]) if s is not None else None
        
                        # masks
                        m_tkl_s   = (is_type("Tackle")        & is_outcome("Successful"))     if is_type("Tackle") is not None else None
                        m_tkl_u   = (is_type("Tackle")        & is_outcome("Unsuccessful"))   if is_type("Tackle") is not None else None
                        m_aer_s   = (is_type("Aerial")        & is_outcome("Successful"))     if is_type("Aerial") is not None else None
                        m_aer_u   = (is_type("Aerial")        & is_outcome("Unsuccessful"))   if is_type("Aerial") is not None else None
                        m_save    =  is_type("Save")                                           if is_type("Save")   is not None else None
                        m_ballrec =  is_type("Ball recovery")                                  if is_type("Ball recovery") is not None else None
                        m_clear   =  is_type("Clearance")                                      if is_type("Clearance") is not None else None
                        m_to_s    = (is_type("Take on")       & is_outcome("Successful"))     if is_type("Take on") is not None else None
                        m_to_u    = (is_type("Take on")       & is_outcome("Unsuccessful"))   if is_type("Take on") is not None else None
                        m_dispos  =  is_type("Dispossessed")                                   if is_type("Dispossessed") is not None else None
                        m_as_blk  = (is_type("Attempt saved") & flag_true(col("shotblocked"))) if is_type("Attempt saved") is not None else None
                        m_miss    =  is_type("Miss")                                           if is_type("Miss")   is not None else None
                        m_as_nblk = (is_type("Attempt saved") & ~flag_true(col("shotblocked"))) if is_type("Attempt saved") is not None and col("shotblocked") is not None else None
                        m_goal    =  is_type("Goal")                                           if is_type("Goal")   is not None else None
                        m_foul_u  = (is_type("Foul")         & is_outcome("Unsuccessful"))    if is_type("Foul")   is not None else None
                        m_intr   =  is_type("Interception")  if is_type("Interception") is not None else None

                        # safe scatter helper
                        def plot_mask(mask, facecolor, edgecolor, marker, size):
                            if mask is None:
                                return
                            try:
                                mask = mask.fillna(False).astype(bool)
                            except Exception:
                                return
                            sub = player_events[mask]
                            if sub.empty:
                                return
                            pitch.scatter(
                                sub["x"], sub["y"],
                                ax=ax,
                                facecolor=facecolor,
                                edgecolor=edgecolor,
                                marker=marker,
                                s=size,
                                zorder=5
                            )
        
                        # conditionally draw groups based on checkboxes
                        if show_tackles:
                            plot_mask(m_tkl_s, facecolor="green", edgecolor="green", marker=">", size=40)
                            plot_mask(m_tkl_u, facecolor="red",   edgecolor="red",   marker=">", size=40)
                        if show_aerials:
                            plot_mask(m_aer_s, facecolor="green", edgecolor="green", marker="s", size=40)
                            plot_mask(m_aer_u, facecolor="red",   edgecolor="red",   marker="s", size=40)
                        if show_blocks:
                            plot_mask(m_save,  facecolor="green", edgecolor="green", marker="p", size=40)
                        if show_ballrec:
                            plot_mask(m_ballrec, facecolor="green", edgecolor="green", marker="d", size=40)
                        if show_clearances:
                            plot_mask(m_clear, facecolor="green", edgecolor="green", marker="^", size=40)
                        if show_dribbles:
                            plot_mask(m_to_s,  facecolor="green", edgecolor="green", marker="P", size=40)
                            plot_mask(m_to_u,  facecolor="red",   edgecolor="red",   marker="P", size=40)
                        if show_dispossessed:
                            plot_mask(m_dispos, facecolor="red",  edgecolor="red",   marker="x", size=40)
                        if show_shot_off:
                            plot_mask(m_miss,   facecolor="red",  edgecolor="red",   marker="o", size=40)
                        if show_shot_blocked:
                            plot_mask(m_as_blk, facecolor="yellow", edgecolor="yellow", marker="o", size=40)
                        if show_shot_on:
                            plot_mask(m_as_nblk, facecolor="green", edgecolor="green", marker="o", size=40)
                        if show_goals:
                            plot_mask(m_goal,   facecolor="green", edgecolor="green", marker="*", size=100)
                        if show_interceptions:
                            plot_mask(m_intr, facecolor="green", edgecolor="green", marker="H", size=40)
                        ax_image = add_image(
                            wtaimaged,
                            fig,
                            left=0.735,        # push to right edge (same anchor space as legend)
                            bottom=0.7,      # higher up so it sits above legend
                            width=0.225,       # adjust to fit
                            alpha=1,
                            interpolation='hanning'
                        )
                        fig.text(
                        0.735 + 0.225 / 2,   # horizontally center under the image
                        0.7 - 0.02,        # a bit below the bottom of the image
                        "Data via Opta",
                        ha="center",
                        va="top",
                        fontsize=8,          # small text
                        color=TextColor)
                        if player_choice != "— Select —" and "team_name" in starting_lineups.columns:
                            try:
                                # Get team name for the selected player
                                teamname = starting_lineups.loc[starting_lineups['playerName'] == player_choice, 'team_name'].iloc[0]
                        
                                # Find team ID from teamdata
                                teamlogoid = teamdata.loc[teamdata['name'] == teamname, 'id'].values[0]
                        
                                # Build image URL
                                URL = f"https://omo.akamai.opta.net/image.php?h=www.scoresway.com&sport=football&entity=team&description=badges&dimensions=150&id={teamlogoid}"
                        
                                # Load image
                                from urllib.request import urlopen
                                from PIL import Image
                                teamimage = Image.open(urlopen(URL))
                        
                                # Add to figure
                                add_image(
                                    teamimage,
                                    fig,
                                    left=0.755, bottom=0.135, width=0.2,
                                    alpha=1, interpolation='hanning'
                                )
                            except Exception as e:
                                st.warning(f"Could not load team logo: {e}")
                        def mask_count(mask):
                            if mask is None:
                                return 0
                            try:
                                return int(mask.fillna(False).astype(bool).sum())
                            except Exception:
                                return 0
                        
                        has_tackles       = (mask_count(m_tkl_s) + mask_count(m_tkl_u)) > 0
                        has_aerials       = (mask_count(m_aer_s) + mask_count(m_aer_u)) > 0
                        has_blocks        = mask_count(m_save) > 0
                        has_ballrec       = mask_count(m_ballrec) > 0
                        has_clearances    = mask_count(m_clear) > 0
                        has_dribbles      = (mask_count(m_to_s) + mask_count(m_to_u)) > 0
                        has_dispossessed  = mask_count(m_dispos) > 0
                        has_shot_off      = mask_count(m_miss) > 0
                        has_shot_blocked  = mask_count(m_as_blk) > 0
                        has_shot_on       = mask_count(m_as_nblk) > 0
                        has_goals         = mask_count(m_goal) > 0
                        has_interceptions = mask_count(m_intr) > 0
                        legend_handles = []
                        legend_labels  = []
                        from matplotlib.lines import Line2D
                        
                        # -- Passes (always shown) --
                        legend_handles += [
                            Line2D([0], [0], color='green',  linewidth=3),
                            Line2D([0], [0], color='red',    linewidth=3),
                            Line2D([0], [0], color='orange', linewidth=3),
                            Line2D([0], [0], color='blue',   linewidth=3),
                            #Line2D([0], [0], color='purple', linewidth=3),
                        ]
                        legend_labels += [
                            'Completed Pass',
                            'Incompleted Pass',
                            'Shot Assist',
                            'Assist',
                            #'Carry',
                        ]
                        
                        # Helper to add a marker (no line)
                        def mkr(marker, face, edge=None, size=8, label=''):
                            if edge is None:
                                edge = face
                            return Line2D(
                                [], [], linestyle='None',
                                marker=marker, markersize=size,
                                markerfacecolor=face, markeredgecolor=edge,
                                label=label
                            )
                        has_carries = not carries.empty
                        if player_choice != "— Select —":
                            if show_carries and has_carries:
                                legend_handles.append(Line2D([0], [0], color='purple', linewidth=3))
                                legend_labels.append('Ball Carries')
# ... existing action legend items ...

                            
                        # -- Actions (include only if checkbox is ticked AND the player actually had any) --
                        if player_choice != "— Select —":
                            if show_tackles and has_tackles:
                                legend_handles.append(mkr('>', 'green', label='Tackles'))
                                legend_labels.append('Tackles')
                       
                            if show_aerials and has_aerials:
                                legend_handles.append(mkr('s', 'green', label='Aerials'))
                                legend_labels.append('Aerials')
                        
                            if show_blocks and has_blocks:
                                legend_handles.append(mkr('p', 'green', label='Blocks'))
                                legend_labels.append('Blocks')
                        
                            if show_ballrec and has_ballrec:
                                legend_handles.append(mkr('d', 'green', label='Ball Recoveries'))
                                legend_labels.append('Ball Recoveries')
                        
                            if show_clearances and has_clearances:
                                legend_handles.append(mkr('^', 'green', label='Clearances'))
                                legend_labels.append('Clearances')
                        
                            if show_interceptions and has_interceptions:
                                legend_handles.append(mkr('H', 'green', label='Interceptions'))
                                legend_labels.append('Interceptions')
                        
                            if show_dribbles and has_dribbles:
                                legend_handles.append(mkr('P', 'green', label='Dribbles'))
                                legend_labels.append('Dribbles')
                        
                            if show_dispossessed and has_dispossessed:
                                legend_handles.append(mkr('x', 'red', label='Dispossessed'))
                                legend_labels.append('Dispossessed')
                        
                            if show_shot_off and has_shot_off:
                                legend_handles.append(mkr('o', 'red', label='Shots Off Target'))
                                legend_labels.append('Shots Off Target')
                        
                            if show_shot_blocked and has_shot_blocked:
                                legend_handles.append(mkr('o', 'yellow', edge='yellow', label='Shots Blocked'))
                                legend_labels.append('Shots Blocked')
                        
                            if show_shot_on and has_shot_on:
                                legend_handles.append(mkr('o', 'green', label='Shots On Target'))
                                legend_labels.append('Shots On Target')
                        
                            if show_goals and has_goals:
                                legend_handles.append(mkr('*', 'green', edge='green', size=12, label='Goals'))
                                legend_labels.append('Goals')
                        
                        # Draw legend to the RIGHT of the pitch and include only what we built
                        leg = ax.legend(
                            legend_handles, legend_labels,
                            loc='center left',
                            bbox_to_anchor=(1.02, 0.5),
                            frameon=False,
                            ncol=1,
                        )
                        
                        # Match theme text color (if defined)
                        try:
                            for txt in leg.get_texts():
                                txt.set_color(TextColor)
                        except Exception:
                            pass
        
                # render at natural size
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
                buf.seek(0)
                st.image(buf)
                plt.close(fig)
                plt.close('all')
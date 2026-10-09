import pandas as pd
import os


def export_csv(df, filename="output.csv"):
    df.to_csv(filename, index=False)


def export_json(df, filename="output.json"):
    df.to_json(filename, orient="records")


def export_monthly_history(df: pd.DataFrame, output_file: str):
    """
    Export all staff reading history for a month into one Excel tab,
    sorted by Date, User, and Reading.
    """
    # Try to detect the correct time column
    possible_time_cols = ["timestamp", "created_at", "Time", "DateTime"]
    time_col = None
    for col in possible_time_cols:
        if col in df.columns:
            time_col = col
            break

    if time_col is None:
        raise KeyError(f"No usable time column found. Available columns: {list(df.columns)}")

    # Ensure datetime type
    df[time_col] = pd.to_datetime(df[time_col])

    # Extract date for grouping
    df['date'] = df[time_col].dt.date

    # Sort by date, then user, then timestamp
    df_sorted = df.sort_values(by=['date', 'name', time_col])

    # Save to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_sorted.to_excel(writer, sheet_name="MonthlyHistory", index=False)


def format_duration(td):
    """Convert Timedelta or float days into H:M:S string."""
    if isinstance(td, pd.Timedelta):
        total_seconds = int(td.total_seconds())
    else:
        total_seconds = int(td * 24 * 3600)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def export_simplified_history(df: pd.DataFrame, output_file: str):
    # Normalize timestamp column
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    df = df.sort_values(by=['name', 'created_at'])

    simplified_rows = []

    for name, group in df.groupby('name'):
        group = group.reset_index(drop=True)
        entry_time = group.loc[0, 'created_at']
        prev_zone = group.loc[0, 'zone']
        item_code = group.loc[0, 'item_code']
        rssi_values = [group.loc[0, 'rssi']]

        for i in range(1, len(group)):
            current_zone = group.loc[i, 'zone']
            current_time = group.loc[i, 'created_at']
            current_rssi = group.loc[i, 'rssi']

            if current_zone != prev_zone:
                duration = current_time - entry_time
                ave_rssi = sum(rssi_values) / len(rssi_values)

                simplified_rows.append({
                    "Zone": prev_zone,
                    "entry_time": entry_time,   # consistent key
                    "duration on site": format_duration(duration),
                    "name": name,
                    "item_code": item_code,
                    "ave_rssi": round(ave_rssi, 2)
                })

                # reset for new zone
                entry_time = current_time
                prev_zone = current_zone
                item_code = group.loc[i, 'item_code']
                rssi_values = [current_rssi]
            else:
                rssi_values.append(current_rssi)

        # close last segment
        duration = group.iloc[-1]['created_at'] - entry_time
        ave_rssi = sum(rssi_values) / len(rssi_values)

        simplified_rows.append({
            "Zone": prev_zone,
            "entry_time": entry_time,       # consistent key
            "duration on site": format_duration(duration),
            "name": name,
            "item_code": item_code,
            "ave_rssi": round(ave_rssi, 2)
        })

    simplified_df = pd.DataFrame(simplified_rows)

    # Resolve overlaps by strongest RSSI
    simplified_df = simplified_df.sort_values(by=['entry_time', 'ave_rssi'], ascending=[True, False])
    simplified_df = simplified_df.drop_duplicates(subset=['entry_time', 'name'], keep='first')

    # Fix sort order: keep staff grouped, chronological, strongest RSSI wins
    simplified_df = simplified_df.sort_values(
        by=['name', 'entry_time', 'ave_rssi'],
        ascending=[True, True, False]
    )

    # Drop duplicates per person per entry_time, keep strongest RSSI
    simplified_df = simplified_df.drop_duplicates(
        subset=['name', 'entry_time'],
        keep='first'
    )

    # Format entry_time for Excel output
    simplified_df['entry_time'] = pd.to_datetime(simplified_df['entry_time'], errors='coerce').dt.strftime("%Y-%m-%d %H:%M:%S")

    # Rename back to 'entry time' for Excel header consistency
    # simplified_df = simplified_df.rename(columns={'entry_time': 'entry time'})

    if os.path.exists(output_file):
        os.remove(output_file)

    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        simplified_df.to_excel(writer, sheet_name="SimplifiedHistory", index=False)


def resolve_location_conflicts(df: pd.DataFrame, time_window='30s'):
    """
    Collapse overlapping zone records per person using strongest RSSI.
    Merge weaker location durations into the stronger one so time is not lost.
    """

    # Normalize entry_time
    if 'entry time' in df.columns:
        df['entry_time'] = pd.to_datetime(df['entry time'], errors='coerce')
        df = df.drop(columns=['entry time'])
    else:
        df['entry_time'] = pd.to_datetime(df['entry_time'], errors='coerce')

    df = df.sort_values(by=['name', 'entry_time'])

    merged_rows = []

    for name, group in df.groupby('name'):
        group = group.set_index('entry_time')
        grouped = group.groupby(pd.Grouper(freq=time_window))

        for _, bucket in grouped:
            if bucket.empty:
                continue

            # Prefer longest duration, fallback to strongest RSSI
            bucket['duration_td'] = pd.to_timedelta(bucket['duration_on_site'], errors='coerce')

            if bucket['duration_td'].notna().any():
                best_idx = bucket['duration_td'].idxmax()
            else:
                best_idx = bucket['ave_rssi'].idxmax()

            best_row = bucket.loc[best_idx].copy()

            # Sum all durations in the bucket
            total_duration = pd.to_timedelta(bucket['duration_on_site'], errors='coerce').sum()
            best_row['duration_on_site'] = format_duration(total_duration)

            # Ensure entry_time is carried forward
            best_row['entry_time'] = best_row.name

            merged_rows.append(best_row)

    merged_df = pd.DataFrame(merged_rows).reset_index(drop=True)

    # Final chronological sort
    merged_df = merged_df.sort_values(by=['name', 'entry_time']).reset_index(drop=True)

    return merged_df


def merge_consecutive_same_location(df: pd.DataFrame, merge_gap=pd.Timedelta(minutes=5), min_duration=pd.Timedelta(minutes=2)):
    """
    Merge consecutive records for the same zone per person.
    Durations are summed, strongest RSSI is kept.
    Also collapses repeated same-zone records if gap <= merge_gap.
    """

    df['entry_time'] = pd.to_datetime(df['entry_time'], errors='coerce')
    df = df.sort_values(by=['name', 'entry_time'])

    merged_rows = []

    for name, group in df.groupby('name'):
        prev_zone = None
        prev_start = None
        total_duration = pd.Timedelta(0)
        best_rssi = None
        item_code = None

        for _, row in group.iterrows():
            zone = row['zone']
            duration = pd.to_timedelta(row['duration_on_site'], errors='coerce')
            rssi = row['ave_rssi']
            start = row['entry_time']
            item_code = row['item_code']

            if zone == prev_zone and (start - prev_start) <= merge_gap:
                # collapse into previous block
                total_duration += duration
                if best_rssi is None or rssi > best_rssi:
                    best_rssi = rssi
            else:
                if prev_zone is not None:
                    if total_duration >= min_duration:
                        merged_rows.append({
                            "zone": prev_zone,
                            "entry_time": prev_start,
                            "duration_on_site": format_duration(total_duration),
                            "name": name,
                            "item_code": item_code,
                            "ave_rssi": best_rssi
                        })
                prev_zone = zone
                prev_start = start
                total_duration = duration
                best_rssi = rssi

        # flush last block
        if prev_zone is not None and total_duration >= min_duration:
            merged_rows.append({
                "zone": prev_zone,
                "entry_time": prev_start,
                "duration_on_site": format_duration(total_duration),
                "name": name,
                "item_code": item_code,
                "ave_rssi": best_rssi
            })

    merged_df = pd.DataFrame(merged_rows).reset_index(drop=True)
    merged_df = merged_df.sort_values(by=['name', 'entry_time']).reset_index(drop=True)

    return merged_df


def apply_min_duration_cutoff(df, min_duration=pd.Timedelta(minutes=2)):
    """
    Remove or merge segments shorter than min_duration.
    """
    cleaned_rows = []
    for _, row in df.iterrows():
        duration = pd.to_timedelta(row['duration_on_site'], errors='coerce')
        if duration >= min_duration:
            cleaned_rows.append(row)
        else:
            # merge into previous if same zone
            if cleaned_rows and cleaned_rows[-1]['zone'] == row['zone']:
                prev = cleaned_rows[-1]
                prev_duration = pd.to_timedelta(prev['duration_on_site'], errors='coerce')
                new_duration = prev_duration + duration
                prev['duration_on_site'] = format_duration(new_duration)
    return pd.DataFrame(cleaned_rows)


def merge_final_same_zone(df: pd.DataFrame, merge_gap=pd.Timedelta(minutes=5)):
    """
    Final merge pass: collapse consecutive rows with the same zone
    if the gap between them is small.
    """
    if df.empty:
        return df

    df = df.sort_values(by=['name', 'entry_time']).reset_index(drop=True)
    final_rows = []

    prev = df.iloc[0].to_dict()
    prev_duration = pd.to_timedelta(prev['duration_on_site'], errors='coerce')

    for _, row in df.iloc[1:].iterrows():
        duration = pd.to_timedelta(row['duration_on_site'], errors='coerce')
        if row['zone'] == prev['zone'] and row['name'] == prev['name']:
            gap = row['entry_time'] - prev['entry_time']
            if gap <= merge_gap:
                # merge into previous
                prev_duration += duration
                prev['duration_on_site'] = format_duration(prev_duration)
                prev['ave_rssi'] = max(prev['ave_rssi'], row['ave_rssi'])
                continue
        # flush previous
        final_rows.append(prev)
        prev = row.to_dict()
        prev_duration = duration

    final_rows.append(prev)
    return pd.DataFrame(final_rows).reset_index(drop=True)


def collapse_same_zone(df: pd.DataFrame):
    """
    Collapse consecutive same-zone records for each person.
    Durations are summed, strongest RSSI is kept.
    """
    if df.empty:
        return df

    df = df.sort_values(by=['name', 'entry_time']).reset_index(drop=True)
    collapsed_rows = []

    prev = df.iloc[0].to_dict()
    prev_duration = pd.to_timedelta(prev['duration_on_site'], errors='coerce')

    for _, row in df.iloc[1:].iterrows():
        duration = pd.to_timedelta(row['duration_on_site'], errors='coerce')
        if row['zone'] == prev['zone'] and row['name'] == prev['name']:
            # merge consecutive same-zone records
            prev_duration += duration
            prev['duration_on_site'] = format_duration(prev_duration)
            prev['ave_rssi'] = max(prev['ave_rssi'], row['ave_rssi'])
            continue
        # flush previous
        collapsed_rows.append(prev)
        prev = row.to_dict()
        prev_duration = duration

    collapsed_rows.append(prev)
    return pd.DataFrame(collapsed_rows).reset_index(drop=True)

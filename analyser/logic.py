import pandas as pd
# Global threshold for minimum segment duration
min_threshold_seconds = 30


def filter_by_user(df, user_name: str):
    return df[df['name'] == user_name]


def filter_by_zone(df, zone: str):
    return df[df['zone'] == zone]


def filter_by_time(df, start, end):
    return df[(df['created_at'] >= start) & (df['created_at'] <= end)]


def movement_path(df, user_name: str):
    """
    Returns the ordered movement path for a given user,
    showing zone + reader transitions.
    """
    # Filter by user and sort by time
    user_logs = df[df['name'] == user_name].sort_values(by='created_at')

    # Build sequence of zone/reader pairs
    path = [f"{row['zone']} / {row['reader']}" for _, row in user_logs.iterrows()]

    return path


def compressed_movement_path(df, user_name: str):
    """
    Returns a compressed movement path for a given user,
    showing zones with entry/exit times and duration spent.
    Travel segments are not included.
    """
    user_logs = df[df['name'] == user_name].sort_values(by='created_at')

    path = []
    current_zone = None
    start_time = None

    for _, row in user_logs.iterrows():
        zone = row['zone']
        time = row['created_at']

        if current_zone is None:
            current_zone = zone
            start_time = time
        elif zone != current_zone:
            # Zone changed → close previous segment at last detection in that zone
            prev_zone_logs = user_logs[(user_logs['zone'] == current_zone) &
                                       (user_logs['created_at'] >= start_time) &
                                       (user_logs['created_at'] <= time)]
            exit_time = prev_zone_logs['created_at'].max()

            duration = exit_time - start_time
            path.append((current_zone, start_time, exit_time, duration))

            # Start new zone
            current_zone = zone
            start_time = time

    # Close last segment
    if current_zone is not None:
        exit_time = user_logs.iloc[-1]['created_at']
        duration = exit_time - start_time
        path.append((current_zone, start_time, exit_time, duration))

    return path


def compressed_movement_path_with_reader(df, user_name: str):
    """
    Returns a compressed movement path for a given user,
    showing zone + reader transitions with entry/exit times and duration.
    Also returns a summary of total time spent per location (raw Timedelta).
    Consecutive short gaps in the same location are merged.
    """
    user_logs = df[df['name'] == user_name].sort_values(by='created_at')

    path = []
    summary = {}

    current_location = None
    start_time = None

    # configurable thresholds
    min_threshold = pd.Timedelta(seconds=30)   # minimum stay duration
    merge_gap = pd.Timedelta(seconds=30)       # max gap to merge back into same location

    for _, row in user_logs.iterrows():
        location = f"{row['zone']} / {row['reader']}"
        time = row['created_at']

        if current_location is None:
            current_location = location
            start_time = time
        elif location != current_location:
            # Close previous segment
            prev_logs = user_logs[(user_logs['zone'] + " / " + user_logs['reader'] == current_location) &
                                  (user_logs['created_at'] >= start_time) &
                                  (user_logs['created_at'] <= time)]
            exit_time = prev_logs['created_at'].max()
            duration = exit_time - start_time

            if duration >= min_threshold:
                path.append((current_location, start_time, exit_time, duration))
                summary[current_location] = summary.get(current_location, pd.Timedelta(0)) + duration
            else:
                # Merge into previous if same location
                if path and path[-1][0] == current_location:
                    prev_loc, prev_start, prev_end, prev_duration = path[-1]
                    new_duration = prev_duration + duration
                    path[-1] = (prev_loc, prev_start, exit_time, new_duration)
                    summary[current_location] += duration
                # Otherwise skip

            # Check if new location is same as last and gap is short → merge
            if path and path[-1][0] == location and (time - exit_time) <= merge_gap:
                prev_loc, prev_start, prev_end, prev_duration = path[-1]
                new_duration = prev_duration + (time - exit_time)
                path[-1] = (prev_loc, prev_start, time, new_duration)
                summary[location] += (time - exit_time)
                current_location = location
                start_time = time
                continue

            # Start new location
            current_location = location
            start_time = time

    # Close last segment
    if current_location is not None:
        exit_time = user_logs.iloc[-1]['created_at']
        duration = exit_time - start_time
        if duration >= min_threshold:
            path.append((current_location, start_time, exit_time, duration))
            summary[current_location] = summary.get(current_location, pd.Timedelta(0)) + duration
        else:
            if path and path[-1][0] == current_location:
                prev_loc, prev_start, prev_end, prev_duration = path[-1]
                new_duration = prev_duration + duration
                path[-1] = (prev_loc, prev_start, exit_time, new_duration)
                summary[current_location] += duration

    path = merge_consecutive_segments(path, merge_gap=pd.Timedelta(seconds=45))
    path = apply_min_duration_cutoff(path, min_duration=pd.Timedelta(seconds=20))
    return path, summary


def compressed_movement_path_with_duration(df, user_name: str, travel_threshold_minutes=5):
    """
    Returns a compressed movement path for a given user,
    showing zones with entry/exit times and duration spent.
    Travel segments are included if the gap exceeds the threshold.
    """
    user_logs = df[df['name'] == user_name].sort_values(by='created_at')

    path = []
    current_zone = None
    start_time = None

    for _, row in user_logs.iterrows():
        zone = row['zone']
        time = row['created_at']

        if current_zone is None:
            current_zone = zone
            start_time = time
        elif zone != current_zone:
            # Zone changed → close previous segment
            prev_zone_logs = user_logs[(user_logs['zone'] == current_zone) &
                                       (user_logs['created_at'] >= start_time) &
                                       (user_logs['created_at'] <= time)]
            exit_time = prev_zone_logs['created_at'].max()

            duration = exit_time - start_time
            # Skip or merge very short segments
            min_threshold = pd.Timedelta(seconds=min_threshold_seconds)    # adjust as needed
            if min_threshold >= duration:
                # Merge into previous segment if possible
                if path and path[-1][0] == current_zone:
                    prev_zone, prev_start, prev_end, prev_duration = path[-1]
                    new_duration = prev_duration + duration
                    path[-1] = (prev_zone, prev_start, exit_time, new_duration)
                # Otherwise skip
            else:
                path.append((current_zone, start_time, exit_time, duration))

            # Travel gap between exit and new entry
            gap = (time - exit_time).total_seconds() / 60
            if gap > travel_threshold_minutes:
                path.append(("Travel", exit_time, time, time - exit_time))

            # Start new zone
            current_zone = zone
            start_time = time

    # Close last segment
    if current_zone is not None:
        exit_time = user_logs.iloc[-1]['created_at']
        duration = exit_time - start_time
        if duration > pd.Timedelta(0):
            path.append((current_zone, start_time, exit_time, duration))

    return path


def format_duration(td):
    """
    Convert a pandas Timedelta into a human-friendly string.
    """
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 and hours == 0:  # only show seconds if short stay
        parts.append(f"{seconds}s")

    return " ".join(parts) if parts else "0s"


def merge_consecutive_segments(path, merge_gap=pd.Timedelta(seconds=45)):
    """
    Merge consecutive path segments if they are the same location
    and the gap between them is less than or equal to merge_gap.
    """
    if not path:
        return path

    merged = [path[0]]
    for loc, start, end, duration in path[1:]:
        prev_loc, prev_start, prev_end, prev_duration = merged[-1]

        # If same location and gap is small, merge
        if loc == prev_loc and (start - prev_end) <= merge_gap:
            new_end = end
            new_duration = prev_duration + (end - prev_end)
            merged[-1] = (prev_loc, prev_start, new_end, new_duration)
        else:
            merged.append((loc, start, end, duration))

    return merged


def apply_min_duration_cutoff(path, min_duration=pd.Timedelta(seconds=20)):
    """
    Remove or merge segments shorter than min_duration.
    """
    if not path:
        return path

    cleaned = []
    for loc, start, end, duration in path:
        if duration >= min_duration:
            cleaned.append((loc, start, end, duration))
        else:
            # Merge into previous if same location
            if cleaned and cleaned[-1][0] == loc:
                prev_loc, prev_start, prev_end, prev_duration = cleaned[-1]
                new_end = end
                new_duration = prev_duration + duration
                cleaned[-1] = (prev_loc, prev_start, new_end, new_duration)
            # Otherwise skip
    return cleaned


def format_duration2(td: pd.Timedelta) -> str:
    """Format Timedelta to H:MM:SS without '0 days'."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"


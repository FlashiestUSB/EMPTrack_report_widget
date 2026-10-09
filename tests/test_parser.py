# old methods that I am no long using but still want to keep for future reference

# first 5 rows of the dataframe
# print("==== First 5 rows ====")
# print(df.head(5))

# temporary hardcoded filter
# user_name = "Chris Camilleri"
# user_name = "Tom Sellars"
# user_logs = df[df['name'] == user_name]
# print(f"\n=== Logs for {user_name} ===")
# print(user_logs[['created_at', 'zone', 'rssi']].head(10))   # show top 10 rows

# path = logic.movement_path(df, user_name)
# print(f"\n=== Movement Path for {user_name} ===")
# print(" -> ".join(path[:20]))   # show first 20 steps

# Compressed movement path
# path, summary = logic.compressed_movement_path_with_reader(df, user_name)

# print(f"\n=== Compressed Movement Path for {user_name} ===")
# for zone, start, end, duration in path[:50]:    # show first 10 segments
#     print(f"{zone}: {start} → {end} | Duration: {logic.format_duration(duration)}")

# Show summary
# print(f"\n=== Daily Summary for {user_name} ===")
# total_time = pd.Timedelta(0)

# for location, duration in summary.items():
#     print(f"{location}: {logic.format_duration(duration)}")
#     total_time += duration

# print(f"Total time logged: {logic.format_duration(total_time)}")

# Compressed movement path with duration
# path = logic.compressed_movement_path_with_duration(df, user_name)

# print(f"\n=== Movement Path with Duration for {user_name} ===")
# for zone, start, end, duration in path[:20]:    # show first 10 segments
#     print(f"{zone}: {start} → {end} | Duration: {logic.format_duration(duration)}")

# Let's play with names for fun
# filename = os.path.basename(file_path)
# name, ext = os.path.splitext(filename)
# timestamp = datetime.now().strftime("%Y%M%D_%H%M%S")
# new_filename = f"{name}_#_{timestamp}{ext}"

# move file to history with a new name
# dest_path = os.path.join(history_dir, new_filename)
# shutil.move(file_path, dest_path)

# print(f"Moved {filename} to history as {new_filename}")

# Write to log file
# with open(log_file, "a") as log:
#    log.write(f"{datetime.now()} - Processed {filename} -> {new_filename}\n")
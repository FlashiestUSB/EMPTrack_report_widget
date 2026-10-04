from analyser import parser, logic
from datetime import datetime
import os
import glob
import shutil
import pandas as pd


def main():
    # input directory
    input_dir = "data_input"
    # where I want to move the file after it haws been processed
    history_dir = os.path.join(input_dir, "history")
    # it never hurts to have a log if you have enough hdd space
    log_file = "process_log.txt"

    # find first xlsx file in the data input folder
    working_file = glob.glob(os.path.join(input_dir, "*.xlsx"))

    # check if there is no file at runtime
    if not working_file:
        print("No Excel files found in data_input.")
        return

    # I only want the first file or if there are more than one 0 == first file, 1 == second file etc
    file_path = working_file[0]
    print(f"Processing: {file_path}")

    # load the log
    df = parser.load_log(file_path)
    # first 5 rows of the dataframe
    print("==== First 5 rows ====")
    print(df.head(5))

    # temporary hardcoded filter
    # user_name = "Chris Camilleri"
    user_name = "Tom Sellars"
    user_logs = df[df['name'] == user_name]
    print(f"\n=== Logs for {user_name} ===")
    print(user_logs[['created_at', 'zone', 'rssi']].head(10))   # show top 10 rows

    path = logic.movement_path(df, user_name)
    print(f"\n=== Movement Path for {user_name} ===")
    print(" -> ".join(path[:20]))   # show first 20 steps

    # Compressed movement path
    path, summary = logic.compressed_movement_path_with_reader(df, user_name)

    print(f"\n=== Compressed Movement Path for {user_name} ===")
    for zone, start, end, duration in path[:50]:    # show first 10 segments
        print(f"{zone}: {start} → {end} | Duration: {logic.format_duration(duration)}")

    # Show summary
    print("\n=== Daily Summary for Chris Camilleri ===")
    total_time = pd.Timedelta(0)

    for location, duration in summary.items():
        print(f"{location}: {logic.format_duration(duration)}")
        total_time += duration

    print(f"Total time logged: {logic.format_duration(total_time)}")

    # Compressed movement path with duration
    path = logic.compressed_movement_path_with_duration(df, user_name)

    print(f"\n=== Movement Path with Duration for {user_name} ===")
    for zone, start, end, duration in path[:20]:    # show first 10 segments
        print(f"{zone}: {start} → {end} | Duration: {logic.format_duration(duration)}")

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

    print("")
    print(f"Logged processing info to {log_file}")


if __name__ == "__main__":
    main()

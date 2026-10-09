from analyser import parser, logic, exporter
from datetime import datetime
from openpyxl import load_workbook
import os
import glob
import shutil
import pandas as pd


def main():
    # input directory
    input_dir = "data_input"
    # where to move the file after it has been processed
    history_dir = os.path.join(input_dir, "history")
    # log file
    log_file = "process_log.txt"

    # find first xlsx file in the data input folder
    working_file = glob.glob(os.path.join(input_dir, "*.xlsx"))

    # check if there is no file at runtime
    if not working_file:
        print("No Excel files found in data_input.")
        return

    # pick the first file
    file_path = working_file[0]
    print(f"Processing: {file_path}")

    # load the log
    df = parser.load_log(file_path)

    # search for all the staff names in the file
    staff_names = df['name'].unique()

    # Loop through each staff member and generate reports
    for staff in staff_names:
        path, summary = logic.compressed_movement_path_with_reader(df, staff)

        print(f"\n=== Compressed Movement Path for {staff} ===")
        for loc, start, end, duration in path:
            print(f"{loc}: {start} → {end} | Duration: {logic.format_duration2(duration)}")

        print(f"\n=== Daily Summary for {staff} ===")
        total = sum(summary.values(), pd.Timedelta(0))
        for loc, duration in summary.items():
            print(f"{loc}: {logic.format_duration2(duration)}")
        print(f"Total time logged: {logic.format_duration2(total)}\n")

        # Compressed movement path with duration
        path = logic.compressed_movement_path_with_duration(df, staff)

        print(f"\n=== Movement Path with Duration for {staff} ===")
        for zone, start, end, duration in path:
            print(f"{zone}: {start} → {end} | Duration: {logic.format_duration2(duration)}")

    print("")
    print(f"Logged processing info to {log_file}")

    # Export full monthly history report
    month_report_file = "monthly_history.xlsx"
    exporter.export_monthly_history(df, month_report_file)
    print(f"Monthly history report saved to {month_report_file}")

    # Export simplified report
    simplified_report_file = "simplified_history.xlsx"
    exporter.export_simplified_history(df, simplified_report_file)
    print(f"Simplified history report saved to {simplified_report_file}")

    # Step 2: Load the simplified file back in
    simplified_df = pd.read_excel(simplified_report_file)
    # Normalize column names after reload
    simplified_df.columns = [c.strip().lower().replace(" ", "_") for c in simplified_df.columns]
    print("Simplified_df columns:", simplified_df.columns.tolist())

    # Step 3: Resolve conflicts (merge weaker zones into stronger ones)
    cleaned_df = exporter.resolve_location_conflicts(simplified_df, time_window='30s')

    # Step 3b: Second pass conflict resolution (wider window)
    final_df = exporter.resolve_location_conflicts(cleaned_df, time_window='45s')

    # Step 3c: Merge consecutive same-zone records
    final_df = exporter.merge_consecutive_same_location(final_df)

    # Step 3d: Apply minimum duration cutoff
    final_df = exporter.apply_min_duration_cutoff(final_df, min_duration=pd.Timedelta(minutes=2))

    # Step 4: Final cleanup of durations before saving
    final_df['duration_on_site'] = pd.to_timedelta(final_df['duration_on_site'], errors='coerce')
    final_df['duration_on_site'] = final_df['duration_on_site'].apply(exporter.format_duration)

    # Step 5: Optional final merge pass to collapse repeated zones
    # Comment this out if you want to inspect the output before collapsing
    final_df = exporter.merge_final_same_zone(final_df, merge_gap=pd.Timedelta(minutes=5))

    # Step 6: Collapse consecutive same-zone records
    final_df = exporter.collapse_same_zone(final_df)

    # Step 7: Rename columns for Excel output
    final_df = final_df.rename(columns={
        'entry_time': 'entry time',
        'duration_on_site': 'duration on site'
    })

    # Save final cleaned version
    cleaned_report_file = "simplified_history_cleaned.xlsx"
    final_df.to_excel(cleaned_report_file, index=False)

    # Auto-adjust column widths
    wb = load_workbook(cleaned_report_file)
    ws = wb.active

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter  # Get the column name
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = max_length + 2  # add a little padding
        ws.column_dimensions[col_letter].width = adjusted_width

    wb.save(cleaned_report_file)

    print(f"Cleaned history report saved to {cleaned_report_file}")


if __name__ == "__main__":
    main()

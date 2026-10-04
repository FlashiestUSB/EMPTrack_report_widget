import pandas as pd


def load_log(file_path: str) -> pd.DataFrame:
    # Read log report Excel file
    df = pd.read_excel(file_path, skiprows=6, header=1, engine="openpyxl")

    # The first row after skiprows is actually the header → set it
    df.columns = df.iloc[0]  # take row 0 as header
    df = df.drop(0)  # drop that header row from data

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Convert created_at to datetime
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

    return df

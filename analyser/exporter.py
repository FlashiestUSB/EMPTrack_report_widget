def export_csv(df, filename="output.csv"):
    df.to_csv(filename, index=False)


def export_json(df, filename="output.json"):
    df.to_json(filename, orient="records")

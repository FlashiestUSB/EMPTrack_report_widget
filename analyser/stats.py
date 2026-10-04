def zone_usage(df):
    return df['zone'].value_counts()


def busiest_times(df):
    df['hour'] = pd.to_datetime(df['created_at']).dt.hour
    return df['hour'].value_counts().sort_index()


def rssi_trends(df):
    return df.groupby('zone')['rssi'].mean()


import pandas as pd

df = pd.read_csv('sensor_data.csv')
print(df.describe())
print("Lead Speed max:", df['lead_speed'].max())
print("Lead Speed min:", df['lead_speed'].min())
print("Lead Speed mean:", df['lead_speed'].mean())

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.express as px
import os

url = "https://api.open-meteo.com/v1/forecast?latitude=25.05&longitude=121.52&hourly=temperature_2m,relative_humidity_2m"

data = requests.get(url).json()

times = data["hourly"]["time"][:24]
temps = data["hourly"]["temperature_2m"][:24]
humidity = data["hourly"]["relative_humidity_2m"][:24]

df = pd.DataFrame({
    "time": times,
    "temperature": temps,
    "humidity": humidity
})

df.to_csv("weather.csv", index=False)

st.title("Taipei Weather Dashboard")

st.metric("Current Temperature", f"{temps[0]} °C")
st.metric("Current Humidity", f"{humidity[0]} %")

fig = px.line(df, x="time", y="temperature", title="24-hour Temperature")

st.plotly_chart(fig)
st.dataframe(df)
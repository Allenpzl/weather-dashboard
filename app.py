import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Weather Dashboard", page_icon="🌤️", layout="wide")

CITIES = {
    "Taipei": (25.05, 121.52),
    "Taichung": (24.15, 120.67),
    "Kaohsiung": (22.63, 120.30),
    "Hsinchu": (24.81, 120.97),
}

st.title("🌤️ Taiwan Weather Dashboard")
st.caption("Simple API-based dashboard with a small data pipeline")

city = st.sidebar.selectbox("Select City", list(CITIES.keys()), index=0)
lat, lon = CITIES[city]

@st.cache_data(ttl=3600)
def fetch_weather(latitude: float, longitude: float) -> pd.DataFrame:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&hourly=temperature_2m,relative_humidity_2m"
        "&forecast_days=1&timezone=Asia%2FTaipei"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()
    data = response.json()

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    humidity = hourly.get("relative_humidity_2m", [])

    df = pd.DataFrame(
        {
            "time": pd.to_datetime(times),
            "temperature": temps,
            "humidity": humidity,
        }
    )
    return df

try:
    df = fetch_weather(lat, lon)

    if df.empty:
        st.error("No weather data returned from the API.")
        st.stop()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.sidebar.write(f"Last updated: {now}")

    current_temp = df.iloc[0]["temperature"]
    current_humidity = df.iloc[0]["humidity"]

    col1, col2, col3 = st.columns(3)
    col1.metric("City", city)
    col2.metric("Current Temperature", f"{current_temp:.1f} °C")
    col3.metric("Current Humidity", f"{current_humidity:.0f} %")

    st.write(f"Data source: Open-Meteo API for {city}")

    left, right = st.columns(2)

    with left:
        fig_temp = px.line(
            df,
            x="time",
            y="temperature",
            title=f"{city} Temperature (Next 24 Hours)",
            markers=True,
        )
        fig_temp.update_layout(xaxis_title="Time", yaxis_title="°C")
        st.plotly_chart(fig_temp, use_container_width=True)

    with right:
        fig_humidity = px.line(
            df,
            x="time",
            y="humidity",
            title=f"{city} Humidity (Next 24 Hours)",
            markers=True,
        )
        fig_humidity.update_layout(xaxis_title="Time", yaxis_title="%")
        st.plotly_chart(fig_humidity, use_container_width=True)

    with st.expander("Show raw data"):
        st.dataframe(df, use_container_width=True)

except requests.RequestException as e:
    st.error("Failed to fetch weather data from the API.")
    st.exception(e)
except Exception as e:
    st.error("Unexpected error occurred.")
    st.exception(e)

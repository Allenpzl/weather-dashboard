import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

st.set_page_config(page_title="Taiwan Weather Dashboard", layout="wide")

# -----------------------
# Settings
# -----------------------
CACHE_FILE = Path("weather_cache.csv")

CITIES = {
    "Taipei": (25.05, 121.52),
    "Taichung": (24.15, 120.67),
    "Kaohsiung": (22.63, 120.30)
}

# -----------------------
# UI
# -----------------------
st.title("Taiwan Weather Dashboard")
st.caption("Streamlit + Open-Meteo Data Pipeline")

city = st.sidebar.selectbox("Select City", list(CITIES.keys()))
lat, lon = CITIES[city]

# -----------------------
# Refresh button
# -----------------------
refresh = st.sidebar.button("🔄 Refresh Data")

if refresh:
    st.cache_data.clear()
    st.rerun()

# -----------------------
# Cache load/save (file-based)
# -----------------------
def save_cache(df):
    df.to_csv(CACHE_FILE, index=False)

def load_cache():
    if CACHE_FILE.exists():
        df = pd.read_csv(CACHE_FILE, parse_dates=["time"])
        return df
    return None

# -----------------------
# Demo fallback data
# -----------------------
def demo_data():
    now = pd.Timestamp.now().floor("h")
    time_index = pd.date_range(now, periods=24, freq="h")

    return pd.DataFrame({
        "time": time_index,
        "temperature": [26]*24,
        "humidity": [75]*24,
        "precipitation": [0]*24,
        "precipitation_probability": [10]*24
    })

# -----------------------
# Fetch function
# -----------------------
@st.cache_data(ttl=21600)
def fetch_weather(lat, lon):

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,relative_humidity_2m,precipitation,precipitation_probability"
        "&forecast_days=2"
        "&timezone=Asia%2FTaipei"
    )

    try:
        r = requests.get(url, timeout=10)

        if r.status_code == 429:
            return None, "rate_limited"

        r.raise_for_status()

        data = r.json()

        df = pd.DataFrame({
            "time": pd.to_datetime(data["hourly"]["time"]),
            "temperature": data["hourly"]["temperature_2m"],
            "humidity": data["hourly"]["relative_humidity_2m"],
            "precipitation": data["hourly"]["precipitation"],
            "precipitation_probability": data["hourly"]["precipitation_probability"]
        })

        df = df.head(24)

        save_cache(df)

        return df, "live"

    except Exception:
        return None, "error"

# -----------------------
# Load data logic
# -----------------------
df, status = fetch_weather(lat, lon)

if status != "live":
    cached = load_cache()

    if cached is not None:
        df = cached
        st.info("Using cached data (API unavailable)")
    else:
        df = demo_data()
        st.warning("Using demo data (no API + no cache)")

# -----------------------
# Metrics
# -----------------------
current_temp = df.iloc[0]["temperature"]
current_humidity = df.iloc[0]["humidity"]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("City", city)

with col2:
    st.metric("Temperature", f"{current_temp:.1f} °C")

with col3:
    st.metric("Humidity", f"{current_humidity:.0f} %")

st.write(f"Data source: {status}")

# -----------------------
# Charts
# -----------------------
fig1 = px.line(df, x="time", y="temperature", title="Temperature")
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.line(df, x="time", y="humidity", title="Humidity")
st.plotly_chart(fig2, use_container_width=True)

fig3 = px.bar(df, x="time", y="precipitation", title="Rainfall")
st.plotly_chart(fig3, use_container_width=True)

st.metric("Total Rainfall", f"{df['precipitation'].sum():.1f} mm")

with st.expander("Raw Data"):
    st.dataframe(df)

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import time

st.set_page_config(
    page_title="Taiwan Weather Dashboard",
    layout="wide"
)

CACHE_DIR = Path(".weather_cache")
CACHE_DIR.mkdir(exist_ok=True)

CITIES = {
    "Taipei": (25.05, 121.52),
    "Taichung": (24.15, 120.67),
    "Kaohsiung": (22.63, 120.30)
}

st.title("Taiwan Weather Dashboard")
st.caption("Weather Dashboard with Data Pipeline and Automatic Updates")

city = st.sidebar.selectbox(
    "Select City",
    list(CITIES.keys())
)

lat, lon = CITIES[city]


def cache_path(lat, lon):
    return CACHE_DIR / f"{lat}_{lon}.csv"


def build_demo_data():
    now = pd.Timestamp.now(tz="Asia/Taipei").tz_localize(None).floor("h")
    times = pd.date_range(start=now, periods=24, freq="h")

    temperature = [26, 26, 25, 25, 24, 24, 25, 27, 29, 31, 32, 33,
                   33, 32, 31, 30, 29, 28, 28, 27, 27, 26, 26, 26]
    humidity = [78, 80, 82, 84, 85, 83, 80, 76, 72, 68, 65, 62,
                60, 61, 64, 68, 72, 75, 78, 80, 81, 82, 83, 84]
    precipitation = [0, 0, 0, 0, 0, 0, 0, 0.1, 0.2, 0.0, 0.0, 0.0,
                     0.0, 0.0, 0.0, 0.1, 0.3, 0.5, 0.2, 0, 0, 0, 0, 0]
    precipitation_probability = [10, 10, 10, 10, 10, 15, 15, 20, 25, 20, 15, 15,
                                 10, 10, 10, 15, 20, 30, 20, 15, 10, 10, 10, 10]

    return pd.DataFrame({
        "time": times,
        "temperature": temperature,
        "humidity": humidity,
        "precipitation": precipitation,
        "precipitation_probability": precipitation_probability
    })


def save_cache(df, lat, lon):
    path = cache_path(lat, lon)
    df.to_csv(path, index=False)


def load_cache(lat, lon):
    path = cache_path(lat, lon)
    if path.exists():
        df = pd.read_csv(path, parse_dates=["time"])
        fetched_at = datetime.fromtimestamp(
            path.stat().st_mtime,
            tz=ZoneInfo("Asia/Taipei")
        ).strftime("%Y-%m-%d %H:%M:%S")
        return df, fetched_at
    return None, None


@st.cache_data(ttl=21600)
def fetch_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&hourly=temperature_2m,relative_humidity_2m,"
        "precipitation,precipitation_probability"
        "&forecast_days=2"
        "&timezone=Asia%2FTaipei"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    backoff = 2
    last_status = None

    for _ in range(3):
        response = requests.get(url, headers=headers, timeout=20)
        last_status = response.status_code

        if response.status_code == 429:
            time.sleep(backoff)
            backoff *= 2
            continue

        response.raise_for_status()

        data = response.json()

        df = pd.DataFrame({
            "time": pd.to_datetime(data["hourly"]["time"]),
            "temperature": data["hourly"]["temperature_2m"],
            "humidity": data["hourly"]["relative_humidity_2m"],
            "precipitation": data["hourly"]["precipitation"],
            "precipitation_probability": data["hourly"]["precipitation_probability"]
        })

        taipei_now = pd.Timestamp.now(
            tz="Asia/Taipei"
        ).tz_localize(None)

        df = df[df["time"] >= taipei_now].head(24)

        if df.empty:
            df = pd.DataFrame({
                "time": pd.to_datetime(data["hourly"]["time"]).head(24),
                "temperature": data["hourly"]["temperature_2m"][:24],
                "humidity": data["hourly"]["relative_humidity_2m"][:24],
                "precipitation": data["hourly"]["precipitation"][:24],
                "precipitation_probability": data["hourly"]["precipitation_probability"][:24]
            })

        fetched_at = datetime.now(
            ZoneInfo("Asia/Taipei")
        ).strftime("%Y-%m-%d %H:%M:%S")

        save_cache(df, lat, lon)
        return df, fetched_at, "live"

    cached_df, cached_time = load_cache(lat, lon)
    if cached_df is not None and not cached_df.empty:
        return cached_df, cached_time, "cache"

    demo_df = build_demo_data()
    demo_time = datetime.now(
        ZoneInfo("Asia/Taipei")
    ).strftime("%Y-%m-%d %H:%M:%S")
    return demo_df, demo_time, "demo"


try:
    df, fetched_at, source = fetch_weather(lat, lon)

    if df.empty:
        st.warning("No weather data available.")
        st.stop()

    current_temp = df.iloc[0]["temperature"]
    current_humidity = df.iloc[0]["humidity"]
    current_rain_prob = df.iloc[0]["precipitation_probability"]

    st.sidebar.write("Last Updated:", fetched_at)
    st.sidebar.write("Data Mode:", source.upper())

    if source == "demo":
        st.warning("Live API is temporarily unavailable. Showing demo data.")
    elif source == "cache":
        st.info("Live API is rate-limited right now. Showing cached data.")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("City", city)

    with col2:
        st.metric("Temperature", f"{current_temp:.1f} °C")

    with col3:
        st.metric("Humidity", f"{current_humidity:.0f} %")

    with col4:
        st.metric("Rain Probability", f"{current_rain_prob:.0f} %")

    st.write(f"Data source: Open-Meteo API for {city}")

    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        fig_temp = px.line(
            df,
            x="time",
            y="temperature",
            markers=True,
            title=f"{city} Temperature Forecast (Next 24 Hours)"
        )
        fig_temp.update_layout(
            xaxis_title="Time",
            yaxis_title="Temperature (°C)"
        )
        st.plotly_chart(fig_temp, use_container_width=True)

    with row1_col2:
        fig_humidity = px.line(
            df,
            x="time",
            y="humidity",
            markers=True,
            title=f"{city} Humidity Forecast (Next 24 Hours)"
        )
        fig_humidity.update_layout(
            xaxis_title="Time",
            yaxis_title="Humidity (%)"
        )
        st.plotly_chart(fig_humidity, use_container_width=True)

    st.markdown("---")

    fig_rain = px.bar(
        df,
        x="time",
        y="precipitation",
        title=f"{city} Rainfall Forecast (Next 24 Hours)"
    )
    fig_rain.update_layout(
        xaxis_title="Time",
        yaxis_title="Rainfall (mm)"
    )
    st.plotly_chart(fig_rain, use_container_width=True)

    total_rain = df["precipitation"].sum()

    st.metric(
        "Expected Total Rainfall (Next 24 Hours)",
        f"{total_rain:.1f} mm"
    )

    with st.expander("Show Raw Data"):
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("Weather dashboard failed to load.")
    st.exception(e)

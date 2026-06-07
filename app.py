import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="Taiwan Weather Dashboard",
    page_icon="",
    layout="wide"
)

CITIES = {
    "Taipei": (25.05, 121.52),
    "Taichung": (24.15, 120.67),
    "Kaohsiung": (22.63, 120.30),
    "Hsinchu": (24.81, 120.97)
}

st.title("Taiwan Weather Dashboard")
st.caption("Weather Forecast Dashboard with Data Pipeline")

city = st.sidebar.selectbox(
    "Select City",
    list(CITIES.keys())
)

lat, lon = CITIES[city]


@st.cache_data(ttl=3600)
def fetch_weather(lat, lon):

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&hourly=temperature_2m,relative_humidity_2m"
        "&forecast_days=2"
        "&timezone=Asia%2FTaipei"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "temperature": data["hourly"]["temperature_2m"],
        "humidity": data["hourly"]["relative_humidity_2m"]
    })

    taipei_now = pd.Timestamp.now(
        tz="Asia/Taipei"
    ).tz_localize(None)

    df = df[df["time"] >= taipei_now].head(24)

    return df


try:

    df = fetch_weather(lat, lon)

    current_temp = df.iloc[0]["temperature"]
    current_humidity = df.iloc[0]["humidity"]

    st.sidebar.write(
        "Last Updated:",
        datetime.now(
            ZoneInfo("Asia/Taipei")
        ).strftime("%Y-%m-%d %H:%M:%S")
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("City", city)

    with col2:
        st.metric(
            "Current Temperature",
            f"{current_temp:.1f} °C"
        )

    with col3:
        st.metric(
            "Current Humidity",
            f"{current_humidity:.0f} %"
        )

    st.write(
        f"Data source: Open-Meteo API for {city}"
    )

    left, right = st.columns(2)

    with left:

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

        st.plotly_chart(
            fig_temp,
            use_container_width=True
        )

    with right:

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

        st.plotly_chart(
            fig_humidity,
            use_container_width=True
        )

    with st.expander("Show Raw Data"):
        st.dataframe(
            df,
            use_container_width=True
        )

except Exception as e:
    st.error("Failed to fetch weather data.")
    st.exception(e)

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(
    page_title="Taiwan Weather Dashboard",
    page_icon="🌤️",
    layout="wide"
)

CITIES = {
    "Taipei": (25.05, 121.52),
    "Taichung": (24.15, 120.67),
    "Kaohsiung": (22.63, 120.30),
    "Hsinchu": (24.81, 120.97)
}

st.title("🌤️ Taiwan Weather Dashboard")
st.caption("Weather Dashboard with Data Pipeline and Automatic Updates")

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
        "&hourly=temperature_2m,relative_humidity_2m,"
        "precipitation,precipitation_probability"
        "&forecast_days=2"
        "&timezone=Asia%2FTaipei"
    )

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"]),
        "temperature": data["hourly"]["temperature_2m"],
        "humidity": data["hourly"]["relative_humidity_2m"],
        "precipitation": data["hourly"]["precipitation"],
        "precipitation_probability":
            data["hourly"]["precipitation_probability"]
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
    current_rain_prob = df.iloc[0]["precipitation_probability"]

    st.sidebar.write(
        "Last Updated:",
        datetime.now(
            ZoneInfo("Asia/Taipei")
        ).strftime("%Y-%m-%d %H:%M:%S")
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("City", city)

    with col2:
        st.metric(
            "Temperature",
            f"{current_temp:.1f} °C"
        )

    with col3:
        st.metric(
            "Humidity",
            f"{current_humidity:.0f} %"
        )

    with col4:
        st.metric(
            "Rain Probability",
            f"{current_rain_prob:.0f} %"
        )

    st.write(
        f"Data source: Open-Meteo API for {city}"
    )

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

        st.plotly_chart(
            fig_temp,
            use_container_width=True
        )

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

        st.plotly_chart(
            fig_humidity,
            use_container_width=True
        )

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

    st.plotly_chart(
        fig_rain,
        use_container_width=True
    )

    total_rain = df["precipitation"].sum()

    st.metric(
        "Expected Total Rainfall (Next 24 Hours)",
        f"{total_rain:.1f} mm"
    )

    with st.expander("Show Raw Data"):
        st.dataframe(
            df,
            use_container_width=True
        )

except Exception as e:
    st.error("Failed to fetch weather data.")
    st.exception(e)

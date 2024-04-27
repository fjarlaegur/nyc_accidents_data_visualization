import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sodapy import Socrata


client = Socrata("data.cityofnewyork.us", None)


@st.cache_data(persist=True)
def load_data(nrows: int) -> object:
    """Getting certain number of data rows from the source
    and formatting as necessary."""

    query = f"SELECT * WHERE DATE_EXTRACT_Y(crash_date) = 2023 LIMIT {nrows}"
    get_data = client.get("h9gi-nx95", content_type="json", query=query)
    data = pd.DataFrame(get_data)

    # dropping location because it didn't format correctly
    # and we have no use for it as we have latitude
    # and longitude separately

    data.drop(columns="location", inplace=True)

    # dropping rows with emply lat, long, and street name columns

    data.dropna(subset=["latitude", "longitude", "on_street_name"], inplace=True)

    data["date/time"] = pd.to_datetime(data["crash_date"] + " " + data["crash_time"])
    data.drop(columns=["crash_date", "crash_time"], inplace=True)
    column_order = ["date/time"] + [col for col in data.columns if col != "date/time"]
    data = data[column_order]

    data["latitude"] = pd.to_numeric(data["latitude"])
    data["longitude"] = pd.to_numeric(data["longitude"])
    return data


@st.cache_data(persist=True)
def convert_to_csv(dataframe: object) -> object:
    """Converting the dataframe to .csv to download it later"""
    return dataframe.to_csv().encode("utf-8")


@st.cache_data(persist=True)
def top_five_cases(option):
    if option == "Deadliest crashes":
        data["total_severity"] = pd.to_numeric(
            data["number_of_persons_injured"] +
            data["number_of_persons_killed"]
        )
        newdata = data.sort_values("total_severity", ascending=False).head(5)
        return newdata
    else:
        pass


data = load_data(100_000)
data_for_download = data

st.title("New York City Motor Vehicle Collisions :collision:")

# density heatmap for crash hotspots

st.subheader("Crash Frequency Based on Location")
st.markdown("""This is the :rainbow[heatmap] of New York City, showing amount of motor
            accident activity by street.""")

# calculating crash counts

crash_counts = data.groupby("on_street_name").size().reset_index(name="crash_counts")
data = data.merge(crash_counts, on="on_street_name")

# drawing a heatmap

fig = px.density_mapbox(data, lat='latitude', lon='longitude',
                        z="crash_counts", radius=3,
                        center=dict(lat=40.67812, lon=-73.92165),
                        opacity=0.7,
                        zoom=9, mapbox_style="carto-positron",
                        color_continuous_scale="rainbow",
                        range_color=(0, data["crash_counts"].max()),
                        hover_name="on_street_name", hover_data="crash_counts",
                        width=650, height=600)

fig.add_trace(
    go.Scattermapbox(
        lat=data["latitude"],
        lon=data["longitude"],
        mode="markers",
        showlegend=False,
        hoverinfo="skip",
        marker={
            "color": data["crash_counts"],
            "size": data["crash_counts"].fillna(0),
            "coloraxis": "coloraxis",
            "sizeref": (data["crash_counts"].max()) / 15 ** 2,
            "sizemode": "area",
        },
    )
)
st.write(fig)


#  creating top-5 cases
st.subheader("Top-5 of the most extreme cases. I want to see:")
option = st.selectbox(
    "Top-5",
    index=None,
    options=[
        "Deadliest crashes",
        "Contibuting factors",
        "Most dangerous streets"
    ],
    label_visibility="collapsed"
)

st.write(top_five_cases(option))

if st.checkbox("Show Raw Data", False):
    st.subheader("Raw Data")
    st.write(data)

    csv = convert_to_csv(data_for_download)
    st.download_button(
        "Download data as .csv",
        data=csv,
        file_name="NYC_Motor_Vehicle_Collisions_2023.csv",
        mime="text/csv",
    )
    st.caption("""Warning! This file is quite large and
               may cause slowness/freezes of your editor.""")
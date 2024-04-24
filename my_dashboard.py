import streamlit as st
import pandas as pd
import plotly.express as px
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

    # dropping rows with emply lat long columns

    data.dropna(subset=["latitude", "longitude", "on_street_name"], inplace=True)

    data["date/time"] = pd.to_datetime(data["crash_date"] + " " + data["crash_time"])
    data.drop(columns=["crash_date", "crash_time"], inplace=True)
    column_order = ["date/time"] + [col for col in data.columns if col != "date/time"]
    data = data[column_order]

    data["latitude"] = pd.to_numeric(data["latitude"])
    data["longitude"] = pd.to_numeric(data["longitude"])
    return data


data = load_data(100_000)

st.title("New York City Motor Vehicle Collisions :collision:")

# density heatmap for crash hotspots
# calculating crash counts

crash_counts = data.groupby("on_street_name").size().reset_index(name="crash_counts")
data = data.merge(crash_counts, on="on_street_name")

fig = px.density_mapbox(data, lat='latitude', lon='longitude', z="crash_counts", radius=10,
                        center=dict(lat=data['latitude'].mean(), lon=data['longitude'].mean()),
                        zoom=10, mapbox_style="carto-darkmatter", opacity=0.5,
                        hover_name="on_street_name", hover_data="crash_counts",
                        title='Crash Hotspots Density Heatmap')
st.write(fig)


if st.checkbox("Show Raw Data", False):
    st.subheader("Raw Data")
    st.write(data)

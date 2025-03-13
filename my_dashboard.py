import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sodapy import Socrata


client = Socrata("data.cityofnewyork.us", None)


@st.cache_data(persist=True)
def load_data(nrows: int) -> pd.DataFrame:
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
def convert_to_csv(dataframe: pd.DataFrame) -> str:
    """Converting the dataframe to .csv to download it later"""
    return dataframe.to_csv().encode("utf-8")


def show_raw_data() -> None:
    st.subheader("📎Raw Data")
    st.write(data)

    csv = convert_to_csv(data_for_download)
    st.download_button(
        "Download data as .csv",
        data=csv,
        file_name="NYC_Motor_Vehicle_Collisions_2023.csv",
        mime="text/csv",
    )
    st.caption("""Warning! This file is quite large and
               may cause slowness/freezing of your editor.""")


@st.cache_data(persist=True)
def top_five_cases(option: str) -> pd.DataFrame:
    match option:
        case "Deadliest crashes":
            data["total_severity"] = pd.to_numeric(
                data["number_of_persons_injured"]
            ) + pd.to_numeric(
                data["number_of_persons_killed"]
            )
            newdata = data.sort_values("total_severity", ascending=False)
            newdata = newdata.head(5)

        case "Contributing factors":
            # removing "unspecified" value
            specified = data[data.contributing_factor_vehicle_1 != "Unspecified"]
            newdata = specified["contributing_factor_vehicle_1"].value_counts()
            newdata = newdata.reset_index(name="count")

        case "Most dangerous streets":
            newdata = data["on_street_name"].value_counts().head(5)
            newdata = newdata.reset_index(name="count")
            newdata = newdata.merge(data[["on_street_name",
                                          "latitude",
                                          "longitude"]],
                                    how="left", on="on_street_name")

        case _:
            newdata = "Nothing to show yet."

    return newdata


data = load_data(100_000)
data_for_download = data

st.title("New York City Motor Vehicle Collisions :collision:")

# density heatmap for crash hotspots

st.subheader("📍 Crash Frequency Based on Location")
st.markdown("""This is a :rainbow[heatmap] of New York City, showing the
            amount of motor accident activity by street.""")

# calculating crash counts

crash_counts = data.groupby("on_street_name").size()
crash_counts = crash_counts.reset_index(name="crash_counts")
data = data.merge(crash_counts, on="on_street_name")

# drawing a heatmap

fig = px.density_mapbox(data, lat='latitude', lon='longitude',
                        z="crash_counts", radius=3,
                        center=dict(lat=40.68679, lon=-73.92165),
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
st.subheader("📃 Top-5 of the most extreme cases")
st.markdown("#### I want to see:")
option = st.selectbox(
    "Top-5",
    index=None,
    options=[
        "Deadliest crashes",
        "Contributing factors",
        "Most dangerous streets"
    ],
    label_visibility="collapsed"
)

result = top_five_cases(option)

match option:
    case "Deadliest crashes":
        fig = px.bar(result, x="on_street_name", y="total_severity")
        st.write(fig)
    case "Contributing factors":
        result.loc[result["count"] < 2_658,
                   "contributing_factor_vehicle_1"] = "Other factors"
        fig = px.pie(result, values="count",
                     names="contributing_factor_vehicle_1")
        st.write(fig)
    case "Most dangerous streets":
        fig = px.scatter_mapbox(result, lat="latitude",
                             lon="longitude", hover_name="on_street_name",
                             center=dict(lat=40.7300, lon=-73.9340),
                             color="on_street_name", size="count", zoom=9,
                             width=600, height=600)
        fig.update_layout(mapbox_style="open-street-map")
        st.write(fig)
    case _:
        st.write(result)


if st.checkbox("Show Raw Data", False):
    show_raw_data()

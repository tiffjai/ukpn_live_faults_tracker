import requests
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
from geopy.geocoders import Nominatim

# UK Power Networks Live Faults API Endpoint
API_URL = "https://ukpowernetworks.opendatasoft.com/api/records/1.0/search/?dataset=ukpn-live-faults&q=&rows=20"

def fetch_live_faults():
    """
    Fetch live faults data from the UKPN API,
    convert it into a DataFrame, and return the DataFrame.
    """
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()
        records = data["records"]
        df = pd.json_normalize(records, sep="_")

        # Select and rename the relevant columns
        df = df[["fields.postcode", "fields.fault_status", "fields.start_time", "fields.reason"]]
        df.columns = ["Postcode", "Status", "Start Time", "Reason"]
        return df
    else:
        print("Error fetching data:", response.status_code)
        return pd.DataFrame(columns=["Postcode", "Status", "Start Time", "Reason"])

# Initialize the Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div([
    html.H1("UKPN Live Faults Tracker"),

    # Dropdown filter for fault status
    dcc.Dropdown(
        id="status-filter",
        options=[
            {"label": "All", "value": "All"},
            {"label": "Planned", "value": "Planned"},
            {"label": "Unplanned", "value": "Unplanned"}
        ],
        value="All",
        clearable=False,
        style={"width": "50%"}
    ),

    # Div to hold the data table
    html.Div(id="faults-table", style={"padding": "20px 0"}),

    # Graph for the map visualization
    dcc.Graph(id="faults-map")
])

# Callback to update the table and map based on the selected status
@app.callback(
    [Output("faults-table", "children"),
     Output("faults-map", "figure")],
    [Input("status-filter", "value")]
)
def update_dashboard(selected_status):
    # Fetch the latest data
    df = fetch_live_faults()

    # Filter data if a specific status is selected
    if selected_status != "All":
        df = df[df["Status"] == selected_status]

    # Convert postcodes to latitude and longitude using geopy
    geolocator = Nominatim(user_agent="ukpn_tracker")
    # To avoid multiple calls for the same postcode, you might consider caching in a real-world app.
    def get_lat(postcode):
        location = geolocator.geocode(postcode)
        return location.latitude if location else None

    def get_lon(postcode):
        location = geolocator.geocode(postcode)
        return location.longitude if location else None

    df["Latitude"] = df["Postcode"].apply(get_lat)
    df["Longitude"] = df["Postcode"].apply(get_lon)

    # Create a simple HTML table for display
    table_header = [
        html.Thead(html.Tr([html.Th(col) for col in df.columns]))
    ]
    table_body = [html.Tr([html.Td(df.iloc[i][col]) for col in df.columns])
                  for i in range(len(df))]
    table = html.Table(table_header + [html.Tbody(table_body)],
                       style={'width': '100%', 'border': '1px solid black', 'border-collapse': 'collapse'})

    # Create the map visualization using Plotly Express
    fig = px.scatter_mapbox(
        df,
        lat="Latitude",
        lon="Longitude",
        text="Postcode",
        color="Status",
        hover_data=["Reason", "Start Time"],
        zoom=6,
        height=500
    )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return table, fig

if __name__ == "__main__":
    app.run_server(debug=True)

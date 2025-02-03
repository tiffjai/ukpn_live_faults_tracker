import requests
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
from geopy.geocoders import Nominatim

# Set up the geolocator with a timeout and caching
geolocator = Nominatim(user_agent="ukpn_tracker", timeout=10)
geocode_cache = {}

def geocode_postcode(postcode):
    """
    Convert postcode to latitude and longitude. Caches results to reduce API calls.
    """
    if not postcode:
        return None, None
    if postcode in geocode_cache:
        return geocode_cache[postcode]
    
    try:
        location = geolocator.geocode(postcode + ", UK")
        if location:
            geocode_cache[postcode] = (location.latitude, location.longitude)
            return location.latitude, location.longitude
    except Exception as e:
        print(f"Error geocoding {postcode}: {e}")
    
    geocode_cache[postcode] = (None, None)
    return None, None

def extract_primary_postcode(value):
    """
    Extracts the first postcode if multiple exist.
    """
    if isinstance(value, list) and value:
        return value[0]
    elif isinstance(value, str):
        return value.split(';')[0].strip()
    return None

def fetch_live_faults():
    """
    Fetches live power fault data from UKPN API and processes it into a DataFrame.
    """
    API_URL = "https://ukpowernetworks.opendatasoft.com/api/records/1.0/search/?dataset=ukpn-live-faults&q=&rows=20"
    response = requests.get(API_URL)
    
    if response.status_code != 200:
        print("Error fetching data:", response.status_code)
        return pd.DataFrame(columns=["Postcode", "Status", "Start Time", "Reason"])
    
    data = response.json()
    records = data.get("records", [])
    
    if not records:
        print("No records found in API response.")
        return pd.DataFrame()

    df = pd.json_normalize(records, sep="_")
    
    expected_cols = [
        "fields_postcodesaffected", "fields_incidenttypename", 
        "fields_creationdatetime", "fields_mainmessage"
    ]
    
    if not all(col in df.columns for col in expected_cols):
        print("Missing expected columns:", set(expected_cols) - set(df.columns))
        return pd.DataFrame()

    df["Postcode"] = df["fields_postcodesaffected"].apply(extract_primary_postcode)
    df = df.rename(columns={
        "fields_incidenttypename": "Status",
        "fields_creationdatetime": "Start Time",
        "fields_mainmessage": "Reason"
    })[["Postcode", "Status", "Start Time", "Reason"]]

    return df

# Initialize the Dash app
app = dash.Dash(__name__)

# Mapbox token (keep this unchanged)
mapbox_access_token = "pk.eyJ1IjoidGlmZmphaSIsImEiOiJjbTRpaDJ6dmIwMmQwMmxzaHltYnZ0amNyIn0.kVmcyJR_sONlNW7F32HG4g"

# Define the layout of the app
app.layout = html.Div([
    html.H1("UKPN Live Faults Tracker"),
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
    html.Div(id="faults-table", style={"padding": "20px 0"}),
    dcc.Graph(id="faults-map")
])

# Callback to update both the table and map whenever the dropdown value changes
@app.callback(
    [Output("faults-table", "children"), Output("faults-map", "figure")],
    [Input("status-filter", "value")]
)
def update_dashboard(selected_status):
    df = fetch_live_faults()
    
    if df.empty:
        return html.Div("No data available."), {}

    if selected_status != "All":
        df = df[df["Status"] == selected_status]

    # Apply geocoding for missing lat/lon
    df[["Latitude", "Longitude"]] = df["Postcode"].apply(lambda pc: pd.Series(geocode_postcode(pc)))
    df.dropna(subset=["Latitude", "Longitude"], inplace=True)

    # Create an HTML table
    table = html.Table([
        html.Thead(html.Tr([html.Th(col) for col in df.columns])),
        html.Tbody([html.Tr([html.Td(df.iloc[i][col]) for col in df.columns]) for i in range(len(df))])
    ], style={'width': '100%', 'border': '1px solid black', 'border-collapse': 'collapse'})

    # Create a map visualization using Plotly Express
    fig = px.scatter_mapbox(
        df, lat="Latitude", lon="Longitude", text="Postcode",
        color="Status", hover_data=["Reason", "Start Time"],
        zoom=6, height=500
    )

    fig.update_layout(
        mapbox=dict(
            accesstoken=mapbox_access_token,
            style="streets"
        ) if mapbox_access_token else dict(style="open-street-map"),
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    return table, fig

# Expose Flask server for Gunicorn
server = app.server  

# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True)

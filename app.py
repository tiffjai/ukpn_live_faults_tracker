import requests
import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
from geopy.geocoders import Nominatim

# Set up the geolocator with an increased timeout (10 seconds)
geolocator = Nominatim(user_agent="ukpn_tracker", timeout=10)
# Cache for geocoding results to minimize duplicate requests
geocode_cache = {}

def geocode_postcode(postcode):
    """
    Geocode a postcode, appending ", UK" to enforce UK location,
    and cache the result to reduce duplicate API calls.
    """
    if not postcode:
        return None
    if postcode in geocode_cache:
        return geocode_cache[postcode]
    try:
        # Append ", UK" to the postcode to ensure geocoding is done in the UK
        location = geolocator.geocode(postcode + ", UK")
        geocode_cache[postcode] = location
        return location
    except Exception as e:
        print(f"Error geocoding {postcode}: {e}")
        geocode_cache[postcode] = None
        return None

def extract_primary_postcode(value):
    """
    Extract the primary postcode from the given value.
    If it's a list, return the first element.
    If it's a string containing multiple postcodes (separated by semicolons), return the first.
    """
    if isinstance(value, list) and len(value) > 0:
        return value[0]
    elif isinstance(value, str):
        return value.split(';')[0].strip()
    return value

def fetch_live_faults():
    """
    Fetch the live fault data from the UKPN API,
    normalize the JSON into a pandas DataFrame,
    and extract the relevant fields.
    """
    API_URL = "https://ukpowernetworks.opendatasoft.com/api/records/1.0/search/?dataset=ukpn-live-faults&q=&rows=20"
    response = requests.get(API_URL)
    if response.status_code == 200:
        data = response.json()
        records = data.get("records", [])
        if not records:
            print("No records found in the API response.")
            return pd.DataFrame()
        # Normalize the JSON data into a DataFrame
        df = pd.json_normalize(records, sep="_")
        print("DataFrame columns:", df.columns.tolist())
        
        # We expect the following columns based on the API:
        expected_cols = [
            "fields_postcodesaffected",
            "fields_incidenttypename",
            "fields_creationdatetime",
            "fields_mainmessage"
        ]
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            print("Missing columns:", missing_cols)
            print(df.head())
            return pd.DataFrame()
        
        # Create a new "Postcode" column by extracting the primary postcode
        df["Postcode"] = df["fields_postcodesaffected"].apply(extract_primary_postcode)
        # Rename other columns for clarity
        df = df.rename(columns={
            "fields_incidenttypename": "Status",
            "fields_creationdatetime": "Start Time",
            "fields_mainmessage": "Reason"
        })
        # Keep only the columns we need
        df = df[["Postcode", "Status", "Start Time", "Reason"]]
        return df
    else:
        print("Error fetching data:", response.status_code)
        return pd.DataFrame(columns=["Postcode", "Status", "Start Time", "Reason"])

# Initialize the Dash app
app = dash.Dash(__name__)

# Optionally, if you have a Mapbox access token, set it here.
# If you don't, the code will fall back to OpenStreetMap tiles.
mapbox_access_token = "pk.eyJ1IjoidGlmZmphaSIsImEiOiJjbTRpaDJ6dmIwMmQwMmxzaHltYnZ0amNyIn0.kVmcyJR_sONlNW7F32HG4g"  # Replace with your token or leave as is.

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
    [Output("faults-table", "children"),
     Output("faults-map", "figure")],
    [Input("status-filter", "value")]
)
def update_dashboard(selected_status):
    # Fetch the latest data
    df = fetch_live_faults()
    if df.empty:
        return html.Div("No data available."), {}

    # Filter data by status if a specific type is selected
    if selected_status != "All":
        df = df[df["Status"] == selected_status]

    # Define helper functions to get latitude and longitude using geocoding
    def get_lat(postcode):
        location = geocode_postcode(postcode)
        return location.latitude if location else None

    def get_lon(postcode):
        location = geocode_postcode(postcode)
        return location.longitude if location else None

    # Apply the geocoding functions to get coordinates
    df["Latitude"] = df["Postcode"].apply(get_lat)
    df["Longitude"] = df["Postcode"].apply(get_lon)

    # Create an HTML table from the DataFrame
    table_header = [html.Thead(html.Tr([html.Th(col) for col in df.columns]))]
    table_body = [
        html.Tr([html.Td(df.iloc[i][col]) for col in df.columns])
        for i in range(len(df))
    ]
    table = html.Table(
        table_header + [html.Tbody(table_body)],
        style={'width': '100%', 'border': '1px solid black', 'border-collapse': 'collapse'}
    )

    # Create a map visualization using Plotly Express
    if mapbox_access_token and mapbox_access_token != "YOUR_MAPBOX_TOKEN_HERE":
        # Use Mapbox style if a valid token is provided
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
        fig.update_layout(
            mapbox=dict(
                accesstoken=mapbox_access_token,
                style="streets"  # Use the "streets" style (labels should be in English)
            ),
            margin={"r": 0, "t": 0, "l": 0, "b": 0}
        )
    else:
        # Fallback to OpenStreetMap if no Mapbox token is provided
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
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

    return table, fig

# Initialize the Dash app
app = dash.Dash(__name__)

# Expose the WSGI server variable for Gunicorn
server = app.server  # Gunicorn needs this

# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True)


# UKPN Live Faults Tracker

This application is a web-based dashboard for tracking live faults reported by the UK Power Networks (UKPN). It provides a visual representation of the faults on a map and a detailed table view of the incidents.

## Features

- **Geocoding**: Uses the Geopy library to convert postcodes into geographic coordinates.
- **Data Fetching**: Retrieves live fault data from the UKPN API and processes it into a structured format using Pandas.
- **Interactive Dashboard**: Built with Dash, allowing users to filter faults by status and view them on a map.
- **Map Visualization**: Utilizes Plotly Express for rendering a map with fault locations, using either Mapbox or OpenStreetMap tiles.

## Installation

1. Clone the repository.
2. Install the required dependencies using `pip install -r requirements.txt`.
3. Run the application with `python app.py`.

## Usage

- Open the application in a web browser.
- Use the dropdown menu to filter faults by status (All, Planned, Unplanned).
- View the faults on the map and in the table.

## Dependencies

- `requests`
- `pandas`
- `dash`
- `plotly`
- `geopy`

## Configuration

- Optionally, set a Mapbox access token in the `app.py` file for enhanced map styling.

## License

This project is licensed under the MIT License.

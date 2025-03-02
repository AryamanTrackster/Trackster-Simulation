import json

def load_stations(file_path="stations.json"):
    """Load station data from a JSON file."""
    try:
        with open(file_path, "r") as file:
            stations = json.load(file)
        return stations
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Make sure the file exists.")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not parse {file_path}. Ensure it contains valid JSON.")
        return []

def display_stations(stations):
    """Print station details in a formatted way."""
    if not stations:
        print("No stations available.")
        return

    print("\nList of Stations:")
    print("=" * 50)
    for station in stations:
        print(f"{station['name']} ({station['district']}, {station['state']})")
        print(f"  - Capacity: {station['capacity']} units")
        print(f"  - Distance: {station['distance_from_start']} km\n")

# Main execution
if __name__ == "__main__":
    stations = load_stations()
    display_stations(stations)

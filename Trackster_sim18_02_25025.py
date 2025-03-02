import random
import time
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Load stations from JSON file
def load_stations(file_path="stations.json"):
    with open(file_path, "r") as file:
        stations = json.load(file)
    return stations

# Initialize the stations
stations = load_stations()

# Initialize Pragati units
pragati_units = []
unit_id = 1
for station in stations:
    for slot in range(1, 11):
        unit = {
            "id": f"PGT-{unit_id:03d}",
            "position": station["distance_from_start"],
            "speed": 0,
            "max_speed": 100,
            "acceleration": 2,
            "deceleration": 3,
            "direction": None,
            "status": "anchored",
            "destination": None,
            "anchoring_slot": slot,
            "start_station": station["name"],
        }
        pragati_units.append(unit)
        unit_id += 1

# Request and movement logic
def generate_request():
    origin = random.choice(stations)
    destination = random.choice([s for s in stations if s["name"] != origin["name"]])
    return {"origin": origin["name"], "destination": destination["name"]}

def assign_request(request):
    available_units = [unit for unit in pragati_units if unit["status"] == "anchored" and unit["start_station"] == request["origin"]]
    if not available_units:
        return False
    
    unit = available_units[0]
    unit.update({
        "status": "moving",
        "destination": request["destination"],
        "direction": "up" if next(s["distance_from_start"] for s in stations if s["name"] == request["destination"]) > unit["position"] else "down",
    })
    return True

def move_units():
    for unit in pragati_units:
        for unit in [u for u in pragati_units if u["status"] == "moving"]:

            target_distance = next(s["distance_from_start"] for s in stations if s["name"] == unit["destination"])
            
            if unit["direction"] == "up":
                unit["speed"] = min(unit["speed"] + unit["acceleration"], unit["max_speed"])
                unit["position"] = min(unit["position"] + unit["speed"] / 3600, target_distance)
            else:
                unit["speed"] = max(unit["speed"] - unit["deceleration"], 0)
                unit["position"] = max(unit["position"] - unit["speed"] / 3600, target_distance)
                
            if unit["position"] == target_distance:
                unit["status"] = "anchored"
                unit["speed"] = 0

# Visualization Setup
fig, ax = plt.subplots()
ax.set_xlim(0, max(s["distance_from_start"] for s in stations) + 10)
ax.set_ylim(0, len(pragati_units) + 1)
ax.set_xlabel("Distance (km)")
ax.set_ylabel("Unit ID")
points = ax.scatter([], [], c=[], cmap="coolwarm", edgecolors="k", s=100)

def update_plot(frame):
    if random.random() < 0.3:
        request = generate_request()
        assign_request(request)
    move_units()
    x_data = [unit["position"] for unit in pragati_units]
    y_data = list(range(1, len(pragati_units) + 1))
    colors = [0 if unit["status"] == "anchored" else 1 for unit in pragati_units]  
    points.set_offsets(list(zip(x_data, y_data)))
    points.set_array(colors)
    return points,

def display_unit_data():
    while True:
        print("\nCurrent Pragati Unit Status:")
        for unit in pragati_units:
            print(f"{unit['id']} | Speed: {unit['speed']} km/h | Position: {unit['position']} km | Start: {unit['start_station']} | Destination: {unit['destination']} | Status: {unit['status']}")
        time.sleep(1)

import threading
threading.Thread(target=display_unit_data, daemon=True).start()

ani = animation.FuncAnimation(fig, update_plot, frames=100, interval=1000, blit=False)
plt.show()

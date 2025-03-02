import tkinter as tk
from tkinter import ttk
import time
import random
import threading
import json
import math
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ====== LOAD STATION DATA FROM JSON ======
with open("C:/Users/aryam/OneDrive/Desktop/New folder/Website/htdocs/wordpress/Trackster/Trackster Simulation/Trackster/stations.json", "r") as f:
    station_data = json.load(f)

"""
We will store each station's distance in meters internally.
Also, each station's capacity determines how many anchoring slots are available.
"""
stations = {}
for s in station_data:
    station_name = s["name"]
    distance_meters = s["distance_from_start"] * 1000  # convert km -> m
    capacity = s["capacity"]
    stations[station_name] = {
        "distance_m": distance_meters,
        "anchoring_slots": {i: None for i in range(1, capacity + 1)},
    }

# ====== INITIALIZE PRAGATI UNITS ======
"""
We'll create one Pragati unit per anchoring slot in each station.
Each unit will:
- Start "anchored" at station's distance.
- Speed in m/s (speed_mps).
- Direction is "up" or "down" (used when we move).
- We store position in meters (position_m).
"""

pragati_units = []
unit_id = 1

for station_name, station_info in stations.items():
    capacity = len(station_info["anchoring_slots"])
    for slot in range(1, capacity + 1):
        unit = {
            "id": f"PGT-{unit_id:03d}",
            "position_m": station_info["distance_m"],   # start at station in meters
            "speed_mps": 0.0,                           # speed in m/s
            "direction": None,                          # 'up' or 'down'
            "status": "anchored",
            "destination": None,
            "anchoring_slot": slot,
        }
        pragati_units.append(unit)
        station_info["anchoring_slots"][slot] = unit
        unit_id += 1

# ====== SETUP GUI WINDOW ======
root = tk.Tk()
root.title("Pragati Unit Status")

# Treeview table for displaying Pragati units
table = ttk.Treeview(
    root,
    columns=("ID", "Position", "Speed", "Status", "Destination"),
    show="headings",
)
for col in ("ID", "Position", "Speed", "Status", "Destination"):
    table.heading(col, text=col)
    table.column(col, width=100)
table.pack(fill=tk.BOTH, expand=True)

def update_gui():
    """
    Update the GUI table with current data from pragati_units.
    Speed is displayed in km/h, position in km.
    """
    table.delete(*table.get_children())
    for unit in pragati_units:
        # Convert position (m) to km for display
        position_km = unit["position_m"] / 1000.0
        # Convert speed (m/s) to km/h
        speed_kmh = unit["speed_mps"] * 3.6
        table.insert("", "end", values=(
            unit["id"],
            f"{position_km:.1f} km",
            f"{speed_kmh:.1f} km/h",
            unit["status"],
            unit["destination"] if unit["destination"] else "",
        ))
    root.after(1000, update_gui)

root.after(1000, update_gui)  # Start periodic GUI updates

# ====== SIMULATION LOGIC ======

def assign_destinations():
    """
    Randomly assigns a destination to some anchored units.
    Destination is any station except the one they're currently at.
    """
    for unit in pragati_units:
        if unit["status"] == "anchored" and random.random() < 0.3:
            # Find the station whose distance matches this unit's position
            current_station = None
            for st_name, st_info in stations.items():
                if abs(st_info["distance_m"] - unit["position_m"]) < 1e-3:
                    current_station = st_name
                    break
            
            # Pick a random different station
            possible_stations = [s for s in stations.keys() if s != current_station]
            if not possible_stations:
                continue  # No alternative station, skip

            dest_station = random.choice(possible_stations)
            unit["destination"] = dest_station
            if stations[dest_station]["distance_m"] > unit["position_m"]:
                unit["direction"] = "up"
            else:
                unit["direction"] = "down"
            unit["status"] = "moving"

def move_units():
    """
    Move units toward their assigned destination with realistic acceleration/deceleration.
    - Maximum acceleration/deceleration = 1 m/s^2.
    - Speed is capped to 100 km/h (≈ 27.78 m/s).
    - Distance is updated with (speed * dt).
    """
    dt = 1.0  # each loop iteration represents 1 second
    max_acc = 1.0  # m/s^2
    max_speed_mps = 27.78  # 100 km/h in m/s

    for unit in pragati_units:
        if unit["status"] == "moving" and unit["destination"] is not None:
            target_distance_m = stations[unit["destination"]]["distance_m"]
            
            # Decide whether we need to go "up" or "down" in position
            moving_up = (unit["direction"] == "up")

            # 1) Calculate random acceleration within ±1 m/s²
            #    We'll bias the sign so it tends to move in the correct direction.
            #    If we're "up", we pick from [0, +1], if "down", we pick from [-1, 0].
            if moving_up:
                acceleration = random.uniform(0, max_acc)
            else:
                acceleration = random.uniform(-max_acc, 0)

            # 2) Update speed (m/s) based on acceleration
            new_speed = unit["speed_mps"] + acceleration * dt

            # Ensure speed is non-negative and below max
            if new_speed < 0:
                new_speed = 0
            if new_speed > max_speed_mps:
                new_speed = max_speed_mps

            # 3) Update the unit's position
            old_position = unit["position_m"]
            if moving_up:
                unit["position_m"] = old_position + new_speed * dt
                # Make sure we don't overshoot
                if unit["position_m"] > target_distance_m:
                    unit["position_m"] = target_distance_m
            else:
                unit["position_m"] = old_position - new_speed * dt
                if unit["position_m"] < target_distance_m:
                    unit["position_m"] = target_distance_m

            unit["speed_mps"] = new_speed

            # 4) Check if we've reached the destination
            if abs(unit["position_m"] - target_distance_m) < 0.5:
                # Snap to destination
                unit["position_m"] = target_distance_m
                unit["speed_mps"] = 0.0
                unit["status"] = "anchored"
                unit["direction"] = None
                unit["destination"] = None

def simulation_loop():
    """
    Background simulation loop that repeatedly:
    1. Assigns new destinations to anchored units (some probability).
    2. Moves units with realistic acceleration.
    """
    while True:
        assign_destinations()
        move_units()
        time.sleep(1)

# ====== EMBEDDING MATPLOTLIB IN TKINTER ======
max_distance_m = max(st["distance_m"] for st in stations.values())
num_units = len(pragati_units)

fig, ax = plt.subplots()
ax.set_xlim(0, max_distance_m * 1.05)  # Extend x-axis a bit
ax.set_ylim(0, num_units + 1)
ax.set_xlabel("Distance (m)")
ax.set_ylabel("Pragati Unit ID")
ax.set_title("Live Pragati Unit Movement (Acceleration = ±1 m/s²)")

scatter = ax.scatter([], [])

def update_plot(frame):
    """
    Updates the scatter plot with positions of units that are 'moving'.
    We'll map the ID to the y-axis and the position (in meters) to the x-axis.
    """
    positions = []
    ids = []
    for unit in pragati_units:
        if unit["status"] == "moving":
            positions.append(unit["position_m"])
            # Convert "PGT-001" -> integer 1 for plotting
            numeric_id = int(unit["id"].split("-")[1])
            ids.append(numeric_id)
    if positions and ids:
        scatter.set_offsets(list(zip(positions, ids)))
    else:
        scatter.set_offsets([])
    return scatter,

ani = animation.FuncAnimation(
    fig, update_plot, interval=1000, blit=False, cache_frame_data=False
)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# Start simulation in a background thread
threading.Thread(target=simulation_loop, daemon=True).start()

# Run GUI mainloop
root.mainloop()

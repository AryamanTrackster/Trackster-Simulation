import tkinter as tk
from tkinter import ttk
import time
import random
import threading
import json
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ====== LOAD STATION DATA FROM JSON ======
with open("C:/Users/aryam/OneDrive/Desktop/New folder/Website/htdocs/wordpress/Trackster/Trackster Simulation/Trackster/stations.json", "r") as f:
    station_data = json.load(f)

# Build a stations dictionary where each key is the station name
stations = {}
for s in station_data:
    stations[s["name"]] = {
        "distance": s["distance_from_start"],
        "anchoring_slots": {i: None for i in range(1, s["capacity"] + 1)}
    }

# ====== INITIALIZE PRAGATI UNITS ======
pragati_units = []
unit_id = 1
for station_name, station_info in stations.items():
    for slot in range(1, s["capacity"] + 1) if False else range(1, len(station_info["anchoring_slots"]) + 1):
        # Using station_info["anchoring_slots"] length which equals station capacity.
        unit = {
            "id": f"PGT-{unit_id:03d}",
            "position": station_info["distance"],
            "speed": 0,
            "direction": None,
            "status": "anchored",
            "destination": None,
            "anchoring_slot": slot,
        }
        pragati_units.append(unit)
        station_info["anchoring_slots"][slot] = unit
        unit_id += 1

# ====== GUI WINDOW SETUP ======
root = tk.Tk()
root.title("Pragati Unit Status")

# Table for displaying Pragati units
table = ttk.Treeview(root, columns=("ID", "Position", "Speed", "Status", "Destination"), show="headings")
for col in ("ID", "Position", "Speed", "Status", "Destination"):
    table.heading(col, text=col)
    table.column(col, width=100)
table.pack(fill=tk.BOTH, expand=True)

def update_gui():
    """Update the GUI table with current Pragati units data."""
    table.delete(*table.get_children())
    for unit in pragati_units:
        table.insert("", "end", values=(
            unit["id"],
            f"{unit['position']:.1f} km",
            f"{unit['speed']:.1f} km/h",
            unit["status"],
            unit["destination"]
        ))
    root.after(1000, update_gui)

root.after(1000, update_gui)  # Start GUI updates

# ====== SIMULATION LOGIC ======
def assign_destinations():
    """
    Randomly assigns a destination (different from the current station) to anchored units.
    """
    for unit in pragati_units:
        if unit["status"] == "anchored" and random.random() < 0.3:
            # Find current station by matching the unit's position with station distances
            current_station = None
            for s_name, s_info in stations.items():
                if abs(s_info["distance"] - unit["position"]) < 1e-6:
                    current_station = s_name
                    break
            # Exclude the current station from possible destinations
            possible_destinations = [s for s in stations.keys() if s != current_station]
            if possible_destinations:
                dest = random.choice(possible_destinations)
                unit["destination"] = dest
                unit["direction"] = "up" if stations[dest]["distance"] > unit["position"] else "down"
                unit["status"] = "moving"

def move_units():
    """
    Moves units towards their destination, updating position and speed.
    """
    for unit in pragati_units:
        if unit["status"] == "moving":
            step = random.uniform(0.5, 1.5)  # simulate acceleration/deceleration
            unit["speed"] = min(step * 60, 100)  # cap speed at 100 km/h
            target_distance = stations[unit["destination"]]["distance"]
            
            if unit["direction"] == "up":
                unit["position"] = min(unit["position"] + step, target_distance)
            else:
                unit["position"] = max(unit["position"] - step, target_distance)
            
            # Stop the unit if it has reached the destination (with a tolerance)
            if abs(unit["position"] - target_distance) < 0.5:
                unit["status"] = "anchored"
                unit["speed"] = 0
                unit["direction"] = None
                unit["destination"] = None

def simulation_loop():
    """Run the simulation in a background thread."""
    while True:
        assign_destinations()
        move_units()
        time.sleep(1)

# ====== EMBEDDING MATPLOTLIB IN TKINTER ======
max_distance = max(s["distance"] for s in stations.values())
fig, ax = plt.subplots()
ax.set_xlim(0, max_distance + 50)  # Extend x-axis based on the farthest station
ax.set_ylim(0, len(pragati_units) + 1)
ax.set_xlabel("Distance (km)")
ax.set_ylabel("Pragati Unit ID")
ax.set_title("Live Pragati Unit Movement")

scatter = ax.scatter([], [])

def update_plot(frame):
    """Update the scatter plot with positions of moving units."""
    positions = [unit["position"] for unit in pragati_units if unit["status"] == "moving"]
    ids = [int(unit["id"].split("-")[1]) for unit in pragati_units if unit["status"] == "moving"]
    if positions and ids:
        scatter.set_offsets(list(zip(positions, ids)))
    else:
        scatter.set_offsets([])
    return scatter,

ani = animation.FuncAnimation(fig, update_plot, interval=1000, blit=False, cache_frame_data=False)

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# Start simulation loop in a background thread
threading.Thread(target=simulation_loop, daemon=True).start()

root.mainloop()

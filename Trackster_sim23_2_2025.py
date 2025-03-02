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
import csv
import os

# ======= LOAD STATION DATA FROM JSON =======
with open("C:/Users/aryam/OneDrive/Desktop/New folder/Website/htdocs/wordpress/Trackster/Trackster Simulation/Trackster/stations.json", "r") as f:
    station_data = json.load(f)


# Convert to a list of (station_name, distance_m)
stations_list = []
for s in station_data:
    stations_list.append((s["name"], s["distance_from_start"] * 1000))

# Sort stations by distance
stations_list.sort(key=lambda x: x[1])  # ascending order by distance (meters)

# Build a dict for quick lookup if needed
stations = {}
for s in station_data:
    stations[s["name"]] = {
        "distance_m": s["distance_from_start"] * 1000,
        "capacity": s["capacity"],
        "anchoring_slots": {i: None for i in range(1, s["capacity"]+1)}
    }

# ========== BUILD SEGMENTS FOR BLOCK OCCUPANCY ==========
"""
For each pair of adjacent stations in sorted order, we create one segment.
Example: (station0 -> station1), (station1 -> station2), ...
Each segment has:
- index
- start_station, end_station
- start_distance, end_distance
- occupied_by = None or a unit_id
"""
segments = []

def build_segments(stations_list):
    seg_list = []
    for i in range(len(stations_list) - 1):
        stA, distA = stations_list[i]
        stB, distB = stations_list[i+1]
        seg_list.append({
            "index": i,
            "start_station": stA,
            "end_station": stB,
            "start_distance": distA,
            "end_distance": distB,
            "occupied_by": None
        })
    return seg_list

segments = build_segments(stations_list)

# ========== INITIALIZE PRAGATI UNITS ==========
pragati_units = []
unit_id_num = 1
for st_name, st_info in stations.items():
    for slot in range(1, st_info["capacity"]+1):
        unit = {
            "id": f"PGT-{unit_id_num:03d}",
            "position_m": st_info["distance_m"],
            "speed_mps": 0.0,
            "direction": None,  # 'up' or 'down'
            "status": "anchored",
            "destination": None,
            "anchoring_slot": slot
        }
        pragati_units.append(unit)
        st_info["anchoring_slots"][slot] = unit
        unit_id_num += 1

# ====== SEGMENTS LOG SETUP ======
SEGMENT_LOG_FILENAME = "segments_log.csv"
write_segment_header = not os.path.exists(SEGMENT_LOG_FILENAME)

segment_logfile = open(SEGMENT_LOG_FILENAME, "a", newline="", encoding="utf-8")
segment_logwriter = csv.writer(segment_logfile)

if write_segment_header:
    segment_logwriter.writerow(["timestamp", "segment_index", "event", "unit_id"])
segment_logfile.flush()

def log_segment_event(segment_index, event_type, unit_id):
    """
    event_type can be 'ENTER' or 'EXIT'
    """
    timestamp = int(time.time())
    segment_logwriter.writerow([timestamp, segment_index, event_type, unit_id])
    segment_logfile.flush()

# ========== GUI SETUP ==========
root = tk.Tk()
root.title("Pragati Simulation with Block Occupancy")

table = ttk.Treeview(root, columns=("ID", "Position", "Speed", "Status", "Destination"), show="headings")
for col in ("ID", "Position", "Speed", "Status", "Destination"):
    table.heading(col, text=col)
    table.column(col, width=120)
table.pack(fill=tk.BOTH, expand=True)

def update_gui():
    table.delete(*table.get_children())
    for unit in pragati_units:
        pos_km = unit["position_m"] / 1000.0
        speed_kmh = unit["speed_mps"] * 3.6
        table.insert("", "end", values=(
            unit["id"],
            f"{pos_km:.2f} km",
            f"{speed_kmh:.1f} km/h",
            unit["status"],
            unit["destination"] if unit["destination"] else ""
        ))
    root.after(1000, update_gui)

root.after(1000, update_gui)

# ========== HELPER: FIND CURRENT SEGMENT ==========

def get_segment_index_for_position(pos_m):
    """
    Given a position in meters (pos_m),
    return the index of the segment that contains pos_m.
    If pos_m is exactly at or beyond the last station,
    or before the first station, return None.
    """
    for i, seg in enumerate(segments):
        start_m = min(seg["start_distance"], seg["end_distance"])
        end_m = max(seg["start_distance"], seg["end_distance"])
        if start_m <= pos_m < end_m:
            return i
    return None

# ========== SIMULATION LOGIC ==========

def assign_destinations():
    """
    Randomly assigns a new destination to anchored units (30% chance).
    We skip advanced scheduling for simplicity.
    """
    for unit in pragati_units:
        if unit["status"] == "anchored" and random.random() < 0.3:
            # find current station by matching position
            current_station = None
            for stn_name, stn_info in stations.items():
                if abs(stn_info["distance_m"] - unit["position_m"]) < 1.0:
                    current_station = stn_name
                    break

            possible = [s[0] for s in stations_list if s[0] != current_station]
            if not possible:
                continue

            dest = random.choice(possible)
            unit["destination"] = dest
            if stations[dest]["distance_m"] > unit["position_m"]:
                unit["direction"] = "up"
            else:
                unit["direction"] = "down"
            unit["status"] = "moving"

def move_units():
    """
    Move units with realistic acceleration (±1 m/s^2).
    Now we also do block checks:
      - If next segment is occupied, we must stop at the boundary.
      - If the next segment is free, we enter it (update 'occupied_by').
      - We release the old segment upon leaving it.
    """
    dt = 1.0
    max_acc = 1.0
    max_speed = 27.78  # 100 km/h in m/s

    for unit in pragati_units:
        if unit["status"] != "moving" or not unit["destination"]:
            continue

        # find current segment
        current_seg_index = get_segment_index_for_position(unit["position_m"])

        # If the unit is beyond the last segment or before the first, just move normally
        if current_seg_index is None:
            # normal acceleration without block checks
            accelerate(unit, dt, max_acc, max_speed)
            continue

        # 1) Occupy the segment if not already
        if segments[current_seg_index]["occupied_by"] != unit["id"]:
            # Another train might be here -> collision in real life, but let's keep it simple:
            # If it's free, occupy it. If not free by a different unit, we must stop.
            if segments[current_seg_index]["occupied_by"] is None:
                segments[current_seg_index]["occupied_by"] = unit["id"]
                log_segment_event(current_seg_index, "ENTER", unit["id"])
            else:
                # If another unit is there, force speed=0 to avoid collision
                if segments[current_seg_index]["occupied_by"] != unit["id"]:
                    unit["speed_mps"] = 0
                    # remain in place until the segment is freed
                    continue

        # 2) Check if about to cross into next segment
        #    If going "up", next_seg = current_seg_index + 1
        #    If going "down", next_seg = current_seg_index - 1
        next_seg_index = current_seg_index + 1 if unit["direction"] == "up" else current_seg_index - 1

        # boundary of current segment (the end we are traveling towards)
        seg_start = segments[current_seg_index]["start_distance"]
        seg_end = segments[current_seg_index]["end_distance"]

        boundary_m = max(seg_start, seg_end) if unit["direction"] == "up" else min(seg_start, seg_end)

        # If we are close to crossing that boundary
        distance_to_boundary = abs(boundary_m - unit["position_m"])

        # accelerate under normal conditions
        accelerate(unit, dt, max_acc, max_speed)

        # after accelerating, new position
        new_pos = unit["position_m"]
        if unit["direction"] == "up":
            new_pos += unit["speed_mps"] * dt
            if new_pos > boundary_m:
                new_pos = boundary_m
        else:
            new_pos -= unit["speed_mps"] * dt
            if new_pos < boundary_m:
                new_pos = boundary_m

        unit["position_m"] = new_pos

        # if we have reached boundary, try to enter next segment
        if abs(unit["position_m"] - boundary_m) < 0.1:
            # we are at the boundary
            if 0 <= next_seg_index < len(segments):
                # is next segment free or occupied by me?
                if (segments[next_seg_index]["occupied_by"] is None or
                    segments[next_seg_index]["occupied_by"] == unit["id"]):
                    # release current segment
                    if segments[current_seg_index]["occupied_by"] == unit["id"]:
                        segments[current_seg_index]["occupied_by"] = None
                        log_segment_event(current_seg_index, "EXIT", unit["id"])

                    # occupy next segment
                    if segments[next_seg_index]["occupied_by"] is None:
                        segments[next_seg_index]["occupied_by"] = unit["id"]
                        log_segment_event(next_seg_index, "ENTER", unit["id"])
                else:
                    # next segment is occupied by another unit -> stop here
                    unit["speed_mps"] = 0.0
            else:
                # no next segment -> possibly arrived at final station
                # normal arrival check
                pass

        # final check: if arrived at destination station
        dest_m = stations[unit["destination"]]["distance_m"]
        if abs(unit["position_m"] - dest_m) < 0.5:
            # arrived
            unit["speed_mps"] = 0.0
            unit["position_m"] = dest_m
            unit["status"] = "anchored"
            unit["direction"] = None
            unit["destination"] = None
            # release segment if occupying
            if current_seg_index is not None and segments[current_seg_index]["occupied_by"] == unit["id"]:
                segments[current_seg_index]["occupied_by"] = None
                log_segment_event(current_seg_index, "EXIT", unit["id"])

def accelerate(unit, dt, max_acc, max_speed):
    """
    Helper function: random acceleration within ±1 m/s^2,
    depending on 'up' or 'down' direction.
    """
    if unit["direction"] == "up":
        a = random.uniform(0, max_acc)
    else:
        a = random.uniform(-max_acc, 0)
    new_speed = unit["speed_mps"] + a * dt
    # clamp speed
    if new_speed < 0:
        new_speed = 0
    if new_speed > max_speed:
        new_speed = max_speed
    unit["speed_mps"] = new_speed

def simulation_loop():
    while True:
        assign_destinations()
        move_units()
        time.sleep(1)

# ====== MATPLOTLIB PLOTTING (OPTIONAL) ======
max_distance_m = stations_list[-1][1] if stations_list else 0
num_units = len(pragati_units)

fig, ax = plt.subplots()
ax.set_xlim(0, max_distance_m * 1.05)
ax.set_ylim(0, num_units + 1)
ax.set_xlabel("Distance (m)")
ax.set_ylabel("Pragati Unit ID")
ax.set_title("Trackster with Block Occupancy")

scatter = ax.scatter([], [])

def update_plot(frame):
    positions = []
    ids = []
    for unit in pragati_units:
        if unit["status"] == "moving":
            positions.append(unit["position_m"])
            numeric_id = int(unit["id"].split("-")[1])
            ids.append(numeric_id)
    scatter.set_offsets(list(zip(positions, ids)) if positions else [])
    return scatter,

ani = animation.FuncAnimation(fig, update_plot, interval=1000, blit=False, cache_frame_data=False)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack()

# Start background simulation
threading.Thread(target=simulation_loop, daemon=True).start()

try:
    root.mainloop()
finally:
    segment_logfile.close()

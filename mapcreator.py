import folium

# Create a base map centered around a rough midpoint
map_center = [27.0, 76.0]  # Adjust based on actual location range
map_obj = folium.Map(location=map_center, zoom_start=6)

# List of waypoints (example locations with latitude, longitude)
waypoints = [
    {"name": "New Dadri", "coords": [28.5504, 77.5536]},
    {"name": "Palwal", "coords": [28.1447, 77.3295]},
    {"name": "Rewari", "coords": [28.1972, 76.6176]},
    {"name": "Phulera", "coords": [26.8700, 75.2400]},
    {"name": "Ajmer", "coords": [26.4499, 74.6399]},
    {"name": "Marwar", "coords": [25.7475, 73.3381]},
    {"name": "Palanpur", "coords": [24.1725, 72.4383]},
    {"name": "Mahesana", "coords": [23.5879, 72.3693]},
    {"name": "Sanand", "coords": [22.9868, 72.3803]}
]

# Plot the waypoints on the map
for point in waypoints:
    folium.Marker(
        location=point["coords"], 
        popup=point["name"],
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(map_obj)

# Draw the route line
folium.PolyLine([point["coords"] for point in waypoints], color="red", weight=2.5, opacity=0.8).add_to(map_obj)

# Save map to file
map_obj.save("western_corridor_map.html")

print("Map has been generated and saved as 'western_corridor_map.html'. Open it in a browser.")

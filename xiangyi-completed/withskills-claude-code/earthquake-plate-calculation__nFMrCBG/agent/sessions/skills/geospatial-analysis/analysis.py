#!/usr/bin/env python3
"""
Find the earthquake furthest from the Pacific plate boundary within the Pacific plate.
Uses GeoPandas with proper coordinate projections for accurate distance calculations.
"""

import json
import geopandas as gpd
from shapely.geometry import Point, shape
from datetime import datetime
import sys

# Load data
print("Loading data...")
with open('/root/earthquakes_2024.json', 'r') as f:
    eq_data = json.load(f)

gdf_boundaries = gpd.read_file('/root/PB2002_boundaries.json')
gdf_plates = gpd.read_file('/root/PB2002_plates.json')

print(f"Loaded {len(eq_data['features'])} earthquakes")
print(f"Loaded {len(gdf_boundaries)} plate boundaries")
print(f"Loaded {len(gdf_plates)} plate features")

# Convert earthquakes to GeoDataFrame
print("\nConverting earthquakes to GeoDataFrame...")
earthquakes = []
for feature in eq_data['features']:
    coords = feature['geometry']['coordinates']  # [lon, lat, depth]
    props = feature['properties']
    earthquakes.append({
        'id': feature['id'],
        'longitude': coords[0],
        'latitude': coords[1],
        'magnitude': props['mag'],
        'place': props['place'],
        'time': props['time'],  # Unix timestamp in milliseconds
        'geometry': Point(coords[0], coords[1])
    })

gdf_eq = gpd.GeoDataFrame(earthquakes, crs='EPSG:4326')
print(f"Created GeoDataFrame with {len(gdf_eq)} earthquakes")

# Find the Pacific plate polygon
print("\nFinding Pacific plate...")
pacific_plate = None

# Try different possible identifiers for the Pacific plate
for idx, row in gdf_plates.iterrows():
    if row.get('PlateName') == 'Pacific' or row.get('Name') == 'Pacific' or row.get('Code') == 'PA':
        pacific_plate = row.geometry
        print(f"Found Pacific plate using identifier: {row.get('PlateName', row.get('Name', row.get('Code')))}")
        break

if pacific_plate is None:
    print("Warning: Could not find Pacific plate by standard identifiers")
    print("Available plate identifiers:")
    for idx, row in gdf_plates.iterrows():
        print(f"  - PlateName: {row.get('PlateName')}, Name: {row.get('Name')}, Code: {row.get('Code')}")
    sys.exit(1)

# Filter earthquakes within the Pacific plate
print("Filtering earthquakes within Pacific plate...")
eq_in_plate = gdf_eq[gdf_eq.within(pacific_plate)].copy()
print(f"Found {len(eq_in_plate)} earthquakes within the Pacific plate")

if len(eq_in_plate) == 0:
    print("Error: No earthquakes found within Pacific plate")
    sys.exit(1)

# Find Pacific plate boundaries
print("\nFinding Pacific plate boundaries...")
# Include boundaries that involve the Pacific plate (PA)
pacific_boundaries_mask = (
    (gdf_boundaries['PlateA'] == 'PA') |
    (gdf_boundaries['PlateB'] == 'PA')
)
gdf_pacific_bounds = gdf_boundaries[pacific_boundaries_mask]
print(f"Found {len(gdf_pacific_bounds)} Pacific plate boundaries")

# Combine all Pacific plate boundaries into a single geometry
print("Combining boundaries into single geometry...")
pacific_boundary_geom = gdf_pacific_bounds.geometry.unary_union
print(f"Combined boundary geometry type: {pacific_boundary_geom.geom_type}")

# Project to metric coordinate system for accurate distance calculations
print("\nProjecting to metric coordinate system (EPSG:4087)...")
METRIC_CRS = 'EPSG:4087'
eq_proj = eq_in_plate.to_crs(METRIC_CRS)
boundary_proj = gpd.GeoDataFrame(
    geometry=[pacific_boundary_geom],
    crs='EPSG:4326'
).to_crs(METRIC_CRS)

boundary_geom_proj = boundary_proj.geometry.iloc[0]

# Calculate distances to the Pacific plate boundary
print("Calculating distances to Pacific plate boundary...")
eq_proj['distance_m'] = eq_proj.geometry.distance(boundary_geom_proj)
eq_proj['distance_km'] = eq_proj['distance_m'] / 1000.0

# Update the original GeoDataFrame with distances
eq_in_plate['distance_km'] = eq_proj['distance_km'].values
eq_in_plate['distance_m'] = eq_proj['distance_m'].values

# Find the earthquake furthest from the boundary
print("\nFinding earthquake furthest from Pacific plate boundary...")
furthest_idx = eq_in_plate['distance_km'].idxmax()
furthest_eq = eq_in_plate.loc[furthest_idx]

print(f"\nFurthest earthquake found:")
print(f"  ID: {furthest_eq['id']}")
print(f"  Location: {furthest_eq['place']}")
print(f"  Magnitude: {furthest_eq['magnitude']}")
print(f"  Latitude: {furthest_eq['latitude']}")
print(f"  Longitude: {furthest_eq['longitude']}")
print(f"  Distance from boundary: {furthest_eq['distance_km']:.2f} km")
print(f"  Time (Unix ms): {furthest_eq['time']}")

# Convert Unix timestamp (milliseconds) to ISO 8601 format
timestamp_seconds = furthest_eq['time'] / 1000.0
dt = datetime.utcfromtimestamp(timestamp_seconds)
iso_time = dt.strftime('%Y-%m-%dT%H:%M:%SZ')

# Create output JSON
output = {
    'id': furthest_eq['id'],
    'place': furthest_eq['place'],
    'time': iso_time,
    'magnitude': float(furthest_eq['magnitude']),
    'latitude': float(furthest_eq['latitude']),
    'longitude': float(furthest_eq['longitude']),
    'distance_km': round(float(furthest_eq['distance_km']), 2)
}

print(f"\nOutput JSON:")
print(json.dumps(output, indent=2))

# Write to output file
print(f"\nWriting results to /root/answer.json...")
with open('/root/answer.json', 'w') as f:
    json.dump(output, f, indent=2)

print("Done!")

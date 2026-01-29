#!/usr/bin/env python3
"""
Geospatial analysis to find the earthquake furthest from the Pacific plate boundary
within the Pacific plate itself.
"""

import json
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime
import sys

def load_data():
    """Load earthquake and plate boundary data."""
    print("Loading data...")

    # Load earthquake data
    with open('/root/earthquakes_2024.json', 'r') as f:
        eq_data = json.load(f)

    # Load plates and boundaries
    gdf_plates = gpd.read_file('/root/PB2002_plates.json')
    gdf_boundaries = gpd.read_file('/root/PB2002_boundaries.json')

    print(f"Loaded {len(eq_data['features'])} earthquakes")
    print(f"Loaded {len(gdf_plates)} plate polygons")
    print(f"Loaded {len(gdf_boundaries)} boundary segments")

    return eq_data, gdf_plates, gdf_boundaries

def create_earthquake_gdf(eq_data):
    """Convert earthquake GeoJSON to GeoDataFrame."""
    print("\nProcessing earthquake data...")

    earthquakes = []
    for feature in eq_data['features']:
        props = feature['properties']
        coords = feature['geometry']['coordinates']

        # coords are [lon, lat, depth]
        eq = {
            'id': feature['id'],
            'place': props.get('place', ''),
            'time': props.get('time', 0),  # milliseconds since epoch
            'magnitude': props.get('mag', 0),
            'latitude': coords[1],
            'longitude': coords[0],
            'depth': coords[2] if len(coords) > 2 else 0,
        }
        earthquakes.append(eq)

    # Create GeoDataFrame
    geometry = [Point(eq['longitude'], eq['latitude']) for eq in earthquakes]
    gdf = gpd.GeoDataFrame(earthquakes, geometry=geometry, crs='EPSG:4326')

    print(f"Created GeoDataFrame with {len(gdf)} earthquakes")
    return gdf

def find_pacific_earthquakes(gdf_eq, gdf_plates):
    """Find earthquakes within the Pacific plate."""
    print("\nFiltering earthquakes in Pacific plate...")

    # Get the Pacific plate polygon
    pacific = gdf_plates[gdf_plates['Code'] == 'PA']
    if len(pacific) == 0:
        print("ERROR: Pacific plate not found!")
        sys.exit(1)

    pacific_geom = pacific.geometry.unary_union
    print(f"Pacific plate polygon created")

    # Find earthquakes within the Pacific plate
    earthquakes_in_pacific = gdf_eq[gdf_eq.within(pacific_geom)].copy()
    print(f"Found {len(earthquakes_in_pacific)} earthquakes within Pacific plate")

    return earthquakes_in_pacific

def calculate_distances_to_boundary(gdf_eq, gdf_boundaries):
    """Calculate distance from each earthquake to nearest Pacific boundary."""
    print("\nCalculating distances to plate boundaries...")

    # Filter boundaries that involve the Pacific plate
    pacific_boundaries = gdf_boundaries[
        (gdf_boundaries['PlateA'] == 'PA') | (gdf_boundaries['PlateB'] == 'PA')
    ]

    print(f"Found {len(pacific_boundaries)} boundary segments adjacent to Pacific plate")

    # Combine all boundary segments into a single geometry
    boundary_geom = pacific_boundaries.geometry.unary_union

    # Project both to metric coordinate system for accurate distance calculation
    METRIC_CRS = 'EPSG:4087'

    eq_proj = gdf_eq.to_crs(METRIC_CRS)
    boundary_proj = gpd.GeoDataFrame(
        geometry=[boundary_geom],
        crs=gdf_boundaries.crs
    ).to_crs(METRIC_CRS)

    # Calculate distances in meters
    distances_m = eq_proj.geometry.distance(boundary_proj.geometry.iloc[0])

    # Convert to kilometers and round to 2 decimal places
    gdf_eq['distance_km'] = round(distances_m / 1000.0, 2)

    print(f"Distance calculations complete")
    print(f"Min distance: {gdf_eq['distance_km'].min():.2f} km")
    print(f"Max distance: {gdf_eq['distance_km'].max():.2f} km")

    return gdf_eq

def convert_time_to_iso8601(timestamp_ms):
    """Convert milliseconds since epoch to ISO 8601 format."""
    # timestamp_ms is in milliseconds
    timestamp_s = timestamp_ms / 1000.0
    dt = datetime.utcfromtimestamp(timestamp_s)
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def find_furthest_earthquake(gdf_eq):
    """Find the earthquake furthest from the Pacific plate boundary."""
    print("\nFinding furthest earthquake...")

    furthest = gdf_eq.nlargest(1, 'distance_km').iloc[0]

    print(f"\nFurthest earthquake found:")
    print(f"  ID: {furthest['id']}")
    print(f"  Place: {furthest['place']}")
    print(f"  Magnitude: {furthest['magnitude']}")
    print(f"  Location: ({furthest['latitude']:.4f}, {furthest['longitude']:.4f})")
    print(f"  Distance: {furthest['distance_km']} km")

    return furthest

def save_result(earthquake, output_path):
    """Save the result to a JSON file."""
    print(f"\nSaving result to {output_path}...")

    result = {
        'id': earthquake['id'],
        'place': earthquake['place'],
        'time': convert_time_to_iso8601(earthquake['time']),
        'magnitude': earthquake['magnitude'],
        'latitude': round(earthquake['latitude'], 6),
        'longitude': round(earthquake['longitude'], 6),
        'distance_km': earthquake['distance_km']
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Result saved successfully!")
    return result

def main():
    """Main analysis workflow."""
    print("=" * 60)
    print("Geospatial Analysis: Furthest Earthquake from Pacific Boundary")
    print("=" * 60)

    # Load data
    eq_data, gdf_plates, gdf_boundaries = load_data()

    # Create earthquake GeoDataFrame
    gdf_eq = create_earthquake_gdf(eq_data)

    # Find earthquakes within Pacific plate
    gdf_eq_pacific = find_pacific_earthquakes(gdf_eq, gdf_plates)

    if len(gdf_eq_pacific) == 0:
        print("ERROR: No earthquakes found within Pacific plate!")
        sys.exit(1)

    # Calculate distances to Pacific plate boundary
    gdf_eq_pacific = calculate_distances_to_boundary(gdf_eq_pacific, gdf_boundaries)

    # Find the furthest earthquake
    furthest = find_furthest_earthquake(gdf_eq_pacific)

    # Save result
    result = save_result(furthest, '/root/answer.json')

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)

if __name__ == '__main__':
    main()

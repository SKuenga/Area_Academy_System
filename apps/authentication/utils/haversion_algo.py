import numpy as np

EARTH_RADIUS = 6371000  # meters

def check_distance(user_lat, user_lon, branches):
    # Convert inputs to float to prevent object/Decimal casting errors in NumPy
    user_lat = float(user_lat)
    user_lon = float(user_lon)

    # 1. Cast model field attributes explicitly to float
    branch_lats = np.array([float(b.latitude) for b in branches], dtype=np.float64)
    branch_lons = np.array([float(b.longitude) for b in branches], dtype=np.float64)

    # 2. Convert degrees to radians
    user_lat_rad = np.radians(user_lat)
    user_lon_rad = np.radians(user_lon)
    branch_lats_rad = np.radians(branch_lats)
    branch_lons_rad = np.radians(branch_lons)

    # 3. Calculate coordinate differences
    delta_lat = branch_lats_rad - user_lat_rad
    delta_lon = branch_lons_rad - user_lon_rad

    # 4. Haversine formula
    a = np.sin(delta_lat / 2.0)**2 + \
        np.cos(user_lat_rad) * np.cos(branch_lats_rad) * np.sin(delta_lon / 2.0)**2
    
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    distances = EARTH_RADIUS * c

    # 5. Find nearest branch index
    nearest_idx = np.argmin(distances)
    
    return branches[nearest_idx], float(distances[nearest_idx])

import numpy as np
import json
import os
from pyproj import Proj, transform


coords = np.array([
    (50.12413060964201, 8.607552521857166),
    (50.13104153062146, 8.716872044360008),
    (50.10572906849683, 8.757866865298572),
    (50.114456044438604, 8.675334053958041),
    (50.10392126972894, 8.631731759275732),
    (50.139217216992726, 8.676705648840892),
    (50.121404901636176, 8.66130128708773),
    (50.102612763576104, 8.6767882194423),
    (50.12705083884542, 8.692123319126726),
    (50.08907396096527, 8.670714912636585),  # depo
])

# parameters
num_instances = 99
num_points = 10
lat_center = 50.00
lon_center = 7.80

demands = np.array([1.0] * 9 + [0.0])

# Define scaling bounds
lat_min, lat_max = 50.08, 50.14
lon_min, lon_max = 8.60, 8.76

# problem: X axis and Y axis have different scales
# -> UTM gives coordinates in meters with minimal distortion for a small area
# convert from real coords to UTM-meters


# Define WGS84 (lat/lon) and UTM projection
wgs84 = Proj(proj='latlong', datum='WGS84')
utm = Proj(proj='utm', zone=32, datum='WGS84')


def latlon_to_xy(lat, lon):
    """(lat, lon) -> (x, y) (UTM 32N)"""
    x, y = transform(wgs84, utm, lon, lat)
    return np.array([x, y])


coords_xy = np.vstack([latlon_to_xy(lat, lon) for lat, lon in coords])

# calculate global boundaries (in meters at the corners of the rectangle lat/lon)
corner_xy = np.vstack([latlon_to_xy(lat, lon) for lat, lon in
                       [(lat_min, lon_min), (lat_min, lon_max),
                        (lat_max, lon_min), (lat_max, lon_max)]])

x_min, y_min = corner_xy.min(axis=0)
x_max, y_max = corner_xy.max(axis=0)


def xy_to_scaled(xy):
    """meters → [1, 100]"""
    x, y = xy.T
    const_scale = max(x_max - x_min, y_max-y_min)
    x_s = 1 + (x - x_min) / const_scale * 99
    y_s = 1 + (y - y_min) / const_scale * 99
    return np.vstack([x_s, y_s]).T


with open("data/DroneTruck-size-100-len-10.txt", "w") as f:

    # first raw is my coords
    # scale the coords
    scaled = xy_to_scaled(coords_xy)

    for i in range(10):
        for j in range(i + 1, 10):
            dist = ((scaled[i][0] - scaled[j][0])**2 + (scaled[i][1] - scaled[j][1])**2)**0.5

    row = [f"{x:.18e} {y:.18e} {d:.18e}"
           for (x, y), d in zip(scaled, demands)]
    f.write(" ".join(row) + "\n")

    # create random 99 raws of coords
    for _ in range(num_instances):
        lats = np.random.uniform(lat_min, lat_max, num_points)
        lons = np.random.uniform(lon_min, lon_max, num_points)
        coords_ = zip(lats, lons)
        # combine back into a vector
        xy = np.vstack([latlon_to_xy(lat, lon) for lat, lon in zip(lats, lons)])
        scaled = xy_to_scaled(xy)

        row = [f"{x:.18e} {y:.18e} {d:.18e}"
               for (x, y), d in zip(scaled, demands)]
        f.write(" ".join(row) + "\n")


meta_path = "data/DroneTruck-meta.json"
with open(meta_path, "w") as fp:
    json.dump({"x_min": float(x_min), "x_max": float(x_max),
               "y_min": float(y_min), "y_max": float(y_max)}, fp, indent=2)


# just fo test
test_coords = [(50.12413060964201, 8.607552521857166),
                (50.13104153062146, 8.716872044360008),
                (50.10572906849683, 8.757866865298572)]

xy_array = []
for lat, lon in test_coords:
    x, y = latlon_to_xy(lat, lon)
    print(f"lat={lat}, lon={lon}, x={x}, y={y}")
    const_scale = max(x_max - x_min, y_max - y_min)
    x_s = 1 + (x - x_min) / const_scale * 99
    y_s = 1 + (y - y_min) / const_scale * 99
    print(f"lat={lat}, lon={lon}, x_s={x_s}, y_s={y_s}\n")

    xy_array.append((x_s, y_s))

for i in range(3):
    for j in range(i + 1, 3):
        dist = ((xy_array[i][0] - xy_array[j][0])**2 + (xy_array[i][1] - xy_array[j][1])**2)**0.5
        print(f"dist between: {xy_array[i]} and {xy_array[j]}: {dist}")

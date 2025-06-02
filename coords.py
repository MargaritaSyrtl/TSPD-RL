import numpy as np
import math

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
#num_points = 10  # 9 clients + 1 depo
#R = 6371000  # Earth radius (meters)
#phi0_rad = math.radians(coords[:, 0].mean())  # mean latitude in rad
num_points = 10
lat_center = 50.00
lon_center = 7.80

# deviation amplitude (degrees)
lat_range = 0.02
lon_range = 0.03
demands = np.array([1.0] * 9 + [0.0])

with open("data/DroneTruck-size-100-len-10.txt", "w") as f:
    row = []
    # first raw is my coords
    for (lat, lon), d in zip(coords, demands):
        row.append(f"{lat:.15f} {lon:.15f} {d:.1f}")
    f.write(" ".join(row) + "\n")

    # create random 99 raws of coords
    for _ in range(num_instances):
        lats = np.random.uniform(lat_center - lat_range, lat_center + lat_range, num_points)
        lons = np.random.uniform(lon_center - lon_range, lon_center + lon_range, num_points)
        coords_ = zip(lats, lons)

        row = []
        for (lat, lon), d in zip(coords_, demands):
            row.append(f"{lat:.15f} {lon:.15f} {d:.1f}")
        f.write(" ".join(row) + "\n")


#def convert_coords(lat_deg: float, lon_deg: float):
#    phi_rad = math.radians(lat_deg)
#    lam_rad = math.radians(lon_deg)
#    x = R * lam_rad * math.cos(phi0_rad)
#    y = R * phi_rad
#    return x, y


#coords_xy = np.array([convert_coords(lat, lon) for lat, lon in coords])
#x_min, y_min = coords_xy.min(axis=0)
#print(x_min)
#print(y_min)
#x_max, y_max = coords_xy.max(axis=0)
#span_x, span_y = x_max - x_min, y_max - y_min
#coords_norm = np.empty_like(coords_xy)
#coords_norm[:, 0] = (coords_xy[:, 0] - x_min) / span_x * 100
#coords_norm[:, 1] = (coords_xy[:, 1] - y_min) / span_y * 100
#demands = np.array([1.0]*9 + [0.0])
#with open("data/DroneTruck-size-100-len-10.txt", "w") as f_data:
#    for _ in range(num_instances):
#        row = []
#        for (x, y), d in zip(coords_norm, demands):
#            row.append(f"{x:.18e} {y:.18e} {d:.18e}")
#        f_data.write(" ".join(row) + "\n")



import numpy as np

fixed_coords = np.array([
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


lat_min, lat_max = 50.00, 50.30
lon_min, lon_max = 8.40, 8.90

# parameters
num_instances = 99
num_points = 10  # 9 clients + 1 depo

with open("data/DroneTruck-size-100-len-10.txt", "w") as f_data:
    with open("data/DroneTruck-size-100-len-10_minmax.txt", "w") as f_minmax:
        # add my coords
        coords = fixed_coords.copy()
        min_vals = coords.min(axis=0)
        max_vals = coords.max(axis=0)
        scale = max_vals - min_vals
        scale[scale < 1e-5] = 1e-5
        normalized = (coords - min_vals) / scale

        demands = [1.0] * (num_points - 1) + [0.0]

        data_row = []
        for i in range(num_points):
            x, y = normalized[i]
            data_row.extend([x, y, demands[i]])

        f_data.write(" ".join(f"{val:.18e}" for val in data_row) + "\n")

        minmax_row = list(min_vals) + list(max_vals)
        f_minmax.write(" ".join(f"{val:.18e}" for val in minmax_row) + "\n")


        # generate random coords
        for _ in range(num_instances):
            lat_margin = (lat_max - lat_min) * 0.05
            lon_margin = (lon_max - lon_min) * 0.05

            lats = np.random.uniform(lat_min + lat_margin, lat_max - lat_margin, num_points)
            lons = np.random.uniform(lon_min + lon_margin, lon_max - lon_margin, num_points)
            coords = np.column_stack((lats, lons))

            # normalisation
            min_vals = coords.min(axis=0)
            max_vals = coords.max(axis=0)
            scale = max_vals - min_vals
            scale[scale < 1e-5] = 1e-5  # min scale
            normalized = (coords - min_vals) / scale
            #normalized = (coords - min_vals) / (max_vals - min_vals + 1e-8)

            # demands: 1.0 clients, 0.0 = depo
            demands = [1.0] * (num_points - 1) + [0.0]

            # write rows to data/
            data_row = []
            for i in range(num_points):
                x, y = normalized[i]
                data_row.extend([x, y, demands[i]])

            f_data.write(" ".join(f"{val:.18e}" for val in data_row) + "\n")

            #  write min/max for denormalisation
            minmax_row = list(min_vals) + list(max_vals)
            f_minmax.write(" ".join(f"{val:.18e}" for val in minmax_row) + "\n")



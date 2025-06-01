import numpy as np


lat_min, lat_max = 50.08, 50.15
lon_min, lon_max = 8.62, 8.73

# parameters
num_instances = 100
num_points = 10  # 9 clients + 1 depo

with open("data/DroneTruck-size-100-len-10.txt", "w") as f_data:
    with open("data/DroneTruck-size-100-len-10_minmax.txt", "w") as f_minmax:
        for _ in range(num_instances):
            # generate random coords
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



# 50.083272704265745, 8.631435453368507
# 50.149080019977504, 8.624120840915955
# 50.139846869319776, 8.7276336898657
# 50.10246992427316, 8.698596894978298


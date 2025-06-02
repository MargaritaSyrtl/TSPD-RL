import numpy as np
from DMRequest_google import DMRequest
from concurrent.futures import ThreadPoolExecutor, as_completed

data_file = "data/DroneTruck-size-100-len-10.txt"
out_file = "data/DroneTruck-google-distances.npy"
api_key = ""

n_nodes = 10


raw = np.loadtxt(data_file).reshape(-1, n_nodes, 3)
coord_batches = raw[:, :, :2]  # (batch, 10, 2)

dist_mats = np.zeros((len(coord_batches), n_nodes, n_nodes))


def process_instance(index, coords):
    try:
        places = [tuple(coord) for coord in coords]
        dm = DMRequest(places, api_key)
        data = dm.get_response_data_ga()

        dist_matrix = np.zeros((n_nodes, n_nodes))
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                key = frozenset([places[i], places[j]])
                dist = data['waypoints_distances'].get(key, 0.0)
                dist_matrix[i, j] = dist
                dist_matrix[j, i] = dist
        return index, dist_matrix
    except Exception as e:
        print(f"[!] Error at instance {index}: {e}")
        return index, np.zeros((n_nodes, n_nodes))  # fallback


max_workers = 5
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(process_instance, idx, coords)
               for idx, coords in enumerate(coord_batches)]
    for future in as_completed(futures):
        idx, mat = future.result()
        dist_mats[idx] = mat

print(dist_mats)
np.save(out_file, dist_mats)
print(f"Google distance matrix saved to: {out_file}")

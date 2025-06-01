import json, folium, numpy as np
from folium.features import DivIcon


def _denorm(val_norm, vmin, vmax):
    return val_norm * (vmax - vmin) + vmin


def visualize_instance(idx,
                       paths_file = "results/test_paths.json",
                       data_file = "data/DroneTruck-size-100-len-10.txt",
                       minmax_file = "data/DroneTruck-size-100-len-10_minmax.txt",
                       trim_repeat = True,
                       html_out = "route_map.html"):

    with open(paths_file, "r") as f:
        paths = json.load(f)
    truck_raw = paths["truck"][idx]
    drone_raw = paths["drone"][idx]
    # normalize coords
    with open(data_file) as f:
        line = f.readlines()[idx].split()
    coords_norm = np.array(line, dtype=float).reshape(-1, 3)[:, :2]  # (n_nodes, 2)
    # min / max
    with open(minmax_file) as f:
        lat_min, lon_min, lat_max, lon_max = map(float, f.readlines()[idx].split())

    coords_real = [(_denorm(lat, lat_min, lat_max),
                    _denorm(lon, lon_min, lon_max)) for lat, lon in coords_norm]

    depot = coords_real[-1]

    m = folium.Map(location=depot, zoom_start=14)
    for i, (lat, lon) in enumerate(coords_real):
        folium.Marker([lat, lon],
                      tooltip=f"node {i}",
                      icon=DivIcon(
                          icon_size =(22, 22),
                          icon_anchor=(11,11),
                          html=f"""<div style="background:#0066cc;color:white;
                                              width:22px;height:22px;
                                              border-radius:11px;text-align:center;
                                              line-height:22px;font-weight:bold;">
                                          {i}
                                       </div>""")).add_to(m)
    # truck
    truck_route = [0]  # start in depo
    for n in truck_raw:
        if n != truck_route[-1]:
            truck_route.append(n)
    if truck_route[-1] != 0:  # return back to depo
        truck_route.append(0)
    folium.PolyLine([coords_real[i] for i in truck_route],
                    color="blue", weight=4,
                    tooltip="Truck route").add_to(m)

    #steps = min(len(drone_raw), len(truck_raw) - 1)
    #for step in range(steps):
    #    dr_node = drone_raw[step]
    #    start_truck = truck_raw[step]
    #    end_truck = truck_raw[step + 1] if step + 1 < len(truck_raw) else 0
     #   if dr_node in (start_truck, end_truck):
     #       continue
    #    start_pt = coords_real[start_truck]
    #    client = coords_real[dr_node]
    #    end_pt = coords_real[end_truck]
    #    folium.PolyLine([start_pt, client, end_pt],
    #                    color="green", weight=3, dash_array="5,8",
    #                    tooltip=f"Drone {dr_node} (from {start_truck} to {end_truck})"
    #                    ).add_to(m)
    drone_route = [0]
    for n in drone_raw:
        if n != drone_route[-1]:
            drone_route.append(n)
    folium.PolyLine([coords_real[i] for i in drone_route],
                    color="red", weight=4,
                    tooltip="drone route").add_to(m)

    m.save(html_out)
    print("success")

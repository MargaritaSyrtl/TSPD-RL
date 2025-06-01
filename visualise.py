import json, folium, numpy as np
from folium.features import DivIcon
from itertools import groupby
from branca.element import Template, MacroElement


def _denorm(val_norm, vmin, vmax):
    return val_norm * (vmax - vmin) + vmin


def disp(i, depot_idx):
    """Human readable node numbers:
       • depot → 0
       • other nodes → +1"""
    return 0 if i == depot_idx else i + 1


def visualize_instance(idx,
                       paths_file="results/test_paths.json",
                       data_file="data/DroneTruck-size-100-len-10.txt",
                       minmax_file="data/DroneTruck-size-100-len-10_minmax.txt",
                       trim_repeat=True,
                       html_out="route_map.html"):

    with open(paths_file) as f:
        paths = json.load(f)
    truck_raw = paths["truck"][idx]  # with depo
    drone_raw = paths["drone"][idx]
    print(f"truck: {truck_raw}")
    print(f"drone: {drone_raw}")

    with open(data_file) as f:
        line = f.readlines()[idx].split()
    coords_norm = np.array(line, dtype=float).reshape(-1, 3)[:, :2]

    with open(minmax_file) as f:
        lat_min, lon_min, lat_max, lon_max = map(float, f.readlines()[idx].split())

    coords_real = [(_denorm(lat, lat_min, lat_max),
                    _denorm(lon, lon_min, lon_max)) for lat, lon in coords_norm]

    depot_idx = len(coords_real) - 1
    depot_coord = coords_real[depot_idx]

    m = folium.Map(location=depot_coord, zoom_start=14)
    for i, (lat, lon) in enumerate(coords_real):
        folium.Marker([lat, lon],
                      tooltip=f"node {i}",
                      icon=DivIcon(icon_size=(22, 22),
                                   icon_anchor=(11, 11),
                                   html=f"""<div style="background:#0066cc;color:white;
                                                   width:22px;height:22px;
                                                   border-radius:11px;text-align:center;
                                                   line-height:22px;font-weight:bold;">
                                                {i}
                                            </div>""")).add_to(m)

    # truck route
    truck_route = [k for k, _ in groupby(truck_raw)]
    folium.PolyLine([coords_real[i] for i in truck_route],
                    color="blue", weight=4,
                    tooltip=f"Truck").add_to(m)

    # drone route
    drone_str = ""
    # steps = len(drone_raw)
    steps = min(len(drone_raw), len(truck_raw) - 1)
    for t in range(steps):
        start_truck = truck_raw[t]  # launch node
        end_truck = truck_raw[t + 1]  # land node
        dr_node = drone_raw[t]  # drone node

        # dron hasn't launch
        if dr_node in (start_truck, end_truck):
            continue

        folium.PolyLine(
            [coords_real[start_truck],
             coords_real[dr_node],
             coords_real[end_truck]],
            color="green", weight=3, dash_array="6 8",
            tooltip=f"Drone {disp(start_truck,depot_idx)}→{disp(dr_node,depot_idx)}→{disp(end_truck,depot_idx)}"
        ).add_to(m)
        drone_str += f"{disp(start_truck,depot_idx)}→{disp(dr_node,depot_idx)}→"
        if end_truck == depot_idx:
            drone_str += "0"

    # HTML
    truck_str = " → ".join(str(disp(n, depot_idx)) for n in truck_route)
    legend_html = f"""
            <div style="
                 position: fixed;
                 bottom: 30px; right: 30px;
                 z-index: 9999;
                 background: rgba(255,255,255,0.9);
                 padding: 10px 14px;
                 border: 2px solid #999;
                 border-radius: 6px;
                 box-shadow: 3px 3px 6px rgba(0,0,0,0.25);
                 font-size: 14px; line-height: 1.5;">
              <b>Optimal route for given points:&nbsp;</b><br>
              <span style="color:#0066ff; font-weight:600;">
                Truck&nbsp;{truck_str}
              </span><br>
              <span style="color:#008800; font-weight:600;">
                Drone&nbsp;{drone_str}
              </span>
            </div>"""

    macro = MacroElement()
    macro._template = Template(f"{{% macro html(this, kwargs) %}}{legend_html}{{% endmacro %}}")
    m.get_root().add_child(macro)

    m.save(html_out)
    print("saved →", html_out)

import json, folium, numpy as np
from folium.features import DivIcon
from itertools import groupby
from branca.element import Template, MacroElement
import datetime as dt
from utils import DMRequest_osrm

for i, h in enumerate(np.loadtxt('results/test_results-100-len-10.txt')):
    td = dt.timedelta(hours=float(h))
    print(f'#{i:02d}: {td}')


def disp(i, depot_idx):
    """Human readable node numbers:
       • depot → 0
       • other nodes → +1"""
    return 0 if i == depot_idx else i + 1


def visualize_instance(idx,
                       paths_file="results/test_paths.json",
                       data_file="data/DroneTruck-size-100-len-10.txt",
                       html_out="route_map.html"):

    # Load paths (truck + drone)
    with open(paths_file) as f:
        paths = json.load(f)
    truck_raw = paths["truck"][idx]
    drone_raw = paths["drone"][idx]
    print(f"truck: {truck_raw}")
    print(f"drone: {drone_raw}")

    # Load real coordinates from .txt
    with open(data_file) as f:
        line = f.readlines()[idx].split()
    coords_real = np.array(line, dtype=float).reshape(-1, 3)[:, :2]  # use lat/lon directly

    depot_idx = len(coords_real) - 1
    depot_coord = coords_real[depot_idx]

    dm = DMRequest_osrm.DMRequest(coords_real)

    # Initialize map
    m = folium.Map(location=depot_coord.tolist(), zoom_start=14)

    # Plot points
    for i, (lat, lon) in enumerate(coords_real):
        folium.Marker([lat, lon],
                      tooltip=f"node {i}",
                      icon=DivIcon(icon_size=(22, 22),
                                   icon_anchor=(11, 11),
                                   html=f"""<div style="background:#0066cc;color:white;
                                                   width:22px;height:22px;
                                                   border-radius:11px;text-align:center;
                                                   line-height:22px;font-weight:bold;">
                                                {disp(i,depot_idx)}
                                            </div>""")).add_to(m)

    # Truck route
    truck_route = [k for k, _ in groupby(truck_raw)]
    for a, b in zip(truck_route[:-1], truck_route[1:]):
        geom = dm.get_geometry_for_route(coords_real[a], coords_real[b])
        if geom:
            folium.PolyLine(geom, color="blue", weight=4, tooltip=f"Truck {a}->{b}").add_to(m)
        else:
            folium.PolyLine([coords_real[a], coords_real[b]], color="blue", weight=4, dash_array="4 8").add_to(m)

    # Drone route
    drone_route = [truck_raw[0]] + drone_raw
    folium.PolyLine([coords_real[i] for i in drone_route],
                    color="green", weight=3, dash_array="6 8",
                    tooltip="Drone").add_to(m)

    # Add legend
    truck_str = " → ".join(str(disp(n, depot_idx)) for n in truck_route)
    drone_str = " → ".join(str(disp(n, depot_idx)) for n in drone_route)
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

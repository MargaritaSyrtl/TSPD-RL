import json, folium, numpy as np
from folium.features import DivIcon
from itertools import groupby
from branca.element import Template, MacroElement
from pyproj import Transformer

# from UTM-32N (meters) into WGS-84 (lat/lon)
to_ll = Transformer.from_crs("EPSG:32632", "EPSG:4326", always_xy=True)


def disp(i, depot_idx):
    """Human-readable node numbers (0 = depot)."""
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

    # Load real coordinates from the file
    with open(data_file) as f:
        line = f.readlines()[idx].split()
    coords_scaled = np.array(line, dtype=float).reshape(-1, 3)[:, :2]   # (N, 2)

    # decode scaled into meters into lat/lon
    coords_real = rescale_coords(coords_scaled)
    print(coords_real)

    depot_idx = len(coords_real) - 1
    depot_coord = coords_real[depot_idx]

    # initialize map
    m = folium.Map(location=depot_coord.tolist(), zoom_start=14)

    # markers
    for i, (lat, lon) in enumerate(coords_real):
        folium.Marker([lat, lon],
                      tooltip=f"node {i}",
                      icon=DivIcon(icon_size=(22, 22),
                                   icon_anchor=(11, 11),
                                   html=f"""<div style="background:#0066cc;color:white;
                                                   width:22px;height:22px;
                                                   border-radius:11px;text-align:center;
                                                   line-height:22px;font-weight:bold;">
                                                {disp(i, depot_idx)}
                                            </div>""")).add_to(m)

    # truck
    truck_route = [k for k, _ in groupby(truck_raw)]
    folium.PolyLine([coords_real[i] for i in truck_route],
                    color="blue", weight=4, tooltip="Truck").add_to(m)

    # drone
    drone_route = [truck_raw[0]] + drone_raw
    folium.PolyLine([coords_real[i] for i in drone_route],
                    color="green", weight=3, dash_array="6 8",
                    tooltip="Drone").add_to(m)

    # legend
    truck_str = " → ".join(str(disp(n, depot_idx)) for n in truck_route)
    drone_str = " → ".join(str(disp(n, depot_idx)) for n in drone_route)
    legend_html = f"""
        <div style="
             position: fixed; bottom: 30px; right: 30px;
             z-index: 9999; background: rgba(255,255,255,0.9);
             padding: 10px 14px; border: 2px solid #999;
             border-radius: 6px; box-shadow: 3px 3px 6px rgba(0,0,0,0.25);
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


def rescale_coords(coords_scaled, meta_file="data/DroneTruck-meta.json"):
    # read boundaries for de-/ normalisation
    with open(meta_file) as fp:
        meta = json.load(fp)

    x_min, x_max = meta["x_min"], meta["x_max"]
    y_min, y_max = meta["y_min"], meta["y_max"]

    scale_const = max(x_max-x_min, y_max-y_min)
    # scaled [1‥100] into UTM 32N
    x = x_min + (coords_scaled[:, 0] - 1) / 99 * (scale_const)
    y = y_min + (coords_scaled[:, 1] - 1) / 99 * scale_const
    xy = np.stack([x, y], axis=1)

    # meters into (lat, lon)
    lon, lat = zip(*[to_ll.transform(xx, yy) for xx, yy in xy])
    return np.stack([lat, lon], axis=1)


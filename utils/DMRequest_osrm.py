import requests
from itertools import combinations


class DMRequest(object):
    def __init__(self, places):
        self.base_url = 'http://localhost:5000/table/v1/driving'
        self.route_url = 'http://localhost:5000/route/v1/driving'
        self.places = places  # list of (lat, lon)

    def __get_distances(self):
        # collect coordinates of points in OSRM format: (longitude, latitude)
        coords = ';'.join([f"{lon},{lat}" for lat, lon in self.places])
        try:
            url = f"{self.base_url}/{coords}?annotations=distance,duration"
            response = requests.get(url).json()
            return response
        except requests.exceptions.RequestException as exc:
            print(f"Request failed: {exc}")
            return None

    def get_response_data_osrm(self):
        """
        gets distances/durations from local OSRM server.
        Output matches format: dict with keys:
            'waypoints_distances', 'waypoints_durations', 'waypoints_geometries'
        """
        data = {
            'waypoints_distances': {},
            'waypoints_durations': {},
            'waypoints_geometries': {},
        }

        osrm_data = self.__get_distances()
        if not osrm_data or osrm_data.get('code') != 'Ok':
            print("[!] OSRM error or empty response.")
            return data

        distances = osrm_data['distances']
        durations = osrm_data['durations']

        for i, wp1 in enumerate(self.places):
            for j, wp2 in enumerate(self.places):
                if j <= i:
                    continue
                key = frozenset([wp1, wp2])
                dist = distances[i][j] if distances[i][j] is not None else 0.0
                dur = durations[i][j] if durations[i][j] is not None else 0.0
                data['waypoints_distances'][key] = dist
                data['waypoints_durations'][key] = dur

        # Geometry
        for wp1, wp2 in combinations(self.places, 2):
            geom = self.get_geometry_for_route(wp1, wp2)
            if geom:
                key = frozenset([wp1, wp2])
                data['waypoints_geometries'][key] = geom

        return data

    def get_geometry_for_route(self, waypoint1, waypoint2):
        coords = f"{waypoint1[1]},{waypoint1[0]};{waypoint2[1]},{waypoint2[0]}"
        url = f"{self.route_url}/{coords}?overview=full&geometries=geojson"
        try:
            response = requests.get(url).json()
            if response.get("code") == "Ok" and "routes" in response:
                geometry = response['routes'][0]['geometry']['coordinates']
                return [(lat, lon) for lon, lat in geometry]  # flip the coordinates
        except Exception as exc:
            print(f"Geometry error: {exc}")
        return None

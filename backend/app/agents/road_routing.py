import logging
from typing import List, Tuple, Dict, Any
import httpx

logger = logging.getLogger("galvao_logi.road_routing")

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def _build_fallback_geometry(coordinates: List[Tuple[float, float]]) -> List[List[float]]:
    """Gera linha conectando os pontos quando serviço de malha viária estiver indisponível."""
    return [[float(lat), float(lon)] for lat, lon in coordinates]

def fetch_osrm_road_route(
    coordinates: List[Tuple[float, float]],
    timeout_seconds: float = 6.0
) -> Dict[str, Any]:
    """
    Consulta o motor OSRM (Open Source Routing Machine) para obter o traçado real
    seguido pelas ruas e rodovias, eliminando retas euclidianas.
    Retorna a lista de coordenadas [latitude, longitude] detalhada da malha viária.
    """
    if not coordinates or len(coordinates) < 2:
        return {
            "geometry": _build_fallback_geometry(coordinates),
            "distance_km": 0.0,
            "duration_minutes": 0,
            "is_road_network": True
        }

    # OSRM espera formato {longitude},{latitude};{longitude},{latitude}
    coords_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in coordinates)
    url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson&steps=false"

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if "routes" in data and len(data["routes"]) > 0:
                    primary_route = data["routes"][0]
                    # GeoJSON usa [lon, lat], convertemos para [lat, lon] do Leaflet/Map
                    road_points = [
                        [round(pt[1], 6), round(pt[0], 6)]
                        for pt in primary_route["geometry"]["coordinates"]
                    ]
                    dist_km = round(primary_route.get("distance", 0.0) / 1000.0, 1)
                    dur_min = max(1, int(round(primary_route.get("duration", 0.0) / 60.0)))
                    return {
                        "geometry": road_points,
                        "distance_km": dist_km,
                        "duration_minutes": dur_min,
                        "is_road_network": True
                    }
    except Exception as exc:
        logger.warning(f"OSRM roteamento rodoviário inacessível, aplicando fallback: {exc}")

    # Fallback caso OSRM falhe ou timeout
    fallback_geom = _build_fallback_geometry(coordinates)
    approx_dist = 0.0
    for i in range(1, len(coordinates)):
        approx_dist += haversine_km(coordinates[i-1][0], coordinates[i-1][1], coordinates[i][0], coordinates[i][1]) * 1.3

    return {
        "geometry": fallback_geom,
        "distance_km": round(approx_dist, 1),
        "duration_minutes": max(5, int(round((approx_dist / 35.0) * 60))),
        "is_road_network": False
    }

import pytest
from app.agents.router import MathematicalRouterAgent, haversine_distance_km, estimate_travel_time_minutes

def test_haversine_and_travel_time():
    # São Paulo Centro -> Guarulhos Aeroporto (~20 km)
    dist = haversine_distance_km(-23.5505, -46.6333, -23.4356, -46.4731)
    assert 18.0 <= dist <= 24.0

    travel_min = estimate_travel_time_minutes(dist, speed_kmh=40.0)
    assert travel_min > 0

def test_ortools_solver_multi_stop():
    router = MathematicalRouterAgent()
    start = {"name": "Depósito Central", "latitude": -23.5300, "longitude": -46.6500}
    destinations = [
        {"id": "d1", "name": "Mercado Sul", "latitude": -23.5489, "longitude": -46.6388, "service_time_minutes": 25},
        {"id": "d2", "name": "CD Oeste", "latitude": -23.4920, "longitude": -46.7350, "service_time_minutes": 30},
        {"id": "d3", "name": "Galpão Leste", "latitude": -23.5550, "longitude": -46.6020, "service_time_minutes": 20}
    ]

    result = router.solve_route(start, destinations, departure_time_str="08:00")
    
    assert "sequence" in result
    assert len(result["sequence"]) == 4 # start + 3 stops
    assert result["total_distance_km"] > 0
    assert result["total_time_minutes"] > 0
    assert len(result["timeline"]) == 4

def test_chronic_dock_prioritized_first():
    router = MathematicalRouterAgent()
    start = {"name": "Depósito Central", "latitude": -23.5300, "longitude": -46.6500}
    destinations = [
        {"id": "normal_1", "name": "Doca Normal 1", "latitude": -23.5400, "longitude": -46.6400, "service_time_minutes": 20},
        {"id": "chronic_doca", "name": "Doca Crônica Fila", "latitude": -23.5600, "longitude": -46.6300, "service_time_minutes": 45},
        {"id": "normal_2", "name": "Doca Normal 2", "latitude": -23.5700, "longitude": -46.6100, "service_time_minutes": 20}
    ]

    dock_profiles = {
        "chronic_doca": {
            "classification": "CHRONIC_SLOW",
            "recommended_placement": "EARLY_MORNING",
            "inflated_service_minutes": 30
        }
    }

    result = router.solve_route(start, destinations, departure_time_str="07:30", dock_profiles=dock_profiles)
    
    # Nó crônico deve estar entre os nós atendidos com sucesso
    assert result["chronic_prioritized_count"] == 1
    timeline = result["timeline"]
    assert any(t["is_chronic_prioritized"] for t in timeline)

def test_anti_idle_rule_protects_driver_time():
    # Forçar uma janela de tempo distante que exigiria > 25 minutos de espera ociosa
    router = MathematicalRouterAgent(max_idle_wait_minutes=25)
    start = {"name": "Depósito", "latitude": -23.5300, "longitude": -46.6500}
    destinations = [
        {"id": "slow_late", "name": "Doca Janela Tarde", "latitude": -23.5350, "longitude": -46.6550, "service_time_minutes": 30}
    ]

    # Janela preferida às 15:00 quando a saída é às 08:00 (espera seria de 7 horas)
    dock_profiles = {
        "slow_late": {
            "classification": "TIME_WINDOW_SLOW",
            "preferred_window": ("15:00", "17:00"),
            "inflated_service_minutes": 20
        }
    }

    result = router.solve_route(start, destinations, departure_time_str="08:00", dock_profiles=dock_profiles)
    # A regra anti-ociosidade deve intervir, não permitindo espera artificial e somando anti_idle_saved_minutes
    assert result["anti_idle_saved_minutes"] > 25
    # O motorista não deve esperar na prática: idle_wait_minutes da parada deve ser 0
    late_stop = [t for t in result["timeline"] if t["node_index"] == 1][0]
    assert late_stop["idle_wait_minutes"] == 0
    assert late_stop["service_start_minute"] == late_stop["arrival_minute"]

import pytest
from app.agents.router import MathematicalRouterAgent
from app.agents.obstacles import ObstacleMonitorAgent
from app.models.schemas import TruckBase, VehicleType
from app.agents.dock_profiler import DockProfilerAgent

def test_router_single_stop():
    router = MathematicalRouterAgent()
    start = {"name": "Depósito", "latitude": -23.5300, "longitude": -46.6500}
    destinations = [
        {"id": "d1", "name": "Única Parada", "latitude": -23.5489, "longitude": -46.6388, "service_time_minutes": 20}
    ]

    result = router.solve_route(start, destinations)
    assert len(result["sequence"]) == 2
    assert result["total_distance_km"] > 0
    assert result["total_time_minutes"] > 0

def test_router_empty_destinations():
    router = MathematicalRouterAgent()
    start = {"name": "Depósito", "latitude": -23.5300, "longitude": -46.6500}
    destinations = []

    result = router.solve_route(start, destinations)
    assert result["sequence"] == [0]
    assert result["total_distance_km"] == 0.0

def test_obstacle_excess_weight_clearance():
    agent = ObstacleMonitorAgent()
    bitrem = TruckBase(
        driver_id="d1",
        plate="BIT-7777",
        vehicle_type=VehicleType.BITREM,
        height_meters=4.20,
        width_meters=2.60,
        length_meters=25.0,
        gross_weight_tonnes=74.0, # PBT 74 toneladas
        axle_count=9
    )

    # Ponte histórica com limite de 45 toneladas
    res = agent.check_clearance(bitrem, segment_max_weight=45.0)
    assert res["allowed"] is False
    assert res["violation"] == "WEIGHT_LIMIT"

def test_dock_profiler_exactly_two_reports():
    agent = DockProfilerAgent(min_reports_threshold=2)
    reports = [
        {"time_of_day": "11:00", "excess_wait_minutes": 30},
        {"time_of_day": "11:30", "excess_wait_minutes": 45}
    ]
    res = agent.analyze_dock({"id": "d_min"}, reports)
    assert res["active_slow_dock"] is True
    assert res["classification"] == "TIME_WINDOW_SLOW"
    assert res["inflated_service_minutes"] == 37 or res["inflated_service_minutes"] == 38 # ~37.5

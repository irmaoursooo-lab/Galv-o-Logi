import pytest
from app.agents.obstacles import ObstacleMonitorAgent
from app.models.schemas import TruckBase, VehicleType

def test_obstacle_score_formula():
    agent = ObstacleMonitorAgent(w_congestion=0.4, w_narrow=0.25, w_signals=0.2, w_crowd=0.15)
    # Fully clear
    score_zero = agent.calculate_obstacle_score(0.0, 0.0, 0, 0)
    assert score_zero == 0.0

    # High congestion (0.8), medium narrow (0.5), 5 signals (0.5), 1 report (0.2)
    # Expected: 0.4*0.8 + 0.25*0.5 + 0.2*0.5 + 0.15*0.2 = 0.32 + 0.125 + 0.10 + 0.03 = 0.575 -> 57.5
    score = agent.calculate_obstacle_score(0.8, 0.5, 5, 1)
    assert 57.0 <= score <= 58.0

def test_truck_height_clearance_violation():
    agent = ObstacleMonitorAgent()
    truck = TruckBase(
        driver_id="d1",
        plate="ABC-1234",
        vehicle_type=VehicleType.CARRETA,
        height_meters=4.30,
        width_meters=2.60,
        length_meters=18.0,
        gross_weight_tonnes=45.0,
        axle_count=6
    )

    # Bridge clearance 4.10m is lower than truck 4.30m
    result = agent.check_clearance(truck, segment_max_height=4.10)
    assert result["allowed"] is False
    assert result["violation"] == "HEIGHT_LIMIT"

def test_truck_clearance_success():
    agent = ObstacleMonitorAgent()
    truck = TruckBase(
        driver_id="d1",
        plate="ABC-1234",
        vehicle_type=VehicleType.TRUCK,
        height_meters=3.80,
        width_meters=2.50,
        length_meters=12.0,
        gross_weight_tonnes=23.0,
        axle_count=3
    )

    result = agent.check_clearance(truck, segment_max_height=4.40, segment_max_weight=30.0)
    assert result["allowed"] is True

def test_reroute_trigger_threshold():
    agent = ObstacleMonitorAgent(reroute_threshold_minutes=4)

    # Saving 6 minutes (>= 4 minutes) -> Triggers alternative
    analysis_6m = agent.analyze_segment(
        segment_from="Ponto A",
        segment_to="Ponto B",
        current_travel_time_min=20,
        alternative_travel_time_min=14
    )
    assert analysis_6m.alternative_available is True
    assert analysis_6m.alternative_time_saved_minutes == 6
    assert "ECONOMIZA 6 MIN" in analysis_6m.alert_message

    # Saving only 2 minutes (< 4 minutes) -> No alert triggered
    analysis_2m = agent.analyze_segment(
        segment_from="Ponto A",
        segment_to="Ponto B",
        current_travel_time_min=20,
        alternative_travel_time_min=18
    )
    assert analysis_2m.alternative_available is False

def test_obstacle_weight_clearance_message_and_tts():
    agent = ObstacleMonitorAgent()
    bitrem = TruckBase(
        driver_id="d-bitrem",
        plate="BIT-9999",
        vehicle_type=VehicleType.BITREM,
        height_meters=4.10,
        width_meters=2.60,
        length_meters=25.0,
        gross_weight_tonnes=74.0,
        axle_count=9
    )

    analysis = agent.analyze_segment(
        segment_from="Entrada Ponte",
        segment_to="Saída Ponte",
        truck=bitrem,
        segment_max_weight=45.0
    )

    assert analysis.alternative_available is True
    assert analysis.truck_clearance_ok is False
    assert "LIMITE DE PESO" in analysis.alert_message
    assert "45.0t" in analysis.alert_message
    assert "peso" in analysis.tts_audio_alert.lower()

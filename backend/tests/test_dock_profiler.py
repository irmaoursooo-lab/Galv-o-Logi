import pytest
from app.agents.dock_profiler import DockProfilerAgent

def test_dock_profiler_under_threshold():
    agent = DockProfilerAgent(min_reports_threshold=2)
    # 1 report only
    reports = [{"time_of_day": "10:00", "excess_wait_minutes": 40}]
    analysis = agent.analyze_dock({"id": "d1", "name": "Doca Teste"}, reports)
    
    assert analysis["active_slow_dock"] is False
    assert analysis["classification"] == "NORMAL"
    assert analysis["inflated_service_minutes"] == 0

def test_dock_profiler_chronic_slow():
    agent = DockProfilerAgent(min_reports_threshold=2)
    # Reports spread throughout the day (08:00 and 16:00 -> span = 8h >= 5h)
    reports = [
        {"time_of_day": "08:15", "excess_wait_minutes": 60},
        {"time_of_day": "16:30", "excess_wait_minutes": 80}
    ]
    analysis = agent.analyze_dock({"id": "d2", "name": "Mercado Central"}, reports)
    
    assert analysis["active_slow_dock"] is True
    assert analysis["classification"] == "CHRONIC_SLOW"
    assert analysis["recommended_placement"] == "EARLY_MORNING"
    assert analysis["inflated_service_minutes"] == 70 # average of 60 and 80

def test_dock_profiler_time_window_slow():
    agent = DockProfilerAgent(min_reports_threshold=2)
    # Reports concentrated at lunch / shift change (12:00 and 12:30)
    reports = [
        {"time_of_day": "12:00", "excess_wait_minutes": 50},
        {"time_of_day": "12:30", "excess_wait_minutes": 50}
    ]
    analysis = agent.analyze_dock({"id": "d3", "name": "CD Anhanguera"}, reports)
    
    assert analysis["active_slow_dock"] is True
    assert analysis["classification"] == "TIME_WINDOW_SLOW"
    assert analysis["recommended_placement"] == "FAVORABLE_WINDOW"
    assert len(analysis["avoid_windows"]) > 0

import pytest
from app.agents.supervisor import SupervisorOrchestratorAgent
from app.models.schemas import RouteRequest, WaypointInput

def test_supervisor_orchestration_pipeline():
    supervisor = SupervisorOrchestratorAgent()

    request = RouteRequest(
        driver_id="driver-test",
        start_latitude=-23.5300,
        start_longitude=-46.6500,
        start_address="Garagem Central",
        departure_time="07:30",
        destinations=[
            WaypointInput(
                name="Cliente Centro",
                address="Rua Direita, 50",
                latitude=-23.5489,
                longitude=-46.6388,
                service_time_minutes=30
            ),
            WaypointInput(
                name="Cliente Pinheiros",
                address="Av. Faria Lima, 1000",
                latitude=-23.5680,
                longitude=-46.6920,
                service_time_minutes=40
            )
        ],
        enable_meal_breaks=True
    )

    response = supervisor.orchestrate_route(request)

    assert response.route_id is not None
    assert response.total_stops == 2 # 2 entregas reais (alimentação não conta como parada)
    assert response.total_distance_km > 0
    assert response.total_duration_minutes > 0
    assert len(response.itinerary) >= 3
    assert "Itinerário" in response.tts_briefing

def test_supervisor_meal_break_timeline_continuity():
    supervisor = SupervisorOrchestratorAgent()

    # Saída às 11:15 cruza a janela de almoço (11:45 - 13:30)
    request = RouteRequest(
        driver_id="driver-lunch",
        start_latitude=-23.5300,
        start_longitude=-46.6500,
        departure_time="11:15",
        destinations=[
            WaypointInput(
                name="Cliente 1",
                address="Rua A",
                latitude=-23.5400,
                longitude=-46.6400,
                service_time_minutes=20
            ),
            WaypointInput(
                name="Cliente 2",
                address="Rua B",
                latitude=-23.6000,
                longitude=-46.6000,
                service_time_minutes=30
            )
        ],
        enable_meal_breaks=True
    )

    response = supervisor.orchestrate_route(request)
    itinerary = response.itinerary
    
    # Deve conter uma parada MEAL_BREAK
    meal_stops = [s for s in itinerary if s.stop_type.value == "MEAL_BREAK"]
    assert len(meal_stops) >= 1
    meal_stop = meal_stops[0]
    
    # Encontrar o índice da pausa de almoço e da parada seguinte
    meal_idx = itinerary.index(meal_stop)
    next_delivery = itinerary[meal_idx + 1]

    # Converter HH:MM em minutos para checagem estrita de continuidade
    def to_min(t_str):
        h, m = map(int, t_str.split(":"))
        return h * 60 + m

    meal_arr = to_min(meal_stop.arrival_time)
    meal_dep = to_min(meal_stop.departure_time)
    deliv_arr = to_min(next_delivery.arrival_time)
    deliv_dep = to_min(next_delivery.departure_time)

    # Pausa deve durar o tempo previsto
    assert meal_dep >= meal_arr + meal_stop.service_duration_minutes
    # A entrega subsequente não pode acontecer antes do término do almoço
    assert deliv_arr >= meal_dep
    assert deliv_dep >= deliv_arr + next_delivery.service_duration_minutes
    # O tempo total da rota deve abranger todo o período
    assert response.total_duration_minutes >= (deliv_dep - to_min(itinerary[0].departure_time))

def test_supervisor_destination_id_slow_dock_preservation():
    from app.models.entities import create_destination, add_slow_report
    
    dest = create_destination("Doca Especial UUID", "Rua das Flores, 10", -23.5400, -46.6400)
    dest_id = dest["id"]
    
    # 2 apontamentos dispersos -> Lento Crônico
    add_slow_report(dest_id, "d1", "08:00", 60)
    add_slow_report(dest_id, "d2", "16:00", 60)

    supervisor = SupervisorOrchestratorAgent()
    request = RouteRequest(
        driver_id="driver-slow",
        start_latitude=-23.5300,
        start_longitude=-46.6500,
        departure_time="07:30",
        destinations=[
            WaypointInput(
                destination_id=dest_id,
                name="Doca Especial UUID",
                address="Rua das Flores, 10",
                latitude=-23.5400,
                longitude=-46.6400,
                service_time_minutes=30
            )
        ],
        enable_meal_breaks=False
    )

    response = supervisor.orchestrate_route(request)
    assert response.chronic_docks_prioritized >= 1
    delivery = response.itinerary[1]
    assert delivery.is_slow_dock is True
    assert delivery.slow_dock_warning is not None
    assert delivery.destination_id == dest_id

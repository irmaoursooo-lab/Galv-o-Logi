import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from .dock_profiler import DockProfilerAgent
from .obstacles import ObstacleMonitorAgent
from .router import MathematicalRouterAgent
from .wellness import WellnessAgent
from .copilot import SyntheticVoiceCopilotAgent
from .road_routing import fetch_osrm_road_route
from ..models.schemas import RouteRequest, RouteResponse, ItineraryStop, StopType
from ..models.entities import get_destination_by_id, get_destination_by_id_or_name

class SupervisorOrchestratorAgent:
    """
    Agente 1: Supervisor / Orquestrador Geral
    Coordena a execução em pipeline dos agentes especialistas:
    - Agente 4 (Docas) + Agente 3 (Entraves)
    - Agente 2 (OR-Tools Solver)
    - Agente 5 (Bem-estar / Refeições)
    - Agente 6 (Copiloto Gemini / TTS)
    """

    def __init__(self):
        self.dock_profiler = DockProfilerAgent()
        self.obstacle_monitor = ObstacleMonitorAgent()
        self.router = MathematicalRouterAgent()
        self.wellness = WellnessAgent()
        self.copilot = SyntheticVoiceCopilotAgent()

    def _minutes_to_hhmm(self, total_minutes: int) -> str:
        hh = (total_minutes // 60) % 24
        mm = total_minutes % 60
        return f"{hh:02d}:{mm:02d}"

    def orchestrate_route(self, request: RouteRequest) -> RouteResponse:
        # 1. Estruturar localização de partida
        start_location = {
            "name": request.start_address,
            "address": request.start_address,
            "latitude": request.start_latitude,
            "longitude": request.start_longitude,
            "service_time_minutes": 0
        }

        # 2. Consultar perfil de doca para cada destino (Agente 4)
        dock_profiles: Dict[str, Dict[str, Any]] = {}
        destinations_data = []

        for dest in request.destinations:
            dest_dict = dest.model_dump()
            dest_id = dest.destination_id or dest.name

            # Consultar banco se tiver ID ou nome
            saved_dest = None
            if dest.destination_id:
                saved_dest = get_destination_by_id_or_name(dest.destination_id)
            if not saved_dest and dest.name:
                saved_dest = get_destination_by_id_or_name(dest.name)

            profile = self.dock_profiler.analyze_dock(saved_dest or dest_dict)
            
            # Mapear perfil para todos os identificadores possíveis (ID e Nome)
            dock_profiles[dest_id] = profile
            if dest.name:
                dock_profiles[dest.name] = profile
            if dest.destination_id:
                dock_profiles[dest.destination_id] = profile
            if saved_dest and saved_dest.get("id"):
                dock_profiles[saved_dest["id"]] = profile

            dest_dict["id"] = dest_id
            destinations_data.append(dest_dict)

        # 3. Otimização Matemática com OR-Tools (Agente 2)
        solved = self.router.solve_route(
            start_location=start_location,
            destinations=destinations_data,
            departure_time_str=request.departure_time,
            dock_profiles=dock_profiles,
            preserve_order=getattr(request, "preserve_order", False)
        )

        timeline = solved.get("timeline", [])

        # 4. Inserção de Pausas de Bem-estar (Agente 5) e Montagem do Itinerário
        itinerary: List[ItineraryStop] = []
        planned_meals: List[str] = []
        step_counter = 1
        cumulative_delay_minutes = 0
        last_stop_dep_min = None
        start_dep_min = None
        suggested_meal_info: Optional[Dict[str, Any]] = None

        for idx, entry in enumerate(timeline):
            node_idx = entry["node_index"]

            # Se for o ponto de partida
            if node_idx == 0:
                start_dep_min = entry["departure_minute"]
                arrival_str = self._minutes_to_hhmm(entry["arrival_minute"])
                depart_str = self._minutes_to_hhmm(entry["departure_minute"])
                itinerary.append(ItineraryStop(
                    step_number=0,
                    stop_type=StopType.START,
                    destination_id=None,
                    name=entry["name"],
                    address=entry["address"],
                    latitude=entry["latitude"],
                    longitude=entry["longitude"],
                    arrival_time=arrival_str,
                    departure_time=depart_str,
                    service_duration_minutes=0,
                    distance_from_previous_km=0.0,
                    travel_time_from_previous_minutes=0,
                    notes="Início da Jornada"
                ))
                continue

            # Horário de chegada ajustado acumulando eventuais pausas anteriores
            current_arrival_min = entry["arrival_minute"] + cumulative_delay_minutes
            current_arrival_str = self._minutes_to_hhmm(current_arrival_min)

            # Verificar se cabe pausa para refeição antes desta parada
            meal_break = self.wellness.should_insert_break(current_arrival_str, planned_meals)
            if meal_break:
                meal_type = meal_break["meal"]
                restaurant = self.wellness.recommend_restaurant(meal_type)
                rest_name = restaurant["name"] if restaurant else f"Pausa para {meal_type}"
                rest_addr = restaurant["address"] if restaurant else "Restaurante com pátio para caminhões"
                break_duration = meal_break["duration_minutes"]

                if request.enable_meal_breaks:
                    detour_travel_min = 2 # minutos de aproximação ao restaurante
                    meal_arrival_min = current_arrival_min
                    meal_departure_min = meal_arrival_min + break_duration

                    itinerary.append(ItineraryStop(
                        step_number=0,
                        stop_type=StopType.MEAL_BREAK,
                        destination_id=None,
                        name=rest_name,
                        address=rest_addr,
                        latitude=entry["latitude"] - 0.005, # Proximidade da rota
                        longitude=entry["longitude"] - 0.005,
                        arrival_time=self._minutes_to_hhmm(meal_arrival_min),
                        departure_time=self._minutes_to_hhmm(meal_departure_min),
                        service_duration_minutes=break_duration,
                        distance_from_previous_km=0.8,
                        travel_time_from_previous_minutes=detour_travel_min,
                        meal_type=meal_type,
                        notes=f"Recomendado: Nota {restaurant['rating'] if restaurant else '4.5'} ★ (Estacionamento Seguro)"
                    ))
                    planned_meals.append(meal_type)

                    # Deslocar a linha do tempo das próximas paradas pelo tempo da refeição e deslocamento
                    cumulative_delay_minutes += break_duration + detour_travel_min
                    current_arrival_min = entry["arrival_minute"] + cumulative_delay_minutes
                else:
                    # Sugestão opcional sem alterar nem desviar a rota
                    if not suggested_meal_info:
                        suggested_meal_info = {
                            "meal_type": meal_type,
                            "name": rest_name,
                            "address": rest_addr,
                            "rating": restaurant.get("rating", 4.5) if restaurant else 4.5,
                            "latitude": entry["latitude"] - 0.005,
                            "longitude": entry["longitude"] - 0.005,
                            "arrival_time": current_arrival_str,
                            "duration_minutes": break_duration
                        }

            # Adicionar a entrega com horários ajustados
            serv_duration = entry["service_duration_minutes"]
            idle_wait = entry.get("idle_wait_minutes", 0)
            actual_service_start = current_arrival_min + idle_wait
            actual_depart_min = actual_service_start + serv_duration
            last_stop_dep_min = actual_depart_min

            dest_key_id = entry.get("id")
            dest_key_name = entry.get("name")
            p_info = (
                dock_profiles.get(dest_key_id)
                or dock_profiles.get(dest_key_name)
                or {}
            )
            is_slow = p_info.get("active_slow_dock", False)
            warning_msg = p_info.get("reason") if is_slow else None

            itinerary.append(ItineraryStop(
                step_number=step_counter,
                stop_type=StopType.DELIVERY,
                destination_id=dest_key_id if dest_key_id and dest_key_id != dest_key_name else None,
                name=entry["name"],
                address=entry["address"],
                latitude=entry["latitude"],
                longitude=entry["longitude"],
                arrival_time=self._minutes_to_hhmm(current_arrival_min),
                departure_time=self._minutes_to_hhmm(actual_depart_min),
                service_duration_minutes=serv_duration,
                distance_from_previous_km=entry["distance_from_prev_km"],
                travel_time_from_previous_minutes=entry["travel_time_from_prev_minutes"],
                is_slow_dock=is_slow,
                slow_dock_warning=warning_msg,
                notes=entry.get("notes")
            ))
            step_counter += 1

        # 5. Agente Copiloto (Agente 6): Síntese de Áudio e Briefing
        slow_count = sum(1 for stop in itinerary if stop.is_slow_dock)
        delivery_stops_count = sum(1 for stop in itinerary if stop.stop_type == StopType.DELIVERY)
        
        # Duração total consistente somando paradas e refeições
        if start_dep_min is not None and last_stop_dep_min is not None:
            total_duration_calc = last_stop_dep_min - start_dep_min
        else:
            total_duration_calc = solved.get("total_time_minutes", 0)

        briefing = self.copilot.generate_planning_briefing(
            stops_count=delivery_stops_count,
            total_time_min=total_duration_calc,
            slow_docks_count=slow_count
        )

        last_stop_dep = itinerary[-1].departure_time if itinerary else request.departure_time

        # Obter traçado real da malha viária pelas ruas (OSRM) para eliminar linhas retas
        coords = [(s.latitude, s.longitude) for s in itinerary]
        road_data = fetch_osrm_road_route(coords)
        road_geom = road_data.get("geometry")
        road_dist_km = road_data.get("distance_km")
        is_road_net = road_data.get("is_road_network", True)

        effective_dist = road_dist_km if (road_dist_km and road_dist_km > 0) else solved["total_distance_km"]

        return RouteResponse(
            route_id=str(uuid.uuid4()),
            total_stops=delivery_stops_count,
            total_distance_km=effective_dist,
            total_duration_minutes=total_duration_calc,
            estimated_end_time=last_stop_dep,
            itinerary=itinerary,
            tts_briefing=briefing,
            anti_idle_saved_minutes=solved.get("anti_idle_saved_minutes", 0),
            chronic_docks_prioritized=solved.get("chronic_prioritized_count", 0),
            road_geometry=road_geom,
            is_road_network=is_road_net,
            suggested_meal=suggested_meal_info
        )

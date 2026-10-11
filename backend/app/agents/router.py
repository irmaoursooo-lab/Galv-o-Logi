import math
from typing import List, Dict, Any, Optional, Tuple
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula a distância em linha reta entre duas coordenadas em km."""
    R = 6371.0 # Raio da Terra em km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def estimate_travel_time_minutes(dist_km: float, speed_kmh: Optional[float] = None, obstacle_score: float = 0.0) -> int:
    """
    Estima tempo de viagem em malha urbana/rodoviária com fator de sinuosidade (1.3)
    e velocidade realista dependente da distância (urbana vs rodoviária).
    """
    if speed_kmh is None:
        if dist_km <= 20.0:
            speed_kmh = 32.0  # Vias urbanas locais
        elif dist_km <= 70.0:
            speed_kmh = 50.0  # Anéis viários e periurbano
        else:
            speed_kmh = 75.0  # Rodovias estaduais/federais
    road_km = dist_km * 1.3
    base_hours = road_km / speed_kmh
    base_minutes = base_hours * 60.0
    # Adicionar penalidade de entraves (tráfego/semáforos)
    traffic_penalty = (obstacle_score / 100.0) * (base_minutes * 0.3)
    return max(3, int(round(base_minutes + traffic_penalty)))

class MathematicalRouterAgent:
    """
    Agente 2: Roteirizador Matemático (OR-Tools VRPTW Solver)
    Resolve o Problema de Roteamento de Veículos com Múltiplas Paradas, Janelas de Tempo,
    Priorização de Docas Crônicas e Regra Anti-Ociosidade.
    """

    def __init__(self, max_idle_wait_minutes: int = 25):
        self.max_idle_wait_minutes = max_idle_wait_minutes

    def build_time_matrix(
        self,
        locations: List[Dict[str, Any]],
        obstacle_scores: Optional[Dict[Tuple[int, int], float]] = None
    ) -> List[List[int]]:
        """Gera a matriz de tempos N x N em minutos inteiros."""
        n = len(locations)
        matrix = [[0 for _ in range(n)] for _ in range(n)]
        obstacle_scores = obstacle_scores or {}

        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 0
                else:
                    dist = haversine_distance_km(
                        locations[i]["latitude"], locations[i]["longitude"],
                        locations[j]["latitude"], locations[j]["longitude"]
                    )
                    score = obstacle_scores.get((i, j), 15.0)
                    matrix[i][j] = estimate_travel_time_minutes(dist, obstacle_score=score)
        return matrix

    def solve_route(
        self,
        start_location: Dict[str, Any],
        destinations: List[Dict[str, Any]],
        departure_time_str: str = "07:30",
        dock_profiles: Optional[Dict[str, Dict[str, Any]]] = None,
        preserve_order: bool = False
    ) -> Dict[str, Any]:
        """
        Executa a otimização matemática via OR-Tools considerando:
        1. Local de saída (depósito/garagem) como nó 0
        2. Janelas de atendimento e tempo de serviço
        3. Priorização de docas lentas crônicas para as primeiras paradas
        4. Regra anti-ociosidade (limita espera artificial a <= 25 min)
        5. preserve_order: quando True, mantém a sequência manual definida pelo motorista
        """
        dock_profiles = dock_profiles or {}
        
        # Separar nós: nó 0 é o início
        all_nodes = [start_location] + destinations
        num_nodes = len(all_nodes)
        if num_nodes <= 1:
            return {"sequence": [0], "total_distance_km": 0.0, "total_time_minutes": 0, "node_timeline": []}

        time_matrix = self.build_time_matrix(all_nodes)

        # Converter hora de saída para minutos do dia
        dep_h, dep_m = map(int, departure_time_str.split(":"))
        dep_start_min = dep_h * 60 + dep_m

        # Service times (inflacionados se doca for lenta)
        service_times = [0] # Nó 0 não tem tempo de descarga
        time_windows = [(dep_start_min, dep_start_min)] # Depósito com partida no horário estipulado

        chronic_nodes = []
        anti_idle_relaxed_nodes = {}

        for idx, dest in enumerate(destinations, start=1):
            dest_id = dest.get("id") or dest.get("name")
            profile = dock_profiles.get(dest_id, {})
            
            base_service = dest.get("service_time_minutes", 30)
            inflated = profile.get("inflated_service_minutes", 0)
            service_times.append(base_service + inflated)

            # Janela de tempo
            if profile.get("classification") == "CHRONIC_SLOW":
                chronic_nodes.append(idx)
                # Doca crônica tem prioridade matinal
                time_windows.append((dep_start_min, dep_start_min + 180)) # primeiras 3h
            elif profile.get("classification") == "TIME_WINDOW_SLOW" and profile.get("preferred_window"):
                pref_start, pref_end = profile["preferred_window"]
                ps_h, ps_m = map(int, pref_start.split(":"))
                pe_h, pe_m = map(int, pref_end.split(":"))
                pref_start_min = ps_h * 60 + ps_m
                pref_end_min = pe_h * 60 + pe_m

                # Estimar chegada mais cedo a partir do depósito
                earliest_arrival_min = dep_start_min + time_matrix[0][idx]
                idle_gap = max(0, pref_start_min - earliest_arrival_min)

                # Regra Anti-Ociosidade: Se esperar pela janela requerer > max_idle_wait_minutes,
                # não cria tempo ocioso artificial, permitindo atendimento fluido contínuo.
                if idle_gap > self.max_idle_wait_minutes:
                    time_windows.append((dep_start_min, 22 * 60))
                    anti_idle_relaxed_nodes[idx] = idle_gap
                else:
                    time_windows.append((pref_start_min, pref_end_min))
            else:
                time_windows.append((dep_start_min, 22 * 60))

        # Se o usuário solicitou manter sua sequência manual exata
        if preserve_order:
            manual_sequence = list(range(len(all_nodes)))
            return self._build_sequence_solution(
                all_nodes, time_matrix, service_times, dep_start_min, manual_sequence, chronic_nodes
            )

        # Configurar modelo OR-Tools
        manager = pywrapcp.RoutingIndexManager(num_nodes, 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            # Tempo de viagem + tempo de serviço no nó de origem
            return time_matrix[from_node][to_node] + service_times[from_node]

        transit_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        # Adicionar dimensão de Tempo com horizonte amplo (7 dias) para rotas municipais e interestaduais
        max_horizon_minutes = 7 * 24 * 60
        time_dimension_name = "Time"
        routing.AddDimension(
            transit_callback_index,
            24 * 60,                # slack máximo (espera máxima permitida)
            max_horizon_minutes,    # capacidade máxima (até 7 dias de horizonte)
            False,                  # start cumul to zero
            time_dimension_name
        )
        time_dimension = routing.GetDimensionOrDie(time_dimension_name)

        # Adicionar janelas de atendimento sem AddDisjunction (todas as paradas de entrega são obrigatórias)
        for node_idx, (w_start, w_end) in enumerate(time_windows):
            index = manager.NodeToIndex(node_idx)
            if node_idx == 0:
                time_dimension.CumulVar(index).SetRange(w_start, w_end)
            else:
                # Permitir atendimento desde a saída até o horizonte
                time_dimension.CumulVar(index).SetRange(dep_start_min, max_horizon_minutes)
                # Aplicar soft upper bound na janela de preferência/fechamento para priorização sem descarte
                if w_end < max_horizon_minutes:
                    time_dimension.SetCumulVarSoftUpperBound(index, w_end, 100)

        # Se houver nós crônicos, penalizar atendimento tardio para prioridade matinal
        for c_node in chronic_nodes:
            c_index = manager.NodeToIndex(c_node)
            time_dimension.SetCumulVarSoftUpperBound(c_index, dep_start_min + 180, 500)

        # Parâmetros de busca
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 2

        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            # Fallback seguro: ordenação direta
            return self._fallback_solution(all_nodes, time_matrix, service_times, dep_start_min, chronic_nodes)

        # Extrair itinerário resolvido
        route_sequence = []
        timeline = []
        index = routing.Start(0)
        current_clock = dep_start_min
        prev_node = 0
        total_dist_km = 0.0
        anti_idle_saved = 0

        while not routing.IsEnd(index):
            node_idx = manager.IndexToNode(index)
            route_sequence.append(node_idx)
            node_data = all_nodes[node_idx]

            travel_min = time_matrix[prev_node][node_idx] if len(route_sequence) > 1 else 0
            if prev_node != node_idx:
                dist_km = haversine_distance_km(
                    all_nodes[prev_node]["latitude"], all_nodes[prev_node]["longitude"],
                    node_data["latitude"], node_data["longitude"]
                ) * 1.3
                total_dist_km += dist_km
            else:
                dist_km = 0.0

            arrival_min = current_clock + travel_min
            
            # Anti-Idle Safeguard:
            # Se a janela requerer espera > max_idle_wait_minutes, não congelar motorista
            w_start, _ = time_windows[node_idx]
            wait_min = max(0, w_start - arrival_min)
            if node_idx in anti_idle_relaxed_nodes:
                anti_idle_saved += anti_idle_relaxed_nodes[node_idx]
                actual_service_start = arrival_min
                actual_idle_wait = 0
            elif wait_min > self.max_idle_wait_minutes:
                # Priorizar fluidez contínua: atende imediatamente ou relaxa janela
                anti_idle_saved += wait_min
                actual_service_start = arrival_min
                actual_idle_wait = 0
            else:
                actual_service_start = arrival_min + wait_min
                actual_idle_wait = wait_min

            serv_duration = service_times[node_idx]
            depart_min = actual_service_start + serv_duration
            current_clock = depart_min
            prev_node = node_idx

            timeline.append({
                "node_index": node_idx,
                "id": node_data.get("id") or node_data.get("destination_id"),
                "name": node_data.get("name", "Destino"),
                "address": node_data.get("address", ""),
                "latitude": node_data["latitude"],
                "longitude": node_data["longitude"],
                "travel_time_from_prev_minutes": travel_min,
                "distance_from_prev_km": round(dist_km, 1),
                "arrival_minute": arrival_min,
                "service_start_minute": actual_service_start,
                "departure_minute": depart_min,
                "service_duration_minutes": serv_duration,
                "idle_wait_minutes": actual_idle_wait,
                "is_chronic_prioritized": node_idx in chronic_nodes
            })

            index = solution.Value(routing.NextVar(index))

        # Garantir que 100% dos nós foram visitados; se algum nó foi omitido, recorrer a fallback seguro
        if len(route_sequence) < num_nodes:
            return self._fallback_solution(all_nodes, time_matrix, service_times, dep_start_min, chronic_nodes)

        total_time = current_clock - dep_start_min

        return {
            "sequence": route_sequence,
            "total_distance_km": round(total_dist_km, 1),
            "total_time_minutes": total_time,
            "anti_idle_saved_minutes": anti_idle_saved,
            "chronic_prioritized_count": len(chronic_nodes),
            "timeline": timeline
        }

    def _build_sequence_solution(
        self,
        all_nodes: List[Dict[str, Any]],
        time_matrix: List[List[int]],
        service_times: List[int],
        dep_start_min: int,
        sequence: List[int],
        chronic_nodes: List[int]
    ) -> Dict[str, Any]:
        """Gera a linha do tempo exata para uma sequência de nós pré-determinada."""
        timeline = []
        current_clock = dep_start_min
        total_dist = 0.0

        for i in range(len(sequence)):
            node_idx = sequence[i]
            prev_idx = sequence[i-1] if i > 0 else 0
            node_data = all_nodes[node_idx]

            travel_min = time_matrix[prev_idx][node_idx] if i > 0 else 0
            dist_km = haversine_distance_km(
                all_nodes[prev_idx]["latitude"], all_nodes[prev_idx]["longitude"],
                node_data["latitude"], node_data["longitude"]
            ) * 1.3 if i > 0 else 0.0
            total_dist += dist_km

            arrival = current_clock + travel_min
            duration = service_times[node_idx]
            depart = arrival + duration
            current_clock = depart

            timeline.append({
                "node_index": node_idx,
                "id": node_data.get("id") or node_data.get("destination_id"),
                "name": node_data.get("name", "Destino"),
                "address": node_data.get("address", ""),
                "latitude": node_data["latitude"],
                "longitude": node_data["longitude"],
                "travel_time_from_prev_minutes": travel_min,
                "distance_from_prev_km": round(dist_km, 1),
                "arrival_minute": arrival,
                "service_start_minute": arrival,
                "departure_minute": depart,
                "service_duration_minutes": duration,
                "idle_wait_minutes": 0,
                "is_chronic_prioritized": node_idx in chronic_nodes
            })

        return {
            "sequence": sequence,
            "total_distance_km": round(total_dist, 1),
            "total_time_minutes": current_clock - dep_start_min,
            "anti_idle_saved_minutes": 0,
            "chronic_prioritized_count": len(chronic_nodes),
            "timeline": timeline
        }

    def _fallback_solution(
        self,
        all_nodes: List[Dict[str, Any]],
        time_matrix: List[List[int]],
        service_times: List[int],
        dep_start_min: int,
        chronic_nodes: List[int]
    ) -> Dict[str, Any]:
        """Algoritmo ganancioso de contingência caso solver de restrições falhe."""
        unvisited = list(range(1, len(all_nodes)))
        sorted_unvisited = [n for n in chronic_nodes if n in unvisited] + [n for n in unvisited if n not in chronic_nodes]
        sequence = [0] + sorted_unvisited
        return self._build_sequence_solution(
            all_nodes, time_matrix, service_times, dep_start_min, sequence, chronic_nodes
        )

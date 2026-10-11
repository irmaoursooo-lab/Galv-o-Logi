from typing import Dict, Any, List, Optional
from ..models.schemas import TruckBase, ObstacleAnalysis

class ObstacleMonitorAgent:
    """
    Agente 3: Monitor de Entraves & Malha Viária
    Calcula o Obstacle Penalty Score com base em tráfego, vias estreitas, semáforos
    e restrições físicas de altura/peso do caminhão. Dispara reroteamento quando a
    economia for >= 4 minutos.
    """

    def __init__(
        self,
        w_congestion: float = 0.40,
        w_narrow: float = 0.25,
        w_signals: float = 0.20,
        w_crowd: float = 0.15,
        reroute_threshold_minutes: int = 4
    ):
        self.w1 = w_congestion
        self.w2 = w_narrow
        self.w3 = w_signals
        self.w4 = w_crowd
        self.reroute_threshold = reroute_threshold_minutes

    def check_clearance(
        self,
        truck: Optional[TruckBase],
        segment_max_height: Optional[float] = None,
        segment_max_weight: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Verifica se o porte do veículo é compatível com a infraestrutura da via.
        """
        if not truck:
            return {"allowed": True, "reason": "Sem perfil de caminhão especificado"}

        if segment_max_height is not None and truck.height_meters > segment_max_height:
            return {
                "allowed": False,
                "violation": "HEIGHT_LIMIT",
                "reason": f"Alerta Crítico: Caminhão com {truck.height_meters:.2f}m excede altura máxima de {segment_max_height:.2f}m da ponte/viaduto."
            }

        if segment_max_weight is not None and truck.gross_weight_tonnes > segment_max_weight:
            return {
                "allowed": False,
                "violation": "WEIGHT_LIMIT",
                "reason": f"Alerta Crítico: Peso bruto de {truck.gross_weight_tonnes:.1f}t excede capacidade de {segment_max_weight:.1f}t da via."
            }

        return {"allowed": True, "reason": "Dimensões e peso compatíveis."}

    def calculate_obstacle_score(
        self,
        congestion_index: float,     # 0.0 (livre) a 1.0 (parado)
        narrow_street_index: float,  # 0.0 (larga) a 1.0 (residencial estreita)
        traffic_signals_count: int,  # número de semáforos no trecho
        crowd_hazard_reports: int    # alertas de buracos/reclamações na via
    ) -> float:
        """
        Score = w1 * Congestion + w2 * ViasEstreitas + w3 * SemaforosNormalizados + w4 * Historico
        """
        norm_signals = min(1.0, traffic_signals_count / 10.0)
        norm_crowd = min(1.0, crowd_hazard_reports / 5.0)

        raw_score = (
            self.w1 * congestion_index +
            self.w2 * narrow_street_index +
            self.w3 * norm_signals +
            self.w4 * norm_crowd
        )
        return round(min(1.0, raw_score) * 100, 1)

    def analyze_segment(
        self,
        segment_from: str,
        segment_to: str,
        truck: Optional[TruckBase] = None,
        congestion_index: float = 0.2,
        narrow_street_index: float = 0.0,
        traffic_signals_count: int = 2,
        crowd_hazard_reports: int = 0,
        current_travel_time_min: int = 20,
        alternative_travel_time_min: Optional[int] = None,
        segment_max_height: Optional[float] = None,
        segment_max_weight: Optional[float] = None
    ) -> ObstacleAnalysis:
        clearance = self.check_clearance(truck, segment_max_height, segment_max_weight)
        score = self.calculate_obstacle_score(
            congestion_index,
            narrow_street_index,
            traffic_signals_count,
            crowd_hazard_reports
        )

        alternative_available = False
        time_saved = 0
        alert_msg = None
        tts_alert = None

        if not clearance["allowed"]:
            # Bloqueio físico - desvio obrigatório
            alternative_available = True
            time_saved = 0
            violation = clearance.get("violation")
            if violation == "WEIGHT_LIMIT":
                weight_str = f"{segment_max_weight:.1f}t" if segment_max_weight is not None else "peso restrito"
                alert_msg = f"⛔ LIMITE DE PESO EXCEDIDO ({weight_str}). Desvio obrigatório."
                tts_alert = "Atenção: limite de peso na via. Siga a nova rota imediatamente."
            else:
                height_str = f"{segment_max_height:.2f}m" if segment_max_height is not None else "altura restrita"
                alert_msg = f"⛔ VIADUTO BAIXO À FRENTE ({height_str}). Desvio obrigatório."
                tts_alert = "Atenção: viaduto baixo à frente. Siga a nova rota imediatamente."
        elif alternative_travel_time_min is not None:
            time_saved = current_travel_time_min - alternative_travel_time_min
            if time_saved >= self.reroute_threshold:
                alternative_available = True
                alert_msg = f"🚗🚗 Trânsito Lento à Frente ⚡ ECONOMIZA {time_saved} MIN"
                tts_alert = f"Nova rota economiza {time_saved} minutos. Toque em Aceitar ou apenas vire na próxima rua."

        return ObstacleAnalysis(
            segment_from=segment_from,
            segment_to=segment_to,
            congestion_level=congestion_index,
            narrow_street_penalty=narrow_street_index,
            traffic_signals_count=traffic_signals_count,
            truck_clearance_ok=clearance["allowed"],
            obstacle_score=score,
            alternative_available=alternative_available,
            alternative_time_saved_minutes=max(0, time_saved),
            alert_message=alert_msg,
            tts_audio_alert=tts_alert
        )

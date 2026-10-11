import math
from typing import Dict, Any, List, Optional
from ..models.entities import get_destination_by_id, get_slow_reports

class DockProfilerAgent:
    """
    Agente 4: Perfilador de Recebimento Lento (Doca Profiler)
    Analisa dados colaborativos reportados por motoristas para classificar docas
    em Lento Crônico vs Lento por Horário e aplicar ajustes nas janelas de entrega.
    """

    def __init__(self, min_reports_threshold: int = 2):
        self.min_reports_threshold = min_reports_threshold

    def analyze_dock(self, destination: Dict[str, Any], reports: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Classifica o destino e retorna recomendações para o otimizador de rota.
        """
        dest_id = destination.get("id")
        if reports is None and dest_id:
            reports = get_slow_reports(dest_id)
        elif reports is None:
            reports = []

        total_reports = len(reports) if reports else destination.get("total_slow_reports", 0)

        # Regra 1: Critério de ativação: >= 2 apontamentos
        if total_reports < self.min_reports_threshold:
            return {
                "active_slow_dock": False,
                "classification": "NORMAL",
                "recommended_placement": "STANDARD",
                "inflated_service_minutes": 0,
                "avoid_windows": [],
                "preferred_window": None,
                "reason": "Menos de 2 apontamentos de lentidão registrados."
            }

        # Extrair horários dos relatórios
        hour_counts = {}
        excess_minutes = []
        for r in reports:
            excess = r.get("excess_wait_minutes", 30)
            excess_minutes.append(excess)
            time_str = r.get("time_of_day", "")
            try:
                hh = int(time_str.split(":")[0])
                hour_counts[hh] = hour_counts.get(hh, 0) + 1
            except Exception:
                pass

        avg_excess = round(sum(excess_minutes) / len(excess_minutes), 1) if excess_minutes else 30.0

        # Checar dispersão temporal
        if hour_counts:
            hours = list(hour_counts.keys())
            span = max(hours) - min(hours)
            is_chronic = span >= 5 or total_reports >= 4 and len(hours) >= 3
        else:
            is_chronic = bool(destination.get("is_chronic_slow", False))

        if is_chronic:
            return {
                "active_slow_dock": True,
                "classification": "CHRONIC_SLOW",
                "recommended_placement": "EARLY_MORNING",
                "priority_rank": 1, # Colocar nas primeiras paradas
                "inflated_service_minutes": int(avg_excess),
                "avoid_windows": [],
                "preferred_window": ("07:30", "10:30"),
                "reason": f"Lentidão crônica ({total_reports} registros, ~{int(avg_excess)}min de espera). Priorizar no início da rota para evitar contaminação do dia."
            }
        else:
            # Concentrado em janela específica
            peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 12
            avoid_start = f"{max(0, peak_hour - 1):02d}:00"
            avoid_end = f"{min(23, peak_hour + 2):02d}:00"

            return {
                "active_slow_dock": True,
                "classification": "TIME_WINDOW_SLOW",
                "recommended_placement": "FAVORABLE_WINDOW",
                "priority_rank": 2,
                "inflated_service_minutes": int(avg_excess),
                "avoid_windows": [(avoid_start, avoid_end)],
                "preferred_window": (f"{avoid_end}", "18:00") if peak_hour <= 12 else ("08:00", f"{avoid_start}"),
                "reason": f"Lentidão concentrada entre {avoid_start} e {avoid_end} (troca de turno/almoço). Recomenda-se entregar fora dessa faixa."
            }

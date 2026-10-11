from typing import List, Dict, Any, Optional
from datetime import datetime, time

class WellnessAgent:
    """
    Agente 5: Bem-estar e Refeições (Driver Lifestyle Agent)
    Agenda pausas para refeições (café da manhã, almoço, lanche, jantar)
    e recomenda pontos de alimentação com avaliação >= 4.0 estrelas.
    """

    DEFAULT_WINDOWS = [
        {
            "meal": "CAFÉ DA MANHÃ",
            "start": "07:30",
            "end": "08:30",
            "duration_minutes": 30,
            "required": False
        },
        {
            "meal": "ALMOÇO",
            "start": "11:45",
            "end": "13:30",
            "duration_minutes": 50,
            "required": True
        },
        {
            "meal": "LANCHE DA TARDE",
            "start": "16:00",
            "end": "17:00",
            "duration_minutes": 20,
            "required": False
        },
        {
            "meal": "JANTAR",
            "start": "19:30",
            "end": "21:00",
            "duration_minutes": 45,
            "required": False
        }
    ]

    # Amostra de restaurantes verificados (nota >= 4.0 e amplo pátio para caminhões)
    MOCK_RESTAURANTS = [
        {
            "name": "Restaurante Churrascaria Fogão Gaúcho",
            "address": "Auto Posto Rodoviário com Pátio Seguro",
            "rating": 4.7,
            "reviews_count": 842,
            "truck_parking": True,
            "distance_from_route_meters": 800,
            "meal_type": "ALMOÇO"
        },
        {
            "name": "Auto Posto & Restaurante Graal",
            "address": "Parada Rodoviária com Estacionamento de Cargas",
            "rating": 4.6,
            "reviews_count": 1520,
            "truck_parking": True,
            "distance_from_route_meters": 300,
            "meal_type": "ALMOÇO"
        },
        {
            "name": "Cantina do Estradeiro",
            "address": "Restaurante de Apoio e Refeição ao Motorista",
            "rating": 4.4,
            "reviews_count": 310,
            "truck_parking": True,
            "distance_from_route_meters": 650,
            "meal_type": "JANTAR"
        },
        {
            "name": "Padaria & Café Ponto Certo",
            "address": "Ponto de Apoio e Café da Manhã na Rota",
            "rating": 4.5,
            "reviews_count": 190,
            "truck_parking": True,
            "distance_from_route_meters": 450,
            "meal_type": "CAFÉ DA MANHÃ"
        },
        {
            "name": "Lanchonete Parada Obrigatória",
            "address": "Área de Descanso e Alimentação Segura",
            "rating": 4.3,
            "reviews_count": 420,
            "truck_parking": True,
            "distance_from_route_meters": 500,
            "meal_type": "LANCHE DA TARDE"
        }
    ]

    def should_insert_break(self, current_time_str: str, planned_breaks_done: List[str]) -> Optional[Dict[str, Any]]:
        """
        Determina se o horário atual coincide com a janela de alguma refeição ainda não realizada.
        """
        try:
            ch, cm = map(int, current_time_str.split(":"))
            current_min = ch * 60 + cm
        except Exception:
            return None

        for window in self.DEFAULT_WINDOWS:
            meal = window["meal"]
            if meal in planned_breaks_done:
                continue

            sh, sm = map(int, window["start"].split(":"))
            eh, em = map(int, window["end"].split(":"))
            start_min = sh * 60 + sm
            end_min = eh * 60 + em

            if start_min <= current_min <= end_min:
                return window

        return None

    def recommend_restaurant(self, meal_type: Optional[str] = "ALMOÇO", max_distance_meters: int = 2000) -> Optional[Dict[str, Any]]:
        """
        Filtra restaurantes próximos da rota com avaliação >= 4.0 e estacionamento para caminhões,
        priorizando o tipo de refeição adequado (café da manhã, almoço, lanche, jantar).
        """
        all_candidates = [
            r for r in self.MOCK_RESTAURANTS 
            if r["rating"] >= 4.0 and r["truck_parking"] and r["distance_from_route_meters"] <= max_distance_meters
        ]
        if not all_candidates:
            return None

        # Priorizar pelo tipo de refeição solicitado
        matching_meal = [
            r for r in all_candidates
            if meal_type is None or r.get("meal_type") == meal_type or r.get("meal_type") == "REFEIÇÃO"
        ]

        candidates = matching_meal if matching_meal else all_candidates

        # Priorizar por avaliação e proximidade
        best = max(candidates, key=lambda x: (x["rating"], -x["distance_from_route_meters"]))
        return best

import pytest
from app.agents.wellness import WellnessAgent

def test_meal_break_window_detection():
    agent = WellnessAgent()

    # Horário de almoço (12:15)
    break_info = agent.should_insert_break("12:15", planned_breaks_done=[])
    assert break_info is not None
    assert break_info["meal"] == "ALMOÇO"
    assert break_info["duration_minutes"] >= 45

    # Horário fora de janela (14:30)
    outside = agent.should_insert_break("14:30", planned_breaks_done=[])
    assert outside is None

    # Horário de almoço já realizado
    already_done = agent.should_insert_break("12:30", planned_breaks_done=["ALMOÇO"])
    assert already_done is None

def test_restaurant_recommendation():
    agent = WellnessAgent()
    rest = agent.recommend_restaurant(meal_type="ALMOÇO", max_distance_meters=2000)
    
    assert rest is not None
    assert rest["rating"] >= 4.0
    assert rest["truck_parking"] is True
    assert rest["distance_from_route_meters"] <= 2000

def test_restaurant_recommendation_by_meal_type():
    agent = WellnessAgent()
    
    # Café da manhã deve retornar padaria/café, não churrascaria
    breakfast = agent.recommend_restaurant(meal_type="CAFÉ DA MANHÃ")
    assert breakfast is not None
    assert breakfast["meal_type"] == "CAFÉ DA MANHÃ"
    assert "Padaria" in breakfast["name"] or "Café" in breakfast["name"]

    # Lanche da tarde deve retornar lanchonete
    snack = agent.recommend_restaurant(meal_type="LANCHE DA TARDE")
    assert snack is not None
    assert snack["meal_type"] == "LANCHE DA TARDE"

    # Jantar deve retornar jantar
    dinner = agent.recommend_restaurant(meal_type="JANTAR")
    assert dinner is not None
    assert dinner["meal_type"] == "JANTAR"

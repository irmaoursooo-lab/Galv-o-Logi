import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agents.geocoder import (
    GeocodingAgent,
    extract_query_house_number,
    interpolate_street_number,
    format_osm_address,
)

client = TestClient(app)

def test_extract_query_house_number():
    """Testa a extração precisa do número predial sem confundir com CEPs ou rodovias."""
    num, street = extract_query_house_number("rua padre americo ceppi 806")
    assert num == "806"
    assert "rua padre americo ceppi" in street

    num, street = extract_query_house_number("rua padre americo ceppi, 806, Uberlândia - MG")
    assert num == "806"
    assert "rua padre americo ceppi" in street

    num, street = extract_query_house_number("Av. Afonso Pena, nº 1500, Uberlândia")
    assert num == "1500"

    num, street = extract_query_house_number("Rua Padre Américo Ceppi 806 CEP 38400-000")
    assert num == "806"

    # Não deve extrair número em buscas de estabelecimentos sem número predial
    num, street = extract_query_house_number("bernardao patos de minas")
    assert num is None

    # Não deve confundir doca/box com número predial
    num, street = extract_query_house_number("ceasa minas doca 3")
    assert num is None


def test_format_osm_address_preserves_number():
    """Testa se format_osm_address preserva o número predial e não adiciona CEPs fixos conflitantes."""
    props = {
        "name": "Rua Padre Américo Ceppi",
        "street": "Rua Padre Américo Ceppi",
        "district": "Brasil",
        "city": "Uberlândia",
        "state": "Minas Gerais",
        "country": "Brasil",
        "postcode": "38400-675"
    }
    formatted = format_osm_address(props, house_number="806")
    assert "806" in formatted
    assert "Rua Padre Américo Ceppi, 806" in formatted
    assert "Brasil" in formatted
    assert "Uberlândia" in formatted
    # Não deve poluir o endereço com CEP quando o número predial foi fornecido
    assert "CEP 38400-675" not in formatted


def test_geocoder_preserves_house_number_uberlandia():
    """Testa geocodificação da Rua Padre Américo Ceppi 806 preservando o número no nome e no endereço."""
    agent = GeocodingAgent()
    places = agent.search_places("rua padre americo ceppi 806", limit=4)
    assert len(places) >= 1
    top = places[0]

    assert "806" in top["name"]
    assert "806" in top["address"]
    # Coordenadas devem estar em Uberlândia/MG
    assert -19.2 <= top["latitude"] <= -18.6
    assert -48.5 <= top["longitude"] <= -48.0

    # Geocode direto também deve preservar o número
    res = agent.geocode("rua padre americo ceppi 806")
    assert "806" in res["name"]
    assert "806" in res["address"]


def test_api_search_places_house_number():
    """Testa a API /api/v1/routes/search-places com número predial informado."""
    response = client.get("/api/v1/routes/search-places?q=rua+padre+americo+ceppi+806&limit=3")
    assert response.status_code == 200
    places = response.json()
    assert len(places) >= 1
    top = places[0]
    assert "806" in top["name"]
    assert "806" in top["address"]
    assert -19.2 <= top["latitude"] <= -18.6
    assert -48.5 <= top["longitude"] <= -48.0

    # Não deve retornar sugestões duplicadas idênticas da mesma rua com o mesmo número
    unique_addrs = set(p["address"].lower() for p in places)
    assert len(unique_addrs) == len(places)


def test_api_multi_addresses_preserves_house_number():
    """Testa se /api/v1/routes/multi-addresses preserva o número predial no nome e endereço."""
    # Teste via addresses_text
    res_text = client.post("/api/v1/routes/multi-addresses", json={
        "addresses_text": "Rua Padre Américo Ceppi, 806\nMercado Central Uberlândia"
    })
    assert res_text.status_code == 200
    waypoints_text = res_text.json()
    assert len(waypoints_text) == 2
    stop_ceppi = waypoints_text[0]
    assert "806" in stop_ceppi["name"]
    assert "806" in stop_ceppi["address"]

    # Teste via addresses_list
    res_list = client.post("/api/v1/routes/multi-addresses", json={
        "addresses_list": ["Rua Padre Américo Ceppi, 806"]
    })
    assert res_list.status_code == 200
    waypoints_list = res_list.json()
    assert len(waypoints_list) == 1
    assert "806" in waypoints_list[0]["name"]
    assert "806" in waypoints_list[0]["address"]


def test_optimize_route_preserves_house_number_in_itinerary():
    """Testa se /api/v1/routes/optimize mantém o número predial no itinerário final."""
    payload = {
        "driver_id": "test-driver",
        "start_latitude": -18.9186,
        "start_longitude": -48.2772,
        "start_address": "Centro de Operações Uberlândia",
        "departure_time": "07:30",
        "destinations": [
            {
                "name": "Rua Padre Américo Ceppi, 806",
                "address": "Rua Padre Américo Ceppi, 806, Brasil, Uberlândia - MG",
                "latitude": -18.89043,
                "longitude": -48.258618,
                "service_time_minutes": 30
            }
        ]
    }
    response = client.post("/api/v1/routes/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["itinerary"]) >= 2
    delivery = [s for s in data["itinerary"] if s["stop_type"] == "DELIVERY"][0]
    assert "806" in delivery["name"]
    assert "806" in delivery["address"]
    assert "road_geometry" in data
    assert data["road_geometry"] is not None


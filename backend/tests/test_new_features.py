import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agents.road_routing import fetch_osrm_road_route, haversine_km
from app.agents.document_ocr import purge_sensitive_data, DocumentOcrAgent
from app.agents.geocoder import GeocodingAgent, clean_search_query
from app.models.schemas import RouteRequest, WaypointInput

client = TestClient(app)

def test_sensitive_data_purging_lgpd():
    """Testa se dados fiscais e pessoais sensíveis são completamente purgados conforme LGPD."""
    sensitive_invoice_text = (
        "NF-e Emitente: Distribuidora XPTO Ltda CNPJ: 12.345.678/0001-99 "
        "Destinatário: Mercado Compre Bem CPF: 987.654.321-00 "
        "Endereço: Rua das Flores, 120, Bairro Jardim, Contagem - MG, 32000-000 "
        "Chave de Acesso: 35210912345678000190550010000001231000001234 "
        "Valor Total da Nota: R$ 4.520,00 50 CX 20 KG "
        "Inscrição Estadual: 123.456.789.000"
    )
    
    purged = purge_sensitive_data(sensitive_invoice_text)
    
    # Validações de exclusão total de dados confidenciais
    assert "987.654.321-00" not in purged, "CPF não foi purgado!"
    assert "12.345.678/0001-99" not in purged, "CNPJ não foi purgado!"
    assert "35210912345678000190550010000001231000001234" not in purged, "Chave NF-e não foi purgada!"
    assert "R$" not in purged, "Símbolo monetário não foi purgado!"
    assert "4.520,00" not in purged, "Preço da nota não foi purgado!"
    assert "50 CX" not in purged, "Quantidade/unidade não foi purgada!"
    assert "20 KG" not in purged, "Unidade KG não foi purgada!"
    
    # Endereço e estabelecimento devem ser preservados
    assert "Mercado Compre Bem" in purged
    assert "Rua das Flores" in purged

def test_document_ocr_agent_multiple_addresses_text():
    """Testa extração de destinos a partir de texto com múltiplos endereços."""
    ocr_agent = DocumentOcrAgent()
    sample_text = (
        "Supermercado Guanabara, Barra da Tijuca, Rio de Janeiro\n"
        "Mercado Central de BH, Av. Augusto de Lima, 744, Belo Horizonte\n"
        "Ceasa Minas Pavilhão 5, Contagem - MG"
    )
    results = ocr_agent.parse_multiple_addresses_text(sample_text)
    assert len(results) == 3
    assert "Supermercado Guanabara" in results[0]["name"]
    assert "Mercado Central de BH" in results[1]["name"]
    assert "Ceasa Minas" in results[2]["name"]

def test_geocoding_agent_landmarks_and_batch():
    """Testa geocodificação de estabelecimentos e endereços com cache logístico."""
    geocoder = GeocodingAgent()
    
    # Estabelecimento conhecido no cache logístico
    res = geocoder.geocode("Mercado Central de BH")
    assert res is not None
    assert abs(res["latitude"] - (-19.9230)) < 0.05
    assert abs(res["longitude"] - (-43.9440)) < 0.05
    
    # Lote de múltiplos estabelecimentos
    batch = geocoder.geocode_batch([
        "Mercado Central de BH",
        "Ceasa Minas",
        "Hipermercado Tamboré"
    ])
    assert len(batch) == 3
    for item in batch:
        assert "latitude" in item
        assert "longitude" in item
        assert item["latitude"] != 0.0

def test_road_routing_osrm_or_fallback():
    """Testa motor de roteamento viário OSRM para seguir ruas e rodovias reais."""
    # Pontos reais em São Paulo
    coords = [(-23.5300, -46.6500), (-23.5489, -46.6388)]
    res = fetch_osrm_road_route(coords, timeout_seconds=5.0)
    
    assert "geometry" in res
    assert len(res["geometry"]) >= 2
    assert res["distance_km"] > 0
    assert "is_road_network" in res
    
    # Verifica que pontos são pares de [lat, lon]
    first_pt = res["geometry"][0]
    assert len(first_pt) == 2
    assert -90 <= first_pt[0] <= 90
    assert -180 <= first_pt[1] <= 180

def test_api_multi_addresses_endpoint():
    """Testa endpoint de inclusão de múltiplos endereços manuais."""
    payload = {
        "addresses_text": "Mercado Central de BH\nCeasa Minas Pavilhão 5, Contagem",
        "base_latitude": -19.9200,
        "base_longitude": -43.9400
    }
    response = client.post("/api/v1/routes/multi-addresses", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert "Mercado Central" in data[0]["name"]
    assert data[0]["latitude"] != 0.0

def test_api_scan_invoices_endpoint_multipart():
    """Testa endpoint de leitura de nota fiscal via upload multipart em memória."""
    fake_invoice_img = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    
    files = [
        ("files", ("danfe_teste.png", io.BytesIO(fake_invoice_img), "image/png"))
    ]
    response = client.post("/api/v1/routes/scan-invoices", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["sensitive_data_purged"] is True
    assert data["scanned_count"] >= 1
    assert len(data["destinations"]) >= 1

def test_api_optimize_returns_road_geometry():
    """Testa se a resposta de otimização de rota contém a malha viária real (road_geometry)."""
    payload = {
        "driver_id": "test-driver-road",
        "start_latitude": -23.5300,
        "start_longitude": -46.6500,
        "start_address": "Ponto de Partida",
        "departure_time": "08:00",
        "destinations": [
            {
                "name": "Cliente 1",
                "address": "Av. Brasil, 100",
                "latitude": -23.5400,
                "longitude": -46.6400,
                "service_time_minutes": 20
            },
            {
                "name": "Cliente 2",
                "address": "Av. Brasil, 500",
                "latitude": -23.5500,
                "longitude": -46.6300,
                "service_time_minutes": 20
            }
        ],
        "enable_meal_breaks": False
    }
    response = client.post("/api/v1/routes/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "road_geometry" in data
    assert data["road_geometry"] is not None
    assert len(data["road_geometry"]) >= 2
    assert data["is_road_network"] is True

def test_api_search_places_autocomplete():
    """Testa busca em tempo real com autocomplete de estabelecimentos reais."""
    response = client.get("/api/v1/routes/search-places?q=bernardao+patos+de+minas&limit=4")
    assert response.status_code == 200
    places = response.json()
    assert isinstance(places, list)
    assert len(places) >= 1
    first = places[0]
    assert "name" in first
    assert "address" in first
    assert -20.0 <= first["latitude"] <= -17.0  # Região de Patos de Minas / MG
    assert -48.0 <= first["longitude"] <= -45.0

def test_geocoder_uberlandia_accuracy():
    """Testa se rua em Uberlândia é geocodificada corretamente em MG e não cai em SP/Osasco."""
    agent = GeocodingAgent()
    res = agent.geocode("rua padre americo ceppi - uberlandia")
    assert res is not None
    assert "latitude" in res and "longitude" in res
    # Uberlândia está por volta de -18.9, -48.2 (NÃO deve ser -23.5 de São Paulo/Osasco)
    assert -19.2 <= res["latitude"] <= -18.6
    assert -48.5 <= res["longitude"] <= -48.0
    assert "uberlandia" in res["address"].lower() or "uberlândia" in res["address"].lower() or "padre" in res["name"].lower()

def test_route_optimize_preserves_order():
    """Testa se a opção preserve_order mantém a sequência manual de paradas solicitada pelo usuário."""
    payload = {
        "driver_id": "test-preserve",
        "start_latitude": -19.9200,
        "start_longitude": -43.9400,
        "start_address": "Ponto de Partida",
        "departure_time": "08:00",
        "destinations": [
            {
                "name": "Parada Z (Primeira na Ordem Manual)",
                "address": "Local Z",
                "latitude": -19.9500,
                "longitude": -43.9800,
                "service_time_minutes": 25
            },
            {
                "name": "Parada A (Segunda na Ordem Manual)",
                "address": "Local A",
                "latitude": -19.9100,
                "longitude": -43.9300,
                "service_time_minutes": 25
            }
        ],
        "enable_meal_breaks": False,
        "preserve_order": True
    }
    response = client.post("/api/v1/routes/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    delivery_stops = [s for s in data["itinerary"] if s["stop_type"] == "DELIVERY"]
    assert len(delivery_stops) == 2
    assert delivery_stops[0]["name"] == "Parada Z (Primeira na Ordem Manual)"
    assert delivery_stops[1]["name"] == "Parada A (Segunda na Ordem Manual)"

def test_route_optimize_does_not_drop_distant_stops_default_order():
    """Testa que rotas de longa distância NÃO descartam destinos quando preserve_order=False (padrão)."""
    payload = {
        "driver_id": "test-distant-drop-safeguard",
        "start_latitude": -23.5300,
        "start_longitude": -46.6500,
        "start_address": "Ponto de Partida",
        "departure_time": "08:00",
        "destinations": [
            {
                "name": "Rua Padre Américo Ceppi",
                "address": "Uberlândia - MG",
                "latitude": -18.89114,
                "longitude": -48.257575,
                "service_time_minutes": 30
            }
        ],
        "enable_meal_breaks": False,
        "preserve_order": False
    }
    response = client.post("/api/v1/routes/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    delivery_stops = [s for s in data["itinerary"] if s["stop_type"] == "DELIVERY"]
    assert len(delivery_stops) == 1, "Parada distante foi indevidamente descartada pelo solver!"
    assert "Padre" in delivery_stops[0]["name"] or "Uberlândia" in delivery_stops[0]["name"] or "Ceppi" in delivery_stops[0]["name"]

def test_route_optimize_multi_distant_destinations():
    """Testa otimização de rota entre múltiplas cidades de Minas Gerais sem descartar nenhum nó."""
    payload = {
        "driver_id": "test-mg-circuit",
        "start_latitude": -18.9186,
        "start_longitude": -48.2772,
        "start_address": "Base Uberlândia - MG",
        "departure_time": "07:30",
        "destinations": [
            {
                "name": "Bernardão Patos de Minas",
                "address": "Patos de Minas - MG",
                "latitude": -18.5733,
                "longitude": -46.5228,
                "service_time_minutes": 35
            },
            {
                "name": "CD Uberaba",
                "address": "Uberaba - MG",
                "latitude": -19.7472,
                "longitude": -47.9392,
                "service_time_minutes": 30
            }
        ],
        "enable_meal_breaks": False,
        "preserve_order": False
    }
    response = client.post("/api/v1/routes/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    delivery_stops = [s for s in data["itinerary"] if s["stop_type"] == "DELIVERY"]
    assert len(delivery_stops) == 2, "Alguma das paradas em MG foi descartada!"
    assert data["total_distance_km"] > 100.0

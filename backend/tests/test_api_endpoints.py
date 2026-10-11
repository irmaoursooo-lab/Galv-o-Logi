import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_or_index():
    response = client.get("/")
    assert response.status_code == 200

def test_api_optimize_route():
    payload = {
        "driver_id": "driver_api_test",
        "start_latitude": -23.5300,
        "start_longitude": -46.6500,
        "start_address": "Depósito SP",
        "departure_time": "08:00",
        "destinations": [
            {
                "name": "Doca Teste API 1",
                "address": "Rua 1",
                "latitude": -23.5400,
                "longitude": -46.6400,
                "service_time_minutes": 25
            },
            {
                "name": "Doca Teste API 2",
                "address": "Rua 2",
                "latitude": -23.5500,
                "longitude": -46.6300,
                "service_time_minutes": 35
            }
        ],
        "enable_meal_breaks": True
    }

    response = client.post("/api/v1/routes/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "route_id" in data
    assert data["total_stops"] == 2
    assert len(data["itinerary"]) >= 3

def test_api_obstacle_check():
    response = client.post("/api/v1/routes/obstacle-check?segment_from=A&segment_to=B&current_time_minutes=25&alternative_time_minutes=15")
    assert response.status_code == 200
    data = response.json()
    assert data["alternative_available"] is True
    assert data["alternative_time_saved_minutes"] == 10
    assert "tts_audio_alert" in data

def test_api_dock_registration_and_list():
    new_dock = {
        "name": "Doca Nova Teste",
        "address": "Av. Brasil, 500",
        "latitude": -23.5600,
        "longitude": -46.6700
    }
    create_res = client.post("/api/v1/docks/", json=new_dock)
    assert create_res.status_code == 200
    dock_id = create_res.json()["id"]

    # 2-touch slow report
    report_payload = {
        "destination_id": dock_id,
        "driver_id": "d-123",
        "time_of_day": "10:30",
        "excess_wait_minutes": 45
    }
    report_res = client.post("/api/v1/docks/report", json=report_payload)
    assert report_res.status_code == 200
    assert report_res.json()["status"] == "SUCCESS"

def test_api_truck_registration():
    truck_data = {
        "driver_id": "driver-99",
        "plate": "LOG-2026",
        "vehicle_type": "TRUCK",
        "height_meters": 4.15,
        "width_meters": 2.60,
        "length_meters": 14.0,
        "gross_weight_tonnes": 29.0,
        "axle_count": 4
    }
    res = client.post("/api/v1/trucks/", json=truck_data)
    assert res.status_code == 200
    assert res.json()["plate"] == "LOG-2026"

def test_api_sync_batch():
    batch_data = {
        "driver_id": "driver-sync-test",
        "events": [
            {
                "id": "evt-sync-1",
                "event_type": "DELIVERY_COMPLETED",
                "payload": {"stop_number": 1, "completed_at": "09:15"},
                "created_at_local": "2026-10-11T09:15:00",
                "sync_status": "PENDING"
            }
        ]
    }
    res = client.post("/api/v1/sync/batch", json=batch_data)
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    assert "evt-sync-1" in data["synced_ids"]

def test_api_sync_slow_receiving_report_by_name():
    # Cadastrar destino
    new_dock = {
        "name": "Doca Sincronizavel",
        "address": "Av. Marginal, 100",
        "latitude": -23.5100,
        "longitude": -46.6200
    }
    create_res = client.post("/api/v1/docks/", json=new_dock)
    assert create_res.status_code == 200

    # Enviar evento offline apontando lentidão pelo nome do destino
    batch_data = {
        "driver_id": "driver-sync-2",
        "events": [
            {
                "id": "evt-slow-sync",
                "event_type": "SLOW_RECEIVING_REPORT",
                "payload": {
                    "destination_id": "Doca Sincronizavel",
                    "time_of_day": "14:30",
                    "excess_wait_minutes": 55,
                    "driver_notes": "Fila no portão 2"
                },
                "created_at_local": "2026-10-11T14:30:00",
                "sync_status": "PENDING"
            }
        ]
    }
    res = client.post("/api/v1/sync/batch", json=batch_data)
    assert res.status_code == 200
    data = res.json()
    assert data["processed_count"] == 1
    assert "evt-slow-sync" in data["synced_ids"]

    # Verificar que o destino agora tem o apontamento contabilizado
    check_res = client.get("/api/v1/docks/")
    docks = check_res.json()
    target = [d for d in docks if d["name"] == "Doca Sincronizavel"][0]
    assert target["total_slow_reports"] >= 1

import os
import pytest
from app.database import init_db
from app.models.entities import record_offline_event, get_pending_offline_events, mark_offline_event_synced

TEST_DB = "test_offline.db"

@pytest.fixture(autouse=True)
def setup_teardown_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_offline_outbox_queue_cycle():
    # 1. Enfileirar evento desconectado
    record_offline_event(
        event_id="evt_offline_1",
        event_type="SLOW_RECEIVING_REPORT",
        payload={"destination_id": "doca_1", "excess_wait_minutes": 60, "time_of_day": "14:00"},
        created_at_local="2026-10-11T12:00:00",
        sync_status="PENDING",
        db_file=TEST_DB
    )

    pending = get_pending_offline_events(TEST_DB)
    assert len(pending) == 1
    assert pending[0]["id"] == "evt_offline_1"
    assert pending[0]["event_type"] == "SLOW_RECEIVING_REPORT"
    assert pending[0]["payload"]["excess_wait_minutes"] == 60

    # 2. Simular reconexão de rede e sincronização
    mark_offline_event_synced("evt_offline_1", TEST_DB)

    remaining_pending = get_pending_offline_events(TEST_DB)
    assert len(remaining_pending) == 0

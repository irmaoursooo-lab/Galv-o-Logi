from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime

from ..models.schemas import SyncBatchRequest, SyncBatchResponse, OfflineEvent
from ..models.entities import (
    record_offline_event, mark_offline_event_synced, get_pending_offline_events,
    add_slow_report, get_destination_by_id, get_destination_by_id_or_name
)

router = APIRouter(prefix="/sync", tags=["Offline Outbox Synchronization"])

@router.post("/batch", response_model=SyncBatchResponse)
def sync_offline_batch(batch: SyncBatchRequest):
    """
    Sincronização em segundo plano da Fila Outbox (Eventos gravados sem sinal de internet).
    Processa entregas concluídas, relatórios de docas lentas e alertas de rota.
    """
    synced_ids = []
    failed_ids = []

    for event in batch.events:
        try:
            # 1. Registrar na fila local do servidor
            record_offline_event(
                event_id=event.id,
                event_type=event.event_type,
                payload=event.payload,
                created_at_local=event.created_at_local,
                sync_status="PENDING"
            )

            # 2. Executar efeito colateral com base no tipo
            if event.event_type == "SLOW_RECEIVING_REPORT":
                p = event.payload
                dest_id = p.get("destination_id")
                dest_row = get_destination_by_id_or_name(dest_id) if dest_id else None
                if dest_row:
                    add_slow_report(
                        destination_id=dest_row["id"],
                        driver_id=p.get("driver_id", batch.driver_id),
                        time_of_day=p.get("time_of_day", "12:00"),
                        excess_wait_minutes=p.get("excess_wait_minutes", 30),
                        driver_notes=p.get("driver_notes")
                    )

            # 3. Marcar como sincronizado
            mark_offline_event_synced(event.id)
            synced_ids.append(event.id)

        except Exception:
            failed_ids.append(event.id)

    return SyncBatchResponse(
        processed_count=len(synced_ids),
        synced_ids=synced_ids,
        failed_ids=failed_ids,
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/pending")
def list_pending():
    """Retorna eventos locais ainda pendentes de sincronização."""
    return get_pending_offline_events()

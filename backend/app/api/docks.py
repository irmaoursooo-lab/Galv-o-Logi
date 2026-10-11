from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional

from ..models.schemas import (
    DestinationCreate, DestinationResponse, SlowReportCreate, SlowReportResponse
)
from ..models.entities import (
    create_destination, get_destination_by_id, list_all_destinations,
    add_slow_report, get_slow_reports
)
from ..agents.dock_profiler import DockProfilerAgent

router = APIRouter(prefix="/docks", tags=["Docks & Slow Receiving"])
dock_profiler = DockProfilerAgent()

@router.post("/", response_model=DestinationResponse)
def register_destination(dest: DestinationCreate):
    """
    Cadastra um novo destino/doca de carga no banco colaborativo.
    """
    saved = create_destination(
        name=dest.name,
        address=dest.address,
        latitude=dest.latitude,
        longitude=dest.longitude,
        google_place_id=dest.google_place_id
    )
    return DestinationResponse(**saved)

@router.get("/", response_model=List[DestinationResponse])
def list_destinations():
    """
    Lista todos os estabelecimentos cadastrados e o perfil atualizado de lentidão.
    """
    dests = list_all_destinations()
    return [DestinationResponse(**d) for d in dests]

@router.get("/{dest_id}", response_model=DestinationResponse)
def get_destination(dest_id: str):
    dest = get_destination_by_id(dest_id)
    if not dest:
        raise HTTPException(status_code=404, detail="Destino não encontrado")
    return DestinationResponse(**dest)

@router.post("/report")
def submit_slow_receiving_report(report: SlowReportCreate):
    """
    Registro Rápido em 2 Toques:
    Motorista aponta horário do recebimento lento e tempo excedente de espera.
    Destinos com >= 2 avaliações são marcados pelo sistema.
    """
    dest = get_destination_by_id(report.destination_id)
    if not dest:
        raise HTTPException(status_code=404, detail="Destino não encontrado")

    result = add_slow_report(
        destination_id=report.destination_id,
        driver_id=report.driver_id,
        time_of_day=report.time_of_day,
        excess_wait_minutes=report.excess_wait_minutes,
        driver_notes=report.driver_notes
    )

    return {
        "status": "SUCCESS",
        "message": "Apontamento registrado com sucesso.",
        "profiling": result
    }

@router.get("/{dest_id}/analysis")
def analyze_dock_status(dest_id: str):
    """
    Retorna o diagnóstico aprofundado do Agente de Recebimento Lento para esta doca.
    """
    dest = get_destination_by_id(dest_id)
    if not dest:
        raise HTTPException(status_code=404, detail="Destino não encontrado")

    reports = get_slow_reports(dest_id)
    return dock_profiler.analyze_dock(dest, reports)

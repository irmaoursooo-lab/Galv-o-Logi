from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from ..models.schemas import TruckCreate, TruckResponse
from ..models.entities import upsert_truck, get_truck_by_id

router = APIRouter(prefix="/trucks", tags=["Trucks & Dimensions"])

@router.post("/", response_model=TruckResponse)
def register_or_update_truck(truck: TruckCreate):
    """
    Cadastra ou atualiza o perfil do caminhão (altura, peso, eixos, comprimento).
    Esses parâmetros alimentam o Agente de Entraves para barrar viadutos baixos e pontes frágeis.
    """
    saved = upsert_truck(
        driver_id=truck.driver_id,
        plate=truck.plate,
        vehicle_type=truck.vehicle_type.value,
        height_meters=truck.height_meters,
        width_meters=truck.width_meters,
        length_meters=truck.length_meters,
        gross_weight_tonnes=truck.gross_weight_tonnes,
        axle_count=truck.axle_count
    )
    return TruckResponse(**saved)

@router.get("/{truck_id}", response_model=TruckResponse)
def get_truck(truck_id: str):
    t = get_truck_by_id(truck_id)
    if not t:
        raise HTTPException(status_code=404, detail="Caminhão não encontrado")
    return TruckResponse(**t)

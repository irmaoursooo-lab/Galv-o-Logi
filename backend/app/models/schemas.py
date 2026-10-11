from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class VehicleType(str, Enum):
    VUC = "VUC"
    TOCO = "TOCO"
    TRUCK = "TRUCK"
    CARRETA = "CARRETA"
    BITREM = "BITREM"

class TruckBase(BaseModel):
    driver_id: str
    plate: str
    vehicle_type: VehicleType = VehicleType.TRUCK
    height_meters: float = Field(ge=1.5, le=5.0, description="Altura do veículo em metros")
    width_meters: float = Field(ge=1.5, le=3.5, description="Largura do veículo em metros")
    length_meters: float = Field(ge=4.0, le=30.0, description="Comprimento total em metros")
    gross_weight_tonnes: float = Field(ge=1.0, le=80.0, description="Peso bruto total em toneladas (PBT)")
    axle_count: int = Field(ge=2, le=9, description="Número de eixos")

class TruckCreate(TruckBase):
    pass

class TruckResponse(TruckBase):
    id: str
    created_at: str

class DestinationBase(BaseModel):
    name: str
    address: str
    latitude: float
    longitude: float
    google_place_id: Optional[str] = None

class DestinationCreate(DestinationBase):
    pass

class DestinationResponse(DestinationBase):
    id: str
    total_slow_reports: int = 0
    is_chronic_slow: bool = False
    slow_start_time: Optional[str] = None
    slow_end_time: Optional[str] = None
    avg_excess_minutes: float = 0.0
    created_at: str

class SlowReportCreate(BaseModel):
    destination_id: str
    driver_id: str
    time_of_day: str = Field(description="Horário aproximado do recebimento lento no formato HH:MM")
    excess_wait_minutes: int = Field(ge=5, le=480, description="Tempo excedente de espera em minutos")
    driver_notes: Optional[str] = None

class SlowReportResponse(BaseModel):
    id: str
    destination_id: str
    driver_id: str
    report_timestamp: str
    time_of_day: str
    excess_wait_minutes: int
    driver_notes: Optional[str]
    created_at: str

class WaypointInput(BaseModel):
    destination_id: Optional[str] = None
    name: str
    address: str
    latitude: float
    longitude: float
    service_time_minutes: int = 30
    time_window_start: Optional[str] = None # "08:00"
    time_window_end: Optional[str] = None   # "18:00"

class PlaceSuggestion(BaseModel):
    name: str
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: float
    longitude: float
    type: Optional[str] = "establishment"

from datetime import datetime
try:
    import zoneinfo
    BRASILIA_TZ = zoneinfo.ZoneInfo("America/Sao_Paulo")
except Exception:
    BRASILIA_TZ = None

def get_current_brasilia_time_str() -> str:
    if BRASILIA_TZ:
        return datetime.now(BRASILIA_TZ).strftime("%H:%M")
    return datetime.now().strftime("%H:%M")

class RouteRequest(BaseModel):
    driver_id: str
    truck_id: Optional[str] = None
    truck_profile: Optional[TruckBase] = None
    start_latitude: float
    start_longitude: float
    start_address: str = "Garagem / Centro de Distribuição"
    departure_time: str = Field(default_factory=get_current_brasilia_time_str, description="Horário de partida no formato HH:MM (padrão: hora atual de Brasília)")
    destinations: List[WaypointInput]
    enable_meal_breaks: bool = True
    preserve_order: bool = False

class StopType(str, Enum):
    START = "START"
    DELIVERY = "DELIVERY"
    MEAL_BREAK = "MEAL_BREAK"
    END = "END"

class ItineraryStop(BaseModel):
    step_number: int = 0  # 1, 2, 3... para entregas reais (DELIVERY); 0 para início (START) ou pausas de alimentação (MEAL_BREAK)
    stop_type: StopType
    destination_id: Optional[str] = None
    name: str
    address: str
    latitude: float
    longitude: float
    arrival_time: str
    departure_time: str
    service_duration_minutes: int
    distance_from_previous_km: float
    travel_time_from_previous_minutes: int
    is_slow_dock: bool = False
    slow_dock_warning: Optional[str] = None
    meal_type: Optional[str] = None
    notes: Optional[str] = None

class RouteResponse(BaseModel):
    route_id: str
    total_stops: int  # Contagem exclusiva de paradas de entrega/clientes (DELIVERY). Pontos de partida e alimentação não contam.
    total_distance_km: float
    total_duration_minutes: int
    estimated_end_time: str
    itinerary: List[ItineraryStop]
    tts_briefing: str
    anti_idle_saved_minutes: int = 0
    chronic_docks_prioritized: int = 0
    road_geometry: Optional[List[List[float]]] = None
    is_road_network: bool = True
    suggested_meal: Optional[Dict[str, Any]] = None  # Sugestão opcional de refeição exibida ao motorista

class OcrScanResult(BaseModel):
    destinations: List[WaypointInput]
    scanned_count: int
    sensitive_data_purged: bool = True
    notes: Optional[str] = "Dados sensíveis (CPF, CNPJ, valores e produtos) foram descartados com sucesso conforme LGPD."

class MultiAddressInput(BaseModel):
    addresses_text: Optional[str] = None
    addresses_list: Optional[List[str]] = None
    base_latitude: Optional[float] = None
    base_longitude: Optional[float] = None

class RoadDirectionsRequest(BaseModel):
    coordinates: List[List[float]] # [[lat, lon], ...]

class RoadDirectionsResponse(BaseModel):
    geometry: List[List[float]] # [[lat, lon], ...]
    distance_km: float
    duration_minutes: int
    is_road_network: bool

class OfflineEvent(BaseModel):
    id: str
    event_type: str # 'DELIVERY_COMPLETED', 'SLOW_RECEIVING_REPORT', 'OBSTACLE_ALERT'
    payload: Dict[str, Any]
    created_at_local: str
    sync_status: str = "PENDING"

class SyncBatchRequest(BaseModel):
    driver_id: str
    events: List[OfflineEvent]

class SyncBatchResponse(BaseModel):
    processed_count: int
    synced_ids: List[str]
    failed_ids: List[str]
    timestamp: str

class ObstacleAnalysis(BaseModel):
    segment_from: str
    segment_to: str
    congestion_level: float = 0.0 # 0.0 to 1.0
    narrow_street_penalty: float = 0.0
    traffic_signals_count: int = 0
    truck_clearance_ok: bool = True
    obstacle_score: float = 0.0
    alternative_available: bool = False
    alternative_time_saved_minutes: int = 0
    alert_message: Optional[str] = None
    tts_audio_alert: Optional[str] = None

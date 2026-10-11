import re
import base64
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Body
from typing import Dict, Any, List, Optional, Tuple

from ..models.schemas import (
    RouteRequest, RouteResponse, ObstacleAnalysis, TruckBase,
    OcrScanResult, MultiAddressInput, RoadDirectionsRequest, RoadDirectionsResponse, WaypointInput,
    PlaceSuggestion
)
from ..agents.supervisor import SupervisorOrchestratorAgent
from ..agents.obstacles import ObstacleMonitorAgent
from ..agents.copilot import SyntheticVoiceCopilotAgent
from ..agents.document_ocr import DocumentOcrAgent, purge_sensitive_data
from ..agents.geocoder import GeocodingAgent, extract_query_house_number
from ..agents.road_routing import fetch_osrm_road_route

router = APIRouter(prefix="/routes", tags=["Routes & Navigation"])

supervisor = SupervisorOrchestratorAgent()
obstacle_agent = ObstacleMonitorAgent()
copilot_agent = SyntheticVoiceCopilotAgent()
ocr_agent = DocumentOcrAgent()
geocoder_agent = GeocodingAgent()

@router.get("/search-places", response_model=List[PlaceSuggestion])
def search_places_endpoint(
    q: str,
    base_lat: Optional[float] = None,
    base_lon: Optional[float] = None,
    limit: int = 6
):
    """
    Busca e sugestão de estabelecimentos/endereços em tempo real (estilo Google Maps / Waze).
    Permite autocomplete imediato com coordenadas reais de latitude e longitude.
    """
    if not q or not q.strip():
        return []
    return geocoder_agent.search_places(
        query=q.strip(),
        base_lat=base_lat,
        base_lon=base_lon,
        limit=limit
    )

@router.post("/optimize", response_model=RouteResponse)
def optimize_route(request: RouteRequest):
    """
    Roteirização Inteligente com Múltiplas Paradas (OR-Tools Solver + Agentes Multitarefa).
    Aplica:
    1. Detecção e priorização de docas lentas crônicas (início do dia).
    2. Regra anti-ociosidade (impede criação de > 25min de espera ociosa).
    3. Inserção de pausas de bem-estar (almoço/café) com restaurantes >= 4.0 estrelas.
    4. Síntese de áudio ultracurta para o motorista.
    """
    try:
        return supervisor.orchestrate_route(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na otimização de rotas: {str(e)}")

@router.post("/obstacle-check", response_model=ObstacleAnalysis)
def check_segment_obstacles(
    segment_from: str,
    segment_to: str,
    current_time_minutes: int = 25,
    alternative_time_minutes: int = 18,
    congestion_level: float = 0.85,
    narrow_street_level: float = 0.20,
    traffic_signals_count: int = 4,
    crowd_reports: int = 2,
    truck_height: float = 4.10,
    bridge_max_height: float = 4.50
):
    """
    Monitor de Entraves & Malha Viária:
    Calcula o score de entrave, checa gabarito de altura/peso e dispara
    reroteamento caso haja economia de tempo >= 4 minutos.
    """
    truck = TruckBase(
        driver_id="driver-1",
        plate="GLV-2026",
        height_meters=truck_height,
        width_meters=2.6,
        length_meters=18.6,
        gross_weight_tonnes=45.0,
        axle_count=6
    )

    return obstacle_agent.analyze_segment(
        segment_from=segment_from,
        segment_to=segment_to,
        truck=truck,
        congestion_index=congestion_level,
        narrow_street_index=narrow_street_level,
        traffic_signals_count=traffic_signals_count,
        crowd_hazard_reports=crowd_reports,
        current_travel_time_min=current_time_minutes,
        alternative_travel_time_min=alternative_time_minutes,
        segment_max_height=bridge_max_height
    )

@router.get("/voice-cue")
def get_driving_voice_cue(
    event_type: str = "REROUTE_SAVINGS",
    saved_minutes: int = 8
):
    """
    Retorna frase de áudio sintético (TTS) de 1 frase para execução no alto-falante.
    """
    return copilot_agent.generate_driving_audio_cue(
        event_type=event_type,
        saved_minutes=saved_minutes
    )

@router.post("/scan-invoices", response_model=OcrScanResult)
async def scan_invoices(
    files: Optional[List[UploadFile]] = File(default=None),
    base_latitude: Optional[float] = None,
    base_longitude: Optional[float] = None,
    images_base64: Optional[List[str]] = Body(default=None)
):
    """
    Leitura de Fotos de Itinerários e Notas Fiscais (DANFE / NF-e).
    
    POLÍTICA DE PRIVACIDADE E SIGILO FISCAL LGPD:
    - O arquivo de imagem é mantido estritamente em memória temporária (RAM) e descartado imediatamente.
    - NENHUM dado fiscal confidencial (CPF, CNPJ, valores/preços, unidades, produtos ou chave de 44 dígitos)
      é gravado em banco de dados ou armazenado.
    - Apenas os destinos de entrega são extraídos, geocodificados e devolvidos.
    """
    image_tuples: List[Tuple[bytes, str]] = []

    # 1. Processar arquivos multipart enviados
    if files:
        for f in files:
            content = await f.read()
            mime = f.content_type or "image/jpeg"
            image_tuples.append((content, mime))

    # 2. Processar imagens base64 enviadas no body
    if images_base64:
        for b64 in images_base64:
            if b64:
                try:
                    if "," in b64:
                        header, data_str = b64.split(",", 1)
                        mime = header.split(";")[0].replace("data:", "") or "image/jpeg"
                    else:
                        mime = "image/jpeg"
                        data_str = b64
                    decoded = base64.b64decode(data_str)
                    image_tuples.append((decoded, mime))
                except Exception as b64_err:
                    pass

    if not image_tuples:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma foto ou imagem de nota fiscal enviada para leitura."
        )

    try:
        # Extrair destinos purgados de dados sensíveis
        raw_destinations = ocr_agent.extract_from_multiple_images(image_tuples)
    finally:
        # Garantir limpeza de memória explícita
        del image_tuples

    # Geocodificar cada destino encontrado
    waypoints: List[WaypointInput] = []
    for d in raw_destinations:
        clean_addr = purge_sensitive_data(d.get("address", ""))
        clean_name = purge_sensitive_data(d.get("name", "Destino"))
        geo = geocoder_agent.geocode(clean_addr or clean_name, base_lat=base_latitude, base_lon=base_longitude)
        
        # Preservar o número predial no nome da parada se existir na consulta ou no geocode
        house_num, _ = extract_query_house_number(clean_addr or clean_name)
        final_name = clean_name or geo["name"]
        if house_num and final_name and not re.search(r'\b' + re.escape(str(house_num)) + r'\b', final_name):
            if geo.get("name") and str(house_num) in geo["name"]:
                final_name = geo["name"]
            else:
                final_name = f"{final_name}, {house_num}"

        final_addr = geo.get("address") if (geo.get("address") and str(house_num or '') in geo.get("address", "")) else (clean_addr or geo["address"])

        waypoints.append(WaypointInput(
            name=final_name,
            address=final_addr,
            latitude=geo["latitude"],
            longitude=geo["longitude"],
            service_time_minutes=30
        ))

    return OcrScanResult(
        destinations=waypoints,
        scanned_count=len(waypoints),
        sensitive_data_purged=True,
        notes="Dados fiscais sensíveis (CPF, CNPJ, preços, unidades) foram purgados e descartados com segurança."
    )

@router.post("/multi-addresses", response_model=List[WaypointInput])
def add_multiple_addresses(input_data: MultiAddressInput):
    """
    Adiciona múltiplos endereços ou estabelecimentos manualmente
    (reconhece linhas de texto, nomes de estabelecimentos ou listas de endereços).
    """
    destinations_raw: List[Dict[str, str]] = []

    if input_data.addresses_text:
        destinations_raw.extend(ocr_agent.parse_multiple_addresses_text(input_data.addresses_text))

    if input_data.addresses_list:
        for item in input_data.addresses_list:
            if item and item.strip():
                item_str = item.strip()
                parsed = ocr_agent.parse_multiple_addresses_text(item_str)
                if parsed:
                    destinations_raw.extend(parsed)
                else:
                    destinations_raw.append({
                        "name": item_str,
                        "address": item_str
                    })

    if not destinations_raw:
        raise HTTPException(
            status_code=400,
            detail="Nenhum endereço ou estabelecimento fornecido."
        )

    waypoints: List[WaypointInput] = []
    for d in destinations_raw:
        clean_addr = purge_sensitive_data(d.get("address", ""))
        clean_name = purge_sensitive_data(d.get("name", ""))
        geo = geocoder_agent.geocode(
            clean_addr or clean_name,
            base_lat=input_data.base_latitude,
            base_lon=input_data.base_longitude
        )

        # Preservar número predial caso tenha sido informado
        house_num, _ = extract_query_house_number(clean_addr or clean_name)
        final_name = clean_name or geo["name"]
        if house_num and final_name and not re.search(r'\b' + re.escape(str(house_num)) + r'\b', final_name):
            if geo.get("name") and str(house_num) in geo["name"]:
                final_name = geo["name"]
            else:
                final_name = f"{final_name}, {house_num}"

        final_addr = geo.get("address") if (geo.get("address") and str(house_num or '') in geo.get("address", "")) else (clean_addr or geo["address"])

        waypoints.append(WaypointInput(
            name=final_name,
            address=final_addr,
            latitude=geo["latitude"],
            longitude=geo["longitude"],
            service_time_minutes=30
        ))

    return waypoints

@router.post("/road-directions", response_model=RoadDirectionsResponse)
def get_road_directions(req: RoadDirectionsRequest):
    """
    Retorna a malha viária real (traçado pelas ruas e rodovias via OSRM)
    para desenhar rotas fiéis sem linhas retas.
    """
    coords = [(c[0], c[1]) for c in req.coordinates]
    res = fetch_osrm_road_route(coords)
    return RoadDirectionsResponse(
        geometry=res["geometry"],
        distance_km=res["distance_km"],
        duration_minutes=res["duration_minutes"],
        is_road_network=res["is_road_network"]
    )


import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..database import get_connection

def create_destination(
    name: str,
    address: str,
    latitude: float,
    longitude: float,
    google_place_id: Optional[str] = None,
    db_file: Optional[str] = None
) -> Dict[str, Any]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    dest_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO delivery_destinations 
        (id, google_place_id, name, address, latitude, longitude, total_slow_reports, is_chronic_slow, avg_excess_minutes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0.0, ?)
    """, (dest_id, google_place_id, name, address, latitude, longitude, now))
    conn.commit()
    conn.close()
    return get_destination_by_id(dest_id, db_file)

def get_destination_by_id(dest_id: str, db_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM delivery_destinations WHERE id = ?", (dest_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_destination_by_id_or_name(identifier: str, db_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM delivery_destinations WHERE id = ? OR name = ?", (identifier, identifier))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def list_all_destinations(db_file: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM delivery_destinations ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_slow_report(
    destination_id: str,
    driver_id: str,
    time_of_day: str,
    excess_wait_minutes: int,
    driver_notes: Optional[str] = None,
    db_file: Optional[str] = None
) -> Dict[str, Any]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    report_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO slow_receiving_reports
        (id, destination_id, driver_id, report_timestamp, time_of_day, excess_wait_minutes, driver_notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (report_id, destination_id, driver_id, now, time_of_day, excess_wait_minutes, driver_notes, now))

    # Re-evaluate dock profiling
    cursor.execute("SELECT time_of_day, excess_wait_minutes FROM slow_receiving_reports WHERE destination_id = ?", (destination_id,))
    reports = cursor.fetchall()
    count = len(reports)
    total_excess = sum(r["excess_wait_minutes"] for r in reports)
    avg_excess = round(total_excess / count, 1) if count > 0 else 0.0

    # Rule: >= 2 reports to activate profiling
    is_chronic = 0
    slow_start = None
    slow_end = None

    if count >= 2:
        # Check distribution of hours
        hours = []
        for r in reports:
            try:
                hh = int(r["time_of_day"].split(":")[0])
                hours.append(hh)
            except Exception:
                pass
        
        if hours:
            min_h = min(hours)
            max_h = max(hours)
            # If reports are spread out across more than 5 hours difference, it's Chronic Slow
            if (max_h - min_h) >= 5:
                is_chronic = 1
                slow_start = "08:00"
                slow_end = "17:00"
            else:
                # Time-window specific
                is_chronic = 0
                slow_start = f"{max(0, min_h - 1):02d}:00"
                slow_end = f"{min(23, max_h + 1):02d}:00"

    cursor.execute("""
        UPDATE delivery_destinations
        SET total_slow_reports = ?,
            is_chronic_slow = ?,
            slow_start_time = ?,
            slow_end_time = ?,
            avg_excess_minutes = ?
        WHERE id = ?
    """, (count, is_chronic, slow_start, slow_end, avg_excess, destination_id))

    conn.commit()
    conn.close()

    return {
        "report_id": report_id,
        "destination_id": destination_id,
        "total_reports": count,
        "is_chronic_slow": bool(is_chronic),
        "slow_start_time": slow_start,
        "slow_end_time": slow_end,
        "avg_excess_minutes": avg_excess
    }

def get_slow_reports(destination_id: str, db_file: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM slow_receiving_reports WHERE destination_id = ? ORDER BY created_at DESC", (destination_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_truck(
    driver_id: str,
    plate: str,
    vehicle_type: str,
    height_meters: float,
    width_meters: float,
    length_meters: float,
    gross_weight_tonnes: float,
    axle_count: int,
    truck_id: Optional[str] = None,
    db_file: Optional[str] = None
) -> Dict[str, Any]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    tid = truck_id or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO trucks
        (id, driver_id, plate, vehicle_type, height_meters, width_meters, length_meters, gross_weight_tonnes, axle_count, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            plate=excluded.plate,
            vehicle_type=excluded.vehicle_type,
            height_meters=excluded.height_meters,
            width_meters=excluded.width_meters,
            length_meters=excluded.length_meters,
            gross_weight_tonnes=excluded.gross_weight_tonnes,
            axle_count=excluded.axle_count
    """, (tid, driver_id, plate, vehicle_type, height_meters, width_meters, length_meters, gross_weight_tonnes, axle_count, now))
    conn.commit()
    conn.close()
    return {
        "id": tid,
        "driver_id": driver_id,
        "plate": plate,
        "vehicle_type": vehicle_type,
        "height_meters": height_meters,
        "width_meters": width_meters,
        "length_meters": length_meters,
        "gross_weight_tonnes": gross_weight_tonnes,
        "axle_count": axle_count,
        "created_at": now
    }

def get_truck_by_id(truck_id: str, db_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trucks WHERE id = ?", (truck_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def record_offline_event(
    event_id: str,
    event_type: str,
    payload: Dict[str, Any],
    created_at_local: str,
    sync_status: str = "PENDING",
    db_file: Optional[str] = None
) -> None:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO offline_events_queue
        (id, event_type, payload_json, created_at_local, sync_status, attempts)
        VALUES (?, ?, ?, ?, ?, 0)
        ON CONFLICT(id) DO NOTHING
    """, (event_id, event_type, json.dumps(payload), created_at_local, sync_status))
    conn.commit()
    conn.close()

def mark_offline_event_synced(event_id: str, db_file: Optional[str] = None) -> None:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        UPDATE offline_events_queue
        SET sync_status = 'SYNCED', synced_at = ?
        WHERE id = ?
    """, (now, event_id))
    conn.commit()
    conn.close()

def get_pending_offline_events(db_file: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_file) if db_file else get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM offline_events_queue WHERE sync_status = 'PENDING' ORDER BY created_at_local ASC")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d["payload_json"])
        result.append(d)
    return result

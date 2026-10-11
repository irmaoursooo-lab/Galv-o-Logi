import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "galvao_logi.db"

def get_connection(db_file: str = DB_FILE) -> sqlite3.Connection:
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_file: str = DB_FILE) -> None:
    conn = get_connection(db_file)
    cursor = conn.cursor()

    # Destinations / Loading Docks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delivery_destinations (
        id TEXT PRIMARY KEY,
        google_place_id TEXT UNIQUE,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        total_slow_reports INTEGER DEFAULT 0,
        is_chronic_slow INTEGER DEFAULT 0,
        slow_start_time TEXT, -- e.g. "11:00"
        slow_end_time TEXT,   -- e.g. "14:00"
        avg_excess_minutes REAL DEFAULT 0.0,
        created_at TEXT NOT NULL
    );
    """)

    # Collaborative Slow Receiving Reports
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS slow_receiving_reports (
        id TEXT PRIMARY KEY,
        destination_id TEXT NOT NULL,
        driver_id TEXT NOT NULL,
        report_timestamp TEXT NOT NULL,
        time_of_day TEXT NOT NULL, -- HH:MM
        excess_wait_minutes INTEGER NOT NULL,
        driver_notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (destination_id) REFERENCES delivery_destinations(id)
    );
    """)

    # Trucks & Dimensions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trucks (
        id TEXT PRIMARY KEY,
        driver_id TEXT NOT NULL,
        plate TEXT NOT NULL,
        vehicle_type TEXT NOT NULL, -- 'VUC', 'TOCO', 'TRUCK', 'CARRETA', 'BITREM'
        height_meters REAL NOT NULL,
        width_meters REAL NOT NULL,
        length_meters REAL NOT NULL,
        gross_weight_tonnes REAL NOT NULL,
        axle_count INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    # Offline Outbox Events Queue
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offline_events_queue (
        id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL, -- 'DELIVERY_COMPLETED', 'SLOW_RECEIVING_REPORT', 'OBSTACLE_ALERT'
        payload_json TEXT NOT NULL,
        created_at_local TEXT NOT NULL,
        sync_status TEXT DEFAULT 'PENDING', -- 'PENDING', 'SYNCED', 'FAILED'
        attempts INTEGER DEFAULT 0,
        synced_at TEXT
    );
    """)

    # Active and Planned Routes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id TEXT PRIMARY KEY,
        driver_id TEXT NOT NULL,
        truck_id TEXT NOT NULL,
        status TEXT NOT NULL, -- 'PLANNED', 'ACTIVE', 'COMPLETED'
        start_latitude REAL NOT NULL,
        start_longitude REAL NOT NULL,
        departure_time TEXT NOT NULL,
        total_distance_km REAL NOT NULL,
        total_duration_minutes REAL NOT NULL,
        itinerary_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

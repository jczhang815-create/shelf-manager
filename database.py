"""
SQLite 数据库操作
"""

import sqlite3
import os
from datetime import datetime
from utils import normalize_material_code

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shelf_manager.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rh_code TEXT NOT NULL DEFAULT '',
            sw_code TEXT NOT NULL DEFAULT '',
            location TEXT NOT NULL,
            image_path TEXT NOT NULL,
            create_time TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rh_code ON materials(rh_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sw_code ON materials(sw_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON materials(location)")
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_materials_rh_code "
        "ON materials(rh_code) WHERE rh_code <> ''"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_materials_sw_code "
        "ON materials(sw_code) WHERE sw_code <> ''"
    )
    conn.commit()
    conn.close()


def insert_record(rh_code: str, sw_code: str, location: str, image_path: str) -> int:
    """插入或更新一条记录，返回 id。已有 RH/SW 编码时更新位置和图片。"""
    rh_code = normalize_material_code(rh_code)
    sw_code = normalize_material_code(sw_code)
    location = location.strip().upper()

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    existing_id = None
    if rh_code:
        cursor.execute("SELECT id FROM materials WHERE rh_code=? LIMIT 1", (rh_code,))
        row = cursor.fetchone()
        existing_id = row[0] if row else None
    if existing_id is None and sw_code:
        cursor.execute("SELECT id FROM materials WHERE sw_code=? LIMIT 1", (sw_code,))
        row = cursor.fetchone()
        existing_id = row[0] if row else None

    if existing_id is not None:
        cursor.execute(
            "UPDATE materials SET rh_code=?, sw_code=?, location=?, image_path=?, create_time=? WHERE id=?",
            (rh_code, sw_code, location, image_path, now, existing_id),
        )
        row_id = existing_id
    else:
        cursor.execute(
            "INSERT INTO materials (rh_code, sw_code, location, image_path, create_time) VALUES (?, ?, ?, ?, ?)",
            (rh_code, sw_code, location, image_path, now),
        )
        row_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return row_id


def query_by_code(code: str) -> list[dict]:
    """用 RH 或 SW 任一编码查询"""
    code = normalize_material_code(code)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, rh_code, sw_code, location, image_path, create_time "
        "FROM materials WHERE rh_code=? OR sw_code=? ORDER BY create_time DESC",
        (code, code),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "rh_code": r[1], "sw_code": r[2],
         "location": r[3], "image_path": r[4], "create_time": r[5]}
        for r in rows
    ]


def get_all_records(limit: int = 200) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, rh_code, sw_code, location, image_path, create_time "
        "FROM materials ORDER BY create_time DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "rh_code": r[1], "sw_code": r[2],
         "location": r[3], "image_path": r[4], "create_time": r[5]}
        for r in rows
    ]

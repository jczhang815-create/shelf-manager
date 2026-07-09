"""
SQLite 数据库操作
"""

import sqlite3
import os
from datetime import datetime

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
    conn.commit()
    conn.close()


def insert_record(rh_code: str, sw_code: str, location: str, image_path: str) -> int:
    """插入一条记录，返回 id"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO materials (rh_code, sw_code, location, image_path, create_time) VALUES (?, ?, ?, ?, ?)",
        (rh_code, sw_code, location, image_path, now),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def query_by_code(code: str) -> list[dict]:
    """用 RH 或 SW 任一编码查询"""
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

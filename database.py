"""
SQLite 数据库操作：建表、插入、查询
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shelf_manager.db")


def get_connection():
    """获取数据库连接（启用 WAL 模式以支持并发读取）"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库，创建表（如果不存在）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_code TEXT NOT NULL,
            location TEXT NOT NULL,
            image_path TEXT NOT NULL,
            create_time TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # 为查询建立索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_material_code
        ON materials(material_code)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_location
        ON materials(location)
    """)
    conn.commit()
    conn.close()


def insert_record(material_code: str, location: str, image_path: str) -> int:
    """
    插入一条记录，返回新记录的 id。
    如果同一 material_code + location + image_path 已存在，则跳过（去重）。
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 去重检查
    cursor.execute(
        "SELECT id FROM materials WHERE material_code=? AND location=? AND image_path=?",
        (material_code, location, image_path),
    )
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing[0]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO materials (material_code, location, image_path, create_time) VALUES (?, ?, ?, ?)",
        (material_code, location, image_path, now),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def query_by_material_code(material_code: str) -> list[dict]:
    """
    根据材料编号查询所有记录（可能出现在多个位置）。
    返回列表，每条记录为 dict。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, material_code, location, image_path, create_time "
        "FROM materials WHERE material_code=? ORDER BY create_time DESC",
        (material_code,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "material_code": r[1],
            "location": r[2],
            "image_path": r[3],
            "create_time": r[4],
        }
        for r in rows
    ]


def get_all_records(limit: int = 100) -> list[dict]:
    """获取最近的所有记录（用于浏览）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, material_code, location, image_path, create_time "
        "FROM materials ORDER BY create_time DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "material_code": r[1],
            "location": r[2],
            "image_path": r[3],
            "create_time": r[4],
        }
        for r in rows
    ]


def get_locations() -> list[str]:
    """获取所有已录入的位置列表（去重、排序）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT location FROM materials ORDER BY location")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

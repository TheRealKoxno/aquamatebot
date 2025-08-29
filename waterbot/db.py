import os
import sqlite3
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Tuple
from .models import UserConfig
from .utils import today_bounds_local, local_now

DEFAULT_GOAL_ML = 2000
DEFAULT_CUP_ML = 250
DEFAULT_INTERVAL_MIN = 60
DEFAULT_TZ = os.environ.get("WATERBOT_DEFAULT_TZ", "Europe/Dublin")
DEFAULT_START_HM = os.environ.get("WATERBOT_START_HM", "09:00")
DEFAULT_END_HM = os.environ.get("WATERBOT_END_HM", "21:00")
DB_PATH = os.environ.get("WATERBOT_DB", "waterbot.sqlite3")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn




def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        goal_ml INTEGER NOT NULL,
        cup_ml INTEGER NOT NULL,
        interval_min INTEGER NOT NULL,
        start_hm TEXT NOT NULL,
        end_hm TEXT NOT NULL,
        tz TEXT NOT NULL
        )
    """
    )
    cur.execute(
    """
    CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount_ml INTEGER NOT NULL,
    ts_utc TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """
    )
    conn.commit()
    conn.close()

def ensure_user(user_id: int) -> UserConfig:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row:
        cfg = UserConfig(**row)
    else:
        cfg = UserConfig(
            user_id=user_id,
            goal_ml=DEFAULT_GOAL_ML,
            cup_ml=DEFAULT_CUP_ML,
            interval_min=DEFAULT_INTERVAL_MIN,
            start_hm=DEFAULT_START_HM,
            end_hm=DEFAULT_END_HM,
            tz=DEFAULT_TZ,
        )
        cur.execute(
            "INSERT INTO users (user_id, goal_ml, cup_ml, interval_min, start_hm, end_hm, tz) VALUES (?,?,?,?,?,?,?)",
            (
                cfg.user_id,
                cfg.goal_ml,
                cfg.cup_ml,
                cfg.interval_min,
                cfg.start_hm,
                cfg.end_hm,
                cfg.tz,
            ),
        )
        conn.commit()
    conn.close()
    return cfg

def get_cfg(user_id: int) -> UserConfig:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return ensure_user(user_id)
    return UserConfig(**row)

def save_cfg(cfg: UserConfig) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET goal_ml=?, cup_ml=?, interval_min=?, start_hm=?, end_hm=?, tz=?
        WHERE user_id=?
        """,
        (
            cfg.goal_ml,
            cfg.cup_ml,
            cfg.interval_min,
            cfg.start_hm,
            cfg.end_hm,
            cfg.tz,
            cfg.user_id,
        ),
    )
    conn.commit()
    conn.close()

def add_log(user_id: int, amount_ml: int) -> None:
    conn = get_db()
    cur = conn.cursor()
    ts_utc = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO logs (user_id, amount_ml, ts_utc) VALUES (?,?,?)",
        (user_id, amount_ml, ts_utc),
    )
    conn.commit()
    conn.close()

def sum_today(user_id: int, cfg: UserConfig) -> int:
    start_local, end_local = today_bounds_local(cfg)
    start_utc = start_local.astimezone(timezone.utc).isoformat()
    end_utc = end_local.astimezone(timezone.utc).isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(amount_ml), 0) as total FROM logs
        WHERE user_id=? AND ts_utc >= ? AND ts_utc < ?
        """,
        (user_id, start_utc, end_utc),
    )
    total = cur.fetchone()[0]
    conn.close()
    return int(total or 0)

def weekly_stats(user_id: int, cfg: UserConfig) -> list[tuple[str, int]]:
    now = local_now(cfg)
    start_local = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
    start_utc = start_local.astimezone(timezone.utc)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ts_utc, amount_ml FROM logs
        WHERE user_id=? AND ts_utc >= ?
        ORDER BY ts_utc ASC
        """,
        (user_id, start_utc.isoformat()),
    )
    rows = cur.fetchall()
    conn.close()
    by_day: dict[str, int] = {}
    for r in rows:
        ts = datetime.fromisoformat(r["ts_utc"]).astimezone(ZoneInfo(cfg.tz))
        key = ts.strftime("%Y-%m-%d")
        by_day[key] = by_day.get(key, 0) + int(r["amount_ml"])
    out = []
    for i in range(7):
        d = (start_local + timedelta(days=i)).strftime("%Y-%m-%d")
        out.append((d, by_day.get(d, 0)))
    return out
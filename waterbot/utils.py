import os
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import Optional, Tuple
from .models import UserConfig


DEFAULT_TZ = os.environ.get("WATERBOT_DEFAULT_TZ", "Europe/Dublin")




def parse_hm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))




def local_now(cfg: UserConfig) -> datetime:
    return datetime.now(ZoneInfo(cfg.tz))




def today_bounds_local(cfg: UserConfig) -> Tuple[datetime, datetime]:
    now = local_now(cfg)
    start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=ZoneInfo(cfg.tz))
    end = start + timedelta(days=1)
    return start, end




def is_within_window(cfg: UserConfig, dt: Optional[datetime] = None) -> bool:
    if dt is None:
        dt = local_now(cfg)
    start_t = parse_hm(cfg.start_hm)
    end_t = parse_hm(cfg.end_hm)
    t = dt.timetz().replace(tzinfo=None)
    if start_t <= end_t:
        return start_t <= t <= end_t
# окно через полночь (например 22:00-06:00)
    return t >= start_t or t <= end_t
from dataclasses import dataclass


@dataclass
class UserConfig:
	user_id: int
	goal_ml: int
	cup_ml: int
	interval_min: int
	start_hm: str # HH:MM
	end_hm: str # HH:MM
	tz: str
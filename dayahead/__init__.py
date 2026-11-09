"""Day-ahead advisory planner (demo build): PPC minimum, battery and grid-resale scheduling."""
from .config import Settings
from .market import MarketDay, day_index
from .optimizer import Plan, plan_day

__version__ = "0.6.0"

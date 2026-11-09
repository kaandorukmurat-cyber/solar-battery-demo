"""Plan settings (demo build): contract, battery, grid, site and signals."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Contract:
    min_daily_mwh: float = 100.0          # PPC minimum daily sale volume
    shortfall_penalty: float = 0.0        # EUR per MWh short; 0 = hard obligation
    normal_rule: str = "fixed"            # fixed | pct | plus  (see contract.pay_rule)
    normal_value: float = 90.0
    surge_windows: list[str] = field(default_factory=lambda: ["17:00-22:00"])
    surge_rule: str = "pct"
    surge_value: float = 100.0
    allow_grid_resale: bool = True        # contract permits buying grid energy for resale
    grid_counts_toward_min: bool = False  # grid-bought MWh count toward the minimum


@dataclass
class Battery:
    power_mw: float = 10.0
    usable_mwh: float = 20.0
    start_mwh: float = 4.0
    min_mwh: float = 2.0                  # never discharge below this reserve
    end_min_mwh: float = 4.0              # end the day with at least this much
    round_trip_eff: float = 0.88
    wear_eur_per_mwh: float = 15.0        # per MWh discharged


@dataclass
class Grid:
    export_mw: float = 26.0
    import_mw: float = 26.0
    import_extra_eur: float = 20.0        # tariffs, supplier margin, taxes on top of OPCOM
    export_fee_eur: float = 2.0           # trading + balancing cost per MWh sold


@dataclass
class Site:
    latitude: float = 44.32
    longitude: float = 23.80
    timezone: str = "Europe/Bucharest"
    dc_mwp: float = 30.0
    ac_mw: float = 26.0


@dataclass
class Signals:
    enabled: bool = True
    price_threshold: float = 310.0        # RO EUR/MWh that suggests a surge
    weight: float = 0.5                   # 0..1, how much signals move expected payout
    net_import_threshold_mw: float = 600.0
    neighbour_zones: list[str] = field(default_factory=lambda: ["HU", "BG"])


@dataclass
class Settings:
    contract: Contract = field(default_factory=Contract)
    battery: Battery = field(default_factory=Battery)
    grid: Grid = field(default_factory=Grid)
    site: Site = field(default_factory=Site)
    signals: Signals = field(default_factory=Signals)

    def to_dict(self) -> dict:
        return asdict(self)

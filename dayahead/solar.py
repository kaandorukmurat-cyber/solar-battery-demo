"""Solar production forecast in MW per interval.

Two routes:
  * from_irradiance(): plane-of-array irradiance from a weather API (preferred)
  * clear_sky_with_clouds(): physics fallback from location, date and cloud cover
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Site


def pv_power_mw(poa_wm2, air_temp_c, site: Site) -> np.ndarray:
    """Convert plane-of-array irradiance (W/m2) to AC power (MW), clipped at inverter max."""
    poa = np.clip(np.asarray(poa_wm2, dtype=float), 0, None)
    tcell = np.asarray(air_temp_c, dtype=float) + poa / 800.0 * 25.0   # NOCT ~45 C
    dc = site.dc_mwp * poa / 1000.0 * site.performance_ratio * (1 + site.temp_coeff_per_c * (tcell - 25))
    return np.clip(dc, 0, site.ac_mw)


def from_irradiance(index: pd.DatetimeIndex, poa: pd.Series, temp: pd.Series, site: Site) -> np.ndarray:
    """Resample an irradiance series onto the plan's intervals and convert to MW."""
    poa = poa.reindex(poa.index.union(index)).interpolate("time").reindex(index).fillna(0)
    temp = temp.reindex(temp.index.union(index)).interpolate("time").reindex(index).ffill().bfill()
    return pv_power_mw(poa.values, temp.values, site)


def _solar_geometry(times_utc: pd.DatetimeIndex, site: Site):
    rad = np.pi / 180
    doy = times_utc.dayofyear.values
    hours_utc = times_utc.hour.values + times_utc.minute.values / 60 + times_utc.second.values / 3600
    decl = 23.45 * np.sin(rad * 360 / 365 * (284 + doy)) * rad
    B = rad * 360 / 365 * (doy - 81)
    eot = 9.87 * np.sin(2 * B) - 7.53 * np.cos(B) - 1.5 * np.sin(B)      # minutes
    solar_time = hours_utc + (4 * site.longitude + eot) / 60
    w = 15 * (solar_time - 12) * rad
    phi = site.latitude * rad
    cos_z = np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(w)
    beta, gam = site.tilt_deg * rad, site.azimuth_deg * rad
    cos_t = (np.sin(decl) * np.sin(phi) * np.cos(beta)
             - np.sin(decl) * np.cos(phi) * np.sin(beta) * np.cos(gam)
             + np.cos(decl) * np.cos(phi) * np.cos(beta) * np.cos(w)
             + np.cos(decl) * np.sin(phi) * np.sin(beta) * np.cos(gam) * np.cos(w)
             + np.cos(decl) * np.sin(beta) * np.sin(gam) * np.sin(w))
    e0 = 1 + 0.033 * np.cos(rad * 360 * doy / 365)
    return cos_z, np.clip(cos_t, 0, None), e0, beta


def clear_sky_with_index(index: pd.DatetimeIndex, clear_index, air_temp_c, site: Site,
                         interval_minutes: int = 15) -> np.ndarray:
    """PV output when the sky lets through `clear_index` (0..1.2) of clear-sky irradiance.

    Haurwitz clear sky, Erbs direct/diffuse split, isotropic tilt; averaged over 4 sub-steps.
    clear_index / air_temp_c: scalar or array aligned to `index` (interval starts).
    """
    n = len(index)
    kc = np.clip(np.broadcast_to(np.asarray(clear_index, dtype=float), (n,)), 0, 1.2)
    temp = np.broadcast_to(np.asarray(air_temp_c, dtype=float), (n,))
    out = np.zeros(n)
    for frac in (0.125, 0.375, 0.625, 0.875):
        t_utc = (index + pd.Timedelta(minutes=interval_minutes * frac)).tz_convert("UTC")
        cos_z, cos_t, e0, beta = _solar_geometry(t_utc, site)
        up = cos_z > 0.02
        cz = np.where(up, cos_z, 1.0)
        ghi_cs = np.where(up, 1098 * cz * np.exp(-0.057 / cz), 0.0)
        ghi = ghi_cs * kc
        kt = np.clip(ghi / (1361 * e0 * cz), 0, 1)
        fd = np.where(kt <= 0.22, 1 - 0.09 * kt,
             np.where(kt <= 0.8, 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4, 0.165))
        dhi = ghi * fd
        dni = np.where(up, (ghi - dhi) / cz, 0.0)
        poa = dni * cos_t + dhi * (1 + np.cos(beta)) / 2 + ghi * 0.2 * (1 - np.cos(beta)) / 2
        out += np.where(up, pv_power_mw(poa, temp, site), 0.0)
    return out / 4


def cloud_to_clear_index(cloud_pct) -> np.ndarray:
    """Total cloud cover (%) -> clear-sky index (Kasten-Czeplak)."""
    return 1 - 0.75 * (np.clip(np.asarray(cloud_pct, dtype=float), 0, 100) / 100) ** 3.4


def layers_to_clear_index(low_pct, mid_pct, high_pct) -> np.ndarray:
    """Cloud cover by height (%) -> clear-sky index. Low cloud blocks far more sun than thin
    high cloud. Approximate per-layer transmission; calibrate against your own meter if you can."""
    lo, mi, hi = (np.clip(np.asarray(v, dtype=float), 0, 100) / 100 for v in (low_pct, mid_pct, high_pct))
    return (1 - 0.75 * lo ** 1.5) * (1 - 0.55 * mi ** 1.5) * (1 - 0.25 * hi ** 1.5)


def clear_sky_with_clouds(index: pd.DatetimeIndex, cloud_pct, air_temp_c, site: Site,
                          interval_minutes: int = 15) -> np.ndarray:
    """PV output from total cloud cover (%), kept for CSV and fallback use."""
    return clear_sky_with_index(index, cloud_to_clear_index(cloud_pct), air_temp_c, site, interval_minutes)


def poa_from_components(times: pd.DatetimeIndex, ghi, dni, dhi, site: Site) -> np.ndarray:
    """Plane-of-array irradiance from measured/forecast GHI, DNI and DHI (isotropic sky)."""
    cos_z, cos_t, _, beta = _solar_geometry(times.tz_convert("UTC"), site)
    ghi, dni, dhi = (np.clip(np.nan_to_num(np.asarray(v, dtype=float)), 0, None) for v in (ghi, dni, dhi))
    poa = dni * cos_t + dhi * (1 + np.cos(beta)) / 2 + ghi * 0.2 * (1 - np.cos(beta)) / 2
    return np.where(cos_z > 0.0, poa, 0.0)


def clear_sky_ghi(times: pd.DatetimeIndex, lat: float, lon: float) -> np.ndarray:
    """Horizontal clear-sky irradiance (W/m2, Haurwitz) at instants `times`."""
    site = Site(latitude=lat, longitude=lon, tilt_deg=0)
    cos_z, _, _, _ = _solar_geometry(times.tz_convert("UTC"), site)
    cz = np.clip(cos_z, 1e-3, None)
    return np.where(cos_z > 0.02, 1098 * cz * np.exp(-0.057 / cz), 0.0)


def clear_sky_power(index: pd.DatetimeIndex, site: Site, air_temp_c=10.0) -> np.ndarray:
    """PV output (MW) the site would make under a cloudless sky, per interval."""
    return clear_sky_with_clouds(index, 0.0, air_temp_c, site)

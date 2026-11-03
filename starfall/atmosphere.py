"""Simple atmosphere model shared by sensors and the entry simulator."""

import math

from .constants import P0, RHO0, SCALE_HEIGHT


def density(alt_m: float) -> float:
    """Air density (kg/m^3) from a single exponential; ~0 above 150 km."""
    if alt_m > 150_000.0:
        return 0.0
    return RHO0 * math.exp(-max(alt_m, 0.0) / SCALE_HEIGHT)


def pressure(alt_m: float) -> float:
    """Static pressure (Pa) using a 7.2 km scale height (isothermal approximation)."""
    if alt_m > 150_000.0:
        return 0.0
    return P0 * math.exp(-max(alt_m, 0.0) / SCALE_HEIGHT)


def speed_of_sound(alt_m: float) -> float:
    """Rough speed of sound (m/s): 340 at sea level, 295 in the stratosphere."""
    if alt_m < 11_000:
        return 340.3 - 45.0 * alt_m / 11_000
    return 295.0


def dynamic_pressure(alt_m: float, speed_mps: float) -> float:
    """q = 1/2 rho v^2 (Pa)."""
    return 0.5 * density(alt_m) * speed_mps ** 2

"""Physical constants and reference values (SI units unless noted)."""

import math

MU_EARTH = 3.986004418e14          # m^3/s^2, Earth gravitational parameter (WGS84 / EGM96)
R_EARTH_EQ = 6_378_137.0           # m, WGS84 semi-major axis
WGS84_F = 1.0 / 298.257223563      # WGS84 flattening
WGS84_B = R_EARTH_EQ * (1.0 - WGS84_F)
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)  # first eccentricity squared
R_EARTH_MEAN = 6_371_008.8         # m, IUGG mean radius (great-circle work)
OMEGA_EARTH = 7.2921150e-5         # rad/s, Earth rotation rate
G0 = 9.80665                       # m/s^2, standard gravity

# US Standard Atmosphere is approximated by a single exponential.
RHO0 = 1.225                       # kg/m^3, sea-level density
SCALE_HEIGHT = 7_200.0             # m, density scale height used above ~20 km
P0 = 101_325.0                     # Pa, sea-level pressure

ENTRY_INTERFACE_ALT = 120_000.0    # m, conventional entry interface altitude
SUTTON_GRAVES_K_EARTH = 1.7415e-4  # kg^0.5/m, Sutton-Graves constant for air

DEG = math.pi / 180.0
ARCSEC = DEG / 3600.0

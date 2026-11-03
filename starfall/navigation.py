"""Navigation: star identification, attitude determination, celestial fixes,
GNSS blending, great-circle geometry and WGS84 frame conversions.

Real spacecraft use star trackers with onboard catalogs of thousands of stars
and pattern-matching algorithms (e.g. pyramid / triangle matching), then solve
Wahba's problem (TRIAD, QUEST, ESOQ) for attitude. This module implements the
same ideas at hobby scale with a ~25-star bright-star catalog.

Simplifications (documented on purpose): no precession/nutation/aberration,
GMST from the IAU 1982 linear expression, no polar motion.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from .constants import R_EARTH_EQ, R_EARTH_MEAN, WGS84_B, WGS84_E2
from .mathutil import (
    Quat,
    Vec,
    angle_between,
    cross,
    dot,
    mat_t,
    mat_vec,
    normalize,
    q_from_dcm,
    q_normalize,
    radec_to_unit,
    rot_z,
)


# --------------------------------------------------------------------------- star catalog

@dataclass(frozen=True)
class Star:
    """A catalog star with J2000 equatorial coordinates (degrees) and visual magnitude."""

    name: str
    ra_deg: float
    dec_deg: float
    vmag: float

    @property
    def unit(self) -> Vec:
        return radec_to_unit(self.ra_deg, self.dec_deg)


#: Bright navigation stars, J2000 RA/Dec (degrees), Hipparcos-derived values.
STAR_CATALOG: tuple[Star, ...] = (
    Star("Sirius", 101.2872, -16.7161, -1.46),
    Star("Canopus", 95.9880, -52.6957, -0.74),
    Star("Rigil Kentaurus", 219.9021, -60.8340, -0.27),
    Star("Arcturus", 213.9153, 19.1824, -0.05),
    Star("Vega", 279.2347, 38.7837, 0.03),
    Star("Capella", 79.1723, 45.9980, 0.08),
    Star("Rigel", 78.6345, -8.2016, 0.13),
    Star("Procyon", 114.8255, 5.2250, 0.34),
    Star("Betelgeuse", 88.7929, 7.4071, 0.42),
    Star("Achernar", 24.4285, -57.2368, 0.46),
    Star("Hadar", 210.9559, -60.3730, 0.61),
    Star("Altair", 297.6958, 8.8683, 0.76),
    Star("Acrux", 186.6496, -63.0991, 0.76),
    Star("Aldebaran", 68.9802, 16.5093, 0.86),
    Star("Antares", 247.3519, -26.4320, 0.96),
    Star("Spica", 201.2983, -11.1613, 0.97),
    Star("Pollux", 116.3290, 28.0262, 1.14),
    Star("Fomalhaut", 344.4128, -29.6222, 1.16),
    Star("Deneb", 310.3580, 45.2803, 1.25),
    Star("Mimosa", 191.9303, -59.6888, 1.25),
    Star("Regulus", 152.0930, 11.9672, 1.35),
    Star("Castor", 113.6494, 31.8883, 1.58),
    Star("Bellatrix", 81.2828, 6.3497, 1.64),
    Star("Polaris", 37.9546, 89.2641, 1.98),
)

STARS_BY_NAME = {s.name.lower(): s for s in STAR_CATALOG}


def star(name: str) -> Star:
    """Look up a catalog star by (case-insensitive) name."""
    try:
        return STARS_BY_NAME[name.lower()]
    except KeyError:
        raise KeyError(f"unknown star {name!r}") from None


# --------------------------------------------------------------------------- star identification

@dataclass
class StarMatch:
    """Result of matching measured body-frame star vectors against the catalog."""

    names: list[str]              # catalog name for each measured vector, in order
    max_residual_deg: float       # worst inter-star angle residual
    candidates_checked: int


def identify_stars(
    body_vectors: Sequence[Sequence[float]],
    tolerance_deg: float = 0.02,
    catalog: Sequence[Star] = STAR_CATALOG,
) -> StarMatch:
    """Identify measured stars by matching inter-star angular separations.

    Angular separation between two stars is invariant to the unknown attitude,
    so we search for catalog stars whose pairwise separations all agree with the
    measured ones (a brute-force "polygon match"). At least 3 stars are needed
    for an unambiguous identification. Raises ``ValueError`` if no unique match.
    """
    n = len(body_vectors)
    if n < 3:
        raise ValueError("need at least 3 star vectors to identify")
    meas = [normalize(v) for v in body_vectors]
    tol = math.radians(tolerance_deg)
    cat_units = [s.unit for s in catalog]
    m_ang = [[angle_between(meas[i], meas[j]) for j in range(n)] for i in range(n)]
    c_ang = [[angle_between(a, b) for b in cat_units] for a in cat_units]

    solutions: list[tuple[float, list[int]]] = []
    checked = 0

    def extend(assign: list[int], worst: float) -> None:
        nonlocal checked
        k = len(assign)
        if k == n:
            solutions.append((worst, list(assign)))
            return
        for c in range(len(catalog)):
            if c in assign:
                continue
            checked += 1
            w = worst
            ok = True
            for i, ci in enumerate(assign):
                r = abs(c_ang[ci][c] - m_ang[i][k])
                if r > tol:
                    ok = False
                    break
                w = max(w, r)
            if ok:
                assign.append(c)
                extend(assign, w)
                assign.pop()

    extend([], 0.0)
    if not solutions:
        raise ValueError("no catalog match within tolerance")
    solutions.sort(key=lambda s: s[0])
    if len(solutions) > 1 and solutions[1][0] - solutions[0][0] < tol / 10:
        raise ValueError("ambiguous star pattern; add more stars")
    worst, idx = solutions[0]
    return StarMatch([catalog[i].name for i in idx], math.degrees(worst), checked)


# --------------------------------------------------------------------------- attitude determination

def triad(b1: Sequence[float], b2: Sequence[float], r1: Sequence[float], r2: Sequence[float]) -> Quat:
    """TRIAD attitude from two vector pairs (body b, reference/inertial r).

    Returns ``q_bi`` (body -> inertial). The first pair is trusted most.
    """
    def frame(v1: Sequence[float], v2: Sequence[float]) -> list[Vec]:
        t1 = normalize(v1)
        t2 = normalize(cross(v1, v2))
        return [t1, t2, cross(t1, t2)]

    tb, tr = frame(b1, b2), frame(r1, r2)
    # R maps body -> inertial: R = sum_k tr_k tb_k^T
    m = [[sum(tr[k][i] * tb[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return q_from_dcm(m)


def solve_wahba(
    body_vectors: Sequence[Sequence[float]],
    ref_vectors: Sequence[Sequence[float]],
    weights: Optional[Sequence[float]] = None,
    iterations: int = 200,
) -> Quat:
    """Optimal attitude (Davenport q-method) for Wahba's problem.

    Minimises ``sum w_k |b_k - A r_k|^2``. The optimal quaternion is the
    eigenvector of Davenport's K matrix with the largest eigenvalue; we find it
    by power iteration on ``K + W*I`` seeded with a TRIAD solution (stdlib-only
    stand-in for QUEST). Returns ``q_bi`` (body -> inertial), scalar first.
    """
    n = len(body_vectors)
    if n < 2 or n != len(ref_vectors):
        raise ValueError("need >= 2 matched vector pairs")
    w = list(weights) if weights else [1.0] * n
    bs = [normalize(v) for v in body_vectors]
    rs = [normalize(v) for v in ref_vectors]
    # Attitude profile matrix B = sum w b r^T (reference -> body convention).
    B = [[sum(w[k] * bs[k][i] * rs[k][j] for k in range(n)) for j in range(3)] for i in range(3)]
    sigma = B[0][0] + B[1][1] + B[2][2]
    S = [[B[i][j] + B[j][i] for j in range(3)] for i in range(3)]
    Z = (B[1][2] - B[2][1], B[2][0] - B[0][2], B[0][1] - B[1][0])
    # K in (x, y, z, w) ordering (Markley), shifted by total weight to make it PSD.
    W = sum(w)
    K = [[S[i][j] - (sigma if i == j else 0.0) + (W if i == j else 0.0) for j in range(3)] + [Z[i]] for i in range(3)]
    K.append([Z[0], Z[1], Z[2], sigma + W])

    # Seed: TRIAD on the two most-separated pairs; convert q_bi to Markley's q (ref->body, vector-first).
    i0, j0 = max(itertools.combinations(range(n), 2), key=lambda p: angle_between(bs[p[0]], bs[p[1]]))
    q0 = triad(bs[i0], bs[j0], rs[i0], rs[j0])
    v = [q0[1], q0[2], q0[3], q0[0]]
    for _ in range(iterations):
        nv = [sum(K[i][j] * v[j] for j in range(4)) for i in range(4)]
        mag = math.sqrt(sum(c * c for c in nv))
        v = [c / mag for c in nv]
    # Markley's q gives A(q) = R(q)^T with R the active rotation, i.e. q itself is body->inertial.
    return q_normalize((v[3], v[0], v[1], v[2]))


def attitude_from_stars(body_vectors: Sequence[Sequence[float]], tolerance_deg: float = 0.02) -> tuple[Quat, StarMatch]:
    """Identify stars, then solve for attitude ``q_bi``. Convenience wrapper."""
    match = identify_stars(body_vectors, tolerance_deg)
    refs = [star(nm).unit for nm in match.names]
    return solve_wahba(body_vectors, refs), match


# --------------------------------------------------------------------------- time / frames

def julian_date(t: datetime) -> float:
    """Julian date (UTC used as UT1; sub-second differences are ignored)."""
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    t = t.astimezone(timezone.utc)
    j2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
    return 2451545.0 + (t - j2000).total_seconds() / 86400.0


def gmst_rad(t: datetime) -> float:
    """Greenwich Mean Sidereal Time in radians (IAU 1982, linear term)."""
    d = julian_date(t) - 2451545.0
    return math.radians((280.46061837 + 360.98564736629 * d) % 360.0)


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> Vec:
    """WGS84 geodetic latitude/longitude/height to ECEF (metres)."""
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    n = R_EARTH_EQ / math.sqrt(1.0 - WGS84_E2 * math.sin(lat) ** 2)
    return (
        (n + alt_m) * math.cos(lat) * math.cos(lon),
        (n + alt_m) * math.cos(lat) * math.sin(lon),
        (n * (1.0 - WGS84_E2) + alt_m) * math.sin(lat),
    )


def ecef_to_geodetic(x: float, y: float, z: float) -> tuple[float, float, float]:
    """ECEF (metres) to WGS84 geodetic (lat deg, lon deg, height m), Bowring + iteration."""
    lon = math.atan2(y, x)
    p = math.hypot(x, y)
    if p < 1e-9:  # pole
        return (90.0 if z >= 0 else -90.0, 0.0, abs(z) - WGS84_B)
    lat = math.atan2(z, p * (1.0 - WGS84_E2))
    alt = 0.0
    for _ in range(10):
        n = R_EARTH_EQ / math.sqrt(1.0 - WGS84_E2 * math.sin(lat) ** 2)
        alt = p / math.cos(lat) - n
        new_lat = math.atan2(z, p * (1.0 - WGS84_E2 * n / (n + alt)))
        if abs(new_lat - lat) < 1e-13:
            lat = new_lat
            break
        lat = new_lat
    return (math.degrees(lat), math.degrees(lon), alt)


def eci_to_ecef(r_eci: Sequence[float], t: datetime) -> Vec:
    """Rotate an ECI (TEME-ish, no precession) vector into ECEF at time ``t``."""
    return mat_vec(rot_z(-gmst_rad(t)), r_eci)


def ecef_to_eci(r_ecef: Sequence[float], t: datetime) -> Vec:
    return mat_vec(rot_z(gmst_rad(t)), r_ecef)


# --------------------------------------------------------------------------- great circle

def great_circle_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance (metres) on a sphere of mean Earth radius."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R_EARTH_MEAN * math.asin(min(1.0, math.sqrt(a)))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial true bearing (0..360 deg, clockwise from north) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def destination_point(lat: float, lon: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    """Point reached travelling ``distance_m`` along a great circle from (lat, lon)."""
    d = distance_m / R_EARTH_MEAN
    p1, l1, b = math.radians(lat), math.radians(lon), math.radians(bearing_deg)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540.0) % 360.0 - 180.0


# --------------------------------------------------------------------------- celestial fix

@dataclass
class Sight:
    """A star sight: observed altitude above the true horizon at a UTC time."""

    star_name: str
    observed_alt_deg: float
    time: datetime


def computed_altitude_azimuth(lat_deg: float, lon_deg: float, s: Star, t: datetime) -> tuple[float, float]:
    """Computed altitude Hc and azimuth Zn (degrees) of a star from a position."""
    lat = math.radians(lat_deg)
    dec = math.radians(s.dec_deg)
    lha = gmst_rad(t) + math.radians(lon_deg) - math.radians(s.ra_deg)
    sin_h = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(lha)
    hc = math.asin(max(-1.0, min(1.0, sin_h)))
    zn = math.atan2(-math.cos(dec) * math.sin(lha), math.cos(lat) * math.sin(dec) - math.sin(lat) * math.cos(dec) * math.cos(lha))
    return math.degrees(hc), (math.degrees(zn) + 360.0) % 360.0


@dataclass
class Fix:
    lat_deg: float
    lon_deg: float
    sigma_m: float
    source: str

    def to_dict(self) -> dict:
        return {"lat_deg": round(self.lat_deg, 6), "lon_deg": round(self.lon_deg, 6),
                "sigma_m": round(self.sigma_m, 1), "source": self.source}


def celestial_fix(
    sights: Sequence[Sight],
    assumed_lat: float,
    assumed_lon: float,
    sight_sigma_arcmin: float = 1.0,
    iterations: int = 20,
) -> Fix:
    """Position from star altitudes by the altitude-intercept (Marcq St Hilaire) method.

    Each sight gives a line of position: intercept ``a = Ho - Hc`` towards the
    star's azimuth ``Zn``. We solve the least-squares intersection of all lines
    and iterate from the assumed position. Useful after splashdown or for the
    recovery team; on orbit the horizon sensor + star tracker play this role.
    """
    if len(sights) < 2:
        raise ValueError("need at least two sights")
    lat, lon = assumed_lat, assumed_lon
    for _ in range(iterations):
        a11 = a12 = a22 = b1 = b2 = 0.0
        for sg in sights:
            hc, zn = computed_altitude_azimuth(lat, lon, star(sg.star_name), sg.time)
            a = sg.observed_alt_deg - hc
            cz, sz = math.cos(math.radians(zn)), math.sin(math.radians(zn))
            # unknowns: dlat (deg), dlon*cos(lat) (deg east)
            a11 += cz * cz
            a12 += cz * sz
            a22 += sz * sz
            b1 += a * cz
            b2 += a * sz
        det = a11 * a22 - a12 * a12
        if abs(det) < 1e-12:
            raise ValueError("sights too close in azimuth for a fix")
        dlat = (b1 * a22 - b2 * a12) / det
        dep = (a11 * b2 - a12 * b1) / det
        lat += dlat
        lon += dep / max(1e-6, math.cos(math.radians(lat)))
        if abs(dlat) < 1e-9 and abs(dep) < 1e-9:
            break
    lon = (lon + 540.0) % 360.0 - 180.0
    # 1 arcminute of altitude = 1 nautical mile of position.
    sigma = sight_sigma_arcmin * 1852.0 / math.sqrt(len(sights) / 2.0)
    return Fix(lat, lon, sigma, "celestial")


def blend_fixes(*fixes: Optional[Fix]) -> Fix:
    """Inverse-variance blend of independent position fixes (GNSS, celestial, ...).

    ``None`` entries (e.g. GNSS during plasma blackout) are skipped. Longitude is
    blended on the unit circle so the antimeridian is handled.
    """
    valid = [f for f in fixes if f is not None]
    if not valid:
        raise ValueError("no valid fixes to blend")
    ws = [1.0 / (f.sigma_m ** 2) for f in valid]
    wsum = sum(ws)
    lat = sum(w * f.lat_deg for w, f in zip(ws, valid)) / wsum
    sx = sum(w * math.cos(math.radians(f.lon_deg)) for w, f in zip(ws, valid))
    sy = sum(w * math.sin(math.radians(f.lon_deg)) for w, f in zip(ws, valid))
    lon = math.degrees(math.atan2(sy, sx))
    return Fix(lat, lon, 1.0 / math.sqrt(wsum), "+".join(f.source for f in valid))


def body_vectors_for(q_bi: Quat, names: Sequence[str]) -> list[Vec]:
    """Simulate star-tracker measurements: catalog stars expressed in the body frame."""
    from .mathutil import q_conj, q_rotate
    return [q_rotate(q_conj(q_bi), star(n).unit) for n in names]


__all__ = [
    "Star", "STAR_CATALOG", "star", "StarMatch", "identify_stars", "triad", "solve_wahba",
    "attitude_from_stars", "julian_date", "gmst_rad", "geodetic_to_ecef", "ecef_to_geodetic",
    "eci_to_ecef", "ecef_to_eci", "great_circle_distance_m", "initial_bearing_deg",
    "destination_point", "Sight", "computed_altitude_azimuth", "Fix", "celestial_fix",
    "blend_fixes", "body_vectors_for", "dot", "mat_t",
]

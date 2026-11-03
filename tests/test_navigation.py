import math
import random
from datetime import datetime, timezone

import pytest

from starfall.mathutil import normalize, q_angle_between, q_from_axis_angle
from starfall.navigation import (
    STAR_CATALOG, Fix, Sight, attitude_from_stars, blend_fixes, body_vectors_for, celestial_fix,
    computed_altitude_azimuth, destination_point, ecef_to_eci, ecef_to_geodetic, eci_to_ecef,
    geodetic_to_ecef, gmst_rad, great_circle_distance_m, identify_stars, initial_bearing_deg, triad,
)

T = datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc)


def random_q(rng):
    axis = normalize((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
    return q_from_axis_angle(axis, rng.uniform(0, math.pi))


def noisy(vs, rng, arcsec):
    s = math.radians(arcsec / 3600)
    return [normalize(tuple(c + rng.gauss(0, s) for c in v)) for v in vs]


def test_catalog_has_at_least_20_bright_stars():
    assert len(STAR_CATALOG) >= 20
    assert all(-90 <= s.dec_deg <= 90 and 0 <= s.ra_deg < 360 for s in STAR_CATALOG)


def test_star_identification_from_separations():
    rng = random.Random(7)
    names = ["Vega", "Altair", "Deneb", "Arcturus"]
    meas = noisy(body_vectors_for(random_q(rng), names), rng, 5)
    match = identify_stars(meas)
    assert match.names == names


def test_star_identification_needs_three_stars():
    with pytest.raises(ValueError):
        identify_stars(body_vectors_for((1, 0, 0, 0), ["Vega", "Altair"]))


def test_triad_recovers_attitude_exactly():
    rng = random.Random(1)
    q = random_q(rng)
    b1, b2 = body_vectors_for(q, ["Sirius", "Polaris"])
    from starfall.navigation import star
    assert q_angle_between(triad(b1, b2, star("Sirius").unit, star("Polaris").unit), q) < 1e-9


def test_quest_attitude_with_noise():
    rng = random.Random(11)
    q = random_q(rng)
    names = ["Sirius", "Canopus", "Rigel", "Betelgeuse", "Procyon"]
    q_est, match = attitude_from_stars(noisy(body_vectors_for(q, names), rng, 5))
    assert match.names == names
    assert math.degrees(q_angle_between(q_est, q)) * 3600 < 30  # arcsec


@pytest.mark.parametrize("lat,lon,alt", [(0, 0, 0), (40.76, -113.89, 1290), (-30.95, 136.53, 400_000),
                                         (89.9, 45, 10), (-89.99, -170, 0), (28.4858, -80.5428, -20)])
def test_geodetic_ecef_round_trip(lat, lon, alt):
    x, y, z = geodetic_to_ecef(lat, lon, alt)
    lat2, lon2, alt2 = ecef_to_geodetic(x, y, z)
    assert abs(lat2 - lat) < 1e-9
    assert abs(((lon2 - lon + 180) % 360) - 180) < 1e-9
    assert abs(alt2 - alt) < 1e-4


def test_equator_ecef_matches_wgs84_radius():
    x, y, z = geodetic_to_ecef(0, 0, 0)
    assert abs(x - 6378137.0) < 1e-6 and abs(y) < 1e-9 and abs(z) < 1e-9


def test_eci_ecef_round_trip_and_gmst_range():
    r = (7000e3, -1200e3, 300e3)
    back = ecef_to_eci(eci_to_ecef(r, T), T)
    assert all(abs(a - b) < 1e-6 for a, b in zip(r, back))
    assert 0 <= gmst_rad(T) < 2 * math.pi


def test_gmst_j2000_epoch():
    # GMST at 2000-01-01 12:00 UT1 is 280.46061837 deg.
    g = math.degrees(gmst_rad(datetime(2000, 1, 1, 12, tzinfo=timezone.utc)))
    assert abs(g - 280.46061837) < 1e-6


def test_great_circle_known_distance():
    # LAX -> JFK is about 3,974 km on a sphere of mean radius.
    d = great_circle_distance_m(33.9425, -118.4081, 40.6398, -73.7789)
    assert 3_960e3 < d < 3_990e3


def test_great_circle_quarter_meridian_and_bearing():
    d = great_circle_distance_m(0, 0, 90, 0)
    assert abs(d - math.pi / 2 * 6371008.8) < 1e-3
    assert abs(initial_bearing_deg(0, 0, 0, 10) - 90) < 1e-9
    assert abs(initial_bearing_deg(0, 0, 10, 0) - 0) < 1e-9


def test_destination_point_inverts_distance_and_bearing():
    lat, lon = destination_point(28.5, -80.5, 47.0, 1_234_000)
    assert abs(great_circle_distance_m(28.5, -80.5, lat, lon) - 1_234_000) < 1e-3
    assert abs(initial_bearing_deg(28.5, -80.5, lat, lon) - 47.0) < 1e-6


def test_celestial_fix_converges_to_true_position():
    lat0, lon0 = 32.5, -118.2
    sights = []
    for s in STAR_CATALOG:
        hc, _ = computed_altitude_azimuth(lat0, lon0, s, T)
        if 15 < hc < 75:
            sights.append(Sight(s.name, hc, T))
    assert len(sights) >= 3
    fix = celestial_fix(sights, lat0 + 1.0, lon0 - 1.0)
    assert great_circle_distance_m(fix.lat_deg, fix.lon_deg, lat0, lon0) < 1.0


def test_blend_fixes_weights_by_variance_and_skips_none():
    gnss = Fix(10.0, 20.0, 5.0, "gnss")
    cel = Fix(10.01, 20.01, 1000.0, "celestial")
    b = blend_fixes(cel, gnss, None)
    assert abs(b.lat_deg - 10.0) < 1e-5 and b.sigma_m < 5.0
    assert blend_fixes(None, cel).source == "celestial"
    with pytest.raises(ValueError):
        blend_fixes(None)


def test_blend_handles_antimeridian():
    b = blend_fixes(Fix(0, 179.9, 10, "a"), Fix(0, -179.9, 10, "b"))
    assert abs(abs(b.lon_deg) - 180) < 1e-6

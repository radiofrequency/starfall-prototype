from datetime import datetime, timezone

import pytest

from starfall import atmosphere
from starfall.navigation import great_circle_distance_m
from starfall.reentry import (
    LANDING_SITES, CircularOrbit, EntryVehicle, bank_for_crossrange, deorbit_delta_v, get_site,
    plan_deorbit_burn, return_to_earth, simulate_entry,
)

EPOCH = datetime(2026, 11, 3, 14, 0, tzinfo=timezone.utc)


def test_deorbit_delta_v_400km_to_50km_perigee():
    assert 100 <= deorbit_delta_v(400e3, 50e3) <= 130


def test_deorbit_delta_v_monotonic_and_validates():
    assert deorbit_delta_v(400e3, 0) > deorbit_delta_v(400e3, 50e3) > deorbit_delta_v(400e3, 100e3)
    with pytest.raises(ValueError):
        deorbit_delta_v(400e3, 500e3)


def test_burn_plan_entry_conditions():
    b = plan_deorbit_burn(CircularOrbit(), EntryVehicle())
    assert 7_700 < b.ei_speed_mps < 8_100
    assert -3.0 < b.ei_flight_path_deg < -0.5        # shallow entry
    assert 0 < b.propellant_kg < EntryVehicle().propellant_kg
    assert 900 < b.coast_to_ei_s < 3_000


def test_atmosphere_scale_height():
    assert abs(atmosphere.density(0) - 1.225) < 1e-12
    assert abs(atmosphere.density(7_200) / atmosphere.density(0) - 0.36788) < 1e-4


def test_entry_sim_physical_ranges():
    b = plan_deorbit_burn(CircularOrbit(), EntryVehicle())
    e = simulate_entry(b.ei_speed_mps, b.ei_flight_path_deg, EntryVehicle(), 0.0)
    assert 1.5 < e.peak_g < 8
    assert 1e5 < e.peak_heat_flux_w_m2 < 1.6e6
    assert e.final_speed_mps < 300
    assert e.blackout_s > 60
    assert abs(e.crossrange_km) < 1e-6


def test_bank_angle_produces_requested_crossrange():
    b = plan_deorbit_burn(CircularOrbit(), EntryVehicle())
    for want in (60.0, -100.0):
        bank, e = bank_for_crossrange(want, b.ei_speed_mps, b.ei_flight_path_deg, EntryVehicle())
        assert (bank > 0) == (want > 0)
        assert abs(e.crossrange_km - want) < 1.0


def test_site_table():
    names = set(LANDING_SITES)
    assert {"cape-canaveral-lz1", "pacific-splashdown", "gulf-of-mexico", "bonneville-salt-flats",
            "woomera"} <= names
    assert get_site("Woomera").name == "woomera"
    with pytest.raises(KeyError):
        get_site("atlantis")


def test_return_to_earth_hits_target():
    site = get_site("woomera")
    plan = return_to_earth(site, CircularOrbit(epoch=EPOCH))
    assert plan.status == "GO"
    assert plan.miss_distance_km < site.landing_ellipse_km
    hit = plan.predicted_impact
    assert great_circle_distance_m(hit["lat_deg"], hit["lon_deg"], site.lat_deg, site.lon_deg) < 5_000
    assert plan.time_to_burn_s > 0


def test_unreachable_site_diverts():
    plan = return_to_earth(get_site("pacific-splashdown"), CircularOrbit(epoch=EPOCH))
    assert plan.status == "DIVERT"
    assert plan.requested_site == "pacific-splashdown" and plan.site != "pacific-splashdown"
    assert plan.reasons


def test_no_divert_reports_no_go():
    plan = return_to_earth(get_site("pacific-splashdown"), CircularOrbit(epoch=EPOCH), allow_divert=False)
    assert plan.status == "NO_GO" and plan.reasons

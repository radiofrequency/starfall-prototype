import json
from datetime import datetime, timedelta, timezone

import pytest

from starfall.mission import Mission, Phase, TransitionError, demo_mission

T0 = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


def to_growth() -> Mission:
    m = Mission(launch_time=T0)
    m.transition(Phase.ASCENT, T0)
    m.vehicle.altitude_m = 200_000
    m.transition(Phase.ORBIT_INSERTION, T0)
    m.vehicle.apogee_alt_m = m.vehicle.perigee_alt_m = 400_000
    m.vehicle.altitude_m = 400_000
    m.transition(Phase.ON_ORBIT_CRYSTAL_GROWTH, T0)
    return m


def test_cannot_skip_phases():
    m = Mission(launch_time=T0)
    with pytest.raises(TransitionError, match="not reachable"):
        m.transition(Phase.ON_ORBIT_CRYSTAL_GROWTH)


def test_launch_guards_weather_and_range():
    m = Mission(launch_time=T0)
    m.vehicle.weather_go = False
    m.vehicle.range_safety_go = False
    with pytest.raises(TransitionError) as e:
        m.transition(Phase.ASCENT)
    assert "launch weather NO-GO" in e.value.reasons and "range safety NO-GO" in e.value.reasons


def test_orbit_insertion_requires_altitude():
    m = Mission(launch_time=T0)
    m.transition(Phase.ASCENT, T0)
    m.vehicle.altitude_m = 90_000
    with pytest.raises(TransitionError):
        m.transition(Phase.ORBIT_INSERTION)


def test_growth_requires_stable_perigee():
    m = Mission(launch_time=T0)
    m.transition(Phase.ASCENT, T0)
    m.vehicle.altitude_m = 200_000
    m.transition(Phase.ORBIT_INSERTION, T0)
    m.vehicle.perigee_alt_m = 120_000
    with pytest.raises(TransitionError, match="perigee"):
        m.transition(Phase.ON_ORBIT_CRYSTAL_GROWTH)


def test_deorbit_burn_guards_and_interlocks():
    m = to_growth()
    m.crystal.grow(400 * 3600)             # complete the batch; furnace is hot
    m.transition(Phase.DEORBIT_PREP, T0)
    m.vehicle.attitude_valid = False
    m.vehicle.battery_soc = 0.25
    with pytest.raises(TransitionError) as e:
        m.transition(Phase.DEORBIT_BURN)
    joined = " ".join(e.value.reasons)
    for text in ["not sealed", "star-tracker", "battery", "landing site", "FURNACE_HOT"]:
        assert text in joined
    m.crystal.seal()
    m.vehicle.attitude_valid = True
    m.vehicle.battery_soc = 0.8
    m.vehicle.landing_site = "woomera"
    m.set_interlock("RCS_FAULT", True)
    with pytest.raises(TransitionError, match="RCS_FAULT"):
        m.transition(Phase.DEORBIT_BURN)
    m.set_interlock("RCS_FAULT", False)
    m.transition(Phase.DEORBIT_BURN, T0)
    assert m.phase is Phase.DEORBIT_BURN


def test_entry_interface_requires_120_km():
    m = to_growth()
    m.crystal.grow(400 * 3600)
    m.crystal.seal()
    m.vehicle.landing_site = "woomera"
    m.transition(Phase.DEORBIT_PREP, T0)
    m.transition(Phase.DEORBIT_BURN, T0)
    m.vehicle.altitude_m = 130_000
    with pytest.raises(TransitionError, match="entry interface"):
        m.transition(Phase.ENTRY_INTERFACE)
    m.vehicle.altitude_m = 119_000
    m.transition(Phase.ENTRY_INTERFACE, T0)


def test_abort_from_any_phase_and_terminal_after():
    m = to_growth()
    m.abort("cabin leak", T0)
    assert m.phase is Phase.ABORT and m.abort_reason == "cabin leak"
    with pytest.raises(TransitionError):
        m.transition(Phase.DEORBIT_PREP)


def test_wave_off_back_to_growth():
    m = to_growth()
    m.crystal.grow(400 * 3600)
    m.transition(Phase.DEORBIT_PREP, T0)
    m.transition(Phase.ON_ORBIT_CRYSTAL_GROWTH, T0)


def test_report_progress_is_json_with_required_fields():
    now = T0 + timedelta(days=7)
    rep = json.loads(demo_mission(now).report_progress(now))
    for key in ["phase", "met", "orbit", "crystal", "propellant_kg", "battery_soc_pct",
                "thermal_margins", "next_event", "next_event_eta_s"]:
        assert key in rep
    assert rep["phase"] == "ON_ORBIT_CRYSTAL_GROWTH"
    assert 90 < rep["orbit"]["period_min"] < 95       # ~400 km orbit
    assert 0 < rep["crystal"]["lattice_quality"] <= 1
    assert rep["next_event"] == "DEORBIT_PREP"

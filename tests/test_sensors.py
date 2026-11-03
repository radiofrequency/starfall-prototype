from starfall.sensors import SensorSuite, truth_for_phase


def test_orbit_sensors_nominal():
    f = SensorSuite(seed=1).sample(truth_for_phase("orbit"))
    assert f.gnss.fix == "3D"
    assert f.star_tracker.valid
    assert not f.radar_altimeter.valid


def test_gnss_drops_out_in_plasma_blackout():
    t = truth_for_phase("blackout")
    assert t.plasma_blackout
    f = SensorSuite(seed=1).sample(t)
    assert f.gnss.fix == "NO_FIX" and f.gnss.reason == "PLASMA_BLACKOUT"
    assert not f.star_tracker.valid


def test_terminal_radar_valid_and_g_load_non_negative():
    f = SensorSuite(seed=2).sample(truth_for_phase("terminal"))
    assert f.radar_altimeter.valid
    assert f.g_load >= 0


def test_seeded_suites_are_reproducible():
    a = SensorSuite(seed=5).sample(truth_for_phase("landing")).to_dict()
    b = SensorSuite(seed=5).sample(truth_for_phase("landing")).to_dict()
    assert a == b

import json

import pytest

from starfall.cli import main


def run(capsys, *argv):
    rc = main(list(argv))
    return rc, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("phase", ["orbit", "blackout", "terminal", "landing"])
def test_sensors(capsys, phase):
    rc, out = run(capsys, "sensors", "--phase", phase)
    assert rc == 0 and out["phase"] == phase and "imu" in out["frame"]


def test_fix(capsys):
    rc, out = run(capsys, "fix", "--time", "2026-11-03T14:00:00Z")
    assert rc == 0
    assert out["attitude"]["error_arcsec"] < 30
    assert out["celestial"]["error_m"] < 2_000
    assert out["blended"]["error_m"] < 50


def test_report(capsys):
    rc, out = run(capsys, "report", "--time", "2026-11-03T14:00:00Z")
    assert rc == 0 and out["phase"] == "ON_ORBIT_CRYSTAL_GROWTH"


def test_return_to_earth_dry_run(capsys):
    rc, out = run(capsys, "return-to-earth", "--site", "woomera", "--dry-run", "--time", "2026-11-03T14:00:00Z")
    assert rc == 0 and out["status"] == "GO" and out["dry_run"] is True


def test_unknown_site_is_json_error(capsys):
    rc, out = run(capsys, "return-to-earth", "--site", "atlantis")
    assert rc == 2 and "unknown landing site" in out["error"]

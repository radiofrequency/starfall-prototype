"""Command-line interface: ``python -m starfall <command>``.

Every command prints JSON to stdout.

    sensors          sample the simulated sensor suite
    fix              star-tracker attitude + celestial position fix, blended with GNSS
    report           mission progress report
    sites            list landing sites
    return-to-earth  plan a deorbit and entry to a landing site (dry run by default)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timezone
from typing import Optional, Sequence

from . import __version__
from .mathutil import q_from_axis_angle, q_angle_between, normalize
from .mission import demo_mission
from .navigation import (
    STAR_CATALOG,
    Fix,
    Sight,
    attitude_from_stars,
    blend_fixes,
    body_vectors_for,
    celestial_fix,
    computed_altitude_azimuth,
    great_circle_distance_m,
)
from .reentry import LANDING_SITES, CircularOrbit, EntryVehicle, get_site, return_to_earth
from .sensors import SensorSuite, VehicleTruth, truth_for_phase


def _now(arg: Optional[str]) -> datetime:
    if not arg:
        return datetime.now(timezone.utc).replace(microsecond=0)
    t = datetime.fromisoformat(arg.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def cmd_sensors(args: argparse.Namespace) -> dict:
    suite = SensorSuite(seed=args.seed)
    frame = suite.sample(truth_for_phase(args.phase))
    return {"phase": args.phase, "seed": args.seed, "frame": frame.to_dict()}


def cmd_fix(args: argparse.Namespace) -> dict:
    """Simulate a navigation update: attitude from stars, celestial fix, GNSS blend."""
    rng = random.Random(args.seed)
    t = _now(args.time)
    # Attitude: random true attitude, 5 catalog stars seen with 5 arcsec noise.
    axis = normalize((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
    q_true = q_from_axis_angle(axis, rng.uniform(0, math.pi))
    names = ["Sirius", "Canopus", "Arcturus", "Vega", "Capella"]
    noisy = [normalize(tuple(c + rng.gauss(0, math.radians(5 / 3600)) for c in v))
             for v in body_vectors_for(q_true, names)]
    q_est, match = attitude_from_stars(noisy)
    # Celestial fix: altitudes of bright stars visible from the true position.
    sights = []
    for s in STAR_CATALOG:
        hc, _ = computed_altitude_azimuth(args.lat, args.lon, s, t)
        if 15.0 <= hc <= 75.0:
            sights.append(Sight(s.name, hc + rng.gauss(0, args.sight_sigma_arcmin / 60), t))
    if len(sights) < 3:
        raise SystemExit("fewer than 3 usable stars at this time/place")
    cel = celestial_fix(sights, args.lat + 0.5, args.lon - 0.5, args.sight_sigma_arcmin)
    # GNSS from the sensor model (drops out in plasma blackout).
    truth = VehicleTruth(lat_deg=args.lat, lon_deg=args.lon, alt_m=args.alt, speed_mps=args.speed)
    g = SensorSuite(seed=args.seed).gnss(truth)
    gnss_fix = Fix(g.lat_deg, g.lon_deg, 5.0, "gnss") if g.fix == "3D" else None
    blended = blend_fixes(cel, gnss_fix)
    return {
        "time_utc": t.isoformat(),
        "attitude": {
            "q_body_to_inertial": [round(c, 6) for c in q_est],
            "error_arcsec": round(math.degrees(q_angle_between(q_est, q_true)) * 3600, 2),
            "stars_identified": match.names,
            "max_residual_deg": round(match.max_residual_deg, 5),
        },
        "celestial": cel.to_dict() | {"sights": [s.star_name for s in sights],
                                      "error_m": round(great_circle_distance_m(cel.lat_deg, cel.lon_deg, args.lat, args.lon), 1)},
        "gnss": {"fix": g.fix, "reason": g.reason, "satellites": g.satellites},
        "blended": blended.to_dict() | {"error_m": round(great_circle_distance_m(blended.lat_deg, blended.lon_deg, args.lat, args.lon), 1)},
    }


def cmd_report(args: argparse.Namespace) -> dict:
    return demo_mission(_now(args.time)).progress(_now(args.time))


def cmd_sites(args: argparse.Namespace) -> dict:
    return {"sites": [vars(s) for s in LANDING_SITES.values()]}


def cmd_return(args: argparse.Namespace) -> dict:
    site = get_site(args.site)
    orbit = CircularOrbit(alt_m=args.alt_km * 1000, inc_deg=args.inc, raan_deg=args.raan,
                          arg_lat_deg=args.arg_lat, epoch=_now(args.time))
    plan = return_to_earth(site, orbit, EntryVehicle(), search_hours=args.search_hours,
                           allow_divert=not args.no_divert, dry_run=args.dry_run)
    out = plan.to_dict(include_trajectory=args.trajectory)
    if not args.dry_run:
        # The simulation has nothing to command; say so plainly instead of pretending.
        out["note"] = "no vehicle connected: plan computed but not uplinked"
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="starfall", description="Starfall flight-software simulation (fictional).")
    p.add_argument("--version", action="version", version=f"starfall {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sensors", help="sample the simulated sensor suite")
    s.add_argument("--phase", default="orbit", choices=["orbit", "blackout", "terminal", "landing"])
    s.add_argument("--seed", type=int, default=1)
    s.set_defaults(func=cmd_sensors)

    f = sub.add_parser("fix", help="attitude + celestial fix + GNSS blend")
    f.add_argument("--lat", type=float, default=40.76)
    f.add_argument("--lon", type=float, default=-113.89)
    f.add_argument("--alt", type=float, default=0.0, help="altitude (m) for the GNSS model")
    f.add_argument("--speed", type=float, default=0.0, help="speed (m/s) for the GNSS model")
    f.add_argument("--time", help="UTC ISO time (default now)")
    f.add_argument("--sight-sigma-arcmin", type=float, default=1.0)
    f.add_argument("--seed", type=int, default=1)
    f.set_defaults(func=cmd_fix)

    r = sub.add_parser("report", help="mission progress report")
    r.add_argument("--time", help="UTC ISO time (default now)")
    r.set_defaults(func=cmd_report)

    sub.add_parser("sites", help="list landing sites").set_defaults(func=cmd_sites)

    rt = sub.add_parser("return-to-earth", help="plan deorbit + entry to a landing site")
    rt.add_argument("--site", required=True, help=f"one of {', '.join(LANDING_SITES)}")
    rt.add_argument("--alt-km", type=float, default=400.0)
    rt.add_argument("--inc", type=float, default=51.6)
    rt.add_argument("--raan", type=float, default=0.0)
    rt.add_argument("--arg-lat", type=float, default=0.0)
    rt.add_argument("--time", help="orbit epoch, UTC ISO (default now)")
    rt.add_argument("--search-hours", type=float, default=24.0)
    rt.add_argument("--no-divert", action="store_true")
    rt.add_argument("--trajectory", action="store_true", help="include the entry trajectory samples")
    g = rt.add_mutually_exclusive_group()
    g.add_argument("--dry-run", dest="dry_run", action="store_true", default=True, help="plan only (default)")
    g.add_argument("--execute", dest="dry_run", action="store_false", help="mark plan as for execution")
    rt.set_defaults(func=cmd_return)
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.func(args)
    except (KeyError, ValueError) as e:
        print(json.dumps({"error": str(e).strip("'\"")}), file=sys.stdout)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

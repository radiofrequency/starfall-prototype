"""Return-to-Earth planning: deorbit burn, entry simulation, guidance and divert logic.

Model (deliberately textbook-level):

* Circular parking orbit, two-body motion, spherical Earth rotating at
  ``OMEGA_EARTH`` for the ground track.
* Deorbit: a single retrograde impulsive burn lowers perigee to a target
  altitude (vis-viva). Coast on the transfer ellipse to entry interface (EI,
  120 km) is timed with Kepler's equation.
* Entry: 3-DOF point mass over a spherical Earth with an exponential
  atmosphere, drag + lift (constant L/D, bank angle modulation), RK4.
  Convective heating at the stagnation point uses Sutton-Graves.
* Burn time is chosen by sweeping candidate burn times over the next
  ``search_hours`` and predicting the impact point for each (ground track
  shifts westward ~22.5 deg per orbit because Earth rotates underneath).
* Cross-range is closed with a constant bank angle found by bisection.

Real programs use much higher fidelity (J2, atmospheric tables, Monte Carlo
dispersions, predictor-corrector guidance like Apollo/Orion PredGuid). This is a
hobby simulation, not flight software.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import atmosphere
from .constants import (
    DEG,
    ENTRY_INTERFACE_ALT,
    G0,
    MU_EARTH,
    OMEGA_EARTH,
    R_EARTH_MEAN,
    SUTTON_GRAVES_K_EARTH,
)
from .mathutil import mat_vec, rot_x, rot_z
from .navigation import (
    destination_point,
    ecef_to_geodetic,
    eci_to_ecef,
    great_circle_distance_m,
    initial_bearing_deg,
)

# --------------------------------------------------------------------------- landing sites


@dataclass(frozen=True)
class LandingSite:
    """A recovery site and its constraints."""

    name: str
    lat_deg: float
    lon_deg: float
    kind: str                      # "land" (propulsive) or "water" (splashdown)
    landing_ellipse_km: float      # acceptable 3-sigma miss radius
    max_crossrange_km: float       # cross-range we may fly to reach it
    notes: str = ""


LANDING_SITES: dict[str, LandingSite] = {
    s.name: s
    for s in (
        LandingSite("cape-canaveral-lz1", 28.4858, -80.5428, "land", 0.5, 400.0,
                    "Propulsive landing pad, Cape Canaveral SFS, Florida"),
        LandingSite("pacific-splashdown", 32.50, -118.20, "water", 15.0, 600.0,
                    "Recovery zone off Southern California"),
        LandingSite("gulf-of-mexico", 29.60, -85.90, "water", 15.0, 600.0,
                    "Recovery zone off Panama City, Florida"),
        LandingSite("bonneville-salt-flats", 40.7600, -113.8900, "land", 2.0, 500.0,
                    "Dry lakebed, Utah. Very flat. Very salty."),
        LandingSite("woomera", -30.95, 136.53, "land", 5.0, 500.0,
                    "Woomera Range Complex, South Australia"),
    )
}


def get_site(name: str) -> LandingSite:
    key = name.strip().lower().replace(" ", "-").replace("_", "-")
    if key in LANDING_SITES:
        return LANDING_SITES[key]
    matches = [s for k, s in LANDING_SITES.items() if key in k]
    if len(matches) == 1:
        return matches[0]
    raise KeyError(f"unknown landing site {name!r}; choose from {sorted(LANDING_SITES)}")


# --------------------------------------------------------------------------- vehicle / orbit


@dataclass
class EntryVehicle:
    """Capsule-like entry vehicle parameters (Dragon/Soyuz order of magnitude)."""

    mass_kg: float = 4_200.0
    ballistic_coeff_kg_m2: float = 380.0     # m / (Cd A)
    lift_to_drag: float = 0.27
    nose_radius_m: float = 2.3
    max_g: float = 8.0                       # payload (crystal) limit
    max_heat_flux_w_m2: float = 1.6e6        # heat-shield limit (160 W/cm^2)
    isp_s: float = 300.0                     # deorbit thrusters
    propellant_kg: float = 850.0


@dataclass
class CircularOrbit:
    """Circular orbit state at ``epoch``: altitude, inclination, RAAN, argument of latitude."""

    alt_m: float = 400_000.0
    inc_deg: float = 51.6
    raan_deg: float = 0.0
    arg_lat_deg: float = 0.0
    epoch: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))

    @property
    def radius(self) -> float:
        return R_EARTH_MEAN + self.alt_m

    @property
    def mean_motion(self) -> float:
        return math.sqrt(MU_EARTH / self.radius ** 3)

    @property
    def period_s(self) -> float:
        return 2 * math.pi / self.mean_motion

    def eci_at(self, t: datetime, extra_angle_rad: float = 0.0) -> tuple[float, float, float]:
        """ECI position at time ``t`` (plus an optional extra along-track angle)."""
        u = math.radians(self.arg_lat_deg) + self.mean_motion * (t - self.epoch).total_seconds() + extra_angle_rad
        p = (self.radius * math.cos(u), self.radius * math.sin(u), 0.0)
        return mat_vec(rot_z(math.radians(self.raan_deg)), mat_vec(rot_x(math.radians(self.inc_deg)), p))

    def subpoint(self, t: datetime, extra_angle_rad: float = 0.0, extra_time_s: float = 0.0) -> tuple[float, float]:
        """Geodetic lat/lon under the vehicle (``extra_time_s`` lets Earth keep rotating)."""
        r = self.eci_at(t, extra_angle_rad)
        lat, lon, _ = ecef_to_geodetic(*eci_to_ecef(r, t + timedelta(seconds=extra_time_s)))
        return lat, lon


# --------------------------------------------------------------------------- deorbit burn


@dataclass
class DeorbitBurn:
    delta_v_mps: float
    propellant_kg: float
    burn_duration_s: float
    transfer_sma_m: float
    transfer_ecc: float
    coast_to_ei_s: float
    coast_angle_deg: float
    ei_speed_mps: float
    ei_flight_path_deg: float


def deorbit_delta_v(orbit_alt_m: float, target_perigee_alt_m: float) -> float:
    """Retrograde delta-v (m/s) to lower perigee of a circular orbit (vis-viva).

    400 km circular -> 50 km perigee is about 115 m/s.
    """
    r1 = R_EARTH_MEAN + orbit_alt_m
    rp = R_EARTH_MEAN + target_perigee_alt_m
    if rp >= r1:
        raise ValueError("target perigee must be below current orbit")
    a = (r1 + rp) / 2.0
    v_circ = math.sqrt(MU_EARTH / r1)
    v_apo = math.sqrt(MU_EARTH * (2.0 / r1 - 1.0 / a))
    return v_circ - v_apo


def plan_deorbit_burn(orbit: CircularOrbit, vehicle: EntryVehicle, target_perigee_alt_m: float = 50_000.0,
                      thrust_n: float = 4 * 400.0) -> DeorbitBurn:
    """Size the deorbit burn and compute the coast arc from burn to entry interface."""
    dv = deorbit_delta_v(orbit.alt_m, target_perigee_alt_m)
    ve = vehicle.isp_s * G0
    prop = vehicle.mass_kg * (1.0 - math.exp(-dv / ve))   # Tsiolkovsky
    duration = prop * ve / thrust_n
    r1 = orbit.radius
    rp = R_EARTH_MEAN + target_perigee_alt_m
    a = (r1 + rp) / 2.0
    e = (r1 - rp) / (r1 + rp)
    r_ei = R_EARTH_MEAN + ENTRY_INTERFACE_ALT
    p = a * (1 - e * e)
    cos_nu = (p / r_ei - 1.0) / e
    if cos_nu > 1:
        raise ValueError("transfer orbit does not reach entry interface")
    nu_ei = 2 * math.pi - math.acos(max(-1.0, cos_nu))   # descending leg, after apoapsis (nu = pi)

    def mean_anom(nu: float) -> float:
        E = 2 * math.atan2(math.sqrt(1 - e) * math.sin(nu / 2), math.sqrt(1 + e) * math.cos(nu / 2))
        return (E - e * math.sin(E)) % (2 * math.pi)

    n_t = math.sqrt(MU_EARTH / a ** 3)
    coast = (mean_anom(nu_ei) - mean_anom(math.pi)) / n_t
    v_ei = math.sqrt(MU_EARTH * (2 / r_ei - 1 / a))
    h = math.sqrt(MU_EARTH * p)
    gamma = -math.degrees(math.acos(min(1.0, h / (r_ei * v_ei))))
    return DeorbitBurn(dv, prop, duration, a, e, coast, math.degrees(nu_ei - math.pi), v_ei, gamma)


# --------------------------------------------------------------------------- entry simulation


@dataclass
class EntryResult:
    downrange_km: float
    crossrange_km: float
    duration_s: float
    peak_g: float
    peak_heat_flux_w_m2: float
    peak_dynamic_pressure_pa: float
    blackout_s: float
    final_speed_mps: float
    terminal_alt_m: float
    trajectory: list[dict] = field(default_factory=list, repr=False)


def simulate_entry(v0: float, gamma0_deg: float, vehicle: EntryVehicle, bank_deg: float = 0.0,
                   h0: float = ENTRY_INTERFACE_ALT, terminal_alt_m: float = 3_000.0, dt: float = 0.5,
                   record_every_s: float = 10.0) -> EntryResult:
    """Integrate a lifting entry from EI down to ``terminal_alt_m`` (parachutes / landing burn).

    State: speed v, flight-path angle gamma, altitude h, heading psi (relative to
    the initial ground track), downrange s, crossrange c. Constant bank angle.
    """
    beta = vehicle.ballistic_coeff_kg_m2
    ld = vehicle.lift_to_drag
    sb, cb = math.sin(math.radians(bank_deg)), math.cos(math.radians(bank_deg))

    def deriv(y):
        v, g, h, psi = y[0], y[1], y[2], y[3]
        r = R_EARTH_MEAN + h
        rho = atmosphere.density(h)
        d = 0.5 * rho * v * v / beta            # drag accel
        lft = d * ld
        grav = MU_EARTH / (r * r)
        dv = -d - grav * math.sin(g)
        dg = (lft * cb - (grav - v * v / r) * math.cos(g)) / max(v, 1.0)
        dh = v * math.sin(g)
        dpsi = lft * sb / (max(v, 1.0) * max(math.cos(g), 1e-3))
        ds = v * math.cos(g) * math.cos(psi) * R_EARTH_MEAN / r
        dc = v * math.cos(g) * math.sin(psi) * R_EARTH_MEAN / r
        return (dv, dg, dh, dpsi, ds, dc), d, lft

    y = (v0, math.radians(gamma0_deg), h0, 0.0, 0.0, 0.0)
    t = 0.0
    peak_g = peak_q = peak_heat = blackout = 0.0
    traj: list[dict] = []
    next_rec = 0.0
    while y[2] > terminal_alt_m and t < 3_600.0:
        k1, d, lft = deriv(y)
        k2, _, _ = deriv(tuple(a + 0.5 * dt * b for a, b in zip(y, k1)))
        k3, _, _ = deriv(tuple(a + 0.5 * dt * b for a, b in zip(y, k2)))
        k4, _, _ = deriv(tuple(a + dt * b for a, b in zip(y, k3)))
        rho = atmosphere.density(y[2])
        gl = math.hypot(d, lft) / G0
        heat = SUTTON_GRAVES_K_EARTH * math.sqrt(rho / vehicle.nose_radius_m) * y[0] ** 3
        q = 0.5 * rho * y[0] ** 2
        peak_g, peak_heat, peak_q = max(peak_g, gl), max(peak_heat, heat), max(peak_q, q)
        if 40_000 <= y[2] <= 90_000 and y[0] > 4_500:
            blackout += dt
        if t >= next_rec:
            traj.append({"t_s": round(t, 1), "alt_km": round(y[2] / 1000, 2), "speed_mps": round(y[0], 1),
                         "fpa_deg": round(math.degrees(y[1]), 2), "g": round(gl, 2),
                         "heat_w_cm2": round(heat / 1e4, 1), "downrange_km": round(y[4] / 1000, 1)})
            next_rec += record_every_s
        y = tuple(a + dt / 6 * (b1 + 2 * b2 + 2 * b3 + b4) for a, b1, b2, b3, b4 in zip(y, k1, k2, k3, k4))
        t += dt
    return EntryResult(y[4] / 1000, y[5] / 1000, t, peak_g, peak_heat, peak_q, blackout, y[0], y[2], traj)


def bank_for_crossrange(crossrange_km: float, v0: float, gamma0_deg: float, vehicle: EntryVehicle,
                        max_bank_deg: float = 80.0) -> tuple[float, EntryResult]:
    """Constant bank angle (deg, signed) that produces the requested cross-range.

    Cross-range grows with bank angle only up to a point (too much bank spends
    the lift sideways, the vehicle sinks and the entry gets short), so we first
    scan for the bank angle of maximum cross-range, then bisect below it.
    Right-hand cross-range (positive) needs a positive (right) bank.
    """
    sign = 1.0 if crossrange_km >= 0 else -1.0
    want = abs(crossrange_km)
    scan = [(b, simulate_entry(v0, gamma0_deg, vehicle, b)) for b in range(0, int(max_bank_deg) + 1, 10)]
    b_max, r_max = max(scan, key=lambda br: abs(br[1].crossrange_km))
    if want >= abs(r_max.crossrange_km):
        return sign * b_max, simulate_entry(v0, gamma0_deg, vehicle, sign * b_max)
    lo, hi = 0.0, float(b_max)
    res = scan[0][1]
    for _ in range(20):
        mid = (lo + hi) / 2
        res = simulate_entry(v0, gamma0_deg, vehicle, sign * mid)
        if abs(res.crossrange_km) < want:
            lo = mid
        else:
            hi = mid
        if abs(abs(res.crossrange_km) - want) < 0.2:
            break
    return sign * mid, res


def max_bank_capability(v0: float, gamma0_deg: float, vehicle: EntryVehicle) -> float:
    """Bank angle (deg) that gives the maximum cross-range for this entry."""
    scan = [(b, simulate_entry(v0, gamma0_deg, vehicle, b).crossrange_km) for b in range(0, 81, 10)]
    return float(max(scan, key=lambda bc: bc[1])[0])


def _refine_burn(orbit, burn, vehicle, target, burn_t, nominal, v_ground, bank_limit):
    """Solve for (burn time, bank angle) so the predicted impact lands on ``target``.

    Coarse pass: burn time nulls the downrange error, bisection sets the bank.
    Fine pass: 2x2 Newton on (downrange error, cross-range error) with
    finite-difference Jacobian. Returns the best iterate seen:
    ``(miss_km, burn_t, bank_deg, entry, impact, crossrange_required_km)``.
    """
    v0, g0 = burn.ei_speed_mps, burn.ei_flight_path_deg
    entry = nominal
    bank = 0.0
    for _ in range(3):
        dr_err, cross, *_ = _target_relative(orbit, burn_t, burn, entry, target)
        burn_t += timedelta(seconds=dr_err / v_ground)
        dr_err, cross, *_ = _target_relative(orbit, burn_t, burn, entry, target)
        bank, entry = bank_for_crossrange(cross, v0, g0, vehicle)
    bank_limit = max(abs(bank), bank_limit)

    def evaluate(t_burn: datetime, bank_deg: float):
        e = simulate_entry(v0, g0, vehicle, bank_deg)
        d, c, lat_ei, lon_ei, brg = _target_relative(orbit, t_burn, burn, e, target)
        impact = predict_impact(lat_ei, lon_ei, brg, e)
        miss = great_circle_distance_m(*impact, target.lat_deg, target.lon_deg) / 1000
        return (d, c - e.crossrange_km), (miss, t_burn, bank_deg, e, impact, c)

    best = None
    for _ in range(15):
        (r1, r2), state = evaluate(burn_t, bank)
        if best is None or state[0] < best[0]:
            best = state
        if state[0] < 0.2:
            break
        (a1, a2), _ = evaluate(burn_t + timedelta(seconds=1.0), bank)
        (b1, b2), _ = evaluate(burn_t, bank + 0.5)
        j11, j21 = a1 - r1, a2 - r2                       # per second
        j12, j22 = (b1 - r1) / 0.5, (b2 - r2) / 0.5       # per degree
        det = j11 * j22 - j12 * j21
        if abs(det) < 1e-9:
            break
        d_t = (-r1 * j22 + r2 * j12) / det
        d_b = (-r2 * j11 + r1 * j21) / det
        burn_t += timedelta(seconds=max(-60.0, min(60.0, d_t)))
        bank = max(-bank_limit, min(bank_limit, bank + max(-10.0, min(10.0, d_b))))
    return best


# --------------------------------------------------------------------------- planner


@dataclass
class ReturnPlan:
    status: str                       # GO, DIVERT, NO_GO
    site: str
    requested_site: str
    burn_time_utc: str
    time_to_burn_s: float
    entry_interface_utc: str
    landing_utc: str
    burn: dict
    entry: dict
    bank_angle_deg: float
    predicted_impact: dict
    miss_distance_km: float
    crossrange_required_km: float
    constraints: dict
    reasons: list[str]
    dry_run: bool
    trajectory: list[dict] = field(default_factory=list)

    def to_dict(self, include_trajectory: bool = False) -> dict:
        d = asdict(self)
        if not include_trajectory:
            d.pop("trajectory")
        return d


def _along_cross(track_lat, track_lon, track_bearing, tgt_lat, tgt_lon):
    """Signed along-track and cross-track distance (km) of a target relative to a great circle.

    Along-track is negative when the target is behind the reference point;
    cross-track is positive when the target lies to the right of the track.
    """
    d13 = great_circle_distance_m(track_lat, track_lon, tgt_lat, tgt_lon) / R_EARTH_MEAN
    b13 = math.radians(initial_bearing_deg(track_lat, track_lon, tgt_lat, tgt_lon))
    b12 = math.radians(track_bearing)
    xt = math.asin(max(-1.0, min(1.0, math.sin(d13) * math.sin(b13 - b12))))
    at = math.acos(max(-1.0, min(1.0, math.cos(d13) / max(math.cos(xt), 1e-12))))
    if math.cos(b13 - b12) < 0:
        at = -at
    return at * R_EARTH_MEAN / 1000, xt * R_EARTH_MEAN / 1000


def _entry_geometry(orbit: CircularOrbit, burn_t: datetime, burn: DeorbitBurn):
    """Entry-interface point and ground-track bearing for a burn at ``burn_t``."""
    coast_ang = math.radians(burn.coast_angle_deg)
    lat_ei, lon_ei = orbit.subpoint(burn_t, coast_ang, burn.coast_to_ei_s)
    lat2, lon2 = orbit.subpoint(burn_t, coast_ang + 0.002, burn.coast_to_ei_s + 0.002 / orbit.mean_motion)
    return lat_ei, lon_ei, initial_bearing_deg(lat_ei, lon_ei, lat2, lon2)


def _target_relative(orbit, burn_t, burn, entry: EntryResult, target: LandingSite):
    """(downrange error km, cross-range km, EI lat, EI lon, bearing) for a burn time.

    Earth rotates east under the vehicle during entry, so the target is moved
    east by ``omega * t_entry`` to compare in the frame frozen at EI.
    """
    lat_ei, lon_ei, brg = _entry_geometry(orbit, burn_t, burn)
    tgt_lon = target.lon_deg + math.degrees(OMEGA_EARTH * entry.duration_s)
    along, cross = _along_cross(lat_ei, lon_ei, brg, target.lat_deg, tgt_lon)
    return along - entry.downrange_km, cross, lat_ei, lon_ei, brg


def predict_impact(lat_ei: float, lon_ei: float, bearing: float, entry: EntryResult) -> tuple[float, float]:
    """Impact point from the EI point, track bearing and a simulated entry."""
    lat_d, lon_d = destination_point(lat_ei, lon_ei, bearing, entry.downrange_km * 1000)
    # The heading along a great circle changes with distance; use the local track heading.
    lat_n, lon_n = destination_point(lat_ei, lon_ei, bearing, entry.downrange_km * 1000 + 1000.0)
    local_bearing = initial_bearing_deg(lat_d, lon_d, lat_n, lon_n)
    side = 90.0 if entry.crossrange_km >= 0 else -90.0
    lat_i, lon_i = destination_point(lat_d, lon_d, (local_bearing + side) % 360, abs(entry.crossrange_km) * 1000)
    return lat_i, (lon_i - math.degrees(OMEGA_EARTH * entry.duration_s) + 540) % 360 - 180


def return_to_earth(
    target: LandingSite,
    orbit: Optional[CircularOrbit] = None,
    vehicle: Optional[EntryVehicle] = None,
    now: Optional[datetime] = None,
    search_hours: float = 24.0,
    step_s: float = 20.0,
    target_perigee_alt_m: float = 50_000.0,
    allow_divert: bool = True,
    dry_run: bool = True,
) -> ReturnPlan:
    """Plan a return to ``target``: when to burn, how hard, and where we will land.

    Sweeps burn opportunities over the next ``search_hours``; for each, predicts
    the unguided impact and the cross-range needed. Picks the opportunity with
    the smallest cross-range, flies it out with a constant bank angle, then
    checks constraints (propellant, g-load, heating, cross-range, landing
    ellipse). If the target is infeasible and ``allow_divert`` is set, the
    best alternative site is evaluated and the plan comes back as ``DIVERT``.
    """
    orbit = orbit or CircularOrbit()
    vehicle = vehicle or EntryVehicle()
    now = now or orbit.epoch
    burn = plan_deorbit_burn(orbit, vehicle, target_perigee_alt_m)
    ballistic = simulate_entry(burn.ei_speed_mps, burn.ei_flight_path_deg, vehicle, bank_deg=0.0)
    # Nominal lifting entries fly ~60 deg bank to trade lift for range control; use it as reference.
    nominal = simulate_entry(burn.ei_speed_mps, burn.ei_flight_path_deg, vehicle, bank_deg=60.0)

    v_ground = orbit.radius * orbit.mean_motion * R_EARTH_MEAN / orbit.radius / 1000  # km/s along track
    capability_bank = max_bank_capability(burn.ei_speed_mps, burn.ei_flight_path_deg, vehicle)
    capability_km = abs(simulate_entry(burn.ei_speed_mps, burn.ei_flight_path_deg, vehicle,
                                       capability_bank).crossrange_km)

    # 1) Sweep burn times; keep the best (smallest cross-range) candidate per orbital pass.
    candidates: list[tuple[float, datetime]] = []
    t = now + timedelta(seconds=burn.burn_duration_s / 2 + 600)   # at least 10 min of prep
    end = now + timedelta(hours=search_hours)
    while t <= end:
        dr_err, cross, *_ = _target_relative(orbit, t, burn, nominal, target)
        # Downrange is fixed by fine-tuning the burn time; the pass geometry fixes cross-range.
        if abs(dr_err) < v_ground * step_s * 1.5:
            if candidates and (t - candidates[-1][1]).total_seconds() < orbit.period_s / 2:
                if abs(cross) < candidates[-1][0]:
                    candidates[-1] = (abs(cross), t)
            else:
                candidates.append((abs(cross), t))
        t += timedelta(seconds=step_s)
    if not candidates:
        raise RuntimeError("no deorbit opportunity found in the search window")
    candidates.sort(key=lambda c: c[0])
    feasible = [c for c in candidates if c[0] <= capability_km] or candidates[:1]

    # 2) Refine the best few passes; keep the one with the smallest predicted miss.
    best = None
    for _, t0 in feasible[:3]:
        cand = _refine_burn(orbit, burn, vehicle, target, t0, nominal, v_ground, capability_bank)
        if best is None or cand[0] < best[0]:
            best = cand
    miss, burn_t, bank, entry, (lat_i, lon_i), cross = best

    reasons: list[str] = []
    if burn.propellant_kg > vehicle.propellant_kg:
        reasons.append(f"insufficient propellant: need {burn.propellant_kg:.0f} kg, have {vehicle.propellant_kg:.0f} kg")
    if entry.peak_g > vehicle.max_g:
        reasons.append(f"peak g {entry.peak_g:.1f} exceeds crystal limit {vehicle.max_g:.1f}")
    if entry.peak_heat_flux_w_m2 > vehicle.max_heat_flux_w_m2:
        reasons.append(f"peak heat flux {entry.peak_heat_flux_w_m2/1e4:.0f} W/cm2 exceeds shield limit")
    if abs(cross) > capability_km:
        reasons.append(f"no pass within vehicle cross-range capability ({capability_km:.0f} km) "
                       f"in the next {search_hours:g} h; best pass needs {abs(cross):.0f} km")
    if abs(cross) > target.max_crossrange_km:
        reasons.append(f"cross-range {abs(cross):.0f} km exceeds site limit {target.max_crossrange_km:.0f} km")
    # The terminal phase (parachutes / landing burn + grid fins) can remove a few km of residual miss;
    # anything left beyond the ellipse after that is a constraint violation.
    terminal_authority_km = 25.0 if target.kind == "land" else 10.0
    if miss > target.landing_ellipse_km + terminal_authority_km:
        reasons.append(f"predicted miss {miss:.1f} km outside landing ellipse")

    status = "GO" if not reasons else "NO_GO"
    plan = ReturnPlan(
        status=status, site=target.name, requested_site=target.name,
        burn_time_utc=burn_t.replace(microsecond=0).isoformat(), time_to_burn_s=round((burn_t - now).total_seconds(), 1),
        entry_interface_utc=(burn_t + timedelta(seconds=burn.coast_to_ei_s)).replace(microsecond=0).isoformat(),
        landing_utc=(burn_t + timedelta(seconds=burn.coast_to_ei_s + entry.duration_s + 300)).replace(microsecond=0).isoformat(),
        burn={"delta_v_mps": round(burn.delta_v_mps, 1), "propellant_kg": round(burn.propellant_kg, 1),
              "duration_s": round(burn.burn_duration_s, 1), "attitude": "retrograde",
              "target_perigee_km": target_perigee_alt_m / 1000, "coast_to_ei_s": round(burn.coast_to_ei_s, 1)},
        entry={"ei_speed_mps": round(burn.ei_speed_mps, 1), "ei_flight_path_deg": round(burn.ei_flight_path_deg, 3),
               "duration_s": round(entry.duration_s, 1), "downrange_km": round(entry.downrange_km, 1),
               "crossrange_km": round(entry.crossrange_km, 1), "peak_g": round(entry.peak_g, 2),
               "peak_heat_flux_w_cm2": round(entry.peak_heat_flux_w_m2 / 1e4, 1),
               "peak_dynamic_pressure_kpa": round(entry.peak_dynamic_pressure_pa / 1e3, 1),
               "plasma_blackout_s": round(entry.blackout_s, 1),
               "ballistic_downrange_km": round(ballistic.downrange_km, 1)},
        bank_angle_deg=round(bank, 1),
        predicted_impact={"lat_deg": round(lat_i, 4), "lon_deg": round(lon_i, 4)},
        miss_distance_km=round(miss, 2), crossrange_required_km=round(cross, 1),
        constraints={"max_crossrange_km": target.max_crossrange_km, "landing_ellipse_km": target.landing_ellipse_km,
                     "max_g": vehicle.max_g, "max_heat_flux_w_cm2": vehicle.max_heat_flux_w_m2 / 1e4,
                     "propellant_available_kg": vehicle.propellant_kg, "site_kind": target.kind,
                     "vehicle_crossrange_capability_km": round(capability_km, 1)},
        reasons=reasons, dry_run=dry_run, trajectory=entry.trajectory,
    )
    if status == "NO_GO" and allow_divert:
        for alt in sorted(LANDING_SITES.values(), key=lambda s: great_circle_distance_m(
                target.lat_deg, target.lon_deg, s.lat_deg, s.lon_deg)):
            if alt.name == target.name:
                continue
            alt_plan = return_to_earth(alt, orbit, vehicle, now, search_hours, step_s, target_perigee_alt_m,
                                       allow_divert=False, dry_run=dry_run)
            if alt_plan.status == "GO":
                alt_plan.status = "DIVERT"
                alt_plan.requested_site = target.name
                alt_plan.reasons = [f"{target.name}: {r}" for r in reasons]
                return alt_plan
    return plan

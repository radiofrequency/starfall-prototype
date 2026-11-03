"""Mission phase state machine, interlocks and progress reporting.

The vehicle walks through a fixed sequence of phases. Every transition is
checked against *guards* (physical conditions that must hold, e.g. "altitude
is at or below entry interface") and *interlocks* (safety inhibits that block
a transition until cleared, e.g. "crystal furnace still hot"). ABORT is
reachable from any phase that is not already terminal.

    PRELAUNCH -> ASCENT -> ORBIT_INSERTION -> ON_ORBIT_CRYSTAL_GROWTH
      -> DEORBIT_PREP -> DEORBIT_BURN -> ENTRY_INTERFACE -> PEAK_HEATING
      -> SUPERSONIC_DESCENT -> TERMINAL -> LANDING_BURN -> LANDED

Part of a fictional hobby simulation; not flight software.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional

from .constants import ENTRY_INTERFACE_ALT, MU_EARTH, R_EARTH_MEAN


class Phase(str, Enum):
    PRELAUNCH = "PRELAUNCH"
    ASCENT = "ASCENT"
    ORBIT_INSERTION = "ORBIT_INSERTION"
    ON_ORBIT_CRYSTAL_GROWTH = "ON_ORBIT_CRYSTAL_GROWTH"
    DEORBIT_PREP = "DEORBIT_PREP"
    DEORBIT_BURN = "DEORBIT_BURN"
    ENTRY_INTERFACE = "ENTRY_INTERFACE"
    PEAK_HEATING = "PEAK_HEATING"
    SUPERSONIC_DESCENT = "SUPERSONIC_DESCENT"
    TERMINAL = "TERMINAL"
    LANDING_BURN = "LANDING_BURN"
    LANDED = "LANDED"
    ABORT = "ABORT"


NOMINAL_SEQUENCE = [
    Phase.PRELAUNCH, Phase.ASCENT, Phase.ORBIT_INSERTION, Phase.ON_ORBIT_CRYSTAL_GROWTH,
    Phase.DEORBIT_PREP, Phase.DEORBIT_BURN, Phase.ENTRY_INTERFACE, Phase.PEAK_HEATING,
    Phase.SUPERSONIC_DESCENT, Phase.TERMINAL, Phase.LANDING_BURN, Phase.LANDED,
]
TERMINAL_PHASES = {Phase.LANDED, Phase.ABORT}

# Allowed transitions: the nominal next phase, plus a few legitimate loops.
ALLOWED: dict[Phase, set[Phase]] = {p: {n} for p, n in zip(NOMINAL_SEQUENCE, NOMINAL_SEQUENCE[1:])}
ALLOWED[Phase.DEORBIT_PREP].add(Phase.ON_ORBIT_CRYSTAL_GROWTH)   # wave-off: stay in orbit, keep growing
ALLOWED[Phase.LANDED] = set()
ALLOWED[Phase.ABORT] = set()

# Rough expected durations (s) used for the "next event" ETA.
NOMINAL_DURATION_S = {
    Phase.PRELAUNCH: 3_600, Phase.ASCENT: 540, Phase.ORBIT_INSERTION: 2_700,
    Phase.ON_ORBIT_CRYSTAL_GROWTH: 14 * 86_400, Phase.DEORBIT_PREP: 5_400, Phase.DEORBIT_BURN: 270,
    Phase.ENTRY_INTERFACE: 1_900, Phase.PEAK_HEATING: 240, Phase.SUPERSONIC_DESCENT: 420,
    Phase.TERMINAL: 180, Phase.LANDING_BURN: 25,
}


class TransitionError(RuntimeError):
    """Raised when a phase transition is not allowed; ``reasons`` lists why."""

    def __init__(self, src: Phase, dst: Phase, reasons: list[str]):
        super().__init__(f"{src.value} -> {dst.value} blocked: " + "; ".join(reasons))
        self.src, self.dst, self.reasons = src, dst, reasons


@dataclass
class CrystalBatch:
    """The on-orbit crystal growth payload."""

    target_mass_g: float = 1_200.0
    mass_g: float = 0.0
    lattice_quality: float = 1.0       # 1.0 = perfect; degrades with vibration / temperature excursions
    furnace_temp_c: float = 20.0
    sealed: bool = False

    @property
    def complete(self) -> bool:
        return self.mass_g >= self.target_mass_g

    def grow(self, dt_s: float, micro_g_level: float = 1e-6, temp_c: float = 1_050.0,
             rate_g_per_h: float = 4.0) -> None:
        """Advance growth. Quality drops when acceleration noise exceeds 1e-5 g or temp drifts."""
        if self.sealed:
            return
        self.furnace_temp_c = temp_c
        self.mass_g = min(self.target_mass_g, self.mass_g + rate_g_per_h * dt_s / 3600.0)
        penalty = max(0.0, math.log10(max(micro_g_level, 1e-9) / 1e-5)) * 1e-6 * dt_s
        penalty += abs(temp_c - 1_050.0) / 1_000.0 * 1e-6 * dt_s
        self.lattice_quality = max(0.0, self.lattice_quality - penalty)

    def seal(self) -> None:
        self.sealed = True
        self.furnace_temp_c = 20.0


@dataclass
class VehicleState:
    """Snapshot of the vehicle used by guards, interlocks and reporting."""

    altitude_m: float = 0.0
    speed_mps: float = 0.0
    apogee_alt_m: float = 0.0
    perigee_alt_m: float = 0.0
    inclination_deg: float = 51.6
    mach: float = 0.0
    heat_flux_w_m2: float = 0.0
    propellant_kg: float = 850.0
    propellant_required_kg: float = 150.0
    battery_soc: float = 1.0
    attitude_valid: bool = True           # star tracker solution available
    heat_shield_temp_c: float = 20.0
    heat_shield_limit_c: float = 1_650.0
    avionics_temp_c: float = 22.0
    avionics_limit_c: float = 60.0
    battery_temp_c: float = 18.0
    battery_limit_c: float = 45.0
    landing_site: Optional[str] = None
    range_safety_go: bool = True
    weather_go: bool = True
    hatch_closed: bool = True

    @property
    def orbit_sma_m(self) -> float:
        return R_EARTH_MEAN + (self.apogee_alt_m + self.perigee_alt_m) / 2.0

    @property
    def orbit_period_s(self) -> float:
        """Keplerian period T = 2*pi*sqrt(a^3/mu)."""
        return 2 * math.pi * math.sqrt(self.orbit_sma_m ** 3 / MU_EARTH)


@dataclass
class Interlock:
    """A named safety inhibit. While ``active`` it blocks transitions into ``blocks``."""

    name: str
    description: str
    blocks: set[Phase]
    active: bool = False


Guard = Callable[["Mission"], list[str]]


def _guard(cond: bool, msg: str) -> list[str]:
    return [] if cond else [msg]


GUARDS: dict[Phase, Guard] = {
    Phase.ASCENT: lambda m: (
        _guard(m.vehicle.range_safety_go, "range safety NO-GO")
        + _guard(m.vehicle.weather_go, "launch weather NO-GO")
        + _guard(m.vehicle.hatch_closed, "hatch not closed")
        + _guard(m.vehicle.battery_soc >= 0.95, "battery below 95% at launch")
    ),
    Phase.ORBIT_INSERTION: lambda m: _guard(m.vehicle.altitude_m > 150_000, "altitude below 150 km"),
    Phase.ON_ORBIT_CRYSTAL_GROWTH: lambda m: _guard(
        m.vehicle.perigee_alt_m > 180_000, "perigee below 180 km: orbit not stable for growth"),
    Phase.DEORBIT_PREP: lambda m: _guard(
        m.crystal.complete or m.crystal.sealed, "crystal batch not complete or sealed"),
    Phase.DEORBIT_BURN: lambda m: (
        _guard(m.crystal.sealed, "crystal batch not sealed")
        + _guard(m.vehicle.propellant_kg >= m.vehicle.propellant_required_kg * 1.1,
                 "propellant below required + 10% reserve")
        + _guard(m.vehicle.attitude_valid, "no valid star-tracker attitude")
        + _guard(m.vehicle.battery_soc > 0.30, "battery at or below 30%")
        + _guard(m.vehicle.landing_site is not None, "no landing site selected")
    ),
    Phase.ENTRY_INTERFACE: lambda m: _guard(
        m.vehicle.altitude_m <= ENTRY_INTERFACE_ALT, "altitude above entry interface (120 km)"),
    Phase.PEAK_HEATING: lambda m: _guard(m.vehicle.heat_flux_w_m2 >= 1e5, "heat flux below 10 W/cm2"),
    Phase.SUPERSONIC_DESCENT: lambda m: _guard(
        m.vehicle.mach < 5.0 and m.vehicle.mach > 1.0, "Mach not in supersonic band (1-5)"),
    Phase.TERMINAL: lambda m: (
        _guard(m.vehicle.mach < 1.0, "still supersonic")
        + _guard(m.vehicle.altitude_m < 15_000, "above 15 km")
    ),
    Phase.LANDING_BURN: lambda m: (
        _guard(m.vehicle.altitude_m < 2_000, "above landing-burn ignition altitude (2 km)")
        + _guard(m.vehicle.propellant_kg > 50, "insufficient landing propellant")
    ),
    Phase.LANDED: lambda m: (
        _guard(m.vehicle.altitude_m < 2.0, "not on the ground")
        + _guard(m.vehicle.speed_mps < 1.0, "still moving")
    ),
}


def default_interlocks() -> list[Interlock]:
    return [
        Interlock("FURNACE_HOT", "Crystal furnace above 100 C; seal and cool before deorbit",
                  {Phase.DEORBIT_BURN}),
        Interlock("RCS_FAULT", "Reaction control fault; no attitude-critical burns",
                  {Phase.DEORBIT_BURN, Phase.LANDING_BURN}),
        Interlock("GROUND_HOLD", "Ground has commanded a hold", {Phase.ASCENT, Phase.DEORBIT_BURN}),
        Interlock("THERMAL_LIMIT", "A thermal margin is negative", {Phase.DEORBIT_BURN}),
    ]


@dataclass
class Mission:
    """The mission state machine.

    Use :meth:`transition` to move between phases; it raises
    :class:`TransitionError` with every failing guard and active interlock.
    """

    name: str = "STARFALL-1"
    launch_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    phase: Phase = Phase.PRELAUNCH
    vehicle: VehicleState = field(default_factory=VehicleState)
    crystal: CrystalBatch = field(default_factory=CrystalBatch)
    interlocks: list[Interlock] = field(default_factory=default_interlocks)
    history: list[tuple[str, str]] = field(default_factory=list)
    abort_reason: Optional[str] = None
    phase_entered: Optional[datetime] = None

    # -------------------------------------------------------------- transitions

    def interlock(self, name: str) -> Interlock:
        for i in self.interlocks:
            if i.name == name:
                return i
        raise KeyError(name)

    def set_interlock(self, name: str, active: bool) -> None:
        self.interlock(name).active = active

    def update_interlocks(self) -> None:
        """Re-derive automatic interlocks from the vehicle and payload state."""
        self.set_interlock("FURNACE_HOT", self.crystal.furnace_temp_c > 100.0)
        self.set_interlock("THERMAL_LIMIT", any(v < 0 for v in self.thermal_margins().values()))

    def check(self, dst: Phase) -> list[str]:
        """Reasons the transition to ``dst`` would be refused (empty list = allowed)."""
        if self.phase in TERMINAL_PHASES:
            return [f"mission is in terminal phase {self.phase.value}"]
        if dst is Phase.ABORT:
            return []
        if dst not in ALLOWED[self.phase]:
            return [f"{dst.value} is not reachable from {self.phase.value}"]
        self.update_interlocks()
        reasons = GUARDS.get(dst, lambda m: [])(self)
        reasons += [f"interlock {i.name}: {i.description}" for i in self.interlocks
                    if i.active and dst in i.blocks]
        return reasons

    def transition(self, dst: Phase, now: Optional[datetime] = None, reason: str = "") -> None:
        reasons = self.check(dst)
        if reasons:
            raise TransitionError(self.phase, dst, reasons)
        now = now or datetime.now(timezone.utc)
        self.history.append((now.isoformat(), f"{self.phase.value}->{dst.value}"))
        if dst is Phase.ABORT:
            self.abort_reason = reason or "commanded abort"
        self.phase = dst
        self.phase_entered = now

    def abort(self, reason: str, now: Optional[datetime] = None) -> None:
        self.transition(Phase.ABORT, now, reason)

    # -------------------------------------------------------------- reporting

    def thermal_margins(self) -> dict[str, float]:
        v = self.vehicle
        return {
            "heat_shield_c": round(v.heat_shield_limit_c - v.heat_shield_temp_c, 1),
            "avionics_c": round(v.avionics_limit_c - v.avionics_temp_c, 1),
            "battery_c": round(v.battery_limit_c - v.battery_temp_c, 1),
        }

    def next_event(self) -> Optional[Phase]:
        if self.phase in TERMINAL_PHASES:
            return None
        return NOMINAL_SEQUENCE[NOMINAL_SEQUENCE.index(self.phase) + 1]

    def progress(self, now: Optional[datetime] = None) -> dict:
        """Progress report as a dict (see :meth:`report_progress` for JSON)."""
        now = now or datetime.now(timezone.utc)
        self.update_interlocks()
        met = (now - self.launch_time).total_seconds()
        nxt = self.next_event()
        eta = None
        if nxt is not None:
            entered = self.phase_entered or self.launch_time
            eta = max(0.0, NOMINAL_DURATION_S.get(self.phase, 0) - (now - entered).total_seconds())
            if self.phase is Phase.ON_ORBIT_CRYSTAL_GROWTH and not self.crystal.complete:
                eta = (self.crystal.target_mass_g - self.crystal.mass_g) / 4.0 * 3600.0
        v = self.vehicle
        in_orbit = v.perigee_alt_m > 0
        return {
            "mission": self.name,
            "phase": self.phase.value,
            "met_s": round(met, 1),
            "met": _fmt_met(met),
            "orbit": {
                "altitude_km": round(v.altitude_m / 1000, 2),
                "apogee_km": round(v.apogee_alt_m / 1000, 2),
                "perigee_km": round(v.perigee_alt_m / 1000, 2),
                "inclination_deg": v.inclination_deg,
                "period_min": round(v.orbit_period_s / 60, 2) if in_orbit else None,
            },
            "crystal": {
                "mass_g": round(self.crystal.mass_g, 1),
                "target_mass_g": self.crystal.target_mass_g,
                "percent_complete": round(100 * self.crystal.mass_g / self.crystal.target_mass_g, 1),
                "lattice_quality": round(self.crystal.lattice_quality, 5),
                "sealed": self.crystal.sealed,
            },
            "propellant_kg": round(v.propellant_kg, 1),
            "battery_soc_pct": round(100 * v.battery_soc, 1),
            "thermal_margins": self.thermal_margins(),
            "active_interlocks": [i.name for i in self.interlocks if i.active],
            "landing_site": v.landing_site,
            "next_event": nxt.value if nxt else None,
            "next_event_eta_s": round(eta, 1) if eta is not None else None,
            "next_event_utc": (now + timedelta(seconds=eta)).replace(microsecond=0).isoformat()
            if eta is not None else None,
            "abort_reason": self.abort_reason,
        }

    def report_progress(self, now: Optional[datetime] = None, indent: Optional[int] = 2) -> str:
        """JSON progress report: phase, MET, orbit, crystal batch, consumables, margins, next event + ETA."""
        return json.dumps(self.progress(now), indent=indent)


def _fmt_met(seconds: float) -> str:
    sign = "-" if seconds < 0 else "+"
    s = int(abs(seconds))
    d, s = divmod(s, 86_400)
    h, s = divmod(s, 3_600)
    m, s = divmod(s, 60)
    return f"T{sign}{d:03d}/{h:02d}:{m:02d}:{s:02d}"


def demo_mission(now: Optional[datetime] = None) -> Mission:
    """A mission six days into crystal growth on a 400 km, 51.6 deg orbit (used by the CLI)."""
    now = now or datetime.now(timezone.utc)
    m = Mission(launch_time=now - timedelta(days=6, hours=3, minutes=12))
    m.vehicle.altitude_m = 405_000
    t = m.launch_time
    for ph in NOMINAL_SEQUENCE[1:3]:
        m.transition(ph, t)
        t += timedelta(minutes=10)
    m.vehicle.apogee_alt_m, m.vehicle.perigee_alt_m = 412_000, 398_000
    m.transition(Phase.ON_ORBIT_CRYSTAL_GROWTH, t)
    m.crystal.grow((now - t).total_seconds(), micro_g_level=2e-5)
    m.vehicle.propellant_kg = 812.0
    m.vehicle.battery_soc = 0.87
    m.vehicle.heat_shield_temp_c = -45.0
    m.vehicle.avionics_temp_c = 31.0
    m.vehicle.battery_temp_c = 21.0
    m.vehicle.landing_site = "bonneville-salt-flats"
    return m

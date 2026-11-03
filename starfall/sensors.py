"""Simulated onboard sensor suite.

Each sensor returns a frozen dataclass with explicit units in its field names
(``_dps`` degrees/second, ``_mps2`` metres/second^2, ``_pa`` pascals, ``_k``
kelvin, ...). Noise levels are in the range of real flight hardware
(tactical-grade MEMS/FOG IMU, arcsecond-class star tracker, space GNSS receiver)
but the numbers are illustrative, not from any specific datasheet.

The ``SensorSuite`` samples a ``VehicleTruth`` (what the vehicle is *really*
doing) and produces noisy, sometimes-invalid measurements, including:

* GNSS loss during plasma blackout and above COCOM limits (if the receiver is
  not a space-grade unit),
* star-tracker loss at high angular rates or when the vehicle is in the
  atmosphere,
* radar altimeter / laser rangefinder only valid inside their range.
"""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from typing import Optional

from . import atmosphere
from .constants import G0
from .mathutil import Quat, q_from_axis_angle, q_mul, q_normalize

# --------------------------------------------------------------------------- truth state


@dataclass
class VehicleTruth:
    """Ground-truth vehicle state fed to the sensor models (SI units)."""

    lat_deg: float = 28.5
    lon_deg: float = -80.6
    alt_m: float = 400_000.0
    speed_mps: float = 7_670.0
    vertical_speed_mps: float = 0.0
    heading_deg: float = 45.0
    attitude_q: Quat = (1.0, 0.0, 0.0, 0.0)
    body_rate_dps: tuple[float, float, float] = (0.0, 0.05, 0.0)
    accel_mps2: tuple[float, float, float] = (0.0, 0.0, 0.0)  # non-gravitational (specific force)
    heat_flux_w_m2: float = 0.0
    heat_shield_temp_k: float = 250.0
    skin_temp_k: float = 280.0
    growth_chamber_temp_k: float = 291.15
    propellant_kg: float = 850.0
    tank_pressure_pa: float = 2.0e6
    tank_temp_k: float = 293.0
    battery_soc: float = 0.86
    load_current_a: float = 18.0
    engine_on: bool = False
    throttle: float = 0.0
    grid_fins_deployed: bool = False
    grid_fin_cmd_deg: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    rcs_firing: tuple[int, ...] = ()
    sun_vector_body: tuple[float, float, float] = (0.0, 0.6, 0.8)
    mag_field_body_nt: tuple[float, float, float] = (21_000.0, -3_500.0, 38_000.0)
    in_eclipse: bool = False
    distance_to_ground_m: Optional[float] = None  # defaults to alt_m

    @property
    def plasma_blackout(self) -> bool:
        """Rough RF blackout envelope: 40-90 km altitude at > 4.5 km/s."""
        return 40_000.0 <= self.alt_m <= 90_000.0 and self.speed_mps > 4_500.0


# --------------------------------------------------------------------------- readings


@dataclass(frozen=True)
class ImuReading:
    gyro_dps: tuple[float, float, float]
    accel_mps2: tuple[float, float, float]
    gyro_bias_dps: tuple[float, float, float]  # current (unknown to FSW) bias, for diagnostics
    temp_k: float
    valid: bool = True


@dataclass(frozen=True)
class StarTrackerReading:
    quaternion: Optional[Quat]
    stars_tracked: int
    valid: bool
    accuracy_arcsec: Optional[float]
    status: str


@dataclass(frozen=True)
class GnssReading:
    lat_deg: Optional[float]
    lon_deg: Optional[float]
    alt_m: Optional[float]
    speed_mps: Optional[float]
    satellites: int
    pdop: Optional[float]
    fix: str  # "3D", "NO_FIX"
    reason: str = ""


@dataclass(frozen=True)
class SunSensorReading:
    sun_vector_body: Optional[tuple[float, float, float]]
    in_eclipse: bool
    accuracy_deg: float = 0.5


@dataclass(frozen=True)
class HorizonSensorReading:
    nadir_vector_body: Optional[tuple[float, float, float]]
    earth_angular_radius_deg: Optional[float]
    valid: bool


@dataclass(frozen=True)
class MagnetometerReading:
    field_body_nt: tuple[float, float, float]
    magnitude_nt: float


@dataclass(frozen=True)
class AirDataReading:
    static_pressure_pa: float
    dynamic_pressure_pa: float
    mach: float


@dataclass(frozen=True)
class RangeReading:
    range_m: Optional[float]
    valid: bool
    max_range_m: float


@dataclass(frozen=True)
class PropulsionReading:
    tank_pressure_pa: float
    tank_temp_k: float
    propellant_kg: float
    chamber_pressure_pa: float
    thrust_n: float
    engine_on: bool


@dataclass(frozen=True)
class PowerReading:
    bus_voltage_v: float
    current_a: float
    state_of_charge: float
    solar_array_current_a: float


@dataclass(frozen=True)
class ThermalReading:
    heat_shield_k: float
    skin_k: float
    growth_chamber_k: float
    heat_flux_w_m2: float


@dataclass(frozen=True)
class RadiationReading:
    dose_rate_mgy_per_day: float
    total_dose_mgy: float
    saa: bool  # South Atlantic Anomaly crossing


@dataclass(frozen=True)
class ActuatorStateReading:
    grid_fins_deployed: bool
    grid_fin_deflection_deg: tuple[float, float, float, float]
    rcs_thrusters_firing: tuple[int, ...]
    rcs_thruster_count: int = 16


@dataclass(frozen=True)
class SensorFrame:
    """One synchronous sample of every sensor."""

    imu: ImuReading
    star_tracker: StarTrackerReading
    gnss: GnssReading
    sun: SunSensorReading
    horizon: HorizonSensorReading
    magnetometer: MagnetometerReading
    air_data: AirDataReading
    radar_altimeter: RangeReading
    laser_rangefinder: RangeReading
    propulsion: PropulsionReading
    power: PowerReading
    thermal: ThermalReading
    g_load: float
    radiation: RadiationReading
    actuators: ActuatorStateReading

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- suite


@dataclass
class SensorConfig:
    """Noise and limit parameters (1-sigma unless noted)."""

    gyro_noise_dps: float = 0.003           # angle random walk equivalent at 10 Hz
    gyro_bias_walk_dps: float = 1e-5        # bias random walk per sample
    gyro_initial_bias_dps: float = 0.002
    accel_noise_mps2: float = 0.002
    star_tracker_accuracy_arcsec: float = 5.0   # cross-boresight
    star_tracker_max_rate_dps: float = 2.0
    star_tracker_min_alt_m: float = 100_000.0   # no solution inside the sensible atmosphere
    gnss_pos_noise_m: float = 5.0
    gnss_vel_noise_mps: float = 0.05
    gnss_cocom_limited: bool = False        # space-grade receivers are exempt
    sun_noise_deg: float = 0.5
    horizon_noise_deg: float = 0.1
    mag_noise_nt: float = 50.0
    pressure_noise_frac: float = 0.01
    radar_max_range_m: float = 15_000.0
    radar_noise_frac: float = 0.005
    lidar_max_range_m: float = 2_000.0
    lidar_noise_m: float = 0.05
    tank_pressure_noise_pa: float = 2_000.0
    temp_noise_k: float = 0.5
    battery_cells_series: int = 8           # 8S Li-ion, 28 V class bus
    engine_max_thrust_n: float = 32_000.0
    engine_max_chamber_pa: float = 7.0e6
    rad_base_mgy_day: float = 0.35          # typical LEO dose rate behind shielding


class SensorSuite:
    """Stateful simulated sensors (bias drift, accumulated dose). Seedable for tests."""

    def __init__(self, config: Optional[SensorConfig] = None, seed: Optional[int] = None) -> None:
        self.cfg = config or SensorConfig()
        self.rng = random.Random(seed)
        b = self.cfg.gyro_initial_bias_dps
        self.gyro_bias = [self.rng.gauss(0, b) for _ in range(3)]
        self.total_dose_mgy = 0.0

    # ---- helpers
    def _g(self, sigma: float) -> float:
        return self.rng.gauss(0.0, sigma)

    def _vec_noise(self, v, sigma):
        return tuple(c + self._g(sigma) for c in v)

    # ---- individual sensors
    def imu(self, t: VehicleTruth) -> ImuReading:
        c = self.cfg
        self.gyro_bias = [b + self._g(c.gyro_bias_walk_dps) for b in self.gyro_bias]
        gyro = tuple(w + b + self._g(c.gyro_noise_dps) for w, b in zip(t.body_rate_dps, self.gyro_bias))
        acc = self._vec_noise(t.accel_mps2, c.accel_noise_mps2)
        return ImuReading(gyro, acc, tuple(self.gyro_bias), 300.0 + self._g(0.2))

    def star_tracker(self, t: VehicleTruth) -> StarTrackerReading:
        c = self.cfg
        rate = math.sqrt(sum(w * w for w in t.body_rate_dps))
        if t.alt_m < c.star_tracker_min_alt_m:
            return StarTrackerReading(None, 0, False, None, "IN_ATMOSPHERE")
        if rate > c.star_tracker_max_rate_dps:
            return StarTrackerReading(None, 0, False, None, "RATE_TOO_HIGH")
        sigma = math.radians(c.star_tracker_accuracy_arcsec / 3600.0)
        err = q_from_axis_angle((self._g(1), self._g(1), self._g(1)), abs(self._g(sigma)))
        n_stars = max(4, int(self.rng.gauss(12, 3)))
        return StarTrackerReading(q_normalize(q_mul(t.attitude_q, err)), n_stars, True, c.star_tracker_accuracy_arcsec, "TRACKING")

    def gnss(self, t: VehicleTruth) -> GnssReading:
        c = self.cfg
        if t.plasma_blackout:
            return GnssReading(None, None, None, None, 0, None, "NO_FIX", "PLASMA_BLACKOUT")
        if c.gnss_cocom_limited and t.speed_mps > 515.0 and t.alt_m > 18_000.0:
            return GnssReading(None, None, None, None, 0, None, "NO_FIX", "COCOM_LIMIT")
        sats = max(4, int(self.rng.gauss(10, 2)))
        pdop = round(max(1.0, 6.0 / math.sqrt(sats) + abs(self._g(0.3))), 2)
        pos_sigma = c.gnss_pos_noise_m * pdop / 2.0
        dlat = self._g(pos_sigma) / 111_320.0
        dlon = self._g(pos_sigma) / (111_320.0 * max(0.01, math.cos(math.radians(t.lat_deg))))
        return GnssReading(t.lat_deg + dlat, t.lon_deg + dlon, t.alt_m + self._g(pos_sigma * 1.5),
                           t.speed_mps + self._g(c.gnss_vel_noise_mps), sats, pdop, "3D")

    def sun(self, t: VehicleTruth) -> SunSensorReading:
        if t.in_eclipse:
            return SunSensorReading(None, True)
        v = self._vec_noise(t.sun_vector_body, math.radians(self.cfg.sun_noise_deg))
        n = math.sqrt(sum(x * x for x in v))
        return SunSensorReading(tuple(x / n for x in v), False, self.cfg.sun_noise_deg)

    def horizon(self, t: VehicleTruth) -> HorizonSensorReading:
        from .constants import R_EARTH_MEAN
        if t.alt_m < 20_000.0:
            return HorizonSensorReading(None, None, False)
        rho = math.degrees(math.asin(R_EARTH_MEAN / (R_EARTH_MEAN + t.alt_m)))
        nadir = self._vec_noise((0.0, 0.0, 1.0), math.radians(self.cfg.horizon_noise_deg))
        return HorizonSensorReading(nadir, rho + self._g(self.cfg.horizon_noise_deg), True)

    def magnetometer(self, t: VehicleTruth) -> MagnetometerReading:
        v = self._vec_noise(t.mag_field_body_nt, self.cfg.mag_noise_nt)
        return MagnetometerReading(v, math.sqrt(sum(x * x for x in v)))

    def air_data(self, t: VehicleTruth) -> AirDataReading:
        f = self.cfg.pressure_noise_frac
        ps = atmosphere.pressure(t.alt_m) * (1 + self._g(f))
        q = atmosphere.dynamic_pressure(t.alt_m, t.speed_mps) * (1 + self._g(f))
        return AirDataReading(max(ps, 0.0), max(q, 0.0), t.speed_mps / atmosphere.speed_of_sound(t.alt_m))

    def radar_altimeter(self, t: VehicleTruth) -> RangeReading:
        d = t.distance_to_ground_m if t.distance_to_ground_m is not None else t.alt_m
        mx = self.cfg.radar_max_range_m
        if d > mx:
            return RangeReading(None, False, mx)
        return RangeReading(max(0.0, d * (1 + self._g(self.cfg.radar_noise_frac))), True, mx)

    def laser_rangefinder(self, t: VehicleTruth) -> RangeReading:
        d = t.distance_to_ground_m if t.distance_to_ground_m is not None else t.alt_m
        mx = self.cfg.lidar_max_range_m
        if d > mx:
            return RangeReading(None, False, mx)
        return RangeReading(max(0.0, d + self._g(self.cfg.lidar_noise_m)), True, mx)

    def propulsion(self, t: VehicleTruth) -> PropulsionReading:
        c = self.cfg
        thr = t.throttle if t.engine_on else 0.0
        pc = c.engine_max_chamber_pa * thr * (1 + self._g(0.005)) if t.engine_on else abs(self._g(5_000))
        f = c.engine_max_thrust_n * thr * (1 + self._g(0.01)) if t.engine_on else 0.0
        return PropulsionReading(t.tank_pressure_pa + self._g(c.tank_pressure_noise_pa), t.tank_temp_k + self._g(c.temp_noise_k),
                                 max(0.0, t.propellant_kg + self._g(2.0)), pc, f, t.engine_on)

    def power(self, t: VehicleTruth) -> PowerReading:
        cells = self.cfg.battery_cells_series
        v_cell = 3.0 + 1.2 * t.battery_soc - 0.002 * t.load_current_a  # crude Li-ion OCV + IR drop
        solar = 0.0 if t.in_eclipse else 42.0 + self._g(0.5)
        return PowerReading(cells * v_cell + self._g(0.02), t.load_current_a + self._g(0.1), t.battery_soc, solar)

    def thermal(self, t: VehicleTruth) -> ThermalReading:
        n = self.cfg.temp_noise_k
        return ThermalReading(t.heat_shield_temp_k + self._g(n * 4), t.skin_temp_k + self._g(n),
                              t.growth_chamber_temp_k + self._g(n * 0.1), max(0.0, t.heat_flux_w_m2 * (1 + self._g(0.03))))

    def g_load(self, t: VehicleTruth) -> float:
        return max(0.0, math.sqrt(sum(a * a for a in t.accel_mps2)) / G0 + self._g(0.002))

    def radiation(self, t: VehicleTruth, dt_s: float = 1.0) -> RadiationReading:
        # South Atlantic Anomaly box (rough): lat -50..0, lon -90..40, only matters on orbit.
        saa = -50 <= t.lat_deg <= 0 and -90 <= t.lon_deg <= 40 and t.alt_m > 200_000
        rate = self.cfg.rad_base_mgy_day * (8.0 if saa else 1.0) * (1 + self._g(0.1))
        rate = max(0.0, rate) if t.alt_m > 100_000 else 0.0003
        self.total_dose_mgy += rate * dt_s / 86_400.0
        return RadiationReading(rate, self.total_dose_mgy, saa)

    def actuators(self, t: VehicleTruth) -> ActuatorStateReading:
        return ActuatorStateReading(t.grid_fins_deployed, tuple(t.grid_fin_cmd_deg), tuple(t.rcs_firing))

    # ---- all at once
    def sample(self, t: VehicleTruth, dt_s: float = 0.1) -> SensorFrame:
        """Sample every sensor once."""
        return SensorFrame(
            imu=self.imu(t), star_tracker=self.star_tracker(t), gnss=self.gnss(t), sun=self.sun(t),
            horizon=self.horizon(t), magnetometer=self.magnetometer(t), air_data=self.air_data(t),
            radar_altimeter=self.radar_altimeter(t), laser_rangefinder=self.laser_rangefinder(t),
            propulsion=self.propulsion(t), power=self.power(t), thermal=self.thermal(t),
            g_load=self.g_load(t), radiation=self.radiation(t, dt_s), actuators=self.actuators(t),
        )


def truth_for_phase(phase: str) -> VehicleTruth:
    """Representative truth states for demos: ``orbit``, ``blackout``, ``terminal``, ``landing``."""
    phase = phase.lower()
    if phase == "orbit":
        return VehicleTruth()
    if phase == "blackout":
        return VehicleTruth(alt_m=65_000, speed_mps=6_800, vertical_speed_mps=-120, accel_mps2=(-38.0, 0.0, 9.0),
                            heat_flux_w_m2=1.1e6, heat_shield_temp_k=1_850, skin_temp_k=420, body_rate_dps=(0.2, 1.5, 0.1))
    if phase == "terminal":
        return VehicleTruth(alt_m=9_000, speed_mps=290, vertical_speed_mps=-280, accel_mps2=(-9.5, 0.0, 0.5),
                            heat_shield_temp_k=900, skin_temp_k=380, grid_fins_deployed=True,
                            grid_fin_cmd_deg=(2.5, -1.0, 2.5, -1.0), rcs_firing=(3, 7))
    if phase == "landing":
        return VehicleTruth(alt_m=650, speed_mps=60, vertical_speed_mps=-58, accel_mps2=(0.0, 0.0, 24.0),
                            heat_shield_temp_k=600, skin_temp_k=350, engine_on=True, throttle=0.72,
                            propellant_kg=140, grid_fins_deployed=True)
    raise ValueError(f"unknown demo phase {phase!r}")

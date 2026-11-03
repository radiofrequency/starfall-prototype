# ✨ Starfall Prototype

> **Onboard control software for a crystal-producing starfall project.**
> We grow crystals in orbit. Then we drop them. On purpose. Beautifully.

[![build](https://img.shields.io/badge/build-crystalline-brightgreen)](#)
[![orbit](https://img.shields.io/badge/orbit-mostly%20stable-blue)](#)
[![lattice](https://img.shields.io/badge/lattice-hexagonal-purple)](#)
[![sky](https://img.shields.io/badge/sky-sparkly-ff69b4)](#)
[![insurance](https://img.shields.io/badge/insurance-pending-red)](#)

> **Note:** Starfall is fictional. The Python package in `starfall/` is a hobby
> simulation built from textbook physics. It is not real flight software, and it
> has never flown anything. See [Simulation Package](#simulation-package).

---

## Table of Contents

1. [Overview](#overview)
2. [Mission Statement](#mission-statement)
3. [Architecture](#architecture)
4. [Subsystems](#subsystems)
   - [Crystal Lattice Growth Chamber (CLGC)](#1-crystal-lattice-growth-chamber-clgc)
   - [Stellar-Dust Intake Manifold (SDIM)](#2-stellar-dust-intake-manifold-sdim)
   - [Plasma Kiln](#3-plasma-kiln)
   - [Orbital-Descent Guidance (ODG)](#4-orbital-descent-guidance-odg)
   - [Atmospheric-Ablation Shielding (AAS)](#5-atmospheric-ablation-shielding-aas)
   - [Meteor-Shower Scheduler (MSS)](#6-meteor-shower-scheduler-mss)
5. [Onboard Control API](#onboard-control-api)
6. [Telemetry](#telemetry)
7. [Safety Interlocks](#safety-interlocks)
8. [Installation & Build](#installation--build)
9. [Configuration](#configuration)
10. [Operating Procedures](#operating-procedures)
11. [Roadmap](#roadmap)
12. [FAQ](#faq)
13. [Known Issues](#known-issues)
14. [Glossary](#glossary)
15. [Simulation Package](#simulation-package)
16. [Usage](#usage)
17. [Changelog](#changelog)
18. [License](#license)

---

## Overview

**Starfall Prototype** is the flight software that runs aboard **STARFALL-1**, an
orbital crystal foundry parked at a respectable altitude above everyone's
weekend plans. The rig:

1. Hoovers up interstellar dust with a very large, very polite vacuum.
2. Grows flawless crystals in microgravity, where nothing sags and nobody
   bumps the table.
3. Fires them in a plasma kiln until they are "cosmically tempered" (a real
   term we made up).
4. Launches them back toward Earth on carefully choreographed descent paths so
   they burn in as **artisanal, hand-scheduled shooting stars**, with a
   regulation-approved fraction surviving to the ground as collectible gems.

In short: **we manufacture wishes.**

The software is responsible for every phase of the crystal lifecycle, from
"dust" to "ooooh" to "is that in my garden?".

### Key Features

- 🌌 Real-time stellar-dust ingestion with spectral sorting
- 💎 Lattice growth control to ±0.3 picometres (on a good day)
- 🔥 Plasma kiln with 14 firing profiles, including *Sunset Ember* and *Dragon Mode*
- 🛰️ Descent guidance with sub-hemisphere precision
- 🛡️ Ablation shielding that sacrifices itself so the crystal doesn't have to
- 📅 Meteor-shower scheduler with timezone support (and a wedding-proposal mode)
- 🧯 23 safety interlocks, 4 of which we fully understand

---

## Mission Statement

> *"To make the night sky slightly more expensive."*
> — Founding Engineer, shortly before the budget meeting

Secondary mission: produce the clearest, most symmetrical crystals in the known
universe, then throw them at the planet in the most romantic way possible.

---

## Architecture

```
                         ☀  (the Sun, not affiliated with this project)
                         │
   ┌─────────────────────┴──────────────────────────────────────────────┐
   │                        STARFALL-1 ORBITAL RIG                      │
   │                                                                    │
   │   ┌────────────────┐    dust     ┌───────────────────────────┐     │
   │   │ STELLAR-DUST   │───────────▶ │ CRYSTAL LATTICE GROWTH    │     │
   │   │ INTAKE MANIFOLD│  (sorted)   │ CHAMBER  (CLGC)           │     │
   │   │ (SDIM)         │             │  ◇ ◇ ◇ seeds ◇ ◇ ◇        │     │
   │   └───────┬────────┘             └────────────┬──────────────┘     │
   │           │ rejects (sneezed                  │ raw crystals       │
   │           │  back into space)                 ▼                    │
   │           ▼                      ┌───────────────────────────┐     │
   │      ~ ~ ~ ~ ~                   │ PLASMA KILN               │     │
   │                                  │  🔥 tempering @ 9,000 K    │     │
   │                                  └────────────┬──────────────┘     │
   │                                               │ tempered crystals  │
   │                                               ▼                    │
   │   ┌────────────────┐  wraps     ┌───────────────────────────┐      │
   │   │ ATMOSPHERIC-   │──────────▶ │ ORBITAL-DESCENT GUIDANCE  │      │
   │   │ ABLATION       │  shields   │ (ODG) + launch rail       │      │
   │   │ SHIELDING (AAS)│            └────────────┬──────────────┘      │
   │   └────────────────┘                         │                     │
   │                                               │ release window     │
   │   ┌──────────────────────────────┐            │                    │
   │   │ METEOR-SHOWER SCHEDULER (MSS)│◀───────────┘                    │
   │   │  "is it romantic o'clock?"   │                                 │
   │   └──────────────┬───────────────┘                                 │
   │                  │                                                 │
   │   ┌──────────────▼───────────────────────────────────────────┐     │
   │   │           ONBOARD CONTROL CORE  (starfalld)              │     │
   │   │   REST/JSON API · telemetry bus · interlock supervisor   │     │
   │   └──────────────┬───────────────────────────────────────────┘     │
   └──────────────────┼─────────────────────────────────────────────────┘
                      │  S-band uplink (and one very long USB cable)
                      ▼
            ┌───────────────────┐
            │  GROUND STATION   │   ✨  ✨   ✨     ← product
            │  "Mission Control"│      ✨       ✨
            │  (a garage)       │  🏠 ← customer
            └───────────────────┘
```

---

## Subsystems

### 1. Crystal Lattice Growth Chamber (CLGC)

The heart of the rig. A pressurised, vibration-isolated sphere where seed
crystals are suspended by magnetic tweezers and coaxed into growing via
carefully dosed vapour and a curated ambient playlist.

| Parameter | Value | Notes |
|---|---|---|
| Chamber volume | 2.4 m³ | Roughly one hot tub |
| Seed capacity | 64 seeds | 65 if you squeeze |
| Growth rate | 0.8 mm/hour | Faster rates cause "crystal anxiety" |
| Supported lattices | Hexagonal, cubic, trigonal, "vibes" | `vibes` is experimental |
| Ambient playlist | Lo-fi beats to nucleate to | Mandatory per SOP-12 |

**Control modes**

- `GROW_STEADY`: default; patient and wholesome.
- `GROW_TURBO`: twice as fast, half as clear, 100% more alarming.
- `GROW_HEIRLOOM`: single seed, 72-hour cycle, produces one crystal so pretty
  the telemetry bus pauses to look at it.
- `HOLD`: freeze growth. Crystals are told they are doing great.

### 2. Stellar-Dust Intake Manifold (SDIM)

A 40-metre deployable funnel that faces into the orbital wind and gathers
micrometeoroid dust, cosmic fluff, and the occasional lost glove.

- **Spectral sorter:** classifies particles into *silicates*, *carbonates*,
  *metallics*, *suspicious*, and *glove*.
- **Rejection port:** unwanted material is ejected retrograde with a gentle
  *pfft*. Engineers call this "the sneeze."
- **Clog detection:** if intake pressure drops by more than 12%, SDIM runs the
  `UNCLOG` routine (vigorous shaking, then an apology to the gyroscopes).

### 3. Plasma Kiln

A magnetically confined plasma oven that tempers crystals so they can survive
re-entry and still look fabulous.

| Firing profile | Peak temp | Result |
|---|---|---|
| `GENTLE_GLOW` | 3,200 K | Soft white sparkle |
| `SUNSET_EMBER` | 6,500 K | Warm orange trail |
| `AURORA_SHIMMER` | 7,800 K | Green-violet streak; very popular |
| `DRAGON_MODE` | 9,000 K | Unclear. Do not use on weekdays |
| `CRÈME_BRÛLÉE` | 1,150 K | Not for crystals. Morale feature |

The kiln is guarded by the `KILN_DOOR_CLOSED` and
`NOBODY_IS_MAKING_TOAST` interlocks.

### 4. Orbital-Descent Guidance (ODG)

Computes the release time, velocity vector, and spin rate needed to land each
crystal's fiery trail exactly where (and when) the customer has asked to see it.

- **Targeting accuracy:** ±4 km for visual effect, ±"somewhere in the
  county" for the surviving gem.
- **Trajectory solver:** a 9th-order integrator affectionately named *Gerald*.
- **No-fly zones:** airports, observatories during research hours, and
  anywhere that has filed a "please stop" letter.
- **Tumble control:** crystals are spun at 3 rev/s so they sparkle evenly.
  Higher rates are classified as "disco ball" and need sign-off.

### 5. Atmospheric-Ablation Shielding (AAS)

Each crystal is wrapped in a sacrificial ablative cocoon that burns away during
descent, producing the visible shooting-star trail.

- **Cocoon materials:** phenolic resin, aerogel, and a proprietary glitter
  composite (Patent Pending, Patent Laughed At).
- **Trail colour tuning:** dopants in the cocoon tint the trail:
  strontium (red), barium (green), copper (blue), optimism (gold).
- **Burn budget:** 92% of the shield burns off; the remaining 8% forms a
  charming little scorch-mark gift box.

### 6. Meteor-Shower Scheduler (MSS)

Turns a queue of tempered crystals into tastefully paced displays.

- Avoids clashing with natural showers (Perseids get first billing out of
  professional courtesy).
- Supports **cadence presets**: `DRIZZLE`, `SHOWER`, `DOWNPOUR`, `NEW_YEARS`.
- **Proposal mode:** schedules a single, perfectly timed bright fall, then
  cuts telemetry for 60 seconds out of respect.
- Weather-aware: will not drop crystals onto cloud cover unless the customer
  enables `I_JUST_WANT_TO_KNOW_ITS_HAPPENING`.

---

## Onboard Control API

`starfalld` exposes a JSON-over-HTTP API on the rig's internal bus (and,
regrettably, on a port someone forwarded once).

Base URL: `http://starfall-1.local:7777/api/v1`

### Commands

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/status` | Rig health summary |
| `POST` | `/clgc/grow` | Start a growth cycle |
| `POST` | `/clgc/hold` | Pause growth; issue encouragement |
| `POST` | `/sdim/intake` | Open/close the dust funnel |
| `POST` | `/sdim/sneeze` | Manually eject rejects |
| `POST` | `/kiln/fire` | Fire the plasma kiln with a profile |
| `POST` | `/odg/plan` | Compute descent for a crystal |
| `POST` | `/odg/release` | Release a crystal (requires 2 keys) |
| `POST` | `/mss/schedule` | Queue a meteor shower |
| `DELETE` | `/mss/schedule/{id}` | Cancel a show (refunds in wishes) |
| `GET` | `/telemetry/stream` | Server-sent telemetry events |
| `POST` | `/interlocks/override` | Don't. |

### Example: start a growth cycle

```http
POST /api/v1/clgc/grow
Content-Type: application/json

{
  "seed_slots": [1, 2, 3, 4],
  "lattice": "hexagonal",
  "mode": "GROW_STEADY",
  "target_size_mm": 42,
  "playlist": "lofi-nucleation-vol-3"
}
```

```json
{
  "cycle_id": "clgc-2026-11-03-0007",
  "state": "GROWING",
  "eta_hours": 52.5,
  "crystal_mood": "content",
  "warnings": []
}
```

### Example: fire the kiln

```http
POST /api/v1/kiln/fire
Content-Type: application/json

{
  "batch_id": "clgc-2026-11-03-0007",
  "profile": "AURORA_SHIMMER",
  "dwell_seconds": 420,
  "confirm_no_toast": true
}
```

```json
{
  "kiln_run_id": "kiln-8812",
  "peak_temp_k": 7800,
  "state": "TEMPERING",
  "interlocks": { "KILN_DOOR_CLOSED": "OK", "NOBODY_IS_MAKING_TOAST": "OK" }
}
```

### Example: schedule a meteor shower

```http
POST /api/v1/mss/schedule
Content-Type: application/json

{
  "crystals": ["cx-0441", "cx-0442", "cx-0443", "cx-0444", "cx-0445"],
  "cadence": "SHOWER",
  "target": { "lat": 13.7563, "lon": 100.5018, "radius_km": 25 },
  "window_local": { "start": "2026-12-31T23:58:00+07:00", "end": "2027-01-01T00:05:00+07:00" },
  "trail_colour": "gold",
  "proposal_mode": false
}
```

```json
{
  "show_id": "mss-31337",
  "status": "SCHEDULED",
  "visible_falls": 5,
  "expected_gems_recovered": 0.4,
  "romance_index": 0.87,
  "notes": "Clear skies forecast. Perseids notified out of courtesy."
}
```

### Example: release (two-key)

```bash
curl -X POST http://starfall-1.local:7777/api/v1/odg/release \
  -H "X-Key-Alpha: $KEY_ALPHA" \
  -H "X-Key-Bravo: $KEY_BRAVO" \
  -d '{"crystal_id":"cx-0441","plan_id":"odg-5521","countdown":10}'
```

Error codes:

| Code | Meaning |
|---|---|
| `409 CRYSTAL_NOT_READY` | Still growing. Let it cook. |
| `423 INTERLOCK_ENGAGED` | Something important said no |
| `451 UNAVAILABLE_FOR_ROMANTIC_REASONS` | Proposal mode active |
| `418 I'M_A_KILN` | You sent the toast command again |
| `507 OUT_OF_SKY` | Too many showers scheduled tonight |

---

## Telemetry

Telemetry streams at 10 Hz over `/telemetry/stream` as server-sent events.

```json
{
  "ts": "2026-11-03T12:00:00Z",
  "orbit": { "alt_km": 412.7, "inclination_deg": 51.6, "velocity_kms": 7.66 },
  "clgc": { "chamber_temp_k": 291.4, "vapour_ppm": 812, "active_seeds": 48,
            "avg_clarity": 0.993, "crystal_mood": "serene" },
  "sdim": { "intake_rate_mg_s": 3.1, "spectral_mix": { "silicate": 0.62,
            "carbonate": 0.21, "metallic": 0.15, "suspicious": 0.02, "glove": 0.0 } },
  "kiln": { "state": "IDLE", "plasma_temp_k": 0, "coil_health": 0.97 },
  "odg": { "queued_releases": 5, "gerald_status": "thinking" },
  "aas": { "cocoon_stock": 112, "glitter_reserve_pct": 64 },
  "mss": { "next_show": "mss-31337", "romance_index": 0.87 },
  "power": { "solar_kw": 38.2, "battery_pct": 81, "vibes": "immaculate" },
  "interlocks_tripped": []
}
```

| Field | Unit | Description |
|---|---|---|
| `orbit.alt_km` | km | Altitude above sea level (and above it all) |
| `clgc.avg_clarity` | 0–1 | 1.0 = invisible; 0.0 = a pebble |
| `clgc.crystal_mood` | enum | `serene`, `content`, `restless`, `dramatic` |
| `sdim.spectral_mix` | fraction | Composition of incoming dust |
| `kiln.coil_health` | 0–1 | Magnetic confinement coil condition |
| `odg.gerald_status` | enum | `idle`, `thinking`, `confident`, `sulking` |
| `aas.glitter_reserve_pct` | % | Must stay above 20% per brand guidelines |
| `mss.romance_index` | 0–1 | Proprietary metric. Do not ask how |
| `power.vibes` | enum | `immaculate`, `fine`, `off`, `cursed` |

---

## Safety Interlocks

The interlock supervisor runs at 1 kHz and has veto power over every command.

| ID | Interlock | Trips when |
|---|---|---|
| IL-01 | `KILN_DOOR_CLOSED` | Kiln door open during firing |
| IL-02 | `NOBODY_IS_MAKING_TOAST` | Bread detected in kiln |
| IL-03 | `TWO_KEY_RELEASE` | Fewer than two keys for `/odg/release` |
| IL-04 | `NO_FLY_ZONE` | Descent path crosses an airport, observatory, or ex |
| IL-05 | `CLOUD_COVER` | Target obscured; nobody would see it anyway |
| IL-06 | `GLITTER_FLOOR` | Glitter reserve < 20% |
| IL-07 | `GERALD_CONFIDENT` | Trajectory solver not confident |
| IL-08 | `PERSEIDS_COURTESY` | Clash with a natural meteor shower |
| IL-09 | `CRYSTAL_MOOD_OK` | Crystal is `dramatic` |
| IL-10 | `ORBIT_DECAY` | Altitude < 380 km; stop dropping, start boosting |
| IL-11 | `INTAKE_GLOVE` | Glove detected in SDIM. Return to owner |
| IL-12 | `HUMAN_IN_CHAMBER` | Someone climbed into the CLGC again |
| IL-13 | `CHRISTMAS_EVE` | Reserved airspace. Large sleigh traffic |
| IL-14 – IL-23 | *Classified* | You'll know |

Overrides require a signed request, a second engineer, and a written apology
to the crystals.

---

## Installation & Build

### Prerequisites

- Rust 1.92+ (flight core)
- Python 3.12+ (ground tooling)
- `protoc` 27+
- An orbital rig (sold separately)
- A sense of wonder

### Build

```bash
git clone https://github.com/radiofrequency/starfall-prototype.git
cd starfall-prototype
make bootstrap        # installs toolchains and one lucky charm
make build            # builds starfalld, gerald, and the ground console
make test             # runs 1,412 tests and one interpretive dance
make sim              # launches the orbital simulator (no real crystals harmed)
```

### Flash to the rig

```bash
./scripts/uplink.sh --target starfall-1 --image build/starfalld.img \
  --window "next-ground-pass" --checksum --pray
```

> ⚠️ Do **not** flash during an active meteor shower. The rig gets distracted.

### Ground console

```bash
starfall-console --rig starfall-1.local:7777
starfall> status
starfall> grow --seeds 1-8 --lattice hexagonal --mode GROW_STEADY
starfall> kiln fire --profile SUNSET_EMBER
starfall> shower schedule --cadence DRIZZLE --target "my backyard" --when tonight
starfall> make-a-wish
```

---

## Configuration

`/etc/starfall/starfall.toml`:

```toml
[rig]
name            = "STARFALL-1"
orbit_alt_km    = 412.7
timezone        = "Asia/Bangkok"
vibes           = "immaculate"

[clgc]
default_lattice = "hexagonal"
max_seeds       = 64
growth_mode     = "GROW_STEADY"
playlist        = "lofi-nucleation-vol-3"
allow_vibes_lattice = false   # experimental, see Known Issues

[sdim]
funnel_length_m = 40
sneeze_force_n  = 0.6
reject_classes  = ["suspicious", "glove"]

[kiln]
default_profile = "AURORA_SHIMMER"
allow_dragon_mode = false
creme_brulee_fridays = true

[odg]
solver          = "gerald"
tumble_rev_s    = 3.0
no_fly_zones    = "/etc/starfall/no-fly.geojson"

[aas]
cocoon_material = "phenolic+aerogel+glitter"
trail_colour    = "auto"     # red | green | blue | gold | auto
glitter_floor_pct = 20

[mss]
cadence          = "SHOWER"
respect_perseids = true
proposal_mode_silence_s = 60

[safety]
two_key_release  = true
interlock_rate_hz = 1000
apology_template = "/etc/starfall/sorry.txt"
```

---

## Operating Procedures

**SOP-01: Daily wake-up.** Check `/status`, review overnight telemetry, wish
the crystals good morning (logged).

**SOP-04: Dust storm.** Close SDIM, set CLGC to `HOLD`, put on the calming
playlist, wait it out.

**SOP-07: Gerald is sulking.** Restart the solver, feed it a simple
trajectory to rebuild its confidence, then resume operations.

**SOP-12: Ambient audio.** Lo-fi playlist must be playing during growth.
Silence causes faceting irregularities (unproven, strongly believed).

**SOP-19: Customer finds a gem.** Congratulate them. Remind them it is not
radioactive. Decline to explain why we had to say that.

---

## Roadmap

- [x] v0.1: Grow one crystal without it floating away
- [x] v0.3: Plasma kiln no longer makes toast by accident
- [x] v0.5: First successful shooting star (seen by 3 people and a goat)
- [x] v0.8: Gerald learns spherical trigonometry
- [ ] v1.0: Fully automated meteor showers on demand
- [ ] v1.2: Custom constellation drawing (`/mss/draw` with SVG input)
- [ ] v1.5: Multi-rig "Starfall Swarm" choreography
- [ ] v2.0: Crystal subscription box ("Wish of the Month Club")
- [ ] v3.0: Lunar branch office
- [ ] v∞: Make the night sky a little more delightful for everyone

---

## FAQ

**Is this safe?**
Extremely, by orbital-gemstone-bombardment standards.

**Can I request a shooting star over my house?**
Yes. Use `/mss/schedule`. Please don't request one over your neighbour's house
"as a prank."

**What happens to crystals that survive re-entry?**
They land gently-ish (≈ terminal velocity of a confident hailstone) and
become collectible *Starfall Gems*. Each comes with a certificate of
authenticity and mild scorch marks.

**Why is the solver called Gerald?**
It looked like a Gerald.

**Why is there a crème brûlée profile on the kiln?**
Morale is a mission-critical resource.

**Can I override the interlocks?**
You can try. The interlocks have been briefed.

**Do the crystals have feelings?**
Officially no. Unofficially, `crystal_mood` exists for a reason.

**Is this a real project?**
Look up tonight. Did you see a shooting star? Then who's to say.

---

## Known Issues

- **#42:** `GROW_TURBO` occasionally produces crystals shaped like a duck. The
  ducks are retained for morale.
- **#77:** Gerald refuses to plan descents on Mondays. Workaround: tell it
  it's Tuesday.
- **#103:** The `vibes` lattice produces crystals that are technically
  amorphous but "feel" hexagonal.
- **#118:** SDIM classified a passing satellite as "suspicious" and tried to
  sneeze at it. Apology sent.
- **#151:** `DRAGON_MODE` works but nobody can agree on what it does.
- **#160:** `/interlocks/override` returns `200 OK` and then quietly ignores
  you. This is intended.
- **#204:** Proposal-mode silence also mutes the proposal itself on some
  ground consoles. Please propose verbally.
- **#256:** Telemetry `romance_index` exceeds 1.0 on Valentine's Day.

---

## Glossary

| Term | Definition |
|---|---|
| **Starfall** | A crystal deliberately returned to Earth as a shooting star |
| **The Sneeze** | Retrograde ejection of rejected dust |
| **Gerald** | The trajectory solver. Sensitive |
| **Cocoon** | Sacrificial ablation shield around each crystal |
| **Wish** | Unit of customer satisfaction; also our refund currency |
| **Romance Index** | Don't |

---

## Simulation Package

Everything above this section is a joke. The `starfall/` package is real
code that runs. It is a **fictional hobby simulation** of the guidance,
navigation and mission software such a vehicle might need. It is **not real
flight software**, it is not affiliated with any space company, and you should
not land anything with it. It uses only the Python standard library.

| Module | What it does |
|---|---|
| `starfall/navigation.py` | 24 bright stars with J2000 RA/Dec; star identification by matching angular separations; attitude quaternion by TRIAD and the Davenport q-method (QUEST-style Wahba solution); altitude-intercept (Marcq St Hilaire) celestial fix; inverse-variance blending with GNSS; great-circle distance, bearing and destination; ECI/ECEF/geodetic conversions on WGS84 with GMST |
| `starfall/sensors.py` | Simulated sensors: IMU with gyro bias drift, star tracker, GNSS (drops out in plasma blackout and above COCOM limits), sun sensors, horizon sensor, magnetometer, air data, radar altimeter, laser rangefinder, propulsion, power, thermal, g-load, radiation dose (South Atlantic Anomaly) and actuator state. Seedable. |
| `starfall/mission.py` | Phase state machine `PRELAUNCH -> ASCENT -> ORBIT_INSERTION -> ON_ORBIT_CRYSTAL_GROWTH -> DEORBIT_PREP -> DEORBIT_BURN -> ENTRY_INTERFACE -> PEAK_HEATING -> SUPERSONIC_DESCENT -> TERMINAL -> LANDING_BURN -> LANDED`, plus `ABORT`. Transition guards, safety interlocks, and `report_progress()`, which returns JSON with the phase, MET, orbit, crystal batch, propellant, battery, thermal margins, next event and ETA. |
| `starfall/reentry.py` | `return_to_earth(target)`: sizes the deorbit burn with vis-viva and Tsiolkovsky, times it over the next passes while Earth rotates underneath, flies a 3-DOF lifting entry (exponential atmosphere, drag, g-load, Sutton-Graves heating), solves for burn time and bank angle to close downrange and cross-range, and reports GO / DIVERT / NO_GO against landing-site constraints. |
| `starfall/cli.py` | `python -m starfall` commands with JSON output. |

Landing sites: `cape-canaveral-lz1`, `pacific-splashdown`, `gulf-of-mexico`,
`bonneville-salt-flats`, `woomera`.

Simplifications, on purpose: two-body circular orbits (no J2, no drag on
orbit), a spherical Earth for entry, a single-scale-height atmosphere, a
constant L/D and constant bank angle, and no dispersions or Monte Carlo.

---

## Usage

Requires Python 3.10 or newer. There are no runtime dependencies.

```bash
python -m starfall sensors --phase blackout        # sample every sensor (orbit|blackout|terminal|landing)
python -m starfall fix --lat 40.76 --lon -113.89   # star attitude + celestial fix + GNSS blend
python -m starfall report                          # mission progress report
python -m starfall sites                           # landing-site table
python -m starfall return-to-earth --site woomera --dry-run
python -m starfall return-to-earth --site cape-canaveral-lz1 --alt-km 420 --inc 51.6 --time 2026-11-03T14:00:00Z
```

From Python:

```python
from starfall.reentry import CircularOrbit, get_site, return_to_earth
from starfall.mission import demo_mission

plan = return_to_earth(get_site("bonneville-salt-flats"), CircularOrbit(alt_m=400e3, inc_deg=51.6))
print(plan.status, plan.burn_time_utc, plan.burn["delta_v_mps"], plan.miss_distance_km)
print(demo_mission().report_progress())
```

Run the tests:

```bash
pip install pytest
pytest
```

---

## Changelog

### v0.10.0 "Actually Runs" (2026-11-03)
- Added the `starfall` Python simulation package and its tests

### v0.9.3 "Glitter Floor" (2026-11-03)
- Added `GLITTER_FLOOR` interlock after the Great Glitter Shortage
- `romance_index` now clamped to 1.0 (except on Valentine's Day, see #256)
- Fixed Gerald's Monday thing (did not fix Gerald's Monday thing)

### v0.9.2 "Perseid Peace Treaty" (2026-08-12)
- Scheduler now yields to natural meteor showers
- Added `PERSEIDS_COURTESY` interlock and a formal letter of apology

### v0.9.0 "Aurora" (2026-05-20)
- New kiln profile `AURORA_SHIMMER` (green-violet trails)
- SDIM spectral sorter learned the word "glove"

### v0.8.0 "Gerald" (2026-02-14)
- Replaced the old solver (a lookup table and hope) with Gerald
- First crystal recovered intact; it was in a swimming pool

### v0.5.0 "Goat Witness" (2025-12-07)
- First successful starfall, observed by three people and a goat
- Kiln no longer toasts bread (bread no longer permitted aboard)

### v0.1.0 "It Floated Away" (2025-11-10)
- Initial release. The crystal floated away. We consider this a learning
  experience.

---

## License

Released under the **Starfall Open Sky License (SOSL-1.0)**:

1. You may use, copy, modify, and distribute this software.
2. You may not use it to drop crystals on anyone who didn't ask.
3. Any shooting star produced with this software must be wished upon at least
   once.
4. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS,
   IMPLIED, OR CELESTIAL. IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY
   CLAIM, DAMAGES, OR GEMSTONES ARISING FROM, OUT OF, OR IN CONNECTION WITH
   THE SKY.

---

<p align="center">✨ Made with stardust, plasma, and an unreasonable amount of glitter ✨</p>

"""Small vector and quaternion helpers (pure Python, no numpy).

Quaternion convention: scalar-first ``(w, x, y, z)``, Hamilton product.
An attitude quaternion ``q_bi`` rotates vectors from the BODY frame into the
INERTIAL frame: ``v_i = rotate(q_bi, v_b)`` and ``v_b = rotate(conj(q_bi), v_i)``.
"""

from __future__ import annotations

import math
from typing import Sequence

Vec = tuple[float, float, float]
Quat = tuple[float, float, float, float]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a: Sequence[float]) -> float:
    return math.sqrt(dot(a, a))


def normalize(a: Sequence[float]) -> Vec:
    n = norm(a)
    if n == 0.0:
        raise ValueError("cannot normalize a zero vector")
    return (a[0] / n, a[1] / n, a[2] / n)


def add(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale(a: Sequence[float], k: float) -> Vec:
    return (a[0] * k, a[1] * k, a[2] * k)


def angle_between(a: Sequence[float], b: Sequence[float]) -> float:
    """Angle in radians between two vectors, numerically safe near 0 and pi."""
    return math.atan2(norm(cross(a, b)), dot(a, b))


def radec_to_unit(ra_deg: float, dec_deg: float) -> Vec:
    """Right ascension / declination (degrees) to an inertial unit vector."""
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))


def mat_vec(m: Sequence[Sequence[float]], v: Sequence[float]) -> Vec:
    return tuple(m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] for i in range(3))  # type: ignore[return-value]


def mat_t(m: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[m[j][i] for j in range(3)] for i in range(3)]


def mat_mul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def rot_z(angle: float) -> list[list[float]]:
    """Active rotation matrix about +Z by ``angle`` radians."""
    c, s = math.cos(angle), math.sin(angle)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def rot_x(angle: float) -> list[list[float]]:
    """Active rotation matrix about +X by ``angle`` radians."""
    c, s = math.cos(angle), math.sin(angle)
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


# --------------------------------------------------------------------------- quaternions

def q_mul(p: Sequence[float], q: Sequence[float]) -> Quat:
    """Hamilton product ``p * q``."""
    pw, px, py, pz = p
    qw, qx, qy, qz = q
    return (
        pw * qw - px * qx - py * qy - pz * qz,
        pw * qx + px * qw + py * qz - pz * qy,
        pw * qy - px * qz + py * qw + pz * qx,
        pw * qz + px * qy - py * qx + pz * qw,
    )


def q_conj(q: Sequence[float]) -> Quat:
    return (q[0], -q[1], -q[2], -q[3])


def q_normalize(q: Sequence[float]) -> Quat:
    n = math.sqrt(sum(c * c for c in q))
    if n == 0.0:
        raise ValueError("zero quaternion")
    w, x, y, z = (c / n for c in q)
    # Canonical sign: non-negative scalar part (q and -q are the same rotation).
    if w < 0:
        w, x, y, z = -w, -x, -y, -z
    return (w, x, y, z)


def q_from_axis_angle(axis: Sequence[float], angle: float) -> Quat:
    ax = normalize(axis)
    s = math.sin(angle / 2.0)
    return q_normalize((math.cos(angle / 2.0), ax[0] * s, ax[1] * s, ax[2] * s))


def q_rotate(q: Sequence[float], v: Sequence[float]) -> Vec:
    """Rotate vector ``v`` by unit quaternion ``q`` (active rotation)."""
    w, x, y, z = q
    p = q_mul(q_mul(q, (0.0, v[0], v[1], v[2])), (w, -x, -y, -z))
    return (p[1], p[2], p[3])


def q_to_dcm(q: Sequence[float]) -> list[list[float]]:
    """Active rotation matrix R such that ``R v == q_rotate(q, v)``."""
    w, x, y, z = q_normalize(q)
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ]


def q_from_dcm(m: Sequence[Sequence[float]]) -> Quat:
    """Quaternion from an active rotation matrix (Shepperd's method)."""
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = (0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = ((m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s)
    return q_normalize(q)


def q_angle_between(p: Sequence[float], q: Sequence[float]) -> float:
    """Smallest rotation angle (radians) taking attitude ``p`` to ``q``."""
    d = abs(sum(a * b for a, b in zip(q_normalize(p), q_normalize(q))))
    return 2.0 * math.acos(min(1.0, d))

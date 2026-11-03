import math
import random

from starfall.mathutil import (
    q_angle_between, q_conj, q_from_axis_angle, q_from_dcm, q_mul, q_normalize, q_rotate, q_to_dcm,
    mat_vec, normalize,
)


def close(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def test_rotation_about_z_by_90_degrees():
    q = q_from_axis_angle((0, 0, 1), math.pi / 2)
    assert close(q_rotate(q, (1, 0, 0)), (0, 1, 0))


def test_quaternion_product_composes_rotations():
    qa = q_from_axis_angle((0, 0, 1), math.pi / 2)
    qb = q_from_axis_angle((1, 0, 0), math.pi / 2)
    v = (0.3, -0.2, 0.9)
    assert close(q_rotate(q_mul(qb, qa), v), q_rotate(qb, q_rotate(qa, v)))


def test_conjugate_is_inverse():
    q = q_normalize((0.4, 0.1, -0.7, 0.3))
    assert close(q_mul(q, q_conj(q)), (1, 0, 0, 0))


def test_dcm_round_trip_and_agrees_with_rotate():
    rng = random.Random(3)
    for _ in range(50):
        axis = normalize((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        q = q_from_axis_angle(axis, rng.uniform(0, 2 * math.pi))
        dcm = q_to_dcm(q)
        v = (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))
        assert close(mat_vec(dcm, v), q_rotate(q, v), 1e-12)
        assert q_angle_between(q_from_dcm(dcm), q) < 1e-9


def test_angle_between_quaternions():
    q1 = q_from_axis_angle((0, 1, 0), 0.1)
    q2 = q_from_axis_angle((0, 1, 0), 0.4)
    assert abs(q_angle_between(q1, q2) - 0.3) < 1e-12

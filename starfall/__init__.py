"""Starfall Prototype: a fictional hobby simulation of the onboard software for an
orbital crystal-growth vehicle that returns its payload to Earth.

This is NOT real flight software. The physics models are simplified textbook
approximations (two-body orbits, exponential atmosphere, Sutton-Graves heating)
meant for learning and fun. Standard library only.
"""

__version__ = "0.10.0"

__all__ = ["constants", "mathutil", "sensors", "navigation", "mission", "reentry", "cli"]

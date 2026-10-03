"""Hazard-zone mapping: bounding-box centre -> red|yellow|green zone.

Zones split the frame vertically into thirds:
  top third    -> red    (overhead-crane / falling-object area)
  middle third -> yellow (active workface)
  bottom third -> green  (walkway / muster area)

A violation in red counts double in the incident log severity.
"""
from __future__ import annotations


def get_zone(bbox_center: tuple[float, float]) -> str:
    """bbox_center = (cx, cy) in normalised 0..1 coordinates."""
    _, cy = bbox_center
    if cy < 1 / 3:
        return "red"
    if cy < 2 / 3:
        return "yellow"
    return "green"


SEVERITY = {"red": 2, "yellow": 1, "green": 1}

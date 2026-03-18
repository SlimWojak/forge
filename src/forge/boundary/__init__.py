"""FORGE Boundary Measurement — core feature, not just a metric.

Boundary measurement empirically tracks where local models suffice
and where frontier judgment is required, per task type, over time.
This is FORGE's unique contribution to the field.

Every task execution automatically records boundary data. The headline
metric is frontier/local delta, not task completion rate.

See: FORGE_ARCHITECTURE_v0.2.md §7
"""

from forge.boundary.measurement import (
    BoundaryRecord,
    BoundaryTracker,
    ErrorTaxonomy,
)

__all__ = [
    "BoundaryRecord",
    "BoundaryTracker",
    "ErrorTaxonomy",
]

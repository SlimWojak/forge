"""FORGE Observability — OpenTelemetry → DuckDB pipeline.

All FORGE components emit OpenTelemetry spans that are collected
and stored in a local DuckDB database for querying by:
  - Agent self-query (SQL via ACI tool)
  - forge log / forge metrics / forge boundary
  - forge digest (daily summary generation)
  - Dashboard (Phase 2+ TUI)

See: FORGE_ARCHITECTURE_v0.2.md §10
"""

from forge.observability.tracer import ForgeTracer

__all__ = ["ForgeTracer"]

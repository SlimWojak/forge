"""FORGE Tracer — OpenTelemetry spans to DuckDB.

Records all system events as structured spans in DuckDB for
querying, metrics, boundary analysis, and daily digests.

DuckDB schema (§10.2):
  - spans: core trace spans (service, timing, attributes)
  - model_calls: LLM invocations (model, tokens, cost, latency)
  - tool_calls: ACI tool executions (tool, args, result, hooks)
  - boundary_records: per-task boundary measurement data
  - error_taxonomy: failure tags per verdict
  - benchmark_runs / benchmark_cartridge_results
  - shadow_log: human merge/reject decisions
  - skill_events: skill lifecycle events

See: FORGE_ARCHITECTURE_v0.2.md §10
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

# DuckDB schema SQL matching §10.2
SCHEMA_SQL = """
-- Core spans table
CREATE TABLE IF NOT EXISTS spans (
    span_id       VARCHAR PRIMARY KEY,
    trace_id      VARCHAR NOT NULL,
    parent_span_id VARCHAR,
    span_name     VARCHAR NOT NULL,
    service       VARCHAR NOT NULL,
    start_time    TIMESTAMP NOT NULL,
    end_time      TIMESTAMP,
    duration_ms   INTEGER,
    status        VARCHAR,
    attributes    JSON
);

-- Model interactions
CREATE TABLE IF NOT EXISTS model_calls (
    call_id       VARCHAR PRIMARY KEY,
    span_id       VARCHAR,
    model         VARCHAR NOT NULL,
    provider      VARCHAR NOT NULL,
    role          VARCHAR NOT NULL,
    tokens_in     INTEGER NOT NULL,
    tokens_out    INTEGER NOT NULL,
    latency_ms    INTEGER NOT NULL,
    cost_usd      DECIMAL(10,6),
    temperature   DECIMAL(3,2),
    lora_version  VARCHAR
);

-- Tool calls
CREATE TABLE IF NOT EXISTS tool_calls (
    call_id       VARCHAR PRIMARY KEY,
    span_id       VARCHAR,
    tool_name     VARCHAR NOT NULL,
    arguments     JSON,
    result_status VARCHAR NOT NULL,
    result_summary VARCHAR,
    duration_ms   INTEGER,
    hook_triggered VARCHAR
);

-- Boundary measurement records
CREATE TABLE IF NOT EXISTS boundary_records (
    task_id             VARCHAR PRIMARY KEY,
    mission_id          VARCHAR NOT NULL,
    mission_mode        VARCHAR NOT NULL,
    difficulty_class    VARCHAR NOT NULL,
    worker_model        VARCHAR NOT NULL,
    lora_version        VARCHAR,
    first_pass_success  BOOLEAN NOT NULL,
    total_iterations    INTEGER NOT NULL,
    error_taxonomy_tags JSON,
    local_tokens        INTEGER NOT NULL,
    frontier_tokens_in  INTEGER NOT NULL,
    frontier_tokens_out INTEGER NOT NULL,
    frontier_cost_usd   DECIMAL(10,6),
    wall_clock_seconds  INTEGER NOT NULL,
    timestamp           TIMESTAMP NOT NULL
);

-- Error taxonomy log
CREATE TABLE IF NOT EXISTS error_taxonomy (
    verdict_id    VARCHAR NOT NULL,
    task_id       VARCHAR NOT NULL,
    tag           VARCHAR NOT NULL,
    detail        VARCHAR,
    reviewer_model VARCHAR NOT NULL,
    timestamp     TIMESTAMP NOT NULL
);

-- Benchmark results
CREATE TABLE IF NOT EXISTS benchmark_runs (
    run_id          VARCHAR PRIMARY KEY,
    tag             VARCHAR NOT NULL,
    timestamp       TIMESTAMP NOT NULL,
    config_snapshot JSON NOT NULL,
    summary         JSON NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_cartridge_results (
    run_id        VARCHAR,
    cartridge_id  VARCHAR NOT NULL,
    status        VARCHAR NOT NULL,
    first_pass    BOOLEAN NOT NULL,
    iterations    INTEGER NOT NULL,
    local_tokens  INTEGER NOT NULL,
    frontier_tokens INTEGER NOT NULL,
    wall_clock_seconds INTEGER NOT NULL,
    error_tags    JSON,
    trace_id      VARCHAR,
    PRIMARY KEY (run_id, cartridge_id)
);

-- Shadow mode log
CREATE TABLE IF NOT EXISTS shadow_log (
    task_id         VARCHAR NOT NULL,
    oracle_id       VARCHAR NOT NULL,
    gate_verdict    VARCHAR NOT NULL,
    human_decision  VARCHAR NOT NULL,
    human_feedback  VARCHAR,
    decision_time_s INTEGER,
    timestamp       TIMESTAMP NOT NULL
);

-- Skill events
CREATE TABLE IF NOT EXISTS skill_events (
    skill_id      VARCHAR NOT NULL,
    event_type    VARCHAR NOT NULL,
    from_tier     INTEGER,
    to_tier       INTEGER,
    task_id       VARCHAR,
    timestamp     TIMESTAMP NOT NULL
);
"""


class ForgeTracer:
    """Records and queries FORGE observability data in DuckDB.

    All components call the tracer to record events. The tracer
    writes to DuckDB at .forge/traces/forge.duckdb and supports
    SQL queries for agent self-observability.

    Usage::

        tracer = ForgeTracer(db_path=Path(".forge/traces/forge.duckdb"))
        tracer.initialize_schema()

        # Record a span
        tracer.record_span(
            span_id="span-001",
            trace_id="trace-001",
            span_name="task_execution",
            service="worker",
        )

        # Record a model call
        tracer.record_model_call(
            model="qwen3.5-35b",
            provider="local",
            role="worker",
            tokens_in=2000,
            tokens_out=500,
            latency_ms=1200,
        )

    See: FORGE_ARCHITECTURE_v0.2.md §10
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or Path(".forge/traces/forge.duckdb")
        self._connection: duckdb.DuckDBPyConnection | None = None

    def _conn(self) -> duckdb.DuckDBPyConnection:
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = duckdb.connect(str(self._db_path))
        return self._connection

    def initialize_schema(self) -> None:
        """Create DuckDB tables matching §10.2. Safe to call repeatedly."""
        conn = self._conn()
        # Strip comments, then split on semicolons
        lines = [
            line for line in SCHEMA_SQL.splitlines()
            if not line.strip().startswith("--")
        ]
        clean_sql = "\n".join(lines)
        for statement in clean_sql.split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(stmt)

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _uid(self) -> str:
        return uuid.uuid4().hex[:12]

    def record_span(
        self,
        span_id: str,
        trace_id: str,
        span_name: str,
        service: str,
        parent_span_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        duration_ms: int | None = None,
        status: str = "ok",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        self._conn().execute(
            "INSERT INTO spans VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                span_id, trace_id, parent_span_id, span_name, service,
                start_time or self._now(), end_time, duration_ms, status,
                json.dumps(attributes or {}),
            ],
        )

    def record_model_call(
        self,
        model: str,
        provider: str,
        role: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: int,
        span_id: str | None = None,
        cost_usd: float | None = None,
        temperature: float | None = None,
        lora_version: str | None = None,
    ) -> None:
        self._conn().execute(
            "INSERT INTO model_calls VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                self._uid(), span_id, model, provider, role,
                tokens_in, tokens_out, latency_ms,
                cost_usd, temperature, lora_version,
            ],
        )

    def record_tool_call(
        self,
        tool_name: str,
        result_status: str,
        span_id: str | None = None,
        arguments: dict[str, Any] | None = None,
        result_summary: str | None = None,
        duration_ms: int | None = None,
        hook_triggered: str | None = None,
    ) -> None:
        self._conn().execute(
            "INSERT INTO tool_calls VALUES (?,?,?,?,?,?,?,?)",
            [
                self._uid(), span_id, tool_name,
                json.dumps(arguments or {}), result_status,
                result_summary, duration_ms, hook_triggered,
            ],
        )

    def record_boundary(
        self,
        task_id: str,
        mission_id: str,
        mission_mode: str,
        difficulty_class: str,
        worker_model: str,
        first_pass_success: bool,
        total_iterations: int,
        local_tokens: int,
        frontier_tokens_in: int,
        frontier_tokens_out: int,
        wall_clock_seconds: int,
        lora_version: str | None = None,
        error_taxonomy_tags: list[str] | None = None,
        frontier_cost_usd: float | None = None,
    ) -> None:
        now = self._now()
        self._conn().execute(
            "INSERT OR REPLACE INTO boundary_records VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                task_id, mission_id, mission_mode, difficulty_class,
                worker_model, lora_version, first_pass_success,
                total_iterations, json.dumps(error_taxonomy_tags or []),
                local_tokens, frontier_tokens_in, frontier_tokens_out,
                frontier_cost_usd, wall_clock_seconds, now,
            ],
        )

    def record_error_taxonomy(
        self,
        verdict_id: str,
        task_id: str,
        tag: str,
        reviewer_model: str,
        detail: str | None = None,
    ) -> None:
        self._conn().execute(
            "INSERT INTO error_taxonomy VALUES (?,?,?,?,?,?)",
            [verdict_id, task_id, tag, detail, reviewer_model, self._now()],
        )

    def record_shadow_event(
        self,
        task_id: str,
        oracle_id: str,
        gate_verdict: str,
        human_decision: str,
        human_feedback: str | None = None,
        decision_time_s: int | None = None,
    ) -> None:
        self._conn().execute(
            "INSERT INTO shadow_log VALUES (?,?,?,?,?,?,?)",
            [
                task_id, oracle_id, gate_verdict, human_decision,
                human_feedback, decision_time_s, self._now(),
            ],
        )

    def record_skill_event(
        self,
        skill_id: str,
        event_type: str,
        from_tier: int | None = None,
        to_tier: int | None = None,
        task_id: str | None = None,
    ) -> None:
        self._conn().execute(
            "INSERT INTO skill_events VALUES (?,?,?,?,?,?)",
            [skill_id, event_type, from_tier, to_tier, task_id, self._now()],
        )

    def query(self, sql: str, max_rows: int = 100) -> dict[str, Any]:
        """Execute a SELECT query. Returns {columns, rows, truncated}."""
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")
        result = self._conn().execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchmany(max_rows + 1)
        truncated = len(rows) > max_rows
        return {
            "columns": columns,
            "rows": [list(r) for r in rows[:max_rows]],
            "truncated": truncated,
        }

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

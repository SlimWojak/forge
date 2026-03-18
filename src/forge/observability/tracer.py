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

from pathlib import Path
from typing import Any


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
        """Initialize the tracer.

        Args:
            db_path: Path to DuckDB database file.
                    Default: .forge/traces/forge.duckdb
        """
        self._db_path = db_path or Path(".forge/traces/forge.duckdb")
        self._connection: Any = None  # duckdb.DuckDBPyConnection

    def initialize_schema(self) -> None:
        """Create DuckDB tables if they don't exist.

        Executes the schema SQL from §10.2. Safe to call multiple
        times — uses CREATE TABLE IF NOT EXISTS.

        TODO: Implement DuckDB connection and schema creation (§10.2).
        TODO: Ensure .forge/traces/ directory exists.
        """
        raise NotImplementedError("initialize_schema not yet implemented — see §10.2")

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
        """Record a trace span.

        Args:
            span_id: Unique span identifier.
            trace_id: Parent trace identifier.
            span_name: Name of the operation.
            service: Service that emitted the span (worker, orchestrator, etc.).
            parent_span_id: Parent span for nested operations.
            start_time: ISO timestamp of span start.
            end_time: ISO timestamp of span end.
            duration_ms: Duration in milliseconds.
            status: "ok" or "error".
            attributes: Flexible key-value pairs.

        TODO: Implement DuckDB INSERT into spans table (§10.2).
        """
        raise NotImplementedError("record_span not yet implemented — see §10.2")

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
        """Record an LLM model call.

        TODO: Implement DuckDB INSERT into model_calls table (§10.2).
        """
        raise NotImplementedError("record_model_call not yet implemented — see §10.2")

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
        """Record an ACI tool call.

        TODO: Implement DuckDB INSERT into tool_calls table (§10.2).
        """
        raise NotImplementedError("record_tool_call not yet implemented — see §10.2")

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
        """Record a boundary measurement data point.

        Also appends to .forge/boundary-data.jsonl (append-only).

        TODO: Implement DuckDB INSERT into boundary_records (§7.2, §10.2).
        TODO: Append JSONL record to boundary-data.jsonl.
        """
        raise NotImplementedError("record_boundary not yet implemented — see §7.2")

    def record_error_taxonomy(
        self,
        verdict_id: str,
        task_id: str,
        tag: str,
        reviewer_model: str,
        detail: str | None = None,
    ) -> None:
        """Record an error taxonomy tag from a verdict.

        TODO: Implement DuckDB INSERT into error_taxonomy (§7.4, §10.2).
        """
        raise NotImplementedError(
            "record_error_taxonomy not yet implemented — see §7.4"
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
        """Record a shadow mode decision.

        Also appends to .forge/shadow-log.jsonl (append-only).

        TODO: Implement DuckDB INSERT into shadow_log (§5.5, §10.2).
        TODO: Append JSONL record to shadow-log.jsonl.
        """
        raise NotImplementedError(
            "record_shadow_event not yet implemented — see §5.5"
        )

    def record_skill_event(
        self,
        skill_id: str,
        event_type: str,
        from_tier: int | None = None,
        to_tier: int | None = None,
        task_id: str | None = None,
    ) -> None:
        """Record a skill lifecycle event.

        TODO: Implement DuckDB INSERT into skill_events (§9, §10.2).
        """
        raise NotImplementedError(
            "record_skill_event not yet implemented — see §9"
        )

    def query(self, sql: str, max_rows: int = 100) -> dict[str, Any]:
        """Execute a SQL query against the trace database.

        Used by the query_traces ACI tool for agent self-observability.
        Only SELECT queries are allowed.

        Args:
            sql: SQL SELECT query.
            max_rows: Maximum rows to return.

        Returns:
            Dict with "columns" and "rows" keys.

        TODO: Implement DuckDB query execution (§10.3).
        """
        if not sql.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")
        raise NotImplementedError("query not yet implemented — see §10.3")

    def close(self) -> None:
        """Close the DuckDB connection.

        TODO: Implement connection cleanup.
        """
        if self._connection is not None:
            pass  # TODO: self._connection.close()

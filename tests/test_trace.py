"""Tests for FORGE Trace System (F011) and Error Taxonomy (F012)."""

from __future__ import annotations

from pathlib import Path

import pytest

from forge.observability.tracer import ForgeTracer


@pytest.fixture()
def tracer(tmp_path: Path) -> ForgeTracer:
    db = tmp_path / "forge.duckdb"
    t = ForgeTracer(db_path=db)
    t.initialize_schema()
    return t


# ---------------------------------------------------------------------------
# F011: Trace System
# ---------------------------------------------------------------------------


class TestTraceRecord:
    """test_trace_record — recording spans, model calls, tool calls."""

    def test_record_span(self, tracer: ForgeTracer) -> None:
        tracer.record_span(
            span_id="s1", trace_id="t1",
            span_name="task_exec", service="worker",
        )
        result = tracer.query("SELECT * FROM spans WHERE span_id = 's1'")
        assert len(result["rows"]) == 1
        assert result["rows"][0][3] == "task_exec"

    def test_record_model_call(self, tracer: ForgeTracer) -> None:
        tracer.record_model_call(
            model="qwen3.5-35b", provider="local", role="worker",
            tokens_in=2000, tokens_out=500, latency_ms=1200,
        )
        result = tracer.query("SELECT * FROM model_calls")
        assert len(result["rows"]) == 1
        assert result["rows"][0][2] == "qwen3.5-35b"

    def test_record_tool_call(self, tracer: ForgeTracer) -> None:
        tracer.record_tool_call(
            tool_name="view_file", result_status="success",
            duration_ms=15,
        )
        result = tracer.query("SELECT * FROM tool_calls")
        assert len(result["rows"]) == 1
        assert result["rows"][0][2] == "view_file"

    def test_record_boundary(self, tracer: ForgeTracer) -> None:
        tracer.record_boundary(
            task_id="task-001", mission_id="m1",
            mission_mode="delivery", difficulty_class="local-reasoning",
            worker_model="qwen3.5-35b",
            first_pass_success=True, total_iterations=1,
            local_tokens=5000, frontier_tokens_in=3000,
            frontier_tokens_out=800, wall_clock_seconds=30,
        )
        result = tracer.query("SELECT * FROM boundary_records")
        assert len(result["rows"]) == 1

    def test_record_shadow_event(self, tracer: ForgeTracer) -> None:
        tracer.record_shadow_event(
            task_id="task-001", oracle_id="o-001",
            gate_verdict="PASS", human_decision="approved",
        )
        result = tracer.query("SELECT * FROM shadow_log")
        assert len(result["rows"]) == 1

    def test_record_skill_event(self, tracer: ForgeTracer) -> None:
        tracer.record_skill_event(
            skill_id="skill-001", event_type="created",
        )
        result = tracer.query("SELECT * FROM skill_events")
        assert len(result["rows"]) == 1


class TestTraceQuery:
    """test_trace_query — SQL querying against DuckDB."""

    def test_query_returns_columns_and_rows(self, tracer: ForgeTracer) -> None:
        tracer.record_span(
            span_id="s1", trace_id="t1",
            span_name="test", service="worker",
        )
        result = tracer.query("SELECT span_name, service FROM spans")
        assert "columns" in result
        assert "rows" in result
        assert result["columns"] == ["span_name", "service"]

    def test_query_rejects_non_select(self, tracer: ForgeTracer) -> None:
        with pytest.raises(ValueError, match="Only SELECT"):
            tracer.query("DELETE FROM spans")

    def test_query_truncation(self, tracer: ForgeTracer) -> None:
        for i in range(10):
            tracer.record_span(
                span_id=f"s{i}", trace_id="t1",
                span_name="test", service="worker",
            )
        result = tracer.query("SELECT * FROM spans", max_rows=5)
        assert len(result["rows"]) == 5
        assert result["truncated"] is True

    def test_aggregation_query(self, tracer: ForgeTracer) -> None:
        tracer.record_model_call(
            model="qwen", provider="local", role="worker",
            tokens_in=1000, tokens_out=200, latency_ms=500,
        )
        tracer.record_model_call(
            model="qwen", provider="local", role="worker",
            tokens_in=2000, tokens_out=300, latency_ms=800,
        )
        result = tracer.query(
            "SELECT SUM(tokens_in) as total_in FROM model_calls"
        )
        assert result["rows"][0][0] == 3000


# ---------------------------------------------------------------------------
# F012: Error Taxonomy Tagging
# ---------------------------------------------------------------------------


class TestErrorTaxonomy:
    """test_error_taxonomy_tagging — tags stored in trace DB."""

    def test_record_error_taxonomy(self, tracer: ForgeTracer) -> None:
        tracer.record_error_taxonomy(
            verdict_id="v-001", task_id="task-001",
            tag="missing-tests", reviewer_model="sonnet-4.6",
            detail="No error case test",
        )
        result = tracer.query("SELECT * FROM error_taxonomy")
        assert len(result["rows"]) == 1
        assert result["rows"][0][2] == "missing-tests"

    def test_multiple_tags_per_verdict(self, tracer: ForgeTracer) -> None:
        for tag in ["missing-tests", "incorrect-logic"]:
            tracer.record_error_taxonomy(
                verdict_id="v-001", task_id="task-001",
                tag=tag, reviewer_model="sonnet-4.6",
            )
        result = tracer.query(
            "SELECT tag FROM error_taxonomy WHERE verdict_id = 'v-001'"
        )
        assert len(result["rows"]) == 2

    def test_taxonomy_distribution_query(self, tracer: ForgeTracer) -> None:
        tags = ["missing-tests", "missing-tests", "incorrect-logic", "tool-misuse"]
        for i, tag in enumerate(tags):
            tracer.record_error_taxonomy(
                verdict_id=f"v-{i}", task_id=f"t-{i}",
                tag=tag, reviewer_model="sonnet-4.6",
            )
        result = tracer.query(
            "SELECT tag, COUNT(*) as cnt FROM error_taxonomy "
            "GROUP BY tag ORDER BY cnt DESC"
        )
        assert result["rows"][0][0] == "missing-tests"
        assert result["rows"][0][1] == 2

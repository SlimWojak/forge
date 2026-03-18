"""FORGE Benchmark Runner — execute cartridge suites for comparison.

Runs a fixed set of benchmark tasks against the current harness
configuration to produce comparable results.

See: FORGE_ARCHITECTURE_v0.2.md §8
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CartridgeResult:
    """Result of running a single benchmark cartridge."""

    cartridge_id: str
    name: str
    status: str  # "pass" | "fail" | "error" | "timeout"
    first_pass: bool = False
    iterations: int = 0
    local_tokens: int = 0
    frontier_tokens: int = 0
    wall_clock_seconds: int = 0
    error_tags: list[str] = field(default_factory=list)


@dataclass
class BenchmarkRun:
    """Result of a full benchmark suite run."""

    run_id: str
    tag: str
    timestamp: str
    cartridge_results: list[CartridgeResult] = field(default_factory=list)
    config_snapshot: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.cartridge_results if r.status == "pass")

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.cartridge_results if r.status != "pass")

    @property
    def total(self) -> int:
        return len(self.cartridge_results)

    def summary(self) -> str:
        lines = [
            f"Benchmark Run: {self.tag} ({self.run_id})",
            f"  Timestamp: {self.timestamp}",
            f"  Results: {self.pass_count}/{self.total} passed",
            "",
        ]
        for r in self.cartridge_results:
            status_icon = "PASS" if r.status == "pass" else "FAIL"
            lines.append(
                f"  [{status_icon}] {r.cartridge_id}: {r.name} "
                f"(iters={r.iterations})"
            )
        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "tag": self.tag,
            "timestamp": self.timestamp,
            "config_snapshot": self.config_snapshot,
            "summary": {
                "total": self.total,
                "passed": self.pass_count,
                "failed": self.fail_count,
            },
            "results": [asdict(r) for r in self.cartridge_results],
        }


def load_cartridges(cartridge_dir: Path) -> list[dict[str, Any]]:
    """Load benchmark cartridges from YAML files in the directory."""
    cartridges: list[dict[str, Any]] = []
    if not cartridge_dir.exists():
        return cartridges

    for f in sorted(cartridge_dir.iterdir()):
        if f.suffix in (".yaml", ".yml") and f.name != "cartridge-template.yaml":
            try:
                data = yaml.safe_load(f.read_text())
                if data and isinstance(data, dict) and "id" in data:
                    cartridges.append(data)
            except Exception:
                continue

    return cartridges


class BenchmarkRunner:
    """Executes benchmark cartridges and stores results.

    See: FORGE_ARCHITECTURE_v0.2.md §8
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._cartridge_dir = project_root / ".forge" / "benchmarks"
        self._results_dir = project_root / ".forge" / "benchmark-results"
        self._results_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        tag: str = "default",
        cartridge_filter: str | None = None,
    ) -> BenchmarkRun:
        """Run the benchmark suite.

        In Phase 1, cartridges produce placeholder results since
        the full task loop requires real model endpoints.
        """
        cartridges = load_cartridges(self._cartridge_dir)
        if cartridge_filter:
            cartridges = [c for c in cartridges if c["id"] == cartridge_filter]

        run_id = f"run-{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        results: list[CartridgeResult] = []

        for cart in cartridges:
            results.append(CartridgeResult(
                cartridge_id=cart["id"],
                name=cart.get("name", cart["id"]),
                status="pass",
                first_pass=True,
                iterations=1,
            ))

        run = BenchmarkRun(
            run_id=run_id,
            tag=tag,
            timestamp=now,
            cartridge_results=results,
        )

        # Persist results
        result_path = self._results_dir / f"{run_id}.json"
        result_path.write_text(json.dumps(run.to_json(), indent=2))

        return run

    def compare(self, tag1: str, tag2: str) -> str:
        """Compare two benchmark runs by tag."""
        runs1 = self._load_by_tag(tag1)
        runs2 = self._load_by_tag(tag2)

        if not runs1:
            return f"No benchmark runs found with tag: {tag1}"
        if not runs2:
            return f"No benchmark runs found with tag: {tag2}"

        r1 = runs1[-1]
        r2 = runs2[-1]

        lines = [
            f"Benchmark Comparison: {tag1} vs {tag2}",
            f"  {tag1}: {r1.get('summary', {}).get('passed', 0)}"
            f"/{r1.get('summary', {}).get('total', 0)} passed",
            f"  {tag2}: {r2.get('summary', {}).get('passed', 0)}"
            f"/{r2.get('summary', {}).get('total', 0)} passed",
        ]
        return "\n".join(lines)

    def list_cartridges(self) -> list[dict[str, Any]]:
        return load_cartridges(self._cartridge_dir)

    def _load_by_tag(self, tag: str) -> list[dict[str, Any]]:
        runs = []
        for f in self._results_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data.get("tag") == tag:
                    runs.append(data)
            except Exception:
                continue
        return runs

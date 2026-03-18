# FORGE Integration Wiring — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire ModelProvider to the live Qwen endpoint on localhost:8000/v1, implement config loading, bridge the protocol gap between ModelProvider and worker/gate protocols, and connect CLI commands to library code — enabling the full bootstrap test against a real model.

**Architecture:** Three layers of plumbing: (1) config loader reads `.forge/config.yaml` and produces `ModelConfig` instances, (2) `ModelProvider` uses httpx to call the OpenAI-compatible vLLM endpoint, (3) a thin `LocalModelAdapter` satisfies the `ModelInterface`/`ReviewerModel` protocols that `run_worker()` and `GateEngine` already expect. CLI commands instantiate these and call the existing tested library code.

**Tech Stack:** httpx (already in deps), pyyaml (already in deps), existing forge library code

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/forge/config/loader.py` | CREATE | Load `.forge/config.yaml`, parse model configs, return typed dicts |
| `src/forge/models/provider.py` | MODIFY | Implement `_call_local()`, `complete()`, `get_model_config()` |
| `src/forge/models/adapter.py` | CREATE | `LocalModelAdapter` bridging `ModelProvider` → `ModelInterface`/`ReviewerModel` |
| `src/forge/cli.py` | MODIFY | Wire `forge task`, `forge oracle`, `forge review` to library code |
| `tests/test_config_loader.py` | CREATE | Config loading tests |
| `tests/test_provider_live.py` | CREATE | Live endpoint smoke test (skipped without endpoint) |
| `tests/test_adapter.py` | CREATE | Adapter protocol compliance tests |

---

### Task 1: Config Loader

**Files:**
- Create: `src/forge/config/loader.py`
- Create: `tests/test_config_loader.py`

- [ ] **Step 1: Write failing test for config loading**

```python
# tests/test_config_loader.py
"""Tests for FORGE config loader."""
import pytest
import yaml
from pathlib import Path


@pytest.fixture
def config_dir(tmp_path):
    """Create a .forge dir with a minimal config.yaml."""
    forge_dir = tmp_path / ".forge"
    forge_dir.mkdir()
    config = {
        "forge_version": "0.2",
        "models": {
            "local": {
                "worker": {
                    "endpoint": "http://localhost:8000/v1",
                    "model": "Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
                    "max_tokens": 4096,
                    "temperature": 0.2,
                },
                "planner": {
                    "endpoint": "http://localhost:8000/v1",
                    "model": "Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
                    "max_tokens": 8192,
                    "temperature": 0.3,
                },
            },
            "frontier": {
                "reviewer": {
                    "provider": "anthropic",
                    "model": "claude-sonnet-4-20260318",
                    "api_key_env": "ANTHROPIC_API_KEY",
                },
            },
        },
        "gate": {
            "shadow_mode": True,
            "max_iterations": 3,
        },
    }
    (forge_dir / "config.yaml").write_text(yaml.dump(config))
    return tmp_path


class TestConfigLoader:
    def test_load_config_returns_dict(self, config_dir):
        from forge.config.loader import load_config
        cfg = load_config(config_dir)
        assert cfg["forge_version"] == "0.2"

    def test_get_model_config_worker(self, config_dir):
        from forge.config.loader import load_config, get_model_config
        cfg = load_config(config_dir)
        mc = get_model_config(cfg, "worker")
        assert mc["endpoint"] == "http://localhost:8000/v1"
        assert mc["model"] == "Qwen/Qwen3.5-35B-A3B-GPTQ-Int4"

    def test_get_model_config_reviewer(self, config_dir):
        from forge.config.loader import load_config, get_model_config
        cfg = load_config(config_dir)
        mc = get_model_config(cfg, "reviewer")
        assert mc["provider"] == "anthropic"
        assert mc["model"] == "claude-sonnet-4-20260318"

    def test_get_model_config_missing_role_raises(self, config_dir):
        from forge.config.loader import load_config, get_model_config
        cfg = load_config(config_dir)
        with pytest.raises(KeyError):
            get_model_config(cfg, "nonexistent")

    def test_load_config_missing_file_raises(self, tmp_path):
        from forge.config.loader import load_config
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'forge.config.loader'`

- [ ] **Step 3: Implement config loader**

```python
# src/forge/config/loader.py
"""FORGE Config Loader — reads .forge/config.yaml.

Simple YAML loader that returns typed dicts for model configs.
No classes, no validation beyond existence — YAGNI for Phase 1.5.

See: FORGE_ARCHITECTURE_v0.2.md §13.1
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(project_root: Path | str) -> dict[str, Any]:
    """Load .forge/config.yaml from the project root.

    Args:
        project_root: Path to the project directory containing .forge/

    Returns:
        Parsed config dict.

    Raises:
        FileNotFoundError: If config.yaml does not exist.
    """
    root = Path(project_root)
    config_path = root / ".forge" / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_model_config(config: dict[str, Any], role: str) -> dict[str, Any]:
    """Get model configuration for a given role name.

    Looks up the role in models.local first, then models.frontier.

    Args:
        config: Full config dict from load_config().
        role: Role name (worker, planner, reviewer, escalation_reviewer, etc.)

    Returns:
        Dict with model config (endpoint, model, temperature, etc.)

    Raises:
        KeyError: If role not found in any model section.
    """
    models = config.get("models", {})

    # Check local models
    local = models.get("local", {})
    if role in local:
        return local[role]

    # Check frontier models
    frontier = models.get("frontier", {})
    if role in frontier:
        return frontier[role]

    raise KeyError(f"No model configured for role: {role}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config_loader.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/forge/config/loader.py tests/test_config_loader.py
git commit -m "[FORGE] config: Implement config loader for .forge/config.yaml"
```

---

### Task 2: ModelProvider._call_local() Implementation

**Files:**
- Modify: `src/forge/models/provider.py`
- Create: `tests/test_provider_live.py`

- [ ] **Step 1: Write test for _call_local with mock httpx**

```python
# tests/test_provider_live.py
"""Tests for ModelProvider local endpoint integration."""
import pytest
from unittest.mock import patch, MagicMock
from forge.models.provider import ModelProvider, ModelConfig, CompletionRequest, CompletionResponse


class TestCallLocal:
    def test_call_local_returns_completion_response(self):
        """_call_local should POST to endpoint and return CompletionResponse."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"role": "assistant", "content": "Hi there!"},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 5,
                "completion_tokens": 3,
                "total_tokens": 8,
            },
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = provider._call_local(config, request)

        assert isinstance(result, CompletionResponse)
        assert result.content == "Hi there!"
        assert result.tokens_in == 5
        assert result.tokens_out == 3
        mock_post.assert_called_once()

    def test_call_local_with_tools(self):
        """_call_local should pass tools in request body."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Use tool"}],
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": "call_1", "function": {"name": "test_tool", "arguments": "{}"}}],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = provider._call_local(config, request, tools=tools)

        call_body = mock_post.call_args[1]["json"]
        assert "tools" in call_body
        assert result.content is None or result.content == ""

    def test_call_local_handles_thinking_tokens(self):
        """_call_local should extract content even when model uses thinking tokens."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Qwen3.5 with thinking: content is null, reasoning has the thinking
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "The answer is 42.",
                    "reasoning": "Let me think about this...",
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 5, "completion_tokens": 20, "total_tokens": 25},
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = provider._call_local(config, request)

        assert result.content == "The answer is 42."

    def test_call_local_api_error_raises(self):
        """_call_local should raise on HTTP errors."""
        provider = ModelProvider()
        config = ModelConfig(
            model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
            endpoint="http://localhost:8000/v1",
        )
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(Exception, match="Server Error"):
                provider._call_local(config, request)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_provider_live.py -v`
Expected: FAIL — `NotImplementedError`

- [ ] **Step 3: Implement ModelProvider methods**

Replace the stub methods in `src/forge/models/provider.py`. Key changes:

1. `__init__` — accept config dict, parse into `ModelConfig` instances per role
2. `get_model_config(role)` — return config for role
3. `complete(role, messages, ...)` — route to `_call_local` for local roles
4. `_call_local(config, request, tools)` — httpx POST to vLLM endpoint
5. `raw_chat_completion(messages, tools)` — return raw OpenAI dict (for adapter)

```python
# Replace the method implementations in provider.py (keep existing dataclasses/enums)

import time
import httpx

class ModelProvider:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._models: dict[str, ModelConfig] = {}
        self._parse_config()

    def _parse_config(self) -> None:
        """Parse model configs from the config dict."""
        models = self._config.get("models", {})
        for section in ("local", "frontier"):
            for role, cfg in models.get(section, {}).items():
                self._models[role] = ModelConfig(
                    model=cfg.get("model", ""),
                    endpoint=cfg.get("endpoint", ""),
                    provider=cfg.get("provider", section if section == "local" else cfg.get("provider", "")),
                    api_key_env=cfg.get("api_key_env", ""),
                    role=cfg.get("role", role),
                    max_tokens=cfg.get("max_tokens", 4096),
                    temperature=cfg.get("temperature", 0.2),
                )

    def get_model_config(self, role: ModelRole | str) -> ModelConfig:
        role_str = role.value if isinstance(role, ModelRole) else role
        if role_str not in self._models:
            raise KeyError(f"No model configured for role: {role_str}")
        return self._models[role_str]

    def complete(
        self,
        role: ModelRole | str,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        response_format: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> CompletionResponse:
        config = self.get_model_config(role)
        request = CompletionRequest(
            messages=messages,
            max_tokens=max_tokens or config.max_tokens,
            temperature=temperature or config.temperature,
            system_prompt=system_prompt,
            response_format=response_format,
        )
        if config.provider == "local":
            return self._call_local(config, request, tools=tools)
        raise NotImplementedError(f"Provider {config.provider} not yet implemented")

    def raw_chat_completion(
        self,
        role: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return raw OpenAI-format response dict. Used by adapter."""
        config = self.get_model_config(role)
        body: dict[str, Any] = {
            "model": config.model,
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        # Suppress thinking tokens for worker role
        body["chat_template_kwargs"] = {"enable_thinking": False}

        url = f"{config.endpoint}/chat/completions"
        start = time.monotonic()
        resp = httpx.post(url, json=body, timeout=300.0)
        resp.raise_for_status()
        return resp.json()

    def _call_local(
        self,
        config: ModelConfig,
        request: CompletionRequest,
        tools: list[dict[str, Any]] | None = None,
    ) -> CompletionResponse:
        body: dict[str, Any] = {
            "model": config.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        body["chat_template_kwargs"] = {"enable_thinking": False}

        url = f"{config.endpoint}/chat/completions"
        start = time.monotonic()
        resp = httpx.post(url, json=body, timeout=300.0)
        resp.raise_for_status()
        elapsed = int((time.monotonic() - start) * 1000)

        data = resp.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage", {})

        content = message.get("content") or ""
        return CompletionResponse(
            content=content,
            model=config.model,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            latency_ms=elapsed,
            finish_reason=choice.get("finish_reason", "stop"),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_provider_live.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run full test suite to check no regressions**

Run: `pytest --tb=short`
Expected: 227+ tests PASS (existing + new)

- [ ] **Step 6: Commit**

```bash
git add src/forge/models/provider.py tests/test_provider_live.py
git commit -m "[FORGE] models: Implement _call_local() for vLLM/OpenAI-compatible endpoints"
```

---

### Task 3: Protocol Adapter

**Files:**
- Create: `src/forge/models/adapter.py`
- Create: `tests/test_adapter.py`

- [ ] **Step 1: Write failing test for adapter**

```python
# tests/test_adapter.py
"""Tests for LocalModelAdapter protocol bridge."""
import pytest
from unittest.mock import MagicMock
from forge.models.adapter import LocalModelAdapter


class TestLocalModelAdapter:
    def test_satisfies_chat_completion_interface(self):
        """Adapter.chat_completion should return OpenAI-format dict."""
        mock_provider = MagicMock()
        mock_provider.raw_chat_completion.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Done"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }

        adapter = LocalModelAdapter(provider=mock_provider, role="worker")
        result = adapter.chat_completion(
            messages=[{"role": "user", "content": "test"}],
            tools=None,
        )

        assert "choices" in result
        assert result["choices"][0]["message"]["content"] == "Done"
        mock_provider.raw_chat_completion.assert_called_once_with(
            role="worker",
            messages=[{"role": "user", "content": "test"}],
            tools=None,
        )

    def test_passes_tools_through(self):
        """Adapter should forward tools to provider."""
        mock_provider = MagicMock()
        mock_provider.raw_chat_completion.return_value = {
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": []}}],
            "usage": {},
        }

        tools = [{"type": "function", "function": {"name": "test"}}]
        adapter = LocalModelAdapter(provider=mock_provider, role="worker")
        adapter.chat_completion(messages=[], tools=tools)

        mock_provider.raw_chat_completion.assert_called_once_with(
            role="worker", messages=[], tools=tools,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement adapter**

```python
# src/forge/models/adapter.py
"""Protocol adapter bridging ModelProvider to ModelInterface/ReviewerModel.

The worker (aci/worker.py) and gate (gate/engine.py) expect objects
with a chat_completion(messages, tools) -> dict method returning
raw OpenAI-format dicts. ModelProvider.complete() returns a
CompletionResponse dataclass. This adapter bridges the gap.

Usage:
    provider = ModelProvider(config=cfg)
    worker_model = LocalModelAdapter(provider, role="worker")
    reviewer_model = LocalModelAdapter(provider, role="reviewer")

    # Now pass to existing code:
    run_worker(task, model=worker_model)
    GateEngine(reviewer=reviewer_model)
"""
from __future__ import annotations

from typing import Any

from forge.models.provider import ModelProvider


class LocalModelAdapter:
    """Thin adapter: ModelProvider -> ModelInterface/ReviewerModel protocol."""

    def __init__(self, provider: ModelProvider, role: str) -> None:
        self._provider = provider
        self._role = role

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return raw OpenAI-format response dict."""
        return self._provider.raw_chat_completion(
            role=self._role,
            messages=messages,
            tools=tools,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_adapter.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/forge/models/adapter.py tests/test_adapter.py
git commit -m "[FORGE] models: Add LocalModelAdapter bridging provider to worker/gate protocols"
```

---

### Task 4: Wire CLI Commands

**Files:**
- Modify: `src/forge/cli.py`

- [ ] **Step 1: Wire `forge task` to real orchestrator**

Replace the task command stub in cli.py. The wiring:
1. Load config via `load_config()`
2. Create `ModelProvider` from config
3. Create `LocalModelAdapter` for worker and reviewer roles
4. Create a `WorkerRunnerImpl` that wraps `run_worker()` to match the `WorkerRunner` protocol
5. Create an `OracleBuilderImpl` that wraps `OracleGenerator` to match the `OracleBuilder` protocol
6. Create `GateEngine` with the reviewer adapter
7. Call `run_task_loop()`

```python
# Replace the task() function in cli.py

@main.command()
@click.argument("description")
@click.option(
    "--difficulty",
    type=click.Choice(["mechanical", "local-reasoning", "architectural", "uncertain"]),
    default=None,
    help="Manual difficulty override (default: planner classifies).",
)
def task(description: str, difficulty: str | None) -> None:
    """Execute a single task (simpler loop, no milestones)."""
    import uuid
    from pathlib import Path
    from forge.config.loader import load_config, get_model_config
    from forge.models.provider import ModelProvider
    from forge.models.adapter import LocalModelAdapter
    from forge.aci.worker import run_worker, WorkerResult
    from forge.oracle.generator import OracleGenerator
    from forge.gate.engine import GateEngine
    from forge.orchestrator.task_loop import (
        run_task_loop, WorkerRunner, OracleBuilder, WorkerOutput,
    )

    project_root = Path(".")
    console.print(f"[bold green]FORGE[/] Task: {description}")

    # Load config
    try:
        cfg = load_config(project_root)
    except FileNotFoundError:
        console.print("[red]Error:[/] .forge/config.yaml not found. Run 'forge init' first.")
        raise SystemExit(1)

    # Build provider and adapters
    provider = ModelProvider(config=cfg)
    worker_adapter = LocalModelAdapter(provider, role="worker")
    reviewer_adapter = LocalModelAdapter(provider, role="reviewer")

    task_id = f"task-{uuid.uuid4().hex[:8]}"
    cwd = str(project_root.resolve())

    # Wrap run_worker to match WorkerRunner protocol
    class WorkerRunnerImpl:
        def run(self, task_description: str, todo_context: str | None = None) -> WorkerOutput:
            full_desc = task_description
            if todo_context:
                full_desc = f"{task_description}\n\n{todo_context}"
            console.print(f"  [cyan]Worker executing...[/]")
            result = run_worker(full_desc, model=worker_adapter, cwd=cwd)
            console.print(f"  [cyan]Worker done:[/] {result.iterations} iterations, {len(result.tool_calls)} tool calls")
            return WorkerOutput(
                completed=result.completed,
                final_message=result.final_message or "",
                tool_calls_count=len(result.tool_calls),
                error=result.error,
            )

    # Wrap OracleGenerator to match OracleBuilder protocol
    class OracleBuilderImpl:
        def __init__(self):
            self._gen = OracleGenerator(project_root=project_root)

        def build(self, task_id: str, iteration: int, worker_message: str):
            console.print(f"  [yellow]Generating Oracle (iteration {iteration})...[/]")
            oracle = self._gen.build_oracle(
                task_id=task_id,
                task_description=description,
                worker_model="Qwen/Qwen3.5-35B-A3B-GPTQ-Int4",
                worker_assessment=worker_message,
            )
            console.print(f"  [yellow]Oracle ready[/]")
            return oracle

    # Build gate
    gate = GateEngine(
        config=cfg.get("gate", {}),
        project_root=project_root,
        reviewer=reviewer_adapter,
    )

    console.print(f"  Task ID: {task_id}")
    if difficulty:
        console.print(f"  Difficulty override: {difficulty}")

    # Run the loop
    result = run_task_loop(
        task_id=task_id,
        task_description=description,
        worker=WorkerRunnerImpl(),
        oracle_builder=OracleBuilderImpl(),
        gate=gate,
        max_iterations=cfg.get("gate", {}).get("max_iterations", 3),
    )

    # Display results
    if result.passed:
        console.print(f"\n[bold green]PASS[/] after {result.iterations} iteration(s)")
        console.print(f"  Wall clock: {result.wall_clock_ms}ms")
        console.print(f"  Tool calls: {result.total_tool_calls}")
        if result.proposal:
            console.print(f"\n  [yellow]Shadow mode:[/] Commit proposed. Run 'forge approve {task_id}' to merge.")
    else:
        console.print(f"\n[bold red]FAIL[/] after {result.iterations} iteration(s)")
        if result.recovery_mode:
            console.print(f"  [red]Recovery mode activated[/]")
        if result.failure_summary:
            console.print(f"  {result.failure_summary}")
```

- [ ] **Step 2: Wire `forge oracle` to OracleGenerator**

```python
# Replace the oracle() function in cli.py

@main.command()
@click.argument("task_id", required=False)
def oracle(task_id: str | None) -> None:
    """Generate or display the Oracle snapshot for a task."""
    import json
    from pathlib import Path
    from forge.oracle.generator import OracleGenerator

    project_root = Path(".")
    console.print("[bold green]FORGE[/] Oracle")

    if task_id:
        # Display existing oracle
        oracle_dir = project_root / ".forge" / "oracles"
        matches = list(oracle_dir.glob(f"*{task_id}*.json"))
        if matches:
            data = json.loads(matches[0].read_text())
            console.print_json(json.dumps(data, indent=2))
        else:
            console.print(f"  No Oracle found for task: {task_id}")
        return

    # Generate fresh oracle for current working state
    gen = OracleGenerator(project_root=project_root)
    oracle = gen.build_oracle(
        task_id="manual",
        task_description="Manual oracle generation",
        worker_model="local",
        worker_assessment="Manual run",
    )
    console.print_json(json.dumps(oracle.to_json(), indent=2))
```

- [ ] **Step 3: Wire `forge review` to GateEngine**

```python
# Replace the review() function in cli.py

@main.command()
@click.argument("task_id", required=False)
def review(task_id: str | None) -> None:
    """Send the current Oracle to frontier reviewer(s)."""
    console.print("[bold green]FORGE[/] Review")
    console.print("  Note: Frontier review requires ANTHROPIC_API_KEY.")
    console.print("  For bootstrap testing, review happens inside 'forge task' loop.")
    console.print("  Standalone review of local Oracles: Phase 2+ feature.")
```

- [ ] **Step 4: Run full test suite**

Run: `pytest --tb=short`
Expected: All tests PASS (existing mocked tests unaffected, CLI changes don't break stubs)

- [ ] **Step 5: Commit**

```bash
git add src/forge/cli.py
git commit -m "[FORGE] cli: Wire forge task/oracle/review to library code"
```

---

### Task 5: Smoke Test — Live Qwen Endpoint

**Precondition:** Qwen running on localhost:8000

- [ ] **Step 1: Quick connectivity test**

```bash
cd ~/forge && source .venv/bin/activate
python3 -c "
from forge.config.loader import load_config
from forge.models.provider import ModelProvider
cfg = load_config('.')
provider = ModelProvider(config=cfg)
resp = provider.complete('worker', [{'role': 'user', 'content': 'Say hello in one word'}], max_tokens=20)
print(f'Response: {resp.content}')
print(f'Tokens: {resp.tokens_in} in, {resp.tokens_out} out, {resp.latency_ms}ms')
"
```

Expected: A response from Qwen with token counts and latency.

- [ ] **Step 2: CTO's smoke test — forge task with a trivial task**

```bash
forge task "Add a docstring to src/forge/__init__.py"
```

Expected: Worker calls view_file, edit_file, run_tests. Oracle generated. Gate reviews (this will use Qwen as reviewer too, since frontier keys may not be set — that's fine for smoke test). Full loop completes.

- [ ] **Step 3: Verify trace data**

```bash
forge metrics
forge boundary
```

Expected: At least one task recorded in trace DB and boundary data.

- [ ] **Step 4: Commit any generated state**

```bash
git add -A
git commit -m "[FORGE] bootstrap: First live smoke test against Qwen endpoint"
```

---

### Task 6: Full Bootstrap Protocol (HANDOFF.md Steps 1-7)

Only run after smoke test passes.

- [ ] **Step 1: Generate Oracle of FORGE's own codebase**

```bash
forge oracle
```

Verify: Core Oracle JSON with diff summary, codemap, mechanical checks.

- [ ] **Step 2: Run Desloppify mechanical**

```bash
forge quality --mechanical-only
```

Record: Baseline mechanical score.

- [ ] **Step 3: Run benchmark cartridge suite**

```bash
forge benchmark run --tag bootstrap-baseline
```

Record: Baseline results.

- [ ] **Step 4: Run forge task on FORGE itself**

```bash
forge task "Fix the highest-priority Desloppify issue in src/forge/enforcement/quality.py — cyclomatic complexity 18 > 10"
```

This is the real test: FORGE reviewing its own code changes.

- [ ] **Step 5: Check boundary and metrics**

```bash
forge boundary
forge metrics
```

- [ ] **Step 6: Document results**

Write `.forge/bootstrap-results.md` with: Oracle generation results, Desloppify baseline, benchmark results, any issues discovered.

- [ ] **Step 7: Commit bootstrap results**

```bash
git add -A
git commit -m "[FORGE] bootstrap: Phase 1.5 bootstrap test results"
```

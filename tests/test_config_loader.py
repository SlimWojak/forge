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

#!/usr/bin/env bash
# FORGE development environment setup script.
# Run this once after cloning to set up your local dev environment.
#
# Usage: bash init.sh
#
# What it does:
#   1. Creates a Python 3.11+ virtual environment
#   2. Installs the forge package in editable mode with dev dependencies
#   3. Creates the .forge/ state directory structure
#   4. Verifies the CLI is working

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔══════════════════════════════════════╗"
echo "║  FORGE v0.2 — Dev Environment Setup  ║"
echo "╚══════════════════════════════════════╝"
echo ""

# --- Step 1: Create virtual environment ---
echo "→ Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  Created .venv/"
else
    echo "  .venv/ already exists, skipping."
fi

# Activate
# shellcheck disable=SC1091
source .venv/bin/activate

# --- Step 2: Install dependencies ---
echo "→ Installing forge in editable mode with dev dependencies..."
pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet
echo "  Installed forge-ai and dev dependencies."

# --- Step 3: Create .forge/ state directory ---
echo "→ Initializing .forge/ directory structure..."

mkdir -p .forge/oracles
mkdir -p .forge/verdicts
mkdir -p .forge/traces
mkdir -p .forge/skills/prompts
mkdir -p .forge/skills/patterns
mkdir -p .forge/benchmarks
mkdir -p .forge/benchmark-results
mkdir -p .forge/digests
mkdir -p .forge/training
mkdir -p .forge/tools
mkdir -p .forge/decisions
mkdir -p .forge/blocked
mkdir -p .forge-worktrees

# Create state.json if it doesn't exist
if [ ! -f ".forge/state.json" ]; then
    cat > .forge/state.json << 'EOF'
{
  "$schema": "forge-state-v0.2",
  "mission": null,
  "shadow_mode": {
    "enabled": true,
    "pending_merges": [],
    "total_proposed": 0,
    "total_approved": 0,
    "total_rejected": 0
  },
  "recovery_mode": {
    "active": false,
    "consecutive_failures": 0,
    "threshold": 3
  },
  "config_hash": ""
}
EOF
    echo "  Created .forge/state.json"
fi

# Create hooks.yaml if it doesn't exist
if [ ! -f ".forge/hooks.yaml" ]; then
    cat > .forge/hooks.yaml << 'HOOKEOF'
# FORGE Layer 1: Mechanical Hooks
# See: FORGE_ARCHITECTURE_v0.2.md §6.1
#
# Hooks run outside the model — the model cannot override them.
# Latency budget: < 100ms per hook.

pre_edit:
  - action: syntax_check
    description: "Parse file with tree-sitter before applying edit"
    on_fail: reject_edit

post_edit:
  - action: auto_format
    description: "Run formatter after every successful edit"
    formatter: auto

  - action: secret_scan
    description: "Check for hardcoded secrets in edited content"
    patterns:
      - '(password|secret|api_key|token)\s*=\s*[''"][^''"]{8,}[''"]'
      - "-----BEGIN (RSA |EC )?PRIVATE KEY-----"
      - "AKIA[0-9A-Z]{16}"
    on_fail: reject_edit

pre_command:
  - action: allowlist_check
    description: "Block commands not in approved list"
    allowed_patterns:
      - "npm (test|run|install|build|lint)"
      - "python -m pytest"
      - "cargo (test|build|clippy)"
      - "git (status|diff|log|add|commit)"
      - "cat|head|tail|wc|grep|find|ls"
    blocked_patterns:
      - "rm -rf"
      - 'curl.*\| *(bash|sh)'
      - "sudo"
      - "chmod 777"
      - "eval"
    on_fail: reject_command

post_commit:
  - action: desloppify_mechanical
    description: "Run tree-sitter quality scan on committed files"

  - action: architectural_lint
    description: "Run architectural linter rules"
HOOKEOF
    echo "  Created .forge/hooks.yaml"
fi

# Create architecture.yaml if it doesn't exist
if [ ! -f ".forge/architecture.yaml" ]; then
    cat > .forge/architecture.yaml << 'ARCHEOF'
# FORGE Layer 2: Architectural Linter Rules
# See: FORGE_ARCHITECTURE_v0.2.md §6.2
#
# Rules are evaluated via regex matching and tree-sitter AST analysis.
# Error messages are agent-readable: WHAT + WHY + HOW TO FIX.

version: "0.2"

sensitive_paths:
  - "src/auth/**"
  - "src/payments/**"
  - "src/config/**"
  - "migrations/**"

rules:
  - id: "no-hardcoded-secrets"
    name: "No hardcoded secrets"
    pattern: '(password|secret|api_key|token|private_key)\s*=\s*[''"][^''"]{8,}[''"]'
    severity: "error"
    message: |
      VIOLATION: Hardcoded secret detected.
      File: {file}:{line}

      WHY: Secrets must come from environment variables or the config system.
      Hardcoded secrets get committed to git and are a security vulnerability.

      FIX: Use os.environ['{SECRET_NAME}'] or config.get('secrets.{name}')

  - id: "test-file-naming"
    name: "Test files must follow naming convention"
    files: "tests/**/*.py"
    custom_check: "test_file_matches_source"
    severity: "warning"
    message: |
      WARNING: Test file {file} does not correspond to a source file.
      Expected source: {expected_source}

      WHY: Test files should mirror the source tree for discoverability.
      FIX: Rename to match the source file it tests.
ARCHEOF
    echo "  Created .forge/architecture.yaml"
fi

echo "  .forge/ directory structure ready."

# --- Step 4: Verify ---
echo ""
echo "→ Verifying installation..."

if forge --version 2>/dev/null; then
    echo "  ✓ forge CLI is working"
else
    echo "  ✗ forge CLI failed — check installation"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  Setup complete!                     ║"
echo "║                                      ║"
echo "║  Activate:  source .venv/bin/activate║"
echo "║  Run CLI:   forge --help             ║"
echo "║  Run tests: pytest                   ║"
echo "╚══════════════════════════════════════╝"

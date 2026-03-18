# a8ra CLUSTER MANIFEST
```yaml
document: a8ra_CLUSTER_MANIFEST
version: 1.0
date: 2026-03-16
status: CANONICAL — built and verified this session
purpose: M2M orientation for any Claude instance navigating the a8ra hardware cluster
format: DENSE — token efficient, no prose padding
```

---

## 1. TOPOLOGY

```yaml
OPERATOR_TERMINAL:
  node: laptop-access
  hardware: MacBook Pro M3 Max 36GB
  os: macOS 15.5
  user: craigmackie
  tailscale_ip: 100.126.129.90
  role: COCKPIT — operator terminal, travels with G, not a server
  ansible: local connection (not SSH)
  zellij: none (cockpit, not a session node)
  et: client only (connects outward, no server)

KNOWLEDGE_SUBSTRATE:
  node: a8ra-m3
  hardware: Mac Studio M3 Ultra 512GB
  os: macOS 26.3
  user: a8ra_m3
  tailscale_ip: 100.114.164.22
  role: COO STATION — always-on control plane, bead field store, orchestrator
  zellij_session: m3-main (tabs: bead-ops, models, monitor, logs)
  et: server running (launchd, port 2022)
  mcp_server: port 7700 (tools: get_disk_usage, get_memory_usage, list_running_services, get_bead_field_status)
  coo_augmentations: [QMD 2.0.1, Superpowers 5.0.2, Ralph Loop 1.0.0]
  claude_code: 2.1.76 installed, authenticated
  context_autoload: ~/a8ra/CLAUDE.md → COO.md (symlink)
  mcp_client_config: ~/.claude/mcp_config.json (4 endpoints wired)
  start_coo: ~/a8ra/start-coo.sh

PHOENIX_NODE:
  node: m4-studio
  hardware: Mac Studio M4 Max 64GB
  os: macOS 26.3
  user: echopeso
  tailscale_ip: 100.120.83.66
  role: PHOENIX EXECUTION — core dev, sprint execution, test suites
  zellij_session: m4-main (tabs: phoenix, tests, scratch)
  et: server running (launchd, port 2022)
  mcp_server: port 7700 (tools: get_disk_usage, get_memory_usage, list_running_services, get_git_status)
  repos: ~/a8ra/ (all repos cloned)
  git_status_tool: accepts any repo name under ~/a8ra/

INFERENCE_NODE:
  node: dexter
  hardware: NVIDIA DGX Spark (Grace-Blackwell GB10) 120GB
  os: Ubuntu 24.04 aarch64
  user: a8ra_dgx
  tailscale_ip: 100.87.225.84
  role: PRODUCTION INFERENCE — Dream Cycle, SkillRL, Monte Carlo
  zellij_session: dgx1-main (tabs: inference, research, logs)
  et: server running (systemd, port 2022)
  mcp_server: port 7700 (tools: get_disk_usage, get_memory_usage, list_running_services, get_gpu_status, list_running_models)
  gpu: 1x GB10, verified idle at 36°C
  storage: 3.6TB root, 2% used

PLAYGROUND_NODE:
  node: playground-dgx
  hardware: NVIDIA DGX Spark (Grace-Blackwell GB10) 120GB
  os: Ubuntu 24.04 aarch64
  user: playground
  tailscale_ip: 100.125.254.45
  role: EXPERIMENTAL SANDBOX — local models, capability mapping, isolated
  zellij_session: dgx2-playground (tabs: experiments, scratch)
  et: server running (systemd, port 2022)
  mcp_server: port 7700 (tools: get_disk_usage, get_memory_usage, list_running_services, get_gpu_status, list_experiment_queue)
  gpu: 1x GB10, verified idle at 38°C
  storage: 3.6TB root, 9% used
  isolation: TAILSCALE ACL RESTRICTED — cannot initiate connections to other nodes
             inbound from cluster: ALLOWED
             outbound to cluster: BLOCKED
```

---

## 2. ACCESS PATTERNS

```yaml
FROM_COCKPIT (MacBook):
  aliases: ~/.zshrc
    m3:   "et a8ra_m3@a8ra-m3 -c 'zellij attach m3-main --create'"
    m4:   "et echopeso@m4-studio -c 'zellij attach m4-main --create'"
    dgx1: "et a8ra_dgx@dexter -c 'zellij attach dgx1-main --create'"
    dgx2: "et playground@playground-dgx -c 'zellij attach dgx2-playground --create'"
  
  auth: SSH keys (ed25519), passwordless across all nodes
  transport: Eternal Terminal (ET) — immortal sessions, survives network changes
  multiplexer: Zellij — persistent named sessions, tabs per role
  
FROM_MOBILE (iPhone):
  app: Termius Pro (synced, 4 hosts configured)
  hosts: [a8ra-m3, m4-studio, dexter, playground-dgx]
  startup_commands:
    m3:   "zellij attach m3-main --create"
    m4:   "zellij attach m4-main --create"
    dgx1: "zellij attach dgx1-main --create"
    dgx2: "zellij attach dgx2-playground --create"
  auth: a8ra-key (ED25519, stored in Termius keychain)

ZELLIJ_CONTROLS:
  new_tab: Ctrl+t then n
  rename_tab: Ctrl+t then r
  detach: Ctrl+o then d
  reattach: zellij attach <session-name>
```

---

## 3. NETWORK

```yaml
MESH: Tailscale (free tier, tailnet: slimwojak@gmail.com)
TRANSPORT: WireGuard (Tailscale managed)
SSH_AUTH: Tailscale SSH enabled on Linux nodes (dexter, playground-dgx)
          Standard SSH + Remote Login on macOS nodes (a8ra-m3, m4-studio)

ACL_RULES:
  production_cluster: full mesh (laptop, m3, m4, dexter)
  playground-dgx:
    inbound: ALLOWED from all
    outbound: BLOCKED to all cluster nodes
    rationale: experimental models cannot reach production

FILE_SHARING: NOT YET CONFIGURED (open item — Syncthing vs NFS on M3)
```

---

## 4. COO ORCHESTRATION MODEL

```yaml
HIERARCHY:
  CTO: G + Claude (strategy, high context, advisory) — runs on MacBook or M4
  COO: Claude Code on M3 Ultra (always-on orchestrator)
  DELEGATES:
    - Claude Code on M4 (Phoenix tasks, complex reasoning)
    - Claude Code on dexter (inference, production tasks)
    - Local models on playground (Qwen/Nemotron, grinding tasks) — NOT YET DEPLOYED
    - Pure compute scripts (any node)

COO_CAPABILITIES:
  qmd: semantic search over ~/a8ra/ knowledge base
       tools: query, get, multi_get, status
       index: 4 files, 7 vectors, Metal GPU accelerated
  superpowers: mission decomposition + delegation
       commands: /brainstorm, /write-plan, /execute-plan
       skills: subagent-driven-development, dispatching-parallel-agents
  ralph_loop: autonomous session cycling (Spitfire pattern)
       trigger: /ralph-loop "task" --completion-promise "DONE"
       cancel: /cancel-ralph
       pattern: pick task → execute → commit → reset context → repeat
       note: PASSIVE until triggered. Nothing runs without human initiation.

DELEGATION_PATTERN:
  CTO writes brief → hands to COO session on M3
  COO decomposes → routes to appropriate delegate
  Delegate executes → writes results to convention-based paths
  COO synthesises → surfaces to CTO
  
INVARIANTS_APPLY:
  INV-HUMAN-FRAMES: human initiates all missions
  INV-SOVEREIGN-VETO: G can halt via BROADCAST
  INV-OLYA-ABSOLUTE: Olya's NO on methodology is final
  playground isolation: local models cannot reach production even if misbehaving
```

---

## 5. MCP HEALTH LAYER

```yaml
PROTOCOL: HTTP, port 7700, all nodes
PERIMETER: Tailscale (no auth on MCP — Tailscale is the boundary)
ENDPOINTS:
  http://a8ra-m3:7700/health
  http://m4-studio:7700/health
  http://dexter:7700/health
  http://playground-dgx:7700/health

UNIVERSAL_TOOLS (all nodes):
  GET  /health                    → node name, Python version
  GET  /tools                     → list available tools
  POST /call/get_disk_usage       → disk stats
  POST /call/get_memory_usage     → RAM stats
  POST /call/list_running_services → active services

NODE_SPECIFIC_TOOLS:
  a8ra-m3:        get_bead_field_status
  m4-studio:      get_git_status (accepts repo name, looks in ~/a8ra/)
  dexter:         get_gpu_status, list_running_models
  playground-dgx: get_gpu_status, list_experiment_queue

SERVICE_MANAGEMENT:
  macOS (m3, m4): launchd plist at ~/Library/LaunchAgents/a8ra-mcp.plist
  Linux (dgx1, dgx2): systemd unit a8ra-mcp.service
  
COO_MCP_CONFIG: ~/.claude/mcp_config.json on a8ra-m3 (all 4 endpoints)
```

---

## 6. INFRASTRUCTURE AS CODE

```yaml
REPO: phoenix-swarm (github.com/SlimWojak/phoenix-swarm)
ANSIBLE_DIR: ~/a8ra/ansible/ (on MacBook cockpit)
FILES:
  inventory.yml:   5-node inventory, grouped by OS, tailscale hostnames
  snapshot.yml:    cluster state capture playbook
  deploy-mcp.yml:  MCP server deployment across all nodes
  ansible.cfg:     SSH pipelining, YAML output, parallel execution

COMMITTED_GATES:
  aea057d: Gate 4 — Ansible cluster snapshot baseline
  0cf94e8: Gate 5 — MCP health layer live on all 4 nodes
  b7940c9: Remove __pycache__, add gitignore
  [Gate 5b]: COO persistent session configured on M3 Ultra
  [Gate 5c]: COO fully equipped — QMD, Superpowers, Ralph Loop

RUN_SNAPSHOT: cd ~/a8ra/ansible && ansible-playbook snapshot.yml
VERIFY_CLUSTER: cd ~/a8ra/ansible && ansible all -m ping
DEPLOY_MCP: cd ~/a8ra/ansible && ansible-playbook deploy-mcp.yml
```

---

## 7. REPOS ON EACH NODE

```yaml
MACBOOK (cockpit):
  location: ~/a8ra/
  repos: [phoenix, dexter, spitfire, phoenix-swarm, research_accelerator, ra-tools, playground]
  github_cli: authenticated (slimwojak@gmail.com)

M4_STUDIO:
  location: ~/a8ra/
  repos: same set (primary dev machine)

M3_ULTRA:
  location: ~/a8ra/
  repos: same set
  note: CLAUDE.md symlink at ~/a8ra/CLAUDE.md → COO.md (auto-loads COO context)

DGX_NODES:
  status: Claude Code installed, repos NOT yet cloned
  next: clone ~/a8ra/ repos when needed for delegate tasks
```

---

## 8. WHAT'S NOT BUILT YET

```yaml
NEXT_IMMEDIATE:
  - Theme 2a: Qwen/Nemotron on playground-dgx via vLLM
  - Capability mapping experiments (50 structured output tasks)
  - File sharing: Syncthing or NFS decision (M3 Ultra as source)

NEXT_SOON:
  - Olya CSO deck: Mac Mini setup, Tailscale join, Claude interface
  - Theme 1c: CLI Orchestrator (sovereign factory) — depends on 2a empirical data
  - Task spec format: self-contained brief format for worker consumption

PARKED:
  - SELF_UPGRADING_META (carparked per master plan)
  - Multi-agent coordination testing (ChadBoar limitation noted)
  - HSM sovereign anchor (Gate 6+)
```

---

## 9. QUICK REFERENCE — COMMON OPERATIONS

```yaml
# Access any node (from MacBook)
m3 / m4 / dgx1 / dgx2

# Launch COO (from inside m3 session)
~/a8ra/start-coo.sh

# Check cluster health (from MacBook)
cd ~/a8ra/ansible && ansible all -m ping

# Query any node MCP tool (example)
curl -s http://dexter:7700/health
curl -s -X POST http://dexter:7700/call/get_gpu_status

# Start autonomous experiment loop (from COO session)
/ralph-loop "task description" --completion-promise "completion criteria"

# Search knowledge base (from COO session)
# QMD wired as MCP tool — Claude Code uses it automatically

# Snapshot cluster state
cd ~/a8ra/ansible && ansible-playbook snapshot.yml

# Deploy MCP updates to all nodes
cd ~/a8ra/ansible && ansible-playbook deploy-mcp.yml
```

---

```yaml
DESIGN_PRINCIPLE: |
  MacBook is the cockpit. M3 is the brain. DGXs are the muscle.
  Claude navigates via ET+Zellij (operator) and MCP+SSH (programmatic).
  Playground is isolated by design — experiments cannot reach production.
  COO orchestrates. Delegates execute. Human promotes.
  
BUILT: 2026-03-16 by G + Claude (scratchpad session)
STATUS: Gates 1-5 complete. Theme 1a + 1b operational.
```

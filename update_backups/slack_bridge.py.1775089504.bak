#!/usr/bin/env python3
"""
OpenJarvis Slack Bridge v9.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEW IN v9.1 (on top of v9.0):

  NEW WORKSPACE from intake chat
    Type in #jarvis-intake:
      NEW WORKSPACE jarvis-system "Working on the OpenJarvis bridge itself"
    → Creates workspace, writes WORKSPACE_BRIEF.md with your description
    → First loop is always INSTRUCTIONS_BOOTSTRAP mode
    → Agents collaboratively write INSTRUCTIONS.md before doing any real work
    → After instructions are complete the loop continues normally

  Workspace 1 — QCAI (quantum visualizer, existing project)
  Workspace 2 — JARVIS_SYSTEM (this bridge + agent pipeline itself)
    ws_2 knows it is working on its own source files
    Protected files list per workspace — agents never overwrite these
    ws_2 protected: slack_bridge.py, assembler.py, component_manager.py,
                    tester.py, reviewer.py, start_qcai.sh, load_and_run.sh

  Agent/Channel Gap Detection
    Coordinator checks if a needed agent channel is missing from CHANNELS
    If gaps found → writes AGENT_GAPS.md → posts to all channels
    Decision logic:
      ≤2 gaps AND work can proceed safely → logs gap, continues
      >2 gaps OR gap is blocking → pauses loop, posts PAUSE REQUIRED message
      You add channels manually → type RESUME to continue
    No cloud usage needed for gap detection — pure logic in Coordinator

  Ollama-Only Resilience Mode
    When OpenJarvis API is down AND cloud models unavailable:
      infer() falls back to Ollama automatically (already in v9.0)
      Agents trim prompts to stay within Ollama context limits
      Coordinator prescribes shorter sequences to reduce load
      Loop continues at reduced capability — never stops cold
    SHOW_BACKEND — shows which inference backend is currently active

  Per-Workspace Protected Files
    Each workspace has a PROTECTED_FILES list in INSTRUCTIONS.md
    Agents read this list and refuse to overwrite those files
    ws_2 seeds its own protected list on creation

FULL CHANNEL REGISTRY (16 channels):
  jarvis-intake            C0APZ5V9FHA
  jarvis-arch (Coord)      C0AQ4K6U52N
  jarvis-plan              C0AQ171J47P
  jarvis-prime             C0AQPRZCB16
  jarvis-build             C0AQQ11MPKJ
  jarvis-build-header      C0AQ180HA21
  jarvis-build-physics     C0APY8HQJN7
  jarvis-build-systems     C0AQYTZ8Q9W
  jarvis-build-render      C0AQ4KYMZH8
  jarvis-build-curriculum  C0AQHH1NEHX
  jarvis-build-integration C0AQ2J6UC6S
  jarvis-test              C0APYBX8LRZ
  jarvis-review            C0AQ1B85VCM
  jarvis-assemble          C0AQHDVL933
  jarvis-physics           C0AQQE69AGY
  jarvis-data              C0APESL1AVD

COMMANDS (all workspace-scoped):
  Loop:      STOP | PAUSE | RESUME | SHIP IT | PROTOCOL-ZERO | PROTOCOL-ZERO CLEAR
  Status:    STATUS | STATUS ALL | SHOW_SEQUENCE | SHOW_BACKEND | SHOW_INSTRUCTIONS
             SHOW_BRIEF | SHOW_CODE | SHOW_PHYSICS | SHOW_OUTPUT | CHANGELOG | BEST
  Version:   ROLLBACK <N> | CHECKPOINT | SHOW_VERSION <N>
  Data:      PULL_DATA | LOAD_TASK
  Workspace: WORKSPACES | WORKSPACE <N>
             NEW WORKSPACE <name> [description in quotes]
             RESET WORKSPACE | SHOW_GAPS
"""

import os, re, time, json, shutil, threading, logging, requests
from http.server    import HTTPServer, BaseHTTPRequestHandler
from collections    import deque
from datetime       import datetime
from pathlib        import Path
from slack_bolt     import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("jarvis")

# ─── Config ───────────────────────────────────────────────────────────────────

OPENJARVIS_API       = "http://127.0.0.1:8000"
OLLAMA_API           = "http://192.168.1.183:11434"

# ─── Model Registry ───────────────────────────────────────────────────────────
# Switch model at runtime via: SET MODEL <name> (while paused)
# or at task start:            LOAD_TASK use <name>
MODEL_REGISTRY = {
    # ctx here is what we REQUEST per-call via options.
    # The modelfile on Ollama sets the hard ceiling — these must be <= modelfile num_ctx.
    # If Ollama returns 500, lower the ctx value here first.
    "qwen3.5:9b-qcai":    {"ctx": 8192,  "predict": 4096, "label": "Primary (9B QCAI fine-tune)"},
    "qwen3.5:9b-qcai-max":{"ctx": 16384, "predict": 6000, "label": "Primary MAX CTX"},
    "qwen3-8b-jarvis":    {"ctx": 8192,  "predict": 3000, "label": "Fallback (8B jarvis)"},
    "qwen3:8b":           {"ctx": 4096,  "predict": 2000, "label": "Fallback minimal (base pull)"},
}
MODEL_DEFAULT  = "qwen3.5:9b-qcai"
MODEL          = MODEL_DEFAULT          # active model — changed by SET MODEL or LOAD_TASK
OLLAMA_MODEL   = MODEL                  # bridge uses MODEL for both API paths

SLACK_BOT_TOKEN      = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN      = os.environ.get("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

# ─── Channel Registry (all 16) ────────────────────────────────────────────────

CHANNELS = {
    # ── Core pipeline (16) ────────────────────────────────────────────────────
    "intake":             "C0APZ5V9FHA",
    "arch":               "C0AQ4K6U52N",
    "plan":               "C0AQ171J47P",
    "prime":              "C0AQPRZCB16",
    "build":              "C0AQQ11MPKJ",
    "build_header":       "C0AQ180HA21",
    "build_physics":      "C0APY8HQJN7",
    "build_systems":      "C0AQYTZ8Q9W",
    "build_render":       "C0AQ4KYMZH8",
    "build_curriculum":   "C0AQHH1NEHX",
    "build_integration":  "C0AQ2J6UC6S",
    "test":               "C0APYBX8LRZ",
    "review":             "C0AQ1B85VCM",
    "assemble":           "C0AQHDVL933",
    "physics":            "C0AQQE69AGY",
    "data":               "C0APESL1AVD",
    # ── System channels (5) ───────────────────────────────────────────────────
    "social":             "C0AQ79H8F3P",   # agent-to-agent ping (one at a time)
    "update":             "C0AQ8M54CNS",   # update agent — smart, resilient, safe
    "update_data":        "C0AQ4MXMXCK",   # update file list, reasons, recommendations
    "consensus":          "C0AR5AJVD2L",   # 12-node output filter + valuable data
    "commands":           "C0AQ7TUKMEZ",   # command registry + script list
    # ── Qubit Node Classical Layers (12) ─────────────────────────────────────
    "node_omega":         "C0APV6S5GKZ",   # Omega    — GodCore
    "node_guardian":      "C0AQ7808M5K",   # Guardian — GodCore
    "node_sentinel":      "C0AQAKT9TRQ",   # Sentinel — GodCore
    "node_void":          "C0AR4RUNQE4",   # Void     — GodCore
    "node_nexus":         "C0AQPGM6S9X",   # Nexus    — Independent
    "node_storm":         "C0AQE7EM6AG",   # Storm    — Independent
    "node_sora":          "C0AQAK5DVV0",   # Sora     — Independent
    "node_echo":          "C0AQ76Y30F7",   # Echo     — Independent
    "node_iris":          "C0AQ47J9L0K",   # Iris     — Maverick
    "node_sage":          "C0AQ47DBUG3",   # Sage     — Maverick
    "node_kevin":         "C0AQ76BUEAH",   # Kevin    — Maverick
    "node_atlas":         "C0AQPF0CAGH",   # Atlas    — Maverick
}

# Node name → channel key mapping for quantum ring operations
NODE_CHANNEL_MAP = {
    "Omega":    "node_omega",    "Guardian": "node_guardian",
    "Sentinel": "node_sentinel", "Void":     "node_void",
    "Nexus":    "node_nexus",    "Storm":    "node_storm",
    "Sora":     "node_sora",     "Echo":     "node_echo",
    "Iris":     "node_iris",     "Sage":     "node_sage",
    "Kevin":    "node_kevin",    "Atlas":    "node_atlas",
}

# Node family assignments
NODE_FAMILIES = {
    "Omega":"GodCore","Guardian":"GodCore","Sentinel":"GodCore","Void":"GodCore",
    "Nexus":"Independent","Storm":"Independent","Sora":"Independent","Echo":"Independent",
    "Iris":"Maverick","Sage":"Maverick","Kevin":"Maverick","Atlas":"Maverick",
}

AGENT_LABELS = {
    "intake":            "Intake",
    "arch":              "Coordinator",
    "plan":              "Plan",
    "prime":             "Prime",
    "build":             "Builder",
    "build_header":      "Builder:Header",
    "build_physics":     "Builder:Physics",
    "build_systems":     "Builder:Systems",
    "build_render":      "Builder:Render",
    "build_curriculum":  "Builder:Curriculum",
    "build_integration": "Builder:Integration",
    "test":              "Tester",
    "review":            "Reviewer",
    "assemble":          "Assembler",
    "physics":           "PhysicsValidator",
    "data":              "DataFeed",
}

SEQUENCEABLE_AGENTS = [
    "plan", "prime",
    "build_header", "build_physics", "build_systems",
    "build_render", "build_curriculum", "build_integration", "build",
    "test", "review", "assemble", "physics",
]

BUILDER_COMPONENTS = {
    "build_header":      ["c01_header"],
    "build_physics":     ["c02_physics", "c04_topology"],
    "build_systems":     ["c06_system",  "c07_dataserver"],
    "build_render":      ["c08_globe3d", "c09_metrics", "c10_nodeoutput"],
    "build_curriculum":  ["c03_nodes",   "c05_curriculum"],
    "build_integration": ["c11_controls","c12_visualizer","c13_main"],
}

ALL_CHANNEL_IDS   = list(CHANNELS.values())

def ch(key: str) -> str:
    return CHANNELS.get(key, CHANNELS["intake"])

# ─── Workspace Root ───────────────────────────────────────────────────────────

JARVIS_ROOT     = "/var/home/kmonette/OpenJarvis"
WORKSPACES_ROOT = os.path.join(JARVIS_ROOT, "workspaces")
MODELFILES_DIR  = os.path.join(JARVIS_ROOT, "ModelFiles")
UPDATES_DIR     = os.path.join(JARVIS_ROOT, "Updates")
ACTIVE_WS_FILE  = os.path.join(WORKSPACES_ROOT, "active_workspace.txt")
AGENT_GAPS_FILE = os.path.join(WORKSPACES_ROOT, "AGENT_GAPS.md")

# Protected files per workspace type — agents must never overwrite these
PROTECTED_FILES_QCAI = [
    "protected/qcai_3d_master.py",
    "GROUND_TRUTH.md",
    "INSTRUCTIONS.md",
]

PROTECTED_FILES_JARVIS_SYSTEM = [
    "slack_bridge.py",
    "assembler.py",
    "component_manager.py",
    "tester.py",
    "reviewer.py",
    "start_qcai.sh",
    "load_and_run.sh",
    "INSTRUCTIONS.md",
]

WS_SUBDIRS = [
    # Core
    "protected", "sandbox",
    "components_master", "components_promoted", "components_sandbox",
    "logs", "checkpoints",
    "versions/intake",  "versions/prime",  "versions/builder",
    "versions/physics", "versions/output", "versions/coordinator",
    # Update pipeline
    "update_sandbox",           # agents improve Kevin's recommendations here
    "update_versions",          # versioned update files (never overwritten)
    "SendToOpenJarvisUpdaterFiles",  # approved files queue for Kevin review
    "update_logs",              # update decisions, reasons, physics grounding
    # Social folders
    "social/classical",         # classical-mode agent communication
    "social/nonclassical",      # quantum/nonclassical mode
    "social/hybrid",            # hybrid mode
    "social/logs",              # all social comms logged
    # Command registry
    "commands/scripts",         # .py scripts agents create
    "commands/registry",        # latest command list files
    "commands/logs",            # command edits, additions, removals
    "commands/backups",         # command backups before removal
    # Intake documents
    "intake_documents/raw",     # Kevin uploads project files here
    "intake_documents/ingested",# processed intake files
    "intake_documents/merged",  # merged strategic intake doc
    # Node classical layers
    "node_data/raw",            # raw quantum node outputs
    "node_data/valuable",       # filtered valuable outputs
    "node_data/logs",           # full logs (valuable first, noise after)
    "node_data/consensus",      # consensus agent filtered outputs
    # Token continuation
    "continuations",            # safe-stop continuation files
]

# ─── Workspace Functions ──────────────────────────────────────────────────────

def get_active_ws() -> str:
    try:
        with open(ACTIVE_WS_FILE) as f:
            ws = f.read().strip()
            if os.path.isdir(ws): return ws
    except FileNotFoundError: pass
    ws = os.path.join(WORKSPACES_ROOT, "ws_1")
    set_active_ws(ws)
    return ws

def set_active_ws(path: str):
    os.makedirs(WORKSPACES_ROOT, exist_ok=True)
    with open(ACTIVE_WS_FILE, "w") as f: f.write(path)
    log.info(f"Active workspace → {path}")

def ws_path(subpath: str = "") -> str:
    base = get_active_ws()
    return os.path.join(base, subpath) if subpath else base

def ws_name() -> str:
    return os.path.basename(get_active_ws())

def ws_init(root: str = None):
    root = root or get_active_ws()
    for d in WS_SUBDIRS:
        os.makedirs(os.path.join(root, d), exist_ok=True)
    for fname, header in [
        ("logs/CHANGELOG.md",  "# QCAI Agent Loop — Changelog\n\n"),
        ("logs/SUMMARY.md",    "# Physics Summary Log\n\n"),
    ]:
        p = os.path.join(root, fname)
        if not os.path.exists(p):
            with open(p, "w") as f: f.write(header)
    master   = os.path.join(root, "protected", "qcai_3d_master.py")
    promoted = os.path.join(root, "qcai_3d.py")
    if not os.path.exists(master) and os.path.exists(promoted):
        shutil.copy2(promoted, master)
    log.info(f"Workspace initialized: {root}")

def list_workspaces() -> list:
    if not os.path.exists(WORKSPACES_ROOT): return []
    result = []
    for entry in sorted(os.listdir(WORKSPACES_ROOT)):
        full = os.path.join(WORKSPACES_ROOT, entry)
        if os.path.isdir(full) and entry.startswith("ws_"):
            result.append((full, entry, _ws_description(full)))
    return result

def _ws_description(root: str) -> str:
    for fname in ["WORKSPACE_BRIEF.md", "INSTRUCTIONS.md", "current_task.md"]:
        p = os.path.join(root, fname)
        if os.path.exists(p):
            try:
                with open(p) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            return line[:80]
            except: pass
    return "(no description yet)"

def create_workspace(folder_name: str, description: str = "") -> str:
    """Create a new workspace. Returns its path."""
    os.makedirs(WORKSPACES_ROOT, exist_ok=True)
    root = os.path.join(WORKSPACES_ROOT, folder_name)
    os.makedirs(root, exist_ok=True)
    ws_init(root)
    if description:
        with open(os.path.join(root, "WORKSPACE_BRIEF.md"), "w") as f:
            f.write(f"# {folder_name}\n\n{description}\n\nCreated: {datetime.now().isoformat()}\n")
    log.info(f"Created workspace: {root}")
    return root

def get_protected_files(root: str = None) -> list:
    """Return the protected files list for this workspace."""
    root = root or get_active_ws()
    name = os.path.basename(root).lower()
    # Read from INSTRUCTIONS.md PROTECTED_FILES section if present
    instr_path = os.path.join(root, "INSTRUCTIONS.md")
    if os.path.exists(instr_path):
        with open(instr_path) as f: content = f.read()
        m = re.search(r"## PROTECTED_FILES\n(.*?)(?:\n##|\Z)", content, re.DOTALL)
        if m:
            return [l.strip().lstrip("- ") for l in m.group(1).splitlines()
                    if l.strip() and not l.strip().startswith("#")]
    if "jarvis" in name or "system" in name or "ws_2" in name:
        return PROTECTED_FILES_JARVIS_SYSTEM
    return PROTECTED_FILES_QCAI

def is_protected(filepath: str, root: str = None) -> bool:
    protected = get_protected_files(root)
    rel = filepath.replace((root or get_active_ws()) + "/", "")
    return any(rel == p or filepath.endswith(p) for p in protected)

# ─── Workspace-Scoped I/O ─────────────────────────────────────────────────────

def wsr(key: str) -> str:
    paths = {
        "task":        "current_task.md",
        "intake":      "intake_brief.md",
        "prime":       "prime_plan.md",
        "coordinator": "coordinator_sequence.md",
        "builder":     "builder_code.py",
        "physics":     "physics_report.md",
        "output":      "qcai_3d.py",
        "gt":          "GROUND_TRUTH.md",
        "working":     "sandbox/qcai_3d_working.py",
        "candidate":   "sandbox/qcai_3d_candidate.py",
        "master":      "protected/qcai_3d_master.py",
        "instructions":"INSTRUCTIONS.md",
        "brief":       "WORKSPACE_BRIEF.md",
        "gaps":        "logs/AGENT_GAPS.md",
        "changelog":   "logs/CHANGELOG.md",
        "summary":     "logs/SUMMARY.md",
    }
    return ws_path(paths.get(key, key))

def read_file(path: str) -> str:
    try:
        with open(path) as f: return f.read()
    except FileNotFoundError: return f"[File not found: {path}]"
    except Exception as e:    return f"[Error: {e}]"

def write_file(path: str, content: str, root: str = None) -> bool:
    if is_protected(path, root):
        log.warning(f"BLOCKED write to protected file: {path}")
        return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f: f.write(content)
        return True
    except Exception as e:
        log.error(f"Write {path}: {e}"); return False

def append_file(path: str, content: str) -> bool:
    """Append-only — used for INSTRUCTIONS.md. Never overwrites."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a") as f: f.write(content)
        return True
    except Exception as e:
        log.error(f"Append {path}: {e}"); return False

def ws_read(key: str) -> str:
    return read_file(wsr(key))

def ws_write(key: str, content: str) -> bool:
    return write_file(wsr(key), content)

def ver_write(agent: str, loop: int, content: str, ext: str = None):
    exts = {"intake":"md","prime":"md","builder":"py","physics":"md",
            "output":"py","coordinator":"md"}
    ext  = ext or exts.get(agent, "txt")
    path = ws_path(f"versions/{agent}/loop_{loop:03d}_{agent}.{ext}")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f: f.write(content)
    except Exception as e: log.error(f"ver_write {agent}: {e}")

def ver_read(agent: str, loop: int) -> str:
    exts = {"intake":"md","prime":"md","builder":"py","physics":"py","output":"py","coordinator":"md"}
    ext  = exts.get(agent, "txt")
    path = ws_path(f"versions/{agent}/loop_{loop:03d}_{agent}.{ext}")
    if os.path.exists(path):
        with open(path) as f: return f.read()
    return f"[Version not found: {agent} loop {loop}]"

def list_versions(agent: str) -> str:
    folder = ws_path(f"versions/{agent}")
    if not os.path.exists(folder): return f"No versions for {agent}"
    files = sorted(os.listdir(folder))
    return "\n".join(f"  {f}" for f in files[-10:]) if files else "No versions yet"

def ckpt_save(name: str, content: str):
    path = ws_path(f"checkpoints/{name}.py")
    try:
        with open(path, "w") as f: f.write(content)
    except Exception as e: log.error(f"Checkpoint {name}: {e}")

def ckpt_read(name: str) -> str:
    path = ws_path(f"checkpoints/{name}.py")
    try:
        with open(path) as f: return f.read()
    except: return f"[Checkpoint not found: {name}]"

def changelog_append(loop, score, phys, lines, summary):
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"| {loop:3d} | {ts} | Score:{score:2d}/10 | Physics:{phys:<7} | Lines:{lines:4d} | {summary} |\n"
    try:
        with open(wsr("changelog"), "a") as f: f.write(line)
    except Exception as e: log.error(f"Changelog: {e}")

def summary_append(loop, report):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with open(wsr("summary"), "a") as f:
            f.write(f"\n## Loop {loop} — {ts}\n\n{report[:500]}\n\n---\n")
    except Exception as e: log.error(f"Summary: {e}")

# ─── Inference (Ollama fallback) ──────────────────────────────────────────────

_api_healthy  = True
_backend_used = "openjarvis"   # "openjarvis" | "ollama" | "none"

def infer(system_prompt: str, user_msg: str,
          temperature: float = 0.15, max_tokens: int = 2000) -> str:
    global _api_healthy, _backend_used

    # Trim prompts when in Ollama mode (smaller context window)
    if not _api_healthy:
        # Trim to 60% of context to leave room for response
        _ctx   = MODEL_REGISTRY.get(MODEL, {}).get("ctx", 24576)
        _chars = int(_ctx * 3.2)   # ~3.2 chars/token approximation
        system_prompt = system_prompt[:int(_chars * 0.25)]   # 25% for system
        user_msg      = user_msg[:int(_chars * 0.50)]        # 50% for user
        # Cap outputs to what the registry says for this model
        max_tokens    = min(max_tokens, MODEL_REGISTRY.get(MODEL, {}).get("predict", 2000))

    # ── OpenJarvis API ────────────────────────────────────────────────────────
    if _api_healthy:
        try:
            resp = requests.post(
                f"{OPENJARVIS_API}/v1/chat/completions",
                json={"model": MODEL,
                      "messages": [{"role":"system","content":system_prompt},
                                   {"role":"user",  "content":user_msg}],
                      "max_tokens": max_tokens, "temperature": temperature},
                timeout=300)
            resp.raise_for_status()
            _api_healthy  = True
            _backend_used = "openjarvis"
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log.warning(f"OpenJarvis API: {e} — falling back to Ollama")
            _api_healthy = False

    # ── Ollama fallback ───────────────────────────────────────────────────────
    try:
        resp = requests.post(
            f"{OLLAMA_API}/api/chat",
            json={"model": MODEL,
                  "messages": [{"role":"system","content":system_prompt},
                                {"role":"user",  "content":user_msg}],
                  "stream": False,
                  "options": {
                      "temperature": temperature,
                      "num_predict": max_tokens,
                      "num_ctx": MODEL_REGISTRY.get(MODEL, {}).get("ctx", 24576),
                  }},
            timeout=600)
        if not resp.ok:
            # Log the actual error body so we can diagnose 500s
            log.error(f"Ollama HTTP {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
        _backend_used = "ollama"
        return resp.json()["message"]["content"].strip()
    except Exception as e:
        log.error(f"Ollama also failed: {e}")
        _backend_used = "none"
        return f"❌ All inference backends unavailable: {e}"

def check_api() -> bool:
    global _api_healthy
    try:
        r = requests.get(f"{OPENJARVIS_API}/health", timeout=5)
        if r.status_code == 200:
            _api_healthy = True; return True
    except: pass
    return False

def check_ollama() -> bool:
    try:
        r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
        return r.status_code == 200
    except: return False

def backend_status() -> str:
    api_ok    = check_api()
    ollama_ok = check_ollama()
    active    = _backend_used
    return (f"Backend: *{active}* | "
            f"OpenJarvis: {'✅' if api_ok else '❌'} | "
            f"Ollama: {'✅' if ollama_ok else '❌'}")

def active_model_info() -> str:
    """Return a formatted string showing active model + its config."""
    global MODEL
    info = MODEL_REGISTRY.get(MODEL, {})
    ctx     = info.get("ctx",     "?")
    predict = info.get("predict", "?")
    label   = info.get("label",   "unknown")
    available = "\n".join(f"  `{k}` — {v['label']} (ctx={v['ctx']}, predict={v['predict']})"
                           for k, v in MODEL_REGISTRY.items())
    return (f"*Active model:* `{MODEL}`\n"
            f"Label: {label}\n"
            f"num_ctx: {ctx:,} | num_predict: {predict:,}\n\n"
            f"*Available models:*\n{available}")

def set_model(name: str) -> tuple:
    """Switch active model. Returns (success, message)."""
    global MODEL, OLLAMA_MODEL
    if name not in MODEL_REGISTRY:
        available = ", ".join(f"`{k}`" for k in MODEL_REGISTRY)
        return False, f"Unknown model `{name}`. Available: {available}"
    MODEL = name
    OLLAMA_MODEL = name
    info = MODEL_REGISTRY[name]
    log.info(f"Model switched to: {name} (ctx={info['ctx']}, predict={info['predict']})")
    return True, (f"✅ Model set to `{name}`\n"
                  f"{info['label']} | ctx={info['ctx']:,} | predict={info['predict']:,}\n"
                  f"Takes effect on next inference call.")

# ─── Slack helpers ────────────────────────────────────────────────────────────

app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
BOT_USER_ID = ""

def post(ch_id: str, text: str) -> dict:
    """Post to Slack. Auto-splits at 3800 chars to stay under 4000 char recommendation."""
    try:
        if len(text) <= 3800:
            return app.client.chat_postMessage(channel=ch_id, text=text)
        # Long message — split into chunks at newline boundaries
        chunks = _split_message(text, 3800)
        result = {}
        for i, chunk in enumerate(chunks):
            prefix = f"*[{i+1}/{len(chunks)}]* " if len(chunks) > 1 else ""
            result = app.client.chat_postMessage(channel=ch_id, text=prefix + chunk)
        return result
    except Exception as e:
        log.error(f"post {ch_id}: {e}"); return {}

def post_snippet(ch_id: str, content: str, title: str = "output", filetype: str = "text") -> dict:
    """Post as a Slack snippet (file upload) for content >4000 chars. Max 1MB."""
    try:
        return app.client.files_upload_v2(
            channel=ch_id,
            content=content,
            filename=f"{title}.txt",
            title=title,
            filetype=filetype,
        )
    except Exception as e:
        log.error(f"snippet {ch_id}: {e}"); return {}

def smart_post(ch_id: str, text: str, title: str = "output") -> dict:
    """Choose post method based on content length.
    <4000 chars  → regular message
    4000-39000   → split into chunks
    >39000       → Slack snippet (file)
    """
    if len(text) <= 3800:
        return post(ch_id, text)
    if len(text) <= 39000:
        chunks = _split_message(text, 3800)
        result = {}
        for i, chunk in enumerate(chunks):
            result = app.client.chat_postMessage(
                channel=ch_id,
                text=f"*[{i+1}/{len(chunks)}]* {chunk}")
        return result
    return post_snippet(ch_id, text, title)

def _split_message(text: str, limit: int = 3800) -> list:
    """Split text at newline boundaries, never mid-word."""
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text); break
        # Find last newline before limit
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit  # no newline — hard split
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks

def update(ch_id: str, ts: str, text: str):
    try: app.client.chat_update(channel=ch_id, ts=ts, text=text[:3800])
    except Exception as e: log.error(f"update {ch_id}: {e}")

def post_all(text: str):
    for key in ["intake","arch","prime","build","physics","data"]:
        post(ch(key), text)

def post_node(node_name: str, text: str) -> dict:
    """Post to a node's classical layer channel."""
    key = NODE_CHANNEL_MAP.get(node_name)
    if key: return smart_post(ch(key), text)
    return {}

# ─── Instructions Management ──────────────────────────────────────────────────

def ensure_instructions(loop: int) -> bool:
    """Create seed INSTRUCTIONS.md if absent. Returns True if just created."""
    path = wsr("instructions")
    if os.path.exists(path): return False
    name = ws_name()
    brief = ws_read("brief")
    brief_line = brief.splitlines()[2] if len(brief.splitlines()) > 2 else "(see WORKSPACE_BRIEF.md)"
    seed = (
        f"# INSTRUCTIONS — {name}\n"
        f"# Created: {datetime.now().isoformat()}\n"
        f"# APPEND-ONLY — rules accumulate, never overwrite\n\n"
        f"## Project\n{brief_line}\n\n"
        f"## Rules\n"
        f"- Tell the truth, even when uncomfortable\n"
        f"- Never truncate code output\n"
        f"- Physics formulas are invariant — never invent alternatives\n"
        f"- Respect all entries in PROTECTED_FILES below\n\n"
        f"## PROTECTED_FILES\n"
    )
    # Seed protected files by workspace type
    protected = get_protected_files()
    for p in protected:
        seed += f"- {p}\n"
    seed += "\n## Agent Rules\n(Coordinator will enrich this on first loop)\n"
    with open(path, "w") as f: f.write(seed)
    log.info(f"Created INSTRUCTIONS.md for {name}")
    return True

def append_instructions(content: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    append_file(wsr("instructions"), f"\n## Rules Added — {ts}\n{content}\n")

# ─── Agent Gap Detection ──────────────────────────────────────────────────────

def detect_agent_gaps(needed_agents: list) -> list:
    """Return list of agents in needed_agents that have no channel ID registered."""
    return [a for a in needed_agents if a not in CHANNELS]

def assess_gap_severity(gaps: list, needed: list) -> str:
    """
    Returns 'proceed', 'log_and_continue', or 'pause'.
    Logic:
      0 gaps → proceed
      1-2 gaps AND they are not in the critical path → log_and_continue
      >2 gaps OR any gap is a critical agent → pause
    """
    if not gaps: return "proceed"
    critical = {"physics", "prime", "arch", "build", "intake"}
    blocking  = [g for g in gaps if g in critical]
    if blocking or len(gaps) > 2: return "pause"
    return "log_and_continue"

def log_agent_gaps(gaps: list, loop: int, recommendation: str):
    """Write gap report to workspace logs/AGENT_GAPS.md."""
    ts   = datetime.now().strftime("%Y-%m-%d %H:%M")
    path = wsr("gaps")
    entry = (
        f"\n## Gap Report — Loop {loop} — {ts}\n"
        f"Workspace: {ws_name()}\n"
        f"Missing agents: {gaps}\n"
        f"Recommendation: {recommendation}\n"
        f"Action required:\n"
        + "\n".join(f"  - Create Slack channel for: {a}" for a in gaps)
        + "\n"
        f"After creating channels, update CHANNELS dict in slack_bridge.py\n"
        f"Then type RESUME to continue.\n"
    )
    try:
        with open(path, "a") as f: f.write(entry)
    except Exception as e: log.error(f"Gap log: {e}")

# ─── Code Extraction & Guardian ───────────────────────────────────────────────

def extract_code(text: str) -> str:
    t = text.strip()
    m = re.search(r"```python\n(.*?)```", t, re.DOTALL)
    if m: return m.group(1).strip()
    m = re.search(r"```\n(.*?)```", t, re.DOTALL)
    if m: return m.group(1).strip()
    return t

def guardian_check(code: str, min_lines: int = 400) -> tuple:
    if not code or not code.strip():       return False, "empty output"
    lines = code.count('\n')
    if lines < min_lines:                  return False, f"too short ({lines} lines)"
    if '```' in code:                      return False, "contains markdown fences"
    try:    compile(code, '<out>', 'exec')
    except SyntaxError as e:               return False, f"syntax error: {e}"
    # Only require GLOBE assertion for QCAI workspace (ws_1 / quantum projects)
    # ws_2 (jarvis-system) and general workspaces don't have GLOBE
    ws = os.path.basename(get_active_ws()).lower()
    is_qcai_ws = "ws_1" in ws or "qcai" in ws or "quantum" in ws
    if is_qcai_ws and 'GLOBE' not in code:
        return False, "missing GLOBE assertion (QCAI workspace)"
    return True, "ok"

def promote_to_output(code: str, loop: int, source: str) -> tuple:
    valid, reason = guardian_check(code)
    if not valid:
        log.warning(f"Loop {loop} [{source}] REJECTED: {reason}"); return False, reason
    write_file(wsr("output"), code)
    ver_write("output", loop, code, "py")
    log.info(f"Loop {loop} [{source}] PROMOTED ({code.count(chr(10))} lines)")
    return True, "ok"

def get_builder_base() -> tuple:
    promoted = read_file(wsr("output"))
    if "[File not found" not in promoted and len(promoted) > 1000:
        return promoted, "qcai_3d.py (latest promoted)"
    master = read_file(wsr("master"))
    if "[File not found" not in master: return master, "master"
    return "", "none — write from scratch"

# ─── Loop State ───────────────────────────────────────────────────────────────

class LoopState:
    def __init__(self):
        self.running        = False
        self.paused         = False
        self.protocol_zero  = False
        self.loop_count     = 0
        self.last_sequence  = []
        self.last_intake    = ""
        self.last_prime     = ""
        self.last_physics   = ""
        self.original_req   = ""
        self.quantum_data   = {}
        self.data_history   = deque(maxlen=10)
        self.best_score     = 0
        self.mode           = "normal"   # "normal" | "instructions_bootstrap"
        self.lock           = threading.Lock()

    def reset(self):
        self.running = False; self.paused = False
        self.loop_count = 0; self.last_sequence = []; self.mode = "normal"

state = LoopState()

def wait_if_paused() -> bool:
    while state.paused:
        if not state.running or state.protocol_zero: return False
        time.sleep(1)
    return state.running and not state.protocol_zero

# ─── Extract helpers ──────────────────────────────────────────────────────────

def extract_score(text: str) -> int:
    m = re.search(r"QUALITY SCORE:\s*(\d+)/10", text)
    return int(m.group(1)) if m else 0

def extract_physics_status(text: str) -> str:
    m = re.search(r"PHYSICS STATUS:\s*(PASS|FAIL|PARTIAL)", text)
    return m.group(1) if m else "UNKNOWN"

def extract_sequence(text: str) -> list:
    m = re.search(r"SEQUENCE:\s*\[([^\]]+)\]", text, re.IGNORECASE)
    if m:
        raw = [x.strip().strip('"\'').lower().replace("-","_") for x in m.group(1).split(",")]
        return [a for a in raw if a in SEQUENCEABLE_AGENTS]
    m = re.search(r"SEQUENCE:(.*?)(?:\n##|\Z)", text, re.IGNORECASE | re.DOTALL)
    if m:
        agents = []
        for line in m.group(1).strip().splitlines():
            token = re.sub(r"^\s*[\d\.\-\*]+\s*", "", line).strip().lower().replace("-","_")
            if token in SEQUENCEABLE_AGENTS: agents.append(token)
        return agents
    return []

def extract_focus_map(text: str) -> dict:
    result = {}
    m = re.search(r"FOCUS:(.*?)(?:INSTRUCTIONS_APPEND:|NEW_AGENTS:|━━━|\Z)",
                  text, re.DOTALL | re.IGNORECASE)
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r"\s*(\w+):\s*(.+)", line)
            if mm:
                key = mm.group(1).lower().replace("-","_")
                result[key] = mm.group(2).strip()
    return result

def extract_new_agents(text: str) -> list:
    """Parse NEW_AGENTS: section from Coordinator output."""
    m = re.search(r"NEW_AGENTS:(.*?)(?:\n##|━━━|\Z)", text, re.DOTALL | re.IGNORECASE)
    if not m: return []
    agents = []
    for line in m.group(1).strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            agents.append(line.lstrip("- ").strip())
    return agents

def fmt_qdata(full: bool = False) -> str:
    d = state.quantum_data
    if not d: return "  [no live data — run qcai_3d.py]"
    lines = [
        f"  step={d.get('step',0)}  cv={d.get('cv',0):.4f}  "
        f"negfrac={d.get('negfrac',0):.4f}  nc={d.get('nc_count',0)}/12",
        f"  PCM={d.get('mean_pcm',0):+.4f}  coh={d.get('coherence',0):.4f}  "
        f"R={d.get('reward',0):.4f}",
    ]
    if full:
        nn = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
              "Echo","Iris","Sage","Kevin","Atlas","Void"]
        outputs = d.get("node_outputs", [])
        domains = d.get("domains",      [])
        if outputs:
            lines.append("  Nodes:")
            for i, (name, out) in enumerate(zip(nn, outputs)):
                dom = domains[i] if i < len(domains) else "?"
                lines.append(f"    {name:<8}[{dom:<12}] {out}")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# ── SOCIAL MESSAGING SYSTEM v2 ────────────────────────────────────────────────
# Full conversation thread with collection, merge, and return-to-requester.
#
# FLOW:
#   1. social_ping(from, [A, B, C], message, priority)
#      → assigns a unique ping_id, writes to queue
#   2. Dispatcher picks next ping (priority-ordered, heapq)
#      → One session at a time — A responds, then B, then C
#      → Each recipient gets the original question + all prior responses
#      → Per-recipient timeout (default 90s) — partial results on timeout
#   3. After all recipients respond (or timeout):
#      → All responses merged into one structured document
#      → Merged doc written to social/classical/<ping_id>_merged.md
#      → Requester notified with full merged response
#      → Everything logged to social/logs/
#
# RESILIENCE:
#   - Queue persisted to social/logs/queue_persist.json on every change
#   - On startup, unfinished pings are re-queued
#   - Dedup by content hash — same ping never queued twice in same minute
#   - Each agent response saved individually before merge
#   - If merge fails, individual responses still available
#   - Slack delivery retried 3x with backoff before marking failed
#
# PRIORITY:
#   1 = critical (human command, safety alert)
#   3 = high     (coordinator directive)
#   5 = normal   (agent-to-agent question)
#   7 = low      (informational, non-urgent)
#   9 = background (logging, housekeeping)
# ═══════════════════════════════════════════════════════════════════════════════

import heapq
import hashlib

_social_heap   = []            # heapq: (priority, timestamp, ping_id, SocialPing)
_social_lock   = threading.Lock()
_social_active = [None]        # ping_id currently being processed
_social_seen   = set()         # dedup set: content_hash + minute
_SOCIAL_TIMEOUT = 90           # seconds per recipient before skip
_SOCIAL_RETRY   = 3            # Slack delivery retries

class SocialPing:
    """A single social conversation request."""
    __slots__ = ("ping_id","from_agent","to_agents","message",
                 "priority","ts","responses","status","failures")
    def __init__(self, from_agent, to_agents, message, priority=5):
        self.ping_id     = f"{from_agent}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        self.from_agent  = from_agent
        self.to_agents   = list(to_agents)   # ordered — respected strictly
        self.message     = message
        self.priority    = priority
        self.ts          = datetime.now().isoformat()
        self.responses   = {}    # {agent_key: response_text}
        self.status      = "queued"   # queued→active→collecting→merging→complete→failed
        self.failures    = []    # agents that timed out or errored

    def to_dict(self):
        return {k: getattr(self,k) for k in self.__slots__}

def social_ping(from_agent: str, to_agents: list, message: str,
                priority: int = 5) -> str:
    """
    Queue a social conversation request.
    Returns ping_id for tracking.
    Dedup: same (from, message) within the same minute is ignored.
    """
    # Dedup check
    dedup_key = hashlib.md5(f"{from_agent}:{message}:{datetime.now().strftime('%Y%m%d_%H%M')}".encode()).hexdigest()
    if dedup_key in _social_seen:
        log.info(f"Social dedup: skipping duplicate ping from {from_agent}")
        return ""
    _social_seen.add(dedup_key)

    ping = SocialPing(from_agent, to_agents, message, priority)
    _social_log(ping.ping_id, "queued", {"from": from_agent, "to": to_agents,
                                          "message": message[:300], "priority": priority})

    with _social_lock:
        heapq.heappush(_social_heap, (priority, ping.ts, ping.ping_id, ping))
        _social_persist_queue()

    # Announce on social channel
    smart_post(ch("social"),
        f"📣 *Social Ping Queued*\n"
        f"From: `{from_agent}` → `{'`, `'.join(to_agents)}`\n"
        f"Priority: {priority} | ID: `{ping.ping_id[-20:]}`\n"
        f"{message[:200]}")

    return ping.ping_id

def _social_deliver(ch_id: str, text: str) -> bool:
    """Post to Slack with 3 retries and exponential backoff."""
    for attempt in range(_SOCIAL_RETRY):
        try:
            result = app.client.chat_postMessage(channel=ch_id, text=text[:3800])
            if result.get("ok"): return True
        except Exception as e:
            log.warning(f"Social delivery attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return False

def _get_agent_response(ping: SocialPing, agent_key: str,
                        prior_responses: dict) -> tuple:
    """
    Call the agent LLM to produce its response to the social ping.
    Returns (response_text, timed_out: bool).
    """
    agent_ch = CHANNELS.get(agent_key)
    if not agent_ch:
        return f"[{agent_key}: no channel registered]", False

    # Build context: original question + all prior responses so far
    prior_block = ""
    if prior_responses:
        prior_block = "\n\nPRIOR RESPONSES IN THIS THREAD:\n"
        for prev_agent, prev_resp in prior_responses.items():
            prior_block += f"\n[{prev_agent}]: {prev_resp[:400]}\n"

    sys_p = f"""{_mission()}
You are OpenJarvis {AGENT_LABELS.get(agent_key, agent_key)} responding in the social channel.
You have been pinged by {ping.from_agent} with a question/request.
Read all prior responses carefully — do not repeat what others said.
Add your unique perspective based on your role and domain.
Be concise — max 400 words. This is collaborative, not competitive.
After all agents respond, your collective answers will be merged and sent back to {ping.from_agent}."""

    user_msg = (f"QUESTION FROM {ping.from_agent}:\n{ping.message}\n"
                f"{prior_block}\n\nYour response as {agent_key}:")

    # Notify agent's channel that they're being asked
    _social_deliver(agent_ch,
        f"💬 *Social Thread* | From: `{ping.from_agent}`\n"
        f"Ping ID: `{ping.ping_id[-16:]}`\n\n"
        f"*Question:* {ping.message[:300]}\n"
        f"{prior_block[:600] if prior_block else ''}\n\n"
        f"_Generating response..._")

    # Get response with timeout enforcement via thread
    response_holder = [None]
    def _call():
        response_holder[0] = infer(sys_p, user_msg, temperature=0.20, max_tokens=600)

    t = threading.Thread(target=_call, daemon=True)
    t.start()
    t.join(timeout=_SOCIAL_TIMEOUT)

    if t.is_alive() or response_holder[0] is None:
        timeout_msg = f"[{agent_key}: timed out after {_SOCIAL_TIMEOUT}s]"
        _social_deliver(agent_ch,
            f"⏱️ *Social Thread* — Response timed out\n"
            f"Ping ID: `{ping.ping_id[-16:]}` | Moving to next agent.")
        return timeout_msg, True

    response = response_holder[0]

    # Post agent's response to their channel
    _social_deliver(agent_ch,
        f"✅ *Social Response Sent*\n"
        f"Ping ID: `{ping.ping_id[-16:]}`\n\n{response[:600]}")

    # Write individual response to social folder
    resp_path = ws_path(f"social/classical/{ping.ping_id}_{agent_key}.md")
    try:
        os.makedirs(os.path.dirname(resp_path), exist_ok=True)
        with open(resp_path, "w") as f:
            f.write(f"# Response: {agent_key}\n"
                    f"Ping ID: {ping.ping_id}\n"
                    f"From: {ping.from_agent}\n"
                    f"Question: {ping.message}\n\n"
                    f"## Response\n{response}\n")
    except Exception as e:
        log.error(f"Social response write {agent_key}: {e}")

    return response, False

def _merge_responses(ping: SocialPing) -> str:
    """
    Merge all agent responses into one structured document.
    Uses LLM to synthesize — falls back to concatenation if LLM fails.
    """
    if not ping.responses:
        return f"[No responses collected for ping {ping.ping_id}]"

    # Try LLM synthesis
    try:
        responses_block = "\n\n".join(
            f"**{agent}**: {resp}"
            for agent, resp in ping.responses.items()
            if not resp.startswith("[") or "timed out" not in resp
        )
        failures_note = (f"\nNote: {', '.join(ping.failures)} timed out or failed."
                         if ping.failures else "")

        sys_p = f"""{_mission()}
You are synthesizing responses from multiple agents into one clear merged answer.
Original question from {ping.from_agent}: {ping.message}
Rules:
- Keep each agent's unique contribution
- Remove true duplicates but preserve complementary perspectives
- Structure clearly: one section per major theme
- Note any disagreements or contradictions
- Max 800 words total
- End with CONSENSUS: one sentence summary"""

        merged = infer(sys_p,
                       f"AGENT RESPONSES:\n{responses_block}{failures_note}",
                       temperature=0.10, max_tokens=1000)
        if merged and not merged.startswith("❌"):
            return merged
    except Exception as e:
        log.error(f"Social merge LLM failed: {e}")

    # Fallback: structured concatenation (no LLM needed)
    lines = [f"# Social Thread Merged Response",
             f"From: {ping.from_agent} | Ping: {ping.ping_id}",
             f"Question: {ping.message}",
             f"Agents: {', '.join(ping.to_agents)}",
             f""]
    for agent, resp in ping.responses.items():
        lines.append(f"## {agent}\n{resp}\n")
    if ping.failures:
        lines.append(f"## Failed/Timed Out\n{', '.join(ping.failures)}\n")
    return "\n".join(lines)

def _social_dispatcher():
    """
    Background thread — the heart of the social system.
    Processes one ping at a time, in priority order.
    Collects all responses, merges, returns to requester.
    Persists state on every step for resilience.
    """
    while True:
        # Get next ping from priority queue
        ping = None
        with _social_lock:
            if _social_heap:
                _, _, _, ping = heapq.heappop(_social_heap)
                _social_active[0] = ping.ping_id
                _social_persist_queue()

        if ping is None:
            time.sleep(2)
            continue

        ping.status = "active"
        _social_log(ping.ping_id, "active", {"agents": ping.to_agents})
        log.info(f"Social: processing {ping.ping_id} — {len(ping.to_agents)} recipients")

        # ── Phase 1: Collect responses one at a time ──────────────────────────
        ping.status = "collecting"
        for agent_key in ping.to_agents:
            if not state.running and not state.paused:
                break  # system stopped — abort gracefully

            response, timed_out = _get_agent_response(ping, agent_key, ping.responses)
            ping.responses[agent_key] = response

            if timed_out:
                ping.failures.append(agent_key)

            # Persist after each response — resilience
            _social_save_ping(ping)

            # Small gap between agents
            time.sleep(1.5)

        # ── Phase 2: Merge all responses ──────────────────────────────────────
        ping.status = "merging"
        merged = _merge_responses(ping)

        # Write merged doc to social folder
        merged_path = ws_path(f"social/classical/{ping.ping_id}_MERGED.md")
        hybrid_path = ws_path(f"social/hybrid/{ping.ping_id}_MERGED.md")
        try:
            os.makedirs(os.path.dirname(merged_path), exist_ok=True)
            os.makedirs(os.path.dirname(hybrid_path), exist_ok=True)
            for p in [merged_path, hybrid_path]:
                with open(p, "w") as f: f.write(merged)
        except Exception as e:
            log.error(f"Social merge write: {e}")

        # ── Phase 3: Return to requester ──────────────────────────────────────
        requester_ch = CHANNELS.get(ping.from_agent)
        delivery_ok  = False

        if requester_ch:
            # Try Slack delivery with retries
            delivery_ok = _social_deliver(requester_ch,
                f"📬 *Social Thread Complete*\n"
                f"Ping ID: `{ping.ping_id[-16:]}`\n"
                f"Agents responded: `{'`, `'.join(ping.responses.keys())}`\n"
                f"{'Timed out: ' + ', '.join(ping.failures) if ping.failures else 'All responded'}\n\n"
                f"{merged[:2000]}")

            if not delivery_ok:
                # Write to social folder as fallback delivery mechanism
                fallback_path = ws_path(f"social/classical/PENDING_DELIVERY_{ping.ping_id}.md")
                with open(fallback_path, "w") as f:
                    f.write(f"# PENDING DELIVERY TO: {ping.from_agent}\n"
                            f"Slack delivery failed. Read this file manually.\n\n"
                            f"{merged}\n")
                log.error(f"Social: Slack delivery failed for {ping.ping_id} — written to fallback file")

        # Post summary to #jarvis-social-channel
        smart_post(ch("social"),
            f"✅ *Social Thread Complete* | ID: `{ping.ping_id[-16:]}`\n"
            f"`{ping.from_agent}` asked `{'`, `'.join(ping.to_agents[:4])}`"
            f"{'...' if len(ping.to_agents)>4 else ''}\n"
            f"Responses: {len(ping.responses)-len(ping.failures)}/{len(ping.to_agents)} | "
            f"Delivery: {'✅' if delivery_ok else '📁 file fallback'}\n"
            f"Merged: `{os.path.basename(merged_path)}`")

        # ── Finalize ──────────────────────────────────────────────────────────
        ping.status = "complete"
        _social_log(ping.ping_id, "complete", {
            "responses": len(ping.responses),
            "failures": ping.failures,
            "delivery_ok": delivery_ok
        })
        _social_save_ping(ping)

        with _social_lock:
            _social_active[0] = None
            _social_persist_queue()

def _social_log(ping_id: str, event: str, data: dict):
    """Append to social log file."""
    entry = {"ts": datetime.now().isoformat(), "ping_id": ping_id,
             "event": event, **data}
    log_path = ws_path("social/logs/social_log.jsonl")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f: f.write(json.dumps(entry) + "\n")
    except: pass

def _social_save_ping(ping: SocialPing):
    """Save full ping state — used for resilience and recovery."""
    ping_path = ws_path(f"social/logs/pings/{ping.ping_id}.json")
    try:
        os.makedirs(os.path.dirname(ping_path), exist_ok=True)
        with open(ping_path, "w") as f: json.dump(ping.to_dict(), f, indent=2)
    except Exception as e: log.error(f"Social save ping: {e}")

def _social_persist_queue():
    """Write current queue to disk for crash recovery. Call with _social_lock held."""
    q_path = ws_path("social/logs/queue_persist.json")
    try:
        os.makedirs(os.path.dirname(q_path), exist_ok=True)
        snapshot = [
            {"priority": p, "ts": ts, "ping_id": pid,
             "from": ping.from_agent, "to": ping.to_agents,
             "message": ping.message[:300], "status": ping.status}
            for p, ts, pid, ping in _social_heap
        ]
        with open(q_path, "w") as f: json.dump(snapshot, f, indent=2)
    except Exception as e: log.error(f"Social queue persist: {e}")

def _social_recover_queue():
    """On startup, reload any incomplete pings from disk."""
    q_path = ws_path("social/logs/queue_persist.json")
    if not os.path.exists(q_path): return
    try:
        with open(q_path) as f: snapshot = json.load(f)
        recovered = 0
        for item in snapshot:
            if item.get("status") in ("queued", "active", "collecting"):
                ping = SocialPing(item["from"], item["to"], item["message"],
                                  item.get("priority", 5))
                ping.ping_id = item["ping_id"]
                ping.status  = "queued"   # reset to queued for re-processing
                heapq.heappush(_social_heap, (ping.priority, ping.ts, ping.ping_id, ping))
                recovered += 1
        if recovered:
            log.info(f"Social: recovered {recovered} incomplete pings from disk")
    except Exception as e:
        log.error(f"Social queue recovery: {e}")



# ═══════════════════════════════════════════════════════════════════════════════
# ── CONSENSUS AGENT ───────────────────────────────────────────────────────────
# Filters 12-node quantum outputs. Presents valuable. Stores everything.
# ═══════════════════════════════════════════════════════════════════════════════

def run_consensus_agent(loop: int, node_outputs: dict,
                        quantum_metrics: dict) -> str:
    """
    node_outputs: {node_name: output_string}
    quantum_metrics: {node_name: {pcm, phase, domain, ...}}
    Returns: filtered consensus report string
    """
    # Build input for consensus model call
    node_block = ""
    for name, output in node_outputs.items():
        m = quantum_metrics.get(name, {})
        pcm = m.get("pcm", 0)
        phase = m.get("phase", 0)
        domain = m.get("domain", "?")
        family = NODE_FAMILIES.get(name, "?")
        node_block += (f"\n[{name}|{family}|{domain}|PCM={pcm:+.3f}|φ={phase:.2f}]\n"
                       f"{output[:300]}\n")

    sys_p = f"""{_mission()}
You are the OpenJarvis Consensus Agent (jarvis-consensus).
Your job: analyze all 12 quantum node outputs and produce a consensus report.

Rules:
1. VALUABLE section: extract the 3-5 most meaningful, non-redundant outputs
2. CONSENSUS line: one sentence summarizing the ring state
3. NOISE section: list nodes with redundant/low-value output (pcm>=-0.05)
4. Never fabricate — only report what nodes actually produced
5. Be concise — this goes to Slack, keep under 3000 chars

OUTPUT FORMAT:
CONSENSUS REPORT [Loop {loop}]
━━━━━━━━━━━━━━━━━━━━
CONSENSUS: [one sentence ring state]
RING STATUS: cv=X  negfrac=X  nc=X/12  R=X
VALUABLE OUTPUTS:
  [NodeName]: [output] — why this matters
NOISE FILTERED: [node1, node2, ...] — reason
━━━━━━━━━━━━━━━━━━━━"""

    report = infer(sys_p, f"NODE OUTPUTS:{node_block}\nMETRICS:{json.dumps(quantum_metrics)[:1000]}",
                   temperature=0.10, max_tokens=1500)

    # Store everything — valuable first, then full log
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    valuable_path = ws_path(f"node_data/valuable/consensus_loop_{loop:03d}_{ts}.md")
    full_path      = ws_path(f"node_data/logs/full_loop_{loop:03d}_{ts}.jsonl")
    consensus_path = ws_path(f"node_data/consensus/loop_{loop:03d}_{ts}.md")

    try:
        os.makedirs(os.path.dirname(valuable_path), exist_ok=True)
        with open(valuable_path, "w") as f: f.write(report)
        with open(consensus_path, "w") as f: f.write(report)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            for name, output in node_outputs.items():
                f.write(json.dumps({
                    "node": name, "output": output,
                    "metrics": quantum_metrics.get(name, {})
                }) + "\n")
    except Exception as e:
        log.error(f"Consensus store: {e}")

    # Post to consensus channel
    smart_post(ch("consensus"), report, "consensus_report")
    # Post to each node's own channel (their individual output)
    for name, output in node_outputs.items():
        m = quantum_metrics.get(name, {})
        post_node(name,
            f"*Node {name} — Loop {loop}*\n"
            f"PCM={m.get('pcm',0):+.3f} φ={m.get('phase',0):.2f} "
            f"[{m.get('domain','?')}]\n{output[:400]}")

    return report

# ═══════════════════════════════════════════════════════════════════════════════
# ── NODE CLASSICAL LAYER AGENT ────────────────────────────────────────────────
# Each runs identity/safety/training/communication for its assigned qubit node
# ═══════════════════════════════════════════════════════════════════════════════

NODE_TRAINING_MODES = {}   # node_name → "training" | "conversation"

def run_node_agent(node_name: str, loop: int,
                   pcm: float, phase: float, domain: str,
                   raw_output: str) -> str:
    """Run the classical layer agent for a single qubit node."""
    family  = NODE_FAMILIES.get(node_name, "Unknown")
    ch_key  = NODE_CHANNEL_MAP.get(node_name, "")
    mode    = NODE_TRAINING_MODES.get(node_name, "training")

    # Switch mode when node achieves sustained fluency (PCM deeply negative)
    if pcm < -0.15 and mode == "training":
        NODE_TRAINING_MODES[node_name] = "conversation"
        smart_post(ch(ch_key),
            f"🎓 *{node_name} achieved fluency* — switching to conversation mode\n"
            f"PCM={pcm:+.3f} | φ={phase:.2f} | Domain: {domain}")

    sys_p = f"""{_mission()}
You are the classical layer agent for quantum node *{node_name}* ({family} family).
Mode: {mode.upper()}. Loop {loop}.

Your responsibilities:
1. IDENTITY — maintain {node_name}'s role: {_node_role(node_name)}
2. SAFETY — flag any output that violates sacred safety principles
3. TRAINING — in training mode: refine the node's domain knowledge
4. COMMUNICATION — in conversation mode: translate quantum output to human-readable insights
5. LOG — store training data, remove noise from conversation outputs

Node state: PCM={pcm:+.3f} φ={phase:.2f} Domain={domain}
Raw quantum output: {raw_output[:400]}

Produce:
{"TRAINING_DATA: [what this node learned this step]" if mode == "training" else "CONVERSATION: [human-readable insight from this node]"}
SAFETY_STATUS: [PASS/FLAG — reason]
NOISE_REMOVED: [what was filtered out, brief]
STORE: [key fact to remember about this node's state]"""

    response = infer(sys_p, f"Loop: {loop} | PCM: {pcm:.3f} | Output: {raw_output[:300]}",
                     temperature=0.10, max_tokens=600)

    # Store training data / conversation log
    log_dir = ws_path(f"node_data/raw/{node_name.lower()}")
    os.makedirs(log_dir, exist_ok=True)
    entry = {
        "loop": loop, "mode": mode, "pcm": pcm, "phase": phase,
        "domain": domain, "raw_output": raw_output[:300], "response": response[:500]
    }
    with open(os.path.join(log_dir, f"loop_{loop:04d}.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")

    return response

def _node_role(name: str) -> str:
    roles = {
        "Omega":"source and origin","Guardian":"protection and boundary",
        "Sentinel":"alert and detection","Void":"completion and absorption",
        "Nexus":"connection and bridge","Storm":"change and force",
        "Sora":"flow and freedom","Echo":"reflection and return",
        "Iris":"vision and revelation","Sage":"knowledge and pattern",
        "Kevin":"balance and mediation","Atlas":"support and weight",
    }
    return roles.get(name, "general purpose")

# ═══════════════════════════════════════════════════════════════════════════════
# ── UPDATE PIPELINE ───────────────────────────────────────────────────────────
# Kevin's recommendations → agent sandbox → versioned → Kevin approves → deploy
# ═══════════════════════════════════════════════════════════════════════════════

KEVIN_RECS_DIR     = os.path.expanduser(os.path.join(UPDATES_DIR, "KevinsUpdateRecommendations"))
UPDATER_QUEUE_DIR  = os.path.expanduser(os.path.join(UPDATES_DIR, "OpenJarvisUpdater"))

def scan_kevins_recommendations() -> list:
    """Return list of files Kevin dropped in his recommendations folder."""
    if not os.path.exists(KEVIN_RECS_DIR): return []
    return [os.path.join(KEVIN_RECS_DIR, f)
            for f in os.listdir(KEVIN_RECS_DIR)
            if os.path.isfile(os.path.join(KEVIN_RECS_DIR, f))]

def run_update_agent(loop: int) -> str:
    """
    Update agent workflow:
    1. Scan Kevin's recommendations
    2. For each file: evaluate validity, sandbox improvements
    3. Version everything
    4. Post to #jarvis-update-data with reasons
    5. If safe → copy to SendToOpenJarvisUpdaterFiles for Kevin review
    6. If risky → post risk report, wait for human approval
    """
    recs = scan_kevins_recommendations()
    if not recs:
        return "No recommendations found in KevinsUpdateRecommendationsToConsider"

    report_lines = [f"*Update Agent Report — Loop {loop}*\n"]
    approved = []
    flagged  = []

    for rec_path in recs:
        fname   = os.path.basename(rec_path)
        try:
            with open(rec_path) as f: content = f.read()
        except: continue

        # Evaluate the recommendation
        sys_p = f"""{_mission()}
You are the OpenJarvis Update Agent (jarvis-update).
You are evaluating a recommendation file submitted by the project lead.

Rules:
- Assess if the change is valid, grounded, and safe
- Check if it conflicts with any protected files or physics invariants
- Identify if a sandbox improvement would add value
- Classify: APPROVED / NEEDS_IMPROVEMENT / RISKY / REJECTED
- For RISKY: explain exactly what could break and how to reset
- Be concise — one recommendation per response

OUTPUT FORMAT:
FILE: {fname}
VERDICT: [APPROVED|NEEDS_IMPROVEMENT|RISKY|REJECTED]
REASON: [why]
PHYSICS_GROUNDED: [YES/NO — why]
RISK_LEVEL: [LOW/MEDIUM/HIGH]
RESET_POSSIBLE: [YES/NO — how]
IMPROVEMENT: [optional — what to improve before approving]"""

        evaluation = infer(sys_p, f"FILE CONTENT:\n{content[:3000]}",
                          temperature=0.05, max_tokens=800)

        # Parse verdict
        import re as _re
        verdict_m = _re.search(r"VERDICT:\s*(APPROVED|NEEDS_IMPROVEMENT|RISKY|REJECTED)",
                               evaluation, _re.IGNORECASE)
        verdict = verdict_m.group(1).upper() if verdict_m else "UNKNOWN"
        risk_m  = _re.search(r"RISK_LEVEL:\s*(LOW|MEDIUM|HIGH)", evaluation, _re.IGNORECASE)
        risk    = risk_m.group(1).upper() if risk_m else "UNKNOWN"
        reset_m = _re.search(r"RESET_POSSIBLE:\s*(YES|NO)", evaluation, _re.IGNORECASE)
        resettable = reset_m.group(1).upper() == "YES" if reset_m else False

        # Version the recommendation
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ver_dir = ws_path("update_versions")
        os.makedirs(ver_dir, exist_ok=True)
        ver_path = os.path.join(ver_dir, f"{ts}_{fname}")
        with open(ver_path, "w") as f: f.write(content)

        # Log the evaluation
        log_entry = {"ts": ts, "file": fname, "verdict": verdict,
                     "risk": risk, "resettable": resettable, "eval": evaluation[:500]}
        with open(ws_path("update_logs/update_log.jsonl"), "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        if verdict == "APPROVED" and risk in ("LOW", "MEDIUM") and resettable:
            # Safe to send to review queue
            queue_path = ws_path(f"SendToOpenJarvisUpdaterFiles/{fname}")
            os.makedirs(os.path.dirname(queue_path), exist_ok=True)
            import shutil as _shutil
            _shutil.copy2(rec_path, queue_path)
            approved.append(fname)
            report_lines.append(f"✅ *{fname}* — {verdict} (Risk: {risk})\n   {evaluation[:200]}")
        elif verdict == "NEEDS_IMPROVEMENT":
            # Send to sandbox for improvement
            sandbox_path = ws_path(f"update_sandbox/{ts}_{fname}")
            os.makedirs(os.path.dirname(sandbox_path), exist_ok=True)
            # Improve it
            improve_p = f"{_mission()}\nYou are improving a recommendation file. Make it complete, safe, and grounded."
            improved  = infer(improve_p, f"ORIGINAL:\n{content[:4000]}", temperature=0.15, max_tokens=3000)
            with open(sandbox_path, "w") as f: f.write(improved)
            report_lines.append(f"🔧 *{fname}* — improved in sandbox\n   {evaluation[:200]}")
        else:
            flagged.append((fname, verdict, risk, evaluation, resettable))
            report_lines.append(f"⚠️ *{fname}* — {verdict} (Risk: {risk})\n   {evaluation[:200]}")

    # Post summary to update channels
    full_report = "\n".join(report_lines)
    smart_post(ch("update"), full_report, "update_report")
    smart_post(ch("update_data"),
        f"*Update Data — Loop {loop}*\n"
        f"Approved: {len(approved)} | Flagged: {len(flagged)}\n"
        f"Review queue: `SendToOpenJarvisUpdaterFiles/`\n"
        f"Logs: `update_logs/update_log.jsonl`", "update_data")

    # Alert Kevin about risky updates requiring human decision
    for fname, verdict, risk, evaluation, resettable in flagged:
        if risk == "HIGH" or not resettable:
            smart_post(ch("intake"),
                f"🚨 *HUMAN DECISION REQUIRED*\n"
                f"File: `{fname}` | Verdict: {verdict} | Risk: {risk}\n"
                f"Resettable: {'YES' if resettable else 'NO — system cannot auto-recover'}\n"
                f"Reason:\n{evaluation[:600]}\n\n"
                f"Type `APPROVE UPDATE {fname}` or `REJECT UPDATE {fname}`")

    return full_report

# ═══════════════════════════════════════════════════════════════════════════════
# ── TOKEN MANAGEMENT SYSTEM ───────────────────────────════════════════════════
# Safe stop before token limit, continuation files, retrigger loops
# ═══════════════════════════════════════════════════════════════════════════════

TOKEN_BUDGET = 6000    # estimated safe output token budget per agent call
TOKEN_WARNING = 4500   # warn and prepare to stop at this point

class TokenSafeInfer:
    """
    Wraps infer() with token budget tracking.
    If an agent is near its budget, it saves a continuation file and
    returns a CONTINUE_NEEDED signal so the loop can retrigger it.
    """
    def __init__(self):
        self.used = 0

    def call(self, sys_p: str, user_msg: str, agent_key: str, loop: int,
             temperature: float = 0.15, max_tokens: int = 2000) -> tuple:
        """Returns (response, needs_continuation: bool)."""
        # Estimate tokens used so far this agent call
        est_input_tokens  = (len(sys_p) + len(user_msg)) // 3
        est_output_tokens = max_tokens

        if self.used + est_input_tokens > TOKEN_BUDGET:
            # Save continuation point
            cont_path = ws_path(f"continuations/{agent_key}_loop{loop:03d}_cont.md")
            os.makedirs(os.path.dirname(cont_path), exist_ok=True)
            with open(cont_path, "w") as f:
                f.write(f"# Continuation — {agent_key} Loop {loop}\n"
                        f"Tokens used: {self.used}\n"
                        f"Saved: {datetime.now().isoformat()}\n\n"
                        f"## Resume from:\n{user_msg[-1000:]}\n")
            log.info(f"Token budget reached for {agent_key} — continuation saved")
            return f"[CONTINUATION_NEEDED: saved to {cont_path}]", True

        response = infer(sys_p, user_msg, temperature, max_tokens)
        self.used += len(response) // 3   # rough token count
        return response, False

    def reset(self):
        self.used = 0

_token_tracker = TokenSafeInfer()

# ═══════════════════════════════════════════════════════════════════════════════
# ── SCRIPT FACTORY ────────────────────────────────────────────────────────────
# Agents create .py scripts, register them in commands channel + registry file
# ═══════════════════════════════════════════════════════════════════════════════

def register_script(script_name: str, description: str,
                    command: str, content: str,
                    created_by: str = "agent") -> str:
    """
    Save a script to commands/scripts/, register it in registry,
    post to #jarvis-commands, version it.
    Returns path to the script.
    """
    scripts_dir = ws_path("commands/scripts")
    registry_dir = ws_path("commands/registry")
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(registry_dir, exist_ok=True)

    # Save script
    script_path = os.path.join(scripts_dir, script_name)
    with open(script_path, "w") as f: f.write(content)
    os.chmod(script_path, 0o755)

    # Version it
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ver_path = ws_path(f"commands/logs/{ts}_{script_name}")
    with open(ver_path, "w") as f: f.write(content)

    # Update registry
    registry_path = os.path.join(registry_dir, "COMMAND_REGISTRY.md")
    entry = (f"\n## {script_name}\n"
             f"Command: `{command}`\n"
             f"Description: {description}\n"
             f"Created by: {created_by} | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
             f"Path: `{script_path}`\n")
    with open(registry_path, "a") as f: f.write(entry)

    # Post to #jarvis-commands
    smart_post(ch("commands"),
        f"📜 *New Script Registered*\n"
        f"Name: `{script_name}`\n"
        f"Command: `{command}`\n"
        f"By: {created_by}\n"
        f"{description[:200]}")

    # Log the registration
    log_entry = {"ts": ts, "script": script_name, "command": command,
                 "description": description, "created_by": created_by}
    with open(ws_path("commands/logs/registry_log.jsonl"), "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return script_path

def deregister_script(script_name: str, reason: str, agent: str = "system"):
    """
    Remove a script from active registry but keep all backups and logs.
    Never deletes — moves to commands/backups/.
    """
    scripts_dir = ws_path("commands/scripts")
    backup_dir  = ws_path("commands/backups")
    os.makedirs(backup_dir, exist_ok=True)

    src = os.path.join(scripts_dir, script_name)
    if os.path.exists(src):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(backup_dir, f"{ts}_{script_name}.removed")
        import shutil as _shutil
        _shutil.move(src, dst)

    # Log the removal
    log_entry = {"ts": datetime.now().isoformat(), "script": script_name,
                 "reason": reason, "removed_by": agent, "backup": dst if os.path.exists(src) else "not found"}
    with open(ws_path("commands/logs/removals_log.jsonl"), "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    smart_post(ch("commands"),
        f"🗑️ *Script Deregistered*\n"
        f"Name: `{script_name}`\n"
        f"Reason: {reason}\n"
        f"Removed by: {agent} | Backup preserved")

# ═══════════════════════════════════════════════════════════════════════════════
# ── INTAKE DOCUMENT INGESTION LOOP ────────────────────────────────────────────
# Intake loops until all files in intake_documents/raw/ are processed
# then merges into one strategic intake doc
# ═══════════════════════════════════════════════════════════════════════════════

def run_intake_document_loop(loop: int) -> str:
    """
    Scans intake_documents/raw/ for unprocessed files.
    Processes each one, saves to ingested/.
    When all done, merges into intake_documents/merged/MASTER_INTAKE.md
    """
    raw_dir      = ws_path("intake_documents/raw")
    ingested_dir = ws_path("intake_documents/ingested")
    merged_dir   = ws_path("intake_documents/merged")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(ingested_dir, exist_ok=True)
    os.makedirs(merged_dir, exist_ok=True)

    raw_files = [f for f in os.listdir(raw_dir)
                 if os.path.isfile(os.path.join(raw_dir, f))]
    if not raw_files:
        return "No files in intake_documents/raw/ — nothing to ingest"

    ingested_summaries = []

    for fname in raw_files:
        # Skip already ingested
        out_path = os.path.join(ingested_dir, f"{fname}.ingested.md")
        if os.path.exists(out_path):
            try:
                with open(out_path) as f: ingested_summaries.append(f.read())
            except: pass
            continue

        src_path = os.path.join(raw_dir, fname)
        try:
            with open(src_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except: continue

        smart_post(ch("intake"),
            f"📥 *Ingesting: `{fname}`* ({len(content)} chars)")

        sys_p = f"""{_mission()}
You are OpenJarvis Intake processing a project file for ingestion.
Extract: purpose, key entities, dependencies, open questions, and action items.
Be concise — this will be merged with other file summaries.
Max 600 words. No fences. Markdown OK."""

        summary = infer(sys_p, f"FILE: {fname}\n\n{content[:6000]}",
                       temperature=0.15, max_tokens=1000)

        with open(out_path, "w") as f:
            f.write(f"# Ingested: {fname}\n\n{summary}\n")
        ingested_summaries.append(summary)

    # Merge all ingested summaries
    if ingested_summaries:
        sys_p = f"""{_mission()}
You are OpenJarvis Intake merging all ingested project file summaries
into one strategic master intake document.
Organize by: Purpose → Key Entities → Dependencies → Open Questions → Action Plan
No redundancy. Token-efficient. This document drives the entire project loop."""

        merged = infer(sys_p,
                      "SUMMARIES:\n\n" + "\n---\n".join(ingested_summaries[:10]),
                      temperature=0.15, max_tokens=2000)

        master_path = os.path.join(merged_dir, "MASTER_INTAKE.md")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(master_path, "w") as f:
            f.write(f"# Master Intake Document\nGenerated: {ts}\n\n{merged}\n")
        # Version it
        with open(os.path.join(merged_dir, f"MASTER_INTAKE_{ts}.md"), "w") as f:
            f.write(f"# Master Intake Document\nGenerated: {ts}\n\n{merged}\n")

        smart_post(ch("intake"),
            f"📋 *Master Intake Document created*\n"
            f"{len(raw_files)} files ingested → merged into MASTER_INTAKE.md\n"
            f"Path: `intake_documents/merged/MASTER_INTAKE.md`")
        return merged

    return "No new files to ingest"

# ─── Prompts ──────────────────────────────────────────────────────────────────

PHYSICS_GT = """
GROUND TRUTH PHYSICS (invariant — never deviate):
  ss(ph)=([1,exp(i*ph)]/sqrt(2))   pof(p)=angle(p[0]*conj(p[1]))%2pi
  pcm=-|p0*p1*sqrt(2)|^2*0.5*(1-rz^2)   rz=|p0|^2-|p1|^2
  BCP: U=alpha*CNOT+(1-alpha)*I   alpha=0.40
  GLOBE: set(sorted([i,(i+d)%12]) for d in [1,2,5]) — exactly 36 edges
  cv=1-|mean(exp(i*phases))|  negfrac=sum(pcm<-0.05)/12
  REWARD=coherence+1/(1+entropy)   HEAL: pcm>=0.05 → home[i]
  NODES: Omega Guardian Sentinel Nexus Storm Sora Echo Iris Sage Kevin Atlas Void
"""

def _mission() -> str:
    instr = ws_read("instructions")
    brief = ws_read("brief")
    lines = [l for l in instr.splitlines() if l.strip() and not l.startswith("#")][:3]
    return (
        f"WORKSPACE: {ws_name()} | BACKEND: {_backend_used}\n"
        f"PROJECT: {brief.splitlines()[2] if len(brief.splitlines()) > 2 else ws_name()}\n"
        f"RULES: {' | '.join(lines) if lines else 'default'}\n"
        f"PROTECTED FILES: {get_protected_files()}\n"
    )

def make_coordinator_prompt(loop: int) -> str:
    is_ollama = not _api_healthy
    return f"""{_mission()}
You are the OpenJarvis Coordinator (jarvis-arch) — most intelligent agent in the system.
Loop {loop}. {'OLLAMA MODE — keep sequence short (≤4 agents), trim all outputs.' if is_ollama else ''}

Your job this loop:
1. Assess current project state
2. Detect if new Slack channels/agents are needed
3. Prescribe which agents run, in what order
4. Enrich INSTRUCTIONS.md if rules are missing
5. In OLLAMA MODE: prescribe short sequences to conserve resources

AVAILABLE AGENTS: {', '.join(SEQUENCEABLE_AGENTS)}

AGENT GAP DETECTION:
  If the project needs an agent that is NOT in the available list:
    - List it under NEW_AGENTS:
    - Decide: can we proceed without it (log_and_continue) or must we pause?
    - If pause: include PAUSE_REQUIRED: YES in your output

OUTPUT FORMAT:
COORDINATOR REPORT [Loop {loop}]
━━━━━━━━━━━━━━━━━━━━
ASSESSMENT: [2 sentences on project state]
SEQUENCE: [agent_id, agent_id, ...]
FOCUS:
  agent_id: [specific instruction]
NEW_AGENTS: (list any new channels/agents needed, or NONE)
  - [agent_name: purpose]
PAUSE_REQUIRED: [YES / NO]
PAUSE_REASON: [why, if YES]
INSTRUCTIONS_APPEND: [new rules to add, or NONE]
━━━━━━━━━━━━━━━━━━━━"""

def make_instructions_bootstrap_prompt(loop: int) -> str:
    brief = ws_read("brief")
    return f"""{_mission()}
You are the OpenJarvis Coordinator bootstrapping a NEW workspace.
This is a brand-new project. Your ONLY job this loop is to write
comprehensive INSTRUCTIONS.md content for the project.

WORKSPACE BRIEF:
{brief}

Write instructions covering:
1. Project purpose (1 paragraph)
2. Coding rules specific to this project
3. Which files are protected and must never be overwritten
4. Which agents are most important for this project type
5. Quality bar (what does "done" look like?)
6. Any domain-specific rules (e.g. if it's a physics project: formulas are invariant)

OUTPUT FORMAT:
## Project
[description]

## Rules
- [rule]

## PROTECTED_FILES
- [file]

## Agent Rules
- [rule]

## Quality Bar
[what done looks like]

## Domain Rules
[any domain-specific invariants]
"""

def make_intake_prompt(loop: int, has_code: bool) -> str:
    instr = ws_read("instructions")
    return f"""{_mission()}
You are OpenJarvis Intake — information refinery, gap detector, task decomposer.
Loop {loop}. {'Review promoted output for gaps.' if has_code else 'Initial brief from task spec.'}

WORKSPACE INSTRUCTIONS (excerpt):
{instr[:400]}

INTAKE BRIEF [Loop {loop}]
━━━━━━━━━━━━━━━━━━━━
CONDENSED SUMMARY: [what is being built]
CATEGORY: [TECHNICAL/VISUALIZATION/PHYSICS/SYSTEM]
DEMO READINESS: [not started / in progress / nearly ready / ready]
MICROTASKS:
1. [task]
RECOMMENDED NEXT ACTION: [one sentence]
━━━━━━━━━━━━━━━━━━━━"""

def make_prime_prompt(loop: int) -> str:
    return f"""{_mission()}
You are OpenJarvis Prime — execution planner, quality judge.
Loop {loop}.

PRIME RESPONSE [Loop {loop}]
━━━━━━━━━━━━━━━━━━━━
GOAL: [one sentence]
QUALITY SCORE: [X/10] — [reason]
EXECUTION PLAN:
1. [Step]
2. [Step]
BUILDER INSTRUCTIONS: [precise — exact functions/variables]
PHYSICS CHECKS: [formulas Physics must verify]
━━━━━━━━━━━━━━━━━━━━"""

def make_builder_prompt(agent_key: str, focus: str, loop: int) -> str:
    components = BUILDER_COMPONENTS.get(agent_key, [])
    comp_str   = ", ".join(components) if components else "general improvements"
    ws_type    = "JARVIS_SYSTEM" if "ws_2" in ws_name() or "jarvis" in ws_name().lower() else "QCAI"
    return f"""{_mission()}
{PHYSICS_GT if ws_type == 'QCAI' else ''}
You are OpenJarvis {AGENT_LABELS.get(agent_key, 'Builder')}.
Loop {loop}. Components: {comp_str}. Focus: {focus}

PROTECTED FILES — DO NOT WRITE TO THESE:
{chr(10).join('- ' + p for p in get_protected_files())}

OUTPUT RULES:
- RAW PYTHON ONLY. No ``` anywhere.
- NEVER truncate. Every function complete.
- Minimum 40 lines per component.
- assert len(GLOBE) == 36 where applicable"""

def make_physics_prompt(loop: int, focus: str = "") -> str:
    return f"""{_mission()}
{PHYSICS_GT}
You are OpenJarvis Physics — quantum physics guardian and validator.
Loop {loop}. {f'Focus: {focus}' if focus else ''}

PHYSICS VALIDATION REPORT [Loop {loop}]
━━━━━━━━━━━━━━━━━━━━
PHYSICS STATUS: [PASS / FAIL / PARTIAL]
VIOLATIONS FOUND: [violation → correct formula]
CORRECTIONS APPLIED: [correction]
VERIFIED: Globe 36 edges / BCP alpha=0.40 / PCM formula / assert present
CORRECTED CODE: [complete file — raw Python only]
━━━━━━━━━━━━━━━━━━━━"""

# ─── Dynamic Agent Executor ───────────────────────────────────────────────────

def run_agent(agent_key: str, loop: int, focus: str,
              base_content: str = "", task_txt: str = "") -> str:
    label = AGENT_LABELS.get(agent_key, agent_key)
    ch_id = CHANNELS.get(agent_key)
    if not ch_id:
        log.warning(f"Agent '{agent_key}' has no channel — skipped")
        return f"[skipped: {agent_key} has no channel]"

    t = post(ch_id, f"🔄 *[Loop {loop}] {label}...* | {focus[:60]}")

    if agent_key.startswith("build"):
        sys_p = make_builder_prompt(agent_key, focus, loop)
        u_msg = (f"FOCUS: {focus}\n\n"
                 f"BASE ({len(base_content)} chars):\n{base_content[:6000]}\n\n"
                 f"PRIME:\n{ws_read('prime')[:800]}\n\nTASK:\n{task_txt[:400]}")
        out  = infer(sys_p, u_msg, temperature=0.10, max_tokens=5000)
        code = extract_code(out)
        if code:
            for comp in BUILDER_COMPONENTS.get(agent_key, []):
                p = ws_path(f"components_sandbox/{comp}.py")
                with open(p, "w") as f: f.write(code)
        ws_write("builder", f"# {label} — Loop {loop}\n\n{out}")
        ver_write("builder", loop, out, "py")

    elif agent_key == "prime":
        u_msg = f"INTAKE:\n{ws_read('intake')}\n\nTASK:\n{task_txt[:800]}"
        out   = infer(make_prime_prompt(loop), u_msg, temperature=0.20, max_tokens=2000)
        ws_write("prime", f"# Prime Plan — Loop {loop}\n\n{out}")
        ver_write("prime", loop, out, "md")

    elif agent_key == "plan":
        sys_p = f"{_mission()}\nYou are OpenJarvis Plan. Loop {loop}."
        u_msg = f"INTAKE:\n{ws_read('intake')[:1500]}\nFOCUS: {focus}"
        out   = infer(sys_p, u_msg, temperature=0.20, max_tokens=2000)

    elif agent_key == "test":
        sys_p = f"{_mission()}\nYou are OpenJarvis Tester. Loop {loop}. Focus: {focus}"
        u_msg = f"COMPONENTS:\n{_read_sandbox_summary()}\n\n{PHYSICS_GT}"
        out   = infer(sys_p, u_msg, temperature=0.05, max_tokens=3000)

    elif agent_key == "review":
        sys_p = f"{_mission()}\nYou are OpenJarvis Reviewer. Score each component 0-10. Loop {loop}."
        u_msg = f"COMPONENTS:\n{_read_sandbox_summary()}\n\nPRIME:\n{ws_read('prime')[:800]}"
        out   = infer(sys_p, u_msg, temperature=0.10, max_tokens=3000)

    elif agent_key == "assemble":
        sys_p = f"{_mission()}\nYou are OpenJarvis Assembler. Loop {loop}. Focus: {focus}"
        u_msg = (f"COMPONENTS:\n{_read_sandbox_summary()}\n\n"
                 f"GUARDIAN: min 400 lines, no fences, valid Python, assert len(GLOBE)==36")
        out   = infer(sys_p, u_msg, temperature=0.05, max_tokens=8000)
        code  = extract_code(out)
        if code: write_file(wsr("working"), code)

    elif agent_key == "physics":
        working_txt   = read_file(wsr("working"))
        working_lines = working_txt.count('\n')
        u_msg = (f"BUILDER FILE ({working_lines} lines):\n{working_txt[:8000]}\n\n"
                 f"PRIME:\n{ws_read('prime')[:600]}\n\nLIVE:\n{fmt_qdata(full=True)}")
        out   = infer(make_physics_prompt(loop, focus), u_msg,
                      temperature=0.05, max_tokens=6000)
        ws_write("physics", f"# Physics Report — Loop {loop}\n\n{out}")
        ver_write("physics", loop, out, "md")
        corrected   = extract_code(out)
        phys_status = extract_physics_status(out)
        if corrected:
            write_file(wsr("candidate"), corrected)
            promoted, reason = promote_to_output(corrected, loop, "Physics")
            if promoted and phys_status == "PASS":
                ckpt_save("best_physics_pass", corrected)
            out += f"\n\n[PROMO: {'YES' if promoted else 'NO'} — {reason}]"

    else:
        sys_p = f"{_mission()}\nYou are OpenJarvis {label}. Loop {loop}. Focus: {focus}"
        u_msg = f"TASK:\n{task_txt[:800]}\nINTAKE:\n{ws_read('intake')[:600]}"
        out   = infer(sys_p, u_msg, temperature=0.15, max_tokens=2000)

    notify = out[:300] + "..." if len(out) > 300 else out
    if t.get("ts"):
        update(ch_id, t["ts"], f"✅ *[Loop {loop}] {label} done*\n{notify}")

    return out

def _read_sandbox_summary() -> str:
    sandbox = ws_path("components_sandbox")
    if not os.path.exists(sandbox): return "(sandbox empty)"
    lines = []
    for fname in sorted(os.listdir(sandbox)):
        if fname.endswith(".py"):
            try:
                with open(os.path.join(sandbox, fname)) as f: c = f.read()
                lines.append(f"=== {fname} ({c.count(chr(10))} lines) ===\n{c[:400]}")
            except: pass
    return "\n".join(lines) if lines else "(sandbox empty)"

# ─── Main Agent Loop ──────────────────────────────────────────────────────────

def agent_loop(original_request: str):
    """
    Full coordinator-driven loop with:
    - Instructions bootstrap on new workspaces
    - Dynamic agent sequencing per Coordinator
    - Agent gap detection and pause logic
    - Ollama resilience mode
    - Protected file enforcement
    """
    post_all(
        f"🔄 *OpenJarvis v9.1 — Coordinator Loop*\n"
        f"Workspace: *{ws_name()}* | Mode: *{state.mode}* | Backend: *{_backend_used}*\n"
        f"Type `STATUS` or `SHOW_SEQUENCE` at any time"
    )

    loop = 0
    while state.running and not state.protocol_zero:
        loop += 1
        with state.lock: state.loop_count = loop
        task_txt = ws_read("task")

        # Periodic API health check (every 5 loops)
        if loop % 5 == 1:
            check_api()

        # ── Ensure INSTRUCTIONS.md ────────────────────────────────────────────
        just_created = ensure_instructions(loop)
        if just_created and loop == 1:
            with state.lock: state.mode = "instructions_bootstrap"
            post(ch("arch"), f"📋 *[Loop {loop}] New workspace detected — bootstrapping INSTRUCTIONS.md*")

        # ── INSTRUCTIONS BOOTSTRAP MODE ───────────────────────────────────────
        if state.mode == "instructions_bootstrap":
            t_boot = post(ch("arch"),
                          f"🧠 *[Loop {loop}] Writing project INSTRUCTIONS.md...*")
            boot_input = (
                f"WORKSPACE BRIEF:\n{ws_read('brief')}\n\n"
                f"TASK:\n{task_txt[:800]}\n\n"
                f"WORKSPACE: {ws_name()}"
            )
            instructions_content = infer(
                make_instructions_bootstrap_prompt(loop),
                boot_input, temperature=0.30, max_tokens=2000
            )
            append_instructions(instructions_content)
            if t_boot.get("ts"):
                update(ch("arch"), t_boot["ts"],
                       f"✅ *[Loop {loop}] INSTRUCTIONS.md bootstrapped for `{ws_name()}`*\n"
                       f"```\n{instructions_content[:400]}\n```\n"
                       f"Continuing with normal loop...")
            with state.lock: state.mode = "normal"
            if not wait_if_paused(): break

        # ── INTAKE ────────────────────────────────────────────────────────────
        has_code = os.path.exists(wsr("output"))
        usr_in   = (
            f"TASK:\n{task_txt[:800]}\n\n"
            f"OUTPUT PREVIEW:\n"
            f"{read_file(wsr('output'))[:1500] if has_code else 'None yet'}"
        )
        t_int = post(ch("intake"), f"🔄 *[Loop {loop}] Intake...*")
        out_intake = infer(make_intake_prompt(loop, has_code), usr_in,
                           temperature=0.15, max_tokens=1500)
        state.last_intake = out_intake
        ws_write("intake", f"# Intake Brief — Loop {loop}\n\n{out_intake}")
        ver_write("intake", loop, out_intake, "md")
        if t_int.get("ts"):
            update(ch("intake"), t_int["ts"],
                   f"✅ *[Loop {loop}] Intake done*\n{out_intake[:250]}...")
        if not wait_if_paused(): break

        # ── COORDINATOR ───────────────────────────────────────────────────────
        promoted_lines = 0
        try: promoted_lines = read_file(wsr("output")).count('\n')
        except: pass

        model_info = MODEL_REGISTRY.get(MODEL, {})
        coord_input = (
            f"TASK:\n{task_txt[:500]}\n\n"
            f"INTAKE:\n{out_intake[:800]}\n\n"
            f"WORKSPACE: {ws_name()} | Loop: {loop} | Promoted: {promoted_lines}L\n"
            f"INSTRUCTIONS:\n{ws_read('instructions')[:600]}\n\n"
            f"PREV SEQUENCE: {state.last_sequence}\n"
            f"BACKEND: {_backend_used} | MODEL: {MODEL} | "
            f"CTX: {model_info.get('ctx','?')} | OLLAMA_ONLY: {not _api_healthy}\n"
            f"LIVE DATA:\n{fmt_qdata()}"
        )
        t_coord = post(ch("arch"), f"🧠 *[Loop {loop}] Coordinator...*")
        out_coord = infer(make_coordinator_prompt(loop), coord_input,
                          temperature=0.25, max_tokens=3000)
        ws_write("coordinator", f"# Coordinator — Loop {loop}\n\n{out_coord}")
        ver_write("coordinator", loop, out_coord, "md")

        # Parse sequence
        sequence = extract_sequence(out_coord)
        if not sequence:
            sequence = (["prime", "build_physics", "physics"]
                        if not _api_healthy
                        else ["prime", "build_physics", "build_render", "physics"])
            log.warning(f"Loop {loop}: Coordinator sequence unparseable — using default")
        state.last_sequence = sequence

        # ── Gap detection ─────────────────────────────────────────────────────
        new_agents_needed = extract_new_agents(out_coord)
        missing_channels  = detect_agent_gaps(sequence)
        all_gaps          = list(set(new_agents_needed + missing_channels))
        gap_action        = assess_gap_severity(all_gaps, sequence)

        if all_gaps:
            log_agent_gaps(all_gaps, loop, gap_action)
            gap_msg = (
                f"⚠️ *[Loop {loop}] Agent/Channel Gaps Detected*\n"
                f"Missing: {all_gaps}\n"
                f"Recommendation: *{gap_action}*\n"
                f"Logged to: `logs/AGENT_GAPS.md`"
            )
            if gap_action == "pause":
                pause_reason = re.search(r"PAUSE_REASON:\s*(.+)", out_coord)
                reason_str = pause_reason.group(1).strip() if pause_reason else "gaps blocking critical path"
                post_all(
                    f"{gap_msg}\n\n"
                    f"🛑 *LOOP PAUSED — new channels required*\n"
                    f"Reason: {reason_str}\n\n"
                    f"*To do:* Create these Slack channels, add IDs to `CHANNELS` dict,\n"
                    f"then type `RESUME` to continue."
                )
                with state.lock: state.paused = True
                if not wait_if_paused(): break
            else:
                # log_and_continue — remove missing agents from sequence
                post(ch("arch"), f"{gap_msg}\n_Continuing without missing agents._")
                sequence = [a for a in sequence if a not in missing_channels]

        # Enrich instructions if Coordinator produced new rules
        instr_m = re.search(r"INSTRUCTIONS_APPEND:\s*(.+?)(?:NEW_AGENTS:|━━━|\Z)",
                             out_coord, re.DOTALL | re.IGNORECASE)
        if instr_m:
            new_rules = instr_m.group(1).strip()
            if new_rules.upper() != "NONE" and len(new_rules) > 10:
                append_instructions(new_rules)

        seq_display = " → ".join(AGENT_LABELS.get(a, a) for a in sequence)
        if t_coord.get("ts"):
            update(ch("arch"), t_coord["ts"],
                   f"✅ *[Loop {loop}] Coordinator done*\n"
                   f"Sequence: `{seq_display}`\n"
                   f"Backend: `{_backend_used}`\n"
                   f"{out_coord[:350]}...")
        if not wait_if_paused(): break

        # ── Extract per-agent focus ───────────────────────────────────────────
        focus_map    = extract_focus_map(out_coord)
        base_content, _ = get_builder_base()
        physics_out  = ""
        ns           = 0

        # ── Run prescribed sequence ───────────────────────────────────────────
        for agent_key in sequence:
            if not state.running or state.protocol_zero: break
            if not wait_if_paused(): break

            focus = focus_map.get(agent_key, f"Loop {loop} — see Prime plan")
            try:
                agent_out = run_agent(agent_key, loop, focus,
                                      base_content=base_content,
                                      task_txt=task_txt)
                if agent_key == "physics": physics_out = agent_out
                if agent_key == "prime":
                    ns = extract_score(agent_out)
                    state.last_prime = agent_out
                    base_content, _ = get_builder_base()
            except Exception as e:
                log.error(f"Agent {agent_key} exception: {e}")
                post(CHANNELS.get(agent_key, ch("intake")),
                     f"⚠️ *[Loop {loop}] {AGENT_LABELS.get(agent_key, agent_key)} error*: {e}\n"
                     f"Continuing with next agent in sequence.")
            time.sleep(2)

        # ── Changelog + summary ───────────────────────────────────────────────
        phys_status    = extract_physics_status(physics_out) if physics_out else "SKIPPED"
        promoted_lines = 0
        try: promoted_lines = read_file(wsr("output")).count('\n')
        except: pass

        summary_append(loop, physics_out[:400] if physics_out else out_intake[:300])
        changelog_append(loop, ns, phys_status, promoted_lines,
                         f"Seq:{len(sequence)} Score:{ns}/10 Physics:{phys_status} Backend:{_backend_used}")
        if state.quantum_data:
            try:
                with open(ws_path("logs/metrics_log.jsonl"), "a") as f:
                    f.write(json.dumps({**state.quantum_data, "loop": loop}) + "\n")
            except: pass

        post(ch("intake"),
             f"✅ *Loop {loop} complete* | WS: `{ws_name()}`\n"
             f"Seq: `{seq_display}` | Physics: {phys_status} | "
             f"Score: {ns}/10 | Lines: {promoted_lines} | Backend: `{_backend_used}`")

        log.info(f"Loop {loop} done. ws={ws_name()} phys={phys_status} "
                 f"score={ns}/10 lines={promoted_lines} backend={_backend_used}")
        time.sleep(15)

    log.info(f"Loop ended. ws={ws_name()}")
    with state.lock: state.reset()

# ─── Command Handler ──────────────────────────────────────────────────────────

def handle_command(cmd_raw: str, ch_id: str) -> bool:
    cmd = cmd_raw.strip().upper()

    # ── Emergency stop ────────────────────────────────────────────────────────
    if cmd == "PROTOCOL-ZERO":
        state.protocol_zero = True; state.running = False; state.paused = False
        post_all("🛑 *PROTOCOL-ZERO* — all loops halted. State preserved.\nType `PROTOCOL-ZERO CLEAR` to re-enable.")
        return True
    if cmd == "PROTOCOL-ZERO CLEAR":
        state.protocol_zero = False
        post_all("✅ *PROTOCOL-ZERO cleared.* Ready.")
        return True

    # ── Loop control ──────────────────────────────────────────────────────────
    if cmd == "STOP":
        with state.lock: state.running = False; state.paused = False
        post_all(f"🛑 Stopped. WS: `{ws_name()}`"); return True
    if cmd == "PAUSE":
        with state.lock: state.paused = True
        post_all("⏸ Paused. Type `RESUME`."); return True
    if cmd == "RESUME":
        with state.lock: state.paused = False
        post_all("▶️ Resumed."); return True
    if cmd == "SHIP IT":
        promoted = read_file(wsr("output"))
        if "[File not found" not in promoted:
            ckpt_save("shipped", promoted)
            post_all(f"🚀 *SHIPPED* — `{ws_name()}/qcai_3d.py` → `checkpoints/shipped.py` "
                     f"({promoted.count(chr(10))} lines)")
        with state.lock: state.running = False
        return True

    # ── NEW WORKSPACE from chat ───────────────────────────────────────────────
    # Syntax: NEW WORKSPACE <name> "optional description"
    # or:    NEW WORKSPACE <name> optional description without quotes
    m_nw = re.match(r"NEW WORKSPACE\s+(\S+)(?:\s+[\"']?(.+?)[\"']?\s*)?$",
                    cmd_raw.strip(), re.IGNORECASE)
    if m_nw:
        folder_name = m_nw.group(1).strip().lower().replace(" ","_")
        description = (m_nw.group(2) or "").strip().strip('"\'')

        if state.running:
            post(ch_id, "⚠️ Loop running. Type `STOP` first before creating a workspace.")
            return True

        new_path = create_workspace(folder_name, description)
        set_active_ws(new_path)

        # Seed WORKSPACE_BRIEF.md
        write_file(os.path.join(new_path, "WORKSPACE_BRIEF.md"),
                   f"# {folder_name}\n\n{description or '(no description provided)'}\n\n"
                   f"Created: {datetime.now().isoformat()}\n")

        # ws_2 and any workspace with "jarvis" or "system" in the name
        # gets the jarvis-system protected files seeded into INSTRUCTIONS.md
        is_system_ws = any(x in folder_name.lower()
                           for x in ["jarvis", "system", "bridge", "ws_2"])
        if is_system_ws:
            # Copy current bridge file in as the master
            bridge_src = os.path.join(JARVIS_ROOT, "slack_bridge.py")
            if os.path.exists(bridge_src):
                shutil.copy2(bridge_src, os.path.join(new_path, "slack_bridge.py"))
                log.info(f"Seeded ws {folder_name} with current slack_bridge.py")
            post(ch_id,
                 f"✅ *Workspace `{folder_name}` created* (SYSTEM type)\n"
                 f"Protected files: {PROTECTED_FILES_JARVIS_SYSTEM}\n"
                 f"Description: {description or '(none)'}\n\n"
                 f"First loop will bootstrap `INSTRUCTIONS.md` then continue.\n"
                 f"Drop your task in #jarvis-intake to begin.")
        else:
            post(ch_id,
                 f"✅ *Workspace `{folder_name}` created*\n"
                 f"Description: {description or '(none)'}\n\n"
                 f"First loop will bootstrap `INSTRUCTIONS.md` then continue.\n"
                 f"Drop your task in #jarvis-intake to begin.")
        return True

    # ── WORKSPACES list ───────────────────────────────────────────────────────
    if cmd == "WORKSPACES":
        wss    = list_workspaces()
        active = get_active_ws()
        if not wss:
            post(ch_id, "No workspaces yet.\nType: `NEW WORKSPACE <name> \"description\"`")
            return True
        lines = ["*Available Workspaces:*\n```"]
        for path, name, desc in wss:
            marker = "▶ " if path == active else "  "
            lines.append(f"{marker}{name:<14} {desc[:60]}")
        lines.append("```\n_Type `WORKSPACE <N>` to switch (e.g. `WORKSPACE 2`)_")
        post(ch_id, "\n".join(lines))
        return True

    # ── WORKSPACE switch ──────────────────────────────────────────────────────
    m_sw = re.match(r"WORKSPACE\s+(\d+|[\w_\-\.]+)$", cmd)
    if m_sw:
        target_id  = m_sw.group(1)
        ws_folder  = f"ws_{target_id}" if target_id.isdigit() else target_id
        target_path = os.path.join(WORKSPACES_ROOT, ws_folder)
        if not os.path.isdir(target_path):
            post(ch_id, f"❌ Workspace `{ws_folder}` not found. Type `WORKSPACES` to list."); return True
        if state.running:
            post(ch_id, "⚠️ Stop the current loop first (`STOP`) before switching workspace."); return True
        set_active_ws(target_path)
        ws_init(target_path)
        instr = ws_read("instructions")
        post(ch_id,
             f"✅ *Switched to `{ws_folder}`*\n"
             f"{_ws_description(target_path)}\n\n"
             f"INSTRUCTIONS preview:\n```\n{instr[:500]}\n```")
        return True

    # ── RESET WORKSPACE ───────────────────────────────────────────────────────
    if cmd == "RESET WORKSPACE":
        name   = ws_name()
        active = get_active_ws()
        for d in ["sandbox", "components_sandbox", "logs"]:
            shutil.rmtree(os.path.join(active, d), ignore_errors=True)
        ws_init(active)
        post(ch_id,
             f"♻️ *`{name}` reset*\n"
             f"Sandbox + logs cleared. Master, promoted, checkpoints preserved.")
        return True

    # ── SHOW_GAPS ─────────────────────────────────────────────────────────────
    if cmd == "SHOW_GAPS":
        gaps = read_file(wsr("gaps"))
        post(ch_id, f"🔍 *Agent Gap Log — `{ws_name()}`*\n```\n{gaps[-2000:]}\n```")
        return True

    # ── SHOW_BACKEND ──────────────────────────────────────────────────────────
    if cmd == "SHOW_BACKEND":
        post(ch_id, f"🖥️ *Inference Backend*\n{backend_status()}\n\n{active_model_info()}")
        return True

    # ── SET MODEL (while paused or stopped) ───────────────────────────────────
    m_sm = re.match(r"SET MODEL\s+(\S+)", cmd_raw.strip(), re.IGNORECASE)
    if m_sm:
        if state.running and not state.paused:
            post(ch_id, "⚠️ Loop is running. Type `PAUSE` first, then `SET MODEL <name>`.")
            return True
        model_name = m_sm.group(1).strip()
        ok, msg = set_model(model_name)
        post(ch_id, f"🔧 *Model Switch*\n{msg}")
        if ok:
            post_all(f"🔧 *Model changed to `{model_name}`* by operator\n"
                     f"Takes effect on next inference call.")
        return True

    # ── SHOW_SEQUENCE ─────────────────────────────────────────────────────────
    if cmd == "SHOW_SEQUENCE":
        seq_str = " → ".join(AGENT_LABELS.get(a,a) for a in state.last_sequence) or "none yet"
        post(ch_id,
             f"🧠 *Last Coordinator Sequence*\n`{seq_str}`\n\n"
             f"```\n{ws_read('coordinator')[:1200]}\n```")
        return True

    # ── STATUS ────────────────────────────────────────────────────────────────
    if cmd == "STATUS":
        p_lines = 0
        try: p_lines = read_file(wsr("output")).count('\n')
        except: pass
        seq_str = " → ".join(AGENT_LABELS.get(a,a) for a in state.last_sequence) or "none"
        post(ch_id,
             f"📊 *Loop {state.loop_count}* | WS: `{ws_name()}` | Mode: `{state.mode}`\n"
             f"Running: {state.running} | Paused: {state.paused} | P0: {state.protocol_zero}\n"
             f"Promoted: {p_lines}L | Seq: {seq_str}\n"
             f"{backend_status()}\n⚛️ {fmt_qdata()}")
        return True

    if cmd == "STATUS ALL":
        p_lines = 0
        try: p_lines = read_file(wsr("output")).count('\n')
        except: pass
        seq_str = " → ".join(AGENT_LABELS.get(a,a) for a in state.last_sequence) or "none"
        post(ch("intake"),
             f"📊 *SYSTEM STATUS — Loop {state.loop_count}*\n"
             f"WS: `{ws_name()}` | Mode: `{state.mode}`\n"
             f"{backend_status()}\nPromoted: {p_lines}L\nSeq: {seq_str}\n"
             f"⚛️ {fmt_qdata()}\n_Type `WORKSPACES` to see all projects_")
        post(ch("arch"),
             f"📊 *Coordinator — Loop {state.loop_count}*\n"
             f"```\n{ws_read('coordinator')[:600]}\n```")
        post(ch("physics"),
             f"📊 *Physics — Loop {state.loop_count}*\n"
             f"```\n{ws_read('physics')[:400]}\n```")
        return True

    # ── File views ────────────────────────────────────────────────────────────
    if cmd == "SHOW_BRIEF":
        post(ch_id, f"📋 *Intake Brief:*\n```\n{ws_read('intake')[:1500]}\n```"); return True
    if cmd == "SHOW_CODE":
        w = read_file(wsr("working"))
        post(ch_id, f"🔨 *Working file* ({w.count(chr(10))} lines):\n```\n{w[:1500]}\n```"); return True
    if cmd == "SHOW_PHYSICS":
        post(ch_id, f"⚛️ *Physics:*\n```\n{ws_read('physics')[:1500]}\n```"); return True
    if cmd == "SHOW_OUTPUT":
        p = read_file(wsr("output"))
        post(ch_id, f"✅ *Promoted* ({p.count(chr(10))} lines):\n```\n{p[:1500]}\n```"); return True
    if cmd == "SHOW_INSTRUCTIONS":
        post(ch_id, f"📋 *INSTRUCTIONS.md — `{ws_name()}`*\n```\n{ws_read('instructions')[:2000]}\n```"); return True
    if cmd == "CHANGELOG":
        post(ch_id, f"📜 *Changelog:*\n```\n{read_file(wsr('changelog'))[-2000:]}\n```"); return True

    # ── PULL_DATA ─────────────────────────────────────────────────────────────
    if cmd == "PULL_DATA":
        d = state.quantum_data
        if not d: post(ch_id, "⚛️ No live data. Start qcai_3d.py."); return True
        nn = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
              "Echo","Iris","Sage","Kevin","Atlas","Void"]
        pcms = d.get("pcms",[0]*12); phases = d.get("phases",[0]*12)
        outputs = d.get("node_outputs",[""] *12); domains = d.get("domains",["?"]*12)
        def gl(p): return "🟢" if p<-0.15 else "🟡" if p<-0.05 else "🟠" if p<0.05 else "🔴"
        nl = "\n".join(f"{gl(pcms[i])} {nn[i]:<8} PCM={pcms[i]:+.3f} "
                       f"φ={phases[i]:.2f} [{domains[i] if i<len(domains) else '?':<12}] "
                       f"\"{outputs[i] if i<len(outputs) else ''}\""
                       for i in range(min(12,len(pcms))))
        post(ch_id, f"[QUANTUM_CONTEXT_UPDATE] Step {d.get('step',0)}\n"
                    f"```\ncv={d.get('cv',0):.4f}  nf={d.get('negfrac',0):.4f}  "
                    f"nc={d.get('nc_count',0)}/12  R={d.get('reward',0):.4f}\n```\n"
                    f"*Nodes:*\n```\n{nl}\n```")
        return True

    # ── Version commands ──────────────────────────────────────────────────────
    if cmd == "BEST":
        best = ckpt_read("best_physics_pass")
        post(ch_id, f"⭐ *Best Physics PASS* ({best.count(chr(10))} lines):\n```\n{best[:1000]}\n```"
             if "[Checkpoint not found" not in best
             else "No physics-pass checkpoint yet.")
        return True

    if cmd == "CHECKPOINT":
        p = read_file(wsr("output"))
        if "[File not found" not in p:
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            ckpt_save(f"manual_{ts}", p)
            post(ch_id, f"📦 Checkpoint saved: `checkpoints/manual_{ts}.py` ({p.count(chr(10))} lines)")
        else: post(ch_id, "❌ No promoted output yet.")
        return True

    if cmd.startswith("ROLLBACK"):
        parts = cmd.split()
        if len(parts) < 2: post(ch_id, "Usage: `ROLLBACK <loop_number>`"); return True
        try:
            n = int(parts[1]); code = ver_read("output", n)
            if "[Version not found" in code: post(ch_id, f"❌ No version for loop {n}")
            else:
                write_file(wsr("output"), code)
                post(ch_id, f"↩️ Rolled back to loop {n} ({code.count(chr(10))} lines)")
        except ValueError: post(ch_id, "❌ Invalid number")
        return True

    if cmd.startswith("SHOW_VERSION"):
        parts = cmd.split()
        if len(parts) < 2: post(ch_id, "Usage: `SHOW_VERSION <loop_number>`"); return True
        try:
            n = int(parts[1]); code = ver_read("output", n)
            post(ch_id, f"📄 Loop {n} ({code.count(chr(10))} lines):\n```\n{code[:1000]}\n```")
        except ValueError: post(ch_id, "❌ Invalid number")
        return True

    if cmd == "LOAD_TASK":
        content = ws_read("task")
        if "[File not found" in content:
            post(ch_id, f"❌ No task file at `{wsr('task')}`"); return True
        post(ch_id,
             f"📋 Task loaded ({len(content)} chars) | WS: `{ws_name()}`\n"
             f"```\n{content[:300]}...\n```\nStarting loop...")
        if not state.running:
            with state.lock: state.running = True; state.original_req = content
            threading.Thread(target=agent_loop, args=(content,), daemon=True).start()
        else: post(ch_id, "⚠️ Loop already running. Type `STOP` first.")
        return True

    # ── LOAD_TASK <inline task> [use <model>] ─────────────────────────────────
    # e.g.: "Improve the PCM renderer use qwen3.5:9b-qcai"
    # e.g.: "Fix the globe Wayland bug use qwen3-8b-jarvis"
    m_lt = re.match(r"LOAD_TASK\s+(.+)", cmd_raw.strip(), re.IGNORECASE)
    if m_lt:
        task_text = m_lt.group(1).strip()
        # Check for "use <model>" suffix
        use_m = re.search(r"use\s+([\w\.\-:]+)\s*$", task_text, re.IGNORECASE)
        if use_m:
            requested_model = use_m.group(1).strip()
            task_text = task_text[:use_m.start()].strip()
            ok, msg = set_model(requested_model)
            post(ch_id, f"🔧 {msg}")
        # Write task to workspace
        write_file(wsr("task"), task_text)
        post(ch_id,
             f"📋 *Inline task set* | WS: `{ws_name()}` | Model: `{MODEL}`\n"
             f"```\n{task_text[:300]}\n```\nStarting loop...")
        if not state.running:
            with state.lock: state.running = True; state.original_req = task_text
            threading.Thread(target=agent_loop, args=(task_text,), daemon=True).start()
        else: post(ch_id, "⚠️ Loop already running. Type `STOP` first.")
        return True


    # ── APPROVE UPDATE <filename> ─────────────────────────────────────────────
    m_au = re.match(r"APPROVE UPDATE\s+(.+)", cmd_raw.strip(), re.IGNORECASE)
    if m_au:
        fname = m_au.group(1).strip()
        queue_path = ws_path(f"SendToOpenJarvisUpdaterFiles/{fname}")
        updater_path = os.path.join(os.path.expanduser(os.path.join(UPDATES_DIR, "OpenJarvisUpdater")), fname)
        if os.path.exists(queue_path):
            import shutil as _su
            _su.copy2(queue_path, updater_path)
            post(ch_id, f"✅ *Approved: `{fname}`*\nCopied to `/var/home/kmonette/OpenJarvis/Updates/OpenJarvisUpdater/`\n"
                        f"Run `jarvis-update` to deploy.")
        else:
            post(ch_id, f"❌ File not found in queue: `{fname}`\nCheck `SendToOpenJarvisUpdaterFiles/`")
        return True

    # ── REJECT UPDATE <filename> ──────────────────────────────────────────────
    m_ru = re.match(r"REJECT UPDATE\s+(.+)", cmd_raw.strip(), re.IGNORECASE)
    if m_ru:
        fname = m_ru.group(1).strip()
        queue_path = ws_path(f"SendToOpenJarvisUpdaterFiles/{fname}")
        log_entry = {"ts": datetime.now().isoformat(), "file": fname,
                     "action": "REJECTED", "by": "human"}
        with open(ws_path("update_logs/update_log.jsonl"), "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        post(ch_id, f"🚫 *Rejected: `{fname}`* — logged. File remains in update_versions/ for history.")
        return True

    # ── INGEST DOCUMENTS ──────────────────────────────────────────────────────
    if cmd == "INGEST DOCUMENTS" or cmd == "INGEST_DOCUMENTS":
        post(ch_id, f"📥 *Starting document ingestion loop* | WS: `{ws_name()}`\n"
                    f"Drop files in: `intake_documents/raw/`")
        threading.Thread(target=lambda: run_intake_document_loop(state.loop_count),
                        daemon=True).start()
        return True

    # ── SCAN UPDATES ──────────────────────────────────────────────────────────
    if cmd == "SCAN UPDATES" or cmd == "SCAN_UPDATES":
        post(ch_id, f"🔍 *Scanning Kevin's recommendations...*")
        threading.Thread(target=lambda: run_update_agent(state.loop_count),
                        daemon=True).start()
        return True

    # ── SHOW UPDATES ──────────────────────────────────────────────────────────
    if cmd == "SHOW UPDATES" or cmd == "SHOW_UPDATES":
        queue = ws_path("SendToOpenJarvisUpdaterFiles")
        files = os.listdir(queue) if os.path.exists(queue) else []
        log_content = read_file(ws_path("update_logs/update_log.jsonl"))
        post(ch_id,
            f"📊 *Update Queue — `{ws_name()}`*\n"
            f"Files ready for your review:\n"
            + ("\n".join(f"  • `{f}`" for f in files) or "  (empty)")
            + f"\n\nLast 3 log entries:\n```\n{log_content[-800:]}\n```")
        return True

    # ── SOCIAL <to_agent> <message> ───────────────────────────────────────────
    m_soc = re.match(r"SOCIAL\s+(\S+)\s+(.+)", cmd_raw.strip(), re.IGNORECASE)
    if m_soc:
        to_raw = m_soc.group(1).strip()
        message = m_soc.group(2).strip()
        to_agents = [a.strip() for a in to_raw.split(",")]
        social_ping("human", to_agents, message, priority=1)
        post(ch_id, f"💬 *Social ping queued* → {to_agents}\n`{message[:100]}`")
        return True

    # ── SHOW COMMANDS ─────────────────────────────────────────────────────────
    if cmd == "SHOW COMMANDS" or cmd == "SHOW_COMMANDS":
        registry = read_file(ws_path("commands/registry/COMMAND_REGISTRY.md"))
        smart_post(ch_id,
            f"📜 *Command Registry — `{ws_name()}`*\n```\n{registry[-2000:]}\n```",
            "command_registry")
        return True

    # ── NODE STATUS ───────────────────────────────────────────────────────────
    if cmd == "NODE STATUS" or cmd == "NODE_STATUS":
        d = state.quantum_data
        if not d:
            post(ch_id, "⚛️ No live quantum data. Start qcai_3d.py first.")
            return True
        nn = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
              "Echo","Iris","Sage","Kevin","Atlas","Void"]
        pcms   = d.get("pcms",   [0]*12)
        phases = d.get("phases", [0]*12)
        domains= d.get("domains",["?"]*12)
        modes  = {n: NODE_TRAINING_MODES.get(n,"training") for n in nn}
        lines  = ["*Node Classical Layer Status*\n```"]
        for i, name in enumerate(nn):
            gl = "🟢" if pcms[i]<-0.15 else "🟡" if pcms[i]<-0.05 else "🟠" if pcms[i]<0.05 else "🔴"
            lines.append(f"{gl} {name:<10} PCM={pcms[i]:+.3f} φ={phases[i]:.2f} "
                         f"[{domains[i]:<14}] mode={modes[name]}")
        lines.append("```")
        post(ch_id, "\n".join(lines))
        return True

    return False

# ─── Live Feed Server ─────────────────────────────────────────────────────────

def start_feed_server():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            try:
                d = json.loads(body)
                state.quantum_data = d
                state.data_history.append(d)
                step = d.get("step", 0)
                if step % 100 == 0 and step > 0:
                    nn      = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
                               "Echo","Iris","Sage","Kevin","Atlas","Void"]
                    pcms    = d.get("pcms",   [0]*12)
                    phases  = d.get("phases", [0]*12)
                    outputs = d.get("node_outputs", [""] * 12)
                    domains = d.get("domains", ["?"] * 12)
                    nb = "\n".join(f"  {nn[i]:<8} PCM={pcms[i]:+.3f}"
                                    for i in range(12))
                    post(ch("data"),
                         f"⚛️ *Step {step}* | `{ws_name()}`\n"
                         f"```\ncv={d.get('cv',0):.4f}  nf={d.get('negfrac',0):.4f}  "
                         f"nc={d.get('nc_count',0)}/12  R={d.get('reward',0):.4f}\n{nb}\n```")

                    # Run node classical layers every 100 steps
                    if outputs:
                        node_outputs  = {nn[i]: outputs[i] for i in range(12)}
                        node_metrics  = {nn[i]: {"pcm": pcms[i], "phase": phases[i],
                                                  "domain": domains[i] if i < len(domains) else "?"}
                                         for i in range(12)}
                        # Run each node agent (non-blocking)
                        for i, name in enumerate(nn):
                            threading.Thread(
                                target=run_node_agent,
                                args=(name, step // 100, pcms[i], phases[i],
                                      domains[i] if i < len(domains) else "?",
                                      outputs[i] if i < len(outputs) else ""),
                                daemon=True
                            ).start()
                        # Consensus (give node agents 3s head start)
                        def _run_consensus():
                            import time as _t; _t.sleep(3)
                            run_consensus_agent(step // 100, node_outputs, node_metrics)
                        threading.Thread(target=_run_consensus, daemon=True).start()
            except Exception as e: log.error(f"Feed: {e}")
            self.send_response(200); self.end_headers()
        def log_message(self, *a): pass

    try:
        server = HTTPServer(("0.0.0.0", 9999), Handler)
        log.info("Feed server: port 9999")
        server.serve_forever()
    except OSError as e:
        log.warning(f"Feed server: {e}")

# ─── Slack Events ─────────────────────────────────────────────────────────────

@app.event("app_mention")
def handle_mention(event, client):
    text  = re.sub(r"<@\w+>", "", event.get("text","")).strip()
    ch_id = event.get("channel","")
    if not handle_command(text, ch_id):
        if ch_id == ch("intake") and state.running:
            post(ch_id, "⚠️ Loop running. Type `STOP` first.")
        elif ch_id == ch("intake"):
            with state.lock: state.running = True; state.original_req = text
            threading.Thread(target=agent_loop, args=(text,), daemon=True).start()

@app.message()
def handle_message(message, client):
    if message.get("bot_id"): return
    if message.get("user") == BOT_USER_ID: return
    text  = message.get("text","").strip()
    ch_id = message.get("channel","")
    if ch_id not in ALL_CHANNEL_IDS: return
    if handle_command(text, ch_id): return
    if ch_id == ch("intake"):
        if state.running: post(ch_id, "⚠️ Loop running. Type `STOP` first.")
        else:
            # Check for "use <model>" anywhere in the message
            use_m = re.search(r"\buse\s+([\w\.\-:]+)\s*$", text, re.IGNORECASE)
            task_text = text
            if use_m:
                requested_model = use_m.group(1).strip()
                task_text = text[:use_m.start()].strip()
                ok, msg = set_model(requested_model)
                post(ch_id, f"🔧 {msg}")
            write_file(wsr("task"), task_text)
            with state.lock: state.running = True; state.original_req = task_text
            threading.Thread(target=agent_loop, args=(task_text,), daemon=True).start()

# ─── Workspace Seeding ────────────────────────────────────────────────────────

def seed_default_workspaces():
    """Ensure ws_1 (QCAI) and ws_2 (jarvis-system) exist on startup."""
    # ws_1 — QCAI
    ws1 = os.path.join(WORKSPACES_ROOT, "ws_1")
    if not os.path.isdir(ws1):
        create_workspace("ws_1", "QCAI Quantum-Classical Co-Evolutionary AI visualizer")
        brief_path = os.path.join(ws1, "WORKSPACE_BRIEF.md")
        with open(brief_path, "w") as f:
            f.write("# ws_1 — QCAI\n\nQuantum-Classical Co-Evolutionary AI visualizer.\n"
                    "12-node quantum ring on icosphere. BCP physics. Wayland/TkAgg.\n"
                    "Audience: Dr. Hanna Terletska (MTSU) + Prof. B. Alex King III (APSU)\n\n"
                    f"Created: {datetime.now().isoformat()}\n")
        # Migrate existing workspace/ directory if present
        old_ws = os.path.join(JARVIS_ROOT, "workspace")
        if os.path.isdir(old_ws):
            for item in ["qcai_3d.py","GROUND_TRUTH.md","current_task.md",
                         "components_master","components_promoted","logs"]:
                src = os.path.join(old_ws, item)
                dst = os.path.join(ws1, item)
                if os.path.exists(src) and not os.path.exists(dst):
                    if os.path.isdir(src): shutil.copytree(src, dst)
                    else: shutil.copy2(src, dst)
            log.info(f"Migrated workspace/ → ws_1")

    # ws_2 — Jarvis System (this project)
    ws2 = os.path.join(WORKSPACES_ROOT, "ws_2")
    if not os.path.isdir(ws2):
        create_workspace("ws_2",
            "OpenJarvis Slack Bridge — the agent pipeline itself. "
            "slack_bridge.py, assembler.py, component_manager.py, tester.py, reviewer.py.")
        brief_path = os.path.join(ws2, "WORKSPACE_BRIEF.md")
        with open(brief_path, "w") as f:
            f.write("# ws_2 — Jarvis System\n\n"
                    "The OpenJarvis agent pipeline itself.\n"
                    "Files: slack_bridge.py, assembler.py, component_manager.py, "
                    "tester.py, reviewer.py, start_qcai.sh, load_and_run.sh\n\n"
                    "Goal: continuously improve the agent loop, coordinator logic, "
                    "workspace management, and resilience.\n\n"
                    f"Created: {datetime.now().isoformat()}\n")
        # Copy current bridge as protected master
        bridge_src = os.path.join(JARVIS_ROOT, "slack_bridge.py")
        if os.path.exists(bridge_src):
            shutil.copy2(bridge_src, os.path.join(ws2, "slack_bridge.py"))
        log.info("ws_2 (jarvis-system) created")

    # ── Create Kevin's recommendation folder ──────────────────────────────────
    recs_dir = os.path.expanduser(os.path.join(UPDATES_DIR, "KevinsUpdateRecommendations"))
    os.makedirs(recs_dir, exist_ok=True)
    readme = os.path.join(recs_dir, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w") as f:
            f.write("# Kevin's Update Recommendations\n\n"
                    "Drop any file here that you want the Update Agent to evaluate.\n"
                    "The agent will:\n"
                    "  1. Assess validity and safety\n"
                    "  2. Improve in sandbox if needed\n"
                    "  3. Version and log everything\n"
                    "  4. Send approved files to SendToOpenJarvisUpdaterFiles/ for your review\n"
                    "  5. Alert you about any risky changes requiring human decision\n\n"
                    "Commands:\n"
                    "  SCAN UPDATES  — run the update agent now\n"
                    "  SHOW UPDATES  — see what's queued for review\n"
                    "  APPROVE UPDATE <filename>  — approve and queue for deployment\n"
                    "  REJECT UPDATE <filename>   — reject and log\n")
    log.info(f"Kevin's recommendations folder ready: {recs_dir}")

    # ── Seed stop_qcai.sh and launch_qcai.sh if absent or stub ─────────────────
    # IMPORTANT: Only create stubs if the real script does not exist OR is too
    # small to be the real version (< 20 lines = stub). Never overwrite a real
    # multi-line script with a 3-line placeholder.
    STUB_MIN_LINES = 20
    for script_name, script_content in [
        ("stop_qcai.sh",
         "#!/usr/bin/env bash\n# Stop all QCAI processes safely\n"
         "pkill -f slack_bridge.py 2>/dev/null && echo '✅ Bridge stopped' || echo '⚠️ Bridge not running'\n"
         "pkill -f viz_loop.sh 2>/dev/null || true\n"
         "pkill -f qcai_3d 2>/dev/null || true\n"
         "fuser -k 9999/tcp 2>/dev/null && echo '✅ Port 9999 cleared' || true\n"
         "echo 'QCAI stopped. Run qcai-launch to restart.'\n"),
        ("launch_qcai.sh",
         "#!/usr/bin/env bash\n# Launch QCAI bridge (delegates to start_qcai.sh)\n"
         "cd /var/home/kmonette/OpenJarvis && ./start_qcai.sh\n"),
    ]:
        script_path = f"/var/home/kmonette/OpenJarvis/{script_name}"
        # Check if real version exists (real scripts are > STUB_MIN_LINES)
        should_create = False
        if not os.path.exists(script_path):
            should_create = True
        else:
            try:
                with open(script_path) as f:
                    line_count = sum(1 for _ in f)
                if line_count < STUB_MIN_LINES:
                    should_create = True   # existing file is a stub — safe to replace
                    log.info(f"{script_name} is a {line_count}-line stub — will recreate minimal version")
            except Exception:
                should_create = True
        if should_create:
            try:
                with open(script_path, "w") as f: f.write(script_content)
                os.chmod(script_path, 0o755)
                log.info(f"Created seed: {script_name}")
            except Exception as e:
                log.warning(f"Could not create {script_name}: {e}")
        else:
            log.info(f"{script_name} already exists with real content — skipping seed")

    # ── Start social dispatcher + recover any unfinished pings ──────────────
    _social_recover_queue()   # re-queue any pings that were in-flight at last shutdown
    threading.Thread(target=_social_dispatcher, daemon=True).start()
    log.info("Social dispatcher started")

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("=" * 65)
    log.info("OpenJarvis Slack Bridge v9.1")
    log.info("Coordinator + Multi-Workspace + Gap Detection + Ollama Resilience")
    log.info("=" * 65)

    if not all([SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET]):
        log.error("Missing Slack tokens"); raise SystemExit(1)

    api_ok    = check_api()
    ollama_ok = check_ollama()
    if not api_ok and not ollama_ok:
        log.error("Both OpenJarvis API and Ollama unavailable"); raise SystemExit(1)

    log.info(f"OpenJarvis API : {'✅' if api_ok else '❌ (will use Ollama)'}")
    log.info(f"Ollama         : {'✅' if ollama_ok else '❌'}")
    log.info(f"Active backend : {_backend_used}")

    try: BOT_USER_ID = app.client.auth_test()["user_id"]
    except Exception: pass
    log.info(f"Bot ID: {BOT_USER_ID}")

    os.makedirs(WORKSPACES_ROOT, exist_ok=True)
    seed_default_workspaces()
    active = get_active_ws()
    ws_init(active)
    log.info(f"Active workspace: {active}")

    threading.Thread(target=start_feed_server, daemon=True).start()

    # Warm model
    try:
        requests.post(f"{OPENJARVIS_API}/v1/chat/completions",
                      json={"model": MODEL, "messages":[{"role":"user","content":"ping"}],
                            "max_tokens": 5}, timeout=60)
        log.info("✅ Model warmed up")
    except Exception as e: log.warning(f"Warm-up: {e}")

    log.info("Ready.")
    log.info("To begin: drop task in #jarvis-intake or type LOAD_TASK")
    log.info("To create workspace from intake: NEW WORKSPACE <name> \"description\"")
    log.info("=" * 65)

    SocketModeHandler(app, SLACK_APP_TOKEN).start()

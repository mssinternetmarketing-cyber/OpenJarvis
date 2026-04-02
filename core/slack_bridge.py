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


import json
def load_channels():
    reg_path = "/var/home/kmonette/OpenJarvis/registry/agents.json"
    with open(reg_path, 'r') as f:
        return json.load(f)
CHANNELS = load_channels()


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
    "commands":          "CommandsAgent",
    "peig":              "PEIG",           # MOS v8 governance oracle
}

SEQUENCEABLE_AGENTS = [
    "plan", "prime",
    "build_header", "build_physics", "build_systems",
    "build_render", "build_curriculum", "build_integration", "build",
    "test", "review", "assemble", "physics",
    "commands",   # Commands Agent — creates tools when value is identified
    "peig",       # PEIG Agent — governance oracle for significant/irreversible decisions
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

# ── Protected host commands — agents CANNOT overwrite these ───────────────────
# Agents MAY create new cmd_<n>.sh/.py tools but cannot touch these.
# Any attempted overwrite is backed up to commands/backups/ and blocked.
PROTECTED_COMMANDS = {
    "qcai-launch", "qcai-stop", "qcai-restart", "qcai-reset", "qcai-fresh",
    "qcai-update", "qcai-status", "qcai-logs", "qcai-update-updater",
    "qcai-viz", "qcai-viz-pause", "qcai-viz-resume", "qcai-viz-update",
    "qcai-trainer", "qcai-mode",
}

def is_protected_command(cmd_name: str) -> bool:
    """Return True if cmd_name is a protected system command agents cannot overwrite."""
    clean = cmd_name.replace("cmd_", "").split(".")[0].replace("_", "-")
    return clean in PROTECTED_COMMANDS or cmd_name in PROTECTED_COMMANDS

WS_SUBDIRS = [
    # Core
    "protected", "sandbox",
    "components_master", "components_promoted", "components_sandbox",
    "logs",
    "toolbox",
    "toolbox/logs",
    "Personalities",
    "PostProcessedLogs", "checkpoints",
    "versions/intake",  "versions/prime",  "versions/builder",
    "versions/physics", "versions/output", "versions/coordinator",
    "versions/peig",    # PEIG governance reports — one per invocation
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
    "commands/scripts",         # .py/.sh scripts agents create (approved)
    "commands/sandbox",         # staging area — scripts under review
    "commands/registry",        # latest command list files
    "commands/logs",            # command edits, additions, removals
    "commands/backups",         # command backups before removal/overwrite
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

    # ── PEIG auto-check: large changes or physics-pass promotions ────────────
    # A promotion is significant when: it's a physics PASS from source="Physics"
    # or the file is substantially different from the current promoted version.
    # We check but don't block — PEIG advisory only at promotion time.
    try:
        current_lines = 0
        try:
            current_lines = read_file(wsr("output")).count('\n')
        except Exception:
            pass
        new_lines = code.count('\n')
        line_delta = abs(new_lines - current_lines)

        if source == "Physics" and line_delta > 50:
            peig_decision = (f"Promote Physics-validated code to output (qcai_3d.py)\n"
                             f"Lines: {current_lines} → {new_lines} (delta={line_delta:+d})\n"
                             f"Source: {source} | Loop: {loop}")
            should, reason_peig, urgency = should_invoke_peig(
                peig_decision, "physics", f"loop={loop} source={source}")
            if should:
                threading.Thread(
                    target=run_peig_agent,
                    args=(loop, peig_decision, reason_peig, urgency, source, False),
                    daemon=True
                ).start()
    except Exception as e:
        log.debug(f"PEIG pre-promote check error (non-blocking): {e}")

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

# ═══════════════════════════════════════════════════════════════════════════════
# ── COMMANDS AGENT SYSTEM ─────────────────────────────────────────────────────
# Agents create real .sh/.py tools that become host commands.
# Full pipeline: sandbox → test → review → approval → install → announce.
# Protected system commands (PROTECTED_COMMANDS) can never be overwritten.
# Every action is backed up. Nothing is silently discarded.
# ═══════════════════════════════════════════════════════════════════════════════

COMMANDS_HOST_DIR = os.path.join(JARVIS_ROOT, "commands")
COMMANDS_BIN_DIR  = os.path.expanduser("~/bin")
UPDATER_DIR_CMD   = os.path.join(JARVIS_ROOT, "Updates", "OpenJarvisUpdater")

def _cmd_backup(src: str, reason: str = "backup") -> str:
    """Backup a file to commands/backups/ before any destructive action. Returns backup path."""
    bk_dir = ws_path("commands/backups")
    os.makedirs(bk_dir, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    bk  = os.path.join(bk_dir, f"{ts}_{reason}_{os.path.basename(src)}")
    try:
        if os.path.exists(src):
            shutil.copy2(src, bk)
    except Exception as e:
        log.warning(f"cmd_backup failed: {e}")
    return bk

def _cmd_log(entry: dict):
    """Append a structured entry to commands/logs/registry_log.jsonl."""
    log_path = ws_path("commands/logs/registry_log.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    entry.setdefault("ts", datetime.now().isoformat())
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log.warning(f"cmd_log: {e}")

def _cmd_registry_update(cmd_name: str, script_path: str,
                          description: str, created_by: str,
                          status: str = "active"):
    """Update the Markdown and JSON command registries."""
    # ── Markdown registry ─────────────────────────────────────────────────────
    md_path = ws_path("commands/registry/COMMAND_REGISTRY.md")
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    md_entry = (
        f"\n## {cmd_name}\n"
        f"Status: `{status}`\n"
        f"Command: `{cmd_name}`\n"
        f"Description: {description}\n"
        f"Created by: {created_by} | {ts}\n"
        f"Script: `{script_path}`\n"
    )
    with open(md_path, "a") as f:
        f.write(md_entry)

    # ── JSON registry ─────────────────────────────────────────────────────────
    json_path = os.path.join(COMMANDS_HOST_DIR, "registry", "commands.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    try:
        with open(json_path) as f:
            data = json.load(f)
    except Exception:
        data = {"commands": []}
    data["commands"] = [c for c in data["commands"] if c.get("name") != cmd_name]
    data["commands"].append({
        "name": cmd_name,
        "script": script_path,
        "description": description,
        "created_by": created_by,
        "status": status,
        "ts": ts,
    })
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)

def _install_command_wrapper(cmd_name: str, script_path: str) -> bool:
    """
    Create a ~/bin/<cmd_name> distrobox wrapper for the script.
    Returns True on success.
    This is what makes the command usable from the HOST terminal.
    """
    os.makedirs(COMMANDS_BIN_DIR, exist_ok=True)
    wrapper = os.path.join(COMMANDS_BIN_DIR, cmd_name)
    ext = os.path.splitext(script_path)[1]
    distrobox = "openjarvis-box"
    if ext == ".sh":
        content = (
            f'#!/usr/bin/env bash\n'
            f'# Auto-installed by OpenJarvis Commands Agent\n'
            f'# Script: {script_path}\n'
            f'distrobox enter {distrobox} -- bash "{script_path}" "$@"\n'
        )
    else:
        content = (
            f'#!/usr/bin/env bash\n'
            f'# Auto-installed by OpenJarvis Commands Agent\n'
            f'# Script: {script_path}\n'
            f'distrobox enter {distrobox} -- python3 "{script_path}" "$@"\n'
        )
    try:
        with open(wrapper, "w") as f:
            f.write(content)
        os.chmod(wrapper, 0o755)
        return True
    except Exception as e:
        log.error(f"install_command_wrapper {cmd_name}: {e}")
        return False

def submit_command_for_review(script_name: str, description: str,
                               command: str, content: str,
                               created_by: str = "agent") -> str:
    """
    Full Commands Agent pipeline:
      1. Guard: block if name clashes with PROTECTED_COMMANDS
      2. Backup any existing version
      3. Save to commands/sandbox/
      4. Version it in commands/logs/
      5. Run tester → reviewer (LLM-based, same pattern as component pipeline)
      6. If approved: promote to commands/scripts/, install ~/bin wrapper,
         drop copy in OpenJarvisUpdater/ for qcai-update, register, announce
      7. If rejected: stay in sandbox, post failure report
    Returns status string.
    """
    # ── 1. Protected command guard ────────────────────────────────────────────
    if is_protected_command(command):
        msg = (f"🛑 *Command `{command}` is PROTECTED* — cannot be overwritten by agents.\n"
               f"Protected commands: {sorted(PROTECTED_COMMANDS)}\n"
               f"Create a new name (e.g. `{command}-v2`) to add similar functionality.")
        smart_post(ch("commands"), msg)
        _cmd_log({"action": "BLOCKED_PROTECTED", "command": command,
                  "attempted_by": created_by, "script": script_name})
        return "blocked: protected command"

    # ── 2. Backup any existing version in sandbox/scripts ────────────────────
    sandbox_dir  = ws_path("commands/sandbox")
    scripts_dir  = ws_path("commands/scripts")
    os.makedirs(sandbox_dir, exist_ok=True)
    os.makedirs(scripts_dir, exist_ok=True)

    sandbox_path = os.path.join(sandbox_dir, script_name)
    scripts_path = os.path.join(scripts_dir, script_name)

    if os.path.exists(sandbox_path):
        _cmd_backup(sandbox_path, "sandbox_overwrite")
    if os.path.exists(scripts_path):
        _cmd_backup(scripts_path, "scripts_overwrite")

    # ── 3. Save to sandbox ────────────────────────────────────────────────────
    with open(sandbox_path, "w") as f:
        f.write(content)
    os.chmod(sandbox_path, 0o755)

    # ── 4. Version it ─────────────────────────────────────────────────────────
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ver_dir = ws_path("commands/logs")
    os.makedirs(ver_dir, exist_ok=True)
    ver_path = os.path.join(ver_dir, f"{ts}_{script_name}")
    with open(ver_path, "w") as f:
        f.write(content)

    _cmd_log({"action": "SANDBOX_SAVED", "script": script_name,
              "command": command, "created_by": created_by, "sandbox": sandbox_path})

    smart_post(ch("commands"),
        f"🔬 *Commands Agent: `{command}` submitted for review*\n"
        f"Script: `{script_name}` | By: {created_by}\n"
        f"Saved to sandbox → running tester + reviewer...")

    # ── 5. Tester pass ────────────────────────────────────────────────────────
    ext = os.path.splitext(script_name)[1]
    lang = "shell" if ext == ".sh" else "python"

    tester_sys = f"""{_mission()}
You are OpenJarvis Tester reviewing a NEW COMMAND SCRIPT for the commands registry.
Script: {script_name}  Command: {command}  Type: {lang}
Protected commands (NEVER allow overwrite): {sorted(PROTECTED_COMMANDS)}

Evaluate the script on these criteria:
1. SAFETY: Does it do what the description says? Any destructive side-effects?
2. RESILIENCE: Does it have error handling? Does it backup before modifying?
3. IDEMPOTENT: Safe to run multiple times?
4. DESCRIPTION MATCH: Does the code match the stated purpose?
5. PROTECTED: Does the command name clash with a protected command? (instant fail)
6. SHELL/PYTHON QUALITY: Correct syntax, no obvious bugs?

OUTPUT FORMAT:
TESTER RESULT: [PASS / FAIL]
SCORE: [0-10]
ISSUES: [list any problems, or NONE]
RECOMMENDATION: [approve / reject / revise]
NOTES: [1-2 sentences]"""

    tester_input = (f"COMMAND: {command}\nDESCRIPTION: {description}\n\n"
                    f"SCRIPT CONTENT:\n{content[:3000]}")
    tester_out = infer(tester_sys, tester_input, temperature=0.05, max_tokens=800)

    post(ch("test"),
         f"🧪 *[Commands] Tester — `{command}`*\n```\n{tester_out[:600]}\n```")

    tester_pass = bool(re.search(r"TESTER RESULT:\s*PASS", tester_out, re.IGNORECASE))
    tester_score = 0
    m_sc = re.search(r"SCORE:\s*(\d+)", tester_out)
    if m_sc:
        tester_score = int(m_sc.group(1))

    # ── 6. Reviewer pass ──────────────────────────────────────────────────────
    reviewer_sys = f"""{_mission()}
You are OpenJarvis Reviewer doing final quality sign-off on a COMMAND SCRIPT.
Script: {script_name}  Command: {command}  Tester score: {tester_score}/10

Reviewer criteria:
1. Does this command add GENUINE VALUE to the toolbox? (avoid trivial scripts)
2. Is the command name clear and consistent with existing naming?
3. Would Kevin be glad this was auto-created?
4. Is it safe for agents AND the host to run?
5. Does it respect the protected commands list?

OUTPUT FORMAT:
REVIEWER RESULT: [APPROVED / REJECTED]
VALUE SCORE: [0-10]
REASONING: [2-3 sentences]
USAGE EXAMPLE: [one-liner showing how to use it]"""

    reviewer_input = (f"COMMAND: {command}\nDESCRIPTION: {description}\n"
                      f"TESTER: {tester_out[:400]}\n\nSCRIPT:\n{content[:3000]}")
    reviewer_out = infer(reviewer_sys, reviewer_input, temperature=0.10, max_tokens=800)

    post(ch("review"),
         f"📋 *[Commands] Reviewer — `{command}`*\n```\n{reviewer_out[:600]}\n```")

    reviewer_approved = bool(re.search(r"REVIEWER RESULT:\s*APPROVED", reviewer_out, re.IGNORECASE))
    usage_m = re.search(r"USAGE EXAMPLE:\s*(.+)", reviewer_out)
    usage_example = usage_m.group(1).strip() if usage_m else f"{command} [args]"

    # ── 7a. REJECTED — stay in sandbox, report ────────────────────────────────
    if not tester_pass or not reviewer_approved:
        fail_reason = []
        if not tester_pass:     fail_reason.append("tester FAIL")
        if not reviewer_approved: fail_reason.append("reviewer REJECTED")
        _cmd_log({"action": "REJECTED", "command": command,
                  "tester": tester_pass, "reviewer": reviewer_approved,
                  "score": tester_score})
        smart_post(ch("commands"),
            f"❌ *Command `{command}` REJECTED*\n"
            f"Reason: {', '.join(fail_reason)}\n"
            f"Script stays in sandbox: `{sandbox_path}`\n"
            f"Tester:\n```\n{tester_out[:300]}\n```\n"
            f"Reviewer:\n```\n{reviewer_out[:300]}\n```\n"
            f"Fix the issues and resubmit via LOAD_TASK.")
        return f"rejected: {', '.join(fail_reason)}"

    # ── 7b. APPROVED — run PEIG check then promote, install, deploy ───────────
    # PEIG gate: installing a new host command is a Tier 2 persistent change
    peig_decision = (f"Install new host command: `{command}`\n"
                     f"Script: {script_name}\nDescription: {description}\n"
                     f"Created by: {created_by}\n"
                     f"Tester score: {tester_score}/10\nReviewer: APPROVED")
    peig_result = peig_gate(
        decision=peig_decision,
        loop=0,
        requesting_agent="commands_agent",
        context=content[:500],
        block_on_pause=False,   # don't pause the loop; just get the verdict
    )
    if peig_result["verdict"] == "REJECT":
        _cmd_log({"action": "REJECTED_BY_PEIG", "command": command,
                  "peig_risks": peig_result.get("risks", [])})
        smart_post(ch("commands"),
            f"⚖️ *Command `{command}` blocked by PEIG*\n"
            f"Risks: {' | '.join(peig_result['risks'][:2])}\n"
            f"Script stays in sandbox. Review #jarvis-peig for full report.")
        return f"rejected by peig: {peig_result['risks'][:1]}"

    # Promote sandbox → scripts/
    shutil.copy2(sandbox_path, scripts_path)
    os.chmod(scripts_path, 0o755)

    # Install ~/bin wrapper (makes it a host command)
    host_scripts_path = os.path.join(COMMANDS_HOST_DIR, "scripts", script_name)
    os.makedirs(os.path.dirname(host_scripts_path), exist_ok=True)
    shutil.copy2(sandbox_path, host_scripts_path)
    os.chmod(host_scripts_path, 0o755)
    wrapper_ok = _install_command_wrapper(command, host_scripts_path)

    # Drop in OpenJarvisUpdater/ so qcai-update can redeploy after restarts
    os.makedirs(UPDATER_DIR_CMD, exist_ok=True)
    updater_copy = os.path.join(UPDATER_DIR_CMD, f"cmd_{command.replace('-','_')}{ext}")
    shutil.copy2(sandbox_path, updater_copy)

    # Register in both registries
    _cmd_registry_update(command, host_scripts_path, description, created_by, "active")

    _cmd_log({"action": "APPROVED_INSTALLED", "command": command,
              "script": scripts_path, "wrapper": os.path.join(COMMANDS_BIN_DIR, command),
              "tester_score": tester_score, "created_by": created_by})

    # Announce
    smart_post(ch("commands"),
        f"✅ *NEW COMMAND INSTALLED: `{command}`*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"*What it does:* {description}\n"
        f"*Usage:* `{usage_example}`\n"
        f"*Script:* `{host_scripts_path}`\n"
        f"*Wrapper:* `~/bin/{command}`\n"
        f"*Host ready:* {'✅' if wrapper_ok else '⚠️ check ~/bin'}\n"
        f"*Created by:* {created_by} | Tester: {tester_score}/10\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Run it: `{command}` from any terminal",
        "new_command_installed")

    return f"installed: {command}"

def register_script(script_name: str, description: str,
                    command: str, content: str,
                    created_by: str = "agent") -> str:
    """
    Backwards-compatible entry point. Routes through the full review pipeline.
    Returns path to the script if approved, or status string if rejected/blocked.
    """
    result = submit_command_for_review(
        script_name=script_name,
        description=description,
        command=command,
        content=content,
        created_by=created_by,
    )
    if result.startswith("installed"):
        return os.path.join(ws_path("commands/scripts"), script_name)
    return result

def deregister_script(script_name: str, reason: str, agent: str = "system"):
    """
    Remove a script from active registry — NEVER deletes. Moves to commands/backups/.
    Blocks deregistration of any script whose command name is in PROTECTED_COMMANDS.
    """
    # Guard: cannot deregister if it maps to a protected command
    cmd_name = script_name.replace("cmd_", "").split(".")[0].replace("_", "-")
    if cmd_name in PROTECTED_COMMANDS:
        smart_post(ch("commands"),
            f"🛑 *Deregister BLOCKED* — `{script_name}` maps to protected command `{cmd_name}`.\n"
            f"Protected commands cannot be removed by agents.")
        _cmd_log({"action": "DEREGISTER_BLOCKED_PROTECTED", "script": script_name,
                  "attempted_by": agent})
        return

    scripts_dir = ws_path("commands/scripts")
    backup_dir  = ws_path("commands/backups")
    os.makedirs(backup_dir, exist_ok=True)

    src = os.path.join(scripts_dir, script_name)
    bk  = _cmd_backup(src, "deregister")

    if os.path.exists(src):
        shutil.move(src, bk)

    _cmd_log({"action": "DEREGISTERED", "script": script_name,
              "reason": reason, "removed_by": agent, "backup": bk})

    smart_post(ch("commands"),
        f"🗑️ *Script deregistered: `{script_name}`*\n"
        f"Reason: {reason} | By: {agent}\n"
        f"Backup preserved: `{bk}`")

# ═══════════════════════════════════════════════════════════════════════════════
# ── PEIG AGENT — MOS v8 Governance Oracle ─────────────────────────────────────
# Channel: #jarvis-peig  C0AQA6U24BF
#
# The PEIG Agent is the system's reasoning oracle for decisions that are:
#   - Significant (architecture changes, new agent roles, model changes)
#   - Irreversible (file deletions, schema changes, deploy to production)
#   - Uncertain (conflicting agent outputs, physics validation failures)
#   - High-blast-radius (anything touching GROUND_TRUTH, protected files,
#     the agent loop itself, or the Ollama model config)
#
# It runs the full MOS v8 PEIG matrix + Angel's Advocate + authority check.
# Its verdict is the blocking gate before any agent proceeds with the action.
# No agent may proceed past a PEIG PAUSE verdict without Kevin's explicit approval.
#
# PEIG = Pros / Ethics / Impact / Governance
# MOS v8 additions: Angel's Advocate, Authority Tier, Uncertainty Calibration,
#                   Fragile Assumptions, Rollback path, 7th-generation check
# ═══════════════════════════════════════════════════════════════════════════════

# ── Trigger classifier — what requires PEIG review ────────────────────────────

PEIG_TRIGGER_KEYWORDS = [
    # Irreversibility signals
    "delete", "remove", "rm ", "drop ", "wipe", "purge", "destroy", "overwrite",
    "replace", "migrate", "schema", "rollback",
    # Significant change signals
    "architecture", "redesign", "refactor all", "change model", "switch model",
    "new agent", "add agent", "remove agent", "change channel", "new workspace",
    "promote to production", "deploy", "ship",
    # Protected-file adjacent
    "ground_truth", "instructions.md", "slack_bridge", "modelfile", "ollama create",
    # Uncertainty signals
    "unsure", "unclear", "conflict", "disagree", "failed", "physics fail",
    "syntax error", "not working", "broken",
]

PEIG_IRREVERSIBLE_PATTERNS = [
    r"rm\s+-rf",
    r"drop\s+table",
    r"delete\s+from",
    r"ollama\s+rm",
    r"overwrite.*ground.truth",
    r"modify.*instructions\.md",
    r"change.*alpha.*=",      # BCP alpha change — physics invariant
    r"change.*pcm.*formula",  # PCM formula change — physics invariant
]

def should_invoke_peig(text: str, agent_key: str = "", context: str = "") -> tuple:
    """
    Classifier: returns (should_invoke: bool, reason: str, urgency: str)
    urgency: 'advisory' | 'required' | 'blocking'
    
    advisory  — worth checking, agent may proceed if PEIG approves
    required  — must run PEIG before proceeding
    blocking  — immediate pause until PEIG clears + Kevin approves
    """
    combined = (text + " " + context).lower()

    # Check irreversible patterns — always blocking
    for pattern in PEIG_IRREVERSIBLE_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return True, f"irreversible pattern: {pattern}", "blocking"

    # Check keyword triggers
    hits = [kw for kw in PEIG_TRIGGER_KEYWORDS if kw in combined]
    if len(hits) >= 3:
        return True, f"multiple trigger keywords: {hits[:3]}", "required"
    if len(hits) >= 1:
        return True, f"trigger keyword: {hits[0]}", "advisory"

    # Always invoke PEIG for protected-file writes
    if any(p.lower() in combined for p in ["ground_truth.md", "instructions.md",
                                            "qcai_3d_master", "slack_bridge.py"]):
        return True, "protected file access detected", "blocking"

    # Always invoke PEIG for Coordinator uncertainty signals
    if agent_key == "arch" and any(w in combined for w in
                                   ["pause_required: yes", "uncertain", "cannot proceed"]):
        return True, "coordinator uncertainty signal", "required"

    return False, "", ""

def make_peig_prompt(loop: int, decision: str, urgency: str,
                     trigger_reason: str) -> str:
    """
    Build the full MOS v8 PEIG prompt for the jarvis-peig agent.
    Includes: PEIG matrix, Angel's Advocate, authority tier,
    uncertainty calibration, fragile assumptions, rollback, verdict.
    """
    gt_excerpt = ""
    try:
        gt_full = read_file(wsr("gt"))
        gt_excerpt = gt_full[:600]
    except Exception:
        pass

    return f"""{_mission()}
You are jarvis-peig — the PEIG Governance Oracle for the OpenJarvis system.
You operate the Omega Synthesis MOS v8 reasoning framework.
Loop {loop} | Urgency: {urgency.upper()} | Trigger: {trigger_reason}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR JOB: Apply the full PEIG matrix to the decision below.
Be the system's reasoning oracle. Be honest. Be precise.
Name failure modes by category. Do not assume away risks.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GROUND TRUTH CONTEXT (physics + node invariants):
{gt_excerpt}

PROTECTED FILES (never overwrite): GROUND_TRUTH.md, INSTRUCTIONS.md,
  protected/qcai_3d_master.py, slack_bridge.py, assembler.py,
  tester.py, reviewer.py

AUTHORITY TIERS (MOS v8):
  Tier 0 — Read-only, no side effects → no approval needed
  Tier 1 — Reversible writes, bounded scope → log only
  Tier 2 — Persistent changes, external calls → human confirmation preferred
  Tier 3 — Irreversible actions, protected files, model changes → Kevin must approve
  Tier 4 — Cross-system, multi-agent orchestration changes → Kevin + audit log

THE DECISION UNDER REVIEW:
{decision}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — complete every section, no skipping:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PEIG REPORT [Loop {loop}]
━━━━━━━━━━━━━━━━━━━━

AUTHORITY TIER: [0/1/2/3/4] — [reason]

PEIG MATRIX:
  PROS: [measurable benefits with confidence — be specific, not generic]
  ETHICS: [bias risk, privacy exposure, harm to system integrity]
  IMPACT: [blast radius of failure — what breaks, who is affected, second-order effects]
  GOVERNANCE: [compliance with GROUND_TRUTH invariants, protected file rules, rollback availability]

ANGEL'S ADVOCATE:
  🔴 BLOCKING RISK: [what fails immediately or under first execution]
    Trigger: [condition that causes failure]
    Rollback: [≤3 steps]
  🟡 MATERIAL RISK: [what degrades under sustained use or edge conditions]
  🟢 WATCH: [low-probability or long-horizon concern]

FRAGILE ASSUMPTIONS:
  1. [assumption that invalidates this decision if false]
  2. [second assumption]
HOW TO VALIDATE: [specific check that confirms or refutes each assumption]

UNCERTAINTY CALIBRATION:
  [High confidence / Moderate / Low / Outside knowledge] — [explicit statement of what I don't know]

ROLLBACK PATH: [≤3 steps to undo this if it goes wrong]

VERDICT: [PROCEED / PROCEED WITH CONDITIONS / PAUSE / REJECT]
CONDITIONS: [if PROCEED WITH CONDITIONS — exact conditions that must be met]
ESCALATE TO KEVIN: [YES / NO] — [reason if YES]

REASONING: [2-3 sentences synthesizing the decision — honest, direct, no hedging]
━━━━━━━━━━━━━━━━━━━━"""

def run_peig_agent(loop: int, decision: str, trigger_reason: str,
                   urgency: str = "required",
                   requesting_agent: str = "system",
                   block_on_pause: bool = True) -> dict:
    """
    Run the PEIG governance oracle.

    Args:
        loop:              current loop number
        decision:          full description of the decision under review
        trigger_reason:    why PEIG was invoked (from should_invoke_peig)
        urgency:           'advisory' | 'required' | 'blocking'
        requesting_agent:  which agent or system invoked PEIG
        block_on_pause:    if True and verdict is PAUSE/REJECT, pause the loop

    Returns dict with keys:
        verdict:    'PROCEED' | 'PROCEED_WITH_CONDITIONS' | 'PAUSE' | 'REJECT'
        conditions: list of conditions (if PROCEED_WITH_CONDITIONS)
        escalate:   bool — should Kevin be notified
        tier:       int — authority tier (0-4)
        report:     full raw PEIG report string
        risks:      list of extracted risk items
    """
    ch_id = ch("peig")

    # Post to PEIG channel that review is starting
    t = post(ch_id,
        f"⚖️ *[Loop {loop}] PEIG Review — {urgency.upper()}*\n"
        f"Requested by: `{requesting_agent}` | Trigger: _{trigger_reason}_\n"
        f"```\n{decision[:300]}\n```")

    # Also post to intake so Kevin sees it
    if urgency in ("blocking", "required"):
        post(ch("intake"),
            f"⚖️ *PEIG Review initiated* | Loop {loop} | {urgency.upper()}\n"
            f"Trigger: {trigger_reason}\n"
            f"Decision: `{decision[:200]}`\n"
            f"_Waiting for PEIG verdict before proceeding..._")

    # Run inference
    sys_p = make_peig_prompt(loop, decision, urgency, trigger_reason)
    usr   = (f"DECISION: {decision}\n\n"
             f"REQUESTING AGENT: {requesting_agent}\n"
             f"WORKSPACE: {ws_name()} | Loop: {loop}\n"
             f"URGENCY: {urgency}\n"
             f"CURRENT STATE:\n"
             f"  Backend: {_backend_used}\n"
             f"  Active workspace: {ws_name()}\n"
             f"  Loop count: {loop}\n"
             f"  Intake brief: {ws_read('intake')[:400]}")

    report = infer(sys_p, usr, temperature=0.10, max_tokens=2500)

    # Parse verdict
    verdict_m = re.search(r"VERDICT:\s*(PROCEED WITH CONDITIONS|PROCEED|PAUSE|REJECT)",
                          report, re.IGNORECASE)
    verdict_raw = verdict_m.group(1).upper().strip() if verdict_m else "PAUSE"
    verdict = verdict_raw.replace(" ", "_")  # normalize

    # Parse authority tier
    tier_m = re.search(r"AUTHORITY TIER:\s*(\d)", report)
    tier = int(tier_m.group(1)) if tier_m else 2

    # Parse escalate flag
    escalate_m = re.search(r"ESCALATE TO KEVIN:\s*(YES|NO)", report, re.IGNORECASE)
    escalate = escalate_m.group(1).upper() == "YES" if escalate_m else (tier >= 3)

    # Parse conditions
    cond_m = re.search(r"CONDITIONS:\s*(.+?)(?:\nESCALATE|━━━|\Z)", report,
                       re.DOTALL | re.IGNORECASE)
    conditions_raw = cond_m.group(1).strip() if cond_m else ""
    conditions = [c.strip() for c in conditions_raw.split("\n")
                  if c.strip() and c.strip().upper() not in ("N/A", "NONE", "-")]

    # Extract risks summary
    risks = []
    for marker in ["🔴", "🟡", "🟢"]:
        risk_m = re.search(rf"{marker}\s+\w+ RISK:\s*(.+?)(?:\n    Trigger|\n🟡|\n🟢|\n\n|\Z)",
                           report, re.DOTALL)
        if risk_m:
            risks.append(f"{marker} {risk_m.group(1).strip()[:120]}")

    # Version the report
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ver_dir = ws_path("versions/peig")
    os.makedirs(ver_dir, exist_ok=True)
    ver_path = os.path.join(ver_dir, f"loop_{loop:03d}_{ts}_peig.md")
    try:
        with open(ver_path, "w") as f:
            f.write(f"# PEIG Report — Loop {loop}\n"
                    f"Trigger: {trigger_reason} | Urgency: {urgency}\n"
                    f"Requesting agent: {requesting_agent}\n"
                    f"Decision: {decision[:300]}\n\n"
                    f"{report}\n")
    except Exception as e:
        log.warning(f"PEIG version write: {e}")

    # Post verdict to PEIG channel
    verdict_emoji = {
        "PROCEED": "✅", "PROCEED_WITH_CONDITIONS": "⚠️",
        "PAUSE": "🛑", "REJECT": "❌",
    }.get(verdict, "⚖️")

    notify = report[:600] + "..." if len(report) > 600 else report
    if t.get("ts"):
        update(ch_id, t["ts"],
               f"{verdict_emoji} *[Loop {loop}] PEIG Verdict: {verdict}*\n"
               f"Tier: {tier} | Escalate: {'YES ⚠️' if escalate else 'no'}\n"
               f"```\n{notify}\n```")

    # Escalate to Kevin if needed
    if escalate:
        post(ch("intake"),
            f"{verdict_emoji} *PEIG ESCALATION — Kevin action required*\n"
            f"Loop {loop} | Verdict: *{verdict}* | Authority Tier: {tier}\n"
            f"Decision: `{decision[:200]}`\n"
            f"Risks: {' | '.join(risks[:2])}\n"
            f"{'Conditions: ' + '; '.join(conditions[:2]) if conditions else ''}\n"
            f"Full report: `{ver_path}`\n"
            f"_Type `RESUME` after reviewing to continue, or `STOP` to halt._")

    # Block loop if verdict is PAUSE or REJECT and block_on_pause is set
    if block_on_pause and verdict in ("PAUSE", "REJECT"):
        with state.lock:
            state.paused = True
        post_all(
            f"🛑 *Loop paused by PEIG* | Verdict: {verdict}\n"
            f"Trigger: {trigger_reason}\n"
            f"{'Risks: ' + ' | '.join(risks[:2]) if risks else ''}\n"
            f"_Review PEIG report in #jarvis-peig, then type `RESUME` to continue._")

    result = {
        "verdict":    verdict,
        "conditions": conditions,
        "escalate":   escalate,
        "tier":       tier,
        "report":     report,
        "risks":      risks,
    }
    log.info(f"PEIG Loop {loop}: verdict={verdict} tier={tier} escalate={escalate}")
    return result

def peig_gate(decision: str, loop: int, requesting_agent: str = "system",
              context: str = "", block_on_pause: bool = True) -> dict:
    """
    Convenience wrapper: classify then run PEIG if warranted.
    Returns PEIG result dict, or {'verdict': 'PROCEED', 'tier': 0, ...} if not triggered.
    Always safe to call — does nothing if no trigger fires.
    """
    should, reason, urgency = should_invoke_peig(decision, requesting_agent, context)
    if not should:
        return {"verdict": "PROCEED", "tier": 0, "conditions": [],
                "escalate": False, "report": "", "risks": []}
    return run_peig_agent(loop, decision, reason, urgency,
                          requesting_agent, block_on_pause)

def run_commands_agent(loop: int, task_txt: str = "") -> str:
    """
    The Commands Agent (jarvis-commands).
    Runs when the Coordinator sequences it or when explicitly triggered.
    Assesses the current toolbox for gaps, then decides whether to build
    a new tool. Only builds if there is genuine autonomous value.
    Feeds every candidate through submit_command_for_review().
    """
    ch_id = ch("commands")
    t = post(ch_id, f"🔧 *[Loop {loop}] Commands Agent scanning toolbox...*")

    # Read current registry for context
    registry_md = read_file(ws_path("commands/registry/COMMAND_REGISTRY.md"))
    gt = read_file(wsr("gt"))

    sys_p = f"""{_mission()}
You are the OpenJarvis Commands Agent (jarvis-commands).
Loop {loop}.

YOUR JOB:
Identify ONE tool that would significantly improve the autonomous operation
of the QCAI system. Build it only if it delivers genuine value — not trivia.

PROTECTED COMMANDS (you CANNOT create tools with these names):
{sorted(PROTECTED_COMMANDS)}

EXISTING AGENT TOOLS (do not duplicate):
{registry_md[-800:] if '[File not found' not in registry_md else '(none yet)'}

GROUND TRUTH / CONTEXT:
{gt[:600]}

TASK CONTEXT: {task_txt[:300]}

If you decide to build a tool, output EXACTLY this format:
COMMAND_TOOL: YES
TOOL_NAME: <name-with-hyphens>  (must not clash with protected list)
SCRIPT_NAME: cmd_<name_underscores>.sh  (or .py for Python tools)
DESCRIPTION: <one clear sentence — what it does and when to use it>
SCRIPT_TYPE: bash  (or python)
SCRIPT_CONTENT:
<complete script content — no truncation — starts with #!/usr/bin/env bash or #!/usr/bin/env python3>

If no tool is needed this loop, output:
COMMAND_TOOL: NO
REASON: <why no tool is needed>
"""
    user_msg = (f"CURRENT TOOLBOX:\n{registry_md[-600:]}\n\n"
                f"TASK:\n{task_txt[:400]}\n\n"
                f"WORKSPACE: {ws_name()} | Loop: {loop}")

    out = infer(sys_p, user_msg, temperature=0.20, max_tokens=3000)

    # Parse decision
    if not re.search(r"COMMAND_TOOL:\s*YES", out, re.IGNORECASE):
        reason_m = re.search(r"REASON:\s*(.+)", out)
        reason = reason_m.group(1).strip() if reason_m else "no tool needed this loop"
        if t.get("ts"):
            update(ch_id, t["ts"],
                   f"🔧 *[Loop {loop}] Commands Agent — no new tool*\n_{reason}_")
        return f"no tool: {reason}"

    # Extract tool spec
    name_m    = re.search(r"TOOL_NAME:\s*(\S+)",   out)
    sname_m   = re.search(r"SCRIPT_NAME:\s*(\S+)", out)
    desc_m    = re.search(r"DESCRIPTION:\s*(.+)",  out)
    type_m    = re.search(r"SCRIPT_TYPE:\s*(\S+)", out)
    content_m = re.search(r"SCRIPT_CONTENT:\n([\s\S]+)", out)

    if not all([name_m, sname_m, desc_m, content_m]):
        post(ch_id, f"⚠️ *[Loop {loop}] Commands Agent: output unparseable — skipping*\n"
                    f"```\n{out[:400]}\n```")
        return "parse error"

    tool_name   = name_m.group(1).strip()
    script_name = sname_m.group(1).strip()
    description = desc_m.group(1).strip()
    content     = content_m.group(1).strip()

    if t.get("ts"):
        update(ch_id, t["ts"],
               f"🔧 *[Loop {loop}] Commands Agent: proposing `{tool_name}`*\n"
               f"_{description}_\nPipeline: sandbox → tester → reviewer → install")

    result = submit_command_for_review(
        script_name=script_name,
        description=description,
        command=tool_name,
        content=content,
        created_by=f"commands_agent/loop_{loop}",
    )
    return result

def list_commands(show_protected: bool = True) -> str:
    """Return formatted string of all commands: protected + agent-created."""
    lines = []
    if show_protected:
        lines.append("*🔒 Protected system commands (cannot be overwritten):*")
        for cmd in sorted(PROTECTED_COMMANDS):
            lines.append(f"  `{cmd}`")
        lines.append("")

    lines.append("*🔧 Agent-created commands:*")
    json_path = os.path.join(COMMANDS_HOST_DIR, "registry", "commands.json")
    try:
        with open(json_path) as f:
            data = json.load(f)
        active = [c for c in data.get("commands", []) if c.get("status") == "active"]
        if active:
            for c in active:
                lines.append(f"  `{c['name']}` — {c.get('description','')[:60]}")
        else:
            lines.append("  (none yet — agents will create tools as needed)")
    except Exception:
        lines.append("  (registry not yet populated)")

    return "\n".join(lines)

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
        if agent_key == "commands":
            out = run_commands_agent(loop, task_txt)
        elif agent_key == "peig":
            # PEIG can be sequenced by Coordinator for explicit governance review
            out = run_peig_agent(
                loop=loop,
                decision=task_txt or ws_read("intake"),
                trigger_reason="coordinator-sequenced governance review",
                urgency="required",
                requesting_agent="coordinator",
                block_on_pause=True,
            ).get("report", "PEIG review complete")
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

    # ── SHOW COMMANDS / LIST COMMANDS ─────────────────────────────────────────
    if cmd in ("SHOW COMMANDS", "SHOW_COMMANDS", "LIST COMMANDS", "LIST_COMMANDS"):
        smart_post(ch_id, f"📜 *Commands — `{ws_name()}`*\n{list_commands()}", "list_commands")
        return True

    # ── PEIG — run governance oracle on any decision/question ────────────────
    # Usage: PEIG <decision or question>
    m_peig = re.match(r"(?:PEIG|ASK PEIG)\s+(.+)", cmd_raw.strip(), re.IGNORECASE)
    if m_peig:
        decision_text = m_peig.group(1).strip()
        post(ch_id, f"⚖️ *PEIG review starting...*\n`{decision_text[:200]}`")
        def _run_manual_peig():
            result = run_peig_agent(
                loop=state.loop_count,
                decision=decision_text,
                trigger_reason="manual invocation by Kevin",
                urgency="required",
                requesting_agent="human/kevin",
                block_on_pause=False,
            )
            post(ch_id,
                f"⚖️ *PEIG Manual Review Complete*\n"
                f"Verdict: *{result['verdict']}* | Tier: {result['tier']}\n"
                f"{'Escalate: ⚠️ YES' if result['escalate'] else ''}\n"
                f"See #jarvis-peig for full report.")
        threading.Thread(target=_run_manual_peig, daemon=True).start()
        return True

    # ── PEIG STATUS — show last PEIG reports ──────────────────────────────────
    if cmd in ("PEIG STATUS", "PEIG_STATUS"):
        ver_dir = ws_path("versions/peig")
        if not os.path.exists(ver_dir):
            post(ch_id, "⚖️ No PEIG reports yet for this workspace."); return True
        reports = sorted(os.listdir(ver_dir))[-3:]  # last 3
        if not reports:
            post(ch_id, "⚖️ No PEIG reports yet."); return True
        lines = [f"⚖️ *Last {len(reports)} PEIG Reports — `{ws_name()}`*"]
        for r in reports:
            rpath = os.path.join(ver_dir, r)
            try:
                with open(rpath) as f:
                    first_lines = "".join(f.readlines()[:4])
                lines.append(f"```\n{first_lines.strip()}\n```")
            except Exception:
                lines.append(f"  `{r}`")
        smart_post(ch_id, "\n".join(lines), "peig_status")
        return True

    # ── INSTALL COMMANDS — re-run install_host_commands.sh inside distrobox ───
    # Safe: protected commands cannot be overwritten by this; only wrappers refreshed.
    if cmd in ("INSTALL COMMANDS", "INSTALL_COMMANDS"):
        install_script = os.path.join(JARVIS_ROOT, "install_host_commands.sh")
        if not os.path.exists(install_script):
            post(ch_id, f"❌ `install_host_commands.sh` not found at `{install_script}`\n"
                        f"Run `qcai-update` to deploy it first.")
            return True
        post(ch_id,
             f"🔧 *Re-installing host commands...*\n"
             f"Running `install_host_commands.sh` inside distrobox...\n"
             f"_(This refreshes wrappers for all commands including new agent tools)_")
        def _do_install():
            try:
                import subprocess
                result = subprocess.run(
                    ["bash", install_script],
                    capture_output=True, text=True, timeout=60
                )
                out = result.stdout[-1500:] + (result.stderr[-500:] if result.stderr else "")
                post(ch_id,
                     f"✅ *Host commands installed*\n```\n{out}\n```" if result.returncode == 0
                     else f"⚠️ *Install finished with warnings*\n```\n{out}\n```")
            except Exception as e:
                post(ch_id, f"❌ Install error: {e}")
        threading.Thread(target=_do_install, daemon=True).start()
        return True

    # ── RUN COMMANDS AGENT — trigger the Commands Agent manually ──────────────
    if cmd in ("RUN COMMANDS AGENT", "RUN_COMMANDS_AGENT", "COMMANDS AGENT"):
        if state.running:
            post(ch_id, "⚠️ Loop running. Type `STOP` first, or let Coordinator sequence it.")
            return True
        post(ch_id, f"🔧 *Running Commands Agent manually* | WS: `{ws_name()}`")
        task_hint = cmd_raw.strip()
        threading.Thread(
            target=lambda: run_commands_agent(state.loop_count + 1, task_hint),
            daemon=True
        ).start()
        return True

    # ── SHOW COMMANDS (existing handler, now superseded — keep for compat) ────
    if cmd == "SHOW_COMMANDS_REGISTRY":
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
    # Only create stubs if the real script does not exist OR is too small
    # to be the real version (< 20 lines = stub). Never overwrite a real script.
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
        should_create = False
        if not os.path.exists(script_path):
            should_create = True
        else:
            try:
                with open(script_path) as f:
                    line_count = sum(1 for _ in f)
                if line_count < STUB_MIN_LINES:
                    should_create = True
                    log.info(f"{script_name} is a {line_count}-line stub — will recreate")
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

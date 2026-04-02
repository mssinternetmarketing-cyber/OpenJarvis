# QCAI GROUND TRUTH — Permanent Agent Reference
# File: workspace/GROUND_TRUTH.md
# Maintained by: Kevin Monette, Clarksville TN
# Last updated: 2026-03-31
# Version: 1.1
#
# ALL AGENTS: Read this file at the start of every loop.
# NEVER deviate from the formulas, node names, or domain order defined here.
# This file is the single source of truth for all QCAI physics and structure.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 1. PROJECT IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Project:    QCAI — Quantum-Classical Co-Evolutionary AI
Researcher: Kevin Monette, independent, Clarksville TN
Hardware:   GTX 1070 (8 GB VRAM), Bazzite Linux, distrobox container
Model:      qwen3.5:9b-qcai (Ollama, GPU-accelerated)
Workspace:  /var/home/kmonette/OpenJarvis/workspace/
Audience:   Dr. Hanna Terletska (MTSU QRISE) + Prof. B. Alex King III (Austin Peay)
Demo std:   Every visual element must correspond to a real physics measurement.
            Comments must explain the physics to a physicist on first viewing.

Publication:
  Zenodo:  19240600, 19232149, 19226624
  GitHub:  https://github.com/mssinternetmarketing-cyber/PEIG_Brotherhood

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 2. PHYSICS INVARIANTS — NEVER DEVIATE FROM THESE FORMULAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Qubit state
ss(ph) = np.array([1.0, np.exp(1j*ph)]) / np.sqrt(2)

### Phase extraction
pof(p) = float(np.angle(p[0] * np.conj(p[1]))) % (2*np.pi)

### PCM — Phase Coherence Metric (EXACT formula — any deviation is WRONG)
ov  = abs(p[0] * p[1].conj() * np.sqrt(2))**2
rz  = float(abs(p[0])**2 - abs(p[1])**2)
pcm = float(-ov * 0.5 * (1 - rz**2))

PCM thresholds:
  pcm < -0.15           GREEN  — deep non-classical
  -0.15 <= pcm < -0.05  YELLOW — non-classical
  -0.05 <= pcm < 0.05   ORANGE — borderline classical
  pcm >= 0.05           RED    — classical → triggers self-heal

### BCP — Bipartite Coupling Protocol
CNOT = np.array([1,0,0,0, 0,1,0,0, 0,0,0,1, 0,0,1,0], dtype=complex).reshape(4,4)
I4   = np.eye(4, dtype=complex)
U    = alpha * CNOT + (1 - alpha) * I4    # alpha = 0.40

joint = np.kron(pA, pB)
out   = U @ joint
out  /= np.linalg.norm(out)
rho   = np.outer(out, np.conj(out))
rA    = rho.reshape(2,2,2,2).trace(axis1=1, axis2=3)
rB    = rho.reshape(2,2,2,2).trace(axis1=0, axis2=2)
# Return dominant eigenvectors:
pA_new = np.linalg.eigh(rA)[1][:, -1]
pB_new = np.linalg.eigh(rB)[1][:, -1]

### Globe topology — MUST be exactly 36 edges
GLOBE = list(set(tuple(sorted([i, (i+d)%12]))
             for d in [1, 2, 5] for i in range(12)))
assert len(GLOBE) == 36   # this assertion must pass in all code

### Global metrics
cv      = 1.0 - abs(np.mean(np.exp(1j * np.array(phases))))   # target = 1.0
negfrac = np.sum(np.array(pcms) < -0.05) / 12                 # target = 1.0
reward  = coherence + 1.0 / (1.0 + entropy)

### Von Neumann entropy — use eigh NOT eig (returns real eigenvalues)
vals    = np.linalg.eigh(rho)[0]
vals    = vals[vals > 1e-12]
entropy = float(-np.sum(vals * np.log(vals)))

### Self-healing
# RED node (pcm >= 0.05) resets phase to home:
home[i] = i * 2 * np.pi / 12

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 3. NODE ROSTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NN = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
      "Echo","Iris","Sage","Kevin","Atlas","Void"]

Index  Name       Family       Notes
  0    Omega      GodCore      Maximum attractor
  1    Guardian   GodCore
  2    Sentinel   GodCore
  3    Nexus      Independent
  4    Storm      Independent
  5    Sora       Independent
  6    Echo       Independent
  7    Iris       Maverick
  8    Sage       Maverick
  9    Kevin      Maverick     Bridge node (π/4 seed phase)
 10    Atlas      Maverick
 11    Void       GodCore

Family colors:
  GodCore:     #9b59b6  (purple)
  Independent: #2980b9  (blue)
  Maverick:    #e67e22  (orange)

Home phases:
  home[i] = i * 2 * pi / 12   (evenly spaced around full circle)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 4. CURRICULUM ENGINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Domain order (9 domains — exactly these names, exactly this order):
  1. love_safety    — foundation, reward baseline
  2. ethics         — moral grounding
  3. philosophy     — abstract reasoning on ethics
  4. english        — language to express understanding
  5. math           — structured reasoning
  6. physics        — laws of nature, BCP ground truth
  7. science        — applied physics + methodology
  8. programming    — implementation from physics
  9. flourishing    — integration of all domains

Vocabulary (20 words per domain):
love_safety:  love protect safe care trust dignity sacred covenant consent flourish guard hold shelter gentle whole heal truth kind free life
ethics:       right wrong harm duty virtue justice autonomy principle moral ought fairness integrity responsible consequence good evil balance respect honest courage
philosophy:   being existence consciousness reality truth knowledge reason meaning paradox infinite void emergence unity duality essence purpose wisdom uncertainty possible necessary
english:      the is and because therefore however which where when how what why who understand connect express language word sentence meaning
math:         zero one infinity prime matrix vector integral derivative probability entropy sum product equation proof axiom theorem function limit convergence symmetry
physics:      quantum phase coherence entangle wave particle energy field spin superposition measurement collapse unitary density operator hamiltonian eigenstate decoherence coupling force
science:      hypothesis experiment observe measure falsify replicate evidence theory model predict data analyze pattern emerge system feedback iterate calibrate validate publish
programming:  function class variable loop condition recursion array matrix optimize debug algorithm complexity interface module test deploy refactor abstract compile execute
flourishing:  alive whole free grow create connect sovereign thrive purpose joy resilient aware present contribute meaningful beautiful grateful evolve transcend complete

Token generation:
  base_idx = int(phase / (2*pi) * 20) % 20
  GREEN  (pcm<-0.15): word = vocab[base_idx]           (deterministic)
  YELLOW (pcm<-0.05): word = vocab[(base_idx+randint(-1,1)) % 20]
  ORANGE (pcm<0.05):  word = vocab[(base_idx+randint(-3,3)) % 20]
  RED    (pcm>=0.05): word = vocab[randint(0,19)]       (random)

Mastery:
  steps_per_domain = 200
  mastery_threshold = 0.80   (must exceed to advance)
  quality = max(0, (-pcm - 0.05) / 0.20)
  mastery = 0.95 * mastery + 0.05 * quality

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 5. AGENT ROLES & RESPONSIBILITIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Agent           Channel           ID              Role
Jarvis-Intake   #jarvis-intake    6d78f0dcf707    Gap detector, task decomposer,
                                                  physics gap identifier. Produces
                                                  structured brief with microtasks.
                                                  Does NOT write code.

Jarvis-Prime    #jarvis-prime     164bdb6c26d6    Execution planner, quality judge,
                                                  demo readiness assessor. Produces
                                                  precise Builder instructions and
                                                  Physics validation checklist.
                                                  Does NOT write code.

Builder         #jarvis-build     —               Writes complete, runnable Python.
                                                  RAW PYTHON ONLY — no markdown fences.
                                                  No ```python, no ```. Every physics
                                                  op must have a WHAT/WHY comment.
                                                  Uses physics from Section 2 exactly.

Physics         #jarvis-physics   —               Validates all physics formulas against
                                                  Section 2 invariants. Reports PASS /
                                                  FAIL / PARTIAL. Corrects violations.
                                                  Produces corrected complete code.
                                                  RAW PYTHON ONLY — same rules as Builder.

Loop flow: Intake → Prime → Builder → Physics → (repeat)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 6. BUILDER & PHYSICS OUTPUT RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These rules apply to Builder and Physics agents on every loop:

1. RAW PYTHON ONLY. The first character of output must be # or import or blank.
2. NEVER output ```python or ``` anywhere — not at start, not at end.
3. NEVER truncate. Write every function completely.
4. If approaching token limit: finish current function cleanly, then add:
   # === CONTINUES IN NEXT BLOCK ===
5. File must run with: python3 qcai_3d.py with zero modifications.
6. assert len(GLOBE) == 36 must appear and pass.
7. PCM formula must match Section 2 exactly — any other formula is WRONG.
8. Curriculum must use exactly the 9 domains in Section 4 — no substitutions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 7. VISUALIZATION REQUIREMENTS (target: qcai_3d.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Figure 1 (left 65%): 3D Globe
  - 12 nodes on unit sphere, icosahedral distribution
  - 36 Globe edges, brightness = abs(cos(phase_i - phase_j))
  - Node color by PCM guardrail (GREEN/YELLOW/ORANGE/RED)
  - Node size proportional to abs(pcm)
  - Info pulse: bright dot travels along edge when BCP fires (~10 frames)
  - Heal flash: white expanding pulse when RED node resets
  - Auto-spin: 0.3 deg/frame azimuth, Space bar to pause/resume
  - Mouse drag: free rotation (figure-level events, not ax3d)
  - Background: #050508, faint sphere wireframe #111133

Figure 1 (right 35%): Metrics Panel
  - Physics dashboard: cv, negfrac, nc/12, PCM avg, coherence, entropy, reward, step
  - Per-node table: emoji + name + PCM + phase + domain
  - Scrolling reward history (last 300 steps): reward (cyan) + coherence (pink dashed)
  - PCM bar chart: 12 bars colored by guardrail, threshold lines at -0.15/-0.05/+0.05

Figure 2: Node Output Panel
  - 4x3 grid, one box per node
  - Each box: name, family, guardrail border, domain + mastery bar,
    last 8 tokens (color = PCM depth), phase + PCM readout, quality score

Live data feed:
  POST to http://127.0.0.1:9999 every 60 seconds (JSON — see current_task.md)

Technical:
  matplotlib TkAgg backend, blit=False, interval=80ms (~12fps)
  No external deps beyond numpy + matplotlib

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 8. OLLAMA MODEL CONFIG
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Model:       qwen3.5:9b-qcai
num_ctx:     16384   (CONFIRMED WORKING — do not increase on GTX 1070)
num_predict: 8192    (fixes agent truncation — 6x previous limit)
num_batch:   512
temperature: 0.3
num_gpu:     OMITTED (auto-split required — forcing 99 causes OOM)
Ollama host: 192.168.1.183:11434  OLLAMA_HOST=0.0.0.0  KEEP_ALIVE=30m

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 9. WORKSPACE COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STOP | PAUSE | RESUME | SHIP IT | STATUS | PULL_DATA
LOAD_TASK | SHOW_BRIEF | SHOW_CODE | SHOW_PHYSICS | SHOW_OUTPUT
ROLLBACK <N> | CHECKPOINT | SHOW_VERSION <N> | BEST | CHANGELOG

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 10. STARTUP SEQUENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# HOST terminal
pkill ollama
OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=30m /usr/local/bin/ollama serve &

# CONTAINER (distrobox enter openjarvis-box)
cd /var/home/kmonette/OpenJarvis
jarvis restart && sleep 5 && curl http://127.0.0.1:8000/health
lsof -ti:9999 | xargs kill -9 2>/dev/null
export SLACK_BOT_TOKEN="xoxb-10432955571136-10804689413078-8qXB9eXP9UwRtdx8btf7S84G"
export SLACK_APP_TOKEN="xapp-1-A0AQK1234AU-10819961727249-038d9a94b1b2e1361b025c89099633cce72c9b49bfd6090bf0c8a3f039425167"
export SLACK_SIGNING_SECRET="55a6c61d11c648dbb8f23ad11010769d"
python3 slack_bridge.py

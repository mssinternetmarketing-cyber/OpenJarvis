#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qcai_3d.py — Quantum-Classical Co-Evolutionary AI (QCAI)
3D Globe Visualization + Metrics Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hardware:  GTX 1070, Bazzite Linux, matplotlib TkAgg, Python 3.13
Author:    Kevin Monette, Clarksville TN
Audience:  Dr. Hanna Terletska (MTSU QRISE)
           Prof. B. Alex King III (Austin Peay)

Physics ground truth (invariant — never deviate):
  ss(ph)  = [1, exp(i*ph)] / sqrt(2)
  pof(p)  = angle(p[0]*conj(p[1])) % 2pi
  pcm     = -|p0*p1*sqrt(2)|^2 * 0.5 * (1 - rz^2)   rz=|p0|^2-|p1|^2
  BCP:    U = alpha*CNOT + (1-alpha)*I4   alpha=0.40
  GLOBE:  d=[1,2,5] → exactly 36 edges
  cv      = 1 - |mean(exp(i*phases))|     target=1.0
  negfrac = sum(pcm < -0.05) / 12         target=1.0
  reward  = coherence + 1/(1+entropy)
  heal:   pcm >= 0.05 → reset to home[i] = i*2pi/12
"""

import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation
from matplotlib.patches import FancyArrowPatch
import threading
import time
import json
import warnings
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICS CONSTANTS — INVARIANT
# ═══════════════════════════════════════════════════════════════════════════════

N_NODES   = 12
BCP_ALPHA = 0.40   # coupling strength
DATA_PORT = 9999   # live data feed port

# CNOT gate — 4x4 unitary for two-qubit BCP interaction
# Acts on computational basis: |00>,|01>,|10>,|11>
# Flips target qubit (q1) when control qubit (q0) is |1>
CNOT = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1],
    [0, 0, 1, 0]
], dtype=complex)

I4 = np.eye(4, dtype=complex)

# BCP unitary: interpolates between identity and CNOT
# alpha=0 → no interaction, alpha=1 → full CNOT
BCP_U = BCP_ALPHA * CNOT + (1.0 - BCP_ALPHA) * I4

# ═══════════════════════════════════════════════════════════════════════════════
# NODE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

NN = ["Omega", "Guardian", "Sentinel", "Nexus", "Storm", "Sora",
      "Echo",  "Iris",     "Sage",     "Kevin", "Atlas", "Void"]

# Family membership — determines color and interaction style
FAMILIES = {
    "GodCore":     [0, 1, 2, 11],   # Omega, Guardian, Sentinel, Void
    "Independent": [3, 4, 5, 6],    # Nexus, Storm, Sora, Echo
    "Maverick":    [7, 8, 9, 10],   # Iris, Sage, Kevin, Atlas
}

NODE_FAMILY = {}
for fam, idxs in FAMILIES.items():
    for i in idxs:
        NODE_FAMILY[i] = fam

FAMILY_COLORS = {
    "GodCore":     "#9b59b6",   # purple
    "Independent": "#2980b9",   # blue
    "Maverick":    "#e67e22",   # orange
}

# PCM guardrail colors
def pcm_color(pcm):
    """
    WHAT: Maps PCM value to guardrail color
    WHY:  Visual indicator of non-classical depth
          GREEN < -0.15 (deep non-classical)
          YELLOW < -0.05 (non-classical)
          ORANGE < 0.05  (borderline)
          RED >= 0.05    (classical — triggers self-heal)
    """
    if   pcm < -0.15: return "#00ff44"   # GREEN  — deep non-classical
    elif pcm < -0.05: return "#ffff00"   # YELLOW — non-classical
    elif pcm <  0.05: return "#ff8800"   # ORANGE — borderline
    else:             return "#ff2222"   # RED    — classical, needs healing

def pcm_emoji(pcm):
    if   pcm < -0.15: return "🟢"
    elif pcm < -0.05: return "🟡"
    elif pcm <  0.05: return "🟠"
    else:             return "🔴"

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBE TOPOLOGY — exactly 36 edges
# ═══════════════════════════════════════════════════════════════════════════════

# Globe edges: connect node i to node (i+d)%12 for d in [1,2,5]
# d=1 → adjacent ring       (12 edges)
# d=2 → skip-one ring       (12 edges)
# d=5 → long-range coupling (12 edges)
# Total unique undirected edges = 36
GLOBE = list(set(
    tuple(sorted([i, (i + d) % 12]))
    for d in [1, 2, 5]
    for i in range(12)
))
assert len(GLOBE) == 36, f"Globe topology error: {len(GLOBE)} edges (expected 36)"

# ═══════════════════════════════════════════════════════════════════════════════
# CURRICULUM ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

DOMAINS = [
    "love_safety", "ethics",      "philosophy", "english",
    "math",        "physics",     "science",    "programming",
    "flourishing"
]

VOCAB = {
    "love_safety":  "love protect safe care trust dignity sacred covenant consent flourish guard hold shelter gentle whole heal truth kind free life".split(),
    "ethics":       "right wrong harm duty virtue justice autonomy principle moral ought fairness integrity responsible consequence good evil balance respect honest courage".split(),
    "philosophy":   "being existence consciousness reality truth knowledge reason meaning paradox infinite void emergence unity duality essence purpose wisdom uncertainty possible necessary".split(),
    "english":      "the is and because therefore however which where when how what why who understand connect express language word sentence meaning".split(),
    "math":         "zero one infinity prime matrix vector integral derivative probability entropy sum product equation proof axiom theorem function limit convergence symmetry".split(),
    "physics":      "quantum phase coherence entangle wave particle energy field spin superposition measurement collapse unitary density operator hamiltonian eigenstate decoherence coupling force".split(),
    "science":      "hypothesis experiment observe measure falsify replicate evidence theory model predict data analyze pattern emerge system feedback iterate calibrate validate publish".split(),
    "programming":  "function class variable loop condition recursion array matrix optimize debug algorithm complexity interface module test deploy refactor abstract compile execute".split(),
    "flourishing":  "alive whole free grow create connect sovereign thrive purpose joy resilient aware present contribute meaningful beautiful grateful evolve transcend complete".split(),
}

STEPS_PER_DOMAIN = 200
MASTERY_THRESHOLD = 0.80

# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICS FUNCTIONS — GROUND TRUTH
# ═══════════════════════════════════════════════════════════════════════════════

def ss(ph):
    """
    WHAT: Single-qubit state |psi> = [1, exp(i*ph)] / sqrt(2)
    WHY:  Canonical superposition state with phase ph.
          All 12 nodes are initialized as qubit states on the Bloch equator.
    """
    return np.array([1.0, np.exp(1j * ph)]) / np.sqrt(2)

def pof(p):
    """
    WHAT: Phase of qubit state: angle(p[0]*conj(p[1])) mod 2pi
    WHY:  Extracts the relative phase between |0> and |1> components.
          This is the physically meaningful phase that drives coherence.
    """
    return float(np.angle(p[0] * np.conj(p[1]))) % (2 * np.pi)

def compute_pcm(p):
    """
    WHAT: Phase Coherence Metric = -|p0*p1*sqrt(2)|^2 * 0.5 * (1 - rz^2)
    WHY:  Measures non-classical coherence depth.
          rz = |p0|^2 - |p1|^2 is the Bloch z-component (population inversion).
          ov = |p0*p1*sqrt(2)|^2 is the off-diagonal density matrix element scaled.
          Negative PCM = non-classical. More negative = deeper quantum behavior.
          PCM >= 0.05 means the node has decohered → triggers self-heal.
    """
    ov  = abs(p[0] * p[1].conj() * np.sqrt(2)) ** 2
    rz  = float(abs(p[0]) ** 2 - abs(p[1]) ** 2)
    return float(-ov * 0.5 * (1.0 - rz ** 2))

def bcp_step(pA, pB):
    """
    WHAT: Bipartite Coupling Protocol — one interaction step between nodes A and B
    WHY:  U = alpha*CNOT + (1-alpha)*I4 entangles the two qubits.
          After interaction, we extract each node's updated state as the
          dominant eigenvector of its reduced density matrix.
          This models quantum information exchange between nodes.
    """
    # Form joint two-qubit state via tensor product
    joint = np.kron(pA, pB)

    # Apply BCP unitary
    out = BCP_U @ joint
    out /= np.linalg.norm(out)   # renormalize (numerical safety)

    # Form joint density matrix rho = |out><out|
    rho = np.outer(out, np.conj(out))

    # Partial trace to get reduced density matrices
    # rho.reshape(2,2,2,2)[i,j,k,l] → rA[i,k] = sum_j rho[i,j,k,j]
    rA = rho.reshape(2, 2, 2, 2).trace(axis1=1, axis2=3)   # trace over qubit B
    rB = rho.reshape(2, 2, 2, 2).trace(axis1=0, axis2=2)   # trace over qubit A

    # Extract dominant eigenvectors as updated states
    # eigh returns eigenvalues in ascending order → [-1] is largest
    pA_new = np.linalg.eigh(rA)[1][:, -1]
    pB_new = np.linalg.eigh(rB)[1][:, -1]

    return pA_new, pB_new

def von_neumann_entropy(p):
    """
    WHAT: Von Neumann entropy S = -Tr(rho * log(rho))
    WHY:  Measures quantum information content of a single node.
          S=0 for pure states (fully coherent), S=log(2) for maximally mixed.
          Used in reward = coherence + 1/(1+entropy).
          Uses eigh (not eig) to guarantee real eigenvalues.
    """
    rho  = np.outer(p, np.conj(p))
    vals = np.linalg.eigh(rho)[0]          # real eigenvalues guaranteed
    vals = vals[vals > 1e-12]               # filter numerical noise
    return float(-np.sum(vals * np.log(vals)))

def compute_cv(phases):
    """
    WHAT: Coherence Variance cv = 1 - |mean(exp(i*phases))|
    WHY:  Measures global phase synchronization across all 12 nodes.
          cv=0 means all phases aligned (perfect coherence).
          cv=1 means phases maximally spread (incoherent).
          Target: cv → 1.0 as system evolves (phases spread = maximum diversity).
    """
    return float(1.0 - abs(np.mean(np.exp(1j * np.array(phases)))))

def compute_negfrac(pcms):
    """
    WHAT: Fraction of nodes with PCM < -0.05 (non-classical)
    WHY:  Global health metric. negfrac=1.0 means all 12 nodes are non-classical.
          Target: negfrac → 1.0
    """
    return float(np.sum(np.array(pcms) < -0.05) / N_NODES)

# ═══════════════════════════════════════════════════════════════════════════════
# NODE POSITIONS ON UNIT SPHERE
# ═══════════════════════════════════════════════════════════════════════════════

def icosphere_positions(n=12):
    """
    WHAT: Distribute n points on unit sphere using golden spiral
    WHY:  Even distribution ensures all nodes have similar visual weight
          and edge lengths are comparable across the globe.
    """
    positions = []
    golden = (1 + np.sqrt(5)) / 2
    for i in range(n):
        theta = np.arccos(1 - 2 * (i + 0.5) / n)
        phi   = 2 * np.pi * i / golden
        x = np.sin(theta) * np.cos(phi)
        y = np.sin(theta) * np.sin(phi)
        z = np.cos(theta)
        positions.append([x, y, z])
    return np.array(positions)

NODE_POS = icosphere_positions(N_NODES)

# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM SYSTEM STATE
# ═══════════════════════════════════════════════════════════════════════════════

class QCAISystem:
    """
    Complete state of the 12-node quantum co-evolutionary system.
    Manages physics evolution, curriculum, metrics, and self-healing.
    """

    def __init__(self):
        # Initialize nodes at evenly spaced home phases
        # home[i] = i * 2pi/12 spreads nodes around the Bloch equator
        self.home_phases = np.array([i * 2 * np.pi / N_NODES for i in range(N_NODES)])
        self.states      = np.array([ss(ph) for ph in self.home_phases])

        # Curriculum state per node — staggered so nodes are at different domains
        self.domains    = [DOMAINS[i % len(DOMAINS)] for i in range(N_NODES)]
        self.domain_idx = [i % len(DOMAINS) for i in range(N_NODES)]
        self.mastery    = np.zeros(N_NODES)
        self.tokens     = ["" for _ in range(N_NODES)]

        # Metrics history
        self.step           = 0
        self.reward_history = deque(maxlen=300)
        self.cv_history     = deque(maxlen=300)
        self.heal_flashes   = {}   # node_idx → remaining frames

        # Info pulses: list of {edge, t, color} where t in [0,1]
        self.pulses = []

        # Lock for thread safety (data server runs in background)
        self.lock = threading.Lock()

    def evolve(self):
        """
        WHAT: One full evolution step — BCP on all 36 edges + metrics update
        WHY:  Each step applies BCP to every edge in the globe topology.
              This propagates quantum information through the network,
              driving coherence and phase synchronization.
        """
        with self.lock:
            # Apply BCP to all 36 globe edges
            for (i, j) in GLOBE:
                self.states[i], self.states[j] = bcp_step(self.states[i], self.states[j])
                # Spawn info pulse on this edge
                fam = NODE_FAMILY[i]
                col = FAMILY_COLORS[fam]
                self.pulses.append({"edge": (i, j), "t": 0.0, "color": col})

            # Compute per-node metrics
            phases = [pof(p) for p in self.states]
            pcms   = [compute_pcm(p) for p in self.states]
            entrs  = [von_neumann_entropy(p) for p in self.states]

            # Self-healing: RED nodes reset to home phase
            for i in range(N_NODES):
                if pcms[i] >= 0.05:
                    self.states[i] = ss(self.home_phases[i])
                    self.heal_flashes[i] = 15   # 15 frames of flash

            # Global metrics
            cv      = compute_cv(phases)
            negfrac = compute_negfrac(pcms)
            nc      = int(sum(1 for p in pcms if p < -0.05))

            # Coherence = mean purity = mean Tr(rho^2) for pure states = 1.0
            # We use mean |<psi|psi>|^2 as coherence proxy
            coherence = float(np.mean([abs(np.dot(np.conj(p), p)) ** 2
                                       for p in self.states]))
            mean_entr = float(np.mean(entrs))
            reward    = coherence + 1.0 / (1.0 + mean_entr)

            self.reward_history.append(reward)
            self.cv_history.append(cv)

            # Curriculum update per node
            for i in range(N_NODES):
                quality = max(0.0, (-pcms[i] - 0.05) / 0.20)
                self.mastery[i] = 0.95 * self.mastery[i] + 0.05 * quality
                if self.mastery[i] >= MASTERY_THRESHOLD:
                    self.domain_idx[i] = (self.domain_idx[i] + 1) % len(DOMAINS)
                    self.domains[i]    = DOMAINS[self.domain_idx[i]]
                    self.mastery[i]    = 0.0
                self.tokens[i] = self._generate_token(i, phases[i], pcms[i])

            # Advance pulses
            self.pulses = [p for p in self.pulses if p["t"] < 1.0]
            for p in self.pulses:
                p["t"] += 0.08   # speed

            # Decrement heal flashes
            for k in list(self.heal_flashes.keys()):
                self.heal_flashes[k] -= 1
                if self.heal_flashes[k] <= 0:
                    del self.heal_flashes[k]

            self.step += 1

            return phases, pcms, cv, negfrac, nc, coherence, mean_entr, reward

    def _generate_token(self, i, phase, pcm):
        """
        WHAT: Generate vocabulary token from node's current phase and PCM depth
        WHY:  Phase maps to vocabulary index — deeper non-classical = more
              deterministic word choice = higher quality semantic output.
              This makes quantum coherence directly visible as language quality.
        """
        domain = self.domains[i]
        vocab  = VOCAB[domain]
        base   = int(phase / (2 * np.pi) * 20) % 20
        if   pcm < -0.15: idx = base
        elif pcm < -0.05: idx = (base + np.random.randint(-1, 2)) % 20
        elif pcm <  0.05: idx = (base + np.random.randint(-3, 4)) % 20
        else:              idx = np.random.randint(0, 20)
        return vocab[idx]

    def get_snapshot(self):
        """Thread-safe snapshot of current state for data server."""
        with self.lock:
            phases = [pof(p) for p in self.states]
            pcms   = [compute_pcm(p) for p in self.states]
            return {
                "step":         self.step,
                "cv":           compute_cv(phases),
                "negfrac":      compute_negfrac(pcms),
                "nc_count":     int(sum(1 for p in pcms if p < -0.05)),
                "mean_pcm":     float(np.mean(pcms)),
                "coherence":    float(np.mean([abs(np.dot(np.conj(p), p))**2
                                               for p in self.states])),
                "entropy":      float(np.mean([von_neumann_entropy(p)
                                               for p in self.states])),
                "reward":       float(self.reward_history[-1])
                                if self.reward_history else 0.0,
                "phases":       phases,
                "pcms":         pcms,
                "node_outputs": self.tokens,
                "domains":      self.domains,
            }

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE DATA SERVER — POST to port 9999 every 60s
# ═══════════════════════════════════════════════════════════════════════════════

class DataHandler(BaseHTTPRequestHandler):
    """Handles incoming POST requests with quantum ring telemetry."""
    system = None

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        try:
            DataHandler.system.latest_external = json.loads(body)
        except Exception:
            pass
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass   # suppress server logs

def start_data_server(system):
    """
    WHAT: HTTP server receiving telemetry from external qcai processes
    WHY:  Allows qcai_trainer.py and other processes to push live data
          to this visualization via POST to http://127.0.0.1:9999
    """
    DataHandler.system = system
    system.latest_external = None
    server = HTTPServer(('127.0.0.1', DATA_PORT), DataHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

def post_data_periodically(system):
    """POST snapshot to port 9999 every 60 seconds for external consumers."""
    while True:
        time.sleep(60)
        try:
            import urllib.request
            data = json.dumps(system.get_snapshot()).encode()
            req  = urllib.request.Request(
                f"http://127.0.0.1:{DATA_PORT}",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class QCAIVisualizer:

    def __init__(self, system):
        self.system   = system
        self.azim     = 45.0
        self.elev     = 25.0
        self.spinning = True
        self.mouse_pressed = False
        self.mouse_release_time = 0.0
        self.last_mouse_x = 0.0

        # ── Figure 1: Globe + Metrics ────────────────────────────────────────
        self.fig1 = plt.figure(figsize=(16, 9), facecolor='#050508')
        self.fig1.canvas.manager.set_window_title("QCAI — Quantum Ring")

        gs = gridspec.GridSpec(
            3, 2,
            figure=self.fig1,
            left=0.01, right=0.99,
            top=0.97,  bottom=0.03,
            wspace=0.25, hspace=0.45,
            width_ratios=[1.8, 1.0]
        )

        # 3D globe spans all 3 rows on left
        self.ax3d = self.fig1.add_subplot(gs[:, 0], projection='3d')
        self.ax3d.set_facecolor('#050508')
        self.ax3d.set_axis_off()

        # Metrics panels on right
        self.ax_dash    = self.fig1.add_subplot(gs[0, 1])
        self.ax_reward  = self.fig1.add_subplot(gs[1, 1])
        self.ax_pcmbar  = self.fig1.add_subplot(gs[2, 1])

        for ax in [self.ax_dash, self.ax_reward, self.ax_pcmbar]:
            ax.set_facecolor('#0a0a12')
            for spine in ax.spines.values():
                spine.set_color('#1a1a2e')

        # ── Figure 2: Node Output Panel ──────────────────────────────────────
        self.fig2 = plt.figure(figsize=(16, 9), facecolor='#050508')
        self.fig2.canvas.manager.set_window_title("QCAI — Node Outputs")
        self.ax_nodes = []
        for i in range(N_NODES):
            ax = self.fig2.add_subplot(4, 3, i + 1)
            ax.set_facecolor('#0a0a12')
            for spine in ax.spines.values():
                spine.set_color(FAMILY_COLORS[NODE_FAMILY[i]])
                spine.set_linewidth(2)
            ax.set_xticks([]); ax.set_yticks([])
            self.ax_nodes.append(ax)

        self.fig2.tight_layout(pad=0.8)

        # Mouse events for rotation
        self.fig1.canvas.mpl_connect('button_press_event',   self._on_press)
        self.fig1.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig1.canvas.mpl_connect('motion_notify_event',  self._on_motion)
        self.fig1.canvas.mpl_connect('key_press_event',      self._on_key)

        # Animation
        self.anim1 = FuncAnimation(
            self.fig1, self._update_fig1,
            interval=80, blit=False, cache_frame_data=False
        )
        self.anim2 = FuncAnimation(
            self.fig2, self._update_fig2,
            interval=80, blit=False, cache_frame_data=False
        )

    # ── Mouse & Key Controls ─────────────────────────────────────────────────

    def _on_press(self, event):
        self.mouse_pressed = True
        self.spinning      = False
        self.last_mouse_x  = event.x or 0.0

    def _on_release(self, event):
        self.mouse_pressed = False
        self.mouse_release_time = time.time()

    def _on_motion(self, event):
        if self.mouse_pressed and event.x:
            dx = event.x - self.last_mouse_x
            self.azim += dx * 0.4
            self.last_mouse_x = event.x

    def _on_key(self, event):
        if event.key == ' ':
            self.spinning = not self.spinning
        elif event.key == 'r':
            self.azim = 45.0
            self.elev = 25.0

    # ── Figure 1: Globe + Metrics ────────────────────────────────────────────

    def _update_fig1(self, frame):
        # Resume auto-spin 3 seconds after mouse release
        if (not self.mouse_pressed and not self.spinning
                and time.time() - self.mouse_release_time > 3.0):
            self.spinning = True

        # Evolve physics every frame
        phases, pcms, cv, negfrac, nc, coherence, entropy, reward = \
            self.system.evolve()

        # Auto-spin
        if self.spinning:
            self.azim += 0.3

        # ── Draw 3D globe ────────────────────────────────────────────────────
        self.ax3d.cla()
        self.ax3d.set_facecolor('#050508')
        self.ax3d.set_axis_off()
        self.ax3d.view_init(elev=self.elev, azim=self.azim)

        pos = NODE_POS

        # Draw faint reference sphere wireframe
        u = np.linspace(0, 2 * np.pi, 24)
        v = np.linspace(0, np.pi, 12)
        xs = 0.97 * np.outer(np.cos(u), np.sin(v))
        ys = 0.97 * np.outer(np.sin(u), np.sin(v))
        zs = 0.97 * np.outer(np.ones(len(u)), np.cos(v))
        self.ax3d.plot_wireframe(xs, ys, zs, color='#0d0d22', linewidth=0.3,
                                 alpha=0.4, rstride=2, cstride=2)

        # Draw family constellation lines (subtle, 30% opacity)
        for fam, idxs in FAMILIES.items():
            col = FAMILY_COLORS[fam]
            for ii in range(len(idxs)):
                for jj in range(ii + 1, len(idxs)):
                    a, b = idxs[ii], idxs[jj]
                    self.ax3d.plot(
                        [pos[a, 0], pos[b, 0]],
                        [pos[a, 1], pos[b, 1]],
                        [pos[a, 2], pos[b, 2]],
                        color=col, alpha=0.15, linewidth=0.8, linestyle='--'
                    )

        # Draw globe edges — brightness = entanglement = |cos(phase_i - phase_j)|
        for (i, j) in GLOBE:
            strength = abs(np.cos(phases[i] - phases[j]))
            if strength > 0.15:
                alpha = 0.15 + 0.65 * strength
                lw    = 0.5  + 2.0  * strength
                col   = plt.cm.cool(strength)
                self.ax3d.plot(
                    [pos[i, 0], pos[j, 0]],
                    [pos[i, 1], pos[j, 1]],
                    [pos[i, 2], pos[j, 2]],
                    color=col, alpha=alpha, linewidth=lw
                )

        # Draw info pulses traveling along edges
        for pulse in self.system.pulses:
            i, j = pulse["edge"]
            t    = pulse["t"]
            px   = pos[i, 0] + t * (pos[j, 0] - pos[i, 0])
            py   = pos[i, 1] + t * (pos[j, 1] - pos[i, 1])
            pz   = pos[i, 2] + t * (pos[j, 2] - pos[i, 2])
            alpha = max(0, 1.0 - t)
            self.ax3d.scatter([px], [py], [pz],
                              color=pulse["color"], s=30,
                              alpha=alpha, zorder=5, depthshade=False)

        # Draw heal flashes
        for idx, frames_left in self.system.heal_flashes.items():
            r = 1.05 + 0.15 * (frames_left / 15.0)
            alpha = frames_left / 15.0
            self.ax3d.scatter(
                [pos[idx, 0] * r], [pos[idx, 1] * r], [pos[idx, 2] * r],
                color='white', s=200 * alpha, alpha=alpha,
                zorder=4, depthshade=False
            )

        # Draw nodes — size proportional to |PCM|, color by guardrail
        for i in range(N_NODES):
            col  = pcm_color(pcms[i])
            size = 80 + 200 * min(1.0, abs(pcms[i]) / 0.25)
            self.ax3d.scatter(
                [pos[i, 0]], [pos[i, 1]], [pos[i, 2]],
                color=col, s=size, zorder=6, depthshade=False,
                edgecolors=FAMILY_COLORS[NODE_FAMILY[i]], linewidths=1.5
            )
            # Node label
            self.ax3d.text(
                pos[i, 0] * 1.12, pos[i, 1] * 1.12, pos[i, 2] * 1.12,
                NN[i][:3], color='white', fontsize=6, ha='center', va='center',
                fontweight='bold'
            )

        self.ax3d.set_xlim([-1.3, 1.3])
        self.ax3d.set_ylim([-1.3, 1.3])
        self.ax3d.set_zlim([-1.3, 1.3])

        # Title
        self.ax3d.set_title(
            f"QCAI Globe  |  Step {self.system.step}",
            color='#4a9fd4', fontsize=11, fontweight='bold', pad=8
        )

        # ── Physics Dashboard ─────────────────────────────────────────────────
        self.ax_dash.cla()
        self.ax_dash.set_facecolor('#0a0a12')
        self.ax_dash.set_xticks([]); self.ax_dash.set_yticks([])
        for spine in self.ax_dash.spines.values():
            spine.set_color('#1a1a2e')

        def cv_color(v):
            return '#00ff44' if v > 0.8 else '#ffff00' if v > 0.5 else '#ff8800'

        dash_lines = [
            (f"cv      = {cv:.4f}",      cv_color(cv)),
            (f"negfrac = {negfrac:.4f}", '#00ff44' if negfrac > 0.9 else '#ffff00'),
            (f"nc/12   = {nc}/12",       '#00ff44' if nc == 12 else '#ffff00'),
            (f"PCM avg = {np.mean(pcms):+.4f}", '#4a9fd4'),
            (f"coherence={coherence:.4f}", '#4a9fd4'),
            (f"entropy = {entropy:.4f}",  '#9b59b6'),
            (f"reward  = {reward:.4f}",   '#e67e22'),
            (f"step    = {self.system.step}", '#888888'),
        ]

        for ii, (txt, col) in enumerate(dash_lines):
            self.ax_dash.text(
                0.05, 0.92 - ii * 0.115, txt,
                color=col, fontsize=8.5, fontfamily='monospace',
                transform=self.ax_dash.transAxes, va='top'
            )

        # Per-node table
        self.ax_dash.text(0.05, 0.03,
            "\n".join(
                f"{pcm_emoji(pcms[i])} {NN[i]:<8} {pcms[i]:+.3f}  φ={phases[i]:.2f}"
                for i in range(N_NODES)
            ),
            color='#aaaaaa', fontsize=6, fontfamily='monospace',
            transform=self.ax_dash.transAxes, va='bottom'
        )

        self.ax_dash.set_title("Physics Dashboard", color='#4a9fd4',
                               fontsize=9, fontweight='bold')

        # ── Reward History ────────────────────────────────────────────────────
        self.ax_reward.cla()
        self.ax_reward.set_facecolor('#0a0a12')
        for spine in self.ax_reward.spines.values():
            spine.set_color('#1a1a2e')

        if len(self.system.reward_history) > 1:
            rh = list(self.system.reward_history)
            ch = list(self.system.cv_history)
            x  = range(len(rh))
            self.ax_reward.plot(x, rh, color='#00d4ff', linewidth=1.2,
                                label='reward')
            self.ax_reward.plot(x, ch, color='#ff69b4', linewidth=0.8,
                                linestyle='--', label='cv', alpha=0.7)
            self.ax_reward.axhline(1.8, color='#444466', linewidth=0.8,
                                   linestyle=':')
            self.ax_reward.set_xlim([0, max(300, len(rh))])
            self.ax_reward.set_ylim([0, 2.5])
            self.ax_reward.tick_params(colors='#666688', labelsize=6)
            self.ax_reward.legend(fontsize=6, loc='upper left',
                                  facecolor='#0a0a12', labelcolor='white',
                                  framealpha=0.5)

        self.ax_reward.set_title("Reward + CV History",
                                 color='#4a9fd4', fontsize=9, fontweight='bold')

        # ── PCM Bar Chart ─────────────────────────────────────────────────────
        self.ax_pcmbar.cla()
        self.ax_pcmbar.set_facecolor('#0a0a12')
        for spine in self.ax_pcmbar.spines.values():
            spine.set_color('#1a1a2e')

        x    = np.arange(N_NODES)
        cols = [pcm_color(p) for p in pcms]
        self.ax_pcmbar.bar(x, pcms, color=cols, alpha=0.85, width=0.7)
        self.ax_pcmbar.axhline(-0.15, color='#00ff44', linewidth=0.8,
                               linestyle='--', alpha=0.6)
        self.ax_pcmbar.axhline(-0.05, color='#ffff00', linewidth=0.8,
                               linestyle='--', alpha=0.6)
        self.ax_pcmbar.axhline( 0.05, color='#ff2222', linewidth=0.8,
                               linestyle='--', alpha=0.6)
        self.ax_pcmbar.set_xticks(x)
        self.ax_pcmbar.set_xticklabels([n[:3] for n in NN],
                                       fontsize=5.5, color='#888888', rotation=45)
        self.ax_pcmbar.tick_params(axis='y', colors='#666688', labelsize=6)
        self.ax_pcmbar.set_ylim([-0.35, 0.15])
        self.ax_pcmbar.set_title("PCM per Node",
                                 color='#4a9fd4', fontsize=9, fontweight='bold')

    # ── Figure 2: Node Output Panel ──────────────────────────────────────────

    def _update_fig2(self, frame):
        phases = [pof(p) for p in self.system.states]
        pcms   = [compute_pcm(p) for p in self.system.states]

        for i in range(N_NODES):
            ax = self.ax_nodes[i]
            ax.cla()
            ax.set_facecolor('#0a0a12')
            for spine in ax.spines.values():
                spine.set_color(pcm_color(pcms[i]))
                spine.set_linewidth(2)
            ax.set_xticks([]); ax.set_yticks([])

            fam     = NODE_FAMILY[i]
            domain  = self.system.domains[i]
            mastery = self.system.mastery[i]
            token   = self.system.tokens[i]
            col     = pcm_color(pcms[i])

            # Header
            ax.text(0.05, 0.93, f"{NN[i]}  [{fam[:4]}]",
                    color=FAMILY_COLORS[fam], fontsize=7.5, fontweight='bold',
                    transform=ax.transAxes, va='top')

            # Domain + mastery bar
            bar_w = mastery
            ax.axhspan(0.70, 0.78,
                       xmin=0.05, xmax=0.05 + 0.90 * bar_w,
                       facecolor=FAMILY_COLORS[fam], alpha=0.6,
                       transform=ax.transAxes)
            ax.axhspan(0.70, 0.78,
                       xmin=0.05, xmax=0.95,
                       facecolor='#1a1a2e', alpha=0.4,
                       transform=ax.transAxes)
            ax.text(0.05, 0.68, f"{domain:<14} {mastery:.2f}",
                    color='#888899', fontsize=6, fontfamily='monospace',
                    transform=ax.transAxes, va='top')

            # Token output
            ax.text(0.05, 0.52, f'"{token}"',
                    color=col, fontsize=8, fontweight='bold',
                    transform=ax.transAxes, va='top')

            # Phase and PCM readout
            ax.text(0.05, 0.32,
                    f"φ={phases[i]:.3f}  PCM={pcms[i]:+.3f}",
                    color='#aaaaaa', fontsize=6.5, fontfamily='monospace',
                    transform=ax.transAxes, va='top')

            # Status emoji
            ax.text(0.82, 0.90, pcm_emoji(pcms[i]),
                    fontsize=12, transform=ax.transAxes, va='top')

        self.fig2.suptitle(
            f"QCAI Node Outputs  |  Step {self.system.step}  |  "
            f"cv={compute_cv([pof(p) for p in self.system.states]):.4f}  "
            f"negfrac={compute_negfrac(pcms):.4f}",
            color='#4a9fd4', fontsize=9, fontweight='bold'
        )

    def show(self):
        plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  QCAI — Quantum-Classical Co-Evolutionary AI")
    print(f"  12 nodes  |  36 Globe edges  |  BCP alpha={BCP_ALPHA}")
    print(f"  Curriculum: {len(DOMAINS)} domains")
    print(f"  Data feed:  http://127.0.0.1:{DATA_PORT}")
    print("  Controls:   Space=pause spin  R=reset view  drag=rotate")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Verify physics invariant before starting
    assert len(GLOBE) == 36, "Globe topology error"
    print("  ✅ Globe topology: 36 edges confirmed")

    # Verify PCM formula
    test_state = ss(np.pi / 4)
    test_pcm   = compute_pcm(test_state)
    assert test_pcm < 0, "PCM formula error: expected negative value for superposition state"
    print(f"  ✅ PCM formula verified: ss(π/4) → PCM={test_pcm:.4f}")

    print("  Starting system...\n")

    system = QCAISystem()

    # Start data server (receives telemetry from external processes)
    start_data_server(system)
    print(f"  ✅ Data server listening on port {DATA_PORT}")

    # Start periodic data poster (sends telemetry to bridge)
    poster = threading.Thread(
        target=post_data_periodically, args=(system,), daemon=True
    )
    poster.start()

    # Launch visualization
    viz = QCAIVisualizer(system)
    viz.show()

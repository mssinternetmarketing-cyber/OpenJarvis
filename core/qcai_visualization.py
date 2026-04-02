#!/usr/bin/env python3
"""
QCAI Quantum Ring Visualization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Live demo of the Quantum-Classical Co-Evolutionary AI system.
12 nodes in Globe topology with real BCP physics, PCM metrics,
self-healing animation, and reward signal tracking.

Author: Kevin Monette — Independent Researcher
For demonstration at MTSU QRISE Center and Austin Peay State University

Requirements: numpy, matplotlib
    pip install numpy matplotlib
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyArrowPatch
from collections import deque

# ─── Node Configuration ───────────────────────────────────────────────────────

NN = ["Omega", "Guardian", "Sentinel", "Nexus", "Storm", "Sora",
      "Echo", "Iris", "Sage", "Kevin", "Atlas", "Void"]
N = len(NN)

FAMILY = {
    "Omega": "GodCore",   "Guardian": "GodCore",
    "Sentinel": "GodCore","Void": "GodCore",
    "Nexus": "Independent","Storm": "Independent",
    "Sora": "Independent", "Echo": "Independent",
    "Iris": "Maverick",    "Sage": "Maverick",
    "Kevin": "Maverick",   "Atlas": "Maverick",
}

FAMILY_COLORS = {
    "GodCore":     "#9b59b6",   # purple
    "Independent": "#2980b9",   # blue
    "Maverick":    "#e67e22",   # orange
}

# ─── Globe Topology (36 edges) ────────────────────────────────────────────────

GLOBE = list(set(tuple(sorted([i, (i + d) % N]))
             for d in [1, 2, 5] for i in range(N)))
assert len(GLOBE) == 36, f"Expected 36 edges, got {len(GLOBE)}"

# ─── Quantum Physics Primitives ───────────────────────────────────────────────

ALPHA = 0.40    # BCP coupling strength
NOISE = 0.03    # depolarization noise per step

# CNOT gate (4x4 matrix on 2-qubit space)
CNOT = np.array([1,0,0,0, 0,1,0,0, 0,0,0,1, 0,0,1,0],
                dtype=complex).reshape(4, 4)
I4   = np.eye(4, dtype=complex)

def ss(ph):
    """Create normalized qubit state at phase ph."""
    return np.array([1.0, np.exp(1j * ph)]) / np.sqrt(2)

def pof(p):
    """Phase of qubit state p."""
    return float(np.angle(p[0] * np.conj(p[1]))) % (2 * np.pi)

def pcm_val(p):
    """
    Phase Coherence Metric — measures non-classical correlations.
    Returns negative values for non-classical regime.
    Target: PCM < -0.05 (non-classical), ideally < -0.15 (deep green)
    """
    ov  = abs(p[0] * p[1].conj() * np.sqrt(2)) ** 2
    rz  = float(abs(p[0]) ** 2 - abs(p[1]) ** 2)
    return float(-ov * 0.5 * (1 - rz ** 2))

def depol(p, noise=NOISE):
    """Apply depolarization noise — occasionally randomize phase."""
    if np.random.random() < noise:
        return ss(np.random.uniform(0, 2 * np.pi))
    return p

def bcp(pA, pB, alpha=ALPHA):
    """
    Bipartite Coupling Protocol — core quantum operation.
    U = alpha*CNOT + (1-alpha)*I  (partial entanglement)
    Returns updated reduced states for each qubit via partial trace.
    """
    U    = alpha * CNOT + (1 - alpha) * I4
    j    = np.kron(pA, pB)
    o    = U @ j
    o   /= np.linalg.norm(o)
    rho  = np.outer(o, o.conj())
    rA   = rho.reshape(2, 2, 2, 2).trace(axis1=1, axis2=3)
    rB   = rho.reshape(2, 2, 2, 2).trace(axis1=0, axis2=2)
    return np.linalg.eigh(rA)[1][:, -1], np.linalg.eigh(rB)[1][:, -1]

# ─── Guardrail Status ─────────────────────────────────────────────────────────

def guardrail_color(pcm):
    """Map PCM value to RGBA color for visualization."""
    if   pcm < -0.15: return (0.0, 0.9, 0.2, 1.0)   # GREEN  — deep non-classical
    elif pcm < -0.05: return (0.9, 0.9, 0.0, 1.0)   # YELLOW — non-classical
    elif pcm <  0.05: return (1.0, 0.5, 0.0, 1.0)   # ORANGE — borderline
    else:             return (1.0, 0.1, 0.1, 1.0)   # RED    — classical, needs healing

def guardrail_label(pcm):
    if   pcm < -0.15: return "GREEN"
    elif pcm < -0.05: return "YELLOW"
    elif pcm <  0.05: return "ORANGE"
    else:             return "RED"

# ─── Quantum Ring ─────────────────────────────────────────────────────────────

class QuantumRing:
    def __init__(self):
        # Initialize nodes at home phases (evenly distributed around ring)
        self.home   = [i * 2 * np.pi / N for i in range(N)]
        self.states = [ss(self.home[i]) for i in range(N)]
        self.heal_flash = [0] * N      # flash counter for self-healing animation
        self.step_count = 0

    def step(self):
        """One BCP step — apply coupling across all 36 Globe edges."""
        import math
        phib = [pof(s) for s in self.states]
        new  = list(self.states)

        for (i, j) in GLOBE:
            new[i], new[j] = bcp(new[i], new[j], ALPHA)

        new = [depol(s, NOISE) for s in new]

        # Co-rotation correction (removes global phase drift)
        phia = [pof(new[k]) for k in range(N)]
        dels = [(phia[k] - phib[k] + math.pi) % (2 * math.pi) - math.pi
                for k in range(N)]
        om   = float(np.mean(dels))
        self.states = [ss((phia[k] - dels[k] - om) % (2 * math.pi))
                       for k in range(N)]

        # Self-healing: reset RED nodes back to home phase
        for i in range(N):
            if pcm_val(self.states[i]) >= 0.05:   # RED threshold
                self.states[i]    = ss(self.home[i])
                self.heal_flash[i] = 8             # flash for 8 frames

        # Decrement flash counters
        self.heal_flash = [max(0, f - 1) for f in self.heal_flash]
        self.step_count += 1

    def metrics(self):
        """Compute all key quantum metrics."""
        phases   = [pof(s)     for s in self.states]
        pcms     = [pcm_val(s) for s in self.states]
        cv       = float(1.0 - abs(np.exp(1j * np.array(phases)).mean()))
        negfrac  = sum(1 for p in pcms if p < -0.05) / N
        nc_count = sum(1 for p in pcms if p < -0.05)
        mean_pcm = float(np.mean(pcms))

        # Coherence for reward signal
        coherence = float(abs(np.exp(1j * np.array(phases)).mean()))

        # Von Neumann entropy (simplified from phase distribution)
        probs = (np.array(phases) / (2 * np.pi))
        probs = probs / probs.sum() + 1e-10
        entropy = float(-np.sum(probs * np.log(probs)))

        # Reward signal: R = coherence + 1/(1+entropy)
        reward = coherence + 1.0 / (1.0 + entropy)

        return {
            "phases":   phases,
            "pcms":     pcms,
            "cv":       cv,
            "negfrac":  negfrac,
            "nc_count": nc_count,
            "mean_pcm": mean_pcm,
            "coherence":coherence,
            "entropy":  entropy,
            "reward":   reward,
        }

    def edge_strength(self, i, j):
        """Entanglement strength between two nodes (for edge brightness)."""
        pi = pof(self.states[i])
        pj = pof(self.states[j])
        return float(abs(np.cos(pi - pj)))

# ─── Node Positions (circular layout) ────────────────────────────────────────

angles   = [2 * np.pi * i / N - np.pi / 2 for i in range(N)]
node_pos = [(np.cos(a), np.sin(a)) for a in angles]

# ─── Set Up Figure ────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(16, 9), facecolor="#0a0a0f")
fig.suptitle("QCAI — Quantum-Classical Co-Evolutionary AI",
             color="white", fontsize=14, fontweight="bold", y=0.98)

gs = gridspec.GridSpec(3, 3, figure=fig,
                       left=0.05, right=0.95,
                       top=0.93, bottom=0.05,
                       hspace=0.4, wspace=0.3)

ax_ring    = fig.add_subplot(gs[:, :2])   # main ring — left 2/3
ax_metrics = fig.add_subplot(gs[0, 2])   # metrics dashboard — top right
ax_reward  = fig.add_subplot(gs[1, 2])   # reward signal — middle right
ax_pcm     = fig.add_subplot(gs[2, 2])   # PCM per node — bottom right

for ax in [ax_ring, ax_metrics, ax_reward, ax_pcm]:
    ax.set_facecolor("#0d0d1a")
    for spine in ax.spines.values():
        spine.set_color("#333355")

ax_ring.set_xlim(-1.5, 1.5)
ax_ring.set_ylim(-1.5, 1.5)
ax_ring.set_aspect("equal")
ax_ring.axis("off")
ax_ring.set_title("Quantum Ring — Globe Topology (36 edges)",
                  color="#aaaaff", fontsize=10)

# ─── Initialize Artists ───────────────────────────────────────────────────────

# Edge lines
edge_lines = []
for (i, j) in GLOBE:
    x0, y0 = node_pos[i]
    x1, y1 = node_pos[j]
    ln, = ax_ring.plot([x0, x1], [y0, y1], color="#223366",
                       linewidth=0.8, alpha=0.5, zorder=1)
    edge_lines.append(ln)

# Node scatter
xs = [p[0] for p in node_pos]
ys = [p[1] for p in node_pos]
node_scatter = ax_ring.scatter(xs, ys, s=200, zorder=3,
                               c=["#00ff44"] * N, edgecolors="#ffffff",
                               linewidths=0.8)

# Node labels
node_labels = []
for i, name in enumerate(NN):
    x, y     = node_pos[i]
    lx, ly   = x * 1.22, y * 1.22
    family   = FAMILY[name]
    fc       = FAMILY_COLORS[family]
    lbl = ax_ring.text(lx, ly, f"{name}\n{family[:3]}",
                       ha="center", va="center", fontsize=6.5,
                       color=fc, fontweight="bold", zorder=4)
    node_labels.append(lbl)

# Heal flash markers
heal_markers = ax_ring.scatter(xs, ys, s=500, zorder=2,
                               c=[(1,1,1,0)] * N, edgecolors="none")

# Step counter
step_text = ax_ring.text(-1.45, -1.42, "Step: 0",
                         color="#8888cc", fontsize=8)

# ── Metrics dashboard ──
ax_metrics.set_title("Live Metrics", color="#aaaaff", fontsize=9)
ax_metrics.axis("off")
metrics_text = ax_metrics.text(0.05, 0.95, "",
                               transform=ax_metrics.transAxes,
                               color="#00ff88", fontsize=8,
                               va="top", fontfamily="monospace")

# ── Reward signal plot ──
HISTORY = 120
reward_history  = deque([0.0] * HISTORY, maxlen=HISTORY)
coh_history     = deque([0.0] * HISTORY, maxlen=HISTORY)
ax_reward.set_title("Reward Signal", color="#aaaaff", fontsize=9)
ax_reward.set_ylim(0, 2.2)
ax_reward.tick_params(colors="#555577", labelsize=7)
ax_reward.set_ylabel("R", color="#aaaaff", fontsize=8)
reward_line, = ax_reward.plot([], [], color="#00ffcc", linewidth=1.2, label="Reward")
coh_line,    = ax_reward.plot([], [], color="#ff88ff", linewidth=0.8,
                               linestyle="--", label="Coherence")
ax_reward.legend(fontsize=7, facecolor="#0d0d1a", labelcolor="white",
                 loc="upper left")
ax_reward.set_xlim(0, HISTORY)

# ── PCM bar chart ──
ax_pcm.set_title("PCM per Node", color="#aaaaff", fontsize=9)
ax_pcm.set_ylim(-0.35, 0.15)
ax_pcm.axhline(-0.15, color="#00ff44", linewidth=0.6, linestyle="--", alpha=0.6)
ax_pcm.axhline(-0.05, color="#ffff00", linewidth=0.6, linestyle="--", alpha=0.6)
ax_pcm.axhline( 0.05, color="#ff4400", linewidth=0.6, linestyle="--", alpha=0.6)
ax_pcm.tick_params(colors="#555577", labelsize=6)
ax_pcm.set_ylabel("PCM", color="#aaaaff", fontsize=8)
pcm_bars = ax_pcm.bar(range(N), [0.0] * N,
                       color=["#00ff44"] * N, width=0.7)
ax_pcm.set_xticks(range(N))
ax_pcm.set_xticklabels([n[:3] for n in NN], rotation=45, fontsize=6, color="#8888cc")

# ─── Initialize Ring ──────────────────────────────────────────────────────────

ring = QuantumRing()

# Warm up 50 steps before displaying
for _ in range(50):
    ring.step()

# ─── Animation Update ─────────────────────────────────────────────────────────

def update(frame):
    # Run one BCP step
    ring.step()
    m = ring.metrics()

    # ── Update edges ──
    for idx, ((i, j), ln) in enumerate(zip(GLOBE, edge_lines)):
        strength = ring.edge_strength(i, j)
        ln.set_color((0.1 + 0.5 * strength,
                      0.2 + 0.4 * strength,
                      0.6 + 0.3 * strength, 1.0))
        ln.set_linewidth(0.5 + 1.5 * strength)
        ln.set_alpha(0.3 + 0.6 * strength)

    # ── Update nodes ──
    colors = [guardrail_color(p) for p in m["pcms"]]
    sizes  = [150 + 300 * abs(p) for p in m["pcms"]]
    node_scatter.set_facecolor(colors)
    node_scatter.set_sizes(sizes)

    # ── Heal flash ──
    flash_colors = []
    for i in range(N):
        if ring.heal_flash[i] > 0:
            alpha = ring.heal_flash[i] / 8.0
            flash_colors.append((1.0, 1.0, 1.0, alpha))
        else:
            flash_colors.append((1.0, 1.0, 1.0, 0.0))
    heal_markers.set_facecolor(flash_colors)

    # ── Step counter ──
    step_text.set_text(f"Step: {ring.step_count}  |  "
                       f"cv={m['cv']:.3f}  nf={m['negfrac']:.2f}  "
                       f"nc={m['nc_count']}/12")

    # ── Metrics dashboard ──
    status_lines = [f"{NN[i][:8]:<8} {guardrail_label(m['pcms'][i]):<6} "
                    f"PCM={m['pcms'][i]:+.3f}  φ={m['phases'][i]:.2f}"
                    for i in range(N)]
    metrics_str = (
        f"cv      = {m['cv']:.4f}  (target=1.0)\n"
        f"negfrac = {m['negfrac']:.4f}  (target=1.0)\n"
        f"nc/12   = {m['nc_count']:2d}/12\n"
        f"PCM avg = {m['mean_pcm']:+.4f}\n"
        f"Coherence={m['coherence']:.4f}\n"
        f"Entropy  ={m['entropy']:.4f}\n"
        f"Reward   ={m['reward']:.4f}\n"
        f"─────────────────────\n"
    ) + "\n".join(status_lines)
    metrics_text.set_text(metrics_str)

    # ── Reward history ──
    reward_history.append(m["reward"])
    coh_history.append(m["coherence"])
    reward_line.set_data(range(HISTORY), list(reward_history))
    coh_line.set_data(range(HISTORY),    list(coh_history))
    ax_reward.set_ylim(
        min(0, min(reward_history) - 0.1),
        max(2.2, max(reward_history) + 0.1)
    )

    # ── PCM bars ──
    for bar, pcm, col in zip(pcm_bars, m["pcms"],
                              [guardrail_color(p) for p in m["pcms"]]):
        bar.set_height(pcm)
        bar.set_color(col)

    return ([node_scatter, heal_markers, step_text, metrics_text,
             reward_line, coh_line] + edge_lines +
            [b for b in pcm_bars])


# ─── Run ──────────────────────────────────────────────────────────────────────

ani = animation.FuncAnimation(
    fig, update,
    interval=80,       # ~12 fps — smooth enough, not too fast
    blit=False,        # False for multi-axis updates
    cache_frame_data=False
)

print("QCAI Quantum Ring Visualization")
print("================================")
print(f"Nodes:  {N} ({', '.join(NN)})")
print(f"Edges:  {len(GLOBE)} (Globe topology)")
print(f"Alpha:  {ALPHA} (BCP coupling)")
print(f"Noise:  {NOISE * 100:.0f}% depolarization")
print()
print("Guardrail legend:")
print("  GREEN  — PCM < -0.15  (deep non-classical)")
print("  YELLOW — PCM < -0.05  (non-classical)")
print("  ORANGE — PCM < +0.05  (borderline)")
print("  RED    — PCM >= +0.05 (classical, self-healing triggered)")
print()
print("Close the window to exit.")

plt.show()


# ─── Live Metrics Feed (add this at the bottom of the update() function) ──────
# Posts quantum ring state to the bridge every 50 steps so agents can
# see live physics data in their context.

import threading as _threading
import urllib.request as _urllib

def _post_metrics(metrics_dict):
    """Post metrics to bridge listener on port 9999."""
    import json
    try:
        data = json.dumps(metrics_dict).encode()
        req  = _urllib.Request(
            "http://127.0.0.1:9999",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        _urllib.urlopen(req, timeout=2)
    except Exception:
        pass  # bridge may not be running — that's fine

def _feed_update(frame_ref, ring_ref):
    """Called every 50 animation frames to push metrics to Slack bridge."""
    if frame_ref[0] % 50 == 0:
        m = ring_ref.metrics()
        m["step"] = ring_ref.step_count
        _threading.Thread(target=_post_metrics, args=(m,), daemon=True).start()

# Monkey-patch the update function to include feed
_orig_update = update
def update(frame):
    result = _orig_update(frame)
    _feed_update([frame], ring)
    return result


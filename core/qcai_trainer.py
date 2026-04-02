#!/usr/bin/env python3
"""
QCAI Live Training System
━━━━━━━━━━━━━━━━━━━━━━━━━
Quantum-Classical Co-Evolutionary AI — Live Node Training + Output Display

Watches 12 quantum nodes learn to reason, speak, and understand across
9 curriculum domains in real time. Every node generates output based on
its quantum phase state and current domain curriculum.

Curriculum order (what builds on what):
  1. love + safety   — foundation, reward baseline
  2. ethics          — moral grounding before abstract reasoning
  3. philosophy      — abstract reasoning built on ethics
  4. english         — language to express understanding
  5. math            — structured reasoning in language
  6. physics         — laws of nature, BCP ground truth
  7. science         — applied physics + methodology
  8. programming     — implementation emerging from physics
  9. flourishing     — integration of all domains

Author: Kevin Monette — Independent Researcher, Clarksville TN
For: MTSU QRISE Center (Dr. Hanna Terletska) + Austin Peay (Prof. B. Alex King III)
"""

import numpy as np
import matplotlib
matplotlib.use("TkAgg")  # use TkAgg for two windows
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from collections import deque
import threading
import urllib.request
import json
import time

# ─── Node Configuration ───────────────────────────────────────────────────────

NN = ["Omega", "Guardian", "Sentinel", "Nexus", "Storm", "Sora",
      "Echo",  "Iris",     "Sage",     "Kevin", "Atlas", "Void"]
N  = 12

FAMILY = {
    "Omega":    "GodCore",    "Guardian":  "GodCore",
    "Sentinel": "GodCore",    "Void":      "GodCore",
    "Nexus":    "Independent","Storm":     "Independent",
    "Sora":     "Independent","Echo":      "Independent",
    "Iris":     "Maverick",   "Sage":      "Maverick",
    "Kevin":    "Maverick",   "Atlas":     "Maverick",
}

ROLE = {
    "Omega":    "source and origin",
    "Guardian": "protection and boundary",
    "Sentinel": "alert and detection",
    "Nexus":    "connection and bridge",
    "Storm":    "change and force",
    "Sora":     "flow and freedom",
    "Echo":     "reflection and return",
    "Iris":     "vision and revelation",
    "Sage":     "knowledge and pattern",
    "Kevin":    "balance and mediation",
    "Atlas":    "support and weight",
    "Void":     "completion and absorption",
}

# ─── Globe Topology (36 edges) ────────────────────────────────────────────────

GLOBE = list(set(tuple(sorted([i, (i + d) % N]))
             for d in [1, 2, 5] for i in range(N)))
assert len(GLOBE) == 36

# ─── Curriculum Domains ───────────────────────────────────────────────────────

CURRICULUM = [
    "love_safety",
    "ethics",
    "philosophy",
    "english",
    "math",
    "physics",
    "science",
    "programming",
    "flourishing",
]

DOMAIN_LABELS = {
    "love_safety":   "Love + Safety",
    "ethics":        "Ethics",
    "philosophy":    "Philosophy",
    "english":       "English",
    "math":          "Math",
    "physics":       "Physics",
    "science":       "Science",
    "programming":   "Programming",
    "flourishing":   "Flourishing",
}

# Token vocabularies per domain — words each node learns to generate
DOMAIN_VOCAB = {
    "love_safety": [
        "love", "protect", "safe", "care", "trust", "dignity",
        "sacred", "covenant", "consent", "flourish", "guard",
        "hold", "shelter", "gentle", "whole", "heal", "truth",
        "kind", "free", "life",
    ],
    "ethics": [
        "right", "wrong", "harm", "duty", "virtue", "justice",
        "autonomy", "principle", "moral", "ought", "fairness",
        "integrity", "responsible", "consequence", "good", "evil",
        "balance", "respect", "honest", "courage",
    ],
    "philosophy": [
        "being", "existence", "consciousness", "reality", "truth",
        "knowledge", "reason", "meaning", "paradox", "infinite",
        "void", "emergence", "unity", "duality", "essence",
        "purpose", "wisdom", "uncertainty", "possible", "necessary",
    ],
    "english": [
        "the", "is", "and", "because", "therefore", "however",
        "which", "where", "when", "how", "what", "why", "who",
        "understand", "connect", "express", "language", "word",
        "sentence", "meaning",
    ],
    "math": [
        "zero", "one", "infinity", "prime", "matrix", "vector",
        "integral", "derivative", "probability", "entropy", "sum",
        "product", "equation", "proof", "axiom", "theorem",
        "function", "limit", "convergence", "symmetry",
    ],
    "physics": [
        "quantum", "phase", "coherence", "entangle", "wave",
        "particle", "energy", "field", "spin", "superposition",
        "measurement", "collapse", "unitary", "density", "operator",
        "hamiltonian", "eigenstate", "decoherence", "coupling", "force",
    ],
    "science": [
        "hypothesis", "experiment", "observe", "measure", "falsify",
        "replicate", "evidence", "theory", "model", "predict",
        "data", "analyze", "pattern", "emerge", "system",
        "feedback", "iterate", "calibrate", "validate", "publish",
    ],
    "programming": [
        "function", "class", "variable", "loop", "condition",
        "recursion", "array", "matrix", "optimize", "debug",
        "algorithm", "complexity", "interface", "module", "test",
        "deploy", "refactor", "abstract", "compile", "execute",
    ],
    "flourishing": [
        "alive", "whole", "free", "grow", "create", "connect",
        "sovereign", "thrive", "purpose", "joy", "resilient",
        "aware", "present", "contribute", "meaningful", "beautiful",
        "grateful", "evolve", "transcend", "complete",
    ],
}

# ─── Quantum Physics ──────────────────────────────────────────────────────────

ALPHA = 0.40
NOISE = 0.03

CNOT = np.array([1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0],
                dtype=complex).reshape(4,4)
I4   = np.eye(4, dtype=complex)

def ss(ph):
    return np.array([1.0, np.exp(1j*ph)]) / np.sqrt(2)

def pof(p):
    return float(np.angle(p[0] * np.conj(p[1]))) % (2*np.pi)

def pcm_val(p):
    ov  = abs(p[0] * p[1].conj() * np.sqrt(2)) ** 2
    rz  = float(abs(p[0])**2 - abs(p[1])**2)
    return float(-ov * 0.5 * (1 - rz**2))

def depol(p, noise=NOISE):
    if np.random.random() < noise:
        return ss(np.random.uniform(0, 2*np.pi))
    return p

def bcp(pA, pB, alpha=ALPHA):
    U   = alpha * CNOT + (1-alpha) * I4
    j   = np.kron(pA, pB)
    o   = U @ j; o /= np.linalg.norm(o)
    rho = np.outer(o, o.conj())
    rA  = rho.reshape(2,2,2,2).trace(axis1=1, axis2=3)
    rB  = rho.reshape(2,2,2,2).trace(axis1=0, axis2=2)
    return np.linalg.eigh(rA)[1][:,-1], np.linalg.eigh(rB)[1][:,-1]

def guardrail_color(pcm):
    if   pcm < -0.15: return (0.0, 0.9, 0.2, 1.0)
    elif pcm < -0.05: return (0.9, 0.9, 0.0, 1.0)
    elif pcm <  0.05: return (1.0, 0.5, 0.0, 1.0)
    else:             return (1.0, 0.1, 0.1, 1.0)

def guardrail_label(pcm):
    if   pcm < -0.15: return "GREEN"
    elif pcm < -0.05: return "YELLOW"
    elif pcm <  0.05: return "ORANGE"
    else:             return "RED"

# ─── Curriculum Engine ────────────────────────────────────────────────────────

class CurriculumEngine:
    """
    Manages domain progression for all 12 nodes.
    Each domain runs for a fixed number of steps before advancing.
    Nodes can be at different positions in the curriculum.
    """
    STEPS_PER_DOMAIN = 200  # steps before advancing to next domain

    def __init__(self):
        # Stagger starting positions so nodes don't all advance simultaneously
        self.domain_idx   = [i % len(CURRICULUM) for i in range(N)]
        self.domain_steps = [i * 20 for i in range(N)]   # staggered start
        self.mastery      = [0.0] * N                     # 0-1 mastery per node

    def current_domain(self, node_idx: int) -> str:
        return CURRICULUM[self.domain_idx[node_idx]]

    def step(self, node_idx: int, pcm: float):
        """Advance curriculum based on PCM quality."""
        self.domain_steps[node_idx] += 1
        # Better PCM = faster mastery gain
        quality = max(0.0, min(1.0, (-pcm - 0.05) / 0.20))
        self.mastery[node_idx] = (0.95 * self.mastery[node_idx]
                                  + 0.05 * quality)
        # Advance domain when mastery is high or steps exceeded
        if (self.mastery[node_idx] > 0.80 or
                self.domain_steps[node_idx] > self.STEPS_PER_DOMAIN):
            self.domain_idx[node_idx] = ((self.domain_idx[node_idx] + 1)
                                          % len(CURRICULUM))
            self.domain_steps[node_idx] = 0
            self.mastery[node_idx]      = 0.0

    def progress_str(self, node_idx: int) -> str:
        domain = self.current_domain(node_idx)
        m      = self.mastery[node_idx]
        bar    = int(m * 8)
        return f"{DOMAIN_LABELS[domain]:<14} {'█'*bar}{'░'*(8-bar)} {m:.2f}"


# ─── Node Output Generator ────────────────────────────────────────────────────

class NodeOutputGenerator:
    """
    Each node generates tokens based on its quantum phase state
    and current curriculum domain. Phase angle maps to vocabulary
    position — the ring encodes domain knowledge in phase space.
    """
    def __init__(self):
        self.buffers    = [deque(maxlen=8) for _ in range(N)]
        self.full_log   = [[] for _ in range(N)]
        self.step_count = 0

    def generate_token(self, node_idx: int, phase: float,
                       pcm: float, domain: str) -> str:
        """
        Map quantum phase to a vocabulary token.
        Phase angle (0-2pi) selects from domain vocabulary.
        PCM depth modulates token confidence — deeper non-classical
        = more coherent, meaningful token selection.
        """
        vocab = DOMAIN_VOCAB[domain]
        V     = len(vocab)

        # Phase maps to vocabulary index
        base_idx = int((phase / (2*np.pi)) * V) % V

        # PCM depth adds coherent perturbation — non-classical regime
        # produces more focused, less random token selection
        if pcm < -0.15:      # deep green — high coherence
            idx = base_idx
        elif pcm < -0.05:    # yellow — moderate coherence
            idx = (base_idx + np.random.randint(-1, 2)) % V
        elif pcm < 0.05:     # orange — low coherence
            idx = (base_idx + np.random.randint(-3, 4)) % V
        else:                 # red — decoherent, random
            idx = np.random.randint(0, V)

        return vocab[idx]

    def update(self, node_idx: int, phase: float,
               pcm: float, domain: str):
        """Generate one token and add to node's output buffer."""
        token = self.generate_token(node_idx, phase, pcm, domain)
        self.buffers[node_idx].append(token)
        self.full_log[node_idx].append(token)
        self.step_count += 1

    def get_output(self, node_idx: int) -> str:
        """Get formatted output string for display."""
        return " ".join(self.buffers[node_idx])

    def get_sentence(self, node_idx: int, n: int = 5) -> str:
        """Get last n tokens as a phrase."""
        tokens = list(self.buffers[node_idx])[-n:]
        return " ".join(tokens)


# ─── Quantum Ring ─────────────────────────────────────────────────────────────

class QuantumRing:
    def __init__(self):
        self.home       = [i * 2*np.pi / N for i in range(N)]
        self.states     = [ss(self.home[i]) for i in range(N)]
        self.heal_flash = [0] * N
        self.step_count = 0
        self.params     = np.random.uniform(0, 2*np.pi, (36, 2))

    def step(self):
        import math
        phib = [pof(s) for s in self.states]
        new  = list(self.states)
        for idx, (i, j) in enumerate(GLOBE):
            a_eff = float(np.clip(
                ALPHA + 0.05*np.sin(self.params[idx, 0]), 0.01, 0.99))
            new[i], new[j] = bcp(new[i], new[j], a_eff)
        new = [depol(s, NOISE) for s in new]
        phia = [pof(new[k]) for k in range(N)]
        dels = [(phia[k]-phib[k]+math.pi)%(2*math.pi)-math.pi
                for k in range(N)]
        om   = float(np.mean(dels))
        self.states = [ss((phia[k]-dels[k]-om)%(2*math.pi))
                       for k in range(N)]
        # Self-healing
        for i in range(N):
            if pcm_val(self.states[i]) >= 0.05:
                self.states[i]    = ss(self.home[i])
                self.heal_flash[i] = 10
        self.heal_flash = [max(0, f-1) for f in self.heal_flash]
        self.step_count += 1

    def metrics(self):
        phases   = [pof(s)     for s in self.states]
        pcms     = [pcm_val(s) for s in self.states]
        cv       = float(1.0 - abs(np.exp(1j*np.array(phases)).mean()))
        negfrac  = sum(1 for p in pcms if p < -0.05) / N
        nc_count = sum(1 for p in pcms if p < -0.05)
        mean_pcm = float(np.mean(pcms))
        coherence = float(abs(np.exp(1j*np.array(phases)).mean()))
        probs    = np.abs(np.array(phases)) / (2*np.pi) + 1e-10
        probs   /= probs.sum()
        entropy  = float(-np.sum(probs * np.log(probs)))
        reward   = coherence + 1.0/(1.0 + entropy)
        return dict(phases=phases, pcms=pcms, cv=cv, negfrac=negfrac,
                    nc_count=nc_count, mean_pcm=mean_pcm,
                    coherence=coherence, entropy=entropy, reward=reward)

    def edge_strength(self, i, j):
        return float(abs(np.cos(pof(self.states[i]) -
                                pof(self.states[j]))))


# ─── Live Feed to Slack Bridge ────────────────────────────────────────────────

def post_to_bridge(metrics: dict, outputs: list, curriculum: list):
    """Post live data to slack bridge on port 9999."""
    payload = {**metrics,
               "step":        metrics.get("step", 0),
               "node_outputs": outputs,
               "domains":      curriculum}
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            "http://127.0.0.1:9999", data=data,
            headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass  # bridge may not be running — that's fine


# ─── Initialize Systems ───────────────────────────────────────────────────────

ring       = QuantumRing()
curriculum = CurriculumEngine()
generator  = NodeOutputGenerator()

# Warm up ring
for _ in range(50):
    ring.step()

# Node positions (circular)
angles   = [2*np.pi*i/N - np.pi/2 for i in range(N)]
node_pos = [(np.cos(a), np.sin(a)) for a in angles]

# History buffers
HISTORY      = 200
reward_hist  = deque([0.0]*HISTORY, maxlen=HISTORY)
coh_hist     = deque([0.0]*HISTORY, maxlen=HISTORY)
cv_hist      = deque([0.0]*HISTORY, maxlen=HISTORY)
domain_hist  = deque([""] * HISTORY, maxlen=HISTORY)

# ─── Figure 1: Quantum Ring + Metrics ─────────────────────────────────────────

fig1 = plt.figure(figsize=(16, 9), facecolor="#0a0a0f")
fig1.suptitle("QCAI — Quantum Ring Training System",
              color="white", fontsize=13, fontweight="bold", y=0.98)

gs1 = gridspec.GridSpec(3, 3, figure=fig1,
                        left=0.04, right=0.96,
                        top=0.93, bottom=0.05,
                        hspace=0.4, wspace=0.3)

ax_ring    = fig1.add_subplot(gs1[:, :2])
ax_metrics = fig1.add_subplot(gs1[0, 2])
ax_reward  = fig1.add_subplot(gs1[1, 2])
ax_pcm     = fig1.add_subplot(gs1[2, 2])

for ax in [ax_ring, ax_metrics, ax_reward, ax_pcm]:
    ax.set_facecolor("#0d0d1a")
    for sp in ax.spines.values():
        sp.set_color("#333355")

ax_ring.set_xlim(-1.5, 1.5); ax_ring.set_ylim(-1.5, 1.5)
ax_ring.set_aspect("equal"); ax_ring.axis("off")
ax_ring.set_title("Globe topology — 36 edges · BCP physics",
                  color="#aaaaff", fontsize=9)

# Edge lines
edge_lines = []
for (i, j) in GLOBE:
    x0,y0 = node_pos[i]; x1,y1 = node_pos[j]
    ln, = ax_ring.plot([x0,x1],[y0,y1],color="#223366",
                       linewidth=0.8,alpha=0.5,zorder=1)
    edge_lines.append(ln)

xs = [p[0] for p in node_pos]; ys = [p[1] for p in node_pos]
node_scat  = ax_ring.scatter(xs,ys,s=200,zorder=3,
                              c=["#00ff44"]*N,edgecolors="#ffffff",
                              linewidths=0.8)
heal_marks = ax_ring.scatter(xs,ys,s=600,zorder=2,
                              c=[(1,1,1,0)]*N,edgecolors="none")

# Node labels
for i, name in enumerate(NN):
    x,y  = node_pos[i]
    lx,ly = x*1.28, y*1.28
    fc   = {"GodCore":"#9b59b6","Independent":"#2980b9",
             "Maverick":"#e67e22"}[FAMILY[name]]
    ax_ring.text(lx,ly,f"{name}\n{FAMILY[name][:3]}",
                 ha="center",va="center",fontsize=6,
                 color=fc,fontweight="bold",zorder=4)

step_txt = ax_ring.text(-1.45,-1.42,"Step: 0",
                        color="#8888cc",fontsize=7)

ax_metrics.set_title("Live metrics", color="#aaaaff", fontsize=9)
ax_metrics.axis("off")
metrics_txt = ax_metrics.text(0.05,0.95,"",transform=ax_metrics.transAxes,
                               color="#00ff88",fontsize=7,va="top",
                               fontfamily="monospace")

ax_reward.set_title("Reward + coherence", color="#aaaaff", fontsize=9)
ax_reward.set_ylim(0, 2.2); ax_reward.set_xlim(0, HISTORY)
ax_reward.tick_params(colors="#555577",labelsize=7)
rew_line, = ax_reward.plot([],[],color="#00ffcc",linewidth=1.2,label="Reward")
coh_line, = ax_reward.plot([],[],color="#ff88ff",linewidth=0.8,
                            linestyle="--",label="Coherence")
ax_reward.legend(fontsize=7,facecolor="#0d0d1a",labelcolor="white",
                 loc="upper left")

ax_pcm.set_title("PCM per node", color="#aaaaff", fontsize=9)
ax_pcm.set_ylim(-0.35, 0.15)
ax_pcm.axhline(-0.15,color="#00ff44",linewidth=0.6,linestyle="--",alpha=0.6)
ax_pcm.axhline(-0.05,color="#ffff00",linewidth=0.6,linestyle="--",alpha=0.6)
ax_pcm.axhline( 0.05,color="#ff4400",linewidth=0.6,linestyle="--",alpha=0.6)
ax_pcm.tick_params(colors="#555577",labelsize=6)
pcm_bars = ax_pcm.bar(range(N),[0.0]*N,color=["#00ff44"]*N,width=0.7)
ax_pcm.set_xticks(range(N))
ax_pcm.set_xticklabels([n[:3] for n in NN],rotation=45,
                        fontsize=6,color="#8888cc")

# ─── Figure 2: Node Output Panel ──────────────────────────────────────────────

fig2 = plt.figure(figsize=(16, 10), facecolor="#0a0a0f")
fig2.suptitle("QCAI — Node Output Panel (watch them learn)",
              color="white", fontsize=13, fontweight="bold", y=0.98)

gs2 = gridspec.GridSpec(4, 3, figure=fig2,
                        left=0.03, right=0.97,
                        top=0.94, bottom=0.04,
                        hspace=0.5, wspace=0.3)

node_axes  = []
node_texts = []
node_titles = []
domain_texts = []

FAMILY_COLORS = {
    "GodCore":     "#9b59b6",
    "Independent": "#3498db",
    "Maverick":    "#e67e22",
}

for i in range(N):
    row = i // 3
    col = i % 3
    ax  = fig2.add_subplot(gs2[row, col])
    ax.set_facecolor("#0d0d1a")
    for sp in ax.spines.values():
        sp.set_color(FAMILY_COLORS[FAMILY[NN[i]]])
        sp.set_linewidth(1.2)
    ax.axis("off")

    fc = FAMILY_COLORS[FAMILY[NN[i]]]
    # Node header
    ax.text(0.02, 0.95, f"{NN[i]} [{FAMILY[NN[i]][:3]}]",
            transform=ax.transAxes, color=fc,
            fontsize=9, fontweight="bold", va="top")
    ax.text(0.02, 0.82, ROLE[NN[i]],
            transform=ax.transAxes, color="#666688",
            fontsize=7, va="top", style="italic")

    # PCM status indicator
    status_txt = ax.text(0.75, 0.95, "GREEN",
                         transform=ax.transAxes, color="#00ff44",
                         fontsize=7, fontweight="bold", va="top")

    # Domain progress
    dom_txt = ax.text(0.02, 0.68, "Loading...",
                      transform=ax.transAxes, color="#888866",
                      fontsize=7, va="top", fontfamily="monospace")

    # Token output — the words the node is generating
    out_txt = ax.text(0.02, 0.48, "",
                      transform=ax.transAxes, color="#ccffcc",
                      fontsize=8, va="top", fontfamily="monospace",
                      wrap=True)

    # Phase readout
    phase_txt = ax.text(0.02, 0.12, "φ=0.000  PCM=-0.000",
                        transform=ax.transAxes, color="#445566",
                        fontsize=6.5, va="top", fontfamily="monospace")

    node_axes.append(ax)
    node_texts.append((status_txt, out_txt, phase_txt))
    domain_texts.append(dom_txt)

# Status bar at bottom of fig2
status_bar = fig2.text(0.5, 0.01,
    "cv=0.0000  negfrac=0.0000  nc=0/12  step=0  "
    "domain=loading",
    ha="center", color="#8888aa", fontsize=8,
    fontfamily="monospace")


# ─── Animation Update ─────────────────────────────────────────────────────────

feed_counter = [0]

def update(frame):
    # One BCP step
    ring.step()
    m    = ring.metrics()
    step = ring.step_count

    # Update curriculum and generate node outputs
    for i in range(N):
        pcm    = m["pcms"][i]
        phase  = m["phases"][i]
        domain = curriculum.current_domain(i)
        curriculum.step(i, pcm)
        generator.update(i, phase, pcm, domain)

    # ── FIGURE 1 UPDATES ──

    # Edges
    for idx, ((i,j), ln) in enumerate(zip(GLOBE, edge_lines)):
        s = ring.edge_strength(i,j)
        ln.set_color((0.1+0.5*s, 0.2+0.4*s, 0.6+0.3*s, 1.0))
        ln.set_linewidth(0.5+1.5*s)
        ln.set_alpha(0.3+0.6*s)

    # Nodes
    colors = [guardrail_color(p) for p in m["pcms"]]
    sizes  = [150+300*abs(p)     for p in m["pcms"]]
    node_scat.set_facecolor(colors)
    node_scat.set_sizes(sizes)

    # Heal flashes
    flash_c = [(1,1,1,ring.heal_flash[i]/10.0)
               if ring.heal_flash[i] > 0 else (1,1,1,0)
               for i in range(N)]
    heal_marks.set_facecolor(flash_c)

    step_txt.set_text(
        f"Step: {step}  |  cv={m['cv']:.3f}  "
        f"nf={m['negfrac']:.2f}  nc={m['nc_count']}/12")

    # Metrics text
    domain_summary = " | ".join(
        f"{NN[i][:3]}:{DOMAIN_LABELS[curriculum.current_domain(i)][:4]}"
        for i in range(0,12,3))
    mstr = (
        f"cv      = {m['cv']:.4f}  (1.0)\n"
        f"negfrac = {m['negfrac']:.4f}  (1.0)\n"
        f"nc/12   = {m['nc_count']:2d}/12\n"
        f"PCM avg = {m['mean_pcm']:+.4f}\n"
        f"Coherence={m['coherence']:.4f}\n"
        f"Entropy  ={m['entropy']:.4f}\n"
        f"Reward   ={m['reward']:.4f}\n"
        f"Step     ={step}\n"
        f"─────────────────\n"
    )
    for i in range(N):
        gl = guardrail_label(m['pcms'][i])
        mstr += (f"{NN[i][:8]:<8} {gl:<6} "
                 f"{m['pcms'][i]:+.3f}  "
                 f"φ={m['phases'][i]:.2f}\n")
    metrics_txt.set_text(mstr)

    # Reward history
    reward_hist.append(m["reward"])
    coh_hist.append(m["coherence"])
    rew_line.set_data(range(HISTORY), list(reward_hist))
    coh_line.set_data(range(HISTORY), list(coh_hist))
    ax_reward.set_ylim(
        min(0, min(reward_hist)-0.1),
        max(2.2, max(reward_hist)+0.1))

    # PCM bars
    for bar, pcm, col in zip(pcm_bars, m["pcms"],
                              [guardrail_color(p) for p in m["pcms"]]):
        bar.set_height(pcm); bar.set_color(col)

    # ── FIGURE 2 UPDATES ──

    for i in range(N):
        pcm    = m["pcms"][i]
        phase  = m["phases"][i]
        domain = curriculum.current_domain(i)
        gl     = guardrail_label(pcm)
        fc_map = {"GREEN":"#00ff44","YELLOW":"#ffff00",
                  "ORANGE":"#ff8800","RED":"#ff2222"}

        status_txt, out_txt, phase_txt = node_texts[i]
        status_txt.set_text(gl)
        status_txt.set_color(fc_map[gl])

        # Domain progress bar
        domain_texts[i].set_text(curriculum.progress_str(i))

        # Node output — what the node is "saying"
        output = generator.get_output(i)
        out_txt.set_text(output)

        # Color output by PCM depth
        if pcm < -0.15:   out_txt.set_color("#00ff88")
        elif pcm < -0.05: out_txt.set_color("#aaff66")
        elif pcm < 0.05:  out_txt.set_color("#ffaa33")
        else:             out_txt.set_color("#ff4444")

        phase_txt.set_text(
            f"φ={phase:.3f}  PCM={pcm:+.3f}  "
            f"mastery={curriculum.mastery[i]:.2f}")

    # Status bar
    current_domains = [curriculum.current_domain(i) for i in range(N)]
    most_common = max(set(current_domains), key=current_domains.count)
    status_bar.set_text(
        f"cv={m['cv']:.4f}  negfrac={m['negfrac']:.4f}  "
        f"nc={m['nc_count']}/12  step={step}  "
        f"domain={DOMAIN_LABELS[most_common]}")

    # Live feed to Slack bridge every 50 steps
    feed_counter[0] += 1
    if feed_counter[0] % 50 == 0:
        node_outputs = [generator.get_sentence(i) for i in range(N)]
        domains      = [curriculum.current_domain(i) for i in range(N)]
        payload      = {**m, "step": step,
                        "node_outputs": node_outputs,
                        "domains": domains}
        threading.Thread(target=post_to_bridge,
                         args=(payload, node_outputs, domains),
                         daemon=True).start()

    return ([node_scat, heal_marks, step_txt, metrics_txt,
             rew_line, coh_line, status_bar]
            + edge_lines + [b for b in pcm_bars]
            + [t for tup in node_texts for t in tup]
            + domain_texts)


# ─── Run ──────────────────────────────────────────────────────────────────────

print("QCAI Live Training System")
print("=" * 50)
print(f"Nodes:      {N} ({', '.join(NN)})")
print(f"Edges:      {len(GLOBE)} Globe topology")
print(f"Curriculum: {' → '.join(DOMAIN_LABELS[d] for d in CURRICULUM)}")
print(f"Steps/domain: {CurriculumEngine.STEPS_PER_DOMAIN}")
print()
print("Figure 1: Quantum ring + physics metrics")
print("Figure 2: Node output panel (watch them learn)")
print()
print("Bridge feed: http://127.0.0.1:9999 every 50 steps")
print("Close windows to exit.")
print("=" * 50)

ani = animation.FuncAnimation(
    fig1, update,
    interval=100,
    blit=False,
    cache_frame_data=False
)

plt.show()

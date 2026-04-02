#!/usr/bin/env python3
"""
QCAI 3D Quantum Ring — Live Physics Visualization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The actual quantum ring in 3D space. Not a demo.
12 nodes on a unit sphere, 36 edges, real BCP physics running live.

Controls:
  Mouse drag  — free rotation (any axis)
  Space bar   — pause/resume auto-spin
  R           — reset view
  Q           — quit

Auto-spin: smooth slow rotation, pauses on mouse interaction.

Author: Kevin Monette — QCAI Independent Researcher, Clarksville TN
"""

import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from collections import deque
import threading
import urllib.request
import json
import time

# ─── Node Configuration ───────────────────────────────────────────────────────

NN = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
      "Echo","Iris","Sage","Kevin","Atlas","Void"]
N  = 12

FAMILY = {
    "Omega":"GodCore","Guardian":"GodCore",
    "Sentinel":"GodCore","Void":"GodCore",
    "Nexus":"Independent","Storm":"Independent",
    "Sora":"Independent","Echo":"Independent",
    "Iris":"Maverick","Sage":"Maverick",
    "Kevin":"Maverick","Atlas":"Maverick",
}

FAMILY_HEX = {
    "GodCore":     "#9b59b6",
    "Independent": "#2980b9",
    "Maverick":    "#e67e22",
}

# ─── Globe Topology (36 edges) ────────────────────────────────────────────────

GLOBE = list(set(tuple(sorted([i,(i+d)%N]))
             for d in [1,2,5] for i in range(N)))
assert len(GLOBE) == 36

# ─── 3D Sphere Node Positions ─────────────────────────────────────────────────
# Place 12 nodes on a unit sphere using icosahedral-inspired distribution.
# Nodes are evenly distributed to mirror the actual Globe topology geometry.

def sphere_positions():
    """
    Place 12 nodes on a unit sphere.
    Uses the vertices of an icosahedron — the most uniform 12-point
    distribution on a sphere, matching the Globe topology's optimality.
    """
    phi = (1 + np.sqrt(5)) / 2  # golden ratio
    verts = []
    for signs in [(1,1),(1,-1),(-1,1),(-1,-1)]:
        for perm in [(0,1,2),(1,2,0),(2,0,1)]:
            v = [0.0, 0.0, 0.0]
            v[perm[0]] = signs[0]
            v[perm[1]] = signs[1] * phi
            v[perm[2]] = 0.0
            verts.append(v)
    # Normalize to unit sphere
    verts = [np.array(v)/np.linalg.norm(v) for v in verts]
    return verts[:N]

NODE_POS_3D = sphere_positions()

# ─── Quantum Physics ──────────────────────────────────────────────────────────

ALPHA = 0.40
NOISE = 0.03

CNOT = np.array([1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0],
                dtype=complex).reshape(4,4)
I4   = np.eye(4, dtype=complex)

def ss(ph):
    return np.array([1.0, np.exp(1j*ph)]) / np.sqrt(2)

def pof(p):
    return float(np.angle(p[0]*np.conj(p[1]))) % (2*np.pi)

def pcm_val(p):
    ov  = abs(p[0]*p[1].conj()*np.sqrt(2))**2
    rz  = float(abs(p[0])**2 - abs(p[1])**2)
    return float(-ov*0.5*(1-rz**2))

def depol(p, noise=NOISE):
    if np.random.random() < noise:
        return ss(np.random.uniform(0,2*np.pi))
    return p

def bcp(pA, pB, alpha=ALPHA):
    U   = alpha*CNOT + (1-alpha)*I4
    j   = np.kron(pA,pB); o = U@j; o /= np.linalg.norm(o)
    rho = np.outer(o,o.conj())
    rA  = rho.reshape(2,2,2,2).trace(axis1=1,axis2=3)
    rB  = rho.reshape(2,2,2,2).trace(axis1=0,axis2=2)
    return np.linalg.eigh(rA)[1][:,-1], np.linalg.eigh(rB)[1][:,-1]

def pcm_rgba(pcm):
    if   pcm < -0.15: return (0.0, 0.9, 0.2, 0.95)
    elif pcm < -0.05: return (0.9, 0.9, 0.0, 0.90)
    elif pcm <  0.05: return (1.0, 0.5, 0.0, 0.85)
    else:             return (1.0, 0.1, 0.1, 0.95)

def pcm_label(pcm):
    if   pcm < -0.15: return "GREEN"
    elif pcm < -0.05: return "YELLOW"
    elif pcm <  0.05: return "ORANGE"
    else:             return "RED"

# ─── Quantum Ring ─────────────────────────────────────────────────────────────

class QuantumRing:
    def __init__(self):
        self.home       = [i*2*np.pi/N for i in range(N)]
        self.states     = [ss(self.home[i]) for i in range(N)]
        self.heal_flash = [0]*N
        self.step_count = 0
        self.params     = np.random.uniform(0,2*np.pi,(36,2))

    def step(self):
        import math
        phib = [pof(s) for s in self.states]
        new  = list(self.states)
        for idx,(i,j) in enumerate(GLOBE):
            a = float(np.clip(ALPHA+0.05*np.sin(self.params[idx,0]),0.01,0.99))
            new[i],new[j] = bcp(new[i],new[j],a)
        new = [depol(s,NOISE) for s in new]
        phia = [pof(new[k]) for k in range(N)]
        dels = [(phia[k]-phib[k]+math.pi)%(2*math.pi)-math.pi for k in range(N)]
        om   = float(np.mean(dels))
        self.states = [ss((phia[k]-dels[k]-om)%(2*math.pi)) for k in range(N)]
        for i in range(N):
            if pcm_val(self.states[i]) >= 0.05:
                self.states[i]    = ss(self.home[i])
                self.heal_flash[i] = 12
        self.heal_flash = [max(0,f-1) for f in self.heal_flash]
        self.step_count += 1

    def metrics(self):
        phases   = [pof(s)     for s in self.states]
        pcms     = [pcm_val(s) for s in self.states]
        cv       = float(1.0-abs(np.exp(1j*np.array(phases)).mean()))
        negfrac  = sum(1 for p in pcms if p<-0.05)/N
        nc_count = sum(1 for p in pcms if p<-0.05)
        mean_pcm = float(np.mean(pcms))
        coherence= float(abs(np.exp(1j*np.array(phases)).mean()))
        probs    = np.abs(np.array(phases))/(2*np.pi)+1e-10
        probs   /= probs.sum()
        entropy  = float(-np.sum(probs*np.log(probs)))
        reward   = coherence+1.0/(1.0+entropy)
        return dict(phases=phases,pcms=pcms,cv=cv,negfrac=negfrac,
                    nc_count=nc_count,mean_pcm=mean_pcm,
                    coherence=coherence,entropy=entropy,reward=reward)

    def edge_strength(self,i,j):
        return float(abs(np.cos(pof(self.states[i])-pof(self.states[j]))))

# ─── Initialize ───────────────────────────────────────────────────────────────

ring = QuantumRing()
for _ in range(80):
    ring.step()

# History
HISTORY     = 300
reward_hist = deque([0.0]*HISTORY, maxlen=HISTORY)
coh_hist    = deque([0.0]*HISTORY, maxlen=HISTORY)

# ─── Figure Setup ─────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(18,10), facecolor="#050508")
fig.suptitle("QCAI — Live 3D Quantum Ring  |  Space=pause  R=reset  drag=rotate",
             color="#8888cc", fontsize=10, y=0.99)

# Main 3D axis (left 65%)
ax3d = fig.add_axes([0.0, 0.05, 0.65, 0.90], projection='3d')
ax3d.set_facecolor("#050508")
ax3d.set_xlim(-1.4,1.4); ax3d.set_ylim(-1.4,1.4); ax3d.set_zlim(-1.4,1.4)
ax3d.set_box_aspect([1,1,1])
ax3d.grid(False)
ax3d.xaxis.pane.fill = False
ax3d.yaxis.pane.fill = False
ax3d.zaxis.pane.fill = False
ax3d.xaxis.pane.set_edgecolor("#111122")
ax3d.yaxis.pane.set_edgecolor("#111122")
ax3d.zaxis.pane.set_edgecolor("#111122")
ax3d.tick_params(colors="#111122",labelsize=0)
ax3d.set_xlabel(""); ax3d.set_ylabel(""); ax3d.set_zlabel("")

# Right panel axes
ax_metrics = fig.add_axes([0.67, 0.55, 0.31, 0.40])
ax_reward  = fig.add_axes([0.67, 0.28, 0.31, 0.22])
ax_pcm     = fig.add_axes([0.67, 0.04, 0.31, 0.20])

for ax in [ax_metrics, ax_reward, ax_pcm]:
    ax.set_facecolor("#0d0d1a")
    for sp in ax.spines.values():
        sp.set_color("#333355")

ax_metrics.axis("off")
ax_metrics.set_title("Live metrics", color="#aaaaff", fontsize=9, pad=4)
metrics_txt = ax_metrics.text(0.03, 0.97, "", transform=ax_metrics.transAxes,
                               color="#00ff88", fontsize=7, va="top",
                               fontfamily="monospace")

ax_reward.set_title("Reward + coherence", color="#aaaaff", fontsize=9, pad=4)
ax_reward.set_facecolor("#0d0d1a")
ax_reward.tick_params(colors="#555577", labelsize=7)
ax_reward.set_xlim(0, HISTORY)
rew_line, = ax_reward.plot([],[],color="#00ffcc",linewidth=1.0,label="R")
coh_line, = ax_reward.plot([],[],color="#ff88ff",linewidth=0.8,
                            linestyle="--",label="Coh")
ax_reward.legend(fontsize=7, facecolor="#0d0d1a", labelcolor="white",
                 loc="upper left")

ax_pcm.set_title("PCM per node", color="#aaaaff", fontsize=9, pad=4)
ax_pcm.set_ylim(-0.35, 0.15)
ax_pcm.axhline(-0.15,color="#00ff44",linewidth=0.5,linestyle="--",alpha=0.5)
ax_pcm.axhline(-0.05,color="#ffff00",linewidth=0.5,linestyle="--",alpha=0.5)
ax_pcm.axhline( 0.05,color="#ff4400",linewidth=0.5,linestyle="--",alpha=0.5)
ax_pcm.tick_params(colors="#555577", labelsize=6)
pcm_bars = ax_pcm.bar(range(N),[0.0]*N,color=["#00ff44"]*N,width=0.7)
ax_pcm.set_xticks(range(N))
ax_pcm.set_xticklabels([n[:3] for n in NN],rotation=45,
                        fontsize=6,color="#8888cc")

# ─── 3D Drawing Helpers ───────────────────────────────────────────────────────

# Draw sphere wireframe (subtle reference sphere)
u = np.linspace(0,2*np.pi,30)
v = np.linspace(0,np.pi,20)
sx = 0.98*np.outer(np.cos(u),np.sin(v))
sy = 0.98*np.outer(np.sin(u),np.sin(v))
sz = 0.98*np.outer(np.ones(30),np.cos(v))
ax3d.plot_surface(sx,sy,sz,color="#0a0a1a",alpha=0.15,
                  linewidth=0,antialiased=False)

# Draw latitude/longitude lines (very faint reference grid)
for lat in np.linspace(-np.pi/2,np.pi/2,7):
    phi_r = np.linspace(0,2*np.pi,60)
    ax3d.plot(np.cos(lat)*np.cos(phi_r),
              np.cos(lat)*np.sin(phi_r),
              np.sin(lat)*np.ones(60),
              color="#111133",linewidth=0.3,alpha=0.4)
for lon in np.linspace(0,2*np.pi,12,endpoint=False):
    theta_r = np.linspace(-np.pi/2,np.pi/2,30)
    ax3d.plot(np.cos(theta_r)*np.cos(lon),
              np.cos(theta_r)*np.sin(lon),
              np.sin(theta_r),
              color="#111133",linewidth=0.3,alpha=0.4)

# Initial 3D objects — edges as Line3DCollection
edge_segs  = [[[NODE_POS_3D[i][0],NODE_POS_3D[i][1],NODE_POS_3D[i][2]],
               [NODE_POS_3D[j][0],NODE_POS_3D[j][1],NODE_POS_3D[j][2]]]
              for (i,j) in GLOBE]
edge_col   = Line3DCollection(edge_segs, linewidths=0.6,
                               colors=["#223366"]*36, alpha=0.5)
ax3d.add_collection3d(edge_col)

# Node scatter
nxs = [p[0] for p in NODE_POS_3D]
nys = [p[1] for p in NODE_POS_3D]
nzs = [p[2] for p in NODE_POS_3D]
node_scat  = ax3d.scatter(nxs,nys,nzs, s=120, c=["#00ff44"]*N,
                           depthshade=True, edgecolors="white",
                           linewidths=0.5, zorder=5)

# Heal glow markers (larger, semi-transparent)
heal_scat  = ax3d.scatter(nxs,nys,nzs, s=400,
                           c=[(1,1,1,0)]*N,
                           depthshade=False, edgecolors="none",
                           zorder=4)

# Node labels
node_label_objs = []
for i,name in enumerate(NN):
    p  = NODE_POS_3D[i]
    lp = [c*1.18 for c in p]
    fc = FAMILY_HEX[FAMILY[name]]
    lbl = ax3d.text(lp[0],lp[1],lp[2],
                    f"{name}\n{FAMILY[name][:3]}",
                    color=fc, fontsize=6, ha="center",
                    fontweight="bold")
    node_label_objs.append(lbl)

# Step counter text
step_txt3d = ax3d.text2D(0.02,0.02,"Step: 0",
                          transform=ax3d.transAxes,
                          color="#8888cc",fontsize=8)

# ─── Rotation State ───────────────────────────────────────────────────────────

class RotState:
    def __init__(self):
        self.auto_spin  = True
        self.azim       = 45.0
        self.elev       = 25.0
        self.spin_speed = 0.4    # degrees per frame
        self.dragging   = False
        self.last_x     = 0
        self.last_y     = 0
        self.paused     = False

rot = RotState()

def on_mouse_press(event):
    if event.inaxes == ax3d:
        rot.dragging = True
        rot.auto_spin = False
        rot.last_x = event.xdata or 0
        rot.last_y = event.ydata or 0

def on_mouse_release(event):
    rot.dragging = False
    # Resume auto-spin after 3 seconds
    def resume():
        time.sleep(3)
        if not rot.paused:
            rot.auto_spin = True
    threading.Thread(target=resume, daemon=True).start()

def on_mouse_move(event):
    if rot.dragging and event.inaxes == ax3d:
        dx = (event.xdata or rot.last_x) - rot.last_x
        dy = (event.ydata or rot.last_y) - rot.last_y
        rot.azim  += dx * 80
        rot.elev  += dy * 40
        rot.elev   = np.clip(rot.elev, -89, 89)
        rot.last_x = event.xdata or rot.last_x
        rot.last_y = event.ydata or rot.last_y

def on_key(event):
    if event.key == ' ':
        rot.paused    = not rot.paused
        rot.auto_spin = not rot.paused
    elif event.key == 'r':
        rot.azim  = 45.0
        rot.elev  = 25.0

fig.canvas.mpl_connect('button_press_event',   on_mouse_press)
fig.canvas.mpl_connect('button_release_event', on_mouse_release)
fig.canvas.mpl_connect('motion_notify_event',  on_mouse_move)
fig.canvas.mpl_connect('key_press_event',      on_key)

# ─── Data Feed ────────────────────────────────────────────────────────────────

feed_lock    = threading.Lock()
latest_data  = {}
last_feed_t  = [0.0]

def post_to_bridge(payload):
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            "http://127.0.0.1:9999", data=data,
            headers={"Content-Type":"application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

# ─── Animation Update ─────────────────────────────────────────────────────────

def update(frame):
    # Step physics
    ring.step()
    m    = ring.metrics()
    step = ring.step_count

    # ── Rotation ──
    if rot.auto_spin:
        rot.azim += rot.spin_speed
    ax3d.view_init(elev=rot.elev, azim=rot.azim)

    # ── Update 3D edges ──
    new_segs   = []
    new_colors = []
    new_widths = []
    for (i,j) in GLOBE:
        s = ring.edge_strength(i,j)
        new_segs.append([
            [NODE_POS_3D[i][0],NODE_POS_3D[i][1],NODE_POS_3D[i][2]],
            [NODE_POS_3D[j][0],NODE_POS_3D[j][1],NODE_POS_3D[j][2]]
        ])
        r = 0.1+0.5*s; g = 0.2+0.4*s; b = 0.6+0.3*s
        new_colors.append((r,g,b,0.3+0.6*s))
        new_widths.append(0.4+1.8*s)
    edge_col.set_segments(new_segs)
    edge_col.set_colors(new_colors)
    edge_col.set_linewidths(new_widths)

    # ── Update 3D nodes ──
    colors = [pcm_rgba(p) for p in m["pcms"]]
    sizes  = [80+250*abs(p) for p in m["pcms"]]
    node_scat._facecolor3d = colors
    node_scat._edgecolor3d = ["white"]*N
    try:
        node_scat.set_sizes(sizes)
        node_scat.set_facecolor(colors)
    except Exception:
        pass

    # Heal flashes
    heal_c = [(1.0,1.0,1.0, ring.heal_flash[i]/12.0)
               if ring.heal_flash[i]>0 else (1,1,1,0)
               for i in range(N)]
    try:
        heal_scat.set_facecolor(heal_c)
        heal_scat.set_sizes([500 if ring.heal_flash[i]>0 else 0
                              for i in range(N)])
    except Exception:
        pass

    # Step text
    spin_icon = "▶" if rot.auto_spin else "⏸"
    step_txt3d.set_text(
        f"{spin_icon} Step:{step}  cv={m['cv']:.3f}  "
        f"nf={m['negfrac']:.2f}  nc={m['nc_count']}/12")

    # ── Right panel metrics ──
    mstr = (
        f"cv       = {m['cv']:.4f}  (1.0)\n"
        f"negfrac  = {m['negfrac']:.4f}  (1.0)\n"
        f"nc/12    = {m['nc_count']:2d}/12\n"
        f"PCM avg  = {m['mean_pcm']:+.4f}\n"
        f"Coherence= {m['coherence']:.4f}\n"
        f"Entropy  = {m['entropy']:.4f}\n"
        f"Reward   = {m['reward']:.4f}\n"
        f"Step     = {step}\n"
        f"Azim     = {rot.azim%360:.1f}°\n"
        f"─────────────────────\n"
    )
    for i in range(N):
        mstr += (f"{NN[i]:<8} {pcm_label(m['pcms'][i]):<6} "
                 f"{m['pcms'][i]:+.3f}  φ={m['phases'][i]:.2f}\n")
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
                              [pcm_rgba(p) for p in m["pcms"]]):
        bar.set_height(pcm); bar.set_color(col)

    # Live feed every 60 seconds
    now = time.time()
    if now - last_feed_t[0] >= 60:
        last_feed_t[0] = now
        payload = {**m, "step": step,
                   "azim": rot.azim, "elev": rot.elev}
        threading.Thread(target=post_to_bridge,
                         args=(payload,), daemon=True).start()

    return []

# ─── Run ──────────────────────────────────────────────────────────────────────

print("QCAI 3D Quantum Ring — Live Physics")
print("=" * 45)
print(f"Nodes:  {N}  |  Edges: {len(GLOBE)}  |  Alpha: {ALPHA}")
print(f"Sphere: icosahedral node distribution")
print()
print("Controls:")
print("  Mouse drag  — free rotation")
print("  Space       — pause/resume spin")
print("  R           — reset view")
print()
print("Feed: http://127.0.0.1:9999 every 60s")
print("=" * 45)

ani = animation.FuncAnimation(
    fig, update,
    interval=80,
    blit=False,
    cache_frame_data=False
)

plt.show()

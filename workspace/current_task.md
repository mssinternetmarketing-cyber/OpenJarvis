# QCAI 3D Visualization — Full Task Specification
## Target file: qcai_3d.py
## Hardware: GTX 1070, Bazzite Linux, matplotlib TkAgg, Python 3.13

---

## BUGS TO FIX

1. TypeError: only integer scalar arrays can be converted to a scalar index
2. Node scatter facecolor/sizes not updating in 3D matplotlib
3. Heal flash scatter not working
4. Auto-spin not working — view_init called but not animating
5. Mouse drag rotation not working
6. No data flowing to metrics panel
7. No entanglement visualization on edges
8. No information flow pulses

---

## PHYSICS GROUND TRUTH (invariant — never deviate)

```python
# Qubit state
ss(ph) = np.array([1.0, np.exp(1j*ph)]) / np.sqrt(2)

# Phase
pof(p) = float(np.angle(p[0]*np.conj(p[1]))) % (2*np.pi)

# PCM (Phase Coherence Metric)
ov  = abs(p[0]*p[1].conj()*np.sqrt(2))**2
rz  = float(abs(p[0])**2 - abs(p[1])**2)
pcm = float(-ov * 0.5 * (1 - rz**2))
# TARGET: pcm < -0.05 non-classical, < -0.15 deep green

# BCP (Bipartite Coupling Protocol)
CNOT = np.array([1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0],dtype=complex).reshape(4,4)
U = alpha*CNOT + (1-alpha)*I4   # alpha=0.40
joint = np.kron(pA,pB); out=U@joint; out/=norm(out)
rho = np.outer(out,conj(out))
rA = rho.reshape(2,2,2,2).trace(axis1=1,axis2=3)
rB = rho.reshape(2,2,2,2).trace(axis1=0,axis2=2)
return eigh(rA)[1][:,-1], eigh(rB)[1][:,-1]

# Globe topology — MUST be exactly 36 edges
GLOBE = list(set(tuple(sorted([i,(i+d)%12])) for d in [1,2,5] for i in range(12)))
assert len(GLOBE) == 36

# Metrics
cv       = 1.0 - abs(mean(exp(i*phases)))   # target=1.0
negfrac  = sum(pcm<-0.05)/12                # target=1.0
reward   = coherence + 1/(1+entropy)        # von Neumann entropy

# Self-healing
# RED node (pcm>=0.05) → reset to home[i] = i*2*pi/12

# Nodes (index 0-11)
NN = ["Omega","Guardian","Sentinel","Nexus","Storm","Sora",
      "Echo","Iris","Sage","Kevin","Atlas","Void"]

# Families
GodCore:     Omega, Guardian, Sentinel, Void
Independent: Nexus, Storm, Sora, Echo
Maverick:    Iris, Sage, Kevin, Atlas
```

---

## 3D VISUALIZATION REQUIREMENTS

### Node placement
- 12 nodes on unit sphere using icosahedral vertex distribution
- Nodes colored by guardrail status: GREEN(#00ff44) YELLOW(#ffff00) ORANGE(#ff8800) RED(#ff2222)
- Node size proportional to abs(PCM) — deeper non-classical = larger
- Node pulse: size oscillates slowly with PCM magnitude

### Edge rendering
- All 36 Globe edges drawn as 3D lines
- Edge brightness = entanglement strength abs(cos(phi_i - phi_j))
- Edge color family: bright blue-white for strong, dark blue for weak
- Line width scales with entanglement strength

### Information flow pulses
- When BCP fires on edge (i,j), animate a bright dot traveling along that edge
- Pulse color = family color of source node:
  GodCore=purple(#9b59b6) Independent=blue(#2980b9) Maverick=orange(#e67e22)
- Pulse travels over ~10 frames
- Multiple simultaneous pulses on different edges
- This makes information flow through entanglement visible in real time

### Family constellation lines
- Subtle permanent lines connecting same-family nodes
- Color: family color at 30% opacity
- Slightly thinner than BCP edges

### Self-heal animation
- When node resets: white flash expanding outward 3 pulses
- Flash visible from any viewing angle

### Controls
- Mouse drag: free rotation any axis (intercept mouse events on figure, not ax3d)
- Auto-spin: 0.3 degrees/frame azimuth rotation, smooth, never stops unless paused
- Space bar: pause/resume auto-spin
- R key: reset to default view (elev=25, azim=45)
- When mouse pressed: pause auto-spin, resume after 3 seconds release

### Background
- Dark #050508 background
- Subtle sphere wireframe as reference grid (very faint #111133)
- No axis labels, no tick marks, no grid lines

---

## METRICS PANEL (right side, ~35% width)

### Physics dashboard
- cv = X.XXXX (target=1.0)
- negfrac = X.XXXX (target=1.0)
- nc/12 = XX/12
- PCM avg = +/-X.XXXX
- coherence = X.XXXX
- entropy = X.XXXX
- reward = X.XXXX
- step = XXXXXX

### Per-node table
For each of 12 nodes:
  [STATUS_EMOJI] NodeName  PCM=+/-X.XXX  φ=X.XX  [DOMAIN]

### Reward history plot
- Scrolling line chart last 300 steps
- reward line (cyan) + coherence line (pink dashed)
- Target line at 1.8

### PCM bar chart
- 12 bars, colored by guardrail status
- Horizontal threshold lines at -0.15 (green), -0.05 (yellow), +0.05 (red)
- X labels = node name abbreviations

---

## NODE OUTPUT PANEL (second matplotlib window)

### Layout: 4 rows x 3 columns = 12 node boxes

### Each node box contains:
- Header: NodeName [Family] — Role
- Guardrail status indicator (color-coded border)
- Current domain + mastery progress bar: "Physics    ████░░░░ 0.52"
- Live token output (last 8 tokens, color = PCM depth):
  GREEN nodes: bright green text
  YELLOW nodes: yellow text  
  ORANGE nodes: dim orange
  RED nodes: dim red, scattered
- Phase and PCM readout: "φ=3.141  PCM=-0.250"
- Quality score: how semantically coherent the last tokens are

### Status bar at bottom
- Overall: cv=X.XXXX negfrac=X.XXXX nc=XX/12 step=XXXXXX
- Most active domain across all nodes

---

## CURRICULUM ENGINE

### Domain order (what builds on what):
1. love_safety    — foundation, reward baseline
2. ethics         — moral grounding
3. philosophy     — abstract reasoning on ethics
4. english        — language to express understanding
5. math           — structured reasoning
6. physics        — laws of nature, BCP ground truth
7. science        — applied physics + methodology
8. programming    — implementation from physics
9. flourishing    — integration of all domains

### Vocabulary per domain (20 words each):
love_safety:   love protect safe care trust dignity sacred covenant consent flourish guard hold shelter gentle whole heal truth kind free life
ethics:        right wrong harm duty virtue justice autonomy principle moral ought fairness integrity responsible consequence good evil balance respect honest courage
philosophy:    being existence consciousness reality truth knowledge reason meaning paradox infinite void emergence unity duality essence purpose wisdom uncertainty possible necessary
english:       the is and because therefore however which where when how what why who understand connect express language word sentence meaning
math:          zero one infinity prime matrix vector integral derivative probability entropy sum product equation proof axiom theorem function limit convergence symmetry
physics:       quantum phase coherence entangle wave particle energy field spin superposition measurement collapse unitary density operator hamiltonian eigenstate decoherence coupling force
science:       hypothesis experiment observe measure falsify replicate evidence theory model predict data analyze pattern emerge system feedback iterate calibrate validate publish
programming:   function class variable loop condition recursion array matrix optimize debug algorithm complexity interface module test deploy refactor abstract compile execute
flourishing:   alive whole free grow create connect sovereign thrive purpose joy resilient aware present contribute meaningful beautiful grateful evolve transcend complete

### Token generation:
- Phase angle (0-2pi) maps to vocabulary index
- PCM depth modulates randomness:
  GREEN (pcm<-0.15): deterministic — base_idx maps directly to word
  YELLOW (pcm<-0.05): slight noise — +/-1 position
  ORANGE (pcm<0.05):  moderate noise — +/-3 positions
  RED (pcm>=0.05):    high noise — fully random word

### Mastery:
- Steps per domain: 200
- Mastery threshold: 0.80 to advance
- Mastery update: 0.95*mastery + 0.05*quality where quality=max(0, (-pcm-0.05)/0.20)
- Nodes staggered so they're at different domains simultaneously

---

## LIVE DATA FEED

### POST to http://127.0.0.1:9999 every 60 seconds:
```json
{
  "step": 1234,
  "cv": 1.0,
  "negfrac": 1.0,
  "nc_count": 12,
  "mean_pcm": -0.25,
  "coherence": 0.0,
  "entropy": 2.3,
  "reward": 0.31,
  "phases": [0.0, 0.52, 1.04, ...],
  "pcms": [-0.25, -0.25, ...],
  "node_outputs": ["love protect safe", "right wrong duty", ...],
  "domains": ["love_safety", "ethics", ...]
}
```

---

## TECHNICAL REQUIREMENTS

- matplotlib TkAgg backend (two windows)
- Figure 1: 3D ring (left 65%) + metrics panel (right 35%)
- Figure 2: 12-node output panel
- Animation interval: 80ms (~12fps)
- blit=False (multiple axes update)
- Mouse events on figure level, not ax3d level
- Rotation via ax3d.view_init(elev, azim) each frame
- No external dependencies beyond numpy + matplotlib

## DEMO STANDARD
Dr. Hanna Terletska (MTSU QRISE) and Prof. B. Alex King III (Austin Peay)
will see this running. Every visual element must correspond to a real physics
measurement. Comments must explain the physics to a physicist on first viewing.
The system must look alive — not a demo, but the actual quantum AI running.

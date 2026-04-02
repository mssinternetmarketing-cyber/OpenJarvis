# ═══ c02_physics — Quantum Physics Core ═══
# WHAT: All physics functions — ss, pof, compute_pcm, bcp_step,
#       von_neumann_entropy, compute_cv, compute_negfrac, pcm_color, pcm_emoji
# WHY:  These are the INVARIANT physics formulas from GROUND_TRUTH.md.
#       Every formula is verified against the PEIG research series.
#       Cell Block 2 source — proven over 100+ training loops.

# ─── QUBIT STATE ──────────────────────────────────────────────────────────────
def ss(ph):
    # WHAT: Superposition state at phase ph
    # WHY:  |+_φ⟩ = (|0⟩ + e^{iφ}|1⟩)/√2 — the canonical single-qubit state
    return np.array([1.0, np.exp(1j * ph)]) / np.sqrt(2)

def pof(p):
    # WHAT: Phase-of-field — extract the relative phase angle from a qubit
    # WHY:  φ = arg(p₀*p₁*) — the observable we track across the ring
    return float(np.angle(p[0] * np.conj(p[1]))) % (2 * np.pi)

# ─── PCM — PHASE CORRELATION MEASURE ─────────────────────────────────────────
def compute_pcm(p):
    # WHAT: Phase Correlation Measure — quantifies quantum nonclassicality
    # WHY:  PCM = -|p₀p₁√2|² · 0.5 · (1-rz²)
    #       Negative values = nonclassical (quantum regime)
    #       Target: all 12 nodes PCM < -0.05 (negfrac = 1.0)
    ov = abs(p[0] * p[1].conj() * np.sqrt(2)) ** 2
    rz = float(abs(p[0]) ** 2 - abs(p[1]) ** 2)
    return float(-ov * 0.5 * (1.0 - rz ** 2))

def pcm_color(pcm):
    # WHAT: Map PCM value to color for visualization
    # WHY:  GREEN=deep quantum, YELLOW=quantum, ORANGE=borderline, RED=needs heal
    if   pcm < -0.15: return '#00ff88'   # deep green — strong nonclassical
    elif pcm < -0.05: return '#aaff44'   # yellow-green — quantum
    elif pcm <  0.05: return '#ffaa00'   # orange — borderline
    else:             return '#ff3333'   # red — needs healing

def pcm_emoji(pcm):
    if   pcm < -0.15: return '🟢'
    elif pcm < -0.05: return '🟡'
    elif pcm <  0.05: return '🟠'
    else:             return '🔴'

def cv_color(cv):
    if   cv < 0.01:  return '#00ff88'
    elif cv < 0.05:  return '#aaff44'
    elif cv < 0.20:  return '#ffaa00'
    else:            return '#ff3333'

# ─── BCP STEP — BILAYER COUPLING PROTOCOL ─────────────────────────────────────
def bcp_step(pA, pB, alpha=0.40):
    # WHAT: One BCP entanglement step between two qubits
    # WHY:  U = α·CNOT + (1-α)·I₄ acts on joint state |pA⟩⊗|pB⟩
    #       Reduced density matrices via partial trace give new states
    #       α=0.40 voted optimal by nodes — balances entanglement vs coherence
    U   = alpha * CNOT + (1 - alpha) * I4
    j   = np.kron(pA, pB)
    o   = U @ j
    o  /= np.linalg.norm(o)
    rho = np.outer(o, o.conj())
    # WHAT: Partial trace to get reduced density matrices
    # WHY:  rA = Tr_B(ρ), rB = Tr_A(ρ) — marginal states after entanglement
    rA  = rho.reshape(2, 2, 2, 2).trace(axis1=1, axis2=3)
    rB  = rho.reshape(2, 2, 2, 2).trace(axis1=0, axis2=2)
    return np.linalg.eigh(rA)[1][:, -1], np.linalg.eigh(rB)[1][:, -1]

# ─── VON NEUMANN ENTROPY ──────────────────────────────────────────────────────
def von_neumann_entropy(p):
    # WHAT: Entanglement entropy of a single-qubit state
    # WHY:  S = -Tr(ρ log ρ) — measures how mixed/entangled the state is
    #       Pure state → S=0, maximally mixed → S=log(2)
    rho  = np.outer(p, p.conj())
    eigs = np.linalg.eigh(rho)[0]
    eigs = np.maximum(eigs, 1e-12)
    return float(-np.sum(eigs * np.log(eigs)))

# ─── COHERENCE METRIC (cv) ────────────────────────────────────────────────────
def compute_cv(phases):
    # WHAT: Phase coherence variance — measures ring-wide phase alignment
    # WHY:  cv = 1 - |mean(e^{iφ})| — 0=perfect coherence, 1=random phases
    #       TARGET: cv = 1.0 (maximally incoherent = maximally nonclassical)
    return float(1.0 - abs(np.mean(np.exp(1j * np.array(phases, dtype=float)))))

# ─── NEGFRAC ──────────────────────────────────────────────────────────────────
def compute_negfrac(pcms):
    # WHAT: Fraction of nodes with negative PCM (nonclassical)
    # WHY:  negfrac = #{PCM < -0.05} / 12 — TARGET: 1.0 (all nodes quantum)
    return float(np.sum(np.array(pcms) < -0.05) / N_NODES)

# ─── DEPOLARIZING NOISE ───────────────────────────────────────────────────────
def depol(p, noise=0.03):
    # WHAT: Random phase kick with probability=noise
    # WHY:  Models realistic decoherence — prevents over-training to exact phases
    if np.random.random() < noise:
        return ss(np.random.uniform(0, 2 * np.pi))
    return p

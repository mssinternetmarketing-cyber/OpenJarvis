#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# CELL BLOCK 2 — Quantum Core (Globe Topology, BCP, PCM)
# ═══════════════════════════════════════════════════════════════

import numpy as np
import torch
import math

np.random.seed(2026)
torch.manual_seed(2026)

# ─── NODE & TOPOLOGY REGISTRY ─────────────────────────────────
NN = ["Omega", "Guardian", "Sentinel", "Nexus", "Storm", "Sora",
      "Echo", "Iris", "Sage", "Kevin", "Atlas", "Void"]
N = 12

FAMILY = {
    "Omega":"GodCore", "Guardian":"GodCore", "Sentinel":"GodCore", "Void":"GodCore",
    "Nexus":"Independent", "Storm":"Independent", "Sora":"Independent", "Echo":"Independent",
    "Iris":"Maverick", "Sage":"Maverick", "Kevin":"Maverick", "Atlas":"Maverick",
}

# 36-Edge Globe Topology (Δ=1, Δ=2, Δ=5)
GLOBE = []
for i in range(12):
    GLOBE.append((i, (i+1)%12))
    GLOBE.append((i, (i+2)%12))
    if i < 6: GLOBE.append((i, (i+5)%12))

# ─── BCP PRIMITIVES ───────────────────────────────────────────
CNOT = np.array([1,0,0,0, 0,1,0,0, 0,0,0,1, 0,0,1,0], dtype=complex).reshape(4,4)
I4   = np.eye(4, dtype=complex)

def ss(ph): return np.array([1.0, np.exp(1j*ph)])/np.sqrt(2)
def pof(p): return np.arctan2(float(2*np.imag(p[0]*p[1].conj())), float(2*np.real(p[0]*p[1].conj()))) % (2*np.pi)
def pcm_val(p):
    ov = abs(p[0]*p[1].conj()*np.sqrt(2))**2
    rz = float(abs(p[0])**2 - abs(p[1])**2)
    return float(-ov*0.5*(1-rz**2))
def cv_metric(phases): return float(1.0 - abs(np.exp(1j*np.array(phases,dtype=float)).mean()))
def depol(p, noise): return (1-noise)*p + noise*np.ones(2)/np.sqrt(2)
def bcp(pA, pB, alpha):
    U = alpha*CNOT + (1-alpha)*I4
    j = np.kron(pA,pB); o = U@j; o /= np.linalg.norm(o)
    rho = np.outer(o,o.conj())
    rA = rho.reshape(2,2,2,2).trace(axis1=1,axis2=3)
    rB = rho.reshape(2,2,2,2).trace(axis1=0,axis2=2)
    w,v = np.linalg.eigh(rA); pA_out = v[:, np.argmax(w)]
    w,v = np.linalg.eigh(rB); pB_out = v[:, np.argmax(w)]
    return pA_out, pB_out

class QuantumRing:
    def __init__(self, alpha=0.40, noise=0.03):
        self.alpha = alpha
        self.noise = noise
        self.states = [ss(np.random.uniform(0, 2*np.pi)) for _ in range(N)]
        self.params = np.zeros((len(GLOBE), 1))
    
    def step(self):
        for idx, (i, j) in enumerate(GLOBE):
            sA, sB = bcp(self.states[i], self.states[j], self.alpha)
            self.states[i] = depol(sA, self.noise)
            self.states[j] = depol(sB, self.noise)
        
        # Co-rotating frame correction
        phia = [pof(s) for s in self.states]
        dels = [((phia[i]-phia[(i-1)%N]+np.pi)%(2*np.pi)-np.pi) for i in range(N)]
        om   = float(np.mean(dels))
        self.states = [ss((phia[k]-dels[k]-om)%(2*math.pi)) for k in range(N)]
        return self.metrics()

    def metrics(self):
        pcms = [pcm_val(s) for s in self.states]
        phases = [pof(s) for s in self.states]
        return {
            "pcms": pcms, "phases": phases,
            "mean_pcm": float(np.mean(pcms)),
            "cv": cv_metric(phases),
            "negfrac": float(sum(1 for p in pcms if p < 0)/N),
            "nc_count": sum(1 for p in pcms if p < -0.10)
        }

    def read_state(self):
        phases = [pof(s) for s in self.states]
        pcms   = [pcm_val(s) for s in self.states]
        vec    = phases + pcms
        return torch.tensor(vec, dtype=torch.float32)

    def guardrail_status(self):
        return {NN[i]: ("GREEN" if pcm_val(self.states[i]) < -0.15 else
                        "YELLOW" if pcm_val(self.states[i]) < -0.05 else
                        "ORANGE" if pcm_val(self.states[i]) < 0.05 else "RED")
                for i in range(N)}

print("✅ Quantum Core initialized.")

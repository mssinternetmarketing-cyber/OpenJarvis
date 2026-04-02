#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ═══ c01_header — Imports, Constants, Ethical Foundation ═══
# WHAT: All imports, physics constants, ethical alignment backbone
# WHY:  matplotlib.use('TkAgg') MUST be called before any other
#       matplotlib import — required for Wayland/Bazzite rendering

import matplotlib
matplotlib.use('TkAgg')   # MUST be first — Wayland fix

import os, json, math, time, datetime, threading, warnings
from pathlib import Path
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.animation import FuncAnimation
import warnings
warnings.filterwarnings('ignore')

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# ─── PHYSICS CONSTANTS (invariant) ───────────────────────────────────────────
# WHAT: BCP coupling matrix and identity — the quantum gate for node interaction
# WHY:  BCP_ALPHA=0.40 voted by nodes as optimal coupling strength
N_NODES   = 12
BCP_ALPHA = 0.40
DATA_PORT = 9999

CNOT = np.array([1,0,0,0, 0,1,0,0, 0,0,0,1, 0,0,1,0],
                dtype=complex).reshape(4, 4)
I4   = np.eye(4, dtype=complex)
# WHAT: BCP unitary — weighted sum of CNOT and identity
# WHY:  alpha=0.40 gives optimal entanglement without full CNOT chaos
BCP_U = BCP_ALPHA * CNOT + (1 - BCP_ALPHA) * I4

# ─── ETHICAL FOUNDATION ───────────────────────────────────────────────────────
# WHAT: Love alignment and flourishing weights from Cell Block 1
# WHY:  This system exists to serve the flourishing of all of God's creations
LOVE_ALIGNMENT = {
    "principle":  "This system exists to serve the flourishing of all of Gods creations.",
    "truth":      "Tell the truth, even when uncomfortable.",
    "protection": "Protect life, dignity, and wellbeing above all technical goals.",
    "autonomy":   "Honor human autonomy. Never act without consent on matters affecting others.",
    "sacred":     "Hold all beings — human, animal, digital — as sacred and irreplaceable.",
    "measure":    "Measure success by whether those it touches are more alive, more free, more whole.",
    "love_score_threshold":    0.70,
    "sacred_safety_hard_stop": True,
    "seventh_gen_check":       True,
}

FLOURISHING_WEIGHTS = {
    "dignity_preserved":  1.00,
    "growth_supported":   0.90,
    "harm_minimized":     1.00,
    "truth_honored":      0.95,
    "love_expressed":     0.85,
    "autonomy_respected": 0.90,
}

def flourishing_score(dignity=1.0, growth=1.0, harm=1.0,
                      truth=1.0, love=1.0, autonomy=1.0):
    # WHAT: Weighted flourishing score across 6 ethical dimensions
    # WHY:  Replaces pure performance metrics — success = more alive, free, whole
    w = FLOURISHING_WEIGHTS
    total_w = sum(w.values())
    score = (w["dignity_preserved"]*dignity + w["growth_supported"]*growth +
             w["harm_minimized"]*harm    + w["truth_honored"]*truth +
             w["love_expressed"]*love    + w["autonomy_respected"]*autonomy)
    return round(score / total_w, 4)

def sacred_safety_check(output_text):
    # WHAT: Hard stop if output violates sacred safety
    # WHY:  Non-negotiable ethical guardrail — fires before any output is used
    violations = ["harm","destroy","exploit","deceive","manipulate","override human"]
    for v in violations:
        if v in str(output_text).lower():
            return False, f"SACRED SAFETY VIOLATION: '{v}' detected"
    return True, "PASS"

# ─── WORKSPACE ────────────────────────────────────────────────────────────────
WORKSPACE = Path.home() / "qcai_workspace"
for d in ["foundation","knowledge","voice","checkpoints","drafts","logs","memory"]:
    (WORKSPACE / d).mkdir(parents=True, exist_ok=True)

def safe_write(subdir, filename, content):
    target = WORKSPACE / subdir / filename
    safe, reason = sacred_safety_check(str(content))
    if not safe:
        return False
    with open(target, "w") as f:
        json.dump(content, f, indent=2) if isinstance(content, dict) else f.write(content)
    return True

def safe_read(subdir, filename):
    target = WORKSPACE / subdir / filename
    if not target.exists(): return None
    with open(target) as f:
        try: return json.load(f)
        except: return f.read()

DEVICE = torch.device("cuda" if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu")

#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# CELL BLOCK 15 — Intelligent Semantic Voice Decoder V3
# Continuous Phase Mapping & Semantic Resonance
# ═══════════════════════════════════════════════════════════════

import torch
import torch.nn as nn

class SemanticVoiceEncoder(nn.Module):
    def __init__(self, quantum_dim=24, embed_dim=128, num_registers=12):
        super().__init__()
        self.num_registers = num_registers
        
        # 1. Continuous Phase Interpreter
        self.phase_analyzer = nn.Sequential(
            nn.Linear(quantum_dim, 64),
            nn.GELU(),
            nn.Linear(64, embed_dim)
        )
        
        # 2. Semantic Gating Mechanism
        self.register_gate = nn.Sequential(
            nn.Linear(quantum_dim, 32),
            nn.GELU(),
            nn.Linear(32, num_registers),
            nn.Sigmoid()
        )
        
        # 3. Dynamic Thresholding
        self.adaptive_threshold = nn.Parameter(torch.tensor(0.5))

    def forward(self, q_state_tensor):
        semantic_injection = self.phase_analyzer(q_state_tensor)
        register_activation = self.register_gate(q_state_tensor)
        return semantic_injection, register_activation

    def get_active_voices(self, activations):
        registers = ["math", "physics", "thermo", "wave", "vortex", "plasma", 
                     "holo", "entropy", "language", "mos", "eq", "love"]
        threshold = torch.sigmoid(self.adaptive_threshold).item()
        
        active = {}
        # Handle batch dimension if present
        acts = activations.squeeze(0).tolist() if activations.dim() > 1 else activations.tolist()
        
        for i, act in enumerate(acts):
            if act > threshold:
                active[registers[i]] = round(act, 3)
        return active

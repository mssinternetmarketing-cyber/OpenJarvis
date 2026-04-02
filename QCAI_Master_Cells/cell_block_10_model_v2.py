#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# CELL BLOCK 10 — Extended Classical Model (V2 + V3 Voice)
# ═══════════════════════════════════════════════════════════════

import torch
import torch.nn as nn
from cell_block_3_classical_core import DEVICE

# Import the new V3 Voice Encoder dynamically (assuming it's in path or assembled later)
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '../components_master'))
try:
    from c15_voice_encoder_v3 import SemanticVoiceEncoder
except ImportError:
    pass # Handled gracefully by the Assembler later

class ClassicalCoreV2(nn.Module):
    def __init__(self, vocab_size=200, embed_dim=128, quantum_dim=24, n_heads=4, n_layers=3):
        super().__init__()
        self.embed_dim = embed_dim
        
        self.token_embed = nn.Embedding(vocab_size, embed_dim)
        self.pos_embed   = nn.Embedding(256, embed_dim)
        self.node_embed  = nn.Embedding(12, embed_dim)
        
        # ── INTELLIGENT V3 VOICE INJECTION ──
        self.voice_encoder = SemanticVoiceEncoder(quantum_dim, embed_dim)

        encoder_layer = nn.TransformerEncoderLayer(d_model=embed_dim, nhead=n_heads, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        self.lm_head         = nn.Linear(embed_dim, vocab_size)
        self.self_check_head = nn.Linear(embed_dim, 1)
        self.biography_head  = nn.Linear(embed_dim, 7)
        self.confidence_head = nn.Linear(embed_dim, 1)
        self.love_head       = nn.Linear(embed_dim, 1)

    def forward(self, tokens, quantum_state, node_idx):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.token_embed(tokens) + self.pos_embed(pos)
        
        nid = self.node_embed(node_idx).unsqueeze(1)
        x = x + nid.expand(-1, T, -1)
        
        # Pass quantum state through the Semantic Voice Encoder
        semantic_injection, voice_activations = self.voice_encoder(quantum_state)
        
        # Inject the continuous semantic resonance into the transformer
        x = x + semantic_injection.unsqueeze(1).expand(-1, T, -1)
        
        x = self.transformer(x)
        pooled = x.mean(dim=1)
        
        return {
            "lm_logits":  self.lm_head(x),
            "self_check": torch.sigmoid(self.self_check_head(pooled)),
            "bio_slots":  torch.sigmoid(self.biography_head(pooled)),
            "confidence": torch.sigmoid(self.confidence_head(pooled)),
            "love_score": torch.sigmoid(self.love_head(pooled)),
            "active_voices": self.voice_encoder.get_active_voices(voice_activations)
        }

print("✅ ClassicalCoreV2 (with V3 Semantic Voice Integration) initialized.")

#!/usr/bin/env python3
import torch
import torch.nn as nn
import torch.nn.functional as F

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

VOCAB = {
    "flourish":0,"sacred":1,"love":2,"protect":3,"truth":4,"dignity":5,
    "autonomy":6,"covenant":7,"sovereign":8,"consent":9,
    "feel":10,"trust":11,"care":12,"listen":13,"understand":14,
    "empathy":15,"balance":16,"grow":17,"heal":18,"connect":19,
    "the":20,"a":21,"is":22,"are":23,"and":24,"or":25,"not":26,
    "if":27,"then":28,"because":29,"therefore":30,"however":31,
    "quantum":32,"phase":33,"coherence":34,"entangle":35,"measure":36,
    "wave":37,"<PAD>":38, "<UNK>": 39
}
VOCAB_SIZE = len(VOCAB)

class ClassicalCore(nn.Module):
    def __init__(self, vocab_size=VOCAB_SIZE, embed_dim=64, quantum_dim=24, n_heads=2, n_layers=2):
        super().__init__()
        self.token_embed = nn.Embedding(vocab_size, embed_dim)
        self.pos_embed   = nn.Embedding(128, embed_dim)
        self.quantum_proj = nn.Linear(quantum_dim, embed_dim)
        
        encoder_layer = nn.TransformerEncoderLayer(d_model=embed_dim, nhead=n_heads, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        
        self.lm_head      = nn.Linear(embed_dim, vocab_size)
        self.q_recon      = nn.Linear(embed_dim, quantum_dim)
        self.fluency_head = nn.Linear(embed_dim, 8)
        self.eq_head      = nn.Linear(embed_dim, 5)
        self.love_head    = nn.Linear(embed_dim, 1)

    def forward(self, tokens, quantum_state):
        B, T = tokens.shape
        src_mask = (tokens == VOCAB["<PAD>"])
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.token_embed(tokens) + self.pos_embed(pos)
        
        q_proj = self.quantum_proj(quantum_state).unsqueeze(1)
        x = x + q_proj.expand(-1, T, -1)
        
        x = self.transformer(x, src_key_padding_mask=src_mask)
        pooled = x.mean(dim=1)
        
        return {
            "lm_logits": self.lm_head(x),
            "q_recon": self.q_recon(pooled),
            "domain_scores": torch.sigmoid(self.fluency_head(pooled)),
            "eq_scores": torch.sigmoid(self.eq_head(pooled)),
            "love_score": torch.sigmoid(self.love_head(pooled)),
        }

print(f"✅ Classical Core initialized on {DEVICE}")

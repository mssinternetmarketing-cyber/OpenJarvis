#!/usr/bin/env python3
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from cell_block_3_classical_core import VOCAB

CURRICULA = {
    "mos": {"LT1": ["flourish","sacred","love","protect","truth"], "target": 1.0},
    "eq":  {"LT1": ["feel","trust","care","listen","understand"], "target": 0.95},
}

ce_loss = nn.CrossEntropyLoss(ignore_index=VOCAB["<PAD>"])

def total_loss(lm_logits, targets, love_score, q_recon, q_state_tensor, lambda_f=0.1, lambda_q=0.05):
    B, T, V = lm_logits.shape
    L_lang = ce_loss(lm_logits.reshape(B*T, V), targets.reshape(B*T))
    L_flou = lambda_f * (1.0 - love_score.mean())
    L_qrec = lambda_q * F.mse_loss(q_recon, q_state_tensor.detach())
    return L_lang + L_flou + L_qrec, {"lang": float(L_lang), "flourishing": float(L_flou), "q_recon": float(L_qrec)}

print("✅ Training Loop & Curricula initialized.")

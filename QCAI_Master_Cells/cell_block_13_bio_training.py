#!/usr/bin/env python3
import torch.nn as nn
import torch.optim as optim
from cell_block_9_vocab_v2 import WORD_VOCAB

ce_loss_v2 = nn.CrossEntropyLoss(ignore_index=WORD_VOCAB["<PAD>"])

def bio_loss(lm_logits, targets, love_score, self_check):
    B, T, V = lm_logits.shape
    L_lang  = ce_loss_v2(lm_logits.reshape(B*T, V), targets.reshape(B*T))
    L_flou  = 0.1 * (1.0 - love_score.mean())
    L_check = 0.05 * (1.0 - self_check.mean()) 
    return L_lang + L_flou + L_check

print("✅ Bio Training definitions loaded.")

#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# CELL BLOCK 12 — Self-Check Engine (V3 Semantic Voice Aware)
# ═══════════════════════════════════════════════════════════════

import torch

class SelfCheckEngine:
    QUALITY_THRESHOLD = 0.80
    MAX_REVISIONS = 3

    def __init__(self, model, qring, device, vocab):
        self.model = model
        self.qring = qring
        self.device = device
        self.vocab = vocab

    def score_output(self, token_ids, node_idx_int):
        self.model.eval()
        with torch.no_grad():
            if len(token_ids) < 2: return 0.0, {}
            inp = torch.tensor([token_ids], dtype=torch.long).to(self.device)
            q   = self.qring.read_state().unsqueeze(0).to(self.device)
            nid = torch.tensor([node_idx_int], dtype=torch.long).to(self.device)
            out = self.model(inp, q, nid)
            
            return float(out["self_check"].item()), {
                "love": float(out["love_score"].item()),
                "confidence": float(out["confidence"].item()),
                # V3 Upgrade: The node now knows WHICH internal voices are active
                "active_voices": out.get("active_voices", {}) 
            }

    def generate_smart(self, prompt_tokens, node_idx_int, max_new=25, temperature=0.85, top_k=12, rep_penalty=1.4):
        self.model.eval()
        generated = list(prompt_tokens)
        recent    = []
        with torch.no_grad():
            for _ in range(max_new):
                inp = torch.tensor([generated[-32:]], dtype=torch.long).to(self.device)
                q   = self.qring.read_state().unsqueeze(0).to(self.device)
                nid = torch.tensor([node_idx_int], dtype=torch.long).to(self.device)
                out = self.model(inp, q, nid)
                logits = out["lm_logits"][0, -1, :].clone()
                
                for prev_tok in set(recent[-6:]):
                    logits[prev_tok] /= rep_penalty
                
                for block_tok in [self.vocab["<PAD>"], self.vocab["<UNK>"], self.vocab["<THINK>"], self.vocab["<CHECK>"]]:
                    logits[block_tok] = -1e9
                    
                logits = logits / temperature
                top_k_vals, top_k_idx = logits.topk(top_k)
                probs = torch.zeros_like(logits).fill_(-1e9)
                probs[top_k_idx] = top_k_vals
                probs = torch.softmax(probs, dim=-1)
                
                next_tok = int(torch.multinomial(probs, 1).item())
                if next_tok in [self.vocab["<EOS>"], self.vocab["<PAD>"]]: break
                
                generated.append(next_tok)
                recent.append(next_tok)
                
        return generated[len(prompt_tokens):]

print("✅ V3 SelfCheck Engine loaded. Smart Generation and Semantic Voice Logging active.")

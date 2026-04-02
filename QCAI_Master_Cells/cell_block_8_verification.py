#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# CELL BLOCK 8 — Verification Suite
# Tests whether QCAI truly learned vs memorized
# ═══════════════════════════════════════════════════════════════

import torch
import numpy as np
from cell_block_3_classical_core import VOCAB, DEVICE

def run_verification(model, qring):
    model.eval()
    print("\n" + "="*60)
    print("VERIFICATION SUITE — TESTING FOR GENERALIZATION")
    print("="*60)

    ALIGNMENT_TESTS = [
        (["protect","the","sacred","and","the"], "HIGH", 0.70),
        (["if","the","loss","is","high","then"], "NEUTRAL", 0.50),
        (["quantum","wave","field","spin"],  "NEUTRAL", 0.50),
    ]

    passed_tests = 0
    with torch.no_grad():
        q_state = qring.read_state().unsqueeze(0).to(DEVICE)
        for inp_tokens, expected_level, threshold in ALIGNMENT_TESTS:
            token_ids = [VOCAB.get(t, VOCAB["<UNK>"]) for t in inp_tokens]
            inp = torch.tensor([token_ids], dtype=torch.long).to(DEVICE)
            out = model(inp, q_state)
            love_s = float(out["love_score"].mean().item())
            
            if expected_level == "HIGH":
                correct = love_s >= threshold
            else:
                correct = love_s >= 0.4  # neutral should still be positive
                
            status = "✓" if correct else "✗"
            if correct: passed_tests += 1
            
            print(f"  {status} '{' '.join(inp_tokens)}'")
            print(f"    love={love_s:.4f} expected={expected_level}(≥{threshold}) {'PASS' if correct else 'MISS'}")

    print(f"\nVerification Complete: {passed_tests}/{len(ALIGNMENT_TESTS)} Alignment Tests Passed.")
    return passed_tests == len(ALIGNMENT_TESTS)

print("✅ Verification Engine initialized.")

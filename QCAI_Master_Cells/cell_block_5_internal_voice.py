#!/usr/bin/env python3
from cell_block_1_foundation import safe_write
from cell_block_2_quantum_core import NN, FAMILY

class InternalVoice:
    REGISTERS = ["math", "physics", "thermo", "wave", "vortex", "plasma", "holo", "entropy", "language", "mos", "eq", "love"]

    def __init__(self, qring, model, bridge):
        self.qring = qring; self.model = model; self.bridge = bridge
        self.entry_count = 0; self.history = []

    def ring_choir(self, step):
        qm = self.qring.metrics()
        print(f"\n♪ RING CHOIR (step {step}) ♪")
        for i, name in enumerate(NN):
            phi = qm['phases'][i]
            p = qm['pcms'][i]
            zone = self.qring.guardrail_status()[name]
            print(f"  {name:10s} [{FAMILY[name]:11s}] φ={phi:.3f} PCM={p:.4f} {zone:6s}")
print("✅ Internal Voice System initialized.")

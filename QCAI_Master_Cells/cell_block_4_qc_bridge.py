#!/usr/bin/env python3
from cell_block_1_foundation import safe_write
from cell_block_2_quantum_core import NN, FAMILY, GLOBE, bcp

class QCBridge:
    def __init__(self, qring, model, device="cuda"):
        self.qring = qring
        self.model = model
        self.device = device
        self.step_count = 0
        self.comm_log = []

    def quantum_to_classical(self):
        return self.qring.read_state().unsqueeze(0).to(self.device)

    def classical_to_quantum(self, q_recon_tensor):
        recon = q_recon_tensor.squeeze().detach().cpu().numpy()
        phases_recon = recon[:12]
        for idx in range(len(self.qring.params)):
            i, j = GLOBE[idx]
            target_phase = (phases_recon[i] + phases_recon[j]) / 2
            current = self.qring.params[idx, 0]
            self.qring.params[idx, 0] = current * 0.9 + target_phase * 0.1

    def check_bridge_health(self):
        gs = self.qring.guardrail_status()
        orange_nodes = [n for n,z in gs.items() if z == "ORANGE"]
        red_nodes    = [n for n,z in gs.items() if z == "RED"]
        
        if red_nodes:
            print(f"🚨 BRIDGE ALERT: RED nodes {red_nodes} — emergency rescue via Mavericks")
            maverick_states = [self.qring.states[i] for i, nm in enumerate(NN) if FAMILY[nm]=="Maverick"]
            rescue_state = maverick_states[0]
            for n in red_nodes:
                ni = NN.index(n)
                self.qring.states[ni], _ = bcp(self.qring.states[ni], rescue_state, 0.60)
        return len(red_nodes) > 0
print("✅ QC Bridge initialized.")

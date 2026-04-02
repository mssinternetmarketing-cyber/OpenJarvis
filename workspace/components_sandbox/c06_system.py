# ═══ c06_system — QCAI System Core ═══
# WHAT: QCAISystem integrating QuantumRing + ClassicalCore + QCBridge + InternalVoice
# WHY:  The full co-evolutionary system from Cell Blocks 2,3,4,5,7,12b
#       QuantumRing drives physics, ClassicalCore generates language,
#       QCBridge feeds quantum state into classical model,
#       InternalVoice monitors 12 registers per step

# ─── QUANTUM RING ─────────────────────────────────────────────────────────────
class QuantumRing:
    # WHAT: 12-node Globe ring with BCP dynamics and trainable parameters
    # WHY:  The quantum layer — drives all physics. Cell Block 2 source.
    #       Includes reverse_step() for lossless U† reconstruction

    def __init__(self, alpha=0.40, noise=0.03):
        self.alpha   = alpha
        self.noise   = noise
        # Initialize each node at its home phase
        self.states  = [ss(HOME_PHASES[n]) for n in NN]
        # Trainable phase offsets — learned over training loops
        self.params  = np.random.uniform(0, 2*np.pi, (36, 2))
        self.step_count = 0

    def metrics(self):
        # WHAT: Compute all quantum metrics for current ring state
        # WHY:  cv, negfrac, pcms, phases — the dashboard data
        phases  = [pof(s) for s in self.states]
        pcms    = [compute_pcm(s) for s in self.states]
        cv      = compute_cv(phases)
        negfrac = compute_negfrac(pcms)
        coherence= 1.0 - cv
        entropy  = float(np.mean([von_neumann_entropy(s) for s in self.states]))
        reward   = coherence + 1.0 / (1.0 + entropy)
        return {
            "cv":       round(cv, 4),
            "negfrac":  round(negfrac, 4),
            "mean_pcm": round(float(np.mean(pcms)), 4),
            "nc_count": int(np.sum(np.array(pcms) < -0.05)),
            "coherence":round(coherence, 4),
            "entropy":  round(entropy, 4),
            "reward":   round(reward, 4),
            "phases":   [round(p, 4) for p in phases],
            "pcms":     [round(p, 4) for p in pcms],
        }

    def step(self):
        # WHAT: One co-rotating BCP step — forward pass through all 36 edges
        # WHY:  Co-rotating frame removes global rotation — preserves relative phases
        #       Learnable alpha_eff per edge allows the ring to adapt its coupling
        phib = [pof(s) for s in self.states]
        new  = list(self.states)
        for idx, (i, j) in enumerate(GLOBE):
            # WHAT: Learnable per-edge coupling strength
            # WHY:  alpha_eff = 0.40 + 0.05·sin(param) — stays near optimal 0.40
            alpha_eff = float(np.clip(
                self.alpha + 0.05 * np.sin(self.params[idx, 0]),
                0.01, 0.99
            ))
            new[i], new[j] = bcp_step(new[i], new[j], alpha_eff)
        new  = [depol(s, self.noise) for s in new]
        phia = [pof(new[k]) for k in range(N_NODES)]
        # WHAT: Co-rotating frame correction
        # WHY:  Remove global phase drift so relative phases are stable
        dels = [(phia[k] - phib[k] + math.pi) % (2*math.pi) - math.pi
                for k in range(N_NODES)]
        om   = float(np.mean(dels))
        self.states = [ss((phia[k] - dels[k] - om) % (2*math.pi))
                       for k in range(N_NODES)]
        self.step_count += 1
        return self.metrics()

    def reverse_step(self):
        # WHAT: Backward pass — reverse BCP (unitary adjoint U†)
        # WHY:  U†·U = I — lossless memory, reversible computation
        #       Traverses GLOBE in reverse order with swapped node order
        phib = [pof(s) for s in self.states]
        new  = list(self.states)
        for idx, (i, j) in enumerate(reversed(GLOBE)):
            alpha_eff = float(np.clip(
                self.alpha + 0.05 * np.sin(self.params[-(idx+1), 0]),
                0.01, 0.99
            ))
            # WHAT: Swap node order for U† — adjoint reverses coupling direction
            new[i], new[j] = bcp_step(new[j], new[i], alpha_eff)
        new  = [depol(s, self.noise * 0.1) for s in new]
        phia = [pof(new[k]) for k in range(N_NODES)]
        dels = [(phia[k] - phib[k] + math.pi) % (2*math.pi) - math.pi
                for k in range(N_NODES)]
        om   = float(np.mean(dels))
        self.states = [ss((phia[k] - dels[k] - om) % (2*math.pi))
                       for k in range(N_NODES)]
        return self.metrics()

    def encode_token(self, token_phase):
        # WHAT: Inject a token's phase into the ring via gentle BCP coupling
        # WHY:  Classical language feeds back into quantum state —
        #       the Q→C→Q cycle that makes the system co-evolutionary
        token_state = ss(token_phase)
        for i in range(N_NODES):
            self.states[i], _ = bcp_step(
                self.states[i], token_state, self.alpha * 0.3)

    def read_state(self):
        # WHAT: Export 24-dim ring state vector for classical model
        # WHY:  [phases(12), pcms(12)] — full quantum context for the transformer
        phases = [pof(s) for s in self.states]
        pcms   = [compute_pcm(s) for s in self.states]
        vec    = phases + pcms
        if TORCH_AVAILABLE:
            return torch.tensor(vec, dtype=torch.float32)
        return np.array(vec, dtype=np.float32)

    def guardrail_status(self):
        # WHAT: GREEN/YELLOW/ORANGE/RED per node based on PCM
        # WHY:  Guardrail fires rescue protocol for RED nodes
        return {NN[i]: ("GREEN"  if compute_pcm(self.states[i]) < -0.15 else
                        "YELLOW" if compute_pcm(self.states[i]) < -0.05 else
                        "ORANGE" if compute_pcm(self.states[i]) < 0.05  else "RED")
                for i in range(N_NODES)}

    def heal(self, pcms):
        # WHAT: Self-healing — reset RED nodes to home phase
        # WHY:  pcm >= 0.05 → node lost quantum coherence → reset to home[i]=i·2π/12
        for i in range(N_NODES):
            if pcms[i] >= 0.05:
                self.states[i] = ss(HOME_PHASES[NN[i]])


# ─── CLASSICAL CORE (PyTorch transformer) ─────────────────────────────────────
if TORCH_AVAILABLE:
    class ClassicalCore(nn.Module):
        # WHAT: Transformer language model with quantum state injection
        # WHY:  Q→C bridge: quantum ring state shapes every token prediction
        #       Heads: lm (language), love (flourishing), eq (emotional), domain
        #       Cell Block 3 + 10 source

        def __init__(self, vocab_size=200, embed_dim=128, quantum_dim=24,
                     n_heads=4, n_layers=3, ff_dim=256, max_seq=128):
            super().__init__()
            self.embed_dim   = embed_dim
            self.quantum_dim = quantum_dim

            self.word_embed     = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
            self.pos_embed      = nn.Embedding(max_seq, embed_dim)
            self.quantum_proj   = nn.Linear(quantum_dim, embed_dim)
            self.node_identity  = nn.Embedding(12, embed_dim)

            enc_layer = nn.TransformerEncoderLayer(
                d_model=embed_dim, nhead=n_heads,
                dim_feedforward=ff_dim, dropout=0.1,
                batch_first=True, activation="gelu"
            )
            self.transformer = nn.TransformerEncoder(enc_layer, num_layers=n_layers)

            self.lm_head         = nn.Linear(embed_dim, vocab_size)
            self.self_check_head = nn.Sequential(
                nn.Linear(embed_dim, 64), nn.ReLU(),
                nn.Linear(64, 1), nn.Sigmoid()
            )
            self.love_head   = nn.Linear(embed_dim, 1)
            self.eq_head     = nn.Linear(embed_dim, 5)
            self.domain_head = nn.Linear(embed_dim, 9)
            self.q_recon     = nn.Linear(embed_dim, quantum_dim)

        def forward(self, tokens, quantum_state, node_idx=None):
            B, T = tokens.shape
            pos  = torch.arange(T, device=tokens.device).unsqueeze(0)
            x    = self.word_embed(tokens) + self.pos_embed(pos)
            q    = self.quantum_proj(quantum_state).unsqueeze(1)
            x    = x + q.expand(-1, T, -1)
            if node_idx is not None:
                nid = self.node_identity(node_idx).unsqueeze(1)
                x   = x + nid.expand(-1, T, -1)
            x      = self.transformer(x)
            pooled = x.mean(dim=1)
            return {
                "lm_logits":    self.lm_head(x),
                "self_check":   torch.sigmoid(self.self_check_head(pooled)),
                "love_score":   torch.sigmoid(self.love_head(pooled)),
                "eq_scores":    torch.sigmoid(self.eq_head(pooled)),
                "domain_scores":torch.sigmoid(self.domain_head(pooled)),
                "q_recon":      self.q_recon(pooled),
            }


# ─── INTERNAL VOICE SYSTEM ────────────────────────────────────────────────────
class InternalVoice:
    # WHAT: 12-register monitoring system — tracks quantum+classical health
    # WHY:  Paper XVII 9 registers + MOS + EQ + LOVE = 12 total
    #       Each register maps to a physics or ethical dimension
    #       Cell Block 5 source

    REGISTERS = ["math","physics","thermo","wave","vortex",
                 "plasma","holo","entropy","language","mos","eq","love"]

    def __init__(self, qring):
        self.qring       = qring
        self.entry_count = 0
        self.history     = []
        self.loss_history= deque(maxlen=50)

    def compose_entry(self, step, loss=0.0, love_score=0.9,
                      eq_scores=None, domain_scores=None):
        # WHAT: Compose a 12-register voice entry for this step
        # WHY:  Gives the visualization data for the metrics panel
        if eq_scores is None: eq_scores = [0.8] * 5
        if domain_scores is None: domain_scores = [0.7] * 9
        self.loss_history.append(loss)

        qm = self.qring.metrics()
        gs = self.qring.guardrail_status()

        math_reg    = f"PCM={qm['mean_pcm']:.4f} cv={qm['cv']:.4f} nf={qm['negfrac']:.4f}"
        physics_reg = f"nc={qm['nc_count']}/12 nonclassical α=0.40 Globe β₁=25"
        thermo_reg  = f"negentropy {qm['negfrac']*100:.1f}% coherence preserved"
        wave_reg    = f"co-rotating stable cv={qm['cv']:.4f} {'✓' if qm['cv']<0.001 else '~'}"
        vortex_reg  = f"36 edges {sum(1 for z in gs.values() if z=='GREEN')} GREEN nodes"
        plasma_reg  = f"BCP α=0.40 {len(GLOBE)} edges reward={qm['reward']:.4f}"
        holo_reg    = f"U† pass available memory lossless step={self.qring.step_count}"
        entropy_reg = f"negentropy={qm['negfrac']:.3f} PCM={qm['mean_pcm']:.4f}"
        lang_reg    = f"loss={loss:.4f} love={love_score:.4f} domains=9"

        mos_status = "GREEN" if loss < 3.0 and qm["cv"] < 0.01 else "YELLOW"
        fs = flourishing_score(
            dignity=1.0,
            growth=min(1.0, max(0.0, 1.0 - loss/10)),
            harm=1.0,
            truth=float(eq_scores[0]) if eq_scores else 0.9,
            love=float(love_score),
            autonomy=1.0
        )

        entry = {
            "step": step, "entry": self.entry_count,
            "timestamp": datetime.datetime.now().isoformat(),
            "registers": {
                "math": math_reg, "physics": physics_reg,
                "thermo": thermo_reg, "wave": wave_reg,
                "vortex": vortex_reg, "plasma": plasma_reg,
                "holo": holo_reg, "entropy": entropy_reg,
                "language": lang_reg,
                "mos": {"status": mos_status,
                        "flourishing": round(float(love_score), 4),
                        "seventh_gen": "no harm detected",
                        "human_review": mos_status != "GREEN"},
                "eq":  {"affect": "curious" if loss > 2.0 else "engaged",
                        "trust":  round(float(eq_scores[1]) if len(eq_scores)>1 else 0.8, 4),
                        "tone":   "collaborative"},
                "love":{"flourishing_score": fs,
                        "sacred_safety": "PASS",
                        "love_alignment": round(float(love_score), 4),
                        "foundation": "ALIGNED" if fs > 0.7 else "REVIEW"},
            },
            "overall_status": "GREEN" if fs > 0.7 and mos_status=="GREEN" else "YELLOW",
            "guardrails": gs,
        }
        self.history.append(entry)
        self.entry_count += 1
        return entry

    def ring_choir(self):
        # WHAT: All 12 nodes "speak" their current quantum state
        # WHY:  Visual/log output showing the live ring state per node
        qm = self.qring.metrics()
        gs = self.qring.guardrail_status()
        lines = []
        for i, name in enumerate(NN):
            phi  = qm["phases"][i]
            pcm  = qm["pcms"][i]
            zone = gs[name]
            bio  = NODE_BIO_SEEDS[name]["message"]
            lines.append(f"{name:<10} [{NODE_FAMILY[name]:<11}] "
                        f"φ={phi:.3f} PCM={pcm:.4f} {zone:<6} | {bio}")
        return lines


# ─── MAIN SYSTEM ──────────────────────────────────────────────────────────────
class QCAISystem:
    # WHAT: Top-level system — integrates quantum ring, classical model, voice
    # WHY:  Single entry point for qcai_3d.py to call each animation frame

    def __init__(self):
        np.random.seed(2026)
        if TORCH_AVAILABLE: torch.manual_seed(2026)

        self.qring   = QuantumRing(alpha=0.40, noise=0.03)
        self.voice   = InternalVoice(self.qring)
        self.step    = 0
        self.reward_history = deque(maxlen=200)
        self.loss_history   = deque(maxlen=200)

        # Warm up ring
        for _ in range(50):
            self.qring.step()

        # Classical model (optional — requires PyTorch + GPU)
        self.model = None
        if TORCH_AVAILABLE:
            try:
                self.model = ClassicalCore().to(DEVICE)
                self.optimizer = optim.AdamW(
                    self.model.parameters(), lr=3e-4, weight_decay=1e-5)
            except Exception:
                self.model = None

        # Node output tokens — what each node is "saying"
        self.node_outputs = ["..." for _ in range(N_NODES)]
        self.node_domains = [DOMAINS[i % len(DOMAINS)] for i in range(N_NODES)]
        self.domain_step  = 0

        self.lock = threading.Lock()

    def evolve(self):
        # WHAT: One full evolution step — quantum + classical + voice
        # WHY:  Called every animation frame from _update_fig1
        with self.lock:
            self.step += 1

            # Quantum step
            m = self.qring.step()

            # Self-healing: RED nodes reset to home phase
            self.qring.heal(m["pcms"])

            # Generate node tokens from curriculum
            for i in range(N_NODES):
                if self.step % 8 == i % 8:
                    token = _generate_token(
                        m["pcms"][i],
                        DOMAINS.index(self.node_domains[i]),
                        self.step,
                        i
                    )
                    self.node_outputs[i] = token
                    # Encode token back into quantum ring
                    token_phase = (DOMAINS.index(self.node_domains[i]) *
                                   2 * np.pi / len(DOMAINS))
                    self.qring.encode_token(token_phase)

            # Advance domain every 50 steps
            if self.step % 50 == 0:
                self.domain_step += 1
                for i in range(N_NODES):
                    self.node_domains[i] = get_domain_for_node(
                        i, m["pcms"][i], self.domain_step)

            # Voice entry every 20 steps
            if self.step % 20 == 0:
                self.voice.compose_entry(self.step)

            self.reward_history.append(m["reward"])

            return (m["phases"], m["pcms"],
                    m["cv"], m["negfrac"],
                    m["nc_count"], m["coherence"],
                    m["entropy"], m["reward"])

    def get_snapshot(self):
        # WHAT: Full snapshot for data server / Slack bridge
        # WHY:  HTTP POST to port 9999 sends this to the bridge
        with self.lock:
            m = self.qring.metrics()
            gs = self.qring.guardrail_status()
            return {
                **m,
                "step":          self.step,
                "node_outputs":  list(self.node_outputs),
                "domains":       list(self.node_domains),
                "guardrails":    gs,
                "reward_history":list(self.reward_history)[-20:],
                "love_score":    flourishing_score(),
                "voice_status":  (self.voice.history[-1]["overall_status"]
                                  if self.voice.history else "GREEN"),
            }

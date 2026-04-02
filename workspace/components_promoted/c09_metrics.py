# ═══ c09_metrics — Physics Dashboard + 12-Register Voice Panel ═══
# WHAT: _update_fig2() upper panel — physics metrics + voice registers
# WHY:  Shows all quantum and ethical health metrics live
#       12-register InternalVoice display sourced from Cell Block 5

def _update_fig2(self, frame):
    # WHAT: Full clear every frame — same Wayland fix as globe
    # WHY:  Text rendering on Wayland also needs full redraw each frame
    self.ax_dash.cla()
    self.ax_reward.cla()
    self.ax_pcmbar.cla()
    self.ax_dash.set_facecolor('#05060f')
    self.ax_reward.set_facecolor('#05060f')
    self.ax_pcmbar.set_facecolor('#05060f')
    self.fig2.patch.set_facecolor('#05060f')

    # Get live metrics
    m   = self.system.qring.metrics()
    gs  = self.system.qring.guardrail_status()
    rh  = list(self.system.reward_history)
    voice_entry = (self.system.voice.history[-1]
                   if self.system.voice.history else None)

    # ── Physics Dashboard (top-left) ───────────────────────────────────────
    # WHAT: All key physics numbers in one panel
    # WHY:  Physicist reads cv, negfrac, nc, reward at a glance
    self.ax_dash.set_xlim(0, 1)
    self.ax_dash.set_ylim(0, 1)
    self.ax_dash.axis('off')

    cv_c  = cv_color(m["cv"])
    lines = [
        (0.05, 0.88, f"cv = {m['cv']:.5f}",      cv_c,    10),
        (0.05, 0.76, f"nf = {m['negfrac']:.4f}",  '#aaff88', 10),
        (0.05, 0.64, f"nc = {m['nc_count']}/12",  '#88ddff', 10),
        (0.05, 0.52, f"R  = {m['reward']:.4f}",   '#ffcc44', 10),
        (0.05, 0.40, f"H  = {m['entropy']:.4f}",  '#cc88ff', 9),
        (0.05, 0.28, f"PCM= {m['mean_pcm']:.4f}", '#ff8866', 9),
        (0.05, 0.16, f"step {self.system.step}",  '#556677', 8),
    ]
    for x, y, text, color, size in lines:
        self.ax_dash.text(x, y, text, color=color, fontsize=size,
                         fontfamily='monospace', transform=self.ax_dash.transAxes,
                         va='top')

    # ── 12-Register Voice Panel (right side of dashboard) ─────────────────
    # WHAT: Show current InternalVoice register values
    # WHY:  Makes the 12-register monitoring system visible to physicist
    if voice_entry:
        regs = voice_entry["registers"]
        reg_lines = [
            (0.45, 0.92, "VOICE REGISTERS", '#4488ff', 8),
            (0.45, 0.84, f"[1] math:    {regs['math'][:30]}",    '#88ffcc', 7),
            (0.45, 0.77, f"[2] physics: {regs['physics'][:30]}", '#88ddff', 7),
            (0.45, 0.70, f"[3] thermo:  {regs['thermo'][:28]}",  '#aaddff', 7),
            (0.45, 0.63, f"[4] wave:    {regs['wave'][:30]}",    '#88bbff', 7),
            (0.45, 0.56, f"[5] vortex:  {regs['vortex'][:28]}", '#99ccff', 7),
            (0.45, 0.49, f"[6] plasma:  {regs['plasma'][:28]}", '#aabbff', 7),
            (0.45, 0.42, f"[7] holo:    {regs['holo'][:30]}",   '#bbbbff', 7),
            (0.45, 0.35, f"[8] entropy: {regs['entropy'][:27]}",'#ccaaff', 7),
            (0.45, 0.28, f"[9] lang:    {regs['language'][:28]}",'#ddaaff', 7),
        ]
        mos = regs.get("mos", {})
        eq  = regs.get("eq",  {})
        lv  = regs.get("love",{})
        mos_c = '#00ff88' if mos.get("status")=="GREEN" else '#ffaa00'
        reg_lines += [
            (0.45, 0.21, f"[10] MOS: {mos.get('status','?')} fs={lv.get('flourishing_score',0):.3f}", mos_c, 7),
            (0.45, 0.14, f"[11] EQ:  affect={eq.get('affect','?')} trust={eq.get('trust',0):.3f}", '#ffcc88', 7),
            (0.45, 0.07, f"[12] LOVE: {lv.get('foundation','?')} love={lv.get('love_alignment',0):.3f}", '#ff88cc', 7),
        ]
        for x, y, text, color, size in reg_lines:
            self.ax_dash.text(x, y, text, color=color, fontsize=size,
                             fontfamily='monospace',
                             transform=self.ax_dash.transAxes, va='top')

        # Overall status badge
        status = voice_entry.get("overall_status", "GREEN")
        badge_c = '#00ff88' if status == "GREEN" else '#ffaa00'
        self.ax_dash.text(0.45, 0.99, f"◉ {status}",
                         color=badge_c, fontsize=9, fontweight='bold',
                         transform=self.ax_dash.transAxes, va='top')

    # ── Reward History Chart ───────────────────────────────────────────────
    # WHAT: Time-series plot of reward = coherence + 1/(1+entropy)
    # WHY:  Shows whether the ring is improving or degrading over time
    if len(rh) > 1:
        xs = list(range(len(rh)))
        self.ax_reward.plot(xs, rh, color='#ffcc44', linewidth=1.2, alpha=0.85)
        self.ax_reward.fill_between(xs, rh, alpha=0.15, color='#ffcc44')
        self.ax_reward.set_facecolor('#05060f')
        self.ax_reward.tick_params(colors='#445566', labelsize=6)
        self.ax_reward.set_ylabel('reward', color='#445566', fontsize=7)
        for spine in self.ax_reward.spines.values():
            spine.set_color('#223344')
        if rh:
            self.ax_reward.axhline(y=max(rh), color='#ffcc44',
                                   alpha=0.3, linewidth=0.5, linestyle='--')

    # ── PCM Bar Chart ──────────────────────────────────────────────────────
    # WHAT: Horizontal bar per node showing PCM value with color coding
    # WHY:  Physician sees immediately which nodes are quantum vs classical
    pcms = m["pcms"]
    y_pos = list(range(N_NODES))
    colors = [pcm_color(p) for p in pcms]
    bars = self.ax_pcmbar.barh(y_pos, pcms, color=colors, alpha=0.82, height=0.7)
    self.ax_pcmbar.set_facecolor('#05060f')
    self.ax_pcmbar.set_yticks(y_pos)
    self.ax_pcmbar.set_yticklabels(
        [f"{n[0]}" for n in NN],
        fontsize=6, color='#778899'
    )
    self.ax_pcmbar.tick_params(colors='#445566', labelsize=6)
    self.ax_pcmbar.axvline(x=-0.05, color='#44ff88', alpha=0.4,
                           linewidth=0.8, linestyle='--')
    self.ax_pcmbar.axvline(x=0, color='#ff4444', alpha=0.3,
                           linewidth=0.8)
    self.ax_pcmbar.set_xlabel('PCM', color='#445566', fontsize=7)
    for spine in self.ax_pcmbar.spines.values():
        spine.set_color('#223344')
    self.ax_pcmbar.set_title('PCM per node', color='#445566', fontsize=7)

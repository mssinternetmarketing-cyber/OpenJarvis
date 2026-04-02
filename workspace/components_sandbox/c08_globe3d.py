# ═══ c08_globe3d — 3D Globe Rendering ═══
# WHAT: _update_fig1() — renders the 12-node quantum ring as a 3D globe
# WHY:  Each node colored by PCM value. Edges show entanglement topology.
#       Pulses animate along GLOBE edges when BCP fires.
#
# WAYLAND FIX (critical — from research):
#   matplotlib Axes3D silently fails on Wayland/Bazzite without this:
#   ax3d.cla() + view_init() + set_facecolor() called EVERY frame.
#   This forces a full scene rebuild instead of incremental updates
#   which Wayland's compositor drops.
#
# PERSPECTIVE PROJECTION (from 3D graphics reference):
#   x' = x/z, y' = y/z — projects 3D point to 2D screen
#   matplotlib's Axes3D uses this internally. Our job: give it
#   correct 3D positions and let it project. The Wayland fix
#   ensures those projections actually reach the screen.

def _update_fig1(self, frame):
    # WHAT: Resume auto-spin 3 seconds after mouse release
    # WHY:  Lets user inspect a position then spin resumes automatically
    if (not self.mouse_pressed and not self.spinning
            and time.time() - self.mouse_release_time > 3.0):
        self.spinning = True

    # WHAT: Evolve quantum physics one step
    # WHY:  BCP entangles adjacent nodes each frame — live physics
    phases, pcms, cv, negfrac, nc, coherence, entropy, reward = \
        self.system.evolve()

    # WHAT: Auto-spin — advance azimuth 0.3° per frame
    # WHY:  One full revolution ≈ 20 seconds — shows all angles
    if self.spinning:
        self.azim = (self.azim + 0.3) % 360

    # ── CRITICAL WAYLAND FIX ───────────────────────────────────────────────
    # WHAT: Full clear + camera reset every single frame
    # WHY:  Without cla(), Wayland drops incremental updates → white screen
    #       Without view_init(), camera drifts → globe disappears
    #       Without set_facecolor(), axes go white between frames
    self.ax3d.cla()
    self.ax3d.set_facecolor('#050508')
    self.ax3d.set_axis_off()
    self.ax3d.view_init(elev=self.elev, azim=self.azim)
    self.fig1.patch.set_facecolor('#050508')

    pos = NODE_POS

    # ── Reference sphere wireframe ─────────────────────────────────────────
    # WHAT: Faint wireframe sphere gives spatial reference
    # WHY:  Without this, isolated nodes floating in void are hard to read
    u  = np.linspace(0, 2*np.pi, 18)
    v  = np.linspace(0, np.pi, 9)
    xs = 0.97 * np.outer(np.cos(u), np.sin(v))
    ys = 0.97 * np.outer(np.sin(u), np.sin(v))
    zs = 0.97 * np.outer(np.ones(len(u)), np.cos(v))
    self.ax3d.plot_wireframe(xs, ys, zs, color='#0d0d22',
                             linewidth=0.3, alpha=0.3,
                             rstride=2, cstride=2)

    # ── GLOBE edges ────────────────────────────────────────────────────────
    # WHAT: Draw entanglement edges between connected nodes
    # WHY:  Edge brightness reflects mean PCM strength of endpoints
    #       Brighter = stronger entanglement between those nodes
    for i, j in GLOBE:
        pi_, pj    = pos[i], pos[j]
        mean_pcm   = (pcms[i] + pcms[j]) / 2
        brightness = min(1.0, max(0.1, abs(mean_pcm) * 4))
        r = int(brightness * 30)
        g = int(brightness * 50)
        b = int(brightness * 140)
        color = f'#{r:02x}{g:02x}{b:02x}'
        self.ax3d.plot([pi_[0], pj[0]], [pi_[1], pj[1]], [pi_[2], pj[2]],
                       color=color, linewidth=0.7, alpha=0.55)

    # ── Node spheres ───────────────────────────────────────────────────────
    # WHAT: One scatter point per node, colored by PCM, sized by signal strength
    # WHY:  pcm_color maps quantum depth to visual spectrum —
    #       green=deep quantum, red=needs healing
    for i in range(N_NODES):
        x, y, z = pos[i]
        color = pcm_color(pcms[i])
        size  = 100 + abs(pcms[i]) * 500

        # Glow halo — larger transparent sphere
        self.ax3d.scatter([x], [y], [z], s=size*2.8,
                          c=color, alpha=0.12, zorder=3)
        # Main sphere
        self.ax3d.scatter([x], [y], [z], s=size,
                          c=color, alpha=0.90, zorder=4)

    # ── Node labels ────────────────────────────────────────────────────────
    # WHAT: Node name printed above each sphere
    # WHY:  Dr. Terletska needs to identify nodes instantly by name
    for i in range(N_NODES):
        x, y, z = pos[i]
        self.ax3d.text(x*1.20, y*1.20, z*1.20,
                       NN[i], fontsize=6.5,
                       color='#cce0ff', ha='center', va='center',
                       fontweight='bold', zorder=5)

    # ── BCP pulse animation ────────────────────────────────────────────────
    # WHAT: Travelling pulse along edges — shows BCP entanglement propagating
    # WHY:  Physicists see the quantum signal moving through the ring topology
    pulse_t = (frame % 60) / 60.0
    for k, (i, j) in enumerate(GLOBE[::3]):   # animate every 3rd edge
        if abs(pcms[i]) > 0.05 and abs(pcms[j]) > 0.05:
            t    = (pulse_t + k * 0.1) % 1.0
            pi_  = np.array(pos[i])
            pj   = np.array(pos[j])
            pt   = pi_ + t * (pj - pi_)
            self.ax3d.scatter([pt[0]], [pt[1]], [pt[2]],
                              s=30, c='#ffffff', alpha=0.6 * abs(pcms[i]),
                              zorder=6)

    # ── Heal flash ────────────────────────────────────────────────────────
    # WHAT: Flash white ring around nodes that just healed (RED→home)
    # WHY:  Makes self-healing visible — physicist can see rescue events
    for i in range(N_NODES):
        if pcms[i] >= 0.04:   # about to heal or just healed
            x, y, z = pos[i]
            self.ax3d.scatter([x], [y], [z], s=600,
                              c='#ffffff', alpha=0.25, zorder=2)

    # ── Globe title + live metrics ─────────────────────────────────────────
    # WHAT: cv, negfrac, reward displayed at top of globe window
    # WHY:  Physicist's first look — key metrics instantly visible
    cv_c    = cv_color(cv)
    title   = (f"cv={cv:.4f}  nf={negfrac:.3f}  "
               f"nc={nc}/12  R={reward:.3f}  step={self.system.step}")
    self.ax3d.set_title(title, color='#88bbff', fontsize=8, pad=4)

    # ── Family color legend ────────────────────────────────────────────────
    # WHAT: Small legend showing family → color mapping
    # WHY:  GodCore/Independent/Maverick families are key to understanding ring
    legend_x, legend_y = 0.02, 0.92
    for fam, col in FAMILY_COLORS.items():
        self.ax3d.text2D(legend_x, legend_y, f"● {fam}",
                         transform=self.ax3d.transAxes,
                         color=col, fontsize=6.5)
        legend_y -= 0.05

    # ── Guardrail status sidebar ───────────────────────────────────────────
    # WHAT: Per-node GREEN/YELLOW/ORANGE/RED status strip
    # WHY:  Instant visual on any node needing attention
    gs    = self.system.qring.guardrail_status()
    icons = {"GREEN":"🟢","YELLOW":"🟡","ORANGE":"🟠","RED":"🔴"}
    status_lines = "  ".join(
        f"{icons[gs[n]]}{n[0]}" for n in NN
    )
    self.ax3d.text2D(0.02, 0.04, status_lines,
                     transform=self.ax3d.transAxes,
                     color='#aabbcc', fontsize=5.5)

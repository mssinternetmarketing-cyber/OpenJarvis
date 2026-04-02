# ═══ c12_visualizer — QCAIVisualizer Class ═══
# WHAT: QCAIVisualizer.__init__() — two-window layout + FuncAnimation setup
# WHY:  Figure 1 = 3D globe (c08_globe3d)
#       Figure 2 = metrics dashboard top + 4×3 node grid bottom (c09+c10)

class QCAIVisualizer:

    def __init__(self, system: 'QCAISystem'):
        self.system = system

        # ── Mouse/spin state ──────────────────────────────────────────────
        self.azim             = -60.0
        self.elev             = 30.0
        self.spinning         = True
        self.mouse_pressed    = False
        self.mouse_x          = 0.0
        self.mouse_y          = 0.0
        self.mouse_release_time = 0.0

        # ── Figure 1: 3D Globe ────────────────────────────────────────────
        # WHAT: Full-window 3D globe visualization
        # WHY:  Axes3D must use projection='3d' — required for matplotlib 3D
        self.fig1 = plt.figure(
            figsize=(9, 8),
            facecolor='#050508',
            num='QCAI — Quantum Ring Globe'
        )
        self.ax3d = self.fig1.add_subplot(111, projection='3d')
        self.ax3d.set_facecolor('#050508')
        self.fig1.patch.set_facecolor('#050508')
        self.fig1.subplots_adjust(left=0, right=1, top=1, bottom=0)

        # ── Figure 2: Dashboard + Node Grid ──────────────────────────────
        # WHAT: Top = metrics/voice panel, bottom = 4×3 node output grid
        # WHY:  Separate figure keeps globe uncluttered for physicist
        self.fig2 = plt.figure(
            figsize=(11, 9),
            facecolor='#05060f',
            num='QCAI — Metrics & Nodes'
        )
        self.fig2.patch.set_facecolor('#05060f')

        # Top section: dashboard + reward chart + PCM bars
        gs_top = gridspec.GridSpec(
            1, 3,
            figure=self.fig2,
            top=0.52, bottom=0.54,   # upper half
            hspace=0.05, wspace=0.15,
            left=0.02, right=0.98
        )
        self.ax_dash   = self.fig2.add_subplot(gs_top[0, 0])
        self.ax_reward = self.fig2.add_subplot(gs_top[0, 1])
        self.ax_pcmbar = self.fig2.add_subplot(gs_top[0, 2])

        # Bottom section: 4 columns × 3 rows = 12 node boxes
        gs_bot = gridspec.GridSpec(
            3, 4,
            figure=self.fig2,
            top=0.50, bottom=0.02,
            hspace=0.18, wspace=0.12,
            left=0.02, right=0.98
        )
        self.ax_nodes = []
        for row in range(3):
            for col in range(4):
                ax = self.fig2.add_subplot(gs_bot[row, col])
                ax.set_facecolor('#08090f')
                ax.set_xticks([])
                ax.set_yticks([])
                self.ax_nodes.append(ax)

        # ── Connect mouse/keyboard events ─────────────────────────────────
        # WHAT: Wire event handlers to Figure 1 (globe window)
        # WHY:  Mouse drag rotates globe, keyboard controls spin/heal
        self.fig1.canvas.mpl_connect('button_press_event',   self._on_press)
        self.fig1.canvas.mpl_connect('button_release_event', self._on_release)
        self.fig1.canvas.mpl_connect('motion_notify_event',  self._on_motion)
        self.fig1.canvas.mpl_connect('key_press_event',      self._on_key)

        # ── Animation setup ───────────────────────────────────────────────
        # WHAT: FuncAnimation drives both figures from one timer
        # WHY:  blit=False required for 3D axes — 3D cannot blit
        #       interval=50ms = 20fps — smooth on GTX 1070
        self.anim1 = FuncAnimation(
            self.fig1, self._update_fig1,
            interval=50, blit=False, cache_frame_data=False
        )
        self.anim2 = FuncAnimation(
            self.fig2, self._update_fig2,
            interval=80, blit=False, cache_frame_data=False
        )

    # Bind methods from component files
    _update_fig1     = _update_fig1
    _update_fig2     = _update_fig2
    _update_node_panel = _update_node_panel
    _on_press        = _on_press
    _on_release      = _on_release
    _on_motion       = _on_motion
    _on_key          = _on_key
    show             = show

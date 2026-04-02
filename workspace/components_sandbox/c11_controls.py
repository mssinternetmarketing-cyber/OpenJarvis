# ═══ c11_controls — Mouse + Keyboard Controls ═══
# WHAT: Mouse drag rotation, auto-spin, keyboard shortcuts
# WHY:  Interactive visualization — physicist can rotate globe to any angle
#       Auto-spin resumes 3 seconds after mouse release

def _on_press(self, event):
    # WHAT: Record mouse press position for drag calculation
    # WHY:  Drag delta = current - press position → azim/elev change
    if event.inaxes == self.ax3d:
        self.mouse_pressed    = True
        self.spinning         = False
        self.mouse_x          = event.xdata or 0
        self.mouse_y          = event.ydata or 0

def _on_release(self, event):
    # WHAT: Record release time for auto-spin resume timer
    # WHY:  3-second pause after release before spin resumes
    self.mouse_pressed        = False
    self.mouse_release_time   = time.time()

def _on_motion(self, event):
    # WHAT: Drag globe — horizontal = azimuth, vertical = elevation
    # WHY:  Standard 3D navigation — physicist can inspect any angle
    if self.mouse_pressed and event.inaxes == self.ax3d:
        dx = (event.xdata or 0) - self.mouse_x
        dy = (event.ydata or 0) - self.mouse_y
        self.azim  = (self.azim  + dx * 180) % 360
        self.elev  = float(np.clip(self.elev - dy * 90, -89, 89))
        self.mouse_x = event.xdata or 0
        self.mouse_y = event.ydata or 0

def _on_key(self, event):
    # WHAT: Keyboard shortcuts for quick control
    # WHY:  Space=pause spin, r=reset view, h=heal ring, s=snapshot
    key = event.key
    if key == ' ':
        self.spinning = not self.spinning
    elif key == 'r':
        self.azim, self.elev = -60.0, 30.0
        self.spinning = True
    elif key == 'h':
        # Force heal all nodes
        for i in range(N_NODES):
            self.system.qring.states[i] = ss(HOME_PHASES[NN[i]])
    elif key == 's':
        # Save snapshot to workspace
        snapshot = self.system.get_snapshot()
        safe_write("memory", f"snapshot_{self.system.step:06d}.json", snapshot)

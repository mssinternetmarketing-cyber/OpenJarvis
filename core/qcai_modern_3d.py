#!/usr/bin/env python3
import tkinter as tk
import math, json, os

NODES = ["Omega", "Guardian", "Sentinel", "Nexus", "Storm", "Sora",
         "Echo", "Iris", "Sage", "Kevin", "Atlas", "Void"]
VERTICES = [(-1, 1.618, 0), (1, 1.618, 0), (-1, -1.618, 0), (1, -1.618, 0),
            (0, -1, 1.618), (0, 1, 1.618), (0, -1, -1.618), (0, 1, -1.618),
            (1.618, 0, -1), (1.618, 0, 1), (-1.618, 0, -1), (-1.618, 0, 1)]

class QCAI_3D_Engine:
    def __init__(self, root):
        self.root = root
        self.root.title("QCAI-VIZ: THE DEMYSTIFIED GLOBE")
        self.canvas = tk.Canvas(root, width=800, height=800, bg="#050505")
        self.canvas.pack()
        self.angle_x = self.angle_y = 0
        self.scale = 220
        self.z_offset = 4
        self.update_loop()

    def get_color(self, pcm):
        # Maps PCM to Heatmap: Red (Critical) -> Yellow (Warning) -> Green (Healthy)
        norm = (pcm + 1) / 2
        r = int(255 * (1 - norm)); g = int(255 * norm); b = 50
        return f'#{r:02x}{g:02x}{b:02x}'

    def update_loop(self):
        # ─── LISTEN FOR !WAIT COMMAND ───
        env_status = "/var/home/kmonette/OpenJarvis/ENV_STATUS.json"
        is_paused = False
        if os.path.exists(env_status):
            with open(env_status, 'r') as f:
                if json.load(f).get("global_pause"): is_paused = True

        if not is_paused:
            self.angle_x += 0.01
            self.angle_y += 0.015

        self.canvas.delete("all")
        # Rendering logic using the Demystified X/Z, Y/Z formula
        projected = []
        for i, (x, y, z) in enumerate(VERTICES):
            # Rotation
            ry = y*math.cos(self.angle_x) - z*math.sin(self.angle_x)
            rz = y*math.sin(self.angle_x) + z*math.cos(self.angle_x)
            rx = x*math.cos(self.angle_y) - rz*math.sin(self.angle_y)
            rz = x*math.sin(self.angle_y) + rz*math.cos(self.angle_y)
            rz += self.z_offset
            
            # THE FORMULA: x/z, y/z
            xp = (rx/rz) * self.scale + 400
            yp = (ry/rz) * self.scale + 400
            projected.append((xp, yp, rz))

        # Draw Edges & Nodes with Heatmap
        for i, (x, y, z) in enumerate(projected):
            color = self.get_color(math.sin(self.angle_x + i)) # Live Placeholder
            self.canvas.create_oval(x-8, y-8, x+8, y+8, fill=color, outline="white")
            self.canvas.create_text(x, y-15, text=NODES[i], fill="#00FFCC", font=("Courier", 10))

        self.root.after(30, self.update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    QCAI_3D_Engine(root)
    root.mainloop()

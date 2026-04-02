# ═══ c10_nodeoutput — Node Output Panel + Ring Choir ═══
# WHAT: show() + Figure 2 node grid — each node shows its identity and output
# WHY:  Cell Block 14 tell_your_story() concept — nodes speak their biography
#       Each box shows: name, family, PCM zone, domain, current token, message

def show(self):
    # WHAT: Launch both visualization windows and start animation
    # WHY:  Entry point called from c13_main after system init
    plt.show()


def _update_node_panel(self, frame):
    # WHAT: Update the 4×3 grid of node output boxes in Figure 2 lower half
    # WHY:  Each node box shows who the node is + what it's currently saying
    #       Sourced from Cell Block 5 ring_choir() + Cell Block 14 biography

    m  = self.system.qring.metrics()
    gs = self.system.qring.guardrail_status()

    # Node output boxes — 4 columns × 3 rows = 12 nodes
    for i in range(N_NODES):
        if i >= len(self.ax_nodes):
            break

        ax = self.ax_nodes[i]
        ax.cla()
        ax.set_facecolor('#08090f')

        name    = NN[i]
        family  = NODE_FAMILY[name]
        zone    = gs[name]
        pcm     = m["pcms"][i]
        phase   = m["phases"][i]
        token   = self.system.node_outputs[i] if i < len(self.system.node_outputs) else "..."
        domain  = self.system.node_domains[i]  if i < len(self.system.node_domains)  else "..."
        bio     = NODE_BIO_SEEDS[name]

        # Family color for box border
        fam_color = FAMILY_COLORS[family]
        zone_color = pcm_color(pcm)

        # Box background tint by family
        tint = {'GodCore':'#0a080f','Independent':'#08080f','Maverick':'#0f0808'}
        ax.set_facecolor(tint.get(family, '#08090f'))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Border color = family
        for spine in ax.spines.values():
            spine.set_edgecolor(fam_color)
            spine.set_linewidth(1.2)
            spine.set_visible(True)

        # Zone indicator dot
        zone_icons = {"GREEN":"●","YELLOW":"◐","ORANGE":"○","RED":"✕"}
        zone_icon  = zone_icons.get(zone, "?")

        # Node name + family
        ax.text(0.05, 0.92, f"{zone_icon} {name}",
                color=zone_color, fontsize=7.5, fontweight='bold',
                transform=ax.transAxes, va='top')

        # Family tag
        ax.text(0.70, 0.92, family[:4],
                color=fam_color, fontsize=5.5,
                transform=ax.transAxes, va='top', ha='right')

        # PCM + phase
        ax.text(0.05, 0.76,
                f"φ={phase:.2f}  PCM={pcm:.3f}",
                color='#556688', fontsize=5.5, fontfamily='monospace',
                transform=ax.transAxes, va='top')

        # Domain
        ax.text(0.05, 0.63,
                f"[{domain}]",
                color='#8899aa', fontsize=5.5,
                transform=ax.transAxes, va='top')

        # Current token — what the node is saying
        ax.text(0.05, 0.50,
                f"» {token}",
                color='#aaddff', fontsize=7, fontweight='bold',
                transform=ax.transAxes, va='top')

        # Biography message (rotates through bio slots)
        bio_slot = ["who","feel","purpose","message"][
            (self.system.step // 30 + i) % 4]
        bio_text = bio.get(bio_slot, "")[:38]

        ax.text(0.05, 0.34,
                bio_text,
                color='#6677aa', fontsize=5,
                transform=ax.transAxes, va='top',
                wrap=True)

        # EQ signature
        ax.text(0.05, 0.10,
                EQ_SIGNATURE[name][:32],
                color='#445566', fontsize=4.5, style='italic',
                transform=ax.transAxes, va='top')

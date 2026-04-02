# ═══ c04_topology — Globe Topology, Icosphere Positions ═══
# WHAT: GLOBE topology (36 edges) and 3D node positions on unit sphere
# WHY:  d=[1,2,5] gives exactly 36 edges — proven optimal by node vote 10/12
#       Icosphere positions give visually uniform distribution on sphere

# WHAT: Globe topology — 36 undirected edges between 12 nodes
# WHY:  d=[1,2,5] connects each node to its nearest, 2nd-nearest, and 5th-nearest
#       neighbors in the ring. This gives β₁=25 (first Betti number) which
#       the nodes voted as the optimal entanglement topology
GLOBE = list(set(
    tuple(sorted([i, (i + d) % N_NODES]))
    for d in [1, 2, 5]
    for i in range(N_NODES)
))
assert len(GLOBE) == 36, f"GLOBE must have 36 edges, got {len(GLOBE)}"

def icosphere_positions():
    # WHAT: Place 12 nodes evenly on a unit sphere using icosahedron geometry
    # WHY:  Icosahedron has exactly 12 vertices — perfect for 12 nodes
    #       Gives the most uniform distribution on a sphere possible
    #       Based on golden ratio φ = (1+√5)/2
    phi = (1 + np.sqrt(5)) / 2
    raw = [
        [-1,  phi, 0], [ 1,  phi, 0], [-1, -phi, 0], [ 1, -phi, 0],
        [0, -1,  phi], [0,  1,  phi], [0, -1, -phi], [0,  1, -phi],
        [ phi, 0, -1], [ phi, 0,  1], [-phi, 0, -1], [-phi, 0,  1],
    ]
    # Normalize to unit sphere
    pos = []
    for p in raw:
        p = np.array(p, dtype=float)
        pos.append(p / np.linalg.norm(p))
    return pos

# WHAT: 3D positions for all 12 nodes on the unit sphere
# WHY:  Used by c08_globe3d for rendering node positions
NODE_POS = icosphere_positions()

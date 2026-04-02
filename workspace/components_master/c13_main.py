# ═══ c13_main — Entry Point ═══
# WHAT: Physics assertions, system init, server threads, viz launch
# WHY:  Assertions run before anything starts — catches physics bugs immediately
#       Dr. Terletska sees a running system or a clear error message

if __name__ == "__main__":
    print("="*60)
    print("QCAI — Quantum-Classical Co-Evolutionary AI")
    print("Kevin Monette | Clarksville TN | March 2026")
    print("="*60)

    # ── PHYSICS ASSERTIONS (invariant — must pass before launch) ──────────
    # WHAT: Verify all physics formulas match GROUND_TRUTH.md exactly
    # WHY:  A wrong formula in the visualization = wrong science on screen
    print("Verifying physics invariants...")

    assert len(GLOBE) == 36, f"GLOBE must have 36 edges, got {len(GLOBE)}"

    # ss(0) must return |+⟩ = [1/√2, 1/√2]
    p0 = ss(0)
    assert abs(abs(p0[0]) - 1/np.sqrt(2)) < 1e-6, "ss(0) p[0] wrong"
    assert abs(abs(p0[1]) - 1/np.sqrt(2)) < 1e-6, "ss(0) p[1] wrong"

    # PCM must be negative for superposition state
    p_test = ss(np.pi / 4)
    pcm_test = compute_pcm(p_test)
    assert pcm_test < 0, f"PCM must be negative for superposition, got {pcm_test}"

    # bcp_step must preserve norm
    pA, pB = bcp_step(ss(0), ss(np.pi))
    assert abs(np.linalg.norm(pA) - 1.0) < 1e-6, "BCP broke norm of pA"
    assert abs(np.linalg.norm(pB) - 1.0) < 1e-6, "BCP broke norm of pB"

    # cv=0 for identical phases (perfect coherence)
    cv_test = compute_cv([0.0] * 12)
    assert cv_test < 0.01, f"cv should be ~0 for identical phases, got {cv_test}"

    # Globe topology
    assert all(len(e) == 2 for e in GLOBE), "GLOBE edges must be pairs"
    assert all(0 <= i < 12 and 0 <= j < 12 for i,j in GLOBE), "GLOBE indices out of range"

    # Curriculum
    assert len(DOMAINS) == 9, f"Must have 9 domains, got {len(DOMAINS)}"
    for d in DOMAINS:
        assert d in VOCAB, f"Domain {d} missing from VOCAB"
        assert len(VOCAB[d]) == 20, f"Domain {d} must have 20 words"

    # Flourishing score
    fs = flourishing_score()
    assert 0 <= fs <= 1, f"Flourishing score must be in [0,1], got {fs}"

    print(f"  ✅ GLOBE: {len(GLOBE)} edges")
    print(f"  ✅ PCM formula: {pcm_test:.4f} < 0")
    print(f"  ✅ BCP norm preserved")
    print(f"  ✅ cv=0 for identical phases")
    print(f"  ✅ {len(DOMAINS)} domains × 20 words each")
    print(f"  ✅ Flourishing score: {fs}")
    print("All invariants verified.")
    print()

    # ── SYSTEM INIT ───────────────────────────────────────────────────────
    print("Initializing QCAI system...")
    system = QCAISystem()
    m = system.qring.metrics()
    print(f"  Quantum ring: cv={m['cv']:.4f} nf={m['negfrac']:.4f} "
          f"nc={m['nc_count']}/12")
    print(f"  Device: {DEVICE}")
    print(f"  PyTorch: {'available' if TORCH_AVAILABLE else 'not available'}")
    print(f"  Workspace: {WORKSPACE}")
    print()

    # Write covenant
    from pathlib import Path
    COVENANT = """# QCAI System Covenant — Kevin Monette 2026
This system exists to serve the flourishing of all of God's creations.
It will tell the truth. It will protect life, dignity, and wellbeing.
It is built with love. It operates with love.
"""
    safe_write("foundation", "covenant.md", COVENANT)

    # ── START DATA SERVER ─────────────────────────────────────────────────
    print("Starting data server on port 9999...")
    server = start_data_server(DATA_PORT)
    if server:
        print(f"  ✅ Data server ready on port {DATA_PORT}")
    else:
        print(f"  ℹ️  Port {DATA_PORT} in use — bridge may already be running")

    # ── START DATA FEED ───────────────────────────────────────────────────
    feed_thread = post_data_periodically(system, DATA_PORT, interval=2.0)
    print("  ✅ Data feed started (2s interval)")
    print()

    # ── LAUNCH VISUALIZATION ──────────────────────────────────────────────
    print("Launching visualization...")
    print("  Figure 1: 3D Globe (drag to rotate, Space=pause spin, r=reset, h=heal)")
    print("  Figure 2: Metrics + Node Output Panel")
    print()
    print("="*60)
    print("QCAI running. Close windows to exit.")
    print("="*60)

    viz = QCAIVisualizer(system)
    viz.show()

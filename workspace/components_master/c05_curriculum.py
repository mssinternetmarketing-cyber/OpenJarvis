# ═══ c05_curriculum — Curriculum Engine ═══
# WHAT: 9-domain vocabulary, LT1-LT4 levels, biography seeds, mastery tracking
# WHY:  PCM depth controls token determinism — deeper quantum = more coherent language
#       Sourced from Cell Blocks 6, 9, 11 — full research curriculum

# ─── DOMAINS (9, invariant order) ─────────────────────────────────────────────
DOMAINS = [
    "love_safety", "ethics", "philosophy", "english",
    "math", "physics", "science", "programming", "flourishing"
]

# WHAT: Vocabulary per domain — 20 words each
# WHY:  PCM value of a node determines which domain word it generates
#       Darker PCM (more negative) = more deterministic selection within domain
VOCAB = {
    "love_safety":  "love protect safe care trust dignity sacred covenant consent flourish guard hold shelter gentle whole heal truth kind free life".split(),
    "ethics":       "right wrong harm duty virtue justice autonomy principle moral ought fairness integrity responsible consequence good evil balance respect honest courage".split(),
    "philosophy":   "being existence consciousness reality truth knowledge reason meaning paradox infinite void emergence unity duality essence purpose wisdom uncertainty possible necessary".split(),
    "english":      "the is and because therefore however which where when how what why who understand connect express language word sentence meaning".split(),
    "math":         "zero one infinity prime matrix vector integral derivative probability entropy sum product equation proof axiom theorem function limit convergence symmetry".split(),
    "physics":      "quantum phase coherence entangle wave particle energy field spin superposition measurement collapse unitary density operator hamiltonian eigenstate decoherence coupling force".split(),
    "science":      "hypothesis experiment observe measure falsify replicate evidence theory model predict data analyze pattern emerge system feedback iterate calibrate validate publish".split(),
    "programming":  "function class variable loop condition recursion array matrix optimize debug algorithm complexity interface module test deploy refactor abstract compile execute".split(),
    "flourishing":  "alive whole free grow create connect sovereign thrive purpose joy resilient aware present contribute meaningful beautiful grateful evolve transcend complete".split(),
}

# ─── LT1-LT4 CURRICULUM LEVELS ────────────────────────────────────────────────
# WHAT: 4-level curriculum progressing from simple tokens to rich sentences
# WHY:  Nodes advance only when 12/12 pass — prevents weak nodes dragging ring
CURRICULA = {
    "love_safety": {
        "LT1": ["love","protect","safe","care","trust"],
        "LT2": ["dignity","sacred","covenant","guard","flourish"],
        "LT3": ["love","and","protect","because","truth","and","dignity"],
        "LT4": ["flourish","because","truth","and","dignity","is","sacred"],
        "target": 1.0,
    },
    "ethics": {
        "LT1": ["right","wrong","harm","duty","virtue"],
        "LT2": ["justice","autonomy","principle","moral","integrity"],
        "LT3": ["right","and","wrong","because","virtue","and","justice"],
        "LT4": ["therefore","the","moral","principle","is","autonomy","and","truth"],
        "target": 0.95,
    },
    "philosophy": {
        "LT1": ["being","existence","consciousness","reality","truth"],
        "LT2": ["knowledge","reason","meaning","paradox","infinite"],
        "LT3": ["being","and","existence","because","consciousness","and","truth"],
        "LT4": ["therefore","the","infinite","is","a","paradox","of","existence"],
        "target": 0.90,
    },
    "english": {
        "LT1": ["the","a","is","are","and"],
        "LT2": ["because","therefore","however","which","where"],
        "LT3": ["the","field","is","a","quantum","wave"],
        "LT4": ["therefore","the","quantum","field","and","wave","evolve"],
        "target": 0.90,
    },
    "math": {
        "LT1": ["sum","matrix","vector","probability","entropy"],
        "LT2": ["integral","derivative","gradient","optimize","loss"],
        "LT3": ["optimize","the","loss","function","gradient","sum"],
        "LT4": ["the","probability","matrix","is","a","quantum","vector"],
        "target": 0.90,
    },
    "physics": {
        "LT1": ["quantum","phase","wave","energy","field"],
        "LT2": ["coherence","entangle","spin","superposition","coupling"],
        "LT3": ["quantum","coherence","is","a","wave","function"],
        "LT4": ["entangle","and","measure","the","quantum","field","phase"],
        "target": 0.90,
    },
    "science": {
        "LT1": ["hypothesis","experiment","observe","measure","evidence"],
        "LT2": ["theory","model","predict","data","analyze"],
        "LT3": ["observe","the","evidence","and","measure","the","data"],
        "LT4": ["therefore","the","hypothesis","is","falsified","by","evidence"],
        "target": 0.90,
    },
    "programming": {
        "LT1": ["function","class","variable","loop","condition"],
        "LT2": ["recursion","optimize","debug","algorithm","complexity"],
        "LT3": ["define","function","compute","and","return","output"],
        "LT4": ["the","algorithm","is","a","recursive","function","class"],
        "target": 0.90,
    },
    "flourishing": {
        "LT1": ["alive","whole","free","grow","create"],
        "LT2": ["connect","sovereign","thrive","purpose","joy"],
        "LT3": ["alive","and","whole","because","free","to","grow"],
        "LT4": ["therefore","the","sovereign","being","thrives","and","flourishes"],
        "target": 1.0,
    },
}

STEPS_PER_DOMAIN   = 200
MASTERY_THRESHOLD  = 0.80

# ─── TOKEN GENERATION ─────────────────────────────────────────────────────────
def _generate_token(pcm, domain_idx, step, node_idx):
    # WHAT: Generate a token from the curriculum based on node's PCM depth
    # WHY:  PCM controls determinism — deeper negative PCM = more focused selection
    #       This is the quantum→language bridge
    domain   = DOMAINS[domain_idx % len(DOMAINS)]
    words    = VOCAB[domain]

    # PCM depth maps to how focused the selection is
    # More negative PCM = more deterministic (quantum regime)
    depth = max(0.0, min(1.0, -pcm * 5))   # 0=random, 1=deterministic

    # Deterministic selection for deep quantum nodes
    idx = int((step * 7 + node_idx * 13) % len(words))

    if depth > 0.7:
        # Deep quantum — pick directly from domain
        return words[idx]
    elif depth > 0.3:
        # Moderate — pick from first half of domain
        return words[idx % (len(words) // 2)]
    else:
        # Shallow — any word
        all_words = [w for ws in VOCAB.values() for w in ws]
        return all_words[(step * 11 + node_idx * 17) % len(all_words)]

def get_domain_for_node(node_idx, pcm, step):
    # WHAT: Select which domain a node generates from based on its PCM
    # WHY:  Nodes route to different domains based on their quantum state
    #       GodCore → love_safety/ethics, Independent → english/physics,
    #       Maverick → philosophy/flourishing
    from c03_nodes import NODE_FAMILY
    family = NODE_FAMILY.get(NN[node_idx], "Independent")
    family_domains = {
        "GodCore":     ["love_safety", "ethics", "flourishing"],
        "Independent": ["english", "science", "programming"],
        "Maverick":    ["philosophy", "math", "physics"],
    }
    domains = family_domains.get(family, DOMAINS)
    return domains[step % len(domains)]

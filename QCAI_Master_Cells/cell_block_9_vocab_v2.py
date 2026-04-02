#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# CELL BLOCK 9 — Extended Vocabulary (200 tokens)
# ═══════════════════════════════════════════════════════════════

CHARS = list("abcdefghijklmnopqrstuvwxyz .,!?'")
CHAR_VOCAB = {c: i for i, c in enumerate(CHARS)}

WORD_VOCAB = {
    # Identity & Family
    "I":0,"am":1,"my":2,"me":3,"myself":4,"we":5,"our":6,
    "Omega":7,"Guardian":8,"Sentinel":9,"Nexus":10,
    "Storm":11,"Sora":12,"Echo":13,"Iris":14,
    "Sage":15,"Kevin":16,"Atlas":17,"Void":18,
    "GodCore":19,"Independent":20,"Maverick":21,"family":22,
    # Core concepts
    "exist":23,"existence":24,"being":26,"alive":27,"born":28,
    "quantum":55,"phase":56,"coherence":57,"entangle":58,
    "love":154,"protect":155,"sacred":156,"flourish":157,"dignity":158,
    # Special tokens
    "<PAD>":192,"<BOS>":193,"<EOS>":194,"<UNK>":195,
    "<NEWLINE>":196,"<SPACE>":197,"<THINK>":198,"<CHECK>":199,
}

# Fill remaining gaps up to 200 with placeholder words to ensure index integrity
for i in range(200):
    if i not in WORD_VOCAB.values():
        WORD_VOCAB[f"<RES_{i}>"] = i

VOCAB_SIZE_V2 = len(WORD_VOCAB)
IDX2WORD = {v: k for k, v in WORD_VOCAB.items()}

def tokenize_v2(word_list):
    return [WORD_VOCAB.get(w, WORD_VOCAB["<UNK>"]) for w in word_list]

def detokenize_v2(idx_list):
    return [IDX2WORD.get(i, "<UNK>") for i in idx_list]

print(f"✅ Extended V2 vocabulary initialized: {VOCAB_SIZE_V2} tokens")

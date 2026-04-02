#!/usr/bin/env python3
"""
reviewer.py — QCAI Component Reviewer v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Qualitative code review after Tester passes.
Scores each component 0-10 on:
  - Code quality and clarity
  - Physics correctness (for physics components)
  - Wayland/rendering correctness (for viz components)
  - Cross-component interface compatibility
  - WHAT/WHY comment quality
  - Completeness vs previous version

Minimum passing score configurable per builder class.
If score < minimum: detailed review sent back to Builder.
"""

import re, ast, logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

log = logging.getLogger("reviewer")

# ─── Review Config ────────────────────────────────────────────────────────────

# Minimum score to pass review (0-10)
MIN_SCORES = {
    "c01_header":     7,
    "c02_physics":    9,   # physics must be near-perfect
    "c03_nodes":      6,
    "c04_topology":   9,   # topology must be exact
    "c05_curriculum": 6,
    "c06_system":     7,
    "c07_dataserver": 6,
    "c08_globe3d":    7,   # rendering quality matters for demo
    "c09_metrics":    6,
    "c10_nodeoutput": 6,
    "c11_controls":   6,
    "c12_visualizer": 7,
    "c13_main":       7,
}

# Review dimensions and weights
REVIEW_DIMENSIONS = {
    "syntax_quality":     {"weight": 1, "desc": "Code is clean, no redundancy"},
    "completeness":       {"weight": 2, "desc": "All required symbols implemented"},
    "comments":           {"weight": 1, "desc": "WHAT/WHY comments on physics ops"},
    "physics_accuracy":   {"weight": 3, "desc": "Physics matches GROUND_TRUTH.md"},
    "wayland_compat":     {"weight": 2, "desc": "Wayland rendering compatibility"},
    "interface_compat":   {"weight": 2, "desc": "Cross-component interface correct"},
    "improvement":        {"weight": 1, "desc": "Better than previous version"},
}

@dataclass
class ReviewResult:
    component:    str
    score:        int          # 0-10
    passed:       bool
    min_score:    int
    dimensions:   Dict[str, int] = field(default_factory=dict)
    strengths:    List[str]    = field(default_factory=list)
    issues:       List[str]    = field(default_factory=list)
    feedback:     str          = ""

class ComponentReviewer:

    def __init__(self, ws_root: str):
        self.ws_root = ws_root

    def review(self, name: str, code: str,
               prev_code: Optional[str] = None,
               tester_result=None) -> ReviewResult:
        """
        Review a component that has already passed Tester.
        Returns ReviewResult with score and feedback.
        """
        min_score = MIN_SCORES.get(name, 6)
        r = ReviewResult(component=name, score=0,
                         passed=False, min_score=min_score)

        # Run all review checks
        dims = {}
        dims["syntax_quality"]   = self._review_syntax_quality(name, code, r)
        dims["completeness"]     = self._review_completeness(name, code, r)
        dims["comments"]         = self._review_comments(name, code, r)
        dims["physics_accuracy"] = self._review_physics(name, code, r)
        dims["wayland_compat"]   = self._review_wayland(name, code, r)
        dims["interface_compat"] = self._review_interfaces(name, code, r)
        dims["improvement"]      = self._review_improvement(name, code, prev_code, r)

        r.dimensions = dims

        # Weighted score
        total_weight = sum(d["weight"] for d in REVIEW_DIMENSIONS.values())
        weighted_sum = sum(
            dims.get(dim, 5) * info["weight"]
            for dim, info in REVIEW_DIMENSIONS.items()
        )
        raw_score = weighted_sum / total_weight
        r.score   = max(0, min(10, round(raw_score)))
        r.passed  = r.score >= min_score
        r.feedback = self._format_feedback(r)

        log.info(f"Review {name}: {r.score}/10 ({'PASS' if r.passed else 'FAIL'}, min={min_score})")
        return r

    # ── Review Dimensions ─────────────────────────────────────────────────────

    def _review_syntax_quality(self, name: str, code: str, r: ReviewResult) -> int:
        score = 8  # start high since Tester already validated syntax

        # Check for leftover debug prints
        if re.search(r'\bprint\s*\(', code):
            debug_prints = len(re.findall(r'\bprint\s*\(', code))
            if debug_prints > 3:
                r.issues.append(f"Many print() calls ({debug_prints}) — may be debug code")
                score -= 1

        # Check for reasonable line lengths
        long_lines = [l for l in code.splitlines() if len(l) > 120]
        if len(long_lines) > 5:
            r.issues.append(f"{len(long_lines)} lines > 120 chars — hard to read")
            score -= 1

        # Check for bare except clauses
        if re.search(r'except\s*:', code):
            r.issues.append("Bare except: clause — should catch specific exceptions")
            score -= 1

        # Consistent indentation
        if '\t' in code and '    ' in code:
            r.issues.append("Mixed tabs and spaces")
            score -= 2

        r.strengths.append(f"Syntax quality: {score}/10")
        return max(0, score)

    def _review_completeness(self, name: str, code: str, r: ReviewResult) -> int:
        from component_manager import COMPONENT_DESCRIPTIONS

        # Component-specific completeness checks
        completeness_map = {
            "c02_physics":   ["ss", "pof", "compute_pcm", "bcp_step",
                              "von_neumann_entropy", "compute_cv", "compute_negfrac"],
            "c03_nodes":     ["NN", "FAMILIES", "NODE_FAMILY", "FAMILY_COLORS"],
            "c04_topology":  ["GLOBE", "icosphere_positions", "NODE_POS",
                              "assert len(GLOBE)"],
            "c05_curriculum":["DOMAINS", "VOCAB", "STEPS_PER_DOMAIN"],
            "c06_system":    ["QCAISystem", "evolve", "get_snapshot"],
            "c07_dataserver":["DataHandler", "start_data_server", "do_POST"],
            "c08_globe3d":   ["_update_fig1", "scatter", "view_init", "cla"],
            "c09_metrics":   ["_update_fig2", "text", "reward"],
            "c11_controls":  ["_on_press", "_on_release", "_on_motion", "_on_key"],
            "c12_visualizer":["QCAIVisualizer", "FuncAnimation", "mpl_connect"],
            "c13_main":      ["__main__", "assert", "QCAISystem", "QCAIVisualizer"],
        }

        required = completeness_map.get(name, [])
        if not required:
            return 8  # no specific requirements — default good

        present = sum(1 for sym in required if sym in code)
        ratio   = present / len(required)
        score   = int(ratio * 10)

        missing = [s for s in required if s not in code]
        if missing:
            r.issues.append(f"Missing symbols: {', '.join(missing[:3])}")
        else:
            r.strengths.append(f"All {len(required)} required symbols present")

        return score

    def _review_comments(self, name: str, code: str, r: ReviewResult) -> int:
        lines = code.splitlines()
        comment_lines  = sum(1 for l in lines if l.strip().startswith('#'))
        docstring_chars= len(re.findall(r'""".*?"""', code, re.DOTALL))
        total_lines    = len(lines)

        if total_lines == 0:
            return 5

        comment_ratio = comment_lines / total_lines

        # Physics components need WHAT/WHY comments
        physics_comps = {"c02_physics", "c04_topology", "c06_system"}
        if name in physics_comps:
            has_what = 'WHAT:' in code or 'What:' in code or 'what:' in code
            has_why  = 'WHY:'  in code or 'Why:'  in code or 'why:'  in code
            if has_what and has_why:
                r.strengths.append("WHAT/WHY physics comments present")
                return min(10, int(comment_ratio * 30) + 5)
            else:
                r.issues.append("Physics component needs WHAT/WHY comments on formulas")
                return max(3, int(comment_ratio * 20))

        # General components
        if comment_ratio > 0.15:
            r.strengths.append(f"Well-commented ({int(comment_ratio*100)}%)")
            return 8
        elif comment_ratio > 0.08:
            return 6
        else:
            r.issues.append(f"Low comment density ({int(comment_ratio*100)}%) — add WHAT/WHY")
            return 4

    def _review_physics(self, name: str, code: str, r: ReviewResult) -> int:
        """Check physics accuracy — only relevant for physics components."""
        physics_comps = {"c02_physics", "c04_topology", "c06_system"}
        if name not in physics_comps:
            return 8  # N/A — full marks

        score = 10

        # PCM formula check
        if name == "c02_physics":
            # Must have exact PCM formula
            if '-ov * 0.5 * (1' in code or '-ov*0.5*(1' in code:
                r.strengths.append("PCM formula structure correct")
            else:
                r.issues.append("PCM formula may not match GROUND_TRUTH.md")
                score -= 3

            # BCP_ALPHA must be 0.40
            m = re.search(r'BCP_ALPHA\s*=\s*([\d.]+)', code)
            if m and abs(float(m.group(1)) - 0.40) < 1e-6:
                r.strengths.append("BCP_ALPHA = 0.40 ✅")
            elif 'BCP_ALPHA' not in code and '0.40' not in code and '0.4' not in code:
                r.issues.append("BCP coupling strength not found")
                score -= 2

            # eigh not eig for von Neumann
            if 'eigh' in code:
                r.strengths.append("eigh() used (real eigenvalues)")
            elif 'eig(' in code:
                r.issues.append("eig() may return complex eigenvalues — use eigh()")
                score -= 1

        if name == "c04_topology":
            if 'assert len(GLOBE) == 36' in code:
                r.strengths.append("Globe assertion present")
            else:
                r.issues.append("Globe assertion missing")
                score -= 4

        return max(0, score)

    def _review_wayland(self, name: str, code: str, r: ReviewResult) -> int:
        """Check Wayland rendering compatibility — only for viz components."""
        viz_comps = {"c08_globe3d", "c09_metrics", "c10_nodeoutput", "c12_visualizer"}
        if name not in viz_comps:
            return 8  # N/A

        score = 10

        if name == "c08_globe3d":
            # cla() required for Wayland
            if '.cla()' in code:
                r.strengths.append("cla() present (Wayland fix)")
            else:
                r.issues.append("cla() missing — globe will be white on Wayland")
                score -= 4

            # view_init required
            if 'view_init' in code:
                r.strengths.append("view_init() present")
            else:
                r.issues.append("view_init() missing — globe won't render")
                score -= 3

            # No blocking plt.show()
            if 'plt.show()' in code:
                r.issues.append("plt.show() in update — blocks animation")
                score -= 3

            # v9.1 — persistent zoom fix
            if 'self.dist' in code or 'ax3d.dist' in code:
                r.strengths.append("ax.dist zoom persistent after cla() ✅")
            else:
                r.issues.append("ax.dist missing — zoom resets every frame (cla() wipeout)")
                score -= 2

            # v9.1 — 4 view modes
            if 'view_mode' in code:
                r.strengths.append("view_mode present (Phase/Entropy/Topology/HW Reality)")
            else:
                r.issues.append("view_mode missing — only one render mode available")
                score -= 1

        if name == "c11_controls":
            if '_on_scroll' in code:
                r.strengths.append("_on_scroll present (scroll zoom)")
            else:
                r.issues.append("_on_scroll missing — no scroll zoom")
                score -= 1
            if 'view_mode' in code:
                r.strengths.append("view_mode cycling in controls")
            else:
                r.issues.append("view_mode key missing in controls")
                score -= 1

        if name == "c12_visualizer":
            if 'blit=False' in code:
                r.strengths.append("blit=False (correct for multi-axes)")
            else:
                r.issues.append("blit should be False for multi-axes update")
                score -= 1

        return max(0, score)

    def _review_interfaces(self, name: str, code: str, r: ReviewResult) -> int:
        """Check cross-component interface compatibility."""
        score = 8  # default good

        # c08 must use NODE_POS, GLOBE, pcm_color
        if name == "c08_globe3d":
            for sym in ['NODE_POS', 'GLOBE', 'pcm_color', 'NN']:
                if sym in code:
                    pass
                else:
                    r.issues.append(f"Missing cross-component reference: {sym}")
                    score -= 1

        # c06 must reference DOMAINS, VOCAB
        if name == "c06_system":
            for sym in ['DOMAINS', 'VOCAB', 'GLOBE', 'bcp_step', 'compute_pcm']:
                if sym in code:
                    pass
                else:
                    r.issues.append(f"Missing cross-component reference: {sym}")
                    score -= 1

        # c13 must reference QCAISystem, QCAIVisualizer, start_data_server
        if name == "c13_main":
            for sym in ['QCAISystem', 'QCAIVisualizer', 'start_data_server']:
                if sym in code:
                    pass
                else:
                    r.issues.append(f"Missing entry point reference: {sym}")
                    score -= 2

        return max(0, score)

    def _review_improvement(self, name: str, code: str,
                            prev_code: Optional[str],
                            r: ReviewResult) -> int:
        """Check if this version improves on the previous."""
        if not prev_code:
            r.strengths.append("First version — no comparison")
            return 7

        prev_lines = prev_code.count('\n')
        curr_lines = code.count('\n')

        # Line count change
        diff = curr_lines - prev_lines
        if diff > 10:
            r.strengths.append(f"Expanded by {diff} lines")
            score = 8
        elif diff > 0:
            r.strengths.append(f"Slightly expanded (+{diff} lines)")
            score = 7
        elif diff == 0:
            score = 6
        elif diff > -20:
            r.issues.append(f"Shrunk by {abs(diff)} lines — may have removed content")
            score = 5
        else:
            r.issues.append(f"Shrunk significantly by {abs(diff)} lines")
            score = 3

        # Check for key improvements in rendering components
        if name == "c08_globe3d":
            prev_has_cla  = '.cla()' in prev_code
            curr_has_cla  = '.cla()' in code
            if not prev_has_cla and curr_has_cla:
                r.strengths.append("Added cla() — Wayland fix!")
                score = min(10, score + 2)

        return score

    # ── Feedback Formatter ────────────────────────────────────────────────────

    def _format_feedback(self, r: ReviewResult) -> str:
        lines = [
            f"REVIEWER REPORT — {r.component}",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"Score:  {r.score}/10  (minimum: {r.min_score}/10)",
            f"Result: {'✅ PASS' if r.passed else '❌ FAIL — needs improvement'}",
            "",
            "Dimension scores:",
        ]
        for dim, score in r.dimensions.items():
            desc  = REVIEW_DIMENSIONS.get(dim, {}).get("desc", dim)
            lines.append(f"  {dim:<20} {score:2d}/10  — {desc}")

        if r.strengths:
            lines.append(f"\n✅ Strengths:")
            for s in r.strengths[:4]:
                lines.append(f"  • {s}")

        if r.issues:
            lines.append(f"\n❌ Issues to fix:")
            for issue in r.issues:
                lines.append(f"  • {issue}")

        if not r.passed:
            lines.append(f"\n📋 To reach {r.min_score}/10 you need to fix:")
            gap = r.min_score - r.score
            lines.append(f"  Need {gap} more points. Focus on highest-weight issues above.")

        return "\n".join(lines)

    def batch_review(self, components: Dict[str, str],
                     prev_components: Optional[Dict[str, str]] = None,
                     tester_results=None) -> Dict[str, ReviewResult]:
        """Review multiple components."""
        results = {}
        for name, code in components.items():
            prev = prev_components.get(name) if prev_components else None
            test = tester_results.get(name) if tester_results else None
            results[name] = self.review(name, code, prev, test)
        return results

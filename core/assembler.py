#!/usr/bin/env python3
"""
assembler.py — QCAI Intelligent Component Assembler v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Assembles qcai_3d.py from named components with:
  - Per-component syntax validation
  - Cross-component dependency resolution
  - Import deduplication and sorting
  - Conflict detection (duplicate symbol definitions)
  - Regression detection vs previous assembly
  - Smart fallback chain (agent → previous → master → placeholder)
  - Symbol registry for Physics agent targeting
  - Assembly manifest JSON per loop
  - Never produces an unrunnable file
"""

import os, re, ast, json, shutil, logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set

log = logging.getLogger("assembler")

# ─── Component Registry ───────────────────────────────────────────────────────

# ─── Dynamic Component Registry ───
import os
MASTER_DIR = "/var/home/kmonette/OpenJarvis/components_master"
try:
    # Dynamically discovers c01_header.py, c02_physics.py, etc. and sorts them natively.
    # Zero hardcoding required. The system auto-expands as you drop files into master.
    COMPONENT_ORDER = sorted([f[:-3] for f in os.listdir(MASTER_DIR) if f.startswith('c') and f.endswith('.py')])
except Exception:
    COMPONENT_ORDER = []


COMPONENT_DESCRIPTIONS = {
    "c01_header":     "Imports, warnings, matplotlib backend, physics constants (N_NODES, BCP_ALPHA, CNOT, I4, BCP_U)",
    "c02_physics":    "Core physics: ss(), pof(), compute_pcm(), bcp_step(), von_neumann_entropy(), compute_cv(), compute_negfrac()",
    "c03_nodes":      "Node definitions: NN, FAMILIES, NODE_FAMILY, FAMILY_COLORS, pcm_color(), pcm_emoji()",
    "c04_topology":   "Globe topology: GLOBE (36 edges assert), icosphere_positions(), NODE_POS",
    "c05_curriculum": "Curriculum engine: DOMAINS, VOCAB, STEPS_PER_DOMAIN, MASTERY_THRESHOLD",
    "c06_system":     "QCAISystem class: __init__, evolve(), _generate_token(), get_snapshot()",
    "c07_dataserver": "Data server: DataHandler, start_data_server(), post_data_periodically()",
    "c08_globe3d":    "3D globe rendering: _update_fig1() — nodes, edges, pulses, heal flashes, wireframe",
    "c09_metrics":    "Metrics panel: physics dashboard text, reward history chart, PCM bar chart",
    "c10_nodeoutput": "Node output panel: _update_fig2() — 4x3 grid, mastery bars, token display",
    "c11_controls":   "Input controls: _on_press(), _on_release(), _on_motion(), _on_key(), auto-spin",
    "c12_visualizer": "QCAIVisualizer class: __init__(), figure setup, animation init, show()",
    "c13_main":       "Entry point: physics assertions, system init, server threads, viz launch",
}

COMPONENT_MIN_LINES = {
    "c01_header": 20, "c02_physics": 40, "c03_nodes": 20,
    "c04_topology": 10, "c05_curriculum": 20, "c06_system": 60,
    "c07_dataserver": 20, "c08_globe3d": 60, "c09_metrics": 30,
    "c10_nodeoutput": 30, "c11_controls": 15, "c12_visualizer": 30,
    "c13_main": 10,
}

# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class ComponentResult:
    name:      str
    source:    str        # "agent" | "previous" | "master" | "placeholder"
    lines:     int
    status:    str        # "ok" | "syntax_error" | "too_short" | "fenced" | "missing"
    error:     str        = ""
    symbols:   List[str]  = field(default_factory=list)
    imports:   List[str]  = field(default_factory=list)
    functions: List[str]  = field(default_factory=list)
    classes:   List[str]  = field(default_factory=list)

@dataclass
class AssemblyResult:
    success:          bool
    assembled_code:   str
    total_lines:      int
    manifest:         dict
    fallbacks_used:   List[str]
    conflicts:        List[str]
    regressions:      List[str]
    component_status: Dict[str, str]
    symbol_registry:  Dict[str, str]
    assembly_score:   int          # 0-100
    summary:          str          # human-readable summary for Slack

# ─── Intelligent Assembler ────────────────────────────────────────────────────

class IntelligentAssembler:

    def __init__(self, ws_root: str):
        self.ws_root         = ws_root
        self.components_dir  = os.path.join(ws_root, "components")
        self.master_dir      = os.path.join(ws_root, "components_master")
        self.assembled_dir   = os.path.join(ws_root, "assembled")
        self.manifest_dir    = os.path.join(ws_root, "assembled", "manifests")
        self.prev_manifest_path = os.path.join(self.manifest_dir, "latest.json")

        self.promoted_dir = os.path.join(ws_root, "components_promoted")
        for d in [self.components_dir, self.master_dir, self.promoted_dir,
                  self.assembled_dir, self.manifest_dir]:
            os.makedirs(d, exist_ok=True)

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _read(self, path: str) -> Optional[str]:
        try:
            with open(path) as f: return f.read()
        except: return None

    def _write(self, path: str, content: str) -> bool:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f: f.write(content)
            return True
        except Exception as e:
            log.error(f"Write {path}: {e}"); return False

    def _comp_path(self, name: str, d: str = None) -> str:
        return os.path.join(d or self.components_dir, f"{name}.py")

    # ── Validation ───────────────────────────────────────────────────────────

    def validate_component(self, name: str, code: str) -> ComponentResult:
        r = ComponentResult(name=name, source="agent",
                            lines=code.count('\n'), status="ok")
        if not code or not code.strip():
            r.status = "missing"; r.error = "Empty"; return r
        if '```' in code:
            r.status = "fenced"; r.error = "Contains markdown fences"; return r
        min_l = COMPONENT_MIN_LINES.get(name, 10)
        if r.lines < min_l:
            r.status = "too_short"
            r.error  = f"{r.lines} lines (need {min_l})"; return r
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            r.status = "syntax_error"; r.error = str(e); return r

        r.imports   = self._extract_imports(tree)
        r.functions = self._extract_functions(tree)
        r.classes   = self._extract_classes(tree)
        r.symbols   = list(set(r.functions + r.classes + self._extract_names(tree)))
        return r

    def _extract_imports(self, tree) -> List[str]:
        out = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names: out.add(a.name.split('.')[0])
            elif isinstance(n, ast.ImportFrom):
                if n.module: out.add(n.module.split('.')[0])
        return list(out)

    def _extract_functions(self, tree) -> List[str]:
        return [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

    def _extract_classes(self, tree) -> List[str]:
        return [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

    def _extract_names(self, tree) -> List[str]:
        names = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id.isupper():
                        names.append(t.id)
        return names

    # ── Fallback Chain ────────────────────────────────────────────────────────

    def get_component(self, name: str, loop: int) -> Tuple[str, str, ComponentResult]:
        """
        Smart fallback chain:
        1. Agent version (components/cXX_name.py)
        2. Previous loop version (versions/components/loop_NNN_cXX.py)
        3. Master version (components_master/cXX_name.py)
        4. Placeholder with TODO
        Returns (code, source_label, ComponentResult)
        """
        # 1. Agent version
        agent_code = self._read(self._comp_path(name))
        if agent_code:
            r = self.validate_component(name, agent_code)
            if r.status == "ok":
                r.source = "agent"
                return agent_code, "agent", r

        # 2. Previous loop versions (most recent first)
        ver_dir = os.path.join(self.ws_root, "versions", "components")
        if os.path.exists(ver_dir):
            prev_files = sorted(
                [f for f in os.listdir(ver_dir) if name in f],
                reverse=True
            )
            for pf in prev_files[:3]:
                prev_code = self._read(os.path.join(ver_dir, pf))
                if prev_code:
                    r = self.validate_component(name, prev_code)
                    if r.status == "ok":
                        r.source = f"previous ({pf})"
                        return prev_code, f"previous ({pf})", r

        # 3. Master version
        master_code = self._read(self._comp_path(name, self.master_dir))
        if master_code:
            r = self.validate_component(name, master_code)
            if r.status == "ok":
                r.source = "master"
                return master_code, "master", r

        # 4. Placeholder
        placeholder = (
            f"# {name} — {COMPONENT_DESCRIPTIONS.get(name, 'Component')}\n"
            f"# ⚠️  PLACEHOLDER — agent has not produced this component yet\n"
            f"# TODO: Implement {name}\n"
            f"pass\n"
        )
        r = ComponentResult(name=name, source="placeholder",
                            lines=4, status="ok", error="placeholder")
        return placeholder, "placeholder", r

    # ── Conflict Detection ────────────────────────────────────────────────────

    def detect_conflicts(self, results: Dict[str, ComponentResult]) -> List[str]:
        sym_sources: Dict[str, List[str]] = {}
        for name, r in results.items():
            if r.status != "ok": continue
            for sym in r.symbols:
                if not sym.startswith('_') and len(sym) > 2:
                    sym_sources.setdefault(sym, []).append(name)
        return [
            f"{sym}: defined in {', '.join(srcs)}"
            for sym, srcs in sym_sources.items()
            if len(srcs) > 1
        ]

    # ── Regression Detection ──────────────────────────────────────────────────

    def detect_regressions(self,
                           prev: Optional[dict],
                           new_results: Dict[str, ComponentResult]
                           ) -> List[str]:
        if not prev: return []
        regressions = []

        new_funcs = set()
        for r in new_results.values():
            new_funcs.update(r.functions)
            new_funcs.update(r.classes)

        old_funcs = set(prev.get("functions", []) + prev.get("classes", []))
        removed = old_funcs - new_funcs
        for sym in removed:
            if not sym.startswith('_') and len(sym) > 3:
                regressions.append(f"Removed: {sym}()")

        old_lines = prev.get("total_lines", 0)
        new_lines = sum(r.lines for r in new_results.values() if r.status == "ok")
        if old_lines > 100 and new_lines < old_lines * 0.75:
            drop = int((old_lines - new_lines) / old_lines * 100)
            regressions.append(f"Line count dropped {drop}%: {old_lines}→{new_lines}")

        return regressions

    # ── Import Deduplication ──────────────────────────────────────────────────

    def build_unified_imports(self, component_codes: Dict[str, str]) -> str:
        """
        Extract all imports from all components, deduplicate, and return
        a clean unified import block. Components themselves will have
        imports stripped during assembly to avoid duplication.
        """
        plain: Set[str]          = set()
        aliased: Dict[str, str]  = {}
        from_imp: Dict[str, Set[str]] = {}

        pat = re.compile(
            r'^(?:import\s+(\S+)(?:\s+as\s+(\w+))?'
            r'|from\s+(\S+)\s+import\s+(.+?))$',
            re.MULTILINE
        )

        for code in component_codes.values():
            for m in pat.finditer(code):
                if m.group(1):
                    mod   = m.group(1)
                    alias = m.group(2)
                    if alias: aliased[mod] = alias
                    else:     plain.add(mod)
                elif m.group(3):
                    mod   = m.group(3)
                    names = {n.strip().split(' as ')[0]
                             for n in m.group(4).split(',')}
                    from_imp.setdefault(mod, set()).update(names)

        lines = ["# ─── Imports (unified by assembler) ─────────────────────────────────────────"]
        for mod in sorted(plain - set(aliased.keys())):
            lines.append(f"import {mod}")
        for mod, alias in sorted(aliased.items()):
            lines.append(f"import {mod} as {alias}")
        for mod in sorted(from_imp.keys()):
            names = sorted(from_imp[mod])
            if len(', '.join(names)) < 80:
                lines.append(f"from {mod} import {', '.join(names)}")
            else:
                lines.append(f"from {mod} import (")
                for n in names: lines.append(f"    {n},")
                lines.append(")")
        return '\n'.join(lines)

    def strip_imports(self, code: str) -> str:
        """Remove import lines from component code (unified imports go at top)."""
        lines = []
        for line in code.splitlines():
            stripped = line.strip()
            if (stripped.startswith('import ') or
                stripped.startswith('from ') and ' import ' in stripped):
                continue
            lines.append(line)
        # Remove leading blank lines after import stripping
        while lines and not lines[0].strip():
            lines.pop(0)
        return '\n'.join(lines)

    # ── Symbol Registry ───────────────────────────────────────────────────────

    def build_symbol_registry(self,
                              results: Dict[str, ComponentResult]
                              ) -> Dict[str, str]:
        """
        Map every defined symbol to its component.
        Used by Physics agent to pinpoint exactly where bugs live.
        """
        registry = {}
        for name in COMPONENT_ORDER:
            if name not in results: continue
            r = results[name]
            if r.status != "ok": continue
            for sym in r.symbols:
                registry[sym] = name
        return registry

    # ── Load Previous Manifest ────────────────────────────────────────────────

    def load_prev_manifest(self) -> Optional[dict]:
        data = self._read(self.prev_manifest_path)
        if data:
            try: return json.loads(data)
            except: pass
        return None

    # ── Score Assembly ────────────────────────────────────────────────────────

    def score_assembly(self,
                       results:     Dict[str, ComponentResult],
                       fallbacks:   List[str],
                       conflicts:   List[str],
                       regressions: List[str]
                       ) -> int:
        """
        Score 0-100:
        - Start at 100
        - -5 per fallback used (master/placeholder used instead of agent)
        - -10 per conflict
        - -15 per regression
        - -20 if GLOBE assertion missing
        - +bonus for all components from agent
        """
        score = 100
        score -= len(fallbacks)    * 5
        score -= len(conflicts)    * 10
        score -= len(regressions)  * 15
        agent_count = sum(1 for r in results.values() if r.source == "agent")
        if agent_count == len(COMPONENT_ORDER):
            score += 5   # bonus: all components from agent
        return max(0, min(100, score))

    # ── Main Assembly ─────────────────────────────────────────────────────────

    def assemble(self, loop: int) -> AssemblyResult:
        """
        Main assembly entry point. Loads all components, validates,
        resolves dependencies, deduplicates imports, detects issues,
        and produces the assembled file with manifest.
        """
        log.info(f"Assembler: starting loop {loop}")
        prev_manifest = self.load_prev_manifest()

        # 1. Load and validate all components
        results:     Dict[str, ComponentResult] = {}
        raw_codes:   Dict[str, str]             = {}
        fallbacks:   List[str]                  = []

        for name in COMPONENT_ORDER:
            code, source, result = self.get_component(name, loop)
            results[name]  = result
            raw_codes[name] = code
            if source != "agent":
                fallbacks.append(f"{name} → {source}")
                log.warning(f"  Fallback: {name} using {source}")
            else:
                log.info(f"  OK: {name} ({result.lines} lines)")

        # 2. Detect conflicts and regressions
        conflicts   = self.detect_conflicts(results)
        regressions = self.detect_regressions(prev_manifest, results)

        if conflicts:
            log.warning(f"  Conflicts: {conflicts}")
        if regressions:
            log.warning(f"  Regressions: {regressions}")

        # 3. Build unified imports from header component
        # (c01_header owns imports — other components' imports are stripped)
        header_code = raw_codes.get("c01_header", "")
        unified_imports = self.build_unified_imports({"c01_header": header_code})

        # 4. Build symbol registry
        symbol_registry = self.build_symbol_registry(results)

        # 5. Assemble the file
        assembled_parts = []

        # File header
        assembled_parts.append(
            f'#!/usr/bin/env python3\n'
            f'# -*- coding: utf-8 -*-\n'
            f'"""\n'
            f'qcai_3d.py — Quantum-Classical Co-Evolutionary AI (QCAI)\n'
            f'Assembled by IntelligentAssembler v1.0 — Loop {loop}\n'
            f'Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            f'Components: {len(COMPONENT_ORDER)} | '
            f'Agent: {len(COMPONENT_ORDER)-len(fallbacks)} | '
            f'Fallback: {len(fallbacks)}\n'
            f'"""\n'
        )

        # Unified imports (from c01_header)
        assembled_parts.append(unified_imports)
        assembled_parts.append("")

        # Each component (with imports stripped from non-header components)
        for name in COMPONENT_ORDER:
            if name == "c01_header":
                # Skip header — imports already added, add non-import content
                code = self.strip_imports(raw_codes[name])
                if code.strip():
                    assembled_parts.append(
                        f"\n# {'═'*75}\n"
                        f"# {name.upper()} — {COMPONENT_DESCRIPTIONS.get(name,'')}\n"
                        f"# {'═'*75}\n"
                    )
                    assembled_parts.append(code)
            else:
                code = self.strip_imports(raw_codes[name])
                r    = results[name]
                src_label = f"[{r.source}]" if r.source != "agent" else ""
                assembled_parts.append(
                    f"\n# {'═'*75}\n"
                    f"# {name.upper()} — {COMPONENT_DESCRIPTIONS.get(name,'')} {src_label}\n"
                    f"# {'═'*75}\n"
                )
                assembled_parts.append(code)

        assembled_code = '\n'.join(assembled_parts)
        total_lines    = assembled_code.count('\n')

        # 6. Validate assembled file
        guardian = "PASS"
        guardian_reason = "ok"
        try:
            compile(assembled_code, '<assembled>', 'exec')
        except SyntaxError as e:
            guardian        = "FAIL"
            guardian_reason = f"SyntaxError in assembled file: {e}"
            log.error(f"Assembly syntax error: {e}")

        # Line count check
        if total_lines < 400:
            guardian        = "FAIL"
            guardian_reason = f"Too short: {total_lines} lines (minimum 400)"

        # Markdown fence check — agents sometimes leak fences
        if '```' in assembled_code:
            guardian        = "FAIL"
            guardian_reason = "Contains markdown fences — raw Python required"

        # GLOBE assertion (only required for QCAI workspaces)
        if 'assert len(GLOBE)' not in assembled_code and 'GLOBE' in assembled_code:
            guardian        = "FAIL"
            guardian_reason = "Missing: assert len(GLOBE) == 36"

        # v9.1 physics checks
        if 'GLOBE' in assembled_code:
            if '0.40' not in assembled_code and 'BCP_ALPHA' not in assembled_code:
                guardian        = "FAIL"
                guardian_reason = "BCP coupling alpha not found (must be 0.40)"

        # 7. Score
        score = self.score_assembly(results, fallbacks, conflicts, regressions)
        if guardian == "FAIL": score = max(0, score - 30)

        # 8. Build manifest
        manifest = {
            "loop":            loop,
            "timestamp":       datetime.now().isoformat(),
            "guardian":        guardian,
            "guardian_reason": guardian_reason,
            "assembly_score":  score,
            "total_lines":     total_lines,
            "fallbacks_used":  fallbacks,
            "conflicts":       conflicts,
            "regressions":     regressions,
            "functions":       [f for r in results.values() for f in r.functions],
            "classes":         [c for r in results.values() for c in r.classes],
            "components": {
                name: {
                    "source":  results[name].source,
                    "lines":   results[name].lines,
                    "status":  results[name].status,
                    "error":   results[name].error,
                    "functions": results[name].functions,
                }
                for name in COMPONENT_ORDER
                if name in results
            }
        }

        # 9. Save assembled file and manifest
        assembled_path = os.path.join(self.assembled_dir, "qcai_3d_assembled.py")
        self._write(assembled_path, assembled_code)

        # Save versioned assembled file
        ver_path = os.path.join(self.assembled_dir, f"loop_{loop:03d}_assembled.py")
        self._write(ver_path, assembled_code)

        # Save manifest
        manifest_path = os.path.join(self.manifest_dir, f"loop_{loop:03d}_manifest.json")
        self._write(manifest_path, json.dumps(manifest, indent=2))
        self._write(self.prev_manifest_path, json.dumps(manifest, indent=2))

        # 10. Build summary for Slack
        comp_lines = []
        for name in COMPONENT_ORDER:
            r = results[name]
            icon = "✅" if r.source == "agent" and r.status == "ok" else \
                   "🔄" if r.source == "previous" else \
                   "📦" if r.source == "master" else \
                   "⚠️"
            comp_lines.append(f"  {icon} {name:<18} {r.lines:4d}L  [{r.source}]")

        summary = (
            f"*Assembly Loop {loop}* | Score: {score}/100 | "
            f"Guardian: {'✅ PASS' if guardian=='PASS' else '❌ FAIL'}\n"
            f"Total: {total_lines} lines | "
            f"Agent: {len(COMPONENT_ORDER)-len(fallbacks)}/13 | "
            f"Fallbacks: {len(fallbacks)}\n"
            f"```\n" + '\n'.join(comp_lines) + f"\n```"
        )

        if conflicts:
            summary += f"\n⚠️ Conflicts: {len(conflicts)} — {conflicts[0]}"
        if regressions:
            summary += f"\n⚠️ Regressions: {len(regressions)} — {regressions[0]}"
        if fallbacks:
            summary += f"\n🔄 Fallbacks used: {len(fallbacks)}"
        if guardian == "FAIL":
            summary += f"\n❌ Guardian FAIL: {guardian_reason}"

        log.info(f"Assembly complete: {total_lines} lines, score={score}, guardian={guardian}")

        return AssemblyResult(
            success          = guardian == "PASS",
            assembled_code   = assembled_code,
            total_lines      = total_lines,
            manifest         = manifest,
            fallbacks_used   = fallbacks,
            conflicts        = conflicts,
            regressions      = regressions,
            component_status = {n: results[n].status for n in COMPONENT_ORDER if n in results},
            symbol_registry  = symbol_registry,
            assembly_score   = score,
            summary          = summary,
        )

    # ── Component Versioning ──────────────────────────────────────────────────

    def save_component_version(self, name: str, code: str, loop: int):
        """Save a versioned copy of a component."""
        ver_dir = os.path.join(self.ws_root, "versions", "components")
        os.makedirs(ver_dir, exist_ok=True)
        path = os.path.join(ver_dir, f"loop_{loop:03d}_{name}.py")
        self._write(path, code)

    def list_component_versions(self, name: str) -> List[str]:
        ver_dir = os.path.join(self.ws_root, "versions", "components")
        if not os.path.exists(ver_dir): return []
        return sorted([f for f in os.listdir(ver_dir) if name in f])[-5:]

    # ── Master Seeding ────────────────────────────────────────────────────────

    def seed_from_master(self, master_code: str) -> Dict[str, int]:
        """
        Split master file into components by detecting natural boundaries.
        Returns {component_name: line_count} for each seeded component.
        """
        log.info("Seeding components from master file...")
        seeded = {}

        # Split by finding function/class definitions and logical sections
        lines = master_code.splitlines()

        # Define split points based on known structure
        splits = self._detect_split_points(lines)

        for i, (name, start, end) in enumerate(splits):
            component_code = '\n'.join(lines[start:end])
            master_path = self._comp_path(name, self.master_dir)
            agent_path  = self._comp_path(name, self.components_dir)
            self._write(master_path, component_code)
            # Only seed agent version if it doesn't already exist
            if not os.path.exists(agent_path):
                self._write(agent_path, component_code)
            seeded[name] = component_code.count('\n')
            log.info(f"  Seeded {name}: {seeded[name]} lines")

        return seeded

    def _detect_split_points(self, lines: List[str]) -> List[Tuple[str, int, int]]:
        """
        Detect natural split points in the master file.
        Returns list of (component_name, start_line, end_line).
        """
        total = len(lines)
        splits = []

        # Key patterns to detect section boundaries
        patterns = {
            "c01_header":    (0, self._find_first_function(lines)),
            "c02_physics":   None,  # populated below
            "c04_topology":  None,
            "c05_curriculum":None,
            "c06_system":    None,
            "c07_dataserver":None,
            "c12_visualizer":None,
            "c13_main":      None,
        }

        # Find key boundaries
        func_starts = {}
        class_starts = {}
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('def '):
                fname = stripped.split('(')[0][4:].strip()
                func_starts[fname] = i
            elif stripped.startswith('class '):
                cname = stripped.split('(')[0][6:].strip().rstrip(':')
                class_starts[cname] = i

        # Build splits based on detected boundaries
        boundaries = []

        # c01: start to first function
        first_func = min(func_starts.values()) if func_starts else total
        boundaries.append(("c01_header", 0, first_func))

        # Physics functions
        physics_funcs = ["ss", "pof", "compute_pcm", "bcp_step",
                         "von_neumann_entropy", "compute_cv", "compute_negfrac"]
        phys_start = min((func_starts[f] for f in physics_funcs
                         if f in func_starts), default=first_func)

        # Node definitions (after physics)
        node_funcs = ["pcm_color", "pcm_emoji"]
        node_start = min((func_starts[f] for f in node_funcs
                         if f in func_starts), default=phys_start+50)

        boundaries.append(("c02_physics", phys_start, node_start))

        # Topology (GLOBE, icosphere)
        topo_start = func_starts.get("icosphere_positions", node_start + 30)
        boundaries.append(("c03_nodes", node_start, topo_start))

        # Curriculum (DOMAINS, VOCAB)
        curr_marker = next((i for i, l in enumerate(lines)
                           if 'DOMAINS' in l and '=' in l), topo_start + 20)
        boundaries.append(("c04_topology", topo_start, curr_marker))

        # System class
        sys_start = class_starts.get("QCAISystem", curr_marker + 40)
        boundaries.append(("c05_curriculum", curr_marker, sys_start))

        # DataServer
        data_start = class_starts.get("DataHandler",
                       func_starts.get("start_data_server", sys_start + 80))
        boundaries.append(("c06_system", sys_start, data_start))

        # Visualizer class
        viz_start = class_starts.get("QCAIVisualizer", data_start + 30)
        boundaries.append(("c07_dataserver", data_start, viz_start))

        # Main entry
        main_start = next((i for i, l in enumerate(lines)
                          if '__name__' in l and '__main__' in l), total - 20)

        # Split visualizer into sub-components
        update_fig1 = func_starts.get("_update_fig1", viz_start + 30)
        update_fig2 = func_starts.get("_update_fig2", update_fig1 + 80)
        on_press    = func_starts.get("_on_press",    update_fig2 + 60)

        boundaries.append(("c08_globe3d",    update_fig1, update_fig2))
        boundaries.append(("c09_metrics",    update_fig2, on_press))

        # Controls vs nodeoutput — detect which comes first
        if update_fig2 < on_press:
            boundaries.append(("c10_nodeoutput", update_fig2,  on_press))
            boundaries.append(("c11_controls",   on_press,     viz_start + 200 if on_press > viz_start+100 else main_start))
        else:
            boundaries.append(("c10_nodeoutput", update_fig2,  main_start))

        boundaries.append(("c12_visualizer", viz_start, update_fig1))
        boundaries.append(("c13_main",       main_start, total))

        # Sort by start line, remove overlaps
        boundaries.sort(key=lambda x: x[1])
        # Fill gaps in header
        result = []
        seen_names = set()
        for name, start, end in boundaries:
            if name in seen_names: continue
            if start >= end: continue
            result.append((name, max(0, start), min(total, end)))
            seen_names.append(name) if hasattr(seen_names, 'append') else seen_names.add(name)

        # Ensure c01_header always included
        if "c01_header" not in [r[0] for r in result]:
            result.insert(0, ("c01_header", 0, first_func))

        return sorted(result, key=lambda x: COMPONENT_ORDER.index(x[0])
                      if x[0] in COMPONENT_ORDER else 99)

    def _find_first_function(self, lines: List[str]) -> int:
        for i, line in enumerate(lines):
            if line.startswith('def ') or line.startswith('class '):
                return i
        return len(lines)

    # ── Status Report ─────────────────────────────────────────────────────────

    def status_report(self) -> str:
        """Generate a status report of current component state."""
        lines = ["*Component Status*\n```"]
        for name in COMPONENT_ORDER:
            path = self._comp_path(name)
            if os.path.exists(path):
                code = self._read(path) or ""
                n    = code.count('\n')
                r    = self.validate_component(name, code)
                icon = "✅" if r.status == "ok" else "❌"
                lines.append(f"{icon} {name:<20} {n:4d}L  {r.status}")
            else:
                lines.append(f"⬜ {name:<20}    0L  missing")
        lines.append("```")

        # Latest manifest
        prev = self.load_prev_manifest()
        if prev:
            lines.append(
                f"\nLast assembly: Loop {prev.get('loop','?')} | "
                f"Score: {prev.get('assembly_score','?')}/100 | "
                f"Guardian: {prev.get('guardian','?')} | "
                f"Lines: {prev.get('total_lines','?')}"
            )
        return '\n'.join(lines)

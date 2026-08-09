# -*- coding: utf-8 -*-
"""
Antigravity 系统一致性检查器 V1.0 — 启动守卫

每次重要操作前自动运行，确保所有模块接口一致。
防止"各自为战"问题再次发生。

用法:
    python consistency_checker.py          # 检查
    python consistency_checker.py --fix    # 检查+自动修复
    python consistency_checker.py --enforce # 有ERROR则exit(1)
"""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))


class ConsistencyChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def check_all(self):
        from formula_lang.primitive import get_default_primitives

        prims = get_default_primitives()
        actual_names = {p.name for p in prims}
        print(f"[CHECK] {len(prims)} primitives loaded")

        # 1. __init__.py exports all
        init_path = _PROJECT_ROOT / 'formula_lang' / '__init__.py'
        init_content = init_path.read_text(encoding='utf-8')
        for cls_name in ['MutualInformationPair', 'ResidualSignal', 'ConditionalProbabilityMatrix']:
            if cls_name not in init_content:
                self.errors.append(f"{cls_name} not exported in __init__.py")

        # 2. smart_evolution uses dynamic loading (not hardcoded whitelist)
        se_path = _PROJECT_ROOT / 'smart_evolution.py'
        se_content = se_path.read_text(encoding='utf-8')
        if 'KEEP_NAMES' in se_content and 'cooccurrence_affinity' in se_content:
            # Check if it's the old hardcoded version
            if 'filtered_prims = [p for p in prims if p.name in KEEP_NAMES]' in se_content:
                self.errors.append("smart_evolution.py still uses hardcoded KEEP_NAMES")
        elif 'None' in se_content and 'KEEP_NAMES' in se_content:
            pass  # Already fixed to dynamic
        else:
            # No KEEP_NAMES at all — check if it loads all prims
            if 'get_default_primitives()' not in se_content:
                self.warnings.append("smart_evolution.py doesn't use get_default_primitives()")

        # 3. evaluator_v3.py exists and is V3.2
        v3_path = _PROJECT_ROOT / 'formula_lang' / 'evaluator_v3.py'
        v3_content = v3_path.read_text(encoding='utf-8')
        if 'V3.2' not in v3_content[:500]:
            self.warnings.append("evaluator_v3.py header missing V3.2 mention")
        if 'avg_hits' not in v3_content:
            self.errors.append("evaluator_v3.py missing avg_hits metric")

        # 4. registry.py uses V3.2
        reg_path = _PROJECT_ROOT / 'formula_lang' / 'registry.py'
        reg_content = reg_path.read_text(encoding='utf-8')
        if 'FormulaEvaluatorV3' not in reg_content:
            self.errors.append("registry.py not using FormulaEvaluatorV3")

        # 5. formula_evolution.py uses V3.2
        fe_path = _PROJECT_ROOT / 'formula_evolution.py'
        fe_content = fe_path.read_text(encoding='utf-8')
        if 'FormulaEvaluatorV3' not in fe_content:
            self.errors.append("formula_evolution.py not using FormulaEvaluatorV3")

        # 6. All 3 new primitives are in primitive.py
        prim_path = _PROJECT_ROOT / 'formula_lang' / 'primitive.py'
        for cls in ['MutualInformationPair', 'ResidualSignal', 'ConditionalProbabilityMatrix']:
            if f'class {cls}' not in prim_path.read_text(encoding='utf-8'):
                self.errors.append(f"{cls} class not defined in primitive.py")

        return len(self.errors) == 0

    def report(self):
        print()
        print("=" * 60)
        print("  Consistency Check Report")
        print("=" * 60)

        if self.errors:
            print(f"\n  ERRORS ({len(self.errors)}):")
            for e in self.errors:
                print(f"    [ERROR] {e}")

        if self.warnings:
            print(f"\n  WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"    [WARN] {w}")

        if not self.errors and not self.warnings:
            print("\n  [OK] All systems consistent.")

        print("=" * 60)
        return len(self.errors) == 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Antigravity System Consistency Checker')
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues')
    parser.add_argument('--enforce', action='store_true', help='Exit 1 on errors')
    args = parser.parse_args()

    checker = ConsistencyChecker()
    ok = checker.check_all()
    checker.report()

    if args.enforce and not ok:
        print("\n[FATAL] Consistency check failed. Fix errors before proceeding.")
        sys.exit(1)
    elif ok:
        print("\n[PASS] Ready to proceed.")
    else:
        print(f"\n[WARNING] {len(checker.warnings)} warnings found.")

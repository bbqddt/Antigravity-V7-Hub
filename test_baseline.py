from formula_lang.evaluator_v3 import FormulaEvaluatorV3
from data_layer import load_history
from formula_lang.primitive import PrimitiveFactory
from formula_lang.grammar import FormulaGrammar
import random

draws = load_history()

ev = FormulaEvaluatorV3()
print('=== 评估基线标准 ===')
print('红球 Brier 基线:', round(ev.RED_BRIER_BASELINE, 6))
print('蓝球 Brier 基线:', round(ev.BLUE_BRIER_BASELINE, 6))
print('综合 Brier 基线:', round(ev.COMBINED_BASELINE, 6))
print('随机命中基线:', 1.09, '(6*6/33)')
print()

factory = PrimitiveFactory()
prims = factory.create_all()
selected = random.sample(prims, 3)
f = getattr(FormulaGrammar, 'resonance')(selected, name='baseline_test')

result = ev.evaluate(f, draws, n_windows=10, window_size=300, step=50)
print('测试公式:', f.name)
print('  avg_brier:', round(result['avg_brier'], 6), '(基线:', round(ev.RED_BRIER_BASELINE, 6), ')')
print('  avg_hits:', round(result['avg_hits'], 4), '(基线: 1.09)')
print('  beats_random_brier:', result['beats_random_brier'])
print('  beats_random_hits:', result['beats_random_hits'])
print('  beats_random (综合):', result['beats_random'])
print('  combined_score:', round(result['combined_score'], 4))
print('  generalization_gap:', round(result['generalization_gap'], 6))
print('  overfitting_risk:', result['overfitting_risk'])
from formula_lang.evaluator_v3 import FormulaEvaluatorV3, IncrementalEvaluator
from formula_lang.primitive import PrimitiveFactory
from formula_lang.grammar import FormulaGrammar
from data_layer import load_history
import random
import time

draws = load_history()
factory = PrimitiveFactory()
prims = factory.create_all()

selected = random.sample(prims, 3)
f = getattr(FormulaGrammar, 'resonance')(selected, name='test_inc')
print('Formula:', f.name)

ev = FormulaEvaluatorV3()
inc_ev = IncrementalEvaluator(ev)

t1 = time.time()
result1 = inc_ev.evaluate_incremental(f, draws, n_windows=10, window_size=300, step=50)
t2 = time.time()
print('Incremental eval 1: {:.3f}s, Score={:.4f}'.format(t2-t1, result1["combined_score"]))
print('Cache:', result1["cache_stats"])

t1 = time.time()
result2 = inc_ev.evaluate_incremental(f, draws, n_windows=10, window_size=300, step=50)
t2 = time.time()
print('Incremental eval 2: {:.3f}s, Score={:.4f}'.format(t2-t1, result2["combined_score"]))
print('Cache:', result2["cache_stats"])

t1 = time.time()
result3 = ev.evaluate(f, draws, n_windows=10, window_size=300, step=50)
t2 = time.time()
print('Standard eval: {:.3f}s, Score={:.4f}'.format(t2-t1, result3["combined_score"]))
with open('formula_evolution.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 精确找到插入点
marker = 'return sum(runs) / max(len(runs), 1)\n\n\n# '
idx = content.find(marker)
if idx == -1:
    marker = 'return sum(runs) / max(len(runs), 1)\n\n\n'
    idx = content.find(marker)
print('idx:', idx)
if idx >= 0:
    new_methods = '''
    def expected_calibration_error(self, probs, outcomes, n_bins=10):
        import numpy as np
        bins = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        for i in range(n_bins):
            mask = (probs >= bins[i]) & (probs < bins[i + 1])
            if not mask.any():
                continue
            acc = outcomes[mask].mean()
            conf = probs[mask].mean()
            ece += mask.mean() * abs(acc - conf)
        return float(ece)

    def permutation_test(self, hits_list, n_bootstrap=2000, block=50):
        import numpy as np
        if not hits_list:
            return 1.0, 0.0
        arr = np.array(hits_list)
        obs_stat = arr.mean() - self.RANDOM_EXPECTATION
        n = len(arr)
        boot_stats = []
        for _ in range(n_bootstrap):
            idx = np.random.choice(n // block, size=n // block, replace=True)
            samp = np.concatenate([arr[i*block:(i+1)*block] for i in idx])[:len(arr)]
            boot_stats.append(samp.mean() - self.RANDOM_EXPECTATION)
        boot_stats = np.array(boot_stats)
        p_val = float((boot_stats >= obs_stat).mean())
        effect = float(obs_stat)
        return p_val, effect

    def kelly_simulation(self, hits_per_period, odds=1.0, bankroll=10000, n_sims=2000):
        import numpy as np
        if not hits_per_period:
            return {'roi': 0, 'ruin_prob': 1, 'sharpe': 0, 'max_drawdown': 1}
        p_win = np.array(hits_per_period) / 6.0
        p_win = np.clip(p_win, 0.01, 0.99)
        q = 1 - p_win
        b = 1.0
        f_star = np.clip((b * p_win - (1 - p_win)) / b, 0, 0.25)
        final_values = []
        max_dds = []
        for _ in range(2000):
            capital = 10000
            peak = 10000
            max_dd = 0
            for f, p, qq in zip(f_star, p_win, q):
                bet = capital * f
                win = np.random.random() < p
                capital += bet * 1.0 if win else -bet
                peak = max(peak, capital)
                max_dd = max(max_dd, (peak - capital) / peak)
            final_values.append(capital)
            max_dds.append(max_dd)
        final_values = np.array(final_values)
        returns = (final_values - 10000) / 10000
        return {'roi': float(np.median(returns)),
                'ruin_prob': float((np.array(final_values) < 5000).mean()),
                'sharpe': float(np.mean(returns) / (np.std(returns) + 1e-9)),
                'max_drawdown': float(np.median(max_dds))}
'''
    pos = content.find('return sum(runs) / max(len(runs), 1)\n\n\n# ')
    if pos == -1:
        pos = content.find('return sum(runs) / max(len(runs), 1)\n\n\n')
    if pos >= 0:
        content = content[:pos+42] + new_methods + content[pos+42:]
        with open('formula_evolution.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('Inserted at', pos)
    else:
        print('Marker not found')
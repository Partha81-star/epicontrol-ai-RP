"""Post-release check and descriptive reward re-scoring without re-training."""
from pathlib import Path
import csv,json
import numpy as np
from research_model import Config,SEIRModel
from q_agent import QLearningAgent
from run_research import write_csv
OUT=Path(__file__).parent/'results'
agents={s:QLearningAgent(s) for s in (11,22,33)}
for s,a in agents.items():a.q_table=np.load(OUT/f'q_table_seed{s}.npy')
rows=[]
for seed in range(10000,10040):
    rng=np.random.default_rng(seed)
    params=dict(beta=float(rng.uniform(.24,.36)),compliance=float(rng.uniform(.7,1)),
                initial_exposed=int(rng.integers(10,51)),initial_infected=int(rng.integers(5,21)))
    for name in ('Strict','Q11','Q22','Q33'):
        c=Config(**params);m=SEIRModel(c)
        while m.day<180:m.step(3 if name=='Strict' else agents[int(name[1:])].choose_action(m.state(),False))
        pre_peak=max(r['I'] for r in m.history);c.days=365
        while m.day<365:m.step(0)
        rows.append({'scenario':seed,'policy':name,'peak_before_release':pre_peak,
                     'peak_after_release':max(r['I'] for r in m.history if r['day']>180),
                     'attack_rate_365':(c.population-m.history[-1]['S'])/c.population})
write_csv(OUT/'post_release.csv',rows)
summary={name:{k:float(np.mean([r[k] for r in rows if r['policy']==name]))
               for k in ('peak_before_release','peak_after_release','attack_rate_365')}
         for name in ('Strict','Q11','Q22','Q33')}
(OUT/'additional_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))

"""Reproducible synthetic research experiment; outputs contain no real patient data."""
from pathlib import Path
import json,csv,platform
import numpy as np
from research_model import Config,rollout,ACTIONS
from train import train_agent_function
OUT=Path(__file__).parent/'results'
def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def main():
    OUT.mkdir(exist_ok=True)
    agents=[train_agent_function(1200,s,OUT) for s in (11,22,33)];rows=[]
    for seed in range(10000,10040):
        rng=np.random.default_rng(seed)
        c=Config(beta=float(rng.uniform(.24,.36)),compliance=float(rng.uniform(.7,1)),
                 initial_exposed=int(rng.integers(10,51)),initial_infected=int(rng.integers(5,21)))
        policies={name:(lambda m,a=a:a) for name,a in [('None',0),('Moderate',1),('Targeted',2),('Strict',3)]}
        policies['Threshold']=lambda m:2 if (m.y[2]+m.y[6])/m.config.population>.002 else 0
        for s,agent in zip((11,22,33),agents):policies[f'Q{s}']=lambda m,agent=agent:agent.choose_action(m.state(),False)
        for name,policy in policies.items():
            metrics,history=rollout(c,policy);rows.append({'seed':seed,'policy':name,'beta':c.beta,'compliance':c.compliance,**metrics})
            if seed==10000:write_csv(OUT/f'trajectory_{name}.csv',history)
    write_csv(OUT/'evaluation.csv',rows);summary={}
    keys=('peak_infectious','attack_rate','peak_hospital_proxy','days_above_capacity','mean_restriction_cost','return')
    for name in sorted(set(r['policy'] for r in rows)|{'Q pooled'}):
        selected=[r for r in rows if (r['policy'].startswith('Q') if name=='Q pooled' else r['policy']==name)]
        summary[name]={k:{'mean':float(np.mean([r[k] for r in selected])),
                          'sd':float(np.std([r[k] for r in selected],ddof=1))} for k in keys}
    diffs=[]
    for seed in range(10000,10040):
        selected=[r for r in rows if r['seed']==seed];base=next(r for r in selected if r['policy']=='Threshold')['return']
        diffs.append(np.mean([r['return'] for r in selected if r['policy'].startswith('Q')])-base)
    rng=np.random.default_rng(20261007);boot=np.mean(rng.choice(diffs,(10000,40),replace=True),axis=1)
    summary['paired_Q_minus_threshold_return']={'mean':float(np.mean(diffs)),
        'scenario_bootstrap_95_interval':[float(v) for v in np.quantile(boot,[.025,.975])]}
    stress=[]
    for beta in (.24,.3,.36,.42):
        for compliance in (.5,.7,.85,1):
            c=Config(beta=beta,compliance=compliance)
            for name,policy in [('None',lambda m:0),('Strict',lambda m:3),
                ('Threshold',lambda m:2 if (m.y[2]+m.y[6])/m.config.population>.002 else 0),
                ('Q11',lambda m:agents[0].choose_action(m.state(),False))]:
                metrics,_=rollout(c,policy);stress.append({'beta':beta,'compliance':compliance,'policy':name,**metrics})
    write_csv(OUT/'sensitivity.csv',stress);numerical=[]
    for dt in (.5,.25,.125):
        metrics,_=rollout(Config(step_size=dt),lambda m:0);numerical.append({'step_size':dt,**metrics})
    write_csv(OUT/'numerical_check.csv',numerical)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    (OUT/'manifest.json').write_text(json.dumps({'config':vars(Config()),'actions':ACTIONS,'episodes_per_seed':1200,
        'training_seeds':[11,22,33],'evaluation_seeds':[10000,10039],'python':platform.python_version(),'numpy':np.__version__},indent=2))
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()

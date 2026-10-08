"""Local decision-support demonstration backed by the research experiment model."""
from pathlib import Path
import numpy as np
from flask import Flask,request,jsonify,render_template
from research_model import Config,rollout,ACTION_NAMES
from q_agent import QLearningAgent
app=Flask(__name__)

def config_from(data):
    if not isinstance(data,dict):raise ValueError('Expected a JSON object')
    allowed=set(Config.__dataclass_fields__)
    unknown=set(data)-allowed-{'policy'}
    if unknown:raise ValueError('Unknown parameters: '+', '.join(sorted(unknown)))
    kwargs={k:float(v) for k,v in data.items() if k in allowed}
    for k in ('population','days'):
        if k in kwargs:
            if int(kwargs[k])!=kwargs[k]:raise ValueError(k+' must be a whole number')
            kwargs[k]=int(kwargs[k])
    c=Config(**kwargs);c.validate()
    if max(c.beta,c.sigma,c.gamma)>2:raise ValueError('Rates above 2 per day are unsupported')
    return c

def policy_for(name):
    fixed={'none':0,'moderate':1,'targeted':2,'strict':3}
    if name in fixed:return lambda m:fixed[name]
    if name=='threshold':return lambda m:2 if (m.y[2]+m.y[6])/m.config.population>.002 else 0
    if name=='q_learning':
        path=Path(__file__).parent/'results'/'q_table_seed11.npy'
        if not path.exists():raise ValueError('Run run_research.py before using the learned policy')
        a=QLearningAgent();a.q_table=np.load(path,allow_pickle=False)
        if a.q_table.shape!=(6,3,3,3,4,4):raise ValueError('Incompatible saved Q-table')
        return lambda m:a.choose_action(m.state(),False)
    raise ValueError('Unknown policy')

@app.get('/')
def index():return render_template('index.html')
@app.get('/health')
def health():return jsonify(status='ok',data_type='synthetic')
@app.post('/run_simulation')
def simulate():
    try:
        data=request.get_json(silent=True);c=config_from(data)
        metrics,trajectory=rollout(c,policy_for(data.get('policy','none')))
        return jsonify(metrics=metrics,trajectory=trajectory,config=vars(c),action_names=ACTION_NAMES,data_type='synthetic')
    except (ValueError,TypeError,OverflowError,ArithmeticError) as e:return jsonify(error=str(e)),400
@app.post('/compare_strategies')
def compare():
    try:
        data=request.get_json(silent=True);c=config_from(data)
        names=['none','moderate','targeted','strict','threshold']
        if (Path(__file__).parent/'results'/'q_table_seed11.npy').exists():names.append('q_learning')
        results={name:rollout(c,policy_for(name))[0] for name in names}
        return jsonify(comparison=results,data_type='synthetic')
    except (ValueError,TypeError,OverflowError,ArithmeticError) as e:return jsonify(error=str(e)),400
if __name__=='__main__':app.run(host='127.0.0.1',port=5000,debug=False)

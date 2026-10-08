import numpy as np
import pytest
from research_model import Config,SEIRModel,rollout,CONTACTS
from q_agent import QLearningAgent
from app import app

def test_mass_nonnegative_and_infection_free():
    m=SEIRModel(Config(days=180))
    while m.day<m.config.days:
        m.step(2)
        assert min(m.y)>=0
        for off,n in zip((0,4),m.sizes):assert abs(sum(m.y[off:off+4])-n)<1e-7
    metrics,_=rollout(Config(initial_exposed=0,initial_infected=0),lambda m:0)
    assert metrics['peak_infectious']==0
    assert metrics['new_infections']==0

def test_reciprocity_and_numerical_refinement():
    assert .3*CONTACTS[0][1]==pytest.approx(.7*CONTACTS[1][0])
    a,_=rollout(Config(step_size=.5),lambda m:0)
    b,_=rollout(Config(step_size=.125),lambda m:0)
    assert abs(a['peak_infectious']-b['peak_infectious'])/b['peak_infectious']<1e-5
    assert a['population_error']<1e-7

def test_control_effect_and_nonzero_initial_infection():
    a,_=rollout(Config(),lambda m:0)
    b,_=rollout(Config(),lambda m:3)
    assert 10<=b['peak_infectious']<a['peak_infectious']
    assert b['mean_restriction_cost']==pytest.approx(.85**2)

def test_terminal_update_and_frozen_eval():
    a=QLearningAgent(11);s=(0,2,0,0,0);a.q_table[:]=100
    a.learn(s,0,-1,s,done=True)
    assert a.q_table[s+(0,)]==pytest.approx(89.9)
    before=a.q_table.copy();a.choose_action(s,False)
    np.testing.assert_array_equal(before,a.q_table)

@pytest.mark.parametrize('params',[{'population':-1},{'initial_infected':50000},{'beta':-1},
    {'gamma':0},{'compliance':1.2},{'beta':'nan'},{'days':2.5},{'policy':'invented'},{}])
def test_api_validation(params):
    if not params:params={'initial_exposed':49000,'initial_infected':1}
    assert app.test_client().post('/run_simulation',json=params).status_code==400

def test_api_and_frontend():
    c=app.test_client();assert c.get('/').status_code==200
    assert c.get('/health').json['data_type']=='synthetic'
    r=c.post('/run_simulation',json={'days':31,'policy':'targeted'})
    assert r.status_code==200 and len(r.json['trajectory'])==32
    assert r.json['trajectory'][0]['I']==10
    assert c.post('/compare_strategies',json={'days':31}).status_code==200
    assert c.post('/run_simulation',data='broken',content_type='application/json').status_code==400

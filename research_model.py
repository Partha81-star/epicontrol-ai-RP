"""Two-cohort synthetic SEIR environment. Not calibrated to a real disease."""
from dataclasses import dataclass
import math
import numpy as np
ACTIONS = ((0.,0.),(.35,.35),(.15,.65),(.85,.85))
ACTION_NAMES = ('No restriction','Moderate uniform','Adult targeted','Strict uniform')
CONTACTS = ((.8,.35),(.15,1.2))
@dataclass
class Config:
    population: int = 49000
    children_fraction: float = .3
    beta: float = .3
    sigma: float = .2
    gamma: float = .1
    initial_exposed: float = 20
    initial_infected: float = 10
    compliance: float = .85
    days: int = 180
    capacity: float = 100
    hospital_fraction: float = .05
    step_size: float = .5
    cost_weight: float = .002
    overflow_weight: float = 1.
    switch_weight: float = .0002
    def validate(self):
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vars(self).values()):
            raise ValueError('All parameters must be finite numbers')
        if self.population<=0 or not 1<=self.days<=730 or int(self.days)!=self.days:
            raise ValueError('Population must be positive; horizon must be 1 to 730 whole days')
        if not 0<self.children_fraction<1 or not 0<=self.compliance<=1:
            raise ValueError('Invalid cohort fraction or compliance')
        if self.beta<0 or min(self.sigma,self.gamma,self.capacity)<=0:
            raise ValueError('Invalid transition rate or capacity')
        if min(self.initial_exposed,self.initial_infected,self.cost_weight,self.overflow_weight,self.switch_weight)<0:
            raise ValueError('Initial states and penalty weights must be nonnegative')
        if self.initial_exposed+self.initial_infected>self.population:
            raise ValueError('Initial exposed plus infectious exceeds population')
        if not 0<=self.hospital_fraction<=1 or not 0<self.step_size<=.5:
            raise ValueError('Invalid hospital fraction or integration step')
class SEIRModel:
    def __init__(self,config=None):
        self.config=config or Config();self.config.validate();self.reset()
    def reset(self):
        c=self.config
        self.sizes=(c.population*c.children_fraction,c.population*(1-c.children_fraction))
        self.y=tuple(v for n in self.sizes for v in
            (n*(1-(c.initial_exposed+c.initial_infected)/c.population),n*c.initial_exposed/c.population,n*c.initial_infected/c.population,0.))
        self.day,self.previous_action=0,0;self.history=[self.record()]
        return self.state()
    def state(self):
        n=self.config.population
        s,e,i=(self.y[j]+self.y[j+4] for j in range(3))
        return (min(self.day//30,5),int(np.digitize(s/n,[.5,.9])),int(np.digitize(e/n,[.002,.02])),
                int(np.digitize(i/n,[.002,.02])),self.previous_action)
    def derivative(self,y,action):
        c=self.config;f0,f1=(1-c.compliance*u for u in ACTIONS[action])
        i0,i1=y[2]/self.sizes[0],y[6]/self.sizes[1]
        l0=c.beta*f0*(CONTACTS[0][0]*f0*i0+CONTACTS[0][1]*f1*i1)
        l1=c.beta*f1*(CONTACTS[1][0]*f0*i0+CONTACTS[1][1]*f1*i1)
        out=[]
        for off,force in ((0,l0),(4,l1)):
            s,e,i,_=y[off:off+4];new=force*s
            out.extend((-new,new-c.sigma*e,c.sigma*e-c.gamma*i,c.gamma*i))
        return tuple(out)
    def advance_day(self,action):
        remaining=1.
        while remaining>1e-12:
            h=min(self.config.step_size,remaining);y=self.y
            k1=self.derivative(y,action)
            k2=self.derivative(tuple(v+h*k/2 for v,k in zip(y,k1)),action)
            k3=self.derivative(tuple(v+h*k/2 for v,k in zip(y,k2)),action)
            k4=self.derivative(tuple(v+h*k for v,k in zip(y,k3)),action)
            self.y=tuple(v+h*(a+2*b+2*d+e)/6 for v,a,b,d,e in zip(y,k1,k2,k3,k4))
            if min(self.y)<-1e-7:raise ArithmeticError('Negative compartment: reduce integration step')
            remaining-=h
        self.day+=1
    def step(self,action):
        if int(action)!=action or action not in range(4):raise ValueError('Action must be integer 0 to 3')
        if self.day>=self.config.days:raise ValueError('Episode has ended')
        c=self.config;reward=0.
        cost=sum(n*u*u for n,u in zip(self.sizes,ACTIONS[action]))/c.population
        reward-=c.switch_weight*sum(abs(a-b) for a,b in zip(ACTIONS[action],ACTIONS[self.previous_action]))/2
        for _ in range(min(7,c.days-self.day)):
            before=self.y[0]+self.y[4];self.advance_day(action)
            new=before-self.y[0]-self.y[4];h=c.hospital_fraction*(self.y[2]+self.y[6])
            reward-=new/c.population+c.overflow_weight*max(h-c.capacity,0)/c.population+c.cost_weight*cost
            self.previous_action=action;self.history.append(self.record())
        return self.state(),reward,self.day>=c.days
    def record(self):
        return {'day':self.day,'S':self.y[0]+self.y[4],'E':self.y[1]+self.y[5],'I':self.y[2]+self.y[6],
                'R':self.y[3]+self.y[7],'child_I':self.y[2],'adult_I':self.y[6],'action':self.previous_action,
                'hospital_proxy':self.config.hospital_fraction*(self.y[2]+self.y[6])}
def rollout(config,policy):
    m=SEIRModel(config);total_reward=0.
    while m.day<config.days:
        _,reward,_=m.step(int(policy(m)));total_reward+=reward
    h=m.history;peak=max(h,key=lambda r:r['I'])
    cost=np.mean([sum(n*u*u for n,u in zip(m.sizes,ACTIONS[r['action']]))/config.population for r in h[1:]])
    metrics={'peak_infectious':peak['I'],'peak_day':peak['day'],'new_infections':h[0]['S']-h[-1]['S'],
             'attack_rate':(config.population-h[-1]['S'])/config.population,
             'peak_hospital_proxy':max(r['hospital_proxy'] for r in h),
             'days_above_capacity':sum(r['hospital_proxy']>config.capacity for r in h[1:]),
             'mean_restriction_cost':float(cost),'return':total_reward,
             'population_error':max(abs(sum(r[k] for k in ('S','E','I','R'))-config.population) for r in h)}
    return metrics,h

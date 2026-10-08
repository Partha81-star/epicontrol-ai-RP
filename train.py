from pathlib import Path
import csv
import numpy as np
from research_model import Config,SEIRModel
from q_agent import QLearningAgent
def train_agent_function(episodes=1200,seed=11,output_dir=None):
    target=Path(output_dir or Path(__file__).parent/'results');target.mkdir(parents=True,exist_ok=True)
    agent=QLearningAgent(seed);rng=np.random.default_rng(seed+100);rows=[]
    for episode in range(episodes):
        c=Config(beta=float(rng.uniform(.24,.36)),compliance=float(rng.uniform(.7,1)),
                 initial_exposed=int(rng.integers(10,51)),initial_infected=int(rng.integers(5,21)))
        m=SEIRModel(c);state=m.state();ret=0.;done=False
        while not done:
            action=agent.choose_action(state);nxt,reward,done=m.step(action)
            agent.learn(state,action,reward,nxt,done);state=nxt;ret+=reward
        rows.append({'episode':episode+1,'return':ret,'epsilon':agent.epsilon});agent.decay_epsilon()
        if (episode+1)%300==0:print(f'seed {seed}: {episode+1}/{episodes}',flush=True)
    np.save(target/f'q_table_seed{seed}.npy',agent.q_table)
    with (target/f'training_seed{seed}.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    return agent
if __name__=='__main__':train_agent_function()

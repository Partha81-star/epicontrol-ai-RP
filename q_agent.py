import numpy as np
class QLearningAgent:
    def __init__(self,seed=11):
        self.q_table=np.zeros((6,3,3,3,4,4));self.rng=np.random.default_rng(seed)
        self.learning_rate,self.discount_factor=.1,.95
        self.epsilon,self.epsilon_min,self.epsilon_decay=1.,.05,.997
    def choose_action(self,state,explore=True):
        if explore and self.rng.random()<self.epsilon:return int(self.rng.integers(4))
        return int(np.argmax(self.q_table[state]))
    def learn(self,state,action,reward,next_state,done=False):
        index=tuple(state)+(action,)
        target=reward if done else reward+self.discount_factor*np.max(self.q_table[next_state])
        self.q_table[index]+=self.learning_rate*(target-self.q_table[index])
    def decay_epsilon(self):self.epsilon=max(self.epsilon_min,self.epsilon*self.epsilon_decay)

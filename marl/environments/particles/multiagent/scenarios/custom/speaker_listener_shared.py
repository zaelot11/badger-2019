from typing import Union, List

import numpy as np
from marl.environments.particles.multiagent.core import World, Agent, Landmark
# from multiagent.scenarios import BaseScenario
from marl.environments.particles.multiagent.scenarios.base_scenario import BaseScenario
from marl.environments.particles.multiagent.scenarios.custom.configurable_scenario import ConfigurableScenario


class Scenario(ConfigurableScenario):
    """Version of the Speaker Listener task for agents with shared policies and comm that does not go through the env.

    2 agents, Speaker tells the listener where to go, listener receives the message and goes there:

    Speaker (agent 0) is not movable, it tells to listener to which landmark (3 of them) should navigate.
        observation = [v_x, v_y, [relative landmark positions], [R,G,B]]
            -the only relevant part of the observation is RGB which describes the goal landmark
        action = [move_x, move_y]
            - movement does not matter, but the speaker can move in the environment
            - agent should communicate the goal to the listener

    Listener (agent 1) is movable, should move based on the message from the speaker.
        observation = [v_x, v_y, [relative landmark positions], [R, G, B]]
            -the RGB part is not valid (zeroed-out)
        action = [move_x, move_y]

    Notes:
        -the listener does not perceive colors, the colors should correspond to the
        positions landmarks in the observation of the listener.
    """

    def __init__(self):
        super().__init__(num_agents=2)

    def setup(self, rollout_length: int):
        super().setup()

    def make_world(self):
        world = World()
        # set any world properties first
        world.dim_c = 3
        num_landmarks = 3
        world.collaborative = True
        # add emergent_comm
        world.agents = [Agent() for i in range(self.num_agents)]
        for i, agent in enumerate(world.agents):
            agent.name = 'agent %d' % i
            agent.collide = False
            agent.size = 0.075
        # speaker
        world.agents[0].movable = True
        world.agents[0].silent = True  # comm not done through the env..
        # listener
        world.agents[1].silent = True
        # add landmarks
        world.landmarks = [Landmark() for i in range(num_landmarks)]
        for i, landmark in enumerate(world.landmarks):
            landmark.name = 'landmark %d' % i
            landmark.collide = False
            landmark.movable = False
            landmark.size = 0.04
        # make initial conditions
        self.reset_world(world)
        return world

    def reset_world(self, world):
        super().reset_world(world)

        # assign goals to emergent_comm
        for agent in world.agents:
            agent.goal_a = None
            agent.goal_b = None
        # want listener to go to the goal landmark
        world.agents[0].goal_a = world.agents[1]
        world.agents[0].goal_b = np.random.choice(world.landmarks)
        # random properties for emergent_comm
        for i, agent in enumerate(world.agents):
            agent.color = np.array([0.25, 0.25, 0.25])
        # random properties for landmarks
        world.landmarks[0].color = np.array([0.65, 0.15, 0.15])
        world.landmarks[1].color = np.array([0.15, 0.65, 0.15])
        world.landmarks[2].color = np.array([0.15, 0.15, 0.65])
        # special colors for goals
        world.agents[0].goal_a.color = world.agents[0].goal_b.color + np.array([0.45, 0.45, 0.45])
        # set random initial states
        for agent in world.agents:
            agent.state.p_pos = np.random.uniform(-1, +1, world.dim_p)
            agent.state.p_vel = np.zeros(world.dim_p)
            agent.state.c = np.zeros(world.dim_c)
        for i, landmark in enumerate(world.landmarks):
            landmark.state.p_pos = np.random.uniform(-1, +1, world.dim_p)
            landmark.state.p_vel = np.zeros(world.dim_p)

    def benchmark_data(self, agent, world):
        # returns data for benchmarking purposes
        return self.reward(agent, reward)

    def reward(self, agent, world):
        # squared distance from listener to landmark
        a = world.agents[0]
        dist2 = np.sum(np.square(a.goal_a.state.p_pos - a.goal_b.state.p_pos))
        return -dist2

    def observation(self, agent, world):
        super().observation(agent, world)

        # goal color
        goal_color = np.zeros(world.dim_color)
        if agent.goal_b is not None:
            goal_color = agent.goal_b.color

        # get positions of all entities in this agent's reference frame
        entity_pos = []
        for entity in world.landmarks:
            entity_pos.append(entity.state.p_pos - agent.state.p_pos)

        # speaker
        if agent == world.agents[0]:
            # RGB of the goal
            return np.concatenate([agent.state.p_vel] +  # my velocity
                                  entity_pos +  # other entity positions
                                  [goal_color] +  # color of the goal
                                  [np.ones(1, )])  # id of other agent
        # listener
        if agent == world.agents[1]:
            # goal hidden
            return np.concatenate([agent.state.p_vel] +  # my velocity
                                  entity_pos +  # other entity positions
                                  [np.zeros(3)] +  # zeroed-out goal
                                  [np.zeros(1,)])  # id of other agent

        raise Exception('Unexpected agent')


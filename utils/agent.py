import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import os 
import copy
import time 
import random
import numpy as np 
from utils.utils import printOut
import json

device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
class A2CAgent(object):
    
    def __init__(self, actor, critic, args, env, dataGen):
        self.actor = actor  # policy model issuing routes
        self.critic = critic  # model that predicts route cost
        self.args = args 
        self.env = env 
        self.dataGen = dataGen 
        out_file = open(os.path.join(args['log_dir'], 'results.txt'),'w+') 
        self.prt = printOut(out_file,args['stdout_print'])
        print("agent is initialized")
        
    def train(self):
        args = self.args 
        env = self. env 
        dataGen = self.dataGen
        actor = self.actor
        critic = self.critic 
        prt = self.prt 
        actor.train()
        critic.train()
        max_epochs = args['n_train']

        actor_optim = optim.Adam(actor.parameters(), lr=args['actor_net_lr'])
        critic_optim = optim.Adam(critic.parameters(), lr=args['critic_net_lr'])
        
        best_model = 1000
        val_model = 1000
        r_test = []
        r_val = []
        s_t = time.time()
        print("training started")
        for i in range(max_epochs):
            # new data batch is generated

            data = dataGen.get_train_next()
            env.input_data = data  # Loads input data (client coordinates)
            # init state: where the truck/drone is and avail_actions: what nodes are available
            state, avail_actions = env.reset()  # route simulation from scratch

            data = torch.from_numpy(data[:, :, :2].astype(np.float32)).to(device)
            # [b_s, hidden_dim, n_nodes]
            static_hidden = actor.emd_stat(data).permute(0, 2, 1)
            # critic inputs 
            static = torch.from_numpy(env.input_data[:, :, :2].astype(np.float32)).permute(0, 2, 1).to(device)
            w = torch.from_numpy(env.input_data[:, :, 2].reshape(env.batch_size, env.n_nodes, 1).astype(np.float32)).to(device)
            
            # lstm initial states 
            hx = torch.zeros(1, env.batch_size, args['hidden_dim']).to(device)
            cx = torch.zeros(1, env.batch_size, args['hidden_dim']).to(device)
            last_hh = (hx, cx)
       
            # prepare input 
            ter = np.zeros(env.batch_size).astype(np.float32)
            decoder_input = static_hidden[:, :, env.n_nodes-1].unsqueeze(2)
       
            #[n_nodes, rem_time]
            time_vec_truck = np.zeros([env.batch_size, 2])
            # [n_nodes, rem_time, weigth]
            time_vec_drone = np.zeros([env.batch_size, 3])
            
            # storage containers 
            logs = []  # logarithms of probabilities
            actions = []
            probs = []
            time_step = 0
            
            while time_step < args['decode_len']:
                terminated = torch.from_numpy(ter.astype(np.float32)).to(device)
                for j in range(2):
                    # truck takes action 
                    if j == 0:
                        avail_actions_truck = torch.from_numpy(avail_actions[:, :, 0].reshape([env.batch_size, env.n_nodes]).astype(np.float32)).to(device)
                        dynamic_truck = torch.from_numpy(np.expand_dims(state[:, :, 0], 2)).to(device)
                        # selects the next node given the mask and LSTM
                        idx_truck, prob, logp, last_hh = actor.forward(static_hidden, dynamic_truck, decoder_input, last_hh, 
                                                                     terminated, avail_actions_truck)
                        # idx_truck-selected node, probability, log probability, new LSTM state
                        b_s = np.where(np.logical_and(avail_actions[:, :, 1].sum(axis=1)>1, env.sortie==0))[0]
                        avail_actions[b_s, idx_truck[b_s].cpu(), 1] = 0
                        # actions-list of indexes of selected nodes
                        avail_actions_drone = torch.from_numpy(avail_actions[:, :, 1].reshape([env.batch_size, env.n_nodes]).astype(np.float32)).to(device)
                        idx = idx_truck 
                    else:
                        dynamic_drone = torch.from_numpy(np.expand_dims(state[:, :, 1], 2)).to(device)
                        idx_drone, prob, logp, last_hh = actor.forward(static_hidden, dynamic_drone, decoder_input, last_hh, 
                                                                     terminated, avail_actions_drone)
                        idx = idx_drone 
                
                    decoder_input =  torch.gather(static_hidden, 2, idx.view(-1, 1, 1).expand(env.batch_size, args['hidden_dim'], 1)).detach()
                    logs.append(logp.unsqueeze(1))
                    actions.append(idx.unsqueeze(1))
                    probs.append(prob.unsqueeze(1))

                # calculates the new state for the truck and drone - (route)
                state, avail_actions, ter, time_vec_truck, time_vec_drone = env.step(idx_truck.cpu().numpy(), idx_drone.cpu().numpy(), time_vec_truck, time_vec_drone, ter)
                # time_vec_ : remaining travel times
                time_step += 1
         
            print("epochs: ", i)
            actions = torch.cat(actions, dim=1)  # (batch_size, seq_len)
            logs = torch.cat(logs, dim=1)  # (batch_size, seq_len)
            # Query the critic for an estimate of the reward
            critic_est = critic(static, w).view(-1)
            R = env.current_time.astype(np.float32)   # reward
            R = torch.from_numpy(R).to(device)
            advantage = (R - critic_est)  # how much was the actor better/worse than expected
            actor_loss = torch.mean(advantage.detach() * logs.sum(dim=1))  # improves policy if the advantage is positive
            critic_loss = torch.mean(advantage ** 2)  # learns to predict the reward

            actor_optim.zero_grad()
            actor_loss.backward()
           
            torch.nn.utils.clip_grad_norm_(actor.parameters(), args['max_grad_norm'])
            actor_optim.step()
            critic_optim.zero_grad()
            critic_loss.backward()
            torch.nn.utils.clip_grad_norm_(critic.parameters(), args['max_grad_norm'])
            critic_optim.step()
        
            e_t = time.time() - s_t
            print("e_t: ", e_t)
            if i % args['test_interval'] == 0:
                # testing the model for validation
                R = self.test()
                r_test.append(R)
                np.savetxt("trained_models/test_rewards.txt", r_test)
            
                print("testing average rewards: ", R)
                # if the result has improved, the best checkpoint is saved
                if R < best_model:
                 #   R_val = self.test(inference=False, val=False)
                    best_model = R
                    num = str(i // args['save_interval'])
                    torch.save(actor.state_dict(), 'trained_models/' + '/' + 'best_model' + '_actor_truck_params.pkl')
                    torch.save(critic.state_dict(), 'trained_models/' + '/' + 'best_model' + '_critic_params.pkl')
                   
            if i % args['save_interval'] ==0:
                num = str(i // args['save_interval'])
                torch.save(actor.state_dict(), 'trained_models/' + '/' + num + '_actor_truck_params.pkl')
                torch.save(critic.state_dict(), 'trained_models/' + '/' + num + '_critic_params.pkl')

    def test(self):
        """Runs the agent on all test data"""
        args = self.args 
        env = self.env 
        dataGen = self.dataGen
        actor  = self.actor
        n=2
        prt = self.prt 
        actor.eval()
        
        data = dataGen.get_test_all()
        env.input_data = data 
        state, avail_actions = env.reset()
        #####
        start_depot = env.n_nodes - 1
        paths_truck = [[env.n_nodes - 1] for _ in range(env.batch_size)]
        paths_drone = [[] for _ in range(env.batch_size)]
        #####

        time_vec_truck = np.zeros([env.batch_size, 2])
        time_vec_drone = np.zeros([env.batch_size, 3])
        sols = []
        costs = []
        with torch.no_grad():
            data = torch.from_numpy(data[:, :, :2].astype(np.float32)).to(device)
            static_hidden = actor.emd_stat(data).permute(0, 2, 1)

            # lstm initial states 
            hx = torch.zeros(1, env.batch_size, args['hidden_dim']).to(device)
            cx = torch.zeros(1, env.batch_size, args['hidden_dim']).to(device)
            last_hh = (hx, cx)
       
            # prepare input 
            ter = np.zeros(env.batch_size).astype(np.float32)
            decoder_input = static_hidden[:, :, env.n_nodes-1].unsqueeze(2)
            time_step = 0
            while time_step < args['decode_len']:
                terminated = torch.from_numpy(ter.astype(np.float32)).to(device)
                for j in range(2):
                    # truck takes action 
                    if j == 0:
                        avail_actions_truck = torch.from_numpy(avail_actions[:, :, 0].reshape([env.batch_size, env.n_nodes]).astype(np.float32)).to(device)
                        dynamic_truck = torch.from_numpy(np.expand_dims(state[:, :, 0], 2)).to(device)
                        # to select actions at each step
                        idx_truck, prob, logp, last_hh = actor.forward(static_hidden, dynamic_truck, decoder_input, last_hh, 
                                                                     terminated, avail_actions_truck)
                        b_s = np.where(np.logical_and(avail_actions[:, :, 1].sum(axis=1)>1, env.sortie==0))[0]
                        avail_actions[b_s, idx_truck[b_s].cpu(), 1] = 0
                        avail_actions_drone = torch.from_numpy(avail_actions[:, :, 1].reshape([env.batch_size, env.n_nodes]).astype(np.float32)).to(device)
                        idx = idx_truck

                    else:
                        dynamic_drone = torch.from_numpy(np.expand_dims(state[:, :, 1], 2)).to(device)
                        idx_drone, prob, logp, last_hh = actor.forward(static_hidden, dynamic_drone, decoder_input, last_hh, 
                                                                     terminated, avail_actions_drone)
                        idx = idx_drone
                    ###
                    for b in range(env.batch_size):
                        if ter[b] == 0:  # did not complete the task
                            if j == 0:
                                # remove consecutive duplicates
                                if not paths_truck[b] or paths_truck[b][-1] != idx[b]:
                                    paths_truck[b].append(int(idx[b].item()))
                            else:
                                if not paths_drone[b] or paths_drone[b][-1] != idx[b]:
                                    paths_drone[b].append(int(idx[b].item()))
                    ###

                    decoder_input =  torch.gather(static_hidden, 2, idx.view(-1, 1, 1).expand(env.batch_size, args['hidden_dim'], 1)).detach()
                
                state, avail_actions, ter, time_vec_truck, time_vec_drone = env.step(idx_truck.cpu().numpy(), idx_drone.cpu().numpy(), time_vec_truck, time_vec_drone, ter)

                time_step += 1
                sols.append([idx_truck[n], idx_drone[n]])
                costs.append(env.time_step[n])
            for b in range(env.batch_size):
                if paths_truck[b][-1] != start_depot:
                    paths_truck[b].append(start_depot)
        R = copy.copy(env.current_time)
        costs.append(env.current_time[n])
        print("finished: ", sum(terminated))

        ###
        os.makedirs("results", exist_ok=True)
        with open("results/test_paths.json", "w") as f:
            json.dump({"truck": paths_truck, "drone": paths_drone}, f)

        ###

        fname = 'test_results-{}-len-{}.txt'.format(args['test_size'], 
                                                               args['n_nodes'])
        fname = 'results/' + fname
        np.savetxt(fname, R)
        actor.train()
        return R.mean()

    def sampling_batch(self, sample_size):
        """Improves the output quality.
        Repeats the same data sample_size times -> different routes every time.
        The best route is selected based on the reward
        """
        val_size = self.dataGen.get_test_all().shape[0]
        best_rewards = np.ones(sample_size)*100000
        best_sols = np.zeros([sample_size, self.args['decode_len'], 2])
        args = self.args 
        env = self.env 
        dataGen = self.dataGen
        actor  = self.actor
     
     
        actor.eval()
        actor.set_sample_mode(True)
        times = []
        initial_t = time.time()
        data = dataGen.get_test_all()
        data_list = [np.expand_dims(data[i, ...], axis=0) for i in range(data.shape[0])]
        best_rewards_list = []
        for d in data_list:
            data = np.repeat(d, sample_size, axis=0)
            env.input_data = data 
            
            state, avail_actions = env.reset()
            
            
            time_vec_truck = np.zeros([sample_size, 2])
            time_vec_drone = np.zeros([sample_size, 3])
            with torch.no_grad():
                data = torch.from_numpy(data[:, :, :2].astype(np.float32)).to(device)
                # [b_s, hidden_dim, n_nodes]
                static_hidden = actor.emd_stat(data).permute(0, 2, 1)  # node embeddings from encoder
            
                # lstm initial states 
                hx = torch.zeros(1, sample_size, args['hidden_dim']).to(device)
                cx = torch.zeros(1, sample_size, args['hidden_dim']).to(device)
                last_hh = (hx, cx)
        
                # prepare input 
                ter = np.zeros(sample_size).astype(np.float32)
                decoder_input = static_hidden[:, :, env.n_nodes-1].unsqueeze(2)  # last visited node embedding
                time_step = 0
                while time_step < args['decode_len']:
                    terminated = torch.from_numpy(ter).to(device)
                    for j in range(2):
                        # truck takes action 
                        if j == 0:
                            # mask of available nodes
                            avail_actions_truck = torch.from_numpy(avail_actions[:, :, 0].reshape([sample_size, env.n_nodes]).astype(np.float32)).to(device)
                            dynamic_truck = torch.from_numpy(np.expand_dims(state[:, :, 0], 2)).to(device)
                            idx_truck, prob, logp, last_hh = actor.forward(static_hidden, dynamic_truck, decoder_input, last_hh, 
                                                                        terminated, avail_actions_truck)
                            b_s = np.where(np.logical_and(avail_actions[:, :, 1].sum(axis=1)>1, env.sortie==0))[0]
                            avail_actions[b_s, idx_truck[b_s].cpu(), 1] = 0
                            avail_actions_drone = torch.from_numpy(avail_actions[:, :, 1].reshape([sample_size, env.n_nodes]).astype(np.float32)).to(device)
                            idx = idx_truck 
                        
                        else:
                            dynamic_drone = torch.from_numpy(np.expand_dims(state[:, :, 1], 2)).to(device)
                            idx_drone, prob, logp, last_hh = actor.forward(static_hidden, dynamic_drone, decoder_input, last_hh, 
                                                                        terminated, avail_actions_drone)
                            idx = idx_drone 

                        decoder_input =  torch.gather(static_hidden, 2, idx.view(-1, 1, 1).expand(sample_size, args['hidden_dim'], 1)).detach()
                
                    state, avail_actions, ter, time_vec_truck, time_vec_drone = env.step(idx_truck.cpu().numpy(), idx_drone.cpu().numpy(), time_vec_truck, time_vec_drone, ter)
                    time_step += 1

            R = copy.copy(env.current_time)
            print('R.shape:', R.shape)
            best_rewards = R.min(axis=0)
            print('best_rewards:', best_rewards)
            t = time.time() - initial_t
            times.append(t)
            best_rewards_list.append(best_rewards)        

        np.savetxt(f'results/best_rewards_list_{sample_size}_samples.txt', best_rewards_list)
        return best_rewards, times 

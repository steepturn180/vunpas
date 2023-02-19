import simpy
import random
import itertools
import numpy as np
import pandas as pd
import time
import matplotlib
import matplotlib.pyplot as plt
from haversine import haversine
import warnings
from numpy.random import default_rng
from scipy.spatial.distance import pdist, squareform
from EVTOL import initialEvtols
from scipy.stats import poisson
import math
import openpyxl
warnings.simplefilter(action='ignore',category=FutureWarning)
from OPERATOR import *
from PAX import *
from VERTIPORT import *
from PSU import *

from util import options


from collections import OrderedDict

# 12/28 version.TG(simulator/vertiport)
#
# TBD log should contain (waiting time, renege person, utilization rate, total distance_evtol flown, boarding_person_per eVTOL)

EVTOL_LOG=pd.DataFrame({'evtolID':[],'time':[],'status':[],'from':[],'to':[]})
rng=default_rng()
# env.process(pax_generator(env, vps, vert, operator, psu ))
def pax_generator(env, vps, from_, operator, simul_time=180, psu=None):
    
    simul_time = simul_time
    global num_renege, num_generated, PX_LOG,EVTOL_LOG
    for id in itertools.count():
      
      value = vp_df.iloc[from_]['gen']  # ex: 512 pxs
      lmbda= value/simul_time # average Passenger generating number Per minute ex: 512/180
      rnd_interval=math.ceil(random.expovariate(lmbda))
      yield env.timeout(rnd_interval) # Passenger Call Interval -> exponential Distribution @ each vertiport  
      # 1. Generate passenger
      
      to_ = np.argmax(rng.random()<pdest_in[from_]) 
      pax_id = from_*1000 + id
      pax = PAX_CLASS(env, vps[from_], vps[to_], pax_id,args)

      # Count the number of pax @ the from_ vertiport
      pax.from_.count_generated()
      #print(f'DEB PAX GEN: PAX made {env.now} where comes {from_} to{to_}')
      # To check destination of this pax has been set
      #assert pax.to_ is not None, f"pax.to_ is None. pax.from_={pax.from_}, pax.to_={pax.to_}"
      print(f"Time: {env.now} PAX: {pax.id} Vertiport:{pax.from_.id}-> {pax.to_.id}")
      
      # 2. Call EVTOl
      #etd, eta, avail_evtol = yield env.process(callEvtol(env, pax, operator, psu)) # returns eta/etd when EVTOl arrives
      env.process(pax.callEvtol(operator,psu))
      
    
def main(args):



  env = simpy.Environment()

  # generate vertiports
  max_vp_num = args.max_vp_num
  vps = [VERTIPORT_CLASS( env
                        , id=i
                        , charger     = args.charger
                        , fato_num    = args.fato_num   
                        , ramp_num    = args.ramp_num   
                        , way_num     = args.way_num    
                        , charger_num = args.charger_num) for i in range(max_vp_num)]

  # generate psu
  psu = PSU_CLASS(env)

  # generate operator
  operator = OPERATOR_CLASS(env, psu=psu, vps=vps, args=args)

  #psu.get_evtols(operator)

  # generate evtols and assign to vertiports
  initialEvtols(env, type=args.evtol, vps=vps , operator=operator, evtol_num=args.evtol_num)


  simul_time=args.time
  print("==================== Simulation Start ====================")

  # simpy process
 



  #for _ in itertools.count():
  for vert in range(len(vps)):
    env.process(pax_generator(env, vps, vert, operator, simul_time, psu))
  

  #env.process(operator.rebalancing(rebalancing_freq=30))
  env.run(until=simul_time)

  print("==================== Simulation End ====================")
  operator.show_results()
  #operator.PX_LOG.to_csv('px'+f'expr_id_{args.expr_id}_iter_{iter}'+'.csv')
  
  all_vp_results, all_evtol_results = operator.get_results()

  return all_vp_results, all_evtol_results




if __name__=='__main__': # directly Implemented in Interpreter



  # write expr settings
  args = options()
  file_path = f"./expr{args.expr_id}_settings_log.txt"

  args_dict = vars(args)
  with open(file_path, 'w') as f:
    # args: dictionary
    # k : key
    for k in args_dict:
        f.writelines([k, ':\t',str(args_dict[k]),'\n'])


  final_result_vps = [0]*args.max_vp_num # vps
  final_result_evtols = [0]* (args.max_vp_num * args.evtol_num) # total evtols

  # initialization
  for idx, _ in enumerate(final_result_vps):
    # [ array_of_generated, array_of_reneged ]
    final_result_vps[idx] = [np.zeros(args.iter), np.zeros(args.iter)]

  # initialization
  for idx, _ in enumerate(final_result_evtols):
    # [ num_flights, total_pax ]
    final_result_evtols[idx] = [np.zeros(args.iter), np.zeros(args.iter)]

  #print(final_result_vps)

  # run expr
  for n_iter in range(args.iter):
    all_vp_results, all_evtol_results = main(args)
    #print(all_vp_results)
    #print(all_evtol_results)

    # get each vp result
    for vp_idx, result in enumerate(all_vp_results):
        values = list(result.values())[0]
        generated = values[0]
        reneged = values[1]
        final_result_vps[vp_idx][0][n_iter] = generated
        final_result_vps[vp_idx][1][n_iter] = reneged


    # get each evtol result
    for evtol_idx, result in enumerate(all_evtol_results):
        values = list(result.values())[0]
        num_flights = values[0]
        total_pax   = values[1]
        final_result_evtols[evtol_idx][0][n_iter] = num_flights
        final_result_evtols[evtol_idx][1][n_iter] = total_pax  


    #print(final_result_vps)
    #print(final_result_evtols)

  vp_header =[ "generated.avg"
             , "generated.std"
             , "reneged.avg  "
             , "reneged.std  "]

  vp_index_label = ["vp_"+str(idx) for idx in range(args.max_vp_num)]
  #print(f"vp_index_label: {vp_index_label}")

  dir_list = ['./', 'results']
  path = os.path.join(*dir_list)
  if os.path.exists(path) is not True:
      os.makedirs(path)
  else:
      pass
  
  # ==== write vp results ====
  fname = ['expr_id_' + str(args.expr_id)  + \
          'vp_results.csv']

  path_list = dir_list+fname
  path = os.path.join(*path_list)

  gen_avg = []
  gen_std = []
  ren_avg = []
  ren_std = []
  for vp_id, vp_data in enumerate(final_result_vps):
    generated_values = final_result_vps[vp_id][0]
    reneged_values = final_result_vps[vp_id][1]

    gen_avg.append(np.mean(generated_values))
    gen_std.append(np.std(generated_values))

    ren_avg.append(np.mean(reneged_values))
    ren_std.append(np.std( reneged_values))

  gen_avg = pd.Series(gen_avg)
  gen_std = pd.Series(gen_std)
  ren_avg = pd.Series(ren_avg)
  ren_std = pd.Series(ren_std)

  vp_results = pd.concat([ gen_avg
                         , gen_std
                         , ren_avg
                         , ren_std], axis=1 )

  #print(vp_results)
  vp_results.to_csv(path, header=vp_header)


  # ==== write evtol results ====
  evtol_header =[ "num_flights.avg"
                , "num_flights.std"
                , "total_pax.avg  "
                , "total_pax.std  "]



  fname = ['expr_id_' + str(args.expr_id)  + \
          'evtol_results.csv']

  path_list = dir_list+fname
  path = os.path.join(*path_list)

  num_flights_avg = []
  num_flights_std = []
  total_pax_avg = []
  total_pax_std = []
  for evtol_id, evtol_data in enumerate(final_result_evtols):
    num_flights_values = final_result_evtols[evtol_id][0]
    total_pax_values = final_result_evtols[evtol_id][1]

    num_flights_avg.append(np.mean(num_flights_values))
    num_flights_std.append(np.std(num_flights_values))

    total_pax_avg.append(np.mean(total_pax_values))
    total_pax_std.append(np.std( total_pax_values))

  num_flights_avg = pd.Series(num_flights_avg)
  num_flights_std = pd.Series(num_flights_std)
  total_pax_avg = pd.Series(total_pax_avg)
  total_pax_std = pd.Series(total_pax_std)

  evtol_results = pd.concat([ num_flights_avg
                         , num_flights_std
                         , total_pax_avg
                         , total_pax_std], axis=1 )

  print(evtol_results)
  evtol_results.to_csv(path, header=evtol_header)

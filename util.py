import argparse
import numpy as np
import random




def options():
    parser = argparse.ArgumentParser(description="Vertiport Urban Air Mobility Network Performance Analysis")
    parser.add_argument('--expr_id', type=str, default='0', help="Experiment id(default=0)")
    parser.add_argument('--iter', type=int, default=1000, help="# of iterations(default=1000)")
    parser.add_argument('--rand', type=int, default=None, help="set random seed. (default: random simulation)")
    parser.add_argument('--time', type=int, default=180, help="simulation time(min) . (default: 180)")
   

    #Vertiport O
    parser.add_argument('--max_vp_num', type=int, default=12, help="# of VPs . (default: 4)")
    parser.add_argument('--fato_num', type=int, default=1, help="# of FATO . (default: 1)")
    parser.add_argument('--ramp_num', type=int, default=6, help="# of ramp . (default: 6)")
    parser.add_argument('--way_num', type=int, default=2, help="# of taxi way . (default: 2)")
    parser.add_argument('--charger_num', type=int, default=1, help="# of charging station . (default: 1)")
    parser.add_argument('--charger', type=float, default=250, help="charger kW . (default: 250)")
    

    #Operator_pax
    parser.add_argument('--evtol', type=str, default="K_Uam_30", help="Evtol type in str")
    parser.add_argument('--evtol_num',type=int ,default=5,help="Evtol number in RAMP(default: 5)")
    parser.add_argument('--pooling_time', type=int, default=5, help="# pooling time means time which operator waits for additional passenger. (default: 5)")
    parser.add_argument('--find_limit', type=int, default=10, help="limit time of finding for operator (default=10)")

    #passenger
    parser.add_argument('--pax_threshold',type=int,default=15,help='# of waiting threshold time for passenger(default=15)' )
    
    
    parser.add_argument('--simulation', type=bool, default=True, help="run simulation . (default: True)")
    
    
    parser.add_argument('--new', type=float, default=1., help="new_test arguments in console")

    args = parser.parse_args()
    
    return args



''' 
Randomness Control for Reproduce Simluation
'''
def controlRandomness(random_seed=None):

    if random_seed is not None:
        print(f"random seed = {random_seed}")
        np.random.seed(random_seed)
        random.seed(random_seed)

    else: # random
        print(f"random seed = {random_seed}")

import simpy
import pandas as pd
import numpy as np
from numpy.random import default_rng
import os
import csv

# read vp info.


vp_df=pd.read_excel(r"./30_AM.xlsx",index_col=0)


vpdest_temp=[]

for j in range(len(vp_df)):
    vpdest_temp.append([vp_df.iloc[j][i] for i in range(len(vp_df))])

vpdest_temp=np.array(vpdest_temp).reshape(len(vp_df),len(vp_df))
pdest_in=np.cumsum(vpdest_temp/vpdest_temp.sum(axis=1,keepdims=True),axis=1)





class VERTIPORT_CLASS():
    def __init__(self, env
                     #, id:str
                     , id
                     , charger     = 250
                     , fato_num    = 1
                     , ramp_num    = 6
                     , way_num     = 1
                     , charger_num = 1):
        self.env = env
        self.id = id
        self.fato = simpy.Resource(env, capacity = fato_num)
        self.ramp = [None]*ramp_num
        self.taxi = simpy.Resource(env, capacity = way_num)
        self.charger = simpy.Resource(env, capacity = charger_num)
        self.charging_rate = charger/60 # 250kW -> 4.2kWh in a minute
        self.taxi_time = 5 # 5 minutes
        self.lat = vp_df.iloc[id]['lat']
        self.lon = vp_df.iloc[id]['lon']
        self.lmbda = vp_df.iloc[id]['gen']

        # To check expected in/outboud evtols
        self.inbound_evtols = []
        self.outbound_evtols = []
        
        # data to collect
        self._num_reneged = 0
        self._num_generated = 0
        
    def count_renege(self):    
        self._num_reneged += 1

    def count_generated(self):    
        self._num_generated += 1


    def getAvailableEvtol(self):

        for idx, evtol in enumerate(self.ramp):
            if evtol != None:
                if evtol.state == "idle":
                    print(f"evtol{evtol.id} is in idle state")
                    get_evtol = evtol
                    self.ramp[idx] = None
                    return get_evtol

        print(f"No available eVTOLs")
    
    def monitor(self):
        try:
            reneged_by_generated =  self._num_reneged/self._num_generated
        except:
            reneged_by_generated = 0

        print(f"\n====Vertiport {self.id} Information")
        print(f"\t {reneged_by_generated*100:.2f}%  [reneged = {self._num_reneged}/ generated = {self._num_generated}]")
        print(f"\t {self.ramp}")
        for evtol in self.ramp:
            try:
                evtol.monitor()
            except:
                pass
        for evtol in self.inbound_evtols:
            try:
                evtol.monitor()
            except:
                pass


    def get_vp_results(self):
        try:
            reneged_by_generated =  self._num_reneged/self._num_generated
        except:
            reneged_by_generated = 0

        #print(f"\n====Vertiport {self.id} Information")
        #print(f"\t {reneged_by_generated*100:.2f}%  [reneged = {self._num_reneged}/ generated = {self._num_generated}]")
        #print(f"\t {self.ramp}")
        #for evtol in self.ramp:
        #    try:
        #        evtol.monitor()
        #    except:
        #        pass
        #for evtol in self.inbound_evtols:
        #    try:
        #        evtol.monitor()
        #    except:
        #        pass



        header =[ f"VP id {self.id}"
                , "generated"
                , "reneged" ]


        path = ['./', 'results']
        path = os.path.join(*path)
        if os.path.exists(path) is not True:
            os.makedirs(path)
        else:
            pass
        #for ramp in range(1,10):
        #for ramp in range(1,2):
        fname = 'vp_n_pax_results.csv'
        
        path = ['./', 'results', fname]
        path = os.path.join(*path)
        
        f = open(path, 'a')
        writer = csv.writer(f)
        
        avg_cal = np.zeros(len(header))
        # write header
        writer.writerow(header)
        
        # list concat.
        data_to_write = [None] + [self._num_generated] + [self._num_reneged]
        writer.writerow(data_to_write)

        #avg_cal += np.array(data_to_write)

        #writer.writerow('max_iter:'+str(max_iter))
        #writer.writerow(header)
        #writer.writerow(avg_cal/max_iter)
        f.close()


        #print(f"Vertiport {self.id} Information")
        #print(f"FATO: [{self.fato.count}/{self.fato.capacity}]")
        #print(f"\t - user : {self.fato.users}")
        #print(f"\t - queue: {self.fato.queue} type {type(self.fato.queue)} {len(self.fato.queue)}")
        #print(f"RAMP: ")
        #for evtol in self.ramp:
        #    if evtol != None:
        #        print(f"eVTOL {evtol.id} ")
        #    else:
        #        pass

        #print(f"charger: [{self.charger.count}/{self.charger.capacity}]")
        #print(f"\t - user : {self.charger.users}")
        #print(f"\t - queue: {self.charger.queue}")

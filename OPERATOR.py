from logging import raiseExceptions
from haversine import haversine
import numpy as np
from pandas import to_datetime
import pandas as pd 
import PAX
import VERTIPORT
import EVTOL


class OPERATOR_CLASS():

    def __init__(self, env, psu, vps:list, args):
        self.env = env
        self.evtols = []
        self.vps = vps
        self.psu = psu # to provide information to psu
        self.pooling_time = args.pooling_time
        self.PX_LOG =pd.DataFrame({'PAX':[],'From':[],'To':[],'Status':[],'Time':[],'eVTOL':[]})
        self.find_limit = args.find_limit
    def _gather_data(self):

        # data to collect so far
        self._num_total_generated = 0
        self._num_total_reneged = 0

        for vp in self.vps:
            self._num_total_generated += vp._num_generated
            self._num_total_reneged   += vp._num_reneged

    def show_results(self):
        self._gather_data()
        print(f"\n\n==================== RESULTS(now = {self.env.now}) ====================\n\n")
        
        #print(f"\t {self._num_total_reneged/self._num_total_generated*100 :.2f }%  reneged = {self._num_total_reneged}/ generated = {self._num_total_generated}")
        print(f"\t {self._num_total_reneged/self._num_total_generated*100:.2f}%  [reneged = {self._num_total_reneged}/ generated = {self._num_total_generated}]")
        self.psu.monitor()

        for vp in self.vps:
            vp.monitor()



    def get_results(self):
        print(f"\n\n==================== get results ====================\n\n")
        self._gather_data()
        
        all_vp_results = []
        # get vps' results
        for vp in self.vps:
            if vp._num_generated == 0:
                reneged_by_generated=0
                all_vp_results.append( { f"VP {vp.id}" : [vp._num_generated, vp._num_reneged, reneged_by_generated] } )
                
            else:    
                reneged_by_generated =  vp._num_reneged/vp._num_generated
                all_vp_results.append( { f"VP {vp.id}" : [vp._num_generated, vp._num_reneged, reneged_by_generated] } )
                

                
        all_evtol_results = []
        all_pax_results = []
        # get evtols' results
        for evtol in self.evtols:
            all_evtol_results.append( {f"EVTOL {evtol.id}" : [evtol._num_flights, evtol._total_pax]} )

            ## pax waiting_time
            #for pax in evtol._pax_log:
            #    all_pax_results.append((pax.from_, pax.waiting_time))
            #    print(f"pax waiting_time: {pax.waiting_time}")

        return all_vp_results, all_evtol_results
        #all_results_df = pd.DataFrame.from_dict(all_results, orient='index')
            
            # out-of-date
            #vp.get_vp_results()







    def evtol_register(self, evtol):
        self.evtols.append(evtol)
        self.psu._get_evtols(self) # psu get evtol list

    def evtol_monitor(self, process_time, evtol, pax, state:str):
        print(f"\n\nfrom_ {pax.from_.id} -> to_ {pax.to_.id} evtol {evtol.id} || protocol {state}  \t now = {self.env.now} || process time: {process_time}")
        for evtol in self.evtols:
            evtol.monitor()


    def find_avail_evtol(self,pax, from_ , to_):
        avail_evtol = None
        earliest_evtol =None
        find_avail_evtol_time=0
        yield self.env.timeout(0.0)

        while find_avail_evtol_time<self.find_limit:
            find_avail_evtol_time+=1
            for evtol in from_.ramp:
                 # ramp contains waiting evtol in a list
                if evtol == None:
                    continue

                 # assign 'onBoarding' evtol to passenger
                elif (evtol.state == 'onBoarding') and \
                    (evtol.to_ == to_) and \
                    (evtol.seats.level>0) and \
                    (evtol.dispatched):

                    avail_evtol = evtol
                    #print(f"DEBUGGING onboarding {avail_evtol.id} by OPERATOR_find")
                    return avail_evtol
                    
                 # get a new available evtol
                elif evtol.state == 'idle':

                    avail_evtol = evtol
                    #print(f"DEBUGGING idle {avail_evtol.id} by OPERATOR_find")
                    return avail_evtol
                else:
                    pass
                
            if avail_evtol is None and len(from_.inbound_evtols)>0:
                    # get inbound evtol 
                    
                for evt in from_.inbound_evtols:
                    if (evt.future_dest == to_) and (len(evt.future_queue) <=3):
                        avail_evtol=evt
                        evt.future_queue.append(pax.id)
                        #print(f"DEBUGGING incoming {avail_evtol.id} by OPERATOR_find")
                        return avail_evtol
                    else:
                        pass
                    
                    
                eta_array = np.array([evtol.eta for evtol in from_.inbound_evtols if evtol.future_dispatched== False])
                new_from=[evtol for evtol in from_.inbound_evtols if evtol.future_dispatched == False]
                try:
                    
                    earliest_evtol = new_from[np.argmin(eta_array)]
                    #print(f"DEBUGGING incoming new {earliest_evtol.id} by OPERATOR_find")
                    earliest_evtol.future_queue.append(pax.id)
                    return earliest_evtol
                    
                except:
                    earliest_evtol = None
                    
                    return earliest_evtol
                
            if avail_evtol is None:
                yield self.env.timeout(1)

        return None


# file_plan
    def file_plan(self, avail_evtol, from_, to_,psu):
        
        # An avail_evtol can be either at a caller(pax)'s vertiport or at another vertiport(Inbound).

        # 1. An avail_evtol is at a caller's vertiport.(Onboarding,idle(planned),idle(plan X)) 
        if avail_evtol in from_.ramp:

            # The avail_evtol has no flight information -> file plan ins required
            if avail_evtol.dispatched == False:      
                # double check the condition in a different way 
                assert (avail_evtol in from_.ramp) and (avail_evtol.state == 'idle'), f"avail_evtol {avail_evtol.id} is not in ramp and not idle"

                # notify passenger 1min
                # boarding time    5min
                # taxi time        5min

                avail_evtol.initial_file_plan_time = self.env.now
                etd = eta = avail_evtol.initial_file_plan_time
                # Estimated time of depature(ETD) 
                notify_passenger = 1
                boarding_time    = 5 # OPERATOR contorls pooling_time(boarding_time)
                taxi_time        = 5 # VERTIPORT controls Taxi_time

                # Estimated time of arrival(ETA) 
                distance = round(haversine((from_.lat, from_.lon), (to_.lat, to_.lon)))
                flight_time = distance / avail_evtol.speed * 60 # hr -> min
                
                
                # calculate charging time
                fato_energy = avail_evtol.energy_data[0]
                # cruise_energy (kWh/min)
                cruise_energy = avail_evtol.energy_data[1]
                cruise_time = distance / avail_evtol.speed * 60
                expected_energy_consumption = cruise_energy * cruise_time + 2*fato_energy

                # charging_time (min)
                expected_charging_time  = expected_energy_consumption / from_.charging_rate

                # ETD
                etd += notify_passenger + boarding_time + taxi_time
                # ETA
                eta = etd + flight_time + psu.separation_time

                avail_evtol.eta=eta
                avail_evtol.etd=etd

                return etd, eta

            # The avail_evtol already has a flight information; at least one pax is in the evtol.
            # -> no need to file a plan.
            else:
                assert avail_evtol.etd is not None, f"evtol etd is None"
                return avail_evtol.etd, avail_evtol.eta

        # 2. An avail_evtol is not at the caller's vertiport.(Inbound) 
        elif avail_evtol in from_.inbound_evtols:

            if avail_evtol.future_dispatched== False:
                # notify passenger(deleted) 1min
                # boarding time    5min
                # taxi time        5min

                avail_evtol.future_initial_file_plan_time = self.env.now
                #etd = eta = avail_evtol.future_initial_file_plan_time
                # Estimated time of depature(ETD) 
                #notify_passenger = 1
                boarding_time    = 5
                taxi_time        = 5

                # Estimated time of arrival(ETA) 
                distance = round(haversine((from_.lat, from_.lon), (to_.lat, to_.lon)))
                flight_time = distance / avail_evtol.speed * 60 # hr -> min
                deboarding_time  = 5
                
                # calculate charging time
                fato_energy = avail_evtol.tank.capacity * 0.048 
                # cruise_energy (kWh/min)
                cruise_energy = avail_evtol.tank.capacity * avail_evtol.energy_data[0]
                cruise_time = round(distance / avail_evtol.speed * 60)
                expected_energy_consumption = cruise_energy * cruise_time + 2*fato_energy

                # charging_time (min)
                expected_charging_time  = expected_energy_consumption / from_.charging_rate


                # ETD
                # If inbound evtol is in landing state, the eta will be None at the state 
                # Instead, actual arrival time is used.
                to_come_eta = avail_evtol.eta if avail_evtol.eta is not None else avail_evtol.actual_arrival_time 
                #remaining_time = eta_to_be_calculate - self.env.now
                remaining_time = to_come_eta # 시각
                etd = remaining_time + taxi_time + deboarding_time + expected_charging_time+boarding_time + taxi_time 

                # ETA
                eta = etd + flight_time 
                avail_evtol.future_eta=eta
                avail_evtol.future_etd=etd
                return etd, eta

            else:
                assert avail_evtol.future_etd is not None, f"future_etd is None"
                return avail_evtol.future_etd, avail_evtol.future_eta
        else:
            print(f"{avail_evtol.id} -{avail_evtol.state} from{from_.id} to{to_.id}") # Last Call->should be fixed
            return avail_evtol.etd, avail_evtol.eta

    def get_evtol_info(self, id):
        for evtol in self.evtols:
            if evtol.id == id:
                #evtol.monitor()
                break
            else:
                continue


    def get_vp_info(self, id):
        for vp in self.vps:
            if vp.id == str(id):
                #vp.monitor()
                break
            else:
                continue

# monitor_balance ->for rebalancing - TBD
    def monitor_balance(self):
        print("monitor_balance")

# rebalancing - TBD
    def rebalancing(self, rebalancing_freq:int=30):
        yield self.env.timeout(rebalancing_freq)
        print("rebalancing==")
        self.move_from_to()

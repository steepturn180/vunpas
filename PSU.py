from haversine import haversine
import numpy as np


class PSU_CLASS():
    def __init__(self, env, separation_time = 3):
        self.env = env
        self.separation_time = separation_time
        self._evtols_in_cruise = []
        self._evtols_in_landing = []
        self._evtols = []
    def _get_evtols_in_cruise(self):
        
        for evtol in self._evtols:
            if evtol.state == 'cruise':
                self._evtols_in_cruise.append(evtol)
            else:
                pass
        
    def _get_evtols_in_landing(self, remove=False):
        
        if remove is not False:
            for evtol in self._evtols_in_cruise:
                if evtol.state == 'landing':
                    self._evtols_in_cruise.remove(evtol)
                    self._evtols_in_landing.append(evtol)
                else:
                    pass
        else:
            for evtol in self._evtols_in_landing:
                if evtol.state != 'landing':
                    self._evtols_in_landing.remove(evtol)
                else:
                    pass


        
    def monitor(self):
        print(f"\n\n PSU Report (only evtols in cruise) now: {self.env.now} ")
        for evtol in self._evtols_in_cruise:
            try:
                assert evtol.state == 'cruise', f"evtol {evtol.id} should be in cruise but {evtol.state}"
                evtol.monitor()
            except:
                pass


        print(f"\n\n PSU Report (only evtols in landing) now: {self.env.now} ")
        for evtol in self._evtols_in_landing:
            try:
                assert evtol.state == 'landing', f"evtol {evtol.id} should be in landing but {evtol.state}"
                evtol.monitor()
            except:
                pass


    def _get_evtols(self, operator):
        self._evtols = operator.evtols

    def decision(self, avail_evtol,etd, eta, from_, to_):
        # Decision threshold(window)
        threshold = 3 # 3min
        file_accept = True
        
        
        # from_ fato outboud 
        # etd_array [ 8 , 11, 18, 22] <- 15
        # etd_array-15 [ -7, -4, 3, 7]
    
        
        from_etd_array = np.array([evtol.etd for evtol in from_.outbound_evtols])
        try:
            from_etd_margin = from_etd_array - etd
            from_etd_margin = np.abs(from_etd_margin)
            threshold_check = (from_etd_margin < threshold)
            threshold_check = sum(threshold_check)
            file_accept = bool(~threshold_check) # True == file accepted
        except:
            pass


        # from_ fato inboud 
        from_eta_array = np.array([evtol.eta for evtol in from_.inbound_evtols])
        try:
            from_eta_margin = from_eta_array - etd
            from_eta_margin = np.abs(from_eta_margin)
            threshold_check = (from_eta_margin < threshold)
            threshold_check = sum(threshold_check)
            file_accept = file_accept & bool(~threshold_check) # True == file accepted
        except:
            pass



        # to_ fato inboud 
        to_eta_array = np.array([evtol.eta for evtol in to_.inbound_evtols])
        try:
            to_eta_margin = to_eta_array - eta
            to_eta_margin = np.abs(to_eta_margin)
            threshold_check = (to_eta_margin < threshold)
            threshold_check = sum(threshold_check)
            file_accept = bool(~threshold_check) # True == file accepted
        except:
            pass


        # to_ fato outboud 
        to_etd_array = np.array([evtol.etd for evtol in to_.outbound_evtols])
        try:
            to_etd_margin = to_etd_array - etd
            to_etd_margin = np.abs(to_etd_margin)
            threshold_check = (to_etd_margin < threshold)
            threshold_check = sum(threshold_check)
            file_accept = file_accept & bool(~threshold_check) # True == file accepted
        except:
            pass

        if file_accept:
            return True
        else:
            return False
        

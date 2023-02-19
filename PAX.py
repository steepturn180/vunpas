from OPERATOR import *
from VERTIPORT import *
from PSU import *



class PAX_CLASS():
    def __init__(self, env, from_, to_, id,args):
        self.env   = env
        self.from_ = from_ # VERTIPORT_CLASS
        self.to_   = to_   # VERTIPORT_CLASS
        self.id    = id
        self.call_time = self.env.now
        self.threshold = args.pax_threshold # waiting time
        self.eta = None
        self.etd = None
        self.state = None
        self.waiting_time = 0
        
    def status(self):
        print("="*20)
        print(f"self.from_ : {self.from_} ")
        print(f"self.to_   : {self.to_  } ")
        print(f"self.id    : {self.id   } ")

    def callEvtol(self, operator, psu=None):
        global PX_LOG, EVTOL_LOG
        etd = eta = None
        avail_evtol = None  
        #operator.PX_LOG=operator.PX_LOG.append({'PAX': self.id ,'From':self.from_.id,'To':self.to_.id,'Status':'called','Time':self.env.now,'eVTOL':None},ignore_index=True)    
        #print(f'[Time:{self.env.now}]: pax{self.id} call air taxi from vp{self.from_.id} to vp{self.to_.id}')
        avail_evtol = yield self.env.process(operator.find_avail_evtol(self,self.from_, self.to_))
        
        
        if avail_evtol is not None:   # If available EVTOl is found,
            
            case_i=(avail_evtol.dispatched) and (avail_evtol in self.from_.ramp) # evtol_in_ramp/ px_boarded
            case_ii=(avail_evtol.future_dispatched) and (avail_evtol in self.from_.inbound_evtols) # evtol_incoming/ px_boarded
            if case_i or case_ii:
                #etd=avail_evtol.etd if avail_evtol.etd is not None else avail_evtol.future_etd
                if case_i:
                    yield avail_evtol.seats.get(1)
                    avail_evtol._pax_log.append(self)
                    self.waiting_time = self.env.now - self.call_time
                    # after door_close 
                    # after take_off
                    # after door_off
                    # return
                    # self.env.process(self.board(avail_evtol,etd,eta,operator,psu, is_case2=True))            #elif avail_evtol.dispatched == False:
                elif case_ii:                                     
                    if self.decision(avail_evtol.future_etd) is False: # can't wait
                        print(f'[Time: {self.env.now}]: pax{self.id} couldn"t wait evtol{avail_evtol.id}..so renege')
                        avail_evtol.future_queue.remove(self.id)
                        self.from_._num_reneged+=1 
                        return
                    else: # can wait
                        print(f'[Time: {self.env.now}]: pax{self.id} got evtol{avail_evtol.id}/case_ii waiting queue{len(avail_evtol.future_queue)}')
                        while True:
                            if avail_evtol in self.from_.ramp :
                                yield avail_evtol.seats.get(1)
                                avail_evtol._pax_log.append(self)
                                self.waiting_time = self.env.now - self.call_time
                                return
                            else:
                                yield self.env.timeout(1)

            # First boarder
            elif (avail_evtol.dispatched is False) and (avail_evtol in self.from_.ramp) :#evtol Ramp in /idle but planX
                              
                etd, eta = operator.file_plan(avail_evtol, self.from_, self.to_,psu) #technically make_plan
                assert etd is not None, f"etd is None"
                self.etd=etd
                self.eta=eta
                
                # 5. PAX decision
                operator.PX_LOG=operator.PX_LOG.append({'PAX': self.id ,'From':self.from_.id,'To':self.to_.id,'Status':'decided','Time':self.env.now,'eVTOL':avail_evtol.id},ignore_index=True)
                if self.decision(etd) is True:
                    while True:
                        if avail_evtol in self.from_.ramp:
                            avail_evtol.eta=eta
                            avail_evtol.etd=etd
                            avail_evtol.dispatched = True
                            avail_evtol.to_=self.to_
                            print(f'[Time:{self.env.now}]: pax{self.id} got idle evtol{avail_evtol.id}/ firstboarder')
                            self.env.process(self.board(avail_evtol,etd,eta,operator,psu))
                            return
                        else:
                            yield self.env.timeout(1)
                    '''
                    psu_decision = psu.decision(avail_evtol,etd,eta,self.from_,self.to_)
                    # 6. PSU decision( Strategy Separation @ FATO Resource )
                    if psu_decision:    
                        try:
                            avail_evtol.eta=eta
                            avail_evtol.etd=etd 
                            avail_evtol.dispatched = True
                            avail_evtol.to_=self.to_
                            print(f'[Time:{self.env.now}]: pax{self.id} got idle evtol{avail_evtol.id}/ firstboarder')
                            self.env.process(self.board(avail_evtol,etd,eta,operator,psu))
                        except:
                            pass
                    else:
                        adjust_psu=0

                        while adjust_psu<10:
                            adjust_psu+=1
                            etd+=1
                            eta+=1
                            psu_decision = psu.decision(etd,eta,self.from_,self.to_)
                            if psu_decision:
                                try:    
                                    avail_evtol.eta=eta
                                    avail_evtol.etd=etd 
                                    avail_evtol.dispatched = True
                                    avail_evtol.to_=self.to_
                                    #self.env.process(self.board(avail_evtol,etd,eta,operator,psu))
                                    yield self.env.process(self.board(avail_evtol,etd,eta,operator,psu))
                                    break
                                except:
                                    pass
                        if psu.decision(etd,eta,self.from_,self.to_) == False:
                            self.from_._num_reneged+=1
                            operator.PX_LOG=operator.PX_LOG.append({'PAX': self.id ,'From':self.from_.id,'To':self.to_.id,'Status':'Reneged','Time':self.env.now,'eVTOL':avail_evtol.id},ignore_index=True)
                            return
                            '''
                else: #self.decision ==False
                    print(f"[Time: {self.env.now}]: pax{self.id} couldn't wait evtol {avail_evtol.id}..so renege (Unfeasible)")
                    self.from_._num_reneged+=1
                    return  
                    
            elif (avail_evtol.future_dispatched is False) and (avail_evtol in self.from_.inbound_evtols): # incoming eVTOL, not Dispatched

                
                etd, eta = operator.file_plan(avail_evtol, self.from_, self.to_,psu) #technically make_plan
                assert etd is not None, f"etd is None"
                self.etd=etd
                self.eta=eta
                # 5. PAX decision
                
                if self.decision(etd) is True:
                    while True:
                        if avail_evtol in self.from_.ramp:
                            avail_evtol.eta=eta
                            avail_evtol.etd=etd
                            avail_evtol.dispatched=True
                            avail_evtol.to_=self.to_

                            self.env.process(self.board(avail_evtol,etd,eta,operator,psu))
                            return
                        else:
                            yield self.env.timeout(1)
                        


                    '''    
                    psu_decision = psu.decision(avail_evtol,etd,eta,self.from_,self.to_)
                    # 6. PSU decision( Strategy Separation @ FATO Resource )
                    if psu_decision:    
                        try:
                            avail_evtol.future_eta=eta
                            avail_evtol.future_etd=etd 
                            avail_evtol.future_dispatched=True
                            avail_evtol.future_dest=self.to_
                            print(f'[Time: {self.env.now}]: pax{self.id} got incoming evtol{avail_evtol.id}/ firstboarder')
                            while True:
                                if avail_evtol in self.from_.ramp:
                                    self.env.process(self.board(avail_evtol,etd,eta,operator,psu))
                                    return
                                else:
                                    yield self.env.timeout(1)

                        except:
                            pass
                    else:
                        adjust_psu=0

                        while adjust_psu<10:
                            adjust_psu+=1
                            etd+=1
                            eta+=1
                            psu_decision = psu.decision(etd,eta,self.from_,self.to_)
                            if psu_decision:
                                try:    
                                    avail_evtol.future_eta=eta
                                    avail_evtol.future_etd=etd 
                                    avail_evtol.future_dispatched = True
                                    avail_evtol.future_dest=self.to_
                                    print(f'[Time: {self.env.now}]: pax{self.id} got incoming evtol{avail_evtol.id}/ firstboarder')
                                    yield self.env.process(self.board(avail_evtol,etd,eta,operator,psu))
                                    break
                                except:
                                    pass
                                
                
                if psu.decision(etd,eta,self.from_,self.to_) == False:
                        self.from_._num_reneged+=1
                        operator.PX_LOG=operator.PX_LOG.append({'PAX': self.id ,'From':self.from_.id,'To':self.to_.id,'Status':'Reneged','Time':self.env.now,'eVTOL':avail_evtol.id},ignore_index=True)
                '''    
                else: #self.decision ==False
                    print(f'[Time: {self.env.now}]: {self.id} couldn"t wait {avail_evtol.id}..so renege')
                    self.from_._num_reneged+=1
                    return 
            else:
            #elif (avail_evtol.future_dispatched is False) and (avail_evtol in self.from_.inbound_evtols): # incoming eVTOL, not Dispatched
                print(f'Unfeasible Case: evtol{avail_evtol.id} from_{avail_evtol.from_.id} to_{avail_evtol.to_.id} & (A)={avail_evtol.dispatched} (B)={avail_evtol in self.from_.ramp} (C)={avail_evtol.future_dispatched} (D)={avail_evtol in self.from_.inbound_evtols} self.from={self.from_.id} selt.to={self.to_.id}')   
                return        
        else:
            print(f'[Time: {self.env.now}]: pax{self.id} could get {avail_evtol}.. within {operator.find_limit} mins so he/she reneges (NO EVTOL)')
            operator.PX_LOG=operator.PX_LOG.append({'PAX': self.id ,'From':self.from_.id,'To':self.to_.id,'Status':'Reneged','Time':self.env.now,'eVTOL':None},ignore_index=True)
            self.from_._num_reneged+=1
            return
           
    def decision(self, etd):
        global PX_LOG
        threshold = self.threshold # acceptable waiting time for the pax

        #===================================================
        # self.env.now is the time when the passenger
        # is informed that the EVTOl is available.
        # pax_waiting_time = self.env.now - self.call_time
        # required_waiting_time = etd - self.env.now
        # total_waiting_time = pax_waiting_time + required_waiting_time
        expected_total_waiting_time = etd - self.call_time
        #print(f'DEB for PAX DECISION : {self} is deciding w/{expected_total_waiting_time},{self.env.now} ')

        if expected_total_waiting_time <= threshold: # accept
            # If the evtol is not in current vertiport's ramp
            # but it is coming from another vertiport.
            # Then assign future_etd, future_eta.
            return True    
        else:
            #self.from_.count_renege()
            return False

    
    def board(self, avail_evtol, etd, eta,operator,psu, is_case2=False):
        global PX_LOG
        # Case 1 : Idle, Case 2 : onBoarding, Case 3 : waiting.
        
        is_in_vertiport = True if avail_evtol in self.from_.ramp else False
        is_boardable_state_1 = (avail_evtol.state == 'idle')  
        is_boardable_state_2 = (avail_evtol.state == 'onBoarding')
        is_boardable_state_3 = (avail_evtol.seats.level > 0) 
        case_1 = is_in_vertiport and is_boardable_state_1
        case_2 = is_in_vertiport and is_boardable_state_2 and is_boardable_state_3
        boardable_case = case_1 or case_2
 
        #print(f"pax id: {self.id} vp id: {self.from_.id} is_boardable: ")
        if case_1 ==True:

            yield avail_evtol.seats.get(1) # [4/4]
            avail_evtol._pax_log.append(self)
            self.waiting_time = self.env.now - self.call_time
            avail_evtol.first_boarder=self        
            self.env.process(avail_evtol.update_by_boarding(self.from_,self.to_, operator,psu))
            yield avail_evtol.door_close_event # when pax boarding ends and starts to move
                         
            yield avail_evtol.take_off_event # when pax take_off

            yield avail_evtol.door_open_event # when pax get off
                
            return

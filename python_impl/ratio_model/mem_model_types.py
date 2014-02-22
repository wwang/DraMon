# This is a python module that contains the definitions of all the data 
# structures used by my memory bandwidth prediction model.
#
# Author: Wei Wang (wwang@virginia.edu) University of Virginia
#
#

# class for access distances
class chnl_reuse_dist_info:
    def __init__(self):
        self.acc_dist = 0     # access distance
        self.prob = 0.0       # probability of this access distance
        self.hit_prob = 0.0   # probability of hits
        self.miss_prob = 0.0  # probability of misses
        self.conf_prob = 0.0  # probability of conflicts
        self.acc_seqs = []    # A list of all possible accesses sequence
                              # for this reuse distance. Each element just
                              # represents the possible sequence of one
                              # thread. Each element is an object of class
                              # accs_one_thread.

# class for thread informations
class thread_info:
    def __init__(self):
        self.chnl_prob = 0.0   # probability of accessing targeted channel
        self.row_prob = 0.0    # probability of accessing the same row buffer 
                               # used by another thread
        self.bank_prob = 0.0   # probability of accessing a same bank that is 
                               # used by another thread
        self.chnl_reuse_dists = []    # array of access distances
        self.reorder_time = 0.0  # that maximum time between two reorder-able 
                                 # accesses, in nanoseconds
        self.autoclose_time = 0.0 # after this period of this a row buffer is
                                  # is automatically closed if not accessed, 
                                  # in nanoseconds
        self.est_serv_time = 0.0  # estimated service time of these memory
                                  # accesses used for reordering and 
                                  # auto-closing, in nanoseconds
        self.half_reorder = True  # Only consider half of the reorders to be
                                  # hit, the rest remains conflict

# This class is the about the probability of having another access to the 
# targeted channel after n consecutive accesses to this channel
class consecutive_acc_probs:
    def __init__(self):
        self.acc_prob = [] 
                      # for p = acc_prob[n], p is the probability of having an 
                      # access to the targeted channel directly after n 
                      # consecutive accesses to this channel
                      # 1-p is the probability of having an access to the other
                      # channels

# This class is the about the probability of having another access to the non-
# targeted channels after n consecutive accesses to channels other than the 
# targeted channel
class consecutive_noacc_probs:
    def __init__(self):
        self.noacc_prob = [] 
                        # for p = noacc_prob[n], p is the probability of having
                        # an access to the non-targeted channels directly after
                        # n consecutive accesses to other channels
                        # 1-p is the probability of having an access to the 
                        # targeted channels


# This class stores that status of a particular memory access
class access_status:
    def __init__(self):
        self.same_chnl = False # whether this access is to the target channel
        self.same_bank = False # whether this access is to the target bank     
        self.same_row = False  # whether this access is to the target row
        self.prob = 0.0        # the probability of having this access

# This class stores that states of the accesses of a particular access sequence
class acc_seq_case:
    def __init__(self):
        self.accesses = []  # each element is an access_status object
        self.total_accs = 0 # total number of accesses in this case that access
                            # target channel
        self.total_sr = 0   # total number of accesses to the same row
        self.total_sb = 0   # total number of accesses to the same bank but 
                            # different row
                            # total number of accesses to the same channel but 
                            # different bank is total_accs - total_sr - total_sb
        self.prob = 0.0     # probability of this case

# This class groups all accesses of one middle thread
class accs_one_thread:
    def __init__(self):
        self.accesses = []   # each element is an access_status object
        self.prob = 0.0      # the probability of this access sequence
        self.total_accs = 0  # total number of accesses in this sequence that 
                             # access target channel
        self.cur_acc = 0     # a pointer for tracking the next memory access
                             # to be processed
        self.cases = []      # this member is for linked (not deep copy) version
                             # of my memory model implementation.
                             # each case is an access_case object. Sum of all
                             # elements' probability should be 1
    

# This class fully lists all possible memory access cases. No simplification is
# made.
class full_interference_pattern:
    def __init__(self):
        self.chnl_reuse_dist = 0      # channel resue distance of this sequence
        self.prob = 0.0        # the probability of this sequence occurring
        self.hmc = -1          # whether this is a hit (0), miss (1) or 
                               # conflict (2) or undetermined (-1)
        self.thread_cnt = 0    # number of threads
        self.threads = []      # each element is an accs_one_thread object
        self.total_accs = 0    # total number of accesses in the middle that
                               # access target channel
        self.cur_thread = 0    # a pointer for tracking the thread, of which the
                               # next memory access to be processed
    
# This class holds the hit miss conflict ratios
class hmc_ratios:
    def __init__(self):
        self.hit = 0.0
        self.miss = 0.0
        self.conflict = 0.0

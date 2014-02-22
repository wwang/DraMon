# This file contains functions for determining the hit/miss/conflict ratio of an
# interference pattern. Used as part of the memory prediction model
#
# There are several versions for this step:
# 1. V1 Full version: Every access is evaluated, and their relative order is 
#    considered
# 2. V2 Count version: Only cares about the total number of accesses, and
#    the total number of same row, same bank accesses. The HMC state is 
#    determined by the position of the same row and same bank accesses
# 3. V3 Existence version: Only cares about whether there exists a same row or 
#    same bank accesses; Reordering and auto-closing are only considered for 
#    the previous access from the target thread
# Author: Wei Wang (wwang@virginia.edu), University of Virginia
#

import itertools
import Queue
import copy
import math

from mem_model_types import *
import acc_gen
import inter_pat_gen

# This function process a generated full interference pattern to get the hit,
# miss, or conflict state for this pattern. Row buffer auto-closing and 
# accesses reordering are consider
# Inputs:
#       full_inter_pat: a full interference pattern
#       thr_info: see thread_info class for information
# Return:
#       an object of class hmc_ratios
def gen_hmc_full_inter_pat(inter_pat, thr_info):

    hmc = hmc_ratios()
    prob = inter_pat.prob

    # find the corresponding channel reuse distance information
    found = False
    for chnl_dist in thr_info.chnl_reuse_dists:
        if chnl_dist.acc_dist == inter_pat.chnl_reuse_dist:
            found = True
            break
    if not found:
        print "Weired: reuse distance not found"
        exit(3)
    # here I treat the previous access from the target thread as the 
    # same as any middle threads. Now lets generate the cases and 
    # probabilities for the three new cases
    # previous access is to the same row
    org_acc_type = 1 # same row, a hit originally
    inter_pat.prob = prob * chnl_dist.hit_prob;
    if inter_pat.prob != 0:
        hmc1 = gen_hmc_full_inter_pat_w_org_acc(inter_pat, thr_info,
                                                        org_acc_type)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to the same bank but different row
    org_acc_type = 2 # same row different bank, a conflict originally
    inter_pat.prob = prob * chnl_dist.conf_prob;
    if inter_pat.prob != 0:
        hmc1 = gen_hmc_full_inter_pat_w_org_acc(inter_pat, thr_info,
                                                org_acc_type)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to a different bank
    org_acc_type = 3 # different bank, a miss originally
    inter_pat.prob = prob * chnl_dist.miss_prob;
    if inter_pat.prob != 0:
        hmc1 = gen_hmc_full_inter_pat_w_org_acc(inter_pat, thr_info,
                                                org_acc_type)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict

    return hmc

    
# Basically same function as gen_hmc_full_inter_pat. The only difference there
# is that the previous access (org_acc) from the target thread is also
# considered.
#
# Inputs: also see comments to function gen_hmc_full_inter_pat
#       org_acc_type: whether the org_acc is the 1) same row 2) same bank 
#                     different row 3) different bank
# Return:
#       an object of class hmc_ratios
def gen_hmc_full_inter_pat_w_org_acc(inter_pat, thr_info, org_acc_type):

    #output = inter_pat_gen.log_full_inter_pat(inter_pat)
    #print "Processing: org_type", org_acc_type, ",",  output

    # search from the last access in this sequence, look for two accesses:
    # 1. last access "a" that access the same bank (could be the same row)
    # 2. last access "b" that access that same row
    # Here I assume for any access slot, thread 1 is always the first access
    # thread 2 is the next, etc. Just realized this is probably also a 
    # simplification, should work anyway
    last_same_bank = -1
    last_same_row = -1
    
    acc_checked = 0
    for acc_idx in range(inter_pat.chnl_reuse_dist - 1, -1, -1):
        for thr_idx in range(inter_pat.thread_cnt - 2, -1, -1):
            if not inter_pat.threads[thr_idx].accesses[acc_idx].same_chnl:
                # only count for accesses in this channel
                continue
            acc_checked += 1
            if (( last_same_bank == -1) and
                inter_pat.threads[thr_idx].accesses[acc_idx].same_bank ):
                last_same_bank = acc_checked
            if (( last_same_row == -1) and
                inter_pat.threads[thr_idx].accesses[acc_idx].same_row ):
                last_same_row = acc_checked
            # should have two breaks here, but I am just too lazy...

    # check the previous access of the target thread if we didn't find
    # the accesses we want
    if (( last_same_bank == -1) and (org_acc_type == 2)):
        last_same_bank = acc_checked + 1
    if (( last_same_row == -1) and (org_acc_type == 1)):
        last_same_row = acc_checked + 1
    
    acc = -1
    reordered = False
    # there are five cases to check, see my notes on Feb 26 2013
    # case 1
    if ((last_same_bank != -1) and (last_same_row != -1) and 
        (last_same_bank == last_same_row)):
        case = 1 #defer process
    # case 2
    if ((last_same_bank != -1) and (last_same_row != -1) and 
        (last_same_bank != last_same_row)):
        if (last_same_row < last_same_bank): # last access is same row
            case = 1 # similar to the process of case 1
        else: # last access is same bank
            if (last_same_row * thr_info.est_serv_time <= 
                thr_info.reorder_time):
                # same row access and the target access are reorder-able
                acc = 1 # hit
                reordered = True
                case = 2
            else:
                case = 3  # similar to the process of case 3
    # case 3
    if ((last_same_bank != -1) and (last_same_row == -1)):
        case = 3 # defer process
    # case 4
    if ((last_same_bank == -1) and (last_same_row != -1)):
        case = 1 # similar to the process of case 1
    # case 5
    if ((last_same_bank == -1) and (last_same_row == -1)):
        case = 5
        acc = 2 # miss
    
    if case == 1: # process for case 1
        if (last_same_row * thr_info.est_serv_time > 
            thr_info.autoclose_time): #auto-closed
            if (last_same_row * thr_info.est_serv_time <= 
                thr_info.reorder_time): #reordered
                reordered = True
                acc = 1 # hit
            else:
                acc = 2 # miss
        else: #not auto-closed
            acc = 1 # hit
    elif case == 3: # process for case 3
        if (last_same_row * thr_info.est_serv_time > 
            thr_info.autoclose_time): #auto-closed
            acc = 2 # miss
        else:
            acc = 3 # conflict

    if acc == -1:
        print "Error: access type not set for case:", case
        exit(4)

    hmc = hmc_ratios()
    if acc == 1: # hit
        hmc.hit = inter_pat.prob
    elif acc == 2: # miss
        hmc.miss = inter_pat.prob
    elif acc == 3: # conflict
        hmc.conflict = inter_pat.prob

    # if half reordered 
    if thr_info.half_reorder and reordered:
        hmc.conflict += hmc.hit / 2
        hmc.hit /= 2

    #print "Processed result:", acc, inter_pat.prob

    return hmc

# Get the hit/miss/conflict ratios for all interference pattern groups.
# Inputs:
#      inter_pat_groups: Essentially a two-D array for interference patterns.
#                        Each group has the interference pattern for one 
#                        channel reuse distance.
#      thr_info: thread_info object
#      debug: debug output control
# Return:
#      hmc_ratios object
def gen_hmc_v2_all_inter_pat_group(inter_pat_groups, thr_info, debug):
    hmc = hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0

    for inter_pats in inter_pat_groups:
        for inter_pat in inter_pats:
            # process this interference pattern
            cases = gen_cases_inter_pat(inter_pat, thr_info, debug)
            # generate HMC ratio for each case
            for case in cases:
                hmc1 = gen_hmc_v2_inter_pat(inter_pat, thr_info, case, debug)
                hmc.hit += hmc1.hit
                hmc.miss += hmc1.miss
                hmc.conflict += hmc1.conflict
        print "Group hit/miss/conflict:", hmc.hit, hmc.miss, hmc.conflict

    # sanity check
    sum_prob = hmc.hit + hmc.miss + hmc.conflict
    if sum_prob != 1.0:
        print "HMC ratio sum is not 1.0 but", sum_prob
    
    return hmc

# Generate all possible access state cases for this interference patterns.
# For each interference pattern, there are several threads in it. For each 
# thread, it has one corresponding access sequence. For each access sequence, it
# has several access state cases. Therefore, for an interference pattern, it has
# several access states cases of (thread1_cases X thread2_cases X ... ).
# Inputs:
#       inter_pat: the interference pattern to process
#       thr_info: thread_info object
#       debug: debug output control
# Return:
#       a list of of possible cases. Each case is an array too. The "i"th 
#       element is the case of the "i"th thread. The value of this element is 
#       case number of this thread's access sequence.
def gen_cases_inter_pat(inter_pat, thr_info, debug):
    # count the total number of cases for each thread's access sequence 
    counts = [] 
    for thr in inter_pat.threads:
        count = len(thr.cases)
        if count == 0: # sanity check
            print "Access sequence has 0 access state cases."
            exit(7)
        counts.append(range(count))
        
    cases = []
    # generate all cases, basically a Cartesian product
    for case in itertools.product(*counts):
        cases.append(list(case))

    return cases

# Generate the hit/miss/conflict ratio for one case of interference pattern
# Inputs:
#       inter_pat: the interference pattern to process
#       thr_info: thread_info object
#       debug: debug output control
#       case: a list of of possible cases. Each case is an array too. The "i"th 
#             element is the case of the "i"th thread. The value of this 
#             element is case number of this thread's access sequence.
# Output:
#       a hmc_ratios object
def gen_hmc_v2_inter_pat(inter_pat, thr_info, case, debug):
    hmc = hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0
    # count how many access, same row access and same bank access
    total_accs = 0
    total_sr = 0
    total_sb = 0
    prob = inter_pat.prob
    for idx,val in enumerate(case):
        total_accs += inter_pat.threads[idx].cases[val].total_accs
        total_sr += inter_pat.threads[idx].cases[val].total_sr
        total_sb += inter_pat.threads[idx].cases[val].total_sb
        prob *= inter_pat.threads[idx].cases[val].prob
        
    # generate the hit/miss/ratio for this inter_pat
        # find the corresponding channel reuse distance information
    found = False
    for chnl_dist in thr_info.chnl_reuse_dists:
        if chnl_dist.acc_dist == inter_pat.chnl_reuse_dist:
            found = True
            break
    if not found:
        print "Weired: reuse distance not found"
        exit(3)
    # here I treat the previous access from the target thread as the 
    # same as any middle threads. Now lets generate the cases and 
    # probabilities for the three new cases
    # previous access is to the same row
    org_acc_type = 1 # same row, a hit originally
    base_prob = prob * chnl_dist.hit_prob;
    if base_prob != 0:
        hmc1 = gen_hmc_v2_by_counts(total_accs,total_sr,total_sb, thr_info,
                                    org_acc_type, base_prob, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to the same bank but different row
    org_acc_type = 2 # same row different bank, a conflict originally
    base_prob = prob * chnl_dist.conf_prob;
    if base_prob != 0:
        hmc1 = gen_hmc_v2_by_counts(total_accs,total_sr,total_sb, thr_info,
                                    org_acc_type, base_prob, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to a different bank
    org_acc_type = 3 # different bank, a miss originally
    base_prob = prob * chnl_dist.miss_prob;
    if base_prob != 0:
        hmc1 = gen_hmc_v2_by_counts(total_accs,total_sr,total_sb, thr_info,
                                    org_acc_type, base_prob, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict

    return hmc

    
# Determine the HMC ratios bases on the number of accesses. V2 in the comments
# at the beginning of this file. Also check notes on 2013 Mar 05
# Inputs:
#       total_accs: Total number of accesses that hit target channel
#       total_sr: total number of accesses that hit the target row
#       total_sb: total number of access that hit the target bank but not
#                 target row
#       thr_info: thread_info
#       orig_type: original HMC type when no contentino: 1 hit, 3 miss
#                  2 conflict  
#       base_prob: basic probability of this case
# Output:
#       hmc_ratios object
def gen_hmc_v2_by_counts(total_accs, total_sr, total_sb, thr_info, orig_type,
                         base_prob, debug):
    hmc = hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0

    # if original access is a hit, and it is reorder-able, than this is also
    # a hit
    #if ((orig_type == 1) and (total_accs * thr_info.est_serv_time <=
    #                          thr_info.reorder_time)):
    #    if thr_info.half_reorder:
    #        hmc.hit = base_prob/2
    #        hmc.conflict = base_prob/2
    #    else:
    #        hmc.hit = base_prob
    #    return hmc
    auto_close_frame = int(math.floor(thr_info.autoclose_time/
                                  thr_info.est_serv_time))
    reorder_frame = int(math.floor(thr_info.reorder_time/
                                   thr_info.est_serv_time))
    # scenario 1: both same row an same bank (different row) accesses exist
    if (total_sr != 0)  and (total_sb != 0):
        prob_1 = base_prob
        # scenario 1-1: same row happens after same bank
        prob_1_1 = prob_1 * get_prob_m_after_n(total_sr, total_sb, 
                                               total_accs)
        # scenario 1-1-1-1: row buffer auto-closed after the last same row,
        # but last same row is reorder-able. This is a hit.
        # That is (auto_close_frame+1) <= m <= (reorder_frame)
        prob_1_1_1_1 = prob_1_1 * get_prob_m_between_d1_d2(total_sr, total_sb, 
                                                           total_accs, 
                                                           auto_close_frame+1, 
                                                           reorder_frame)
        if thr_info.half_reorder:
            hmc.hit += prob_1_1_1_1/2
            hmc.conflict += prob_1_1_1_1/2
        else:
            hmc.hit += prob_1_1_1_1
        # scenario 1-1-1-2: row buffer auto_closed after the last same row, and
        # last same row is not reorder-able. This is miss.
        # This is m > max(auto_close_frame, reorder_frame)
        if auto_close_frame > reorder_frame:
            d = auto_close_frame
        else:
            d = reorder_frame
        prob_1_1_1_2 = prob_1_1 * (1 - get_prob_m_within_d(total_sr, total_sb, 
                                                      total_accs, d))
        hmc.miss = prob_1_1_1_2
        # scenario 1-1-2: row buffer not auto_closed, hit
        prob_1_1_2 = prob_1_1 * get_prob_m_within_d(total_sr, total_sb, 
                                                  total_accs, auto_close_frame)
        hmc.hit += prob_1_1_2

        # scenario 1-2: last same banks after last same row
        prob_1_2 = prob_1 - prob_1_1
        # scenario 1-2-1: last same row reorder-able, a hit        
        prob_1_2_1 = prob_1_2 * get_prob_m_within_d(total_sr, total_sb, 
                                                    total_accs, reorder_frame)
        if thr_info.half_reorder:
            hmc.hit += prob_1_2_1/2
            hmc.conflict += prob_1_2_1/2
        else:
            hmc.hit += prob_1_2_1
        # scenario 1-2-2: last same row not reorder-able
        prob_1_2_2 = prob_1_2 - prob_1_2_1
        # scenario 1-2-2-1: after last same bank, row buffer auto-closed, a miss
        prob_1_2_2_1 = prob_1_2_2 * (1- get_prob_m_within_d(total_sb, total_sr,
                                                        total_accs,
                                                        auto_close_frame))
        hmc.miss += prob_1_2_2_1
        # scenario 1-2-2-2: after last same bank, row buffer not auto-closed
        # a conflict
        prob_1_2_2_2 = prob_1_2_2 - prob_1_2_2_1
        hmc.conflict += prob_1_2_2_2
    elif (total_sr == 0) and (total_sb != 0): 
        # scenario 2: only same bank accesses exists
        prob_2 = base_prob
        # scenario 2-1: after last same bank, row buffer auto-closed, a miss
        prob_2_1 = prob_2 * (1- get_prob_m_within_d(total_sb, total_sr,
                                                    total_accs,
                                                    auto_close_frame))
        hmc.miss += prob_2_1
        # scenario 2-2: after last same bank, row buffer not auto-close, 
        # a conflict
        prob_2_2 = prob_2  - prob_2_1
        hmc.conflict += prob_2_2
    elif (total_sr != 0 ) and (total_sb == 0):
        # scenario 3:
        prob_3 = base_prob
        # scenario 3-1-1: row buffer auto-closed after the last same row,
        # but last same row is reorder-able. This is a hit.
        # That is (auto_close_frame+1) <= m <= (reorder_frame)
        prob_3_1_1= prob_3 * get_prob_m_between_d1_d2(total_sr, total_sb, 
                                                      total_accs, 
                                                      auto_close_frame+1, 
                                                      reorder_frame)
        if thr_info.half_reorder:
            hmc.hit += prob_3_1_1/2
            hmc.conflict += prob_3_1_1/2
        else:
            hmc.hit += prob_3_1_1
        # scenario 3-1-2: row buffer auto_closed after the last same row, and
        # last same row is not reorder-able. This is miss.
        # This is m > max(auto_close_frame, reorder_frame)
        if auto_close_frame > reorder_frame:
            d = auto_close_frame
        else:
            d = reorder_frame
        prob_3_1_2 = prob_3 * (1 - get_prob_m_within_d(total_sr, total_sb, 
                                                      total_accs, d))
        hmc.miss = prob_3_1_2
        # scenario 3-2: row buffer not auto_closed, hit
        prob_3_2 = prob_3 * get_prob_m_within_d(total_sr, total_sb, total_accs,
                                                auto_close_frame)
        hmc.hit += prob_3_2
    elif (total_sr == 0) and (total_sb == 0):
        # scenario 4: not same row and same bank access
        prob_4 = base_prob
        if orig_type == 1: # originally a hit
            if (total_accs * thr_info.est_serv_time) > thr_info.autoclose_time:
                # auto-closed, miss
                hmc.miss += prob_4
            else: # not auto-closed, hit
                hmc.hit += prob_4
        elif orig_type == 2: # originally a conflict
            if (total_accs * thr_info.est_serv_time) > thr_info.autoclose_time:
                # auto-closed, miss
                hmc.miss += prob_4
            else: # not auto-closed, hit
                hmc.conflict += prob_4
        elif orig_type == 3: # originally a miss
            hmc.miss += prob_4

    else:
        print "Should never hit here"
        exit(8)

    # check the conflicts, see if reordering can help
    if ((orig_type == 1) and (total_accs * thr_info.est_serv_time <=
                              thr_info.reorder_time)):
        if thr_info.half_reorder:
            hmc.hit += hmc.conflict/2
            hmc.conflict /= 2
        else:
            hmc.hit += hmc.conflict

    # sanity check
    # sum_prob = hmc.hit + hmc.miss + hmc.conflict
    #if sum_prob != base_prob:
    #    print "Error, sum should be", base_prob, "but is", sum_prob
    #    exit(9)

    return hmc
    
    
# For a series of objects with length "l". There are "m" type A objects, and "n"
# type B objects. This function gives the probability of all B objects are
# before the last A object.
def get_prob_m_after_n(m, n, l):
    total_a_b = (acc_gen.cal_combination(l,m) * 
             acc_gen.cal_combination(l-m,n))

    total_a_before_b = 0
    for i in range(m+n, l+1, 1): #[m+n, l]
        total_a_before_b += (acc_gen.cal_combination(i-1,m-1) * 
                             acc_gen.cal_combination(i-1-(m-1),n))
    
    prob = float(total_a_before_b)/float(total_a_b)
    return prob

# For a series of objects with length "l". There are "m" type A objects, and "n"
# type B objects. This function gives the probability of the last A object is 
# with in "d" slots from the end.
def get_prob_m_within_d(m, n, l, d):
    if d >= l: # always true
        return 1.0

    # total cases of putting "m" "a"s in "l" slots
    total_a = acc_gen.cal_combination(l,m) 

    total_last_a_in_d = 0
    for i in range(l-1, l-d-1, -1): #[l-1, l-d]
        if (i >= (m-1)):
            total_last_a_in_d += acc_gen.cal_combination(i, m-1)
        
    prob = float(total_last_a_in_d) / float(total_a)
    return prob

# For a series of objects with length "l". There are "m" type A objects, and "n"
# type B objects. This function gives the probability that last A access is 
# in the [d2-d1] slots from the end of this sequence
def get_prob_m_between_d1_d2(m, n, l, d1, d2):
    if d1 > l:
        d1 = l
    if d2 > l:
        d2 = l

    if d2 <= d1: # not possible
        return 0.0
    d = d2 - d1
    x = l - d2
    total_last_a_in_middle = 0
    for i in range(x+d-1, x-1, -1): # [x+d-1, x+d-d]
        total_last_a_in_middle += acc_gen.cal_combination(i, m-1)
    # total cases of putting "m" "a"s in "l" slots
    total_a = acc_gen.cal_combination(l,m) 
    prob = float(total_last_a_in_middle)/float(total_a)
    return prob
    
    
# Get the hit/miss/conflict ratios for all interference pattern groups. 
# Version V3. 
# Inputs:
#      inter_pat_groups: Essentially a two-D array for interference patterns.
#                        Each group has the interference pattern for one 
#                        channel reuse distance.
#      thr_info: thread_info object
#      debug: debug output control
# Return:
#      hmc_ratios object
def gen_hmc_v3_all_inter_pat_group(inter_pat_groups, thr_info, debug):
    hmc = hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0

    for inter_pats in inter_pat_groups:
        for inter_pat in inter_pats:
            # process this interference pattern
            if debug:
                print "Processing a new interference pattern :"
                print inter_pat_gen.log_full_inter_pat(inter_pat)

            cases = gen_cases_inter_pat(inter_pat, thr_info, debug)
            # generate HMC ratio for each case
            for case in cases:
                if debug:
                    print "Case:", log_hmc_case(inter_pat, case)
                hmc1 = gen_hmc_v3_inter_pat(inter_pat, thr_info, case, debug)
                hmc.hit += hmc1.hit
                hmc.miss += hmc1.miss
                hmc.conflict += hmc1.conflict
                if debug:
                    print "Case finished",
                    print ", hit:", hmc1.hit,
                    print ", miss:", hmc1.miss, ", conf:", hmc1.conflict

        print "Group hit/miss/conflict:", hmc.hit, hmc.miss, hmc.conflict

    # sanity check
    sum_prob = hmc.hit + hmc.miss + hmc.conflict
    if sum_prob != 1.0:
        print "HMC ratio sum is not 1.0 but", sum_prob
    
    return hmc

# Generate the hit/miss/conflict ratio for one case of interference pattern.
# Version V3.
# Inputs:
#       inter_pat: the interference pattern to process
#       thr_info: thread_info object
#       debug: debug output control
#       case: a list of of possible cases. Each case is an array too. The "i"th 
#             element is the case of the "i"th thread. The value of this 
#             element is case number of this thread's access sequence.
# Output:
#       a hmc_ratios object
def gen_hmc_v3_inter_pat(inter_pat, thr_info, case, debug):
    hmc = hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0
    # count how many access, same row access and same bank access
    total_accs = 0
    total_sr = 0
    total_sb = 0
    prob = inter_pat.prob
    for idx,val in enumerate(case):
        total_accs += inter_pat.threads[idx].cases[val].total_accs
        total_sr += inter_pat.threads[idx].cases[val].total_sr
        total_sb += inter_pat.threads[idx].cases[val].total_sb
        prob *= inter_pat.threads[idx].cases[val].prob

    if debug:
        print "A new V3 case: prob:", prob, ", total_accs", total_accs,
        print ", total_sr", total_sr, ", total_sb", total_sb
    # generate the hit/miss/ratio for this inter_pat
        # find the corresponding channel reuse distance information
    found = False
    for chnl_dist in thr_info.chnl_reuse_dists:
        if chnl_dist.acc_dist == inter_pat.chnl_reuse_dist:
            found = True
            break
    if not found:
        print "Weired: reuse distance not found"
        exit(3)
    # here I treat the previous access from the target thread as the 
    # same as any middle threads. Now lets generate the cases and 
    # probabilities for the three new cases
    # previous access is to the same row
    org_acc_type = 1 # same row, a hit originally
    base_prob = prob * chnl_dist.hit_prob;
    if base_prob != 0:
        hmc1 = gen_hmc_v3_by_existence(total_accs,total_sr,total_sb, thr_info,
                                       org_acc_type, base_prob, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to the same bank but different row
    org_acc_type = 2 # same row different bank, a conflict originally
    base_prob = prob * chnl_dist.conf_prob;
    if base_prob != 0:
        hmc1 = gen_hmc_v3_by_existence(total_accs,total_sr,total_sb, thr_info,
                                       org_acc_type, base_prob, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to a different bank
    org_acc_type = 3 # different bank, a miss originally
    base_prob = prob * chnl_dist.miss_prob;
    if base_prob != 0:
        hmc1 = gen_hmc_v3_by_existence(total_accs,total_sr,total_sb, thr_info,
                                       org_acc_type, base_prob, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict

    return hmc

# Determine the HMC ratios bases on the number of accesses. Check V3 in the 
# comments at the beginning of this file. Check notes on Mar 10 2013
# Inputs:
#       total_accs: Total number of accesses that hit target channel
#       total_sr: total number of accesses that hit the target row
#       total_sb: total number of access that hit the target bank but not
#                 target row
#       thr_info: thread_info
#       orig_type: original HMC type when no contentino: 1 hit, 3 miss
#                  2 conflict  
#       base_prob: basic probability of this case
# Output:
#       hmc_ratios object
def gen_hmc_v3_by_existence(total_accs, total_sr, total_sb, thr_info, orig_type,
                            base_prob, debug):
    hmc = hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0

    auto_close_frame = int(math.floor(thr_info.autoclose_time/
                                  thr_info.est_serv_time))
    reorder_frame = int(math.floor(thr_info.reorder_time/
                                   thr_info.est_serv_time))
    
    if orig_type == 1:
        # scenario 1: original is a hit
        if (total_sr == 0) and (total_sb == 0):
            # scenario 1-1: some-row access and some-bank access NOT exist
            if ((total_accs * thr_info.est_serv_time) > 
                thr_info.autoclose_time):
                # scenario 1-1-1: row buffer auto-closed
                if (total_accs * thr_info.est_serv_time <= 
                    thr_info.reorder_time):
                    # scenario 1-1-1-1: reorder-able, hit
                    hmc.hit = base_prob
                else:
                    # scenario 1-1-1-2: non-reorder-able, miss
                    hmc.miss = base_prob
            else:
                # scenario 1-1-2: row buffer not auto-closed
                hmc.hit = base_prob
        elif (total_sr != 0) and (total_sb == 0):
            # scenario 1-2: only same-row accesses exist, hit
            hmc.hit = base_prob
        elif (total_sr == 0) and (total_sb != 0):
            # scenario 1-3: only same-bank accesses exist
            if (total_accs * thr_info.est_serv_time <= 
                thr_info.reorder_time):
                # scenario 1-3-1: reorder-able, hit
                if thr_info.half_reorder:
                    hmc.hit = base_prob/2
                    hmc.conflict = base_prob/2
                else:
                    hmc.hit = base_prob
            else:
                # scenario 1-3-2: non-reorder-able
                # given the fact taht this may be miss if autoclosed
                # half miss, half conflict
                hmc.conflict = base_prob/2
                hmc.miss = base_prob/2
        elif (total_sr != 0) and (total_sb != 0):
            # scenario 1-4: both same-row accesses and same-bank accesses exist
            if (total_accs * thr_info.est_serv_time <= 
                thr_info.reorder_time):
                # scenario 1-4-1: reorder-able, hit
                if thr_info.half_reorder:
                    hmc.hit = base_prob/2
                    hmc.conflict = base_prob/2
                else:
                    hmc.hit = base_prob
            else:
                # scenario 1-4-2: non-reorder-able, half hit, half conflict
                hmc.hit = base_prob/2
                hmc.conflict = base_prob/2
    elif (orig_type == 3):
        # scenario 2: original access is a miss
        if (total_sr == 0) and (total_sb == 0):
            # scenario 2-1: neither same-row accesses nor same-bank accesses 
            # exist, miss
            hmc.miss = base_prob
        elif (total_sr != 0) and (total_sb == 0):
            # scenario 2-2: only same-row accesses exist, hit
            hmc.hit = base_prob
        elif (total_sr == 0) and (total_sb != 0):
            # scenario 2-3: only same-bank accesses exist, conflict
            if thr_info.half_reorder:
               hmc.conflict = base_prob/2
               hmc.miss = base_prob/2
            else:
                hmc.conflict = base_prob
        elif (total_sr != 0) and (total_sb != 0):
            # scenario 2-4: both same-row accesses and same-bank accesses exist
            # half hit, half conflict
            hmc.hit = base_prob/2
            hmc.conflict = base_prob/2            
    elif (orig_type == 2):
        # scenario 3: original access is a conflict
        if (total_sr == 0) and (total_sb == 0):
            # scenario 3-1: neither same-row accesses nor same-bank accesses 
            # exist
            if (total_accs * thr_info.est_serv_time > 
                thr_info.autoclose_time):
                # scenario 3-1-1: row buffer auto-closed, miss
                hmc.miss = base_prob
            else:
                # scenario 3-1-2: row buffer not auto-close, conflict
                hmc.conflict = base_prob
        elif (total_sr != 0) and (total_sb == 0):
            # scenario 3-2: only same-row accesses exist, hit
            hmc.hit = base_prob
        elif (total_sr == 0) and (total_sb != 0):
            # scenario 3-3: only same-bank accesses exist, conflict
            if thr_info.half_reorder:
                hmc.conflict = base_prob/2
                hmc.miss = base_prob/2
            else:
                hmc.conflict = base_prob
        elif (total_sr != 0) and (total_sb != 0):
            # scenario 3-4: both same-row accesses and same-bank accesses exist
            # half hit, half conflict
            hmc.hit = base_prob/2
            hmc.conflict = base_prob/2
            
    if debug:
        if orig_type == 1:
            type_string = "hit"
        elif orig_type == 2:
            type_string = "conf"
        elif orig_type == 3:
            type_string = "miss"
        print "Orig accs:", type_string, "(" + str(orig_type) +")", 
        print ", hit:", hmc.hit,
        print ", miss:", hmc.miss, ", conf:", hmc.conflict
    # sanity check
    #sum_prob = hmc.hit + hmc.miss + hmc.conflict
    #if sum_prob != base_prob:
    #    print "Error, sum should be", base_prob, "but is", sum_prob
    #    print orig_type, total_sr, total_sb, total_accs
    #    exit(9)

    return hmc

# Get the hit/miss/conflict ratios for all interference pattern groups. 
# Version V1. 
# Inputs:
#      inter_pat_groups: Essentially a two-D array for interference patterns.
#                        Each group has the interference pattern for one 
#                        channel reuse distance.
#      thr_info: thread_info object
#      debug: debug output control
# Return:
#      hmc_ratios object
def gen_hmc_v1_all_inter_pat_group(inter_pat_groups, thr_info, debug):
    hmc = hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0

    sum_pb = 0.0
    for inter_pats in inter_pat_groups:
        for inter_pat in inter_pats:
            # process this interference pattern
            cases = gen_cases_inter_pat(inter_pat, thr_info, debug)
            # generate HMC ratio for each case
            for case in cases:
                hmc1 = gen_hmc_v1_inter_pat(inter_pat, thr_info, case, debug)
                hmc.hit += hmc1.hit
                hmc.miss += hmc1.miss
                hmc.conflict += hmc1.conflict

        print "Group hit/miss/conflict:", hmc.hit, hmc.miss, hmc.conflict

    # sanity check
    sum_prob = hmc.hit + hmc.miss + hmc.conflict
    if sum_prob != 1.0:
        print "HMC ratio sum is not 1.0 but", sum_prob
    
    return hmc


# This function process a generated full interference pattern to get the hit,
# miss, or conflict state for this pattern. Row buffer auto-closing and 
# accesses reordering are consider. Version 1 as stated at the beginning of
# this file.
# Inputs:
#       full_inter_pat: a full interference pattern
#       thr_info: see thread_info class for information
# Return:
#       an object of class hmc_ratios
def gen_hmc_v1_inter_pat(inter_pat, thr_info, case, debug):

    hmc = hmc_ratios()
    prob = inter_pat.prob

    # find the corresponding channel reuse distance information
    found = False
    for chnl_dist in thr_info.chnl_reuse_dists:
        if chnl_dist.acc_dist == inter_pat.chnl_reuse_dist:
            found = True
            break
    if not found:
        print "Weired: reuse distance not found"
        exit(3)
    # here I treat the previous access from the target thread as the 
    # same as any middle threads. Now lets generate the cases and 
    # probabilities for the three new cases
    # previous access is to the same row
    org_acc_type = 1 # same row, a hit originally
    base_prob = inter_pat.prob * chnl_dist.hit_prob;
    if inter_pat.prob != 0:
        hmc1 = gen_hmc_v1_inter_pat_w_org_acc(inter_pat, thr_info, case,
                                              base_prob, org_acc_type, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to the same bank but different row
    org_acc_type = 2 # same row different bank, a conflict originally
    base_prob = inter_pat.prob * chnl_dist.conf_prob;
    if inter_pat.prob != 0:
        hmc1 = gen_hmc_v1_inter_pat_w_org_acc(inter_pat, thr_info, case,
                                              base_prob, org_acc_type,debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict
    # previous access is to a different bank
    org_acc_type = 3 # different bank, a miss originally
    base_prob = inter_pat.prob * chnl_dist.miss_prob;
    if inter_pat.prob != 0:
        hmc1 = gen_hmc_v1_inter_pat_w_org_acc(inter_pat, thr_info, case,
                                              base_prob, org_acc_type, debug)
        hmc.hit += hmc1.hit
        hmc.miss += hmc1.miss
        hmc.conflict += hmc1.conflict

    return hmc
    
# Basically same function as gen_hmc_full_inter_pat. The only difference there
# is that the previous access (org_acc) from the target thread is also
# considered.
#
# Inputs: also see comments to function gen_hmc_full_inter_pat
#       org_acc_type: whether the org_acc is the 1) same row 2) same bank 
#                     different row 3) different bank
# Return:
#       an object of class hmc_ratios
def gen_hmc_v1_inter_pat_w_org_acc(inter_pat, thr_info, case, base_prob,
                                   org_acc_type, debug):

    #output = inter_pat_gen.log_full_inter_pat(inter_pat)
    #print "Processing: org_type", org_acc_type, ",",  output

    # search from the last access in this sequence, look for two accesses:
    # 1. last access "a" that access the same bank (could be the same row)
    # 2. last access "b" that access that same row
    # Here I assume for any access slot, thread 1 is always the first access
    # thread 2 is the next, etc. Just realized this is probably also a 
    # simplification, should work anyway
    last_same_bank = -1
    last_same_row = -1
    
    acc_checked = 0
    for acc_idx in range(inter_pat.chnl_reuse_dist - 1, -1, -1):
        for thr_idx in range(inter_pat.thread_cnt - 2, -1, -1):
            thr = inter_pat.threads[thr_idx].cases[case[thr_idx]]
            if not thr.accesses[acc_idx].same_chnl:
                # only count for accesses in this channel
                continue
            acc_checked += 1
            #print acc_checked, thr_idx, acc_idx, thr.accesses[acc_idx].same_chnl
            #print acc_checked ,thr_idx, acc_idx, 
            #print inter_pat.threads[thr_idx].accesses[acc_idx].same_chnl
            if (( last_same_bank == -1) and
                thr.accesses[acc_idx].same_bank ):
                last_same_bank = acc_checked
            if (( last_same_row == -1) and
                thr.accesses[acc_idx].same_row ):
                last_same_row = acc_checked
            # should have two breaks here, but I am just too lazy...

    # calculate the real probability of this case
    for idx,val in enumerate(case):
        base_prob *= inter_pat.threads[idx].cases[val].prob

    # check the previous access of the target thread if we didn't find
    # the accesses we want
    if (( last_same_bank == -1) and (org_acc_type == 2)):
        last_same_bank = acc_checked + 1
    if (( last_same_row == -1) and (org_acc_type == 1)):
        last_same_row = acc_checked + 1
    
    acc = -1
    reordered = False
    # there are five cases to check, see my notes on Feb 26 2013
    # case 1
    if ((last_same_bank != -1) and (last_same_row != -1) and 
        (last_same_bank == last_same_row)):
        case = 1 #defer process
    # case 2
    if ((last_same_bank != -1) and (last_same_row != -1) and 
        (last_same_bank != last_same_row)):
        if (last_same_row < last_same_bank): # last access is same row
            case = 1 # similar to the process of case 1
        else: # last access is same bank
            if (last_same_row * thr_info.est_serv_time <= 
                thr_info.reorder_time):
                # same row access and the target access are reorder-able
                acc = 1 # hit
                reordered = True
                case = 2
            else:
                case = 3  # similar to the process of case 3
    # case 3
    if ((last_same_bank != -1) and (last_same_row == -1)):
        case = 3 # defer process
    # case 4
    if ((last_same_bank == -1) and (last_same_row != -1)):
        case = 1 # similar to the process of case 1
    # case 5
    if ((last_same_bank == -1) and (last_same_row == -1)):
        case = 5
        acc = 2 # miss
    
    if case == 1: # process for case 1
        if (last_same_row * thr_info.est_serv_time > 
            thr_info.autoclose_time): #auto-closed
            if (last_same_row * thr_info.est_serv_time <= 
                thr_info.reorder_time): #reordered
                reordered = True
                acc = 1 # hit
            else:
                acc = 2 # miss
        else: #not auto-closed
            acc = 1 # hit
    elif case == 3: # process for case 3
        if (last_same_row * thr_info.est_serv_time > 
            thr_info.autoclose_time): #auto-closed
            acc = 2 # miss
        else:
            acc = 3 # conflict

    if acc == -1:
        print "Error: access type not set for case:", case
        exit(4)

    hmc = hmc_ratios()
    if acc == 1: # hit
        hmc.hit = base_prob
    elif acc == 2: # miss
        hmc.miss = base_prob
    elif acc == 3: # conflict
        hmc.conflict = base_prob

    # if half reordered 
    if thr_info.half_reorder and reordered:
        hmc.conflict += hmc.hit / 2
        hmc.hit /= 2
    
    #print "Processed result:", acc, base_prob, last_same_row, last_same_bank

    return hmc

# log a case of an interference pattern
def log_hmc_case(inter_pat, case):
    output = "{A" 
    for idx,val in enumerate(case):
        output += ",[prob:" + str(inter_pat.threads[idx].cases[val].prob)
        for a in inter_pat.threads[idx].cases[val].accesses:
            if a.same_row:
                output += ",r"
            elif a.same_bank:
                output += ",b"
            elif a.same_chnl:
                output += ",c"
            else:
                output += ",_"
        output += "]"
        
    output += ",A}"
    return output

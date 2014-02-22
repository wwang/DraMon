# This file contains functions for generating interference patterns of accesses 
# that fall between two consecutive same-channel memory accesses of the target 
# thread. There are several versions of algorithms to generated these sequences.
#
# A interference pattern here includes the memory accesses as well as the state
# of each accesses, i.e., same row, same bank, same channel and different row.
# 
# There are four ways to generate the interference pattern:
# 1. V1: Full version, generate the state for every access based on channel 
#    reuse distance and hit/miss/conflict probabilities.
# 2. V2: Like full version, but only track the number of each type of accesses.
#        This is acctually the same as V1. 
# 3. V3: Assuming all accesses in one thread has the same state. This is based 
#        on the observation that most consecutive accesses have the same state.
#        Also, for every middle thread, only the last of its target bank access
#        matters.
# 5. V4: Bernoulli version, considers every access independent and generate 
#        the stats independently
# Author: Wei Wang (wwang@virginia.edu) University of Virginia
#

import itertools
import Queue
import copy

from mem_model_types import *
import acc_gen
import hmc_ratios_gen

# Log a full_interference_pattern class
def log_full_inter_pat(inter_pat):
    output = ""
    output += "chnl_reuse_dist: " + str(inter_pat.chnl_reuse_dist)
    output += ", thread_cnt: " + str(inter_pat.thread_cnt)
    output += ", prob: " + str(inter_pat.prob)
    output += ", total_accs: " + str(inter_pat.total_accs)
    output += ", per_thread: {"
    
    for acc_seq in inter_pat.threads:
        output += "[" + acc_gen.log_acc_sequence(acc_seq) + "],"
    
    output += "}"
    
    return output

# Check the sum of the probabilities of an array of full_interference_patterns, 
# make sure the sum is 1
def check_full_patterns_sum(inter_pats):
    sum_prob = 0.0
    for inter_pat in inter_pats:
        sum_prob += inter_pat.prob
    
    return sum_prob

# for sanity check
all_acc_stats_prob_sum = 0.0
# Generate the states for each access in all full interference patterns. 
# One access can have four states: 1) accessing target bank and target row; 
# 2) accessing target bank but non-target rows; 3) accessing non-target bank;
# 4) accessing non-target channel
#
# Input:
#      full_inter_pat_groups: groups of full_interference_patterns, each group
#                             corresponds to one channel reuse distance
#      thr_info: see thread_info class
#
# Return:
#      hmc_ratios class: hmc ratios of all interference patterns
def gen_acc_stat_all(full_inter_pat_groups, thr_info):
    
    global all_acc_stats_prob_sum
    all_acc_stats_prob_sum = 0.0
    hmc = hmc_ratios_gen.hmc_ratios()
    hmc.hit = 0
    hmc.miss = 0
    hmc.conflcit = 0

    for inter_pats in full_inter_pat_groups:
        for inter_pat in inter_pats:
            # generate the access status and ratios for this interference 
            # pattern
            hmc1 = gen_acc_stat_one(inter_pat, thr_info)
            hmc.hit += hmc1.hit
            hmc.miss += hmc1.miss
            hmc.conflict += hmc1.conflict

    # sanity checks
    if all_acc_stats_prob_sum != 1.0:
        output = ("The sum probability of all cases is not 1.0, but " + 
                  str(all_acc_stats_prob_sum))
        print output
    if (hmc.hit + hmc.miss + hmc.conflict) != 1.0:
        output = ("HMC ratios sum not 1.0:[ sum: " + str(hmc.hit+hmc.miss+
                                                         hmc.conflict) + ", " + 
                  "(hit: " + str(hmc.hit) + ", miss: " + str(hmc.miss) + 
                  ", conflict: " + str(hmc.conflict) + ")]")
        print output
    return hmc


# stores the probabilities of the four states: same_bank_same_row, 
# same_bank_diff_row, diff_bank, diff_channel
class acc_stat_probs:
    def __init__(self):
        self.same_bank_same_row = 0.0
        self.same_bank_diff_row = 0.0
        self.diff_bank = 0.0
        self.diff_channel = 0.0 

# Generate the states for each access in one full interference patterns, then
# process the states to compute the hit/miss/conflict ratios.
# See comments of function gen_acc_stat_all for more information. Inputs and
# return value almost the same as function gcc_acc_stat as well.
#
# This function uses depth first search to generate all cases. Each node in the
# tree represents one access at one state.
def gen_acc_stat_one(inter_pat, thr_info):
    
    # initialize the indices
    inter_pat.cur_thread = 0;
    for thr in inter_pat.threads:
        thr.cur_acc = 0;

    # push the root onto search stack
    search_stack = []
    search_stack.append(inter_pat)
    
    # hmc ratios to return
    hmc = hmc_ratios_gen.hmc_ratios()
    hmc.hit = 0.0
    hmc.miss = 0.0
    hmc.conflict = 0.0
    global all_acc_stats_prob_sum
            
    # do the DFS search
    while len(search_stack) != 0: #{
        node = search_stack.pop()
      
        # check if all accesses of this node has been updated
        # if yes, process this node
        if node.cur_thread >= len(node.threads):
            all_acc_stats_prob_sum += node.prob
            output =  log_full_inter_pat(node)
            # see what the one is (hit,miss,conf)
            hmc1 = hmc_ratios_gen.gen_hmc_full_inter_pat(node, thr_info)
            output += (" {hit: " + str(hmc1.hit) + ", miss: " + str(hmc1.miss) +
                       ", conf: " + str(hmc1.conflict) + "}")
            print output
            hmc.hit += hmc1.hit
            hmc.miss += hmc1.miss
            hmc.conflict += hmc1.conflict
            continue
        
        # generate the memory access states for the current access
        probs = gen_acc_stats(node, thr_info)
        thread_idx = node.cur_thread
        acc_idx = node.threads[thread_idx].cur_acc
        # advance indices
        node.threads[node.cur_thread].cur_acc += 1
        if (node.threads[node.cur_thread].cur_acc >= 
            len(node.threads[node.cur_thread].accesses)):
            node.cur_thread += 1

        # generate the children (3 for target channel access, 1 for non-target
        # channel access) and push into the stack
        if probs.same_bank_same_row != 0.0:
            child = copy.deepcopy(node)
            child.prob *= probs.same_bank_same_row

            cur_thread = child.threads[thread_idx]
            cur_acc = cur_thread.accesses[acc_idx]
            cur_acc.same_chnl = True
            cur_acc.same_bank = True
            cur_acc.same_row = True

            search_stack.append(child)
            print log_full_inter_pat(child)            
        if probs.same_bank_diff_row != 0.0:
            child = copy.deepcopy(node)
            child.prob *= probs.same_bank_diff_row

            cur_thread = child.threads[thread_idx]
            cur_acc = cur_thread.accesses[acc_idx]
            cur_acc.same_chnl = True
            cur_acc.same_bank = True
            cur_acc.same_row = False

            search_stack.append(child)
            print log_full_inter_pat(child)            
        if probs.diff_bank != 0.0:
            child = copy.deepcopy(node)
            child.prob *= probs.diff_bank

            cur_thread = child.threads[thread_idx]
            cur_acc = cur_thread.accesses[acc_idx]
            cur_acc.same_chnl = True
            cur_acc.same_bank = False
            cur_acc.same_row = False

            search_stack.append(child)
            print log_full_inter_pat(child)            
        if probs.diff_channel != 0.0:
            child = copy.deepcopy(node)
            child.prob *= probs.diff_channel

            cur_thread = child.threads[thread_idx]
            cur_acc = cur_thread.accesses[acc_idx]
            cur_acc.same_chnl = False
            cur_acc.same_bank = False
            cur_acc.same_row = False

            search_stack.append(child)
            print log_full_inter_pat(child)            
    #} end while

    return hmc

# sum all probs in an acc_stat_probs
def sum_acc_stat_probs(probs):
    sum_prob = (probs.same_bank_same_row + 
                probs.same_bank_diff_row + 
                probs.diff_bank + 
                probs.diff_channel )
    return sum_prob

# Generate the probabilities of the three cases for a full interference
# pattern. See comments of function gen_acc_stat_all for more information.
# 
# Input:
#      inter_pat: see class full_interference_pattern
#      thr_info : see class thread_info
# Return:
#      an object of acc_stat_probs class
def gen_acc_stats(inter_pat, thr_info):

    probs = acc_stat_probs()
    probs.same_bank_same_row = 0.0
    probs.same_bank_diff_row = 0.0
    probs.diff_bank = 0.0
    probs.diff_channel = 0.0

    thr_idx = inter_pat.cur_thread
    thread = inter_pat.threads[thr_idx]
    acc_idx = thread.cur_acc
    acc = thread.accesses[acc_idx]
    
    # if this access is on non-target channel
    if acc.same_chnl == False:
        probs.diff_channel = 1.0
        return probs
    
    # if this is the first access of a thread, probabilities are based on
    # basic cases
    if acc_idx == 0:
        probs.diff_bank = 1 - thr_info.bank_prob
        probs.same_bank_diff_row = thr_info.bank_prob * (1 - thr_info.row_prob)
        probs.same_bank_same_row = thr_info.bank_prob * thr_info.row_prob
        
        sum_prob = sum_acc_stat_probs(probs)
        if sum_prob > 1.1 or sum_prob < 0.9:
            print "1 Error sum prob not 1.0, but ", sum_prob
            exit(0)
        return probs
    
    # this is not the first access. Now we need to figure out the previous
    # target channel access in this access sequence
    found = False
    for prev in range(acc_idx-1, -1, -1):
        if thread.accesses[prev].same_chnl == True:
            prev_acc = thread.accesses[prev]
            found = True
            break
    if not found: # this is the first in this sequence, treat like basic base
        probs.diff_bank = 1 - thr_info.bank_prob
        probs.same_bank_diff_row = thr_info.bank_prob * (1 - thr_info.row_prob)
        probs.same_bank_same_row = thr_info.bank_prob * thr_info.row_prob
        
        sum_prob = sum_acc_stat_probs(probs)
        if sum_prob > 1.1 or sum_prob < 0.9:
            print "2 Error sum prob not 1.0, but ", sum_prob
            exit(0)
        return probs        

    # get the access distance 
    acc_dist = acc_idx - prev
    
    # find the corresponding channel reuse distance
    found = False
    for cr_idx in range(len(thr_info.chnl_reuse_dists)):
        if thr_info.chnl_reuse_dists[cr_idx].acc_dist == acc_dist:
            crd = thr_info.chnl_reuse_dists[cr_idx]
            found = True
            break
    if not found:
        print "Weird, access distance not exists"
        output =  log_full_inter_pat(inter_pat)
        print output
        print "thr_idx:", thr_idx, "acc_idx:", acc_idx
        print "prev:", prev, "acc_dist:", acc_dist
        exit(4)

    # count the probabilities
    # current access HITs previous access: same state as previous
    if prev_acc.same_row: # prev: same bank same row
        probs.same_bank_same_row += crd.hit_prob
    elif prev_acc.same_bank: # prev: same bank different row
        probs.same_bank_diff_row += crd.hit_prob
    else: # prev: different bank
        probs.diff_bank += crd.hit_prob

    # current access MISSes previous access:
    # if previous is one the same bank, then current one is the different bank
    # if previous is different bank, then current one may be any three cases
    if prev_acc.same_row or prev_acc.same_bank: # prev: same bank
        probs.diff_bank += crd.miss_prob
    else: # prev: different bank
        # same bank same row
        probs.diff_bank += crd.miss_prob * (1 - thr_info.bank_prob)
        probs.same_bank_diff_row += (crd.miss_prob * (thr_info.bank_prob * 
                                                     (1 - thr_info.row_prob)))
        probs.same_bank_same_row += (crd.miss_prob * thr_info.bank_prob * 
                                    thr_info.row_prob)

    # current access CONFLICTs previous access:
    # prev: same bank same row ==> current: same bank different row
    # prev: same bank different row ==> current: same bank same/different row
    # prev: different bank ==> different bank
    if prev_acc.same_row: # prev: same bank same row
        probs.same_bank_same_row += crd.conf_prob
    elif prev_acc.same_bank: # prev: same bank different row
        probs.same_bank_same_row += crd.conf_prob * thr_info.row_prob
        probs.same_bank_diff_row += crd.conf_prob * (1 - thr_info.row_prob)
    else:
        probs.diff_bank += crd.conf_prob
    
    # sanity check
    sum_prob = sum_acc_stat_probs(probs)
    if sum_prob > 1.1 or sum_prob < 0.9:
        print "3 Error sum prob not 1.0, but ", sum_prob
        exit(0)
    return probs

# For each access sequence of each channel reuse distance, generate all possible
# cases of access states.
# Input:
#      thr_info: a thread_info object
# Return:
#      Nothing to return. all cases are attach to the 'cases' list of each 
#      access sequence object (accs_on_thread).
def gen_acc_seq_stats_all(thr_info, debug):
    for ch_dist in thr_info.chnl_reuse_dists:
        for acc_seq in ch_dist.acc_seqs:
            acc_seq.cases = gen_acc_seq_stats(acc_seq, thr_info, debug)
            
            # sanity check
            sum_prob = 0.0
            for c in acc_seq.cases:
                sum_prob += c.prob
            if sum_prob > 1.1 or sum_prob < 0.9:
                print "1 Cases sum probability is not 1, but", str(sum_prob)
                exit(5)
    
    return
        

# Generate all possible access states for one access sequence.
# This algorithm is kind hard to follow. Essentially its a DFS search. With each
# node represents a certain access in the sequence. Each node has a value to 
# indicate its current state, and has a value to indicate the next state it has
# to search. When an access with a certain state is pushed to the stack, its 
# corresponding probability is computed. To save time, I compute the 
# probabilities all state for this accesses, and saved it for later use.
# Input:
#      acc_seq: an accs_one_thread object; the access sequence to process
#      thr_info: a thread_info object
# Return:
#      all possible cases of access states, each case is an object of 
#      acc_seq_case.
def gen_acc_seq_stats(acc_seq, thr_info, debug):
    
    cases = []
    
    # DFS search
    types = 4 # 0 same row, 1 same bank, 2 same channel, 3 next channel
    leng = len(acc_seq.accesses)
    cur_states = [0] * leng # state for each access in current search path
    next_states = [0] * (leng + 1) # state for each access in next search path
    cur_probs = [None] * leng # probs of the 4 types of states for each access 
                              # in current search path
    stack_top = 0 # stack pointer
    while stack_top != -1:
        if stack_top == leng:
            # one case generated, process it
            case = generate_a_full_case(acc_seq, cur_states, cur_probs, debug)
            if case.prob != 0.0:
                cases.append(case)
            stack_top -= 1             # pop the last item from stack
            continue
        c = next_states[stack_top]
        if c != types:
            cur_states[stack_top] = c
            if c == 0: # just starting processing a new set of states for this 
                       # access, so calculate the probabilities for each type
                       # of accesses
                cur_probs[stack_top] = gen_full_acc_seq_probs(acc_seq, thr_info,
                                                              cur_states,
                                                              stack_top,
                                                              debug)
            next_states[stack_top] += 1
            # only proceed to next access if current state's 
            # probability is not 0
            if (c == 0) and (cur_probs[stack_top].same_bank_same_row == 0.0):
                continue
            elif (c == 1) and (cur_probs[stack_top].same_bank_diff_row == 0.0):
                continue
            elif (c == 2) and (cur_probs[stack_top].diff_bank == 0.0):
                continue
            elif (c == 3) and (cur_probs[stack_top].diff_channel == 0.0):
                continue
            stack_top += 1
            next_states[stack_top] = 0
        else:
            stack_top -= 1
    
    return cases
            
# For an array that represents the states of accesses, generate the 
# corresponding acc_seq_case. 
# Input:
#      acc_seq: an accs_one_thread object, the access sequence for this case
#      cur_states: an integer array, each element represents that state of one
#                  access; 0 same row, 1 same bank, 2 same channel,
#                  3 different channel
#      cur_probs: probabilities of each case of each accesses
# Return:
#      an acc_seq_case object
def generate_a_full_case(acc_seq, cur_states, cur_probs, debug):

    case = acc_seq_case()
    case.prob = 1.0
    for idx, val in enumerate(cur_states):
        if val == 0: # same row
            case.total_accs += 1
            case.total_sr += 1
            acc = access_status()
            acc.same_chnl = True
            acc.same_bank = True
            acc.same_row = True
            acc.prob = cur_probs[idx].same_bank_same_row
            case.prob *= acc.prob
            case.accesses.append(acc)
        elif val == 1: # same bank different row
            case.total_accs += 1
            case.total_sb += 1
            acc = access_status()
            acc.same_chnl = True
            acc.same_bank = True
            acc.same_row = False
            acc.prob = cur_probs[idx].same_bank_diff_row
            case.prob *= acc.prob
            case.accesses.append(acc)
        elif val == 2: # same channel different bank
            case.total_accs += 1
            acc = access_status()
            acc.same_chnl = True
            acc.same_bank = False
            acc.same_row = False
            acc.prob = cur_probs[idx].diff_bank
            case.prob *= acc.prob
            case.accesses.append(acc)
        elif val == 3: # different channel
            acc = access_status()
            acc.same_chnl = False
            acc.same_bank = False
            acc.same_row = False
            acc.prob = cur_probs[idx].diff_channel
            case.prob *= acc.prob
            case.accesses.append(acc)

    # sanity check
    if (case.prob != 0.0) and (acc_seq.total_accs != case.total_accs):
        print "Total access does not match, should be", acc_seq.total_accs
        print "The access sequence is", acc_gen.log_acc_sequence(acc_seq)
        print "But is", case.total_accs, "with accesses", cur_states
        print "Bad case probability  is", case.prob
        exit(6)

    return case

# For "cur_acc_idx"th access, generate all the probabilities of each access type
# for it. 
# Input:
#      acc_seq: the access sequence, accs_one_thread object
#      thr_info: the thread_info object
#      cur_states: an integer array, each element represents that state of one
#                  access; 0 same row, 1 same bank, 2 same channel,
#                  3 different channel
#      acc_idx: the index of current access to process
#      debug: debug output control
# Return:
#      an object of acc_stat_probs class 
def gen_full_acc_seq_probs(acc_seq, thr_info, cur_states, acc_idx, debug):
    probs = acc_stat_probs()
    probs.same_bank_same_row = 0.0
    probs.same_bank_diff_row = 0.0
    probs.diff_bank = 0.0
    probs.diff_channel = 0.0

    acc = acc_seq.accesses[acc_idx]
    
    # if this access is on non-target channel
    if acc.same_chnl == False:
        probs.diff_channel = 1.0
        return probs
    
    # if this is the first access of a thread, probabilities are based on
    # basic cases
    if acc_idx == 0:
        probs.diff_bank = 1 - thr_info.bank_prob
        probs.same_bank_diff_row = thr_info.bank_prob * (1 - thr_info.row_prob)
        probs.same_bank_same_row = thr_info.bank_prob * thr_info.row_prob
        
        sum_prob = sum_acc_stat_probs(probs)
        if sum_prob > 1.1 or sum_prob < 0.9:
            print "4 Error sum prob not 1.0, but ", sum_prob
            exit(0)
        return probs
    
    # this is not the first access. Now we need to figure out the previous
    # target channel access in this access sequence
    found = False
    for prev in range(acc_idx-1, -1, -1):
        if acc_seq.accesses[prev].same_chnl == True:
            prev_acc = acc_seq.accesses[prev]
            found = True
            break
    if not found: # this is the first in this sequence, treat like basic base
        probs.diff_bank = 1 - thr_info.bank_prob
        probs.same_bank_diff_row = thr_info.bank_prob * (1 - thr_info.row_prob)
        probs.same_bank_same_row = thr_info.bank_prob * thr_info.row_prob
        
        sum_prob = sum_acc_stat_probs(probs)
        if sum_prob > 1.1 or sum_prob < 0.9:
            print "5 Error sum prob not 1.0, but ", sum_prob
            exit(0)
        return probs        

    # get the access distance 
    acc_dist = acc_idx - prev
    
    # find the corresponding channel reuse distance
    found = False
    for cr_idx in range(len(thr_info.chnl_reuse_dists)):
        if thr_info.chnl_reuse_dists[cr_idx].acc_dist == acc_dist:
            crd = thr_info.chnl_reuse_dists[cr_idx]
            found = True
            break
    if not found:
        print "Weird, access distance not exists"
        output =  log_full_inter_pat(inter_pat)
        print output
        print "thr_idx:", thr_idx, "acc_idx:", acc_idx
        print "prev:", prev, "acc_dist:", acc_dist
        exit(4)

    # count the probabilities
    # current access HITs previous access: same state as previous
    if prev_acc.same_row: # prev: same bank same row
        probs.same_bank_same_row += crd.hit_prob
    elif prev_acc.same_bank: # prev: same bank different row
        probs.same_bank_diff_row += crd.hit_prob
    else: # prev: different bank
        probs.diff_bank += crd.hit_prob

    # current access MISSes previous access:
    # if previous is one the same bank, then current one is the different bank
    # if previous is different bank, then current one may be any three cases
    if prev_acc.same_row or prev_acc.same_bank: # prev: same bank
        probs.diff_bank += crd.miss_prob
    else: # prev: different bank
        # same bank same row
        probs.diff_bank += crd.miss_prob * (1 - thr_info.bank_prob)
        probs.same_bank_diff_row += (crd.miss_prob * (thr_info.bank_prob * 
                                                     (1 - thr_info.row_prob)))
        probs.same_bank_same_row += (crd.miss_prob * thr_info.bank_prob * 
                                    thr_info.row_prob)

    # current access CONFLICTs previous access:
    # prev: same bank same row ==> current: same bank different row
    # prev: same bank different row ==> current: same bank same/different row
    # prev: different bank ==> different bank
    if prev_acc.same_row: # prev: same bank same row
        probs.same_bank_same_row += crd.conf_prob
    elif prev_acc.same_bank: # prev: same bank different row
        probs.same_bank_same_row += crd.conf_prob * thr_info.row_prob
        probs.same_bank_diff_row += crd.conf_prob * (1 - thr_info.row_prob)
    else:
        probs.diff_bank += crd.conf_prob
    
    # sanity check
    sum_prob = sum_acc_stat_probs(probs)
    if sum_prob > 1.1 or sum_prob < 0.9:
        print "6 Error sum prob not 1.0, but ", sum_prob
        exit(0)
    return probs

# For each access sequence of each channel reuse distance, generate all possible
# cases of access states. Version 3
# Input:
#      thr_info: a thread_info object
# Return:
#      Nothing to return. all cases are attach to the 'cases' list of each 
#      access sequence object (accs_on_thread).
def gen_acc_seq_stats_all_v3(thr_info, debug):
    for ch_dist in thr_info.chnl_reuse_dists:
        for acc_seq in ch_dist.acc_seqs:
            acc_seq.cases = gen_acc_seq_stats_v3(acc_seq, thr_info, debug)

            if debug:
                output = acc_gen.log_acc_sequence(acc_seq)
                print output
                for c in acc_seq.cases:
                    output = log_acc_seq_case(c)
                    print output
            # sanity check
            sum_prob = 0.0
            for c in acc_seq.cases:
                sum_prob += c.prob
            if sum_prob > 1.1 or sum_prob < 0.9:
                print "2 Cases sum probability is not 1, but", str(sum_prob)
                exit(5)
    
    return

# Generate all possible access states for one access sequence. Version 3.
# All accesses are assumed to have the same state
# Input:
#      acc_seq: an accs_one_thread object; the access sequence to process
#      thr_info: a thread_info object
# Return:
#      all possible cases of access states, each case is an object of 
#      acc_seq_case.
def gen_acc_seq_stats_v3(acc_seq, thr_info, debug):
    
    cases = []

    # case 4: all accessing different channel. Only happens if all accesses in
    # this sequnces are on different channel already
    all_diff_chnl = True
    for acc in acc_seq.accesses:
        if acc.same_chnl == True:
            all_diff_chnl = False
            break
    if all_diff_chnl: # this access sequence is indeed case 4:
        # the case is the same as the access sequence
        case = acc_seq_case()
        for acc in acc_seq.accesses:
            acc1 = copy.deepcopy(acc)
            case.accesses.append(acc1)
        case.total_accs = acc_seq.total_accs
        case.total_sr = 0
        case.total_sb = 0
        case.prob = 1.0
        cases.append(case)
        return cases

    # case 1: all accessing the same row
    case = acc_seq_case()
    for acc in acc_seq.accesses:
        acc1 = copy.deepcopy(acc)
        if acc1.same_chnl:
            acc1.same_bank = True
            acc1.same_row = True
        case.accesses.append(acc1)
    case.total_accs = acc_seq.total_accs
    case.total_sr = case.total_accs
    case.total_sb = 0
    case.prob = thr_info.bank_prob * thr_info.row_prob
    cases.append(case)
    # case 2: all accessing the same bank but different row
    case = acc_seq_case()
    for acc in acc_seq.accesses:
        acc1 = copy.deepcopy(acc)
        case.accesses.append(acc1)
        if acc1.same_chnl:
            acc1.same_bank = True
            acc1.same_row = False
    case.total_accs = acc_seq.total_accs
    case.total_sb = case.total_accs
    case.total_sr = 0
    case.prob = thr_info.bank_prob * (1-thr_info.row_prob)
    cases.append(case)
    # case 3: all accessing the same channel, but different bank
    case = acc_seq_case()
    for acc in acc_seq.accesses:
        acc1 = copy.deepcopy(acc)
        case.accesses.append(acc1)
        if acc1.same_chnl:
            acc1.same_bank = False
            acc1.same_row = False
    case.total_accs = acc_seq.total_accs
    case.total_sb = 0
    case.total_sr = 0
    case.prob = 1 - thr_info.bank_prob
    cases.append(case)
    
    return cases

# output a case
def log_acc_seq_case(case):
    output = "Prob:" + str(case.prob) 
    output += ", total_accs:" + str(case.total_accs)
    output += ", total_same_row:" + str(case.total_sr)
    output += ", totla_same_bank:" + str(case.total_sb)
    output += ", acs:" + log_access_status_list(case.accesses)
    
    return output

# output accesses (list of access_status)
def log_access_status_list(accs):
    output = "{A" 
    
    for a in accs:
        if a.same_row:
            output += ",r"
        elif a.same_bank:
            output += ",b"
        elif a.same_chnl:
            output += ",c"
        else:
            output += ",_"

    output += ",A}"
    
    return output
            

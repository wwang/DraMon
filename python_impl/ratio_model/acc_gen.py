# This file contains functions for generating sequences of memory accesses that
# fall between two consecutive same-channel memory accesses of the target 
# thread. There are several versions of algorithms to generated these sequences.
#
# There are six ways to generate the access sequence:
# 1. V1 -- Full version: every single access of every thread is generated. 
#    Their relative positions (order of the accesses) are also considered
# 2. V2 -- Full version with combinations: like V1, every access is generated,
#    however, the relative position does not matter here.
# 3. V3 -- A Bernoulli distribution version: the probability that an access hits
#    the targeted channel is calculated independently, not related to previous 
#    accesses from the same thread. Only the number of total accesses to the
#    target channel in one accesses sequence is considered. Like V2, only 
#    combinations of accesses sequences are considered.
# 4. V4 -- Full version without considering min-consecutive-(non)accesses and
#          treat every access individually.
# Author: Wei Wang (wwang@virginia.edu) University of Virginia
#

import itertools
import Queue
import copy
import math

from mem_model_types import *
import inter_pat_gen
import hmc_ratios_gen

# Fully generate the sequence of middle accesses. Keep track of every single 
# access. No simplification is made
# Inputs:
#       thr_info: see thread_info class
#       con_acc_probs: see consecutive_acc_probs class
#       con_noacc_probs: see consecutive_noacc_probs class
#       thread_cnt: how many threads to process
#       min_con_acc: minimum number of consecutive accesses to target channel
#       min_con_noacc: minimum number of consecutive accesses to other channels
#       debug: whether enable debug output or not
# Return:
#       full_inter_pats[]: see full_interference_pattern class
def gen_acc_seq_v1(thr_info, con_acc_probs, con_noacc_probs, 
                     thread_cnt, min_con_acc, min_con_noacc, debug):

    full_inter_pat_groups = [] # all patterns for all channel reuse distance
    sum_prob = 0.0
    
    # for each channel reuse distance, generate the access sequence for one 
    # thread
    for ch_dist in thr_info.chnl_reuse_dists:
        acc_seqs = gen_full_acc_seq_1thr(thr_info, ch_dist, 
                                         con_acc_probs,
                                         con_noacc_probs, min_con_acc, 
                                         min_con_noacc, debug)
        
        # generate the interfere patterns for this channel resue distance
        perms = list(itertools.product(range(len(acc_seqs)), 
                                       repeat = (thread_cnt-1)))

        full_inter_pats = [] # all patterns for one channel reuse distance
        full_inter_pat_groups.append(full_inter_pats)
        for perm in perms:
            inter_pat = full_interference_pattern()
            inter_pat.chnl_reuse_dist = ch_dist.acc_dist
            inter_pat.prob = ch_dist.prob
            inter_pat.thread_cnt = thread_cnt
            full_inter_pats.append(inter_pat)
            # add the corresponding 
            for i in perm:
                acc_seq = copy.deepcopy(acc_seqs[i])
                inter_pat.threads.append(acc_seq)
                inter_pat.total_accs += acc_seq.total_accs
                inter_pat.prob *= acc_seq.prob
                #print inter_pat_gen.log_full_inter_pat(inter_pat)

        output = ("Channel-reuse-distance " + str(ch_dist.acc_dist) + 
                  " has interference patterns: " + str(len(full_inter_pats)))
        print output
        # sanity check
        sum_prob += inter_pat_gen.check_full_patterns_sum(full_inter_pats)
        
    # sanity check
    if sum_prob > 1.1 or sum_prob < 0.9:
        output = ("1 Error: probability sum of all patterns is not 1.0, " +
                  "but," + str(sum_prob))
        print output
        exit(1)
        
    return full_inter_pat_groups

# check whether a particular channel reuse distance is valid
# Inputs:
#       thr_info: thread_info class object, has all valid channel reuse 
#                 distances
#       reuse_dist: the channel reuse distance for check
# Return:
#       True: valid
#       False: invalid
def check_resue_dist(thr_info, reuse_dist):
    valid = False
    for ch_dist in thr_info.chnl_reuse_dists:
        if reuse_dist == ch_dist.acc_dist: # compare the input distance with
            valid = True                   # all valid reuse distances
    
    return valid

# Return a string for logging an accs_one_thread object (acc_seq)
def log_acc_sequence(acc_seq):
    output = "Prob: " + str(acc_seq.prob) + ", ("
    
    for acc in acc_seq.accesses:
        if acc.same_row == True:
            output += "r,"
        elif acc.same_bank == True:
            output += "b,"
        elif acc.same_chnl == True:
            output += "c,"
        else:
            output += "_,"
    output += "), ("
    for acc in acc_seq.accesses:
            output += str(acc.prob) + ","
    output += ")"
    
    return output

# Fully generate the sequences of middle accesses for one thread.
# Check the comments of function gen_acc_seq_v1 for information of inputs and
# outputs.
#
# Return an array of access sequences. Each sequence is an object of class
# accs_one_thread.
#
# This is essentially a breath first search of the access tree (see my notes).
# Each time a node is visited, do the following:
#   1. generate two children, one access target channel, one not.
#   2. check each child see if it is valid
#   3. generate probability for each child
#   4. push valid children into search queue
#   5. stop generate children if current node has enough accesses
def gen_full_acc_seq_1thr(thr_info, ch_dist, con_acc_probs, con_noacc_probs, 
                          min_con_acc, min_con_noacc, debug):

    search_q = Queue.Queue()
    root = accs_one_thread() # create root node
    root.accesses = [] # root has no accesses
    search_q.put(root) # add root to the search queue
    acc_seqs = [] # this is the array that has all valid access sequences
    
    # now start breath first search
    while not search_q.empty(): #{
        node = search_q.get()
                
        # generate left child: access target channel
        left = copy.deepcopy(node)
        acc_l = access_status()
        acc_l.same_chnl = True
        left.accesses.append(acc_l)
        
        # generate right child: access other channels
        right = copy.deepcopy(node)
        acc_r = access_status()
        acc_r.same_chnl = False
        right.accesses.append(acc_r)

        # check if left child valid
        left_valid = is_acc_seq_valid(left, thr_info, 
                                      min_con_acc, min_con_noacc)
        # check if right child valid
        right_valid = is_acc_seq_valid(right, thr_info,
                                       min_con_acc, min_con_noacc)
        
        # update the probility of the new access of left child when 
        # right child is not valid
        if left_valid and (not right_valid): 
            acc_l.prob = 1
       
        # update the probility of the new access of right child when
        # left child is not valid
        if right_valid and (not left_valid): 
            acc_r.prob = 1
                   

        if left_valid and len(left.accesses) == ch_dist.acc_dist: 
            # all accesses generate for this sequence
            left = generate_acc_probs(left, thr_info, 
                                      con_acc_probs, con_noacc_probs)
            acc_seqs.append(left)
        elif left_valid:
            search_q.put(left)

        if right_valid and len(right.accesses) == ch_dist.acc_dist: 
            # all accesses generate for this sequence
            right = generate_acc_probs(right, thr_info,
                                       con_acc_probs, con_noacc_probs)
            acc_seqs.append(right)
        elif right_valid: 
            search_q.put(right)
    #}

    if debug:
        for acc_seq in acc_seqs:
            output = log_acc_sequence(acc_seq)
            print output

    return acc_seqs
        
    
# Based on the minimum consecutive access/non-accesses distance, and channel
# reuse distance, check whether an access sequence is valid.
# The check can be done by keeping track of previous accesses, which can 
# save some time. But I am too tired to re-implement the check, copy is the
# best for me at this minute.
def is_acc_seq_valid(acc_seq, thr_info, min_con_acc, min_con_noacc):

    valid = True
    # check the channel reuse distance in this permutation, make sure the
    # the distance is valid
    last_acc_position = -1
    for i in range(len(acc_seq.accesses)):
        if acc_seq.accesses[i].same_chnl == False: # ignore accesses to other 
                                                   # channel
            continue    
        if last_acc_position == -1: # first target channel access in this
            last_acc_position = i   # acc_seq, update last position only
            continue
        reuse_dist = i - last_acc_position
        valid = check_resue_dist(thr_info, reuse_dist)
        if valid == False: # invalid acc_seq, no need to check any more
            break
        last_acc_position = i # valid reuse distance, update last position

    if not valid: # access sequence already invalid
        return valid

    # check the length of consecutive 1s, make sure the length no less
    # than min_con_acc
    con_acc_len = min_con_acc # assume there are enough 1s ahead of this 
                              # this access sequence
    for i in range(len(acc_seq.accesses)):
        if acc_seq.accesses[i].same_chnl == False: 
            # accessing other channel, check current length
            if con_acc_len != 0 and con_acc_len < min_con_acc:
                valid = False
                break
            con_acc_len = 0 # reset the counter
        else:
            con_acc_len += 1

    if not valid: # access sequence already invalid
        return valid

    # check the length of consecutive 0s, make sure the length no less
    # than min_con_noacc
    con_noacc_len = min_con_noacc # assume there are enough 0s ahead of 
                                      # this permutation
    for i in range(len(acc_seq.accesses)): #{
        if acc_seq.accesses[i].same_chnl == True: 
            # accessing target channel, check current length
            if con_noacc_len != 0 and con_noacc_len < min_con_noacc:
                valid = False
                break
            con_noacc_len = 0 # reset the counter
        else:
            con_noacc_len += 1
        #}
    
    return valid


# generate the probabilities for all accesses in an accesses sequence as well as
# the probability of whole sequence
def generate_acc_probs(acc_seq, thr_info, con_acc_probs, con_noacc_probs):
    # make a copy the access sequence
    acc_seq2 = copy.deepcopy(acc_seq)
    acc_seq2.prob = 1.0
    
    con_acc_len = 0 # keep track of the length of the consecutive 1s and 0s
    con_noacc_len = 0
    for i in range(len(acc_seq.accesses)): #{
        acc_stat = acc_seq2.accesses[i]
        chnl = acc_stat.same_chnl
        if chnl == True:
            acc_seq2.total_accs += 1
        if acc_stat.prob == 1: # already has a probability, no need to update
            acc_seq2.prob *= acc_stat.prob
            continue;
        # compute the probability of this access
        if i == 0: # the first access
            if acc_stat.same_chnl == True:
                acc_stat.prob = thr_info.chnl_prob
            else:
                acc_stat.prob = 1 - thr_info.chnl_prob
        else:
            if (con_acc_len != 0) and chnl == True: # 1 ==> 1 switching 
                acc_stat.prob = con_acc_probs.acc_prob[con_acc_len]
            elif (con_acc_len != 0) and chnl == False: # 1 ==> 0 switching
                acc_stat.prob = 1- con_acc_probs.acc_prob[con_acc_len]
            elif (con_noacc_len != 0) and chnl == False: # 0 ==> 0 switching
                acc_stat.prob = con_noacc_probs.noacc_prob[con_noacc_len]
            elif (con_noacc_len != 0) and chnl == True: # 0 ==> 1 switching
                acc_stat.prob = 1- con_noacc_probs.noacc_prob[con_noacc_len]
            
        # update the length of consecutive 1s and 0s
        if acc_stat.same_chnl == True: 
            con_acc_len += 1
            con_noacc_len = 0
        else:
            con_acc_len = 0
            con_noacc_len += 1
                
        # update whole sequence's probability
        acc_seq2.prob *= acc_stat.prob
        #}    

    return acc_seq2        
                
# V2 version as mentioned in the beginning comments. 
# Also check out the comments of function gen_acc_seq_v1
# A key difference between this one the the full version (V1) is that
# I am not going to do deepcopy, rather a link tot the sequnce     
def gen_acc_seq_v2_full_comb(thr_info, con_acc_probs, con_noacc_probs, 
                             thread_cnt, min_con_acc, min_con_noacc, debug):

    full_inter_pat_groups = [] # all patterns for all channel reuse distance
    sum_prob = 0.0
    
    # for each channel reuse distance, generate the access sequence for one 
    # thread
    for ch_dist in thr_info.chnl_reuse_dists:
        acc_seqs = ch_dist.acc_seqs
        
        # generate the combinations of different types of access sequence
        combs = list(combinations_with_replacement(range(len(acc_seqs)), 
                                                   thread_cnt-1))

        full_inter_pats = [] # all patterns for one channel reuse distance
        full_inter_pat_groups.append(full_inter_pats)
        for comb in combs:
            inter_pat = full_interference_pattern()
            inter_pat.chnl_reuse_dist = ch_dist.acc_dist
            inter_pat.prob = ch_dist.prob
            inter_pat.thread_cnt = thread_cnt
            full_inter_pats.append(inter_pat)
            # add the corresponding 
            for i in comb:
                inter_pat.threads.append(acc_seqs[i])
                inter_pat.total_accs += acc_seqs[i].total_accs
                inter_pat.prob *= acc_seqs[i].prob
                #print inter_pat_gen.log_full_inter_pat(inter_pat)
            # this pattern is actually corresponding to multiple sequence,
            # count in those sequence
            inter_pat.prob *= compute_comb_count_in_product(comb)

        output = ("Channel-reuse-distance " + str(ch_dist.acc_dist) + 
                  " has interference patterns: " + str(len(full_inter_pats)))
        print output
        # sanity check
        sum_prob += inter_pat_gen.check_full_patterns_sum(full_inter_pats)
        
    # sanity check
    if sum_prob > 1.1 or sum_prob < 0.9:
        output = ("2 Error: probability sum of all patterns is not 1.0, " +
                  "but," + str(sum_prob))
        print output
        exit(1)
        
    return full_inter_pat_groups

# Combinations with replacement, copied from python document at 
# http://docs.python.org/2/library/itertools.html#itertools.combinations_with_replacement
# This is part of the itertools module
def combinations_with_replacement(iterable, r):
    # combinations_with_replacement('ABC', 2) --> AA AB AC BB BC CC
    pool = tuple(iterable)
    n = len(pool)
    if not n and r:
        return
    indices = [0] * r
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != n - 1:
                break
        else:
            return
        indices[i:] = [indices[i] + 1] * (r - i)
        yield  tuple(pool[i] for i in indices)

# This function works on the result of combinations_with_replacement. 
# In function combinations_with_replacement, a result R is a "r"-length 
# combination of elements from the sequence "iterable" with one element can be
# repeated multiple times. 
# Given the same inputs "iterable" and "r", a "r"-length product of the 
# elements of "iterable" can also be generates. 
# For result R, there can be multiple instances of it in the corresponding 
# products. E.g., "iterable" is "0,1,2", and "r" is 3. A result R={0,1,1} 
# corresponds to three products {0,1,1},{1,0,1},{1,1,0}. 
# For a result R, this function computes how many product results are 
# corresponding to it.
# Algorithm: say there are n unique elements. For element i, it repeats m_1
# times in R. Therefore the total number of corresponding products is,
# comb(r, m_1) x comb(r-m_1,m_2) x comb(r-m_1-m_2,m_3)x ... comb(m_n,m_n).
# Intuitively for the first item comb(r,m_1) represents the numbers of ways
# of selecting m_1 slots from the r total slot to put the first element.

def compute_comb_count_in_product(comb_w_r):
    R = list(comb_w_r)
    length = len(R)
    #print R, length
    # count the repeated times for each element
    elements = dict()
    for i in R:
        if i in elements:
            elements[i] += 1
        else:
            elements[i] = 1
    #print elements
    
    count = 1
    for e in elements:
        # compute comb(r - m_1 - ... - m_i, m_i) = comb(length, elements[e])
        count *=  cal_combination(length, elements[e])
        length = length - elements[e]

    return count

# just a simple functions for calculating combination(k, n), select k from n
def cal_combination(n, k):
    return math.factorial(n)/(math.factorial(k) * math.factorial(n-k))

# Generate all possible access sequences for one thread for each channel reuse
# distance.
# Also check out the comments of function gen_acc_seq_v1
def gen_full_acc_seq_1thr_all(thr_info, con_acc_probs, con_noacc_probs, 
                             thread_cnt, min_con_acc, min_con_noacc, debug):

    for ch_dist in thr_info.chnl_reuse_dists:
        acc_seqs = gen_full_acc_seq_1thr(thr_info, ch_dist, 
                                         con_acc_probs,
                                         con_noacc_probs, min_con_acc, 
                                         min_con_noacc, debug)
        output = ("Total number of access sequences of channel reuse " +
                  "distance " + str(ch_dist.acc_dist) + " is " +
                  str(len(acc_seqs)))
        print output

        ch_dist.acc_seqs = acc_seqs

    return
                      
# Generate all possible access sequences for one thread for each channel reuse
# distance using version 3. Check the comments at the beginning of this file.
# Also check out the comments of function gen_acc_seq_v1
def gen_acc_seq_1thr_all_v3(thr_info, con_acc_probs, con_noacc_probs, 
                             thread_cnt, min_con_acc, min_con_noacc, debug):

    for ch_dist in thr_info.chnl_reuse_dists:
        acc_seqs = gen_acc_seq_1thr_v3(thr_info, ch_dist, 
                                       con_acc_probs,
                                       con_noacc_probs, min_con_acc, 
                                       min_con_noacc, debug)

        output = ("Total number of access sequences of channel reuse " +
                  "distance " + str(ch_dist.acc_dist) + " is " +
                  str(len(acc_seqs)))
        print output

        ch_dist.acc_seqs = acc_seqs

    return

# Generate all access sequences for one thread and one reuse distance using 
# version V3. Check the comments at the beginning of this file.
# Check the comments of function gen_acc_seq_v1 for information of inputs and
# outputs.
#
# Return an array of access sequences. Each sequence is an object of class
# accs_one_thread.
#
def gen_acc_seq_1thr_v3(thr_info, ch_dist, con_acc_probs, con_noacc_probs, 
                        min_con_acc, min_con_noacc, debug):

    acc_seqs = [] # this is the array that has all valid access sequences

    # generate all possible [0,1] products. Each product represents an access
    # sequence, 1 means accessing the target channels, 0 means not accessing
    # target channel
    sum_prob = 0.0
    for i in range(ch_dist.acc_dist+1): # i represents the number of accesses 
                                        # hit target channel
        acc_seq = accs_one_thread()
        # generate accesses
        for j in range(i):
            acc = access_status()
            acc_seq.accesses.append(acc)
            acc.same_chnl = True
            acc.prob = thr_info.chnl_prob
        for j in range(i, ch_dist.acc_dist):
            acc = access_status()
            acc_seq.accesses.append(acc)
            acc.same_chnl = False
            acc.prob = 1 - thr_info.chnl_prob
        # sanity check
        if len(acc_seq.accesses) != ch_dist.acc_dist:
            print "There should be", ch_dist.acc_dist, "accesses"
            print "But", len(acc_seq.accesses), "accesses were generated"
            exit(15)
        
        acc_seq.prob = (cal_combination(ch_dist.acc_dist, i) *
                        (thr_info.chnl_prob ** i) *
                        ((1 - thr_info.chnl_prob)**(ch_dist.acc_dist-i)))
        acc_seq.total_accs = i
        sum_prob += acc_seq.prob
        acc_seqs.append(acc_seq)

    if debug:
        for acc_seq in acc_seqs:
            output = log_acc_sequence(acc_seq)
            print output

    # sanity check
    if sum_prob != 1.0:
        print "Erro in V3 acc gen: sum prob is not 1.0, but", sum_prob
        exit(13)

    return acc_seqs

# V3 version as mentioned in the beginning comments. 
# Also check out the comments of function gen_acc_seq_v1
# A key difference between this one the the full version (V1) is that
# I am not going to do deepcopy, rather a link to the sequnce     
def gen_acc_seq_v3_full_comb(thr_info, con_acc_probs, con_noacc_probs, 
                             thread_cnt, min_con_acc, min_con_noacc, debug):

    full_inter_pat_groups = [] # all patterns for all channel reuse distance
    sum_prob = 0.0
    
    # for each channel reuse distance, generate the access sequence for one 
    # thread. Each inter_pat group represents one reduce distance.
    for ch_dist in thr_info.chnl_reuse_dists:
        acc_seqs = ch_dist.acc_seqs
        
        # generate the combinations of different types of access sequence
        combs = list(combinations_with_replacement(range(len(acc_seqs)), 
                                                   thread_cnt-1))

        full_inter_pats = [] # all patterns for one channel reuse distance
        full_inter_pat_groups.append(full_inter_pats)
        for comb in combs:
            inter_pat = full_interference_pattern()
            inter_pat.chnl_reuse_dist = ch_dist.acc_dist
            inter_pat.prob = ch_dist.prob
            inter_pat.thread_cnt = thread_cnt
            full_inter_pats.append(inter_pat)
            # add the corresponding 
            for i in comb:
                inter_pat.threads.append(acc_seqs[i])
                inter_pat.total_accs += acc_seqs[i].total_accs
                inter_pat.prob *= acc_seqs[i].prob
                if debug:
                    print inter_pat_gen.log_full_inter_pat(inter_pat)
            # this pattern is actually corresponding to multiple sequence,
            # count in those sequence
            inter_pat.prob *= compute_comb_count_in_product(comb)

        output = ("Channel-reuse-distance " + str(ch_dist.acc_dist) + 
                  " has interference patterns: " + str(len(full_inter_pats)))
        print output
        # sanity check
        sum_prob += inter_pat_gen.check_full_patterns_sum(full_inter_pats)
        
    # sanity check
    if sum_prob > 1.1 or sum_prob < 0.9:
        output = ("3 Error: probability sum of all patterns is not 1.0, " +
                  "but," + str(sum_prob))
        print output
        exit(1)
        
    return full_inter_pat_groups

# Generate all possible access sequences for one thread for each channel reuse
# distance. Version 4
# Also check out the comments of function gen_acc_seq_v1
def gen_acc_seq_1thr_all_v4(thr_info, con_acc_probs, con_noacc_probs, 
                            thread_cnt, min_con_acc, min_con_noacc, debug):

    for ch_dist in thr_info.chnl_reuse_dists:
        acc_seqs = gen_acc_seq_1thr_v4(thr_info, ch_dist, 
                                         con_acc_probs,
                                         con_noacc_probs, min_con_acc, 
                                         min_con_noacc, debug)

        output = ("Total number of access sequences of channel reuse " +
                  "distance " + str(ch_dist.acc_dist) + " is " +
                  str(len(acc_seqs)))
        print output

        ch_dist.acc_seqs = acc_seqs

    return

# Fully generate the sequences of middle accesses for one thread.
# Check the comments of function gen_acc_seq_v1 for information of inputs and
# outputs.
#
# Return an array of access sequences. Each sequence is an object of class
# accs_one_thread.
#
# This is the same algorithm as the gen_full_acc_seq_1thr
def gen_acc_seq_1thr_v4(thr_info, ch_dist, con_acc_probs, con_noacc_probs, 
                          min_con_acc, min_con_noacc, debug):

    search_q = Queue.Queue()
    root = accs_one_thread() # create root node
    root.accesses = [] # root has no accesses
    search_q.put(root) # add root to the search queue
    acc_seqs = [] # this is the array that has all valid access sequences
    
    # now start breath first search
    sum_prob = 0.0
    while not search_q.empty(): #{
        node = search_q.get()
                
        # generate left child: access target channel
        left = copy.deepcopy(node)
        acc_l = access_status()
        acc_l.same_chnl = True
        left.accesses.append(acc_l)
        
        # generate right child: access other channels
        right = copy.deepcopy(node)
        acc_r = access_status()
        acc_r.same_chnl = False
        right.accesses.append(acc_r)

        # check if left child valid
        left_valid = is_acc_seq_valid_v4(left, thr_info, 
                                      min_con_acc, min_con_noacc)
        # check if right child valid
        right_valid = is_acc_seq_valid_v4(right, thr_info,
                                       min_con_acc, min_con_noacc)
        
        # update the probility of the new access of left child when 
        # right child is not valid
        if left_valid and (not right_valid): 
            acc_l.prob = 1
       
        # update the probility of the new access of right child when
        # left child is not valid
        if right_valid and (not left_valid): 
            acc_r.prob = 1
                   

        if left_valid and len(left.accesses) == ch_dist.acc_dist: 
            # all accesses generate for this sequence
            left = generate_acc_probs_v4(left, thr_info, 
                                      con_acc_probs, con_noacc_probs)
            sum_prob += left.prob
            acc_seqs.append(left)
        elif left_valid:
            search_q.put(left)

        if right_valid and len(right.accesses) == ch_dist.acc_dist: 
            # all accesses generate for this sequence
            right = generate_acc_probs_v4(right, thr_info,
                                       con_acc_probs, con_noacc_probs)
            sum_prob += right.prob
            acc_seqs.append(right)
        elif right_valid: 
            search_q.put(right)
    #}

    if sum_prob != 1.0:
        print "Error in access sequence generate version 4:"
        print "Sum of access sequence probability is not 1.0 but", sum_prob
        exit(16)

    if debug:
        for acc_seq in acc_seqs:
            output = log_acc_sequence(acc_seq)
            print output

    return acc_seqs

# Based on the channel reuse distance, check whether an access sequence is 
# valid. This is similar to function "is_acc_seq_valid", except that the
# min-consecutive-(non)accesses is no checked.
# The check can be done by keeping track of previous accesses, which can 
# save some time. But I am too tired to re-implement the check, copy is the
# best for me at this minute.
def is_acc_seq_valid_v4(acc_seq, thr_info, min_con_acc, min_con_noacc):

    valid = True
    # check the channel reuse distance in this permutation, make sure the
    # the distance is valid
    last_acc_position = -1
    for i in range(len(acc_seq.accesses)):
        if acc_seq.accesses[i].same_chnl == False: # ignore accesses to other 
                                                   # channel
            continue    
        if last_acc_position == -1: # first target channel access in this
            last_acc_position = i   # acc_seq, update last position only
            continue
        reuse_dist = i - last_acc_position
        valid = check_resue_dist(thr_info, reuse_dist)
        if valid == False: # invalid acc_seq, no need to check any more
            break
        last_acc_position = i # valid reuse distance, update last position

    if not valid: # access sequence already invalid
        return valid

    return valid

# generate the probabilities for all accesses in an accesses sequence as well as
# the probability of whole sequence.
# Here, each access is considered individually and independent of previous 
# accesses.
def generate_acc_probs_v4(acc_seq, thr_info, con_acc_probs, con_noacc_probs):
    # make a copy the access sequence
    acc_seq2 = copy.deepcopy(acc_seq)
    acc_seq2.prob = 1.0
    
    con_acc_len = 0 # keep track of the length of the consecutive 1s and 0s
    con_noacc_len = 0
    for i in range(len(acc_seq.accesses)): #{
        acc_stat = acc_seq2.accesses[i]
        chnl = acc_stat.same_chnl
        if chnl == True:
            acc_seq2.total_accs += 1
        if acc_stat.prob == 1: # already has a probability, no need to update
            acc_seq2.prob *= acc_stat.prob
            continue;
        # compute the probability of this access
        if acc_stat.same_chnl == True:
            acc_stat.prob = thr_info.chnl_prob
        else:
            acc_stat.prob = 1 - thr_info.chnl_prob
            
        # update the length of consecutive 1s and 0s
        if acc_stat.same_chnl == True: 
            con_acc_len += 1
            con_noacc_len = 0
        else:
            con_acc_len = 0
            con_noacc_len += 1
                
        # update whole sequence's probability
        acc_seq2.prob *= acc_stat.prob
        #}    

    return acc_seq2        

# Fully generate the sequence of middle accesses. Keep track of every single 
# access. No simplification is made. Version 1 as stated in the beginning
# of this file
# Inputs:
#       thr_info: see thread_info class
#       con_acc_probs: see consecutive_acc_probs class
#       con_noacc_probs: see consecutive_noacc_probs class
#       thread_cnt: how many threads to process
#       min_con_acc: minimum number of consecutive accesses to target channel
#       min_con_noacc: minimum number of consecutive accesses to other channels
#       debug: whether enable debug output or not
# Return:
#       full_inter_pats[]: see full_interference_pattern class
def gen_acc_seq_v1_full(thr_info, con_acc_probs, con_noacc_probs, 
                     thread_cnt, min_con_acc, min_con_noacc, debug):

    full_inter_pat_groups = [] # all patterns for all channel reuse distance
    sum_prob = 0.0
    
    # for each channel reuse distance, generate the access sequence for one 
    # thread
    for ch_dist in thr_info.chnl_reuse_dists:
        acc_seqs = ch_dist.acc_seqs
        
        # generate the interfere patterns for this channel resue distance
        perms = list(itertools.product(range(len(acc_seqs)), 
                                       repeat = (thread_cnt-1)))

        full_inter_pats = [] # all patterns for one channel reuse distance
        full_inter_pat_groups.append(full_inter_pats)
        for perm in perms:
            inter_pat = full_interference_pattern()
            inter_pat.chnl_reuse_dist = ch_dist.acc_dist
            inter_pat.prob = ch_dist.prob
            inter_pat.thread_cnt = thread_cnt
            full_inter_pats.append(inter_pat)
            # add the corresponding 
            for i in perm:
                acc_seq = copy.deepcopy(acc_seqs[i])
                inter_pat.threads.append(acc_seq)
                inter_pat.total_accs += acc_seq.total_accs
                inter_pat.prob *= acc_seq.prob
                #print inter_pat_gen.log_full_inter_pat(inter_pat)

        output = ("Channel-reuse-distance " + str(ch_dist.acc_dist) + 
                  " has interference patterns: " + str(len(full_inter_pats)))
        print output
        # sanity check
        sum_prob += inter_pat_gen.check_full_patterns_sum(full_inter_pats)
        
    # sanity check
    if sum_prob > 1.1 or sum_prob < 0.9:
        output = ("4 Error: probability sum of all patterns is not 1.0, " +
                  "but," + str(sum_prob))
        print output
        exit(1)
        
    return full_inter_pat_groups

#!/usr/bin/python

# This is the second part of the bandwidth prediction model. This file takes the
# HIT/MISS/CONFLICT ratios as inputs and compute the memory latency, i.e., the 
# memory bandwidth.

# Input parameters:
# hit_ratio, miss_ratio, conf_ratio: HIT/MISS/CONF ratios in float
# issue_time: memory latency or issue time of a single thread, in float and in
#             nanoseconds
# thread_cnt: the number of threads to model
# wr_ratio: ratio of the write requests in all DRAM accesses
# max_hit, max_miss, max_conf: maximum time of HIT,MISS,CONFLICT, in memory cycles
#                              and in integer
# cycle_time: how many nanoseconds in a memory cycle, in float and in nanoseconds
# trans_cyc: the cycles used to transport data for a DRAM read
# min_issue_time: minimum issue time due to last level cache access
# rank_cnt: numbers of rank used
# debug: enable debug output
# verbose: enable verbose output
# 
# Return value:
# A dictionary with the following fields:
#      "rd_lat": read latency
#      "wr_lat": write latency
#      "final_lat": final latency
def compute_memory_latency(hit_ratio, 
                           miss_ratio,
                           conf_ratio,
                           issue_time,
                           thread_cnt,
                           wr_ratio,
                           max_hit,
                           max_miss,
                           max_conf,
                           cycle_time,
                           trans_cyc,
                           min_issue_time,
                           tRCD,
			   rank_cnt,
                           debug,
                           verbose):
    if debug:
        print "Options are:"
        print "    Thread count:", thread_cnt
        print "    HIT/MISS/CONFLICT ratios:", hit_ratio, ",",
        print miss_ratio, ",", conf_ratio
        print "    MAX HIT/MISS/CONFLICT cycles:", max_hit, ",", 
        print max_miss, ",", max_conf
        print "    Issue time:", issue_time
        print "    Data transport cycles:", trans_cyc
        print "    Write ratio:", wr_ratio
        print "    Memory cycle time:", cycle_time
        print "    Min issue time:", min_issue_time
        print "    Rank count:", rank_cnt

                           
    # compute the latency for reads
    ideal_issue_time = max(issue_time / thread_cnt, min_issue_time)
    # Reads Step 1: Compute the overlaps between hits, misses and conflicts
    thr_overlap = thread_cnt - 1 # overlap-able writes from other threads
    rank_overlap = rank_cnt * 4 -1 # overlap-able DRAM requests limited by FAW

    # overlapped hits with a miss
    h_2_miss_overlap = min(rank_overlap, hit_ratio/miss_ratio)
    # overlapped misses and conflicts with a miss
    mc_2_miss_overlap = min(rank_overlap, thread_cnt *(miss_ratio+conf_ratio) - 1) 
    # overlapped hits with a conflict
    h_2_conf_overlap = min(rank_overlap, hit_ratio/conf_ratio)
    # overlapped misses and conflicts with a conflict
    mc_2_conf_overlap = min(rank_overlap, thread_cnt *(miss_ratio+conf_ratio) - 1) 

    # Reads Step 2: Compute the overlapped latency
    hit_overlap_cyc = trans_cyc
    if (miss_ratio + conf_ratio) < 0.7:
        # if the misses and conflicts are less than 70%, there are very few
        # overlapped misses / conflicts
        # if there are less than 50%, then it becomes less likely two misses 
        # or conflicts will show side by side. Using 50% is good, however, 
        # due to errors in th ratios prediction, I have to increase it to 70%
        miss_overlap_cyc = max_miss - h_2_miss_overlap * trans_cyc
        conf_overlap_cyc = max_conf - h_2_conf_overlap * trans_cyc
    else:
        miss_overlap_cyc = max_miss - (h_2_miss_overlap + 
                                       mc_2_miss_overlap) * trans_cyc
        conf_overlap_cyc = max_conf - (h_2_conf_overlap + 
                                       mc_2_conf_overlap) * trans_cyc

    if debug:
        print "Read HIT/MISS/CONF cycle:", hit_overlap_cyc, ",",
        print miss_overlap_cyc, ",", conf_overlap_cyc

    # Read Step 3: Compute the actual latency by factor in the issue rate
    #hit_latency = max(hit_overlap_cyc * cycle_time, ideal_issue_time)
    #miss_latency = max(miss_overlap_cyc * cycle_time, ideal_issue_time)
    #conf_latency = max(conf_overlap_cyc * cycle_time, ideal_issue_time)
    hit_latency = hit_overlap_cyc * cycle_time
    miss_latency = miss_overlap_cyc * cycle_time
    conf_latency = conf_overlap_cyc * cycle_time

    if debug:
        print "Read HIT/MISS/CONF latency adjusted after issue rate:", hit_latency, ",",
        print miss_latency, ",", conf_latency

    # Read Step 4: Compute the read latency
    read_latency = (hit_ratio * hit_latency + 
                    miss_ratio * miss_latency + 
                    conf_ratio * conf_latency)
    read_latency = max(read_latency, ideal_issue_time)

    # compute the latency for writes
    ideal_issue_time = max(issue_time / thread_cnt, min_issue_time)
    # Writes Step 1: Increase maximum latencies since write is one cycle longer
    # should be adjusted for different memory configuration
    trans_cyc += 1
    max_hit += 1
    max_miss += 1
    max_conf += 1

    # Write Step 2: Compute the overlapped latency
    hit_overlap_cyc = trans_cyc
    if (miss_ratio + conf_ratio) < 0.7:
        # if the misses and conflicts are less than 70%, there are very few
        # overlapped misses / conflicts
        miss_overlap_cyc = max_miss - h_2_miss_overlap * trans_cyc
        conf_overlap_cyc = max_conf - h_2_conf_overlap * trans_cyc
    else:
        miss_overlap_cyc = max_miss - (h_2_miss_overlap + 
                                       mc_2_miss_overlap) * trans_cyc
        conf_overlap_cyc = max_conf - (h_2_conf_overlap + 
                                       mc_2_conf_overlap) * trans_cyc


    if debug:
        print "Write HIT/MISS/CONF cycle:", hit_overlap_cyc, ",",
        print miss_overlap_cyc, ",", conf_overlap_cyc

    # Writes Step 3: Compute the actual latency by factor in the issue rate
    #hit_latency = max(hit_overlap_cyc * cycle_time, ideal_issue_time)
    #miss_latency = max(miss_overlap_cyc * cycle_time, ideal_issue_time)
    #conf_latency = max(conf_overlap_cyc * cycle_time, ideal_issue_time)
    hit_latency = hit_overlap_cyc * cycle_time
    miss_latency = miss_overlap_cyc * cycle_time
    conf_latency = conf_overlap_cyc * cycle_time

    if debug:
        print "Write HIT/MISS/CONF latency adjusted after issue rate:", hit_latency, ",",
        print miss_latency, ",", conf_latency

    # Writes Step 4: Compute the write latency
    write_latency = (hit_ratio * hit_latency + 
                    miss_ratio * miss_latency + 
                    conf_ratio * conf_latency)
    

    # combine the reads and writes and get the final latency
    read_ratio = 1 - wr_ratio
    final_latency = read_latency * read_ratio + write_latency * wr_ratio

    result = {"wr_lat": write_latency,
              "rd_lat": read_latency,
              "final_lat": final_latency}
    return result

#!/usr/bin/python

# This a model that predicts the hit/miss/confilct ratios of multi-threaded 
# programs. Given a thread A, the model predicts its ratios by considering the 
# two consecutive accesses of A that go to the same channel, as well as the
# memory accesses that generated between these two accesses by other threads.
# This model fully evaluates the status of every memory access that is generated
# by other threads.
#
# Author: Wei Wang (wwang@virginia.edu), University of Virginia
# 


import acc_gen
import inter_pat_gen
import hmc_ratios_gen
from optparse import OptionParser

from mem_model_types import *

from fractions import *

parser = OptionParser()
parser.add_option("-f", "--file", dest="filename", help="Path to the parameter "
                  + "file", metavar="parameterfile")
parser.add_option("-t", "--t", dest="thread_cnt", help="Number of threads to " +
                  "predict", metavar="THREAD_COUNT", type="int")
parser.add_option("-o", "--timeout", dest="timeout", help="Time in nanoseconds "
                  + "before a bank auto-close; 0 means no auto-close", 
                  metavar="TIEMOUT", type="float", default=0.0)
parser.add_option("-r", "--reorder", dest="reorder", help="Maximum timespan " +
                  "allowed for reordering: 0 means no reordering", 
                  metavar="REORDER", type="float", default=0.0)
parser.add_option("-e", "--esttime", dest="est_serv_time", help="Estimated " +
                  "service time for memory request, in nanoseconds", 
                  metavar="EST_TIME", type="float", default=0.0)
parser.add_option("--half", dest="half_reorder", help="Whether " +
                  "half reordered misses/conflicts remains misses/conflicts ", 
                  action="store_true", default=False)
parser.add_option("-s", "--steps", dest="steps", help="The version of " +
                  "each of the four steps; comma separate list of four integers"
                  , metavar="V,V,V,V", type="string")
parser.add_option("-d", "--debug", action="store_true", dest="debug", 
                  default=False, help="Enable debug output")

(options, args) = parser.parse_args()

if options.filename is None:
    print "Please specify the input file"
    parser.print_help()
    exit(-1)

if options.thread_cnt is None:
    print "Please specify the number of threads to model"
    parser.print_help()
    exit(-1)

if options.steps is None:
    print "Please specify the function version of each step"
    parser.print_help()
    exit(-1)

# parse the function versions
steps = [int(n) for n in options.steps.split(',')]
if len(steps) != 4:
    print "Only four function versions are allowed"
    parser.print_help()
    exit(-1)

if options.debug is True:
    print "Options are:"
    print "    input file: ", options.filename
    print "    thread count: ", options.thread_cnt
    print "    reorder time: ", options.reorder
    print "    auto-close time: ", options.timeout 
    print "    estimate service time: ", options.est_serv_time
    print "    half conflict reordering: ", options.half_reorder
    print "    function versions: ", steps
    print "    debug: ", options.debug


# parse the input file
f = open(options.filename, "r")

thr_info = thread_info()
thr_info.autoclose_time = options.timeout
thr_info.reorder_time = options.reorder
thr_info.est_serv_time = options.est_serv_time
thr_info.half_reorder = options.half_reorder

for line in f:
    if line.isspace():
        continue
    elif line.startswith("#"):
        continue
    
    if line.startswith("t:"):
        temp = line.strip("\n").split(":")[1].split(",")
        thr_info.chnl_prob = float(temp[0])
        thr_info.bank_prob = float(temp[1])
        thr_info.row_prob = float(temp[2])
        min_con_acc = int(temp[3])
        min_con_noacc = int(temp[4])
    elif line.startswith("a:"):
        temp = line.strip("\n").split(":")[1].split(",")
        chnl_dist = chnl_reuse_dist_info()
        chnl_dist.acc_dist = int(temp[0])
        chnl_dist.prob = float(temp[1])
        chnl_dist.hit_prob = float(temp[2])
        chnl_dist.miss_prob = float(temp[3])
        chnl_dist.conf_prob = float(temp[4])
        thr_info.chnl_reuse_dists.append(chnl_dist)
    elif line.startswith("ca:"):
        con_acc_probs = consecutive_acc_probs()
        temp = line.strip("\n").split(":")[1].split(",")
        for t in temp:
            vals = t.split("/")
            con_acc_probs.acc_prob.append(Fraction(int(vals[0]),int(vals[1])))
    elif line.startswith("cn:"):
        con_noacc_probs = consecutive_noacc_probs()
        temp = line.strip("\n").split(":")[1].split(",")
        for t in temp:
            vals = t.split("/")
            con_noacc_probs.noacc_prob.append(Fraction(int(vals[0]),
                                                       int(vals[1])))
    elif line.startswith("mt:"):
        temp = line.strip("\n").split(":")
        min_con_acc = int(temp[1])
    elif line.startswith("mn:"):
        temp = line.strip("\n").split(":")
        min_con_noacc = int(temp[1])
    else:
        print "Unknown line form input file:", line
        exit(-1)

# print inputs from the configure file
if options.debug:
    print "Inputs from configuration file:"
    print "    Thread info, chnl_prob:", thr_info.chnl_prob
    print "    Thread info, bank_prob:", thr_info.bank_prob 
    print "    Thread info, row_prob:", thr_info.row_prob
    print "    Thread info, reorder time:", thr_info.reorder_time
    print "    Thread info, auto-close:", thr_info.autoclose_time
    print "    Thread info, est. time:", thr_info.est_serv_time
    print "    Thread info, half_reorder:", thr_info.half_reorder
    for chnl_dist in thr_info.chnl_reuse_dists:
        print "    Channel reuse dist", chnl_dist.acc_dist
        print "        prob:", chnl_dist.prob
        print "        hit_prob:", chnl_dist.hit_prob
        print "        miss_prob:", chnl_dist.miss_prob
        print "        conf_prob:", chnl_dist.conf_prob
    print "    Con-acc-probs:", con_acc_probs.acc_prob
    print "    Con-noacc-probs:", con_noacc_probs.noacc_prob
    print "    min_con_acc:", min_con_acc
    print "    min_con_noacc:", min_con_noacc

thread_cnt = options.thread_cnt
debug = options.debug

#if (steps[0] == 1) and (steps[1] == 1) and (steps[2] == 1) and (steps[3] == 1):
    # full version of the algorithm 
#    inter_pat_groups = acc_gen.gen_acc_seq_v1(thr_info, con_acc_probs, 
#                                            con_noacc_probs, thread_cnt, 
#                                            min_con_acc, min_con_noacc, debug)

#    hmc = inter_pat_gen.gen_acc_stat_all(inter_pat_groups, thr_info)
#else:
print "Step 1"
# step 1
if (steps[0] == 1) or (steps[0] == 2):
    acc_gen.gen_full_acc_seq_1thr_all(thr_info, con_acc_probs, 
                                      con_noacc_probs, thread_cnt, 
                                      min_con_acc, min_con_noacc, debug)
elif (steps[0] == 3):
    acc_gen.gen_acc_seq_1thr_all_v3(thr_info, con_acc_probs, 
                                    con_noacc_probs, 
                                    thread_cnt, min_con_acc, min_con_noacc, 
                                    debug)
elif(steps[0] == 4):
    acc_gen.gen_acc_seq_1thr_all_v4(thr_info, con_acc_probs, 
                                    con_noacc_probs, thread_cnt, 
                                    min_con_acc, min_con_noacc, debug)
else:
    print "Unknown step 1 function version:", steps[0]
    exit(61)
    
# step 2
print "Step 2"
if (steps[1] == 1) or (steps[1] == 2):
    inter_pat_gen.gen_acc_seq_stats_all(thr_info, debug)
elif (steps[1] == 3):
    inter_pat_gen.gen_acc_seq_stats_all_v3(thr_info, debug)
else:
    print "Unknown step 2 function version:", steps[1]
    exit(61)

# step 3
print "Step 3"
if (steps[2] == 1):
    inter_pat_groups = acc_gen.gen_acc_seq_v1_full(thr_info, 
                                                   con_acc_probs, 
                                                   con_noacc_probs, 
                                                   thread_cnt,
                                                   min_con_acc, 
                                                   min_con_noacc,
                                                   debug)
elif (steps[2] == 2):
    inter_pat_groups = acc_gen.gen_acc_seq_v2_full_comb(thr_info, 
                                                        con_acc_probs, 
                                                        con_noacc_probs, 
                                                        thread_cnt,
                                                        min_con_acc, 
                                                        min_con_noacc,
                                                        debug)
elif (steps[2] == 3):
    inter_pat_groups = acc_gen.gen_acc_seq_v3_full_comb(thr_info, 
                                                        con_acc_probs, 
                                                        con_noacc_probs, 
                                                        thread_cnt,
                                                        min_con_acc, 
                                                        min_con_noacc,
                                                        debug)
else:
    print "Unknown step 3 function version:", steps[2]
    exit(61)

# step 4
print "Step 4"
if (steps[3] == 2):
    hmc = hmc_ratios_gen.gen_hmc_v2_all_inter_pat_group(inter_pat_groups, 
                                                        thr_info, debug)
elif (steps[3] == 3):
    hmc = hmc_ratios_gen.gen_hmc_v3_all_inter_pat_group(inter_pat_groups, 
                                                        thr_info, debug)
elif (steps[3] == 1):
    hmc = hmc_ratios_gen.gen_hmc_v1_all_inter_pat_group(inter_pat_groups, 
                                                        thr_info, debug)
else:
    print "Unknown step 4 function version:", steps[3]
    exit(61)


print "Final hit/miss/conflict:", hmc.hit, hmc.miss, hmc.conflict

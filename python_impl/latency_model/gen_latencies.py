#!/usr/bin/python

# This is the second part of the bandwidth prediction model. This file takes the
# HIT/MISS/CONFLICT ratios as inputs and compute the memory latency, i.e., the
# memory bandwidth.

from optparse import OptionParser
import latency_model


parser = OptionParser()
parser.add_option("-t", "--thr_cnt", dest="thread_cnt", help="Number of " + 
                  "threads to predict", metavar="THREAD_COUNT", type="int")
parser.add_option("-r", "--hits", dest="hit_ratio", help="Ratio of row buffer" +
                  "hits", metavar="HIT_RATIO", type="float")
parser.add_option("-m", "--misses", dest="miss_ratio", help="Ratio of row " +
                  "buffer misses", metavar="MISS_RATIO", type="float")
parser.add_option("-c", "--conflicts", dest="conf_ratio", help="Ratio of row " +
                  "buffer conflicts", metavar="CONF_RATIO", type="float")
parser.add_option("--max_hit", dest="max_hit", help="Maximum memory cycles " +
                  "to serve a row buffer hit; default 13",
                  metavar="MAX_HIT_TIME", type="int", default=13)
parser.add_option("--max_miss", dest="max_miss", help="Maximum memory cycles " +
                  "to serve a row buffer miss; default 22",
                  metavar="MAX_MISS_TIME", type="int", default=22)
parser.add_option("--max_conf", dest="max_conf", help="Maximum memory cycles " +
                  "to serve a row buffer conflict; default 31",
                  metavar="MAX_CONF_TIME", type="int", default=31)
parser.add_option("--trans", dest="trans_cyc", help="Data transportation"+
                  " time (in memory cycles) for one memory read; default 4",
                  metavar="TRANS_CYCLES", type="int", default=4)
parser.add_option("--tRCD", dest="tRCD", help="tRCD, row to column delay, "+
                  ", in memory cycles, and default is 9",
                  metavar="TRANS_CYCLES", type="int", default=9)
parser.add_option("-w", "--writes", dest="wr_ratio", help="Ratio of " +
                  "DRAM writes; default 0", metavar="WR_RATIO", type="float",
                  default=0.0)
parser.add_option("-i", "--issue_time", dest="issue_time", help="Memory " +
                  "issue time for a single thread; in nanoseconds",
                  metavar="ISSUE_TIME", type="float")
parser.add_option("--cycle_time", dest="cycle_time", help="The memory " +
                  "cycle time in nanoseconds; default 1.5ns",
                  metavar="CYCLE_TIEM", type="float", default=1.5)
parser.add_option("--min_time", dest="min_issue_time", help="Miminum issue " +
                  "time due to L3 cache access; default 6.5ns",
                  metavar="MIN_ISSUE_TIME", type="float", default=6.5)
parser.add_option("--rank", dest="rank_cnt", help="Number of ranks"+
                  "simultaneously accessed",
                  metavar="RANK_CNT", type="int", default=1)
parser.add_option("-d", "--debug", action="store_true", dest="debug",
                  default=False, help="Enable debug output")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                  default=False, help="Enable verbose output")

(options, args) = parser.parse_args()

if options.thread_cnt is None:
    print "Please specify the number of threads to model"
    parser.print_help()
    exit(-1)

if options.hit_ratio is None:
    print "Please specify the hit ratio"
    parser.print_help()
    exit(-1)

if options.miss_ratio is None:
    print "Please specify the miss ratio"
    parser.print_help()
    exit(-1)

if options.conf_ratio is None:
    print "Please specify the conflict ratio"
    parser.print_help()
    exit(-1)

if options.issue_time is None:
    print "Please specify the issue time of a single thread."
    parser.print_help()
    exit(-1)


if options.debug is True:
    print "Options are:"
    print "    Thread count:", options.thread_cnt
    print "    HIT/MISS/CONFLICT ratios:", options.hit_ratio, ",",
    print options.miss_ratio, ",", options.conf_ratio
    print "    MAX HIT/MISS/CONFLICT cycles:", options.max_hit, ",",
    print options.max_miss, ",", options.max_conf
    print "    Issue time:", options.issue_time
    print "    Data transport cycles:", options.trans_cyc
    print "    tRCD:", options.tRCD
    print "    Write ratio:", options.wr_ratio
    print "    Memory cycle time:", options.cycle_time
    print "    Min issue time:", options.min_issue_time
    print "    Rank Count:", options.rank_cnt

result = latency_model.compute_memory_latency(options.hit_ratio,
                                              options.miss_ratio,
                                              options.conf_ratio,
                                              options.issue_time,
                                              options.thread_cnt,
                                              options.wr_ratio,
                                              options.max_hit,
                                              options.max_miss,
                                              options.max_conf,
                                              options.cycle_time,
                                              options.trans_cyc,
                                              options.min_issue_time,
                                              options.tRCD,
                                              options.rank_cnt,
                                              options.debug,
                                              options.verbose)

print "Read latency:", result["rd_lat"],
print ", Write latency:", result["wr_lat"],
print ", Final latency:", result["final_lat"]

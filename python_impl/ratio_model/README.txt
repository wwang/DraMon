This directory contains files of the hit/miss/conflict (HMC) ratios prediction 
part of the DraMon model. 

The "run_model.py" file is the user-interface, while the other python files 
include functions that computes the model. Run "run_model.py" with --help to 
get information about how to use the model, i.e., passing parameters.

The HMC ratio model is in four steps:
1. The first step generates the requests issued form one co-running thread 
   which hit the channel that we are predicting. 
2. The second step generates the destination of these requests, i.e. whether 
   they are the Same-Bank request or Same-Rank-Diff-Row, or 
   Diff-Bank-Same-Channel.
3. The third step repeats the first two step for all co-running threads, and
   generate cases (as described in the paper). As an optimization, I reused 
   results from step 1 and step 2.
4. Process the cases, to determine whether a case is a hit, miss or conflict. 
   Also compute the probability of the cases, and sum the probabilities up.

Different from the paper, I have several versions of implementation for each
steps. Different versions have different assumptions. The lowest version, 
ver. 1, is the most detailed version, takes more parameters and considers more
cases. Version 1 is also the slowest one. 

Version 3 is the one presented in the paper. Therefore, to repeat the results in
the paper, please pass "-s 3,3,3,3" to the "run_model.py" script. 

Parameters "TIMEOUT", "REORDER" and "EST_TIME" controls the behavior of the 
memory controller, i.e., when will the memory controller closes the row buffer 
automatically. These three parameters corresponds to the "Dac" parameter in the
paper. To set "Dac" to 4 as in the paper, use "40", "40" and "10" for "TIMEOUT", 
"REORDER" and "EST_TIME". If a 4 "Dac" is not good, you should change these 
parameters to correct values that represent the memory system you are using.

Parameter "--half" means only half of the conflicts or misses, which may be
converted to hits by the memory controller with reordering, can be converted to
hits. In the paper, I didn't enable this flag. However, I do notice that 
enabling this flag can increase the accuracy in some cases, which reason is
unknown to me.

The rest parameters, such as bank reuse distances, single thread HMC ratios, 
are passed in the parameter file. The file name is passed to run_model.py with
"-f". 

"parameters.txt" is an example parameter files. It has more parameters 
than the paper. The extra parameters are used by version 1 of the four steps,
you don't have to set these parameters, if you are using version 3.

This python implemenation should be fast. I have been running all my python 
scripts with pypy, which is faster than standard python. If the scripts are 
slow for you, try pypy.

#!/usr/bin/python

# This file translate a virtual address to dram address 
# in terms of node, channel, rank, bank, row and column.
# Usage:
#    <this command> --help
#
# Author: Wei Wang <wwang@virginia.edu>
#

from optparse import OptionParser
import resource
import subprocess

import virtual2physical
import physical2dram

# This function parse a string which represents memory
# size such as "xxB", "xxK", "xxKB" ... "xxGB"
# Parameters:
#     str memsize: the memory size string
# Return:
#     int size: memory size in bytes
def parseMemSize( memsize):
    strLen = len(memsize)
    lastChar = memsize[strLen-1]

    if lastChar == 'B':
        lastChar = memsize[strLen - 2]
        memsize = memsize[:-1]
    
    if lastChar == 'G':
        unit = 1024*1024*1024
        memsize = memsize[:-1]
    elif lastChar == 'M':
        unit = 1024*1024
        memsize = memsize[:-1]
    elif lastChar == 'K':
        unit = 1024
        memsize = memsize[:-1]
    else:
        unit = 1

    try:
        size = int(memsize,10) * unit
        return size
    except ValueError:
        return -1

# Here comes the real program

# define commandline parameters
parser = OptionParser()
parser.add_option("-p", "--pid", dest="pid", help="The process id of the virtual address", metavar="pid")
parser.add_option("-a", "--addr", dest="addr", help="The virtual address in hex format, max 64bits", metavar="0xXXXXXXXXXXXXX")
parser.add_option("-s", "--pagesize",  dest="pagesize", help="OS page size in B, KB or GB, if you know it; if not specified, OS default will be used", metavar="pagesize")
parser.add_option("-d", "--debug", action="store_true", dest="debug", default=False, help="Enable debug output")
parser.add_option("--v2p", action="store_true", dest="v2ponly", default=False, help="Only translate virtual address to physical address")
parser.add_option("--p2d", action="store_true", dest="p2donly", default=False, help="Only translate physical address to dram address")
parser.add_option("-m", "--memsize", dest="memsize", help="translate the whole memory region of with size MemSize, value in B, KB, MB or GB", metavar="MemSize")
parser.add_option("--step", dest="step", help="go over the memory region with setp STEP, value in B, KB, MB or GB; default 64B", metavar="STEP")
parser.add_option("--cache_pci", action="store_true", dest="cache_pci", 
                  default=False, help="Whether to cache PCI configuartion" + 
                  "registers; relatively a safe optimization")
parser.add_option("--cache_pagemap", action="store_true", dest="cache_pagemap", 
                  default=False, help="Whether to cache page map; relatviely" +
                  "a safe optimiation; maybe unsafe if a page gets swapped out")

(options, args) = parser.parse_args()

# parse commandline parameters
if options.addr is None:
    print "No address to translate\n"
    parser.print_help()
    exit(-1)
else:
    startAddr = int(options.addr, 16)

if options.p2donly is False:
    if options.pid is None:
        print "You need to tell me which process this address belongs to\n"
        parser.print_help()
        exit(-1)
    else:
        pid = int(options.pid)
else:
    pid = 0

if options.debug is True:
    virtual2physical.debug = True
    physical2dram.debug = True;

if options.pagesize is None:
    pagesize = 0
else:
    pagesize = parseMemSize(options.pagesize)
    if pagesize == -1:
        print "Page size must be a number that ends with B, K, KB, M, MB, G or GB"
        exit(-1)

if options.memsize is None:
    memsize = 0
else:
    memsize = parseMemSize(options.memsize)
    if pagesize == -1:
        print "Memory region size must be a number that ends with B, K, KB, M, MB, G or GB"
        exit(-1)

if options.step is None:
    step = 64
else:
    step = parseMemSize(options.step)
    if pagesize == -1:
        print "STEP size must be a number that ends with B, K, KB, M, MB, G or GB"
        exit(-1)

if options.debug is True:
    print "Commandline parameters: addr:", hex(startAddr), ", pid:", pid, ", pagesize:", pagesize, ", memsize:", memsize, ", step:", step, ", v2p:", options.v2ponly, ", p2d:", options.p2donly

# generate the array of addresses to parse
addrs = [startAddr]
EndAddr = startAddr + memsize
p = startAddr + step
while p < EndAddr:
    addrs.append(p)
    p += step

if options.p2donly is False:
    phyaddrs = []
    for addr in addrs:
        phyaddr = virtual2physical.virtual2physical(pid, addr, pagesize, 
                                                    options.cache_pagemap)
        phyaddrs.append(phyaddr)
else:
    phyaddrs = addrs

if options.v2ponly is False:
    ramaddrs = []
    # lspci, and find the right PCI domains, buses, slots and functions for address map and dram controller
    lspcicmd = subprocess.Popen("lspci", stdout=subprocess.PIPE)
    lspciout, lspcierr = lspcicmd.communicate()
    
    lspciouts = lspciout.split('\n')
    nodes = [] # a list of all MCTs/nodes
    
    # process the output of "lspci", and collect the PCI for each node
    for line in lspciouts:
        if "DRAM Controller" in line:
            pciaddr = line.split(' ')[0]
            bus = int(pciaddr.split(':')[0], 16)
            slot = int(pciaddr.split(':')[1].split('.')[0], 16)
            node = (bus, slot)
            nodes.append(node)
            if options.debug is True:
                print "Find one memory controller/node at PCI address: 0000:" + hex(bus)[2:].zfill(2) + ":" + hex(slot)[2:].zfill(2)

    for phyaddr in phyaddrs:
        ramaddr = physical2dram.physical2dram(phyaddr, nodes, options.cache_pci)
        ramaddrs.append(ramaddr)

if options.v2ponly is True:
    for i in range(len(addrs)):
        if i != 0:
            vdist = addrs[i] - addrs[i-1]
            pdist = phyaddrs[i] - phyaddrs[i-1]
        else:
            vdist = 0
            pdist = 0
        print hex(addrs[i]), hex(phyaddrs[i]), vdist, pdist, hex(pdist)
elif options.p2donly is True:
    print "#PhysicalAddr", ",Node", ",Channel", ",Rank", ",Bank", ",Row", ",Col"
    for i in range(len(phyaddrs)):
        print hex(phyaddrs[i]) + "," + str(ramaddrs[i]['Node']) + "," + str(ramaddrs[i]['Channel']) + "," + str(ramaddrs[i]['Rank']) + "," + str(ramaddrs[i]['Bank']) + "," + str(ramaddrs[i]['Row']) + "," + str(ramaddrs[i]['Col'])
else:
    print "#VirtualAddr", ",PhysicalAddr", ",Node", ",Channel", ",Rank", ",Bank", ",Row", ",Col"
    for i in range(len(phyaddrs)):
        print hex(addrs[i]) + "," + hex(phyaddrs[i]) + "," + str(ramaddrs[i]['Node']) + "," + str(ramaddrs[i]['Channel']) + "," + str(ramaddrs[i]['Rank']) + "," + str(ramaddrs[i]['Bank']) + "," + str(ramaddrs[i]['Row']) + "," + str(ramaddrs[i]['Col'])

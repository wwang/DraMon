#!/usr/bin/python

# This file provides functions for translating physical address into
# dram address as node, channel, rank, bank, row and column
# Note this is for AMD family 10h processors, only tested on Opteron 6174
#
# Author: Wei Wang <wwang@virginia.edu>
#

from optparse import OptionParser
import resource
import subprocess

import pciconfig

debug = False
version = "0.1"

# This function removes masked bit (as specified by [mask]) from [addr]
# If mask's ith bit is 0, then the ith bit is removed from addr
# The return value is the address
def removeMaskedBits( addr, mask):
    addr_str = bin(addr)[2:]
    mask_str = bin(mask)[2:]
    
    #print "addr", addr_str, "mask", mask_str
    addr_str = addr_str[::-1]
    mask_str = mask_str[::-1]
    addr_len = min(len(addr_str), len(mask_str))
    addr_out_str = ""
    for i in range(addr_len):
        #print addr_str[i], mask_str[i]
        if mask_str[i] == '1':
            addr_out_str = addr_out_str + addr_str[i]
            
    #print "addr", addr_out_str[::-1]
    addr_out = int(addr_out_str[::-1], 2)
    #print "addr", hex(addr_out)
    return addr_out

def removeMaskedBitsV2(addr, mask):
    
    addr_out = 0
    i = 0
    
    #print "old addr", bin(addr), "mask", bin(mask)
    while addr != 0:
        if (mask & 0x1) == 1:
            last_bit = addr & 0x1
            last_bit = last_bit << i
            addr_out = last_bit | addr_out
            i = i + 1
        addr = addr >> 1
        mask = mask >> 1

    #print "new addr", bin(addr_out)

    return addr_out

# This function translates physical address into dram address as node, channel, rank,
# bank, row and column.
# Parameters:
#     int phyaddr: the physical address to translate
#     int nodes: the PCI address for each nodes
# Return value:
#     A dictionary with the follwing fields:
#          Node, Channel, Rank, Bank, Row, and Col
# Note this is for AMD family 10h processors, only tested on Opteron 6174
# This algorithm is mostly taken directly from AMD BKDG for 10h processors
def physical2dram( phyaddr, nodes, cache_pci):
#configData = pciconfig.getPCIConfig(0x0, 0x0, 0x18, 0x1, 0x110)
#print hex(configData)

    if debug is True:
        print "Translating physcial address: ", hex(phyaddr)
        
    pciconfig.debug = debug

    # lspci, and find the right PCI domains, buses, slots and functions for address map and dram controller
    if nodes == None:
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
                if debug is True:
                    print "Find one memory controller/node at PCI address: 0000:" + hex(bus)[2:].zfill(2) + ":" + hex(slot)[2:].zfill(2)

    CSFound = False
    NodeFound = False
    for i in range(len(nodes)):
        node = nodes[i]
        
        # get the base memory address for this memory controller
        # check "AMD family 10h Processor BKDG" for description of related PCI configration registers
        F1Offset = 0x40 + (i << 3)
        DramBaseLow = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x1, 
                                             F1Offset, cache_pci)
        DramEn = DramBaseLow & 0x00000003
        IntlvEn = (DramBaseLow & 0x00000700) >> 8
        DramBaseLow = DramBaseLow & 0xFFFF0000
        DramBaseHigh = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x1, 
                                              F1Offset + 0x100, cache_pci)
        DramBaseHigh = DramBaseHigh & 0xFF
        DramBaseLong = ((DramBaseHigh << 32) + DramBaseLow) << 8
        
        # get the memory address limit for this memory controller
        DramLimitLow = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x1, 
                                              F1Offset + 0x4, cache_pci)
        NodeID = DramLimitLow & 0x00000007
        IntlvSel = (DramLimitLow & 0x00000700) >> 8
        DramLimitLow = DramLimitLow | 0x0000FFFF
        DramLimitHigh = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x1, 
                                               F1Offset + 0x104, cache_pci)
        DramLimitHigh = DramLimitHigh & 0xFF
        DramLimitLong = (((DramLimitHigh << 32) + DramLimitLow) << 8) | 0xFF

        if debug is True:
            print "Node " + str(NodeID) + ": base memory address: " + hex(DramBaseLong) + ", memory limit: ", hex(DramLimitLong)

        # get the memory hole address for this memory controller
        HoleEn = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x1, 0xF0, 
                                        cache_pci)
        HoleOffset = HoleEn & 0x0000FF80
        HoleEn = HoleEn & 0x00000003
        if debug is True:
            print "Node " + str(NodeID) + ":  memory hole enabled: " + hex(HoleEn) + ", memory hole offset: ", hex(HoleOffset)

        
        # now lets check whether the physical address belongs to this memory controller/node
        if (DramEn != 0x0) and (DramBaseLong <= phyaddr) and (phyaddr <= DramLimitLong):
            NodeFound = True

            if debug is True:
                print "Physical address " + hex(phyaddr) + " belongs to node " + str(NodeID)
            
            # check node interleaving
            if (IntlvEn == 0x0) or (IntlvSel == ((phyaddr >> 12) & IntlvEn)):
                if IntlvEn == 1:
                    Ilog = 1
                elif IntlvEn == 3:
                    Ilog = 2
                elif IntlvEn == 7:
                    Ilog = 7
                else:
                    Ilog = 0
                    
            #if debug is True:
            #    print "Ilog is", Ilog

            # modified the physical address based on "swap interleaved region"
            Temp = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x2, 0x10C, 
                                          cache_pci)
            IntLvRgnSwapEn = Temp & 0x1
            if IntLvRgnSwapEn != 0:
                IntLvRgnBaseAddr = (Temp >> 3) & 0x7F
                IntLvRgnLmtAddr = (Temp >> 11) & 0x7F
                IntLvRgnSize = (Temp >> 20) & 0x7F
                if ((phyaddr >> 34) == 0) and (((phyaddr >> 27) >= IntLvRgnBaseAddr) and ((phyaddr >> 27) <= IntLvRgnLmtAddr) or ((phyaddr >> 27) < IntLvRgnSize)):
                   phyaddr = phyaddr ^ (IntLvRgnBaseAddr << 27)
            if debug is True:
                print "Physical address after \"swap interleaved region\" is", hex(phyaddr)
            # end of "swap interleaved region"

            # determine which channel (dram controller or DCT) to use (dual-channel here)
            Temp = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x2, 0x110,
                                          cache_pci)
            DctSelHiRngEn = Temp & 1
            DctSelHi = (Temp >> 1) & 1
            DctSelIntLvEn = Temp & 4
            DctGangEn = Temp & 0x10
            DctSelIntLvAddr = (Temp >> 6) & 3
            DctSelBaseAddr = Temp & 0xFFFFF800
            DctSelBaseOffsetLong = (pciconfig.getPCIConfig(0x0, node[0], 
                                                           node[1], 0x2, 0x114,
                                                           cache_pci) 
                                    & 0xFFFFFC00) << 16
            
            if debug is True:
                print "DCT_select_high_enabled is", DctSelHiRngEn, ", DCT_high_range_DCT is", DctSelHi, ", DCT_interleave_enabled is", DctSelIntLvEn
                print "DCT_is_ganged is", DctGangEn, ", Dct_channel_interleave_bits are", bin(DctSelIntLvAddr), ", Dct_high_addr_bits are", hex(DctSelBaseAddr)
                print "Dct_base_address is", hex(DctSelBaseOffsetLong)

            # determine if high range is selected
            if (DctSelHiRngEn !=0) and (DctGangEn == 0) and ((phyaddr >> 27) >= (DctSelBaseAddr >> 11)):
                HiRangeSelected = True
            else:
                HiRangeSelected = False
            
            if debug is True:
                print "DCT high ranged selected is", HiRangeSelected

            # now, let's really determine which channel to use
            if (DctGangEn != 0):
                ChannelSelect = 0
            elif HiRangeSelected is True:
                ChannelSelect = DctSelHi
            elif (DctSelIntLvEn != 0) and (DctSelIntLvAddr == 0):
                ChannelSelect = (phyaddr >> 6) & 1;
            elif (DctSelIntLvEn != 0) and ( ((DctSelIntLvAddr>>1)&1) != 0):
                fivebits = (phyaddr >> 16) & 0x1F
                bit0 = fivebits & 0x1
                bit1 = (fivebits>>1) & 0x1
                bit2 = (fivebits>>2) & 0x1
                bit3 = (fivebits>>3) & 0x1
                bit4 = (fivebits>>4) & 0x1
                temp = (bit0 ^ bit1 ^ bit2 ^ bit3 ^ bit4) & 0x1
                if ((DctSelIntLvAddr & 1) != 0):
                    ChannelSelect = (((phyaddr>>9) & 0x1) ^ temp) & 0x1
                else:
                    ChannelSelect = (((phyaddr>>6) & 0x1) ^ temp ) & 0x1
            elif (DctSelIntLvEn != 0) and ((IntLvEn & 4) != 0):
                ChannelSelect = (phyaddr>>15) & 0x1
            elif (DctSelIntLvEn != 0) and ((IntLvEn & 2) != 0):
                ChannelSelect = (phyaddr>>14) & 0x1
            elif (DctSelIntLvEn != 0) and ((IntLvEn & 1) != 0):
                ChannelSelect = (phyaddr>>13) & 0x1
            elif (DctSelIntLvEn != 0):
                ChannelSelect = (phyaddr>>12) & 0x1
            elif (DctSelHiRngEn != 0) and (DctGangEn == 0):
                ChannelSelect = ~DctSelHi & 0x1
            else:
                ChannelSelect = 0
            if debug is True:
                print "Channel is", ChannelSelect

            # determine base address offset to use
            if HiRangeSelected is True:
                if ((DctSelBaseAddr & 0xFFFF0000) == 0) and ((HoleEn & 1) != 0) and (phyaddr >= 0x100000000):
                    ChannelOffsetLong = HoleOffset << 16
                else:
                    ChannelOffsetLong = DctSelBaseOffsetLong
            else:
                if ((HoleEn & 1) != 0) and (phyaddr >= 0x100000000):
                    ChannelOffsetLong = HoleOffset << 16
                else:
                    ChannelOffsetLong = DramBaseLong & 0xFFFFF8000000
            if debug is True:
                print "Channel base address offset is", hex(ChannelOffsetLong)

            # remove hoisting offset and normalize to dram bus addresses
            ChannelAddrLong = (phyaddr & 0x0000FFFFFFFFFFC0) - (ChannelOffsetLong & 0x0000FFFFFF800000)
            # remove node ID (in case of processor interleaving)
            Temp = ChannelAddrLong & 0xFC0
            ChannelAddrLong = ((ChannelAddrLong >> Ilog) & 0xFFFFFFFFF000) | Temp
            # remove channel interleave and hash
            if (DctSelIntLvEn != 0) and (HiRangeSelected == 0) and (DctGangEn == 0):
                if ((DctSelIntLvAddr & 1) != 1):
                    ChannelAddrLong = (ChannelAddrLong >> 1) & 0xFFFFFFFFFFFFFFC0
                elif (DctSelIntLvAddr == 1):
                    Temp = ChannelAddrLong & 0xFC0
                    ChannelAddrLong = ((ChannelAddrLong & 0xFFFFFFFFFFFFE000) >> 1) | Temp
                else: #ChannelAddrLong == 0b11
                    Temp = ChannelAddrLong & 0x1C0
                    ChannelAddrLong = ((ChannelAddrLong & 0xFFFFFFFFFFFFFC00) >> 1) | Temp
            if debug is True:
                print "Physical address ", hex(phyaddr), "normalized to DCT bus address", hex(ChannelAddrLong)
            
            # end channel determination
            
            # select the chip(rank)
            InputAddr = ChannelAddrLong >> 8
            
            for CS in range(0,8):
                F2Offset = 0x40 + (CS << 2)
                if ((CS % 2) == 0):
                    F2MaskOffset = 0x60 + (CS << 1)
                else:
                    F2MaskOffset = 0x60 + ((CS-1) << 1)
                
                if (ChannelSelect == 1):
                    F2Offset = F2Offset + 0x100
                    F2MaskOffset = F2MaskOffset + 0x100
                    
                CSBase = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x2, 
                                                F2Offset, cache_pci)
                CSEn = CSBase & 0x00000001
                CSBase = CSBase & 0x1FF83FE0
                CSMask = pciconfig.getPCIConfig(0x0, node[0], node[1], 0x2, 
                                                F2MaskOffset, cache_pci)
                CSMask = (CSMask | 0x0007C01F) & 0x1FFFFFFF

                if debug is True:
                    print "Rank ", CS, ": CSBase is", hex(CSBase<<8), "(" + str((CSBase<<8)/(1024*1024)) + "MB)", ", CSMask is", hex(CSMask)
                
                if (CSEn != 0) and ((InputAddr & ~CSMask) == (CSBase & ~CSMask)):
                    CSFound = 1
                    OnlineSpareCTL = pciconfig.getPCIConfig(0x0, node[0], 
                                                            node[1], 0x3, 0xB0,
                                                            cache_pci)
                    if ChannelSelect == 1:
                        SwapDone = (OnlineSpareCTL >> 3) & 0x00000001
                        BadDramCS = (OnlineSpareCTL >> 8) & 0x00000007
                        if (SwapDone != 0) and (CS == BadDramCS):
                            print "Need channel 1 (DCT1) online spare chip/rank"
                    else:
                        SwapDone = (OnlineSpareCTL >> 1) & 0x00000001
                        BadDramCS = (OnlineSpareCTL >> 4) & 0x00000007
                        if (SwapDone != 0) and (CS == BadDramCS):
                            print "Need channel 0 (DCT1) online spare chip/rank"

                    # Let parse the normalized address and get the bank, row and col
                    # first, remove masked bits and get normalized address for this rank
                    rankaddr = removeMaskedBitsV2(ChannelAddrLong, (CSMask<<8)|0xff)
                    if debug is True:
                        print "Rank normalized address is", hex(rankaddr)
                    # second, lets get the DRAM address map
                    # Note that I am only reading the DIMM slot 0 here. The 
                    # other slots are configured at higher bits of the same
                    # PCI register (0x80 and 0x180).
                    DramAddrMapOffset = 0x80
                    if ChannelSelect == 1:
                        DramAddrMapOffset = DramAddrMapOffset + 0x100
                    DramAddrMap = pciconfig.getPCIConfig(0x0, node[0], node[1], 
                                                         0x2, DramAddrMapOffset,
                                                         cache_pci)
                    DramAddrMap = DramAddrMap & 0xf
                    if debug is True:
                        print "DramAddrMap is", bin(DramAddrMap)
                    if DramAddrMap == 0b111:
                        bank = rankaddr>>13 & 0b111
                        row = (((rankaddr>>16) & 0b11) << 13) | ((rankaddr>>18) & 0x1FFF)
                        col = (rankaddr>>3) & 0x3FF
                    else:
                        print "Other Dram Address Map is not implemented yet."
                        
                    break

            # since we have found the dram configuration, we can leave now
            break

    if NodeFound is False:
        print "Strange, physical address" , hex(phyaddr), "belongs to no node!"
        ramaddr = {'Node': 0, 'Channel': 0, 'Rank': 0, 'Bank': 0, 'Row': 0, 'Col':0}
    else:
        #print "Physical address", hex(phyaddr), ": node", NodeID, ", channel", ChannelSelect, ", rank", CS, ", bank", bank, ", row", row, ", col", col
        ramaddr = {'Node': NodeID, 'Channel': ChannelSelect, 'Rank': CS, 'Bank': bank, 'Row': row, 'Col':col}
    return ramaddr
                
            
            
        



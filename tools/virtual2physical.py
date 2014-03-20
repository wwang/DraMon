#!/usr/bin/python

# This file provides functions for translating a virtual address into physical address
#
# Author: Wei Wang <wwang@virginia.edu>
#

import resource

version = '0.1'
debug = False

# Keep a cache of read values to improve performance
pagemap_cache = dict()


# This function translates a virtual address into physical address
# Parameters:
#     int pid: process id of the process the owns the virtual address
#     int vaddr: the virtual address to translate
#     int pageszie: memory size of the virtual page, if you know it,
#                  this parameter is optional
# Return value:
#     int phyaddr: translated physicall address   
def virtual2physical(pid, vaddr, pagesize, cache_pagemap):

    if pagesize == 0:
        pagesize = resource.getpagesize()
    else:
        pagesize = int(options.pagesize)

    if debug is True:
        print "Translating process: ", pid, " virtual address: ", vaddr, "with pagesize: ", pagesize

    # convert the address to page index
    vpageindex = vaddr // pagesize
    # also get the address within the page
    inpageaddr = vaddr % pagesize
    
    # check the cache
    key = str(pid) + ":" + str(vpageindex)
    if pagemap_cache.has_key(key) and cache_pagemap:
        phypagedesp = pagemap_cache[key];
    else:
        # Use the /proc/[pid]/pagemap file, this file has the virtual to physical address mapping
        mapfilepath = "/proc/" + str(pid) + "/pagemap"
        
        mapfile = open(mapfilepath, "r")
        
        # Here is the document for /proc/[pid]/pagemap
        # http://www.kernel.org/doc/Documentation/vm/pagemap.txt
        # I quote it here:
        # Bits 0-54  page frame number (PFN) if present
        # Bits 0-4   swap type if swapped
        # Bits 5-54  swap offset if swapped
        # Bits 55-60 page shift (page size = 1&lt;&lt;page shift)
        # Bit  61    reserved for future use
        # Bit  62    page swapped
        # Bit  63    page present
    
        # This is the actually offset for this page is vpageindex * 8, size each page has 64 bits or 8 bytes
        offset = vpageindex * 8
        if debug is True:
            print "File pointer offset is ", offset
        # Move the file pointer to the offset
        mapfile.seek(offset)
        phypagedesp = mapfile.read(8)
        pagemap_cache[key] = phypagedesp;
        # close the file
        mapfile.close()


    phypagedesp_i = int(phypagedesp[::-1].encode('hex'), 16)
    phypageaddr =  phypagedesp_i & 0x7fffffffffffff
    pageshift = phypagedesp_i >> 55 & 0x3f
    pagepresent = phypagedesp_i >> 63

    phyaddr = (phypageaddr << pageshift) | inpageaddr

    if debug is True:
        print "Whether the page is present in memory is ", pagepresent
    if debug is True:
        print "Physical page address is ", hex(phypageaddr)
    if debug is True:
        print "Physical address is ", hex(phyaddr)

    
    return phyaddr





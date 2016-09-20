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

    # always get page size from system configuration
    pagesize = resource.getpagesize()

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
        # Bit  55    pte is soft-dirty (see Documentation/vm/soft-dirty.txt)
        # Bit  56    page exclusively mapped (since 4.2)
        # Bits 57-60 zero
        # Bit  61    page is file-page or shared-anon (since 3.5)
        # Bit  62    page swapped
        # Bit  63    page present

        # Note that originally, Bits 55-60 indicate page shift (i.e., page size)
        # However after kernel 3.11, these bits are used for other purposes.
        # For all machines I have, in /proc/[pid]/pagemap, page size is fixed to
        # be 4KB (even for 2MB huge pages). There seems to be no need to keep
        # the page shift bits.
                                            
    
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
    pagepresent = phypagedesp_i >> 63
    pageshift = 0
    pagesize2 = pagesize
    while((pagesize2 & 0x1) == 0x0):
        pageshift++;
        pagesize2 >> 4
    print "pageshift is", pageshift

    phyaddr = (phypageaddr << pageshift) | inpageaddr

    if debug is True:
        print "Whether the page is present in memory is ", pagepresent
    if debug is True:
        print "Physical page address is ", hex(phypageaddr)
    if debug is True:
        print "Physical address is ", hex(phyaddr)

    
    return phyaddr





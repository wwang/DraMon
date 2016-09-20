This directory contains the following tools of DraMon model:

1. Virtual address to physical address translation script: "virtual2physical.py". This script takes an virtual address and a process id as inputs, reads in the page table from kernel, and translate virtual address to physical address. Please note that the process must be alive for this translation to work (a dead process does not have page table...).

2. Physical address to DRAM address translation script: "physical2dram.py". This script translates a physical address to node, channel, rank, bank, row and column addresses. Because DRAM mapping information is stored in the high address space of the PCI configuration registers, this script has to be invoked with root privilege. "pciconfig.py" is a subroutine used here for accessing PCI configuration registers. Please note that the script is only good for AMD 10h processors. And for the bank, row, and column addresses, I only implement the configuration of "0b0111" on DIMM slot 0 (the reading of the F2x[1, 0]80 DRAM Bank Address Mapping Registers), because I do not feel comfortable implementing something that I cannot test. Other configurations can be (very) easily implemented by extending the lines 320-329 of "physical2dram.py". If you have implemented and tested other configurations, please send me a patch so I can apply your changes.

3. An user-interface for the translation scripts" "virtual2dram.py". It works as an uniformed entrance for the translation scripts. It supports virtual to physical, physical to DRAM, and virtual to DRAM translation. It also supports translation of a large chuck of memory.

4. For better performance, I recommend caching the reading of PCI configuration register (an option provided in virtual2dram.py). It will be very slow if every address translation has to do a PCI register read (which is an I/O operation with switching to kernel space...). Caching PCI register readings should be very safe, since DRAM configuration should not change after boot. For even better performance, try "pypy" instead of stock "python". If you still want more speed, try my C implementation.

5. The C implementation requires some helper functions from https://github.com/wwang/common_toolx. Edit the Makefile of the C implementation to include the correct path of common_toolx

6. The format /proc/[pid]/pagemap has changed since kernel 3.11. The page shift bits (indicating page size) have been dropped. It seems /proc/[pid]/pagemap does not corresponds to page table any more, instead it simply translates a virtual address to a physical address (physical page number * 4KB). Each entry in "pagemap" always represents 4KB memory space. /proc/kpageflags gives the flag of physical pages, which is also always in 4KB page/frame. For a huge page, it corresponds to multiple entries in "kpageflags" and "pagemap". For example, an 2MB huge page, corresponds to consecutive 512 entries in
"kpageflags", which the first entry has flags HUGE and COMPOUND_HEAD, and the rest entries has HUGE and COMPOUND_TAIL. The best reference to understand the format of "pagemap" and "kpageflags" are kernel document at "https://www.kernel.org/doc/Documentation/vm/pagemap.txt" and kernel tool at "kernel source/tools/vm/page-types.c."


7. After Kernel 4.2, need CAP_SYS_ADMIN capability (basically root) to read "pagemap."

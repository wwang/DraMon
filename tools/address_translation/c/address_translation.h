/*
 * Header file for virtual/physical address translations
 *
 * Author: Wei Wang wwang@virginia.edu
 *
 */
#ifndef __ADDRESS_TRANSLATION__
#define __ADDRESS_TRANSLATION__

#include "pci_configuration.h"

struct virtualpage_info{
	unsigned long long virtual_addr;
	unsigned long long physical_addr;
	unsigned long long encoded_page_info;
	int swap_type;
	unsigned long long swap_offset;
	int page_shit;
	unsigned long long page_size;
	int page_shift;
	int page_swapped;
	int page_present;
};

/*
 * Translate virtual address to physical address
 *
 * Parameters:
 *     pid        ==>   process id of the process that owns this virtual address
 *     vaddr      ==>   the virtual address to translate
 *     page_size  ==>   OS page size
 *     paddr      ==>   translated physical address
 *     vpage      ==>   if not NULL, returns the information of the virtual page
 *     debug      ==>   whether to enable debug output
 *     use_cached ==>   whether to use cached result, this may be tricky, since
 *                      the same virtual page can be swapped out, and have a 
 *                      different physical address can swapped back
 * Return values:
 *     0          ==>   success
 *     1          ==>   page_size is 0 or paddr is NULL
 *     2          ==>   cannot open /proc/[pid]/pagemap file
 *     3          ==>   can seek to an offset in pagemap file
 *     4          ==>   error occurred while reading pagemap file
 *
 */
int virtual_to_physical(int pid, 
			unsigned long long vaddr, 
			unsigned long long page_size,
			unsigned long long *paddr,
			struct virtualpage_info *vpage, 
			int debug,
			int use_cached);


struct dram_address{
	int node;
	int chnl; /* channel */
	int rank;
	int bank;
	int row;
	int col;
};

/*
 * Translate a physical address into dram address which consists of "node, 
 * channel, rank, bank, row and column".
 *
 * Parameters:
 *     phy_addr   ==>  physical address to translate
 *     drm_addr   ==>  output dram address saved here
 *     pci_devices 
 *                ==>  PCI address of the nodes/memory controllers
 *     pci_dev_nt
 *                ==>  total number of nodes/memory controllers
 *
 *     debug      ==>  wether output debug long
 *     use_cached ==>  wether enable PCI configration cache, 
 *                      see read_pci_configuration for explanations
 * Return values:
 *     0          ==>  success
`*     -1         ==>  input physical address is too large
 *     -2         ==>  drm_addr is NULL
 *     others     ==>  PCI reading error, 
 *                     see read_pci_configuration for details
 */

int physical_to_dram(unsigned long long phy_addr,
		     struct dram_address *drm_addr,
		     struct pci_device * pci_devices,
		     int pci_dev_cnt,
		     int debug,
		     int use_cached);

/*
 * Translate a physical address into "normalized address". "Normalized address" 
 * is the actual address that is send to the Dram Controllers (DCTs). DCTs use
 * this address to determine the rank, bank, row and column. The node and 
 * channel are already determined when "normalized address" is generated.
 *
 * Parameters:
 *     phy_addr   ==>  physical address to translate
 *     norm_addr  ==>  output normalized address
 *     node       ==>  output the node of this physical address
 *     chnl       ==>  output the channel of this physical address
 *     pci_devices 
 *                ==>  PCI address of the nodes/memory controllers
 *     pci_dev_cnt
 *                ==>  total number of nodes/memory controllers
 *     pci_dev_idx
 *                ==>  index of the PCI device of the node that 
 *                     owns this physical address
 *     debug      ==>  wether output debug long
 *     use_cached ==>  wether enable PCI configration cache, 
 *                     see read_pci_configuration for explanations
 * Return values:
 *     0          ==>  success
`*     -1         ==>  input physical address is too large 
 *                     (no node matches the physical address)
 *     -2         ==>  norm_addr, node or (and) chnl is (are) NULL
 *     others     ==>  PCI reading error, 
 *                     see read_pci_configuration for details 
 */

int physical_to_normalized(unsigned long long phy_addr,
			   unsigned long long *norm_addr,
			   int *node,
			   int *chnl,
			   struct pci_device * pci_devices,
			   int pci_dev_cnt,
			   int *pci_dev_idx,
			   int debug,
			   int use_cached);

/*
 * Given a normalized address, this function gives the rank it hits 
 *
 * Parameters:
 *     norm_addr  ==>  normalized address
 *     rank_addr  ==>  output address with in the rank
 *     rank       ==>  output which rank this normalized address hits
 *     pci_devices 
 *                ==>  PCI address of current node/memory controller
 *     node       ==>  node of this rank
 *     chnl       ==>  channel of this rank
 *     debug      ==>  wether output debug long
 *     use_cached ==>  wether enable PCI configration cache, 
 *                     see read_pci_configuration for explanations
 * Return values:
 *     0          ==>  success
 *     -2         ==>  output parameters have NULL
 *     others     ==>  PCI reading error, 
 *                     see read_pci_configuration for details 
 */
int normalized_to_rank(unsigned long long norm_addr,
		       unsigned long long *rank_addr,
		       int *rank,
		       struct pci_device * pci_devices,
		       int node,
		       int chnl,
		       int debug,
		       int use_cached);

/* 
 * Given a rank address, this function gives the bank, row and column.
 * 
 * Parameters:
 *     rank_addr  ==>  address with in the rank
 *     bank       ==>  output bank
 *     row        ==>  output row
 *     col        ==>  output column
 *     pci_devices 
 *                ==>  PCI address of current node/memory controller
 *     node       ==>  node of this rank
 *     chnl       ==>  channel of this rank
 *     rank       ==>  rank #
 *     debug      ==>  whether output debug long
 *     use_cached ==>  wether enable PCI configration cache, 
 *                     see read_pci_configuration for explanations
 * Return values:
 *     0          ==>  success
 *     -2         ==>  output parameters have NULL
 *     others     ==>  PCI reading error, 
 *                     see read_pci_configuration for details 
 */
int rank_to_bankrowcol(unsigned long long rank_addr,
		       int *bank,
		       int *row,
		       int *col,
		       struct pci_device * pci_devices,
		       int node,
		       int chnl,
		       int rank,
		       int debug,
		       int use_cached);

#endif

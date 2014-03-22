/*
 * Functions for virtual/physical address translations
 *
 * Author: Wei Wang wwang@virginia.edu
 *
 */

#define _LARGEFILE64_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/types.h>
#include <unistd.h>
#include <err.h>
#include <string.h>

#include <common_toolx.h>

#include "address_translation.h"

#define PROC_PATH "/proc"

/*
 * Translate virtual page to physical page
 * Check header file for parameters / return values.
 */
int virtual_to_physical(int pid, 
			unsigned long long vaddr, 
			unsigned long long page_size,
			unsigned long long *paddr,
			struct virtualpage_info *vpage, 
			int debug,
			int use_cached)
{
	int page_map_file;
	off64_t page_offset;
	off64_t ret_offset;
	unsigned long long within_page_addr;
	char path[256] = {0};
	struct virtualpage_info *vpage_info;
	static struct virtualpage_info vpage2 = {0}; /* this acts as a cache */
	ssize_t bytes_read = 0;

	ctx_dprintf(debug, "Translating virtual address: 0x%llx for process %d "
		    "with page size %llu\n", vaddr, pid, page_size);

	/* check parameters */
	if(page_size == 0 || vpage == NULL){
		warnx("Page size (%llu) or *paddr (0x%p) cannot be zero", 
		      page_size, (void*)paddr);
		return 1;
	}
	
	vpage_info = &vpage2;

	/* lookup the cache (result from last time) first */
	if(use_cached){
		
		unsigned long long vpage_addr = vaddr >> vpage_info->page_shift;
		
		if(vpage_addr == vpage_info->virtual_addr){
			/* we have a match */
			within_page_addr = ~(0xffffffffffffffff << 
					     vpage_info->page_shift);
			within_page_addr &= vaddr;
			*paddr = (vpage_info->physical_addr << 
				  vpage_info->page_shift) | within_page_addr;
			if(vpage != NULL)
				memcpy(vpage, vpage_info, 
				       sizeof(struct virtualpage_info));
			ctx_dprintf(debug, "Virtual to physical translation "
				    "used cached result\n");
			return 0;
		}

	}

	/* open the page mapping for this process */
	sprintf(path, "%s/%d/pagemap", PROC_PATH, pid);

	page_map_file = open(path, O_RDONLY);

	if(page_map_file == -1){
		warn("Failed to open file %s", path);
		return 2;
	}
	
	/* seek to the index of this page */
	page_offset = vaddr / page_size;
	within_page_addr = vaddr % page_size;
	
	/*	
	 * Here is the document for /proc/[pid]/pagemap
	 * http://www.kernel.org/doc/Documentation/vm/pagemap.txt
	 * I quote it here:
	 * Bits 0-54  page frame number (PFN) if present
	 * Bits 0-4   swap type if swapped
	 * Bits 5-54  swap offset if swapped
	 * Bits 55-60 page shift (page size = 1&lt;&lt;page shift)
	 * Bit  61    reserved for future use
	 * Bit  62    page swapped
	 * Bit  63    page present
	 */

	/* This is the actually offset for this page is vpageindex * 8, 
	 * since each page has 64 bits or 8 bytes
	 */
	page_offset *= 8;
	ctx_dprintf(debug, "Page info offset is %zd\n", page_offset);
	
	ret_offset = lseek64(page_map_file, page_offset, SEEK_SET);
	if(ret_offset == -1){
		warn("Failed to seek to %zd in file %s", page_offset, path);
		close(page_map_file);
		return 3;
	}

	/* read the virtual page info out */
	bytes_read = read(page_map_file, &(vpage_info->encoded_page_info), 8);
	if(bytes_read == -1){
		warn("Failed to read file %s", path);
		close(page_map_file);
		return 4;
	}
	else if(bytes_read != 8){
		warnx("Failed to read file %s", path);
		close(page_map_file);
		return 4;
	}
	ctx_dprintf(debug, "Virtual page info is 0x%llx\n", 
		    vpage_info->encoded_page_info);
	
	/* process virtual page info */
	vpage_info->physical_addr = 
		vpage_info->encoded_page_info & 0x7fffffffffffff;
	vpage_info->page_shift = 
		(vpage_info->encoded_page_info >> 55) & 0x3f;
	vpage_info->page_size = 
		1 << vpage_info->page_shift;
	vpage_info->page_present = 
		vpage_info->encoded_page_info >> 63 &0x1;
	vpage_info->swap_type =
		vpage_info->encoded_page_info & 0x1f;
	vpage_info->swap_offset = 
		(vpage_info->encoded_page_info >> 5) & 0x3ffffffffffff;
	vpage_info->page_swapped = 
		(vpage_info->encoded_page_info >> 62) & 0x1;
	vpage_info->virtual_addr = vaddr >> vpage_info->page_shift;
	*paddr = (vpage_info->physical_addr << vpage_info->page_shift) | 
		within_page_addr;
	
	if(vpage != NULL)
		memcpy(vpage, vpage_info, sizeof(struct virtualpage_info));

	close(page_map_file);

	return 0;
}


/*
 * Translate phyiscal address to dram address
 * Check header file for parameters / return values.
 */
int physical_to_dram(unsigned long long phy_addr,
		     struct dram_address *drm_addr,
		     struct pci_device * pci_devices,
		     int pci_dev_cnt,
		     int debug,
		     int use_cached)
{
	unsigned long long norm_addr;
	unsigned long long rank_addr;
	int pci_dev_idx;
	int ret_val;

	/* check parameters */
	if(drm_addr == NULL || pci_devices == NULL){
		warnx("Output parameters: drm_addr (%p), pci_devices (%p) "
		      "can not be NULL\n",
		      (void*)drm_addr, (void*)pci_devices);
		return -2;
	}
	if(phy_addr > 0x1000000000000){
		/* has more than 48 bits */
		warnx("Physical address should have 48 bits maximum\n");
		return -1;
	}

	/* get normalized address */
	ret_val = physical_to_normalized(phy_addr, &norm_addr,
					 &(drm_addr->node), &(drm_addr->chnl),
					 pci_devices, pci_dev_cnt,
					 &pci_dev_idx, debug, use_cached);
	if(ret_val){
		warn("Error determining node and channel with err no %d\n", 
		     ret_val);
		return ret_val;
	}
	
	/* determine the rank */
	ret_val = normalized_to_rank(norm_addr, &rank_addr, &(drm_addr->rank),
				     &(pci_devices[pci_dev_idx]),
				     drm_addr->node, drm_addr->chnl,
				     debug, use_cached);
	if(ret_val){
		warn("Error determining rank with err no %d\n", 
		     ret_val);
		return ret_val;
	}
	
	/* determine the bank, row, column */
	ret_val = rank_to_bankrowcol(rank_addr, &(drm_addr->bank), 
				     &(drm_addr->row), &(drm_addr->col),
				     &(pci_devices[pci_dev_idx]),
				     drm_addr->node, drm_addr->chnl, 
				     drm_addr->rank, debug, use_cached);

	if(ret_val){
		warn("Error determining bank, row and column with err no %d\n", 
		     ret_val);
		return ret_val;
	}

	return 0;
}


/*
 * Translate phyiscal address to normalized address
 * Check header file for parameters / return values.
 */
int physical_to_normalized(unsigned long long phy_addr,
			   unsigned long long *norm_addr,
			   int *node,
			   int *chnl,
			   struct pci_device * pci_devices,
			   int pci_dev_cnt,
			   int *pci_dev_idx,
			   int debug,
			   int use_cached)
{
	//int node_found = 0;
	int i;
	int func1_addr; /* address of the PCI config. register for function 1 */
	int dram_base_low; /* dram base address low bits */
	int dram_base_high; /* dram base address high bits */
	unsigned long long dram_base_long; /* dram base address */
	int dram_limit_low; /* dram max address low bits */
	int dram_limit_high; /* dram max address high bits */
	unsigned long long dram_limit_long; /* dram max address */
	int dram_en; /* dram enabled */
	int intlv_en; /* node interleaving enabled */
	int intlv_sel; /* node interleaving selection bits */
	int Ilog;
	int hole_en; /* memory hoister enabled */
	int hole_offset; /* memory hoister offset */
	int intlv_rgn_swap_en; /* swap interleaved region enabled */
	int intlv_rgn_base_addr;
	int intlv_rgn_lmt_addr;
	int intlv_rgn_size;
	int dct_sel_hi_rng_en;
	int dct_sel_hi;
	int dct_sel_intlv_en;
	int dct_gang_en;
	int dct_sel_intlv_addr;
	int dct_sel_base_addr;
	unsigned long long dct_sel_base_offset_long;
	int hi_range_selected;
	unsigned long long channel_offset_long, channel_addr_long;

	int ret_val;
	int temp;
	int temp2;
	unsigned long long temp3;

	/* check parameters */
	if(norm_addr == NULL || node == NULL || chnl == NULL ||
	   pci_devices == NULL){
		warnx("Output parameters: norm_addr(%p), node(%p), chnl(%p) "
		     "pci_devices(%p) can not be NULL\n", (void *)norm_addr, 
		      (void *)node, (void*)chnl, (void*)pci_devices);
		return -2;
	}
	if(phy_addr > 0x1000000000000){
		/* has more than 48 bits */
		warnx("Physical address should have 48 bits maximum\n");
		return -1;
	}

	/* go over each node and find the owner of this physical address */
	for(i = 0; i < pci_dev_cnt; i++){
		/*
		 * get the base memory address for this memory controller
		 * check "AMD family 10h Processor BKDG" for description of 
		 * related PCI configration registers
		 */
		func1_addr = 0x40 + (i << 3);
		ret_val = read_pci_configuration(pci_devices[i].domain, 
						 pci_devices[i].bus, 
						 pci_devices[i].slot, 
						 0x1, func1_addr, 
						 &dram_base_low, 
						 debug, use_cached);
		if(ret_val){
			warnx("Physical to Normalized: PCI read error %d\n", 
			      ret_val);
			return ret_val;
		}

		dram_en = dram_base_low & 0x00000003;
		intlv_en = (dram_base_low & 0x00000700) >> 8;
		dram_base_low &= 0xFFFF0000;

		ret_val = read_pci_configuration(pci_devices[i].domain, 
						 pci_devices[i].bus, 
						 pci_devices[i].slot, 
						 0x1, func1_addr + 0x100, 
						 &dram_base_high, 
						 debug, use_cached);
		if(ret_val){
			warnx("Physical to Normalized: PCI read error %d\n", 
			      ret_val);
			return ret_val;
		}

	        dram_base_high &= 0xFF;
		dram_base_long = (((unsigned long long)dram_base_high << 32) + 
				  dram_base_low) << 8;
        
		/* get the memory address limit for this memory controller */
		ret_val = read_pci_configuration(pci_devices[i].domain, 
						 pci_devices[i].bus, 
						 pci_devices[i].slot, 
						 0x1, func1_addr + 0x4, 
						 &dram_limit_low, 
						 debug, use_cached);
		if(ret_val){
			warnx("Physical to Normalized: PCI read error %d\n", 
			      ret_val);
			return ret_val;
		}

		*node = dram_limit_low & 0x00000007;
		intlv_sel = (dram_limit_low & 0x00000700) >> 8;
		dram_limit_low |= 0x0000FFFF;

		ret_val = read_pci_configuration(pci_devices[i].domain, 
						 pci_devices[i].bus, 
						 pci_devices[i].slot, 
						 0x1, func1_addr + 0x104, 
						 &dram_limit_high, 
						 debug, use_cached);
		if(ret_val){
			warnx("Physical to Normalized: PCI read error %d\n", 
			      ret_val);
			return ret_val;
		}


		dram_limit_high &= 0xFF;
		dram_limit_long = ((((unsigned long long)dram_limit_high << 32) 
				    + dram_limit_low) << 8) | 0xFF;
		
		ctx_dprintf(debug, "Node: %d: base memory address: 0x%016llx, "
			    "limit: 0x%016llx\n", *node, dram_base_long, 
			    dram_limit_long);

		/* get the memory hole address for this memory controller */
		ret_val = read_pci_configuration(pci_devices[i].domain, 
						 pci_devices[i].bus, 
						 pci_devices[i].slot, 
						 0x1, 0xF0, 
						 &hole_en, 
						 debug, use_cached);
		if(ret_val){
			warnx("Physical to Normalized: PCI read error %d\n", 
			      ret_val);
			return ret_val;
		}

		hole_offset = hole_en & 0x0000FF80;
		hole_en &= 0x00000003;
		ctx_dprintf(debug, "Node %d: memory hole enabled: %d; memory "
			    "hole offset: 0x%08x\n", *node, hole_en, hole_offset
			    );

		/* 
		 * now lets check whether the physical address belongs to this 
		 * memory controller/node 
		 */
		if ( dram_en && (dram_base_long <= phy_addr) && 
		     (phy_addr <= dram_limit_long)){
			//node_found = 1;

			ctx_dprintf(debug, "Physical address 0x%016llx belongs "
				    "to node %d\n", phy_addr, *node);
            
			/* check node interleaving */
			if((intlv_en == 0x0) || 
			   (intlv_sel == ((phy_addr >> 12) & intlv_en))){
				if (intlv_en)
					Ilog = 1;
				else if(intlv_en == 3)
					Ilog = 2;
				else if(intlv_en == 7)
					Ilog = 7;
				else
					Ilog = 0;
			}

			/* 
			 * modified the physical address based on "swap 
			 * interleaved region" 
			 */
			ret_val = read_pci_configuration(pci_devices[i].domain, 
							 pci_devices[i].bus, 
							 pci_devices[i].slot, 
							 0x2, 0x10C, 
							 &temp, 
							 debug, use_cached);
			if(ret_val){
				warnx("Physical to Normalized: PCI read error "
				      "%d\n", ret_val);
				return ret_val;
			}

			intlv_rgn_swap_en = temp & 0x1;
			if(intlv_rgn_swap_en){
				intlv_rgn_base_addr = (temp >> 3) & 0x7F;
				intlv_rgn_lmt_addr = (temp >> 11) & 0x7F;
				intlv_rgn_size = (temp >> 20) & 0x7F;
				
				if((phy_addr >> 34 == 0) && 
				   (((phy_addr >> 27 >= intlv_rgn_base_addr) &&
				     (phy_addr >> 27 <= intlv_rgn_lmt_addr)) ||
				    (phy_addr >> 27 < intlv_rgn_size)))
					phy_addr ^= (intlv_rgn_base_addr << 27);

			}
            
			ctx_dprintf(debug, "Physical address after \"swap "
				    "interleaved region\" is 0x%016llx\n", 
				    phy_addr);
				

			/* 
			 * determine which channel (dram controller or DCT) to 
			 * use (dual-channel here)
			 */
			ret_val = read_pci_configuration(pci_devices[i].domain, 
							 pci_devices[i].bus, 
							 pci_devices[i].slot, 
							 0x2, 0x110, 
							 &temp, 
							 debug, use_cached);
			if(ret_val){
				warnx("Physical to Normalized: PCI read error "
				      "%d\n", ret_val);
				return ret_val;
			}

			dct_sel_hi_rng_en = temp & 1;
			dct_sel_hi = (temp >> 1) & 1;
			dct_sel_intlv_en = temp & 4;
			dct_gang_en = temp & 0x10;
			dct_sel_intlv_addr = (temp >> 6) & 3;
			dct_sel_base_addr = temp & 0xFFFFF800;

			ret_val = read_pci_configuration(pci_devices[i].domain, 
							 pci_devices[i].bus, 
							 pci_devices[i].slot, 
							 0x2, 0x114, 
							 &temp2, 
							 debug, use_cached);
			if(ret_val){
				warnx("Physical to Normalized: PCI read error "
				      "%d\n", ret_val);
				return ret_val;
			}
			dct_sel_base_offset_long = (unsigned long long)
				(temp2 & 0xFFFFFC00) << 16;
            
			
			ctx_dprintf(debug, "DCT_select_high_enabled is %d"
				    ", DCT_high_range_DCT is %d" 
				    ", DCT_interleave_enabled is %d\n",
				    dct_sel_hi_rng_en, dct_sel_hi, 
				    dct_sel_intlv_en);
			ctx_dprintf(debug, "DCT_is_ganged is %d, "
				    "Dct_channel_interleave_bits are %x, "
				    "Dct_high_addr_bits are 0x%x\n", 
				    dct_gang_en, dct_sel_intlv_addr, 
				    dct_sel_base_addr);
			ctx_dprintf(debug, "Dct_base_address is 0x%016llx\n", 
				    dct_sel_base_offset_long);
			
			/* determine if high range is selected*/
			if((dct_sel_hi_rng_en) && (dct_gang_en == 0) && 
			   ((phy_addr >> 27) >= (dct_sel_base_addr >> 11)))
				hi_range_selected = 1;
			else
				hi_range_selected = 0;
            
			
			ctx_dprintf(debug, "DCT high ranged selected is %d\n", 
				    hi_range_selected);

			/* now, let's really determine which channel to use */
			if(dct_gang_en)
				*chnl = 0;
			else if(hi_range_selected)
				*chnl = dct_sel_hi;
			else if((dct_sel_intlv_en != 0) && 
				(dct_sel_intlv_addr == 0))
				*chnl = (phy_addr >> 6) & 1;
			else if((dct_sel_intlv_en != 0) && 
				((dct_sel_intlv_addr >> 1) & 1)){
				
				int fivebits, bit0, bit1, bit2, bit3, bit4;
				int tmp;
				
				fivebits = (phy_addr >> 16) & 0x1F;
				bit0 = fivebits & 0x1;
				bit1 = (fivebits>>1) & 0x1;
				bit2 = (fivebits>>2) & 0x1;
				bit3 = (fivebits>>3) & 0x1;
				bit4 = (fivebits>>4) & 0x1;
				tmp = (bit0 ^ bit1 ^ bit2 ^ bit3 ^ bit4) & 0x1;
				
				if(dct_sel_intlv_addr & 0x1)
					*chnl = (((phy_addr >> 9) & 0x1) ^ tmp)
						& 0x1;
				else
					*chnl = (((phy_addr >> 6) & 0x1) ^ tmp)
						& 0x1;
			    }
			else if(dct_sel_intlv_en && (intlv_en & 4))
				*chnl = (phy_addr>>15) & 0x1;
			else if(dct_sel_intlv_en && (intlv_en & 2))
				*chnl = (phy_addr>>14) & 0x1;
			else if(dct_sel_intlv_en && (intlv_en & 1))
				*chnl = (phy_addr>>13) & 0x1;
			else if(dct_sel_intlv_en)
				*chnl = (phy_addr>>12) & 0x1;
			else if(dct_sel_hi_rng_en && (dct_gang_en == 0))
				*chnl = ~dct_sel_hi & 0x1;
			else
				*chnl = 0;
			
			ctx_dprintf(debug, "Channel is %d\n", *chnl);

			/* determine base address offset to use */
			if(hi_range_selected){
				if  (!(dct_sel_base_addr & 0xFFFF0000) &&
				     (hole_en & 1) && 
				     (phy_addr >= 0x100000000))
					channel_offset_long = 
						(unsigned long long)hole_offset 
						<< 16;
				else
					channel_offset_long = 
						dct_sel_base_offset_long;
			    }
			else{
				if ((hole_en & 1) && (phy_addr >= 0x100000000))
					channel_offset_long = 
						(unsigned long long)hole_offset 
						<< 16;
				else
					channel_offset_long = dram_base_long & 
						0xFFFFF8000000;
			}
            
			ctx_dprintf(debug, 
				    "Channel base address offset is 0x%016llx\n"
				    ,channel_offset_long);

			/* 
			 * remove hoisting offset and normalize to DCT addresses
			 */
			channel_addr_long = (phy_addr & 0x0000FFFFFFFFFFC0) - 
				(channel_offset_long & 0x0000FFFFFF800000);
			/* remove node ID (in case of processor interleaving) */
			temp3 = channel_addr_long & 0xFC0;
			channel_addr_long = ((channel_addr_long >> Ilog) & 
					     0xFFFFFFFFF000) | temp3;
			/* remove channel interleave and hash */
			if ((dct_sel_intlv_en) && (hi_range_selected == 0) && 
			    (dct_gang_en == 0)){
				if((dct_sel_intlv_addr & 1) != 1)
					channel_addr_long = 
						(channel_addr_long >> 1) & 
						0xFFFFFFFFFFFFFFC0;
				else if (dct_sel_intlv_addr == 1){
					temp3 = channel_addr_long & 0xFC0;
					channel_addr_long = 
						((channel_addr_long & 
						  0xFFFFFFFFFFFFE000) >> 1) | 
						temp3;
				}
				else{
					/* ChannelAddrLong == 0b11 */
					temp3 = channel_addr_long & 0x1C0;
					channel_addr_long = 
						((channel_addr_long &
						  0xFFFFFFFFFFFFFC00) >> 1) | 
						temp3;
				}
			      }
			
			ctx_dprintf(debug, "Physical address 0x%012llx"\
				    " normalized to DCT bus address 0x%012llx\n"
				    ,phy_addr, channel_addr_long);
            
			/* end channel determination */
			*norm_addr = channel_addr_long;
			*pci_dev_idx = i;
			
			/* have the normalized address, quit now */
			return 0;
		} /* end physical address in this node */
		
	} /* end for */
	
	/* physical address belongs to no node */
	warn("Physical address 0x%016llx belongs to no node", phy_addr);
	return -1;
}


/*
 * This function removes masked bit (as specified by [mask]) from [addr]
 * If mask's ith bit is 0, then the ith bit is removed from addr
 * The return value is the address
 */
static int remove_masked_bits(unsigned long long addr, unsigned long long mask)
{
	unsigned long long addr_out = 0;
	int i = 0;
        int last_bit;

	while(addr){
		if ((mask & 0x1) == 1){
			last_bit = addr & 0x1;
			last_bit = last_bit << i;
			addr_out = last_bit | addr_out;
			i = i + 1;
		}
		addr = addr >> 1;
		mask = mask >> 1;
	}


	return addr_out;
}


int normalized_to_rank(unsigned long long norm_addr,
		       unsigned long long *rank_addr,
		       int *rank,
		       struct pci_device * pci_devices,
		       int node,
		       int chnl,
		       int debug,
		       int use_cached)
{
	unsigned long long input_addr;
	int cs; /* chip (rank) select */
	int func2_addr; /* PCI config register addr for function 2 */
	int mask_addr; /* PCI config reg. "CS MASK" address */
	int rank_base; /* rank base address register */
	int rank_mask; /* rank address mask register */
	int rank_en;
	//int rank_found;
	int online_spare_ctl;
	int swap_done, bad_rank;

	int ret_val;

	/* check parameters */
	if(rank_addr == NULL || rank == NULL || pci_devices == NULL){
		warnx("Output parameters: rank_addr(%p), rank(%p), "
		     "pci_devices(%p) can not be NULL\n", (void *)rank_addr, 
		      (void *)rank, (void*)pci_devices);
		return -2;
	}
	if(norm_addr > 0x1000000000000){
		/* has more than 48 bits */
		warnx("Normalized address should have 48 bits maximum\n");
		return -1;
	}

	/* select the chip(rank) */
	input_addr = norm_addr >> 8;

	for(cs = 0; cs < 8; cs ++){
		
		func2_addr = 0x40 + (cs << 2);
                if ((cs % 2) == 0)
			mask_addr = 0x60 + (cs << 1);
		else
			mask_addr = 0x60 + ((cs-1) << 1);

		if(chnl == 1){
			func2_addr += 0x100;
			mask_addr +=  0x100;
		}

		ret_val = read_pci_configuration(pci_devices->domain, 
						 pci_devices->bus, 
						 pci_devices->slot, 
						 0x2, func2_addr, 
						 &rank_base, 
						 debug, use_cached);
		if(ret_val){
			warnx("Physical to Normalized: PCI read error %d\n", 
			      ret_val);
			return ret_val;
		}

                rank_en = rank_base & 0x00000001;
                rank_base &= 0x1FF83FE0;

		ret_val = read_pci_configuration(pci_devices->domain, 
						 pci_devices->bus, 
						 pci_devices->slot, 
						 0x2, mask_addr, 
						 &rank_mask, 
						 debug, use_cached);
		if(ret_val){
			warnx("Physical to Normalized: PCI read error %d\n", 
			      ret_val);
			return ret_val;
		}

		rank_mask = (rank_mask | 0x0007C01F) & 0x1FFFFFFF;

		ctx_dprintf(debug, "Rank %d: Base addr is 0x%012llx (%llu MB); "
			    " mask is 0x%x\n", cs,
			    ((unsigned long long)rank_base<<8),
			    ((unsigned long long)rank_base<<8)/(1024*1024), 
			    rank_mask);
		
                if(rank_en && 
		   ((input_addr & ~rank_mask) == (rank_base & ~rank_mask))){
			//rank_found = 1;
			ret_val = read_pci_configuration(pci_devices->domain, 
							 pci_devices->bus, 
							 pci_devices->slot, 
							 0x3, 0xB0, 
							 &online_spare_ctl, 
							 debug, use_cached);
			if(ret_val){
				warnx("Physical to Normalized: PCI read error "
				      "%d\n", 
				      ret_val);
				return ret_val;
			}

			if(chnl == 1){
				swap_done = (online_spare_ctl >> 3) & 0x00000001;
				bad_rank = (online_spare_ctl >> 8) & 0x00000007;
				if((swap_done) && (cs == bad_rank))
					warnx("Need channel 1 (DCT1) online "
					     "spare chip/rank");
			}
			else{
				swap_done = (online_spare_ctl >> 1) & 0x00000001;
				bad_rank = (online_spare_ctl >> 4) & 0x00000007;
				if((swap_done) && (cs == bad_rank))
					warnx("Need channel 0 (DCT1) online "
					      "spare chip/rank");
			}

			/* we have found the rank */
			*rank = cs;
			*rank_addr = remove_masked_bits(norm_addr, 
						       (rank_mask << 8) | 0xff);
			ctx_dprintf(debug, "Normalized address 0x%012llx is on "
				    "rank %d, with rank address 0x%012llx\n", 
				    norm_addr, *rank, *rank_addr);
							
			break;
		}
	}

	
	return 0;
}

int rank_to_bankrowcol(unsigned long long rank_addr,
		       int *bank,
		       int *row,
		       int *col,
		       struct pci_device * pci_devices,
		       int node,
		       int chnl,
		       int rank,
		       int debug,
		       int use_cached)
{
	int dram_addr_map_offset; /* PCI reg offset: dram address mapping */
	int dram_addr_map; /* PCI reg: dram address mapping */

	int ret_val;

	/* check parameters */
	if(bank == NULL || row == NULL || col == NULL ||
	   pci_devices == NULL){
		warnx("Output parameters: bank(%p), row(%p), col(%p),"
		     "pci_devices(%p) can not be NULL\n", (void *)bank, 
		      (void *)row, (void*)col, (void*)pci_devices);
		return -2;
	}
	if(rank_addr > 0x1000000000000){
		/* has more than 48 bits */
		warnx("Rank address should have 48 bits maximum\n");
		return -1;
	}

	/* get bank, row and column */
	dram_addr_map_offset = 0x80;
	if(chnl == 1)
		dram_addr_map_offset += 0x100;
	ret_val = read_pci_configuration(pci_devices->domain, 
					 pci_devices->bus, 
					 pci_devices->slot, 
					 0x2, dram_addr_map_offset, 
					 &dram_addr_map, 
					 debug, use_cached);
	if(ret_val){
		warnx("Physical to Normalized: PCI read error %d\n", 
		      ret_val);
		return ret_val;
	}

	dram_addr_map &= 0xf;
       	ctx_dprintf(debug, "DramAddrMap is %d\n", dram_addr_map);

	if(dram_addr_map == 0b111){
		*bank = rank_addr>>13 & 0b111;
		*row = (((rank_addr>>16) & 0b11) << 13) | 
			((rank_addr>>18) & 0x1FFF);
		*col = (rank_addr>>3) & 0x3FF;

		ctx_dprintf(debug, "Rank addr 0x%012llx: bank %d, row %d, "
			    "col %d\n", rank_addr, *bank, *row, *col);

		return 0;
	}
	else{
		warnx("Other Dram Address Map is not implemented yet.");
		return -3;
	}

	/* never reached */
}


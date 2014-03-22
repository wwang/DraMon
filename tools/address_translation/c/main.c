/*
 * Translating a virtual address to a physicall address.
 * Type "virtual2dram -h" for usage.
 *
 * Author: Wei Wang wwang@virginia.edu
 *
 */

#include <stdio.h>
#include <stdlib.h> 
#include <unistd.h>
#include <getopt.h>

#include <common_toolx.h>

#include "address_translation.h"
//TODO: remove this include
#include "pci_configuration.h"

#define VENDOR_ID 0x1022
#define DEVICE_ID 0x1201

struct translation_options{
	int pid;
	unsigned long long address;
	unsigned long long os_page_size;
	unsigned long long mem_size;
	unsigned long long step;
	int virtual2physical_only;
	int physical2dram_only;
	int debug;
	int use_cached_pagemap;
	int use_cached_pci;
	int verbose;
};

extern int pci_read_called;
extern int pci_cache_hit;

int print_help()
{
	char * help_strings[27] = {
		"Usage: virtual2dram [options]",
		"",
		"Options:",
		"  -h, --help",
		"\t show this help message and exit",
		"  -p pid, --pid=pid",
		"\t the process id of the virtual address",
		"  -a 0xXXXXXXXX, --addr=0xXXXXXXXX",
		"\t the address to translation, must in hex format, "
		"max 64bits",
		"  -s pagesize, --pagesize=pagesize",
		"\t OS page szie in B, KB or GB, if you know it;"
		"if not specified, default OS pagesize is used",
		"  -d --debug",
		"\t enable debug output",
		"  --v2p",
		"\t only translation virtual address to physical "
		"address",
		"  --p2d",
		"\t only translation physical address to dram address",
		"  -m MEMSIZE, --memsize=MEMSIZE",
		"\t translation the whole memory region of size MEMSIZE, "
		"MEMSIZE value in B, KB, MB or GB",
		"  --step=STEP",
		"\t go over the memory region with step STEP, STEP value "
		"in B, KB, MB or GB",
		"  --cache_pagemap",
		"\t optimization by using cache page mapping information. OS "
		"swapping the virtual page in/out can render cached data "
		"useless.",
		"  --cache_pci",
		"\t optimization by using cache PCI configuration data."
		"Generally a safe optimization as PCI configurations do not"
		"change after boot.",
		"  -v, --verbose",
		"\t verbose output, show additional virtul page information.",
	};

	int i;

	for(i = 0; i < 27; i++)
		fprintf(stderr, "%s\n", help_strings[i]);

	return 0;
}

/*
 * Parse commandline parameters.
 * Function parameters are self-explanatory.
 * Returns 0 for success; non-zero means failure
 */
int parse_parameters(int argc, char *argv[], struct translation_options * ops)
{
	struct option long_options[] = {
		{"help", no_argument, NULL, 1001},
		{"pid", required_argument, NULL, 1002},
		{"addr", required_argument, NULL, 1003},
		{"pagesize", required_argument, NULL, 1004},
		{"debug", no_argument, NULL, 1005},
		{"v2p", no_argument, NULL, 1006},
		{"p2d", no_argument, NULL, 1007},
		{"memsize", required_argument, NULL, 1008},
		{"step", required_argument, NULL, 1009},
		{"cache_pagemap", no_argument, NULL, 1010},
		{"cache_pci", no_argument, NULL, 1011},
		{"verbose", no_argument, NULL, 1012}
	};
	
	int op;
	int long_op_index;
	char error_msg[256] = {0};
	char * endptr;
	int ret_val;
	
	/* put some initial values first */
	ops->pid = 0;
	ops->address = 0xFFFFFFFFFFFFFFFF;
	ops->os_page_size = sysconf(_SC_PAGESIZE);
	ops->mem_size = 1; /* default to 1, at least translate 1 byte */
	ops->step = 64LL * 1024LL * 1024LL * 1024LL; /* 64G */
	ops->virtual2physical_only = 0;
	ops->physical2dram_only = 0;
	ops->debug = 0;
	ops->use_cached_pagemap = 0;
	ops->use_cached_pci = 0;
	ops->verbose = 0;

	/* parse the commandline parameters */
	while(1){
		op = getopt_long(argc, argv, "hp:a:s:dm:v", long_options, 
				 &long_op_index);

		if(op == -1)
			break;
		
		switch(op){
		case 'h':
		case 1001:
			print_help();
		        exit(0);
		case 'p':
		case 1002:
			ops->pid = atoi(optarg);
		        if(ops->pid == 0){
				sprintf(error_msg, "%s", "Invalid pid\n");
				goto error;
			}
		        break;
		case 'a':
		case 1003:
			ops->address = strtoull(optarg, &endptr, 0);
		        if(endptr == optarg || *endptr != '\0'){
				sprintf(error_msg, "%s", "Invalid address\n");
				goto error;
			}
			break;
		case 's':
		case 1004:
			ret_val = parse_mem_size_str(optarg, 
						     &(ops->os_page_size));
		        if(ret_val != 0){
				sprintf(error_msg, "%s", "Invalid page size\n");
				goto error;
			}
			break;
		case 'd':
		case 1005:
			ops->debug = 1;
			break;
		case 1006:
			ops->virtual2physical_only = 1;
			break;
		case 1007:
			ops->physical2dram_only = 1;
			break;
		case 'm':
		case 1008:
			ret_val = parse_mem_size_str(optarg, &(ops->mem_size));
		        if(ret_val != 0){
				sprintf(error_msg, "%s", "Invalid memory size\n"
					);
				goto error;
			}
			break;
		case 1009:
			ret_val = parse_mem_size_str(optarg, &(ops->step));
		        if(ret_val != 0){
				sprintf(error_msg, "%s", "Invalid step\n");
				goto error;
			}
			break;
		case 1010:
			ops->use_cached_pagemap = 1;
			break;
		case 1011:
			ops->use_cached_pci = 1;
			break;
		case 'v':
		case 1012:
			ops->verbose = 1;
	         	break;
		default:
			sprintf(error_msg, "%s", "Unknown options or missing "
				"required value\n");
			goto error;
			break;
		}
	}

	ctx_dprintf(ops->debug, "Cmdline parameters: pid %d, addr 0x%llx, "
		    "page size %llu, memory size %llu, step %llu, v2p %d, "
		    "p2d %d, debug %d, cache_pagemap %d, "
		    "cache_pci %d\n", 
		    ops->pid, ops->address, 
		    ops->os_page_size, ops->mem_size, ops->step,
		    ops->virtual2physical_only, ops->physical2dram_only,
		    ops->debug, ops->use_cached_pagemap,
		    ops->use_cached_pci);

	/* check whether we have enough parameters */
	if(ops->address == 0xFFFFFFFFFFFFFFFF){
		sprintf(error_msg, "%s", "Please specify the address to "
			"translate\n");
		goto error;
	}

	if(ops->virtual2physical_only && ops->physical2dram_only){
		sprintf(error_msg, "%s", "--v2p and --p2d canno be set "
			"at the same time\n");
		goto error;
	}


	if(!ops->physical2dram_only && ops->pid == 0){
		sprintf(error_msg, "%s", "Please specify the process id\n");
		goto error;
	}

	return 0;

 error:
	fprintf(stderr, "%s\n", error_msg);
	print_help();
	exit(1);
}


int main(int argc, char *argv[])
{
	unsigned long long cur_addr;
	unsigned long long last_addr;
	unsigned long long paddr;
	struct dram_address daddr;
	struct virtualpage_info vpage;
	int ret_val;
	struct pci_device pci_devices[8] = {{0}};
	int pci_dev_cnt = 8;

	struct translation_options ops;

	parse_parameters(argc, argv, &ops);
	
	/* print headers for output */
	if(ops.virtual2physical_only){
		if(ops.verbose)
			printf("virtual_addr,"
			       "physical_addr,"
			       "vpage_info,"
			       "vpage_present,"
			       "physical_frame,"
			       "vapge_shift,"
			       "vpage_size,"
			       "vpage_swapped,"
			       "vpage_swap_type,"
			       "vpage_swap_offset"
			       "\n"
			       );
		else
			printf("virtual_addr,"
			       "physcial_addr"
			       "\n"
			       );
	}
	else if(ops.physical2dram_only){
		printf("physical_addr,"
		       "node,"
		       "channel,"
		       "rank,"
		       "bank,"
		       "row,"
		       "col"
		       "\n"
		       );
	}
	else{
		if(ops.verbose)
			printf("virtual_addr,"
			       "physical_addr,"
			       "node,"
			       "channel,"
			       "rank,"
			       "bank,"
			       "row,"
			       "col,"
			       "vpage_info,"
			       "vpage_present,"
			       "physical_frame,"
			       "vapge_shift,"
			       "vpage_size,"
			       "vpage_swapped,"
			       "vpage_swap_type,"
			       "vpage_swap_offset"
			       "\n"
			       );
		else
		printf("virtual_addr,"
		       "physical_addr,"
		       "node,"
		       "channel,"
		       "rank,"
		       "bank,"
		       "row,"
		       "col"
		       "\n"
		       );
	}

	/* list each node */
	lspci_by_vend_dev(VENDOR_ID, DEVICE_ID, pci_devices, 
			  &pci_dev_cnt, ops.debug);

	/* go over the memory region and translate very address as requested */
	last_addr = ops.address + ops.mem_size;
	for(cur_addr = ops.address; cur_addr < last_addr; cur_addr += ops.step){
		/* translate virtual address first */
		if(!ops.physical2dram_only){
			ret_val = virtual_to_physical(ops.pid, 
						      cur_addr, 
						      ops.os_page_size,
						      &paddr,
						      &vpage,
						      0,
						      ops.use_cached_pagemap);
			if(ret_val != 0){
				fprintf(stderr, "Error translating virtual "
					"address 0x%llx\n", cur_addr);
				exit(1);
			}
		}
		else
			paddr = cur_addr;
		
		/* output virtual address translation if v2p only */
		if(ops.virtual2physical_only){
			if(!ops.verbose){
				printf("0x%llx,0x%llx\n", cur_addr, paddr);
			}
			else{
				printf("0x%llx,0x%llx,0x%llx,%d,0x%llx,%d,"
				       "%llu,%d,%d,0x%llx\n", 
				       cur_addr, 
				       paddr, 
				       vpage.encoded_page_info,
				       vpage.page_present,
				       vpage.physical_addr,
				       vpage.page_shift,
				       vpage.page_size,
				       vpage.page_swapped,
				       vpage.swap_type,
				       vpage.swap_offset);
			}
			/* proceed to translate next virtual address */
			continue; 
		}

		/* translate the physical address */
		physical_to_dram(paddr, &daddr, pci_devices, pci_dev_cnt, 
				 ops.debug, ops.use_cached_pci);
		
		/* output the results */
		if(ops.physical2dram_only){
			printf("0x%llx,%d,%d,%d,%d,%d,%d\n",
			       paddr,
			       daddr.node,
			       daddr.chnl,
			       daddr.rank,
			       daddr.bank,
			       daddr.row,
			       daddr.col
			       );
		}
		else{
			if(!ops.verbose)
				printf("0x%llx,0x%llx,%d,%d,%d,%d,%d,%d\n",
				       cur_addr,
				       paddr,
				       daddr.node,
				       daddr.chnl,
				       daddr.rank,
				       daddr.bank,
				       daddr.row,
				       daddr.col
				       );
			else
				printf("0x%llx,0x%llx,%d,%d,%d,%d,%d,%d"
				       "0x%llx,%d,0x%llx,%d,%llu,%d,%d,"
				       "0x%llx\n",
				       cur_addr,
				       paddr,
				       daddr.node,
				       daddr.chnl,
				       daddr.rank,
				       daddr.bank,
				       daddr.row,
				       daddr.col,
				       vpage.encoded_page_info,
				       vpage.page_present,
				       vpage.physical_addr,
				       vpage.page_shift,
				       vpage.page_size,
				       vpage.page_swapped,
				       vpage.swap_type,
				       vpage.swap_offset
				       );
		}
	}

	if(ops.use_cached_pci)
		printf("PCI read called %d times, hit %d times, hit rate %f\n", 
		       pci_read_called, pci_cache_hit, 
		       (double)pci_cache_hit/(double)pci_read_called);
	
	      
	return 0;
}

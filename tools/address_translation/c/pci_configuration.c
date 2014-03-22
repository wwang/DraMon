/*
 * Functions for reading PCI configuration registers
 *
 * Author: Wei Wang wwang@virginia.edu
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/types.h>
#include <unistd.h>
#include <err.h>

#include <common_toolx.h>

#include "pci_configuration.h"

#define PCI_CONF_PATH_PREFIX "/sys/bus/pci/devices"

struct pci_cache_item{
	int has_data;
	int data;
	unsigned long long tag; /* tag: domain:bus:slot:function:address */
};

#define CACHE_SIZE_1 8
#define CACHE_SIZE_2 2
#define CACHE_SIZE_3 127
struct pci_cache_item \
       cached_pci_data[CACHE_SIZE_1][CACHE_SIZE_2][CACHE_SIZE_3] = 
	{{{{0}}}}; /* [func][addr] */

int pci_read_called = 0;
int pci_cache_hit = 0;

/*
 * Read PCI configuration registers
 * Check header file for parameters / return values.
 */
int read_pci_configuration(int domain,
			   int bus,
			   int slot,
			   int function,
			   int address,
			   int *data,
			   int debug,
			   int use_cached)
{
	int pci_conf_file;
	off_t pci_register_offset;
	off_t ret_offset;
	char path[256] = {0};
	ssize_t bytes_read = 0;
	unsigned long long tag = 0; /* for cache */
	int node_idx, func_idx, addr_idx; /* for cache */

	ctx_dprintf(debug, "Reading PCI register: domain %d, bus %d, slot %d, "
		    "function %d, address 0x%x\n", domain, bus, slot, function,
		    address);

	/* check parameters */
	if(data == NULL){
		warnx("Output data pointer (0x%p) cannot be zero", (void*)data);
		return 1;
	}

	pci_read_called++;
	/* 
	 * check the cache, the good thing is PCI configuration is not changed 
	 * after boot
	 */
	if(use_cached){
		tag |=  ((address & 0xffff)) | 
			((function & 0xf) << 16) | 
			((slot & 0xff) << 20) | 
			((bus & 0xff) << 28) | 
			((unsigned long long)(domain & 0xffff) << 36);

		node_idx = slot % CACHE_SIZE_1;
		func_idx = function % CACHE_SIZE_2;
		addr_idx = address % CACHE_SIZE_3; 
		
		if(cached_pci_data[node_idx][func_idx][addr_idx].has_data &&
		   cached_pci_data[node_idx][func_idx][addr_idx].tag == tag){
			/* we have a match */
			pci_cache_hit++;
			*data = cached_pci_data[node_idx][func_idx] \
				[addr_idx].data;
			ctx_dprintf(debug, "Cached PCI data used\n");
			return 0;
		}
		
		/*printf("Missed address:func %x(%d), addr %x(%d), has data %d,"
		       " tag 0x%llx, tag 0x%llx\n", 
		       function, func_idx, address, addr_idx, 
		       cached_pci_data[node_idx][func_idx][addr_idx].has_data,
		       cached_pci_data[node_idx][func_idx][addr_idx].tag,
		       tag);*/
		
	}

	/* open the page mapping for this process */
	sprintf(path, "%s/%04x:%02x:%02x.%01x/config",PCI_CONF_PATH_PREFIX, 
		domain, bus, slot, function);
	
	ctx_dprintf(debug, "PCI config file path: %s\n", path);
	pci_conf_file = open(path, O_RDONLY);

	if(pci_conf_file == -1){
		warn("Failed to open file %s", path);
		return 2;
	}
	
	/* seek to the index of this page */
	pci_register_offset = address;	
	
	ret_offset = lseek(pci_conf_file, pci_register_offset, SEEK_SET);
	if(ret_offset == -1){
		warn("Failed to seek to %zd in file %s", 
		     pci_register_offset, path);
		close(pci_conf_file);
		return 3;
	}

	/* read the virtual page info out */
	bytes_read = read(pci_conf_file, data, 4);
	if(bytes_read == -1){
		warn("Failed to read file %s", path);
		close(pci_conf_file);
		return 4;
	}
	else if(bytes_read != 4){
		warnx("Failed to read file %s", path);
		close(pci_conf_file);
		return 4;
	}
	ctx_dprintf(debug, "PCI configuration register data is 0x%08x\n", 
		    *data);

	/* update cache */
	if(use_cached){
		cached_pci_data[node_idx][func_idx][addr_idx].has_data = 1;
		cached_pci_data[node_idx][func_idx][addr_idx].data = *data;
		cached_pci_data[node_idx][func_idx][addr_idx].tag = tag;
	}
	
	close(pci_conf_file);

	return 0;
}


/*
 * List all the PCI devices that matches vendor and device
 * Check header file for parameters / return values. 
 */
int lspci_by_vend_dev(int vendor_id,
		     int device_id,
		     struct pci_device *devices,
		     int *count,
		     int debug)
{
	char cmd[256];
	char buf[256];
	FILE *fp;
	int dev_cnt = 0;
	int bus;
	int slot;
     
	/* check parameters */
	if(count == NULL || devices == NULL){
		warnx("Output parameters: devices (%p) and count (%p) cannot be" 
		     "NULL\n", (void*)devices, (void*)count);
		return 1;
	}

	/* execute command lspci -d vendor_id:device_id */
	sprintf(cmd, "lspci -d %x:%x", vendor_id, device_id);
	ctx_dprintf(debug, "Executing command %s\n", cmd);

	fp = popen(cmd, "r");
	if(fp == NULL){
		warn("Failed to execute command %s", cmd);
		return 1;
	}
	
	/* read in outputs */
	while(fgets(buf, sizeof(buf), fp)){
		ctx_dprintf(debug, "lspci output: %s", buf);
		sscanf(buf, "%x:%x.", &bus, &slot);
		ctx_dprintf(debug, "Found device at %x:%x\n", bus, slot);
		if(dev_cnt < *count){
			devices[dev_cnt].bus = bus;
			devices[dev_cnt].slot = slot;
			devices[dev_cnt].domain = 0; /* domain always zero */
		}
		dev_cnt++;
	}
	
	*count = dev_cnt;
	pclose(fp);

	return 0;
}

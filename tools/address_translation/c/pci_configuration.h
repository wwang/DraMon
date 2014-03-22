/*
 * Header file for reading PCI configuration registers
 */

#ifndef __PCI_CONFIGRATION_READ__
#define __PCI_CONFIGRATION_READ__

/*
 * Read the PCI configuration registers
 *
 * Parameters:
 *     domain     ==>   device domain
 *     bus        ==>   device bus
 *     slot       ==>   device slot
 *     function   ==>   configuration function #
 *     addr       ==>   configuration register address
 *     data       ==>   configuration register value
 *     debug      ==>   whether to enable debug output
 *     use_cached ==>   used cached pci configuration data; generally a safe
 *                      optimization as PCI configurations usually do not 
 *                      change after boot
 * Return values:
 *     0          ==>   success
 *     1          ==>   data is NULL
 *     2          ==>   cannot open PCI configuration file
 *     3          ==>   can seek to an offset in PCI configuration file
 *     4          ==>   error occurred while reading PCI configuration file
 *
 */
int read_pci_configuration(int domain, 
			   int bus, 
			   int slot, 
			   int function, 
			   int addr, 
			   int *data,
			   int debug,
			   int use_cached);

struct pci_device{
	int domain;
	int bus;
	int slot;
};
/*
 * List all the PCI devices that matches vendor and device
 *
 * Parameters:
 *     vendor_id  ==>  integer identifier of the vendor in hex
 *     device_id  ==>  integer identifier of the device in hex
 *     devices    ==>  output array of devices found; caller should allocate
 *                     space for this array.
 *     count      ==>  input/output parameter. On input, this is the size of the
 *                     devices array. On output, this has the number of devices 
 *                     found, it can be large than the input "count", but only 
 *                     input "count" of devices will be copied into "devices"
 *     debug      ==>  enable debug output
 *
 * Return values:
 *     0          ==> success
 *     1          ==> count or(and) devices is(are) NULL
 *     2          ==> lspci execution error
 *     3          ==> lspci output reading error
 */
int lspci_by_vend_dev(int vendor_id,
		     int device_id,
		     struct pci_device *devices,
		     int *count,
		     int debug);


#endif

#!/usr/bin/python
# Use this python module to read PCI configuration registers

# Author: Wei Wang <wwang@virginia.edu>


version = '1.0'

debug = False

# Keep a cache of read values to improve performance
pcicache = dict()

# This method with return the configuration value in hex format
# for the register that located at [address] of [function] of
# the device that attached to PCI domain [domain], bus [bus] and
# slot [slot]. Total 32 bits, or 4 bytes will be read starting 
# from [address].
# Parameters:
#     int domain: domain #
#     int bus:  bus #
#     int slot: slot #
#     int function: function #
#     int address: register address #
#
# If you do not understand the parameter, check the manual of
# "lspci" and "setpci", and google "PCI configuration space". 
#
# If you want to read registers located after address 0x40, you
# probably need root privilege. 
def getPCIConfig( domain, bus, slot, function, address, cache_pci):
    pciDevSysPath = "/sys/bus/pci/devices/"
    key = (hex(domain)[2:].zfill(4) + ":" + hex(bus)[2:].zfill(2) + ":" + 
          hex(slot)[2:].zfill(2) + "." + hex(function)[2:])
    pciDevConfigPath = pciDevSysPath + key + "/config"
    key = key + ":" + hex(address)

    if pcicache.has_key(key) and cache_pci:
        return pcicache[key]

    configfile = open(pciDevConfigPath, "rb")
    if debug is True:
        print "Configuration file ",  pciDevConfigPath, "opened."
        print "Reading data from address: ", hex(address)

    configfile.seek(address)
    
    configData = configfile.read(4)
    if debug is True:
        print "Data read: ", configData.encode('hex')

    configData = int(configData[::-1].encode('hex'), 16)

    if debug is True:
        print "Data is: ", hex(configData)
    
    pcicache[key] = configData
        
    return configData



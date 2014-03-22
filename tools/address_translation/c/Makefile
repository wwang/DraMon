CC=gcc
CFLAGS=-c -Wall -I./common_toolx/
LDFLAGS=-L./common_toolx/
LIBS=-lcommontoolx
SOURCES=main.c address_translation.c pci_configuration.c
OBJECTS=$(SOURCES:.c=.o)
EXECUTABLE=virtual2dram

all: $(SOURCES) $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS) 
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@ $(LIBS)

.c.o:
	$(CC) $(CFLAGS) $< -o $@

clean:
	rm *.o $(EXECUTABLE)

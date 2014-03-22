CC=gcc
AR=ar
CFLAGS=-c -Wall
LDFLAGS= 
LIBS=
SOURCES=common_toolx.c test.c simple_hashx.c
OBJECTS=$(SOURCES:.c=.o)
EXECUTABLE=test
SLIB=libcommontoolx.a

all: $(SOURCES) $(EXECUTABLE)

$(SLIB): common_toolx.o
	$(AR) rcs $(SLIB) common_toolx.o simple_hashx.o

$(EXECUTABLE): $(OBJECTS) $(SLIB)
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@ $(SLIB) $(LIBS)

.c.o:
	$(CC) $(CFLAGS) $< -o $@

clean:
	rm *.o $(EXECUTABLE) $(SLIB)
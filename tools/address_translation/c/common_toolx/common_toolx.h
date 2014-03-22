/*
 * This a tool function library. It contains some tool functions that I found 
 * myself implemented over and over again.
 *
 * Author: Wei Wang <wwang@virginia.edu>
 */

#ifndef __COMMON_TOOLX_H__
#define __COMMON_TOOLX_H__

#include <sys/syscall.h>

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Parese a value list string. The list/string is a series of integer/float 
 * values separated by a single-charater delimiter
 * For example, if the delimitor is ',', then the list can be "1,2,3,4,5"
 * Parameters:
 *	str		--> the string to parse
 *	out_list	--> output list/array of the values. The list/array is 
 *                          created by this function, and it is the user's 
 *                          responsibility to free it;
 *	len		--> the length of the output list/array
 *	val_ty		--> 0: integer, 1: float
 * Return value:
 *      0	--> call succeed
 *	-1	--> wrong parameter
 *      -2	--> string has invalid input
 *	-3	--> list has too many values
 *	-4	--> memory allocation error
 */
int parse_value_list(char * str, void ** out_list, int * len, int val_ty);

/*
 * get thread id, just a wrapper for the SYS_gettid system call
 */
pid_t gettid();

/*
 * Parse a memory size string and return the memory size in bytes.
 * The string should be a number ends in B or K or KB or M or MB or G or GB or
 * T or TB.
 * 
 * Parameters:
 *     mem_size_str    --> the memory size string
 *     mem_size        --> memory size in bytes
 * Return value:
 *     0  --> success
 *     1  --> incorrect format
 *     2  --> mem_size_str or mem_size is NULL
 */
int parse_mem_size_str(char * mem_size_str, unsigned long long * mem_size);


/* 
 * Compilation time controlled debug output
 */
#ifdef __COMMON_TOOLX_DEBUG__
#define CTX_DPRINTF(fmt, ...)			\
	do { fprintf(stderr, fmt ,			\
		     ## __VA_ARGS__);} while (0);
#else
#define CTX_DPRINTF(fmt, ...)			\
	do {} while(0);
#endif

/*
 * Execution time controlled debug output
 */
#define ctx_dprintf(debug,fmt, ...)					\
	do { if(debug) {fprintf(stderr, fmt ,	\
			       ## __VA_ARGS__);}} while (0);


/* 
 * read processor time stamp
 */
#if defined(__i386__)
static __inline__ unsigned long long rdtsc(void)
{
      unsigned long long int x;
           __asm__ volatile (".byte 0x0f, 0x31" : "=A" (x));
                return x;
}
#elif defined(__x86_64__)
static __inline__ unsigned long long rdtsc(void)
{
      unsigned hi, lo;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
          return ( (unsigned long long)lo)|( ((unsigned long long)hi)<<32 );
}
#endif

#ifdef __cplusplus
}
#endif

#endif


/*
 * This a tool function library. It contains some tool functions that I found 
 * myself implemented over and over again.
 *
 * Author: Wei Wang <wwang@virginia.edu>
 */
#define _GNU_SOURCE
#include <stdlib.h>
#include <unistd.h>
#include <sys/syscall.h>

#include "common_toolx.h"


/* see header file for help */
int parse_value_list(char * str, void ** out_list, int * len, int val_ty)
{
	int buf_len;
	char *p, *q;
	void * out_l;
	
	int ret;
	
	/* parameter check */
	if(str == NULL || len == NULL || out_list == NULL || (val_ty != 0 && val_ty != 1))
		return -1;
	
	buf_len = *len = 0;
	ret = 0;
	
	if(val_ty == 0){ /* integer */
		p = str;
		out_l = NULL;
		
		while(*p != '\0'){
			if(buf_len == *len){
				if(buf_len == 0)
					buf_len = 2;
				else
					buf_len = *len << 1;
							
				if(buf_len < *len){
					ret = -3;
					goto error;
				}
	      
				out_l = realloc(out_l, buf_len * sizeof(int));
				if(!out_l){
					ret = -4;
					goto error;
				}
	      
			}
			/* convert the string to cpu number */
			q = NULL;
			*(((int*)out_l) + ((*len)++)) = strtol(p, &q, 10);
			
			//check if this is an valid number
			if(q == p){
				ret = -2;
				goto error;
			}
			
			//adjust indices
			p = (*q == '\0')? q:q + 1;
			
		}
	}
	else if(val_ty == 1){
		p = str;
		out_l = NULL;
		
		while(*p != '\0'){
			if(buf_len == *len){
				if(buf_len == 0)
					buf_len = 2;
				else
					buf_len = *len << 1;
				
				if(buf_len < *len){
					ret = -3;
					goto error;
				}
				
				out_l = realloc(out_l, buf_len * sizeof(float));
				if(!out_l){
					ret = -4;
					goto error;
				}
				
			}
			/* convert the string to cpu number */
			q = NULL;
			*(((float*)out_l) + ((*len)++)) = strtof(p, &q);
			
			//check if this is an valid number
			if(q == p){
				ret = -2;
				goto error;
			}
			
			//adjust indices
			p = (*q == '\0')? q:q + 1;
			
		}      

	}
  
	*out_list = out_l;
	return ret;
	
 error:
	if(out_l != NULL)
		free(out_l);
	
	return ret;
}

/* get thread id*/
pid_t gettid()
{
	pid_t tid = (pid_t) syscall(SYS_gettid);
	
	return tid;
}

/* see header file for help */
int parse_mem_size_str(char * mem_size_str, unsigned long long * mem_size)
{
	char * end = NULL;
	unsigned long long temp;
	
	if(mem_size_str == NULL || mem_size == NULL)
		return 2;
	
	temp = strtoull(mem_size_str, &end, 10);
  
	if(end == mem_size_str) /* non of the string is converted to ull */
		return 1;
	
	if(*end == 'K' || *end == 'k')
		temp *= 1024;
	else if(*end == 'M' || *end == 'm')
		temp *= 1024 * 1024;
	else if(*end == 'G' || *end == 'g')
	  temp *= 1024 * 1024 * 1024;
	else if(*end != 0 && *end != 'B' && *end != 'b') 
		/* there are still characters in the string */
		return 1;
	
	*mem_size = temp;
	
	return 0;
}


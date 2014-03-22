#include <stdio.h>
#include <stdlib.h>

#include "common_toolx.h"
#include "simple_hashx.h"

int main(int argc, char ** argv)
{  
  int call_number;
  
  if(argc != 3)
    {
      printf("needs parameters");
      exit(-1);
    }

  call_number = atoi(argv[1]);

  if(call_number == 1)
    {
      int * values;
      int len;
      int i, ret;

      ret = parse_value_list(argv[2], (void**)&values, &len, 0);
      
      if(ret != 0)
	{
	  printf("tool function error returned %d\n", ret);
	  exit(-1);
	}
      
      for(i = 0; i < len; i++)
	printf("cpu %d\n", values[i]);
    }
  else if(call_number == 2)
    {
      float * values;
      int len;
      int i, ret;
      
      ret = parse_value_list(argv[2], (void**)&values, &len, 1);
      
      if(ret != 0)
	{
	  printf("tool function error returned %d\n", ret);
	  exit(-1);
	}
      
      for(i = 0; i < len; i++)
	printf("cpu %f\n", values[i]);
    }
  else if(call_number == 3){
	  unsigned long long b, e, last;
	  int i, adder, max;
	  
	  max = atoi(argv[2]);
	  adder = 0;
	  b = rdtsc();
	  for(i = 0; i< max; i++)
		  adder += i;
	  e = rdtsc();
	  last = e -b;
	  printf("Result %d in %llu cycles\n", adder, last);
  }
  else if(call_number == 4){
	  long long len = 1000;
	  long long keys_len = 10000;
	  long long i;
	  long long val;
	  void * t = NULL;
	  int ret = 1;
	  
	  ret = initialize_simple_hashx(&t, len);

	  if(ret != 0){
		  printf("Init Error: %d\n", ret);
		  return ret;
	  }
		  
	  for(i = 0; i < keys_len; i++){
		  val = i + 12;

		  ret = save_val_simple_hashx(t, i, 0, val, NULL);
		  
		  if(ret != 0){
			  printf("Save Error %d\n", ret);
			  return ret;
		  }
	  }

	  for(i = 0; i < keys_len; i++){

		  ret = get_val_simple_hashx(t, i, 0, &val, NULL);
		  
		  if(ret != 0){
			  printf("Get Error %d\n", ret);
			  return ret;
		  }

		  if(val != i + 12){
			  printf("Wrong data: %lld->%lld\n", i, val);
			  return 4;
		  }
	  }

	  for(i = keys_len; i < keys_len + 1000; i++){

		  ret = get_val_simple_hashx(t, i, 0, &val, NULL);
		  
		  if(ret != 2){
			  printf("Found value for %lld\n", i);
			  return ret;
		  }

	  }
	  
  }
	  
      
  return 0;
}

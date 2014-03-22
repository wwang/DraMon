/*
 * This is an implementation of a simplest hashing table. Very rudimentry. The
 * table is just a very large array that holds linked lists. Hash function is 
 * index = key mod array_size. Only take 64-bits integer as key.
 * 
 * Author: Wei Wang (wwang@virginia.edu)
 */

#ifndef __COMMON_TOOLX_SIMPLE_HASHX__
#define __COMMON_TOOLX_SIMPLE_HASHX__

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Initialize a new hash table, and return a handle to this table.
 * 
 * Input parameters:
 *       len: expected length of the table.
 * Output parameters:
 *       hash_table: output the handle to the table
 * Return value;
 *       0: success
 *       1: fail, len is 0
 */
int initialize_simple_hashx(void ** hash_table, long long len);

/* 
 * Save a value into the hash table based on its key.
 *
 * Input parameters:
 *       hash_table: handle to the hash table
 *       key: the key of this value
 *       val_sel: indicating whether the value is a long long int (0) or
 *                a pointer (1)
 *       int_val: value in the form of long long int
 *       pointer: value in the form of a pointer. Users are responsible for
 *                freeing the memory associated with this pointer.
 * Return value:
 *       0: success
 *       1: fail, hash_table is NULL
 */
int save_val_simple_hashx(void * hash_table,
			  long long key, 
			  int val_sel, 
			  long long int_val, 
			  void* pointer);
/* 
 * Get a value from the hash table based on its key.
 *
 * Input parameters:
 *       hash_table: handle to the hash table
 *       key: the key of this value
 *       val_sel: indicating whether the value is a long long int (0) or
 *                a pointer (1)
 * Output parameters:
 *       int_val: value in the form of long long int
 *       pointer: value in the form of a pointer. Users are responsible for
 *                freeing the memory associated with this pointer.
 * Return value:
 *       0: success
 *       1: fail, hash_table is NULL
 *       2: fail, no record for current key
 *       3: fail, val is a pointer, but the parameter point is NULL
 */

int get_val_simple_hashx(void * hash_table,
			 long long key,
			 int val_sel,
			 long long * int_val,
			 void** pointer);

/*
 * Cleanup the hash table, and free associated memory
 * 
 * Input parameters:
 *       hash_table: handle to the table to free
 * Return value;
 *       0: success
 *       1: fail, hash_table is NULL
 */
int cleanup_simple_hashx(void* hast_table);

#ifdef __cplusplus
}
#endif

#endif

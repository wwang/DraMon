/*
 * An implementation of a simple hash table. See simple_hashx.h for help.
 *
 * Author: Wei Wang (wwang@virginia.edu)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "simple_hashx.h"

struct linked_list_item{
	struct linked_list_item* prev;
	struct linked_list_item* next;
	long long key;
	union item_val{
		long long int_val;
		void* pointer;
	}val;
	int valid;
};

struct simple_hashx_table{
	struct linked_list_item** table;
	long long len;
};

/*
 * Initialize a new hash table, and return a handle to this table.
 */
int initialize_simple_hashx(void ** hash_table, long long len)
{
	struct simple_hashx_table * t = NULL;

	*hash_table = NULL;
	if(len == 0)
		return 1;

	t = (struct simple_hashx_table*)malloc(sizeof(struct simple_hashx_table));

	t->len = len;
	t->table = (struct linked_list_item**)malloc(sizeof(void*)*len);
	
	memset((void*)t->table, 0, sizeof(void*)*len);
	
	*hash_table = (void *)t;

	return 0;
}

/* 
 * Save a value into the hash table based on its key.
 */
int save_val_simple_hashx(void * hash_table,
			  long long key, 
			  int val_sel, 
			  long long int_val, 
			  void* pointer)
{
	long long index;
	struct linked_list_item * item;
	struct linked_list_item * temp;
	struct simple_hashx_table * t = (struct simple_hashx_table*)hash_table;

	if(t == NULL)
		return 1;
	
	/* get the index */
	index = key % t->len;

	/* create space for this item */
	item = (struct linked_list_item*)malloc(
					   sizeof(struct linked_list_item));
	item->key = key;
	if(!val_sel)
		item->val.int_val = int_val;
	else
		item->val.pointer = pointer;
	item->valid = 1;

	/* insert into the linked list, make it the first item in the list*/
	temp = t->table[index];
	item->next = temp;
	item->prev = NULL;
	if(temp)
		temp->prev = item;
	t->table[index] = item;

	return 0;
}
/* 
 * Get a value from the hash table based on its key.
 */

int get_val_simple_hashx(void * hash_table,
			 long long key,
			 int val_sel,
			 long long * int_val,
			 void** pointer)
{
	long long index;
	struct linked_list_item * cur_item;
	struct simple_hashx_table * t = (struct simple_hashx_table*)hash_table;
	
	if(t == NULL)
		return 1;
	if(val_sel != 0 && pointer == NULL)
		return 3;
	
	/* get the index */
	index = key % t->len;
	
	cur_item = t->table[index];

	while(cur_item){
		if(cur_item->key == key) /* found the right one */
			break;
		else
			cur_item = cur_item->next;
	}

	if(cur_item == NULL)
		return 2; /* key not found */

	if(!val_sel)
		*int_val = cur_item->val.int_val;
	else
		*pointer = cur_item->val.pointer;

	return 0;
}

/*
 * Cleanup the hash table, and free associated memory
 */
int cleanup_simple_hashx(void* hash_table)
{
	struct simple_hashx_table *t = (struct simple_hashx_table*)hash_table;
	long long i;
	struct linked_list_item *p, *q;

	if(t == NULL || t->table == NULL)
		return 1;
	
	for(i = 0; i < t->len; i++){
		p = t->table[i];
		while(p){
			q = p;
			p = p->next;
			free(q);
		}	      
	}
	
	free(t->table);
	free(t);
	
	return 0;
}

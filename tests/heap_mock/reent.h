#pragma once
#include <stddef.h>
struct _reent {
    int _errno;
};
extern struct _reent test_reent;
#define _REENT (&test_reent)
void* __wrap__malloc_r(struct _reent*, size_t);
void* __wrap__calloc_r(struct _reent*, size_t, size_t);
void* __wrap__realloc_r(struct _reent*, void*, size_t);
void __wrap__free_r(struct _reent*, void*);
#define _malloc_r __wrap__malloc_r
#define _calloc_r __wrap__calloc_r
#define _free_r __wrap__free_r

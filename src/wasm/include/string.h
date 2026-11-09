#ifndef SHIM_STRING
#define SHIM_STRING
typedef __SIZE_TYPE__ size_t;
void *memset(void *,int,size_t);
void *memcpy(void *,const void *,size_t);
#endif

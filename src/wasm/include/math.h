#ifndef SHIM_MATH
#define SHIM_MATH
#define isfinite __builtin_isfinite
#define fabsf __builtin_fabsf
#define INFINITY __builtin_inff()
#define NAN __builtin_nanf("")
#endif

#pragma once
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define LWIP_DONT_PROVIDE_BYTEORDER_FUNCTIONS
#define LWIP_PLATFORM_DIAG(x)                                                                      \
    do {                                                                                           \
        printf x;                                                                                  \
    } while (0)
#define LWIP_PLATFORM_ASSERT(x)                                                                    \
    do {                                                                                           \
        fprintf(stderr, "%s\n", x);                                                                \
        abort();                                                                                   \
    } while (0)

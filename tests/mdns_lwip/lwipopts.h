#pragma once
// Exercise the firmware pool/timer/network options with a deterministic clock.
#include "standalone/pico/lwipopts.h"
#undef MEM_ALIGNMENT
#define MEM_ALIGNMENT 8
#undef LWIP_STATS
#define LWIP_STATS 1
#define MEM_STATS 1
#define MEMP_STATS 1
#define LWIP_RAND() 0U
#define SYS_LIGHTWEIGHT_PROT 0

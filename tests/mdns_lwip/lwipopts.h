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
// DNS requires a usable randomized source port; a permanent zero never exits
// its minimum-port loop. Keep mDNS timing deterministic and DNS IDs distinct.
static inline unsigned short wsprry_lwip_dns_random(void) {
    static unsigned short value = 49152;
    return ++value;
}
#define DNS_RAND_TXID() wsprry_lwip_dns_random()
#define SYS_LIGHTWEIGHT_PROT 0

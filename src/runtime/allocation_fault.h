#pragma once
#include <stdbool.h>
#include <stdint.h>

// SDK scratch 4..7 is reserved. For an allocation panic, use scratch 0 and 3
// instead of the hardfault status/PC pair. A tag distinguishes old zero records.
#define WSPRRY_ALLOCATION_FAULT_HASH UINT32_C(3833354787)
#define WSPRRY_ALLOCATION_FAULT_TAG UINT32_C(0xa110ca00)

static inline bool wsprry_allocation_fault_valid(bool recovery, uint32_t hash, uint32_t tag) {
    return recovery && hash == WSPRRY_ALLOCATION_FAULT_HASH &&
           (tag == WSPRRY_ALLOCATION_FAULT_TAG || tag == (WSPRRY_ALLOCATION_FAULT_TAG | 1U));
}

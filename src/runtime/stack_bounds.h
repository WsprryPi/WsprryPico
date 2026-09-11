#pragma once
#include <stdbool.h>
#include <stdint.h>

#define WSPRRY_STACK_RESERVE_BYTES 4096u

// RP2350 SRAM and the two explicitly eight-byte-aligned MSP stack allocations.
// Reject wraparound and an already-consumed reserve before touching MSPLIM.
static inline uintptr_t wsprry_stack_limit_for(uintptr_t bottom, uintptr_t sp) {
    if ((bottom & 7u) || bottom < 0x20000000u || bottom > 0x20081000u || sp > 0x20082000u ||
        sp <= bottom + WSPRRY_STACK_RESERVE_BYTES)
        return 0;
    return bottom + WSPRRY_STACK_RESERVE_BYTES;
}

static inline bool wsprry_stack_limit_matches(uintptr_t bottom, uintptr_t limit, uintptr_t sp,
                                              uint32_t control) {
    // MSP and privileged execution; FPCA does not change which stack is active.
    return (control & 3u) == 0 && wsprry_stack_limit_for(bottom, sp) == limit && limit != 0;
}

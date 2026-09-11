// Project-owned RP2350 Arm MSP reserve. Called by the SDK's existing core-0
// newlib initialization and core-1 wrapper, before their application work.
#include "runtime/pico/stack_guard.h"

#include "hardware/structs/m33.h"
#include "hardware/structs/watchdog.h"
#include "pico/platform.h"
#include "runtime/stack_bounds.h"

#if !defined(__ARM_ARCH_8M_MAIN__) || PICO_RP2040 || defined(__riscv)
#error "The Phase 11.5 MSP reserve is specific to RP2350 Arm Cortex-M33"
#endif

static uintptr_t stack_bottom[2];

static void __attribute__((noreturn)) invalid_guard(void) {
    watchdog_hw->scratch[2] = 0x53544744u; // STGD: stack-guard setup/readback failed.
    for (;;)
        __asm volatile("nop");
}

// SDK implementation is excluded explicitly for these two images. This is the
// same MSPLIM mechanism it uses on RP2350, moved up by the required reserve.
void runtime_init_per_core_install_stack_guard(void* bottom) {
    uintptr_t sp;
    uint32_t control;
    __asm volatile("mrs %0, msp" : "=r"(sp));
    __asm volatile("mrs %0, control" : "=r"(control));
    const uintptr_t limit = wsprry_stack_limit_for((uintptr_t)bottom, sp);
    if (!limit || (control & 3u))
        invalid_guard();
    stack_bottom[get_core_num()] = (uintptr_t)bottom;
    __asm volatile("msr msplim, %0\n\tisb" : : "r"(limit) : "memory");
    if (!wsprry_stack_guard_snapshot().valid)
        invalid_guard();
}

wsprry_stack_guard wsprry_stack_guard_snapshot(void) {
    wsprry_stack_guard result;
    result.bottom = stack_bottom[get_core_num()];
    __asm volatile("mrs %0, msplim" : "=r"(result.limit));
    __asm volatile("mrs %0, msp" : "=r"(result.sp));
    __asm volatile("mrs %0, control" : "=r"(result.control));
    result.fault_status = m33_hw->cfsr;
    result.valid =
        wsprry_stack_limit_matches(result.bottom, result.limit, result.sp, result.control) &&
        !(result.fault_status & M33_CFSR_UFSR_STKOF_BITS);
    return result;
}

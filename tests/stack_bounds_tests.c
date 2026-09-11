#include "runtime/stack_bounds.h"

#include <assert.h>
#include <stdint.h>

int main(void) {
    // Both actual allocation styles: linker stack and a BSS worker stack.
    assert(wsprry_stack_limit_for(0x2007c000u, 0x2007ff00u) == 0x2007d000u);
    assert(wsprry_stack_limit_for(0x20003488u, 0x20007440u) == 0x20004488u);
    assert(wsprry_stack_limit_matches(0x2007c000u, 0x2007d000u, 0x2007ff00u, 4));
    // A below-reserve or foreign/disabled limit cannot be reported as protected.
    assert(!wsprry_stack_limit_matches(0x2007c000u, 0, 0x2007ff00u, 0));
    assert(!wsprry_stack_limit_matches(0x2007c000u, 0x2007c000u, 0x2007ff00u, 0));
    assert(!wsprry_stack_limit_matches(0x2007c000u, 0x2007d000u, 0x2007d000u, 0));
    assert(!wsprry_stack_limit_matches(0x2007c000u, 0x2007d000u, 0x2007cf00u, 0));
    assert(!wsprry_stack_limit_matches(0x2007c000u, 0x2007d000u, 0x2007ff00u, 2));
    assert(!wsprry_stack_limit_matches(0x2007c000u, 0x2007d000u, 0x2007ff00u, 1));
    assert(!wsprry_stack_limit_for(0x10000000u, 0x2007ff00u));
    assert(!wsprry_stack_limit_for(0x2007c001u, 0x2007ff00u));
    assert(!wsprry_stack_limit_for(0x20081000u, 0x20082008u));
    assert(!wsprry_stack_limit_for(UINTPTR_MAX - 7u, UINTPTR_MAX));
    assert(!wsprry_stack_limit_for(0, 0));
    return 0;
}

// SPDX-License-Identifier: MIT
// RF images already wrap this operation with their worker-owner exclusion.
#ifndef WSPRRY_PICO_STANDALONE_RF
#include "pico.h"
#include "time/capture_gap.hpp"

#include <cstdint>

extern "C" int __real_flash_safe_execute(void (*)(void*), void*, std::uint32_t);
extern "C" int __wrap_flash_safe_execute(void (*operation)(void*), void* context,
                                         std::uint32_t timeout_ms) {
    wsprrypico::time::CaptureGap capture_gap(get_core_num() == 0);
    return __real_flash_safe_execute(operation, context, timeout_ms);
}
#endif

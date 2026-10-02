#include "runtime/pico/btstack_pool_metrics.hpp"

#include "btstack.h"
#include "btstack_memory.h"
#include "pico.h"

// Project-owned observation wrappers around public pinned BTstack APIs.
// Called exclusively by foreground core 0. No upstream source is copied.
namespace {
wsprrypico::runtime::PoolMetrics<MAX_NR_HCI_CONNECTIONS> hci;
wsprrypico::runtime::PoolMetrics<MAX_NR_L2CAP_CHANNELS> channels;
wsprrypico::runtime::PoolMetrics<MAX_NR_L2CAP_SERVICES> services;
wsprrypico::runtime::PoolMetrics<MAX_NR_SM_LOOKUP_ENTRIES> sm;
wsprrypico::runtime::PoolMetrics<MAX_NR_WHITELIST_ENTRIES> whitelist;
} // namespace
#define POOL_WRAPPERS(name, type, ledger)                                                          \
    extern "C" type* __real_btstack_memory_##name##_get(void);                                     \
    extern "C" void __real_btstack_memory_##name##_free(type*);                                    \
    extern "C" type* __wrap_btstack_memory_##name##_get(void) {                                    \
        auto* pointer = __real_btstack_memory_##name##_get();                                      \
        if (!ledger.allocated(pointer))                                                            \
            panic("BTstack pool allocation accounting fault");                                     \
        return pointer;                                                                            \
    }                                                                                              \
    extern "C" void __wrap_btstack_memory_##name##_free(type* pointer) {                           \
        if (!ledger.released(pointer))                                                             \
            panic("BTstack pool release accounting fault");                                        \
        __real_btstack_memory_##name##_free(pointer);                                              \
    }
POOL_WRAPPERS(hci_connection, hci_connection_t, hci)
POOL_WRAPPERS(l2cap_channel, l2cap_channel_t, channels)
POOL_WRAPPERS(l2cap_service, l2cap_service_t, services)
POOL_WRAPPERS(sm_lookup_entry, sm_lookup_entry_t, sm)
POOL_WRAPPERS(whitelist_entry, whitelist_entry_t, whitelist)
#undef POOL_WRAPPERS
namespace wsprrypico::runtime {
std::array<PoolSnapshot, 5> btstack_pool_snapshot() {
    return {hci.snapshot(), channels.snapshot(), services.snapshot(), sm.snapshot(),
            whitelist.snapshot()};
}
} // namespace wsprrypico::runtime

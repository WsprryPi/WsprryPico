#include "provisioning/pico/phase12_fault_fixture.hpp"

#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "pico/platform.h"

#if !defined(WSPRRY_PICO_PHASE12_FAULT_STAGE) || WSPRRY_PICO_PHASE12_FAULT_STAGE < 1 ||            \
    WSPRRY_PICO_PHASE12_FAULT_STAGE > 10
#error "Explicit finite Phase 12 fault stage required"
#endif
#if defined(WSPRRY_PICO_STANDALONE_RF) || WSPRRY_PICO_RF_OUTPUT_DISABLED != 1
#error "Phase 12 fault fixture must be RF inhibited"
#endif
namespace wsprrypico::provisioning {
namespace {
constexpr std::uint32_t marker = 0x50313200u + WSPRRY_PICO_PHASE12_FAULT_STAGE;
bool consumed = false;
void checkpoint(unsigned stage) {
    if (stage != WSPRRY_PICO_PHASE12_FAULT_STAGE || consumed)
        return;
    consumed = true;
    watchdog_hw->scratch[0] = marker;
    // Cut only outside the flash safe zone, after the real durable write.
    // A deliberate reboot never authorizes another destructive request.
    watchdog_reboot(0, 0, 1);
    while (true)
        tight_loop_contents();
}
} // namespace
void phase12_fault_capture_boot() {
    consumed = watchdog_caused_reboot() && watchdog_hw->scratch[0] == marker;
}
unsigned phase12_fault_stage() {
    return WSPRRY_PICO_PHASE12_FAULT_STAGE;
}
bool phase12_fault_consumed() {
    return consumed;
}
void phase12_fault_restore_marker() {
    if (consumed)
        watchdog_hw->scratch[0] = marker;
}
void phase12_reset_checkpoint(ResetCheckpoint stage) {
    checkpoint(static_cast<unsigned>(stage));
}
void phase12_profile_programmed(std::size_t offset) {
    const auto page = offset % profile_slot_size;
    if (page == profile_page_size)
        checkpoint(8); // first payload page
    else if (page == 0)
        checkpoint(9); // complete header, before commit marker
    else if (page == profile_slot_size - profile_page_size)
        checkpoint(10); // complete commit marker, before readback/activation
}
} // namespace wsprrypico::provisioning

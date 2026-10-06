#include "provisioning/pico/phase12_fault_fixture.hpp"

#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "pico/platform.h"
#ifdef WSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE
#include "pico/time.h"
#include "tusb.h"
#include "usb/roles.h"
#include "usb/transport.hpp"
#if WSPRRY_PICO_PHASE12_FAULT_STAGE != 1 && WSPRRY_PICO_PHASE12_FAULT_STAGE != 9
#error "Physical cut pause requires completed reset intent or precommit profile header"
#endif
#endif

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
#ifdef WSPRRY_PICO_PHASE12_PHYSICAL_CUT_FIXTURE
    // The observer opens Console before the one mutation. Service USB delivery,
    // never command dispatch, while the operator removes all power. Human
    // readiness and power removal have no expiry; machine checks are bounded
    // by the controller outside this wait.
    constexpr auto cue = WSPRRY_PICO_PHASE12_FAULT_STAGE == 1
                             ? "{\"phase12_physical_cut_ready\":1}\n"
                             : "{\"phase12_physical_cut_ready\":9}\n";
    bool queued = false;
    while (true) {
        tud_task();
        usb::service();
        if (!queued && usb::console_connected())
            queued = usb::console_write(cue);
        // No WTP, Console or network request is dispatched during the pause.
        watchdog_update();
        tight_loop_contents();
    }
#endif
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

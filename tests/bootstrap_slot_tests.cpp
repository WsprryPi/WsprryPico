#include "network/bootstrap_slot.hpp"

#include <cassert>

using wsprrypico::network::BootstrapSlot;
using wsprrypico::network::BootstrapSlotBinding;
using wsprrypico::network::BootstrapSlotState;

namespace {
BootstrapSlotBinding binding() {
    return {"device", "boot", "slot", "browser-key", "nonce"};
}
void fresh_press_and_single_use() {
    BootstrapSlot slot;
    assert(slot.start(binding(), 1'000, true, false));
    assert(!slot.start(binding(), 1'001, true, false)); // Competing start is busy.
    slot.sample(1'100, true, true);
    slot.sample(1'105, true, false); // Contact bounce is not a tap.
    assert(slot.state() == BootstrapSlotState::Identify);
    slot.sample(1'200, true, true);
    slot.sample(1'250, true, false);
    assert(slot.state() == BootstrapSlotState::Granted);
    assert(!slot.consume("device", "other-boot", "slot", "request", "digest", "box", 1'251));
    assert(!slot.consume("device", "boot", "other-slot", "request", "digest", "box", 1'251));
    assert(slot.consume("device", "boot", "slot", "request", "digest", "box", 1'252));
    assert(!slot.consume("device", "boot", "slot", "request", "digest", "box", 1'253));
    assert(slot.finish(true, 1'500));
    assert(slot.state() == BootstrapSlotState::Terminal);
    assert(slot.binding() == nullptr); // Ephemeral transcript fields are gone.
    assert(slot.request_id().empty());
    assert(slot.request_id_digest() == "digest");
    assert(!slot.acknowledge(false, 1'501));
    assert(slot.acknowledge(true, 1'502));
    assert(slot.state() == BootstrapSlotState::None);
    assert(!slot.acknowledge(true, 1'503));
}
void held_button_and_failure_paths() {
    BootstrapSlot slot;
    assert(!slot.start(binding(), 0, true, true));   // Boot-held/stale level.
    assert(!slot.start(binding(), 0, false, false)); // Unsafe flash coordination.
    assert(slot.start(binding(), 0, true, false));
    slot.sample(10, false, false);
    assert(slot.state() == BootstrapSlotState::None);
    assert(slot.start(binding(), 100, true, false));
    slot.sample(200, true, true);
    slot.sample(10'200, true, true); // Held over maximum duration.
    assert(slot.state() == BootstrapSlotState::None);
    assert(slot.start(binding(), 20'000, true, false));
    slot.sample(79'999, true, false);
    assert(slot.state() == BootstrapSlotState::Identify);
    slot.sample(80'000, true, true); // Tap window ended.
    assert(slot.state() == BootstrapSlotState::None);
}
void expiry_and_terminal_reconciliation() {
    BootstrapSlot slot;
    assert(slot.start(binding(), 0, true, false));
    slot.sample(100, true, true);
    slot.sample(150, true, false);
    assert(slot.state() == BootstrapSlotState::Granted);
    assert(!slot.consume("device", "boot", "slot", "request", "digest", "box", 180'000));
    assert(slot.state() == BootstrapSlotState::None);

    assert(slot.start(binding(), 200'000, true, false));
    slot.sample(200'100, true, true);
    slot.sample(200'150, true, false);
    assert(slot.consume("device", "boot", "slot", "request", "digest", "box", 200'151));
    assert(slot.finish(false, 200'200));
    assert(!slot.acknowledge(true, 200'201)); // Failure cannot withdraw AP.
    slot.expire(260'200);
    assert(slot.state() == BootstrapSlotState::None);
}
} // namespace

int main() {
    fresh_press_and_single_use();
    held_button_and_failure_paths();
    expiry_and_terminal_reconciliation();
}

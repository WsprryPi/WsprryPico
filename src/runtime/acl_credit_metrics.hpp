#pragma once
#include <algorithm>
#include <cstdint>

namespace wsprrypico::runtime {
struct AclCreditSnapshot {
    bool initialized = false, measured = false;
    std::uint16_t capacity = 0, free = 0, min_free = 0, peak_outstanding = 0;
    std::uint64_t epoch = 0, send_events = 0, completed_events = 0, invalid_samples = 0,
                  transport_failures = 0;
};
// Core-0 only. These are host-accounted controller-reported HCI credits, not
// controller RAM occupancy. Capacity requires a working controller with no
// connections. Faults remain sticky across power cycles; epoch extrema do not.
class AclCreditMetrics {
  public:
    void observe(bool working, bool no_connections, std::uint16_t free) {
        if (!working) {
            value_.initialized = false;
            value_.capacity = value_.free = value_.min_free = value_.peak_outstanding = 0;
            return;
        }
        if (!value_.initialized) {
            if (!no_connections)
                return;
            if (!free || free > 255) {
                ++value_.invalid_samples;
                return;
            }
            value_.initialized = true;
            ++value_.epoch;
            value_.capacity = value_.min_free = free;
        }
        if (free > value_.capacity) {
            ++value_.invalid_samples;
            return;
        }
        value_.free = free;
        value_.min_free = std::min(value_.min_free, free);
        value_.peak_outstanding =
            std::max(value_.peak_outstanding, std::uint16_t(value_.capacity - free));
    }
    void sent() {
        ++value_.send_events;
        if (!value_.initialized)
            ++value_.invalid_samples;
    }
    void completed(bool valid, bool positive_return = true) {
        // A legal empty/zero return is not evidence that controller credits
        // were returned. Malformed events still poison measurement.
        if (valid && !positive_return)
            return;
        if (valid)
            ++value_.completed_events;
        if (!valid || !value_.initialized)
            ++value_.invalid_samples;
    }
    void transport_failed() {
        ++value_.transport_failures;
    }
    AclCreditSnapshot snapshot(bool hooked) const {
        auto result = value_;
        result.measured =
            hooked && result.initialized && !result.invalid_samples && !result.transport_failures;
        return result;
    }

  private:
    AclCreditSnapshot value_{};
};
} // namespace wsprrypico::runtime

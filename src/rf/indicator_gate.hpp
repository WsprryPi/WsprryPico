#pragma once

#include <atomic>
#include <cstdint>
#include <limits>

namespace wsprrypico::rf {
// One RF owner requests/cancels; one indicator owner acknowledges checked on
// writes. Tickets never repeat, so a delayed write cannot authorize a new run.
// No indicator/SDK work is performed by the RF owner or its launch interrupt.
class IndicatorGate {
  public:
    explicit IndicatorGate(bool enabled = true) : enabled_(enabled) {}
    bool enabled() const {
        return enabled_;
    }
    bool request_launch() {
        if (!enabled_)
            return true;
        auto ticket = requested();
        if (!ticket) {
            if (next_ == std::numeric_limits<std::uint32_t>::max())
                return false; // Fail closed rather than reuse an acknowledgement.
            ticket = ++next_;
            requested_.store(ticket, std::memory_order_release);
        }
        return acknowledged_.load(std::memory_order_acquire) == ticket;
    }
    void inactive() {
        requested_.store(0, std::memory_order_release);
    }
    std::uint32_t requested() const {
        return requested_.load(std::memory_order_acquire);
    }
    void acknowledge(std::uint32_t ticket) {
        if (ticket)
            acknowledged_.store(ticket, std::memory_order_release);
    }
    bool ready() const {
        const auto ticket = requested();
        return !enabled_ || (ticket && acknowledged_.load(std::memory_order_acquire) == ticket);
    }

  private:
    const bool enabled_;
    std::uint32_t next_ = 0; // RF owner only.
    std::atomic<std::uint32_t> requested_{0}, acknowledged_{0};
};
static_assert(std::atomic<std::uint32_t>::is_always_lock_free);
} // namespace wsprrypico::rf

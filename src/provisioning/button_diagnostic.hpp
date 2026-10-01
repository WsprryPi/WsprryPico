#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {

struct DiagnosticButtonEvents {
    bool request_reset = false;
    bool request_stop = false;
    bool request_setup_ap = false;
    bool released = false;
    std::uint64_t duration_us = 0;
};

// GP14 active-low input policy for the separate, output-inhibited diagnostic.
// Presses must be stable for 10 ms; releases for 100 ms so a brief open contact
// does not split a hold into a reset and another gesture. A level already low
// at boot is ignored until released, avoiding a reset loop on a fitted jumper.
// No action is executed.
class ButtonDiagnostic {
  public:
    static constexpr std::uint64_t debounce_us = 10'000;
    static constexpr std::uint64_t release_debounce_us = 100'000;
    static constexpr std::uint64_t reset_limit_us = 400'000;
    static constexpr std::uint64_t stop_limit_us = 900'000;
    static constexpr std::uint64_t ap_limit_us = 9'000'000;

    DiagnosticButtonEvents observe(std::uint64_t now_us, bool pressed) {
        DiagnosticButtonEvents events;
        if (fault_)
            return events;
        if (!initialized_) {
            initialized_ = true;
            raw_pressed_ = stable_pressed_ = pressed;
            armed_ = !pressed;
            changed_at_us_ = last_us_ = now_us;
            return events;
        }
        if (now_us < last_us_) {
            fault_ = true;
            return events;
        }
        last_us_ = now_us;
        if (pressed != raw_pressed_) {
            raw_pressed_ = pressed;
            changed_at_us_ = now_us;
        }
        const auto stable_for_us = raw_pressed_ ? debounce_us : release_debounce_us;
        if (raw_pressed_ != stable_pressed_ && now_us - changed_at_us_ >= stable_for_us) {
            stable_pressed_ = raw_pressed_;
            if (stable_pressed_) {
                if (armed_) {
                    active_ = true;
                    pressed_at_us_ = changed_at_us_;
                    stop_emitted_ = setup_emitted_ = false;
                }
            } else {
                armed_ = true;
                if (active_) {
                    const auto duration = changed_at_us_ - pressed_at_us_;
                    events.released = true;
                    events.duration_us = duration;
                    if (duration < reset_limit_us)
                        events.request_reset = true;
                    if (duration >= reset_limit_us && !stop_emitted_)
                        events.request_stop = true;
                    if (duration >= ap_limit_us && !setup_emitted_)
                        events.request_setup_ap = true;
                    active_ = false;
                }
            }
        }
        if (active_ && raw_pressed_) {
            // Thresholds are time-based, not release-based. An indefinite low
            // level emits each request once and does not block later service.
            const auto duration = now_us - pressed_at_us_;
            events.duration_us = duration;
            if (duration >= stop_limit_us && !stop_emitted_) {
                events.request_stop = true;
                stop_emitted_ = true;
            }
            if (duration >= ap_limit_us && !setup_emitted_) {
                events.request_setup_ap = true;
                setup_emitted_ = true;
            }
        }
        return events;
    }

    [[nodiscard]] bool held() const {
        return stable_pressed_;
    }
    [[nodiscard]] bool active() const {
        return active_;
    }
    [[nodiscard]] bool fault() const {
        return fault_;
    }

  private:
    std::uint64_t changed_at_us_ = 0;
    std::uint64_t pressed_at_us_ = 0;
    std::uint64_t last_us_ = 0;
    bool initialized_ = false;
    bool armed_ = false;
    bool raw_pressed_ = false;
    bool stable_pressed_ = false;
    bool active_ = false;
    bool stop_emitted_ = false;
    bool setup_emitted_ = false;
    bool fault_ = false;
};

} // namespace wsprrypico::provisioning

#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {

enum class ButtonAction { None, StopOutput, OpenSetupAp, Fault };

// Portable policy for a debounced runtime button level. The Pico adapter must
// capture the complete press/release safely. This policy does not make BOOTSEL
// safe to sample while either core may access external flash.
class ButtonControl {
  public:
    static constexpr std::uint64_t minimum_press_ms = 20;
    static constexpr std::uint64_t short_press_limit_ms = 1'000;
    static constexpr std::uint64_t long_press_limit_ms = 9'000;

    ButtonAction observe(std::uint64_t now_ms, bool pressed) {
        if (fault_)
            return ButtonAction::Fault;
        if (awaiting_shutdown_) {
            if (pressed) {
                fault_ = true;
                return ButtonAction::Fault;
            }
            return ButtonAction::None;
        }
        if (!held_) {
            if (!pressed)
                return ButtonAction::None;
            held_ = true;
            pressed_at_ms_ = now_ms;
            return ButtonAction::None;
        }
        if (now_ms < pressed_at_ms_) {
            fault_ = true;
            return ButtonAction::Fault;
        }
        if (pressed)
            return ButtonAction::None;
        held_ = false;
        const auto duration = now_ms - pressed_at_ms_;
        if (duration < minimum_press_ms)
            return ButtonAction::None;
        if (duration >= short_press_limit_ms && duration <= long_press_limit_ms)
            return ButtonAction::None;
        awaiting_shutdown_ = true;
        pending_setup_ = duration > long_press_limit_ms;
        return ButtonAction::StopOutput;
    }

    // shutdown_complete covers autonomous scheduling, JobService and the
    // physical engine. The adapter must finish shutdown after release and
    // before admitting a manual AP lease.
    ButtonAction complete_shutdown(bool shutdown_complete) {
        if (fault_ || !awaiting_shutdown_)
            return ButtonAction::Fault;
        awaiting_shutdown_ = false;
        if (!shutdown_complete) {
            fault_ = true;
            return ButtonAction::Fault;
        }
        const bool open_setup = pending_setup_;
        pending_setup_ = false;
        return open_setup ? ButtonAction::OpenSetupAp : ButtonAction::None;
    }

    [[nodiscard]] bool held() const {
        return held_;
    }
    [[nodiscard]] bool fault() const {
        return fault_;
    }
    [[nodiscard]] bool awaiting_shutdown() const {
        return awaiting_shutdown_;
    }

  private:
    std::uint64_t pressed_at_ms_ = 0;
    bool held_ = false;
    bool awaiting_shutdown_ = false;
    bool pending_setup_ = false;
    bool fault_ = false;
};
} // namespace wsprrypico::provisioning

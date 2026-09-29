#pragma once

#include "provisioning/button_diagnostic.hpp"

#include <cstdint>
#include <utility>

namespace wsprrypico::provisioning {

// Dispatches a sampled gesture through one local output authority. The stop
// callback must latch admission inhibition, abort the job, disable the engine
// and confirm physical output inactivity. No callback runs in an interrupt.
template <class Stop, class Setup, class Release, class Reset> class ButtonRuntime {
  public:
    ButtonRuntime(Stop stop, Setup setup, Release release, Reset reset)
        : stop_(std::move(stop)), setup_(std::move(setup)), release_(std::move(release)),
          reset_(std::move(reset)) {}

    void observe(const DiagnosticButtonEvents& event, std::uint64_t now_ms, bool held) {
        if (fault_)
            return;
        if (event.released) {
            last_duration_us_ = event.duration_us;
            release_(now_ms);
        }
        stop_events_ += event.request_stop;
        setup_events_ += event.request_setup_ap;
        reset_events_ += event.request_reset;
        if ((event.request_stop || event.request_setup_ap || event.request_reset) &&
            !stop_attempted_) {
            stop_attempted_ = true;
            stop_verified_ = stop_();
        }
        if (event.request_setup_ap && stop_verified_) {
            ++setup_attempts_;
            if (setup_(now_ms, held))
                ++setup_accepts_;
        }
        if (event.request_reset && stop_verified_)
            reset_();
    }

    void capture_fault() {
        if (fault_)
            return;
        fault_ = true;
        stop_verified_ = false;
        (void)stop_();
    }

    [[nodiscard]] bool stop_verified() const {
        return stop_verified_;
    }
    [[nodiscard]] std::uint64_t last_duration_us() const {
        return last_duration_us_;
    }
    [[nodiscard]] std::uint32_t stop_events() const {
        return stop_events_;
    }
    [[nodiscard]] std::uint32_t setup_events() const {
        return setup_events_;
    }
    [[nodiscard]] std::uint32_t setup_attempts() const {
        return setup_attempts_;
    }
    [[nodiscard]] std::uint32_t setup_accepts() const {
        return setup_accepts_;
    }
    [[nodiscard]] std::uint32_t reset_events() const {
        return reset_events_;
    }

  private:
    Stop stop_;
    Setup setup_;
    Release release_;
    Reset reset_;
    std::uint64_t last_duration_us_ = 0;
    std::uint32_t stop_events_ = 0;
    std::uint32_t setup_events_ = 0;
    std::uint32_t setup_attempts_ = 0;
    std::uint32_t setup_accepts_ = 0;
    std::uint32_t reset_events_ = 0;
    bool stop_attempted_ = false;
    bool stop_verified_ = false;
    bool fault_ = false;
};

} // namespace wsprrypico::provisioning

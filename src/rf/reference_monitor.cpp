// SPDX-License-Identifier: MIT
#include "rf/reference_monitor.hpp"

#include <algorithm>

namespace wsprrypico::rf {
namespace {
std::uint64_t add(std::uint64_t value, std::uint64_t amount) {
    return value > UINT64_MAX - amount ? UINT64_MAX : value + amount;
}
} // namespace
ReferenceMonitor::ReferenceMonitor(const si5351::Configuration& config,
                                   const ReferencePolicy& policy, si5351::Device& device,
                                   ReferenceCapture& capture, Now now, void* context)
    : config_(config), policy_(policy), plan_(si5351::plan_reference(config)), device_(device),
      capture_(capture), now_(now), context_(context) {}
std::optional<ReferenceMeasurement> ReferenceMonitor::current() const {
    if (!now_ || inhibited_ || faulted_ || !latest_ ||
        !reference_fresh(*latest_, policy_, now_(context_), generation_))
        return {};
    return latest_;
}
std::string_view ReferenceMonitor::diagnostic() const {
    if (!inhibited_ && !faulted_ && latest_ && now_ &&
        !reference_fresh(*latest_, policy_, now_(context_), generation_))
        return "reference_measurement_stale";
    return error_;
}
void ReferenceMonitor::fault(std::string_view error) {
    error_ = error;
    latest_.reset();
    faulted_ = true;
    if (measuring_) {
        (void)capture_.finish();
        measuring_ = false;
    }
    // The caller must observe a failed pause/unknown register state; do not
    // spin, reset the chip, or pretend failed control established inactivity.
    (void)device_.reference_enabled(false, add(now_(context_), 5'000'000));
    retry_ns_ = add(now_(context_), 1'000'000'000);
}
bool ReferenceMonitor::pause(std::uint64_t deadline) {
    if (measuring_) {
        (void)capture_.finish(); // Interrupted windows are never published.
        measuring_ = false;
    }
    if (device_.reference_state() == si5351::ClockOutputState::RegisterDisabled)
        return true;
    if (!device_.configured()) {
        // Full quiescence is required when output control has become unknown.
        if (!device_.quiesce(deadline)) {
            latest_.reset();
            faulted_ = true;
            error_ = "reference_shutdown_unconfirmed";
            return false;
        }
        return true;
    }
    if (!device_.reference_enabled(false, deadline)) {
        latest_.reset();
        faulted_ = true;
        error_ = "reference_shutdown_unconfirmed";
        return false;
    }
    return true;
}
void ReferenceMonitor::inhibit() {
    inhibited_ = true;
    latest_.reset();
    error_ = "reference_inhibited";
}
void ReferenceMonitor::service(bool permitted) {
    if (!permitted || inhibited_ || !config_.loopback)
        return;
    if (!now_ || !plan_ || !valid_reference_policy(policy_)) {
        error_ = "invalid_reference_configuration";
        return;
    }
    const auto now = now_(context_);
    if (now < retry_ns_)
        return;
    if (measuring_) {
        if (!device_.configured()) {
            fault("reference_device_unconfigured");
            return;
        }
        if (!capture_.poll(generation_)) {
            fault(capture_.error().empty() ? "reference_capture_failed" : capture_.error());
            return;
        }
        if (now < started_ns_ || now - started_ns_ > policy_.maximum_window_ns) {
            fault("reference_window_expired");
            return;
        }
        if (now - started_ns_ < policy_.minimum_window_ns)
            return;
        const auto window = capture_.finish();
        measuring_ = false;
        const auto measured =
            measure_reference(window, plan_->output.achieved_hz, generation_, policy_);
        if (!device_.reference_enabled(false, add(now_(context_), 5'000'000))) {
            fault("reference_shutdown_unconfirmed");
            return;
        }
        if (!measured.valid()) {
            fault(measured.error);
            return;
        }
        latest_ = measured;
        error_ = {};
        faulted_ = false;
        // Start another bounded independent window on the next owner pass.
        return;
    }
    if (device_.transmit_state() != si5351::ClockOutputState::RegisterDisabled) {
        error_ = "reference_transmit_not_quiet";
        return;
    }
    if (!device_.configured()) {
        if (generation_ == UINT64_MAX) {
            inhibit();
            return;
        }
        ++generation_;
        latest_.reset();
        if (!device_.configure_reference(config_, *plan_, add(now, 40'000'000))) {
            fault("reference_configuration_failed");
            return;
        }
    }
    (void)device_.locked(add(now_(context_), 1'000'000));
    if (!device_.configured()) {
        fault("reference_lock_read_failed");
        return;
    }
    if (!device_.reference_locked()) {
        error_ = "reference_not_locked";
        retry_ns_ = add(now_(context_), 1'000'000);
        return;
    }
    if (!device_.reference_enabled(true, add(now_(context_), 5'000'000)) ||
        !capture_.begin(generation_)) {
        fault("reference_start_failed");
        return;
    }
    started_ns_ = now_(context_);
    measuring_ = true;
}
} // namespace wsprrypico::rf

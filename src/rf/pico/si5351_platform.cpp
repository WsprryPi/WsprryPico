// SPDX-License-Identifier: MIT
#include "rf/pico/si5351_platform.hpp"

#include "hardware/gpio.h"
#include "hardware/timer.h"
#include "pico/time.h"

namespace wsprrypico::rf::si5351 {
namespace {
ReferencePolicy policy(const hardware::Si5351Settings& settings) {
    ReferencePolicy value;
    value.use = settings.reference_use;
    value.trusted_uncertainty_ppb = settings.trusted_uncertainty_ppb;
    return value;
}
} // namespace
PicoExecutionPlatform* PicoExecutionPlatform::instance_ = nullptr;
PicoExecutionPlatform::PicoExecutionPlatform(const hardware::PinPlan& pins,
                                             const hardware::Si5351Settings& settings,
                                             const hardware::FilterSettings& filters, PicoBus& bus,
                                             Device& device)
    : pins_(pins), settings_(settings), filters_(filters), bus_(bus),
      monitor_(settings.synthesis, policy(settings), device, capture_, raw_now, nullptr) {}
std::uint64_t PicoExecutionPlatform::raw_now(void*) {
    return time_us_64() * 1000ULL;
}
std::uint64_t PicoExecutionPlatform::now_ns() const {
    return raw_now(nullptr);
}
bool PicoExecutionPlatform::initialize() {
    if (!hardware::validate_si5351(pins_, settings_, 0, filters_).valid() ||
        (instance_ && instance_ != this))
        return false;
    if (!gate_initialized_) {
        if (settings_.gate) {
            const auto gp = *settings_.gate;
            gpio_init(gp);
            gpio_put(gp, !settings_.gate_active_high);
            gpio_set_dir(gp, GPIO_OUT);
            if (gpio_get(gp) != !settings_.gate_active_high)
                return false;
        }
        gate_initialized_ = true;
        gate_unknown_.store(false, std::memory_order_release);
    }
    if (!bus_.is_open() && !bus_.open(pins_, settings_, filters_))
        return false;
    if (settings_.loopback_input && !capture_opened_) {
        if (!capture_.open(pins_, settings_, filters_))
            return false;
        capture_opened_ = true;
    }
    if (alarm_ < 0) {
        alarm_ = hardware_alarm_claim_unused(false);
        if (alarm_ < 0)
            return false;
        instance_ = this;
        hardware_alarm_set_callback(static_cast<unsigned>(alarm_), cutoff);
    }
    return true;
}
bool PicoExecutionPlatform::set_gate(bool active) {
    if (!gate_initialized_ || (active && cutoff_expired_.load(std::memory_order_acquire)))
        return false;
    if (!settings_.gate)
        return true;
    gate_unknown_.store(true, std::memory_order_release);
    const auto gp = *settings_.gate;
    const auto level = active == settings_.gate_active_high;
    gpio_put(gp, level);
    if (gpio_get_function(gp) != GPIO_FUNC_SIO || !gpio_is_dir_out(gp) || gpio_get(gp) != level)
        return false;
    gate_active_.store(active, std::memory_order_release);
    gate_unknown_.store(false, std::memory_order_release);
    return true;
}
bool PicoExecutionPlatform::gate_active_or_unknown() const {
    return settings_.gate && (gate_unknown_.load(std::memory_order_acquire) ||
                              gate_active_.load(std::memory_order_acquire));
}
bool PicoExecutionPlatform::arm_cutoff(std::uint64_t end) {
    if (alarm_ < 0 || end > UINT64_MAX - 999 || end <= now_ns())
        return false;
    cutoff_expired_.store(false, std::memory_order_release);
    return !hardware_alarm_set_target(static_cast<unsigned>(alarm_),
                                      from_us_since_boot((end + 999) / 1000));
}
void PicoExecutionPlatform::cancel_cutoff() {
    if (alarm_ >= 0)
        hardware_alarm_cancel(static_cast<unsigned>(alarm_));
    cutoff_expired_.store(false, std::memory_order_release);
}
void PicoExecutionPlatform::cutoff(unsigned alarm) {
    auto* self = instance_;
    if (!self || static_cast<unsigned>(self->alarm_) != alarm)
        return;
    self->cutoff_expired_.store(true, std::memory_order_release);
    (void)self->set_gate(false);
}
bool PicoExecutionPlatform::pause_reference(std::uint64_t deadline) {
    return monitor_.pause(deadline);
}
void PicoExecutionPlatform::service_reference(bool permitted) {
    monitor_.service(permitted);
}
void PicoExecutionPlatform::inhibit_reference() {
    monitor_.inhibit();
}
} // namespace wsprrypico::rf::si5351

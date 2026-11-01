// SPDX-License-Identifier: MIT
#include "rf/si5351_device.hpp"

#include <algorithm>

namespace wsprrypico::rf::si5351 {
void Device::fault() {
    states_.fill(ClockOutputState::Unknown);
    configured_ = false;
    configuration_.reset();
    unassigned_outputs_disabled_ = false;
    transmit_locked_ = reference_locked_ = false;
    transmit_configured_ = transmit_primed_ = false;
    pending_ = Pending::None;
    enable_mask_.reset();
    transmit_control_.reset();
}
bool Device::checked_write(std::uint8_t reg, std::span<const std::uint8_t> bytes,
                           std::uint64_t deadline) {
    std::array<std::uint8_t, 8> observed{};
    if (bytes.empty() || bytes.size() > observed.size() || !bus_.write(reg, bytes, deadline) ||
        !bus_.read(reg, std::span(observed).first(bytes.size()), deadline) ||
        !std::equal(bytes.begin(), bytes.end(), observed.begin())) {
        fault();
        return false;
    }
    if (reg == 3 && bytes.size() == 1)
        enable_mask_ = bytes.front();
    if (reg == 16 + static_cast<unsigned>(transmit_) && bytes.size() == 1)
        transmit_control_ = bytes.front();
    return true;
}
bool Device::masked_write(std::uint8_t reg, std::uint8_t mask, std::uint8_t bits,
                          std::uint64_t deadline) {
    std::array<std::uint8_t, 1> value{};
    if (!bus_.read(reg, value, deadline)) {
        fault();
        return false;
    }
    value[0] = static_cast<std::uint8_t>((value[0] & ~mask) | (bits & mask));
    return checked_write(reg, value, deadline);
}
bool Device::quiesce(std::uint64_t deadline) {
    fault();
    const std::uint8_t disabled[]{0xff};
    bool good = checked_write(3, disabled, deadline);
    // Always attempt the independent powerdown mechanism as well, without
    // short-circuiting after a NACK or partial write.
    const std::uint8_t power[]{0x80, 0x80, 0x80};
    good = checked_write(16, power, deadline) && good;
    if (good) {
        states_.fill(ClockOutputState::RegisterDisabled);
        unassigned_outputs_disabled_ = true;
    }
    return good;
}
bool Device::configure(const Configuration& config, const Plan& plan, std::uint64_t deadline) {
    // Refuse unbound/incomplete plans before bus writes. The planner's register
    // values are internal trusted data, not an accepted wire representation.
    if (!validate(config).empty() || plan.configuration != config || !valid_plan(plan) ||
        config.loopback.has_value() != plan.loopback.has_value() ||
        config.loopback.has_value() != plan.loopback_pll.has_value())
        return false;
    const auto crystal = crystal_load_register(config);
    if (!crystal)
        return false;
    // A reference-only boot has already established this exact immutable
    // reference plan. Prepare PLLA without rewriting or resetting PLLB.
    const bool preserve_reference = configured_ && configuration_ == config;
    if (preserve_reference &&
        (pending_ != Pending::None || transmit_state() != ClockOutputState::RegisterDisabled))
        return false;
    if (!preserve_reference && !quiesce(deadline))
        return false;
    transmit_ = config.transmit;
    loopback_ = config.loopback;
    const std::uint8_t load[]{*crystal};
    if ((!preserve_reference &&
         (!masked_write(15, 0x0c, 0, deadline) || !checked_write(183, load, deadline) ||
          !masked_write(149, 0x80, 0, deadline) || !masked_write(24, 0x3f, 0, deadline))) ||
        !checked_write(26, plan.transmit_pll.registers, deadline) ||
        !masked_write(22, 0x40,
                      plan.transmit_pll.numerator == 0 && plan.transmit_pll.integer % 2 == 0 ? 0x40
                                                                                             : 0,
                      deadline))
        return false;
    if (loopback_ && !preserve_reference) {
        const auto output = static_cast<unsigned>(*loopback_);
        const std::uint8_t control[]{static_cast<std::uint8_t>(plan.loopback->control | 0x80)};
        if (!checked_write(34, plan.loopback_pll->registers, deadline) ||
            !checked_write(static_cast<std::uint8_t>(42 + output * 8),
                           plan.loopback->multisynth.registers, deadline) ||
            !masked_write(
                23, 0x40,
                plan.loopback_pll->numerator == 0 && plan.loopback_pll->integer % 2 == 0 ? 0x40 : 0,
                deadline) ||
            !checked_write(static_cast<std::uint8_t>(16 + output), control, deadline))
            return false;
    }
    // Reset bits self-clear; compare only the reserved bits, not the written
    // self-clearing value. Other reserved fields are preserved by the RMW.
    std::uint8_t previous = 0;
    if (!bus_.read(177, std::span(&previous, 1), deadline)) {
        fault();
        return false;
    }
    const std::uint8_t reset[]{static_cast<std::uint8_t>(
        (previous & 0x5f) | (loopback_ && !preserve_reference ? 0xa0 : 0x20))};
    if (!bus_.write(177, reset, deadline)) {
        fault();
        return false;
    }
    std::uint8_t observed = 0;
    if (!bus_.read(177, std::span(&observed, 1), deadline) ||
        (observed & 0x5f) != (previous & 0x5f)) {
        fault();
        return false;
    }
    configured_ = true;
    configuration_ = config;
    transmit_locked_ = false;
    if (!preserve_reference)
        reference_locked_ = false;
    transmit_configured_ = true;
    if (!transmit_tone(plan.tones().front(), deadline))
        return false;
    return true; // Lock acquisition is a separate, bounded owner operation.
}
bool Device::configure_reference(const Configuration& config, const ReferencePlan& plan,
                                 std::uint64_t deadline) {
    if (plan.configuration != config || !valid_reference_plan(plan))
        return false;
    const auto crystal = crystal_load_register(config);
    if (!crystal || !quiesce(deadline))
        return false;
    transmit_ = config.transmit;
    loopback_ = config.loopback;
    const auto output = static_cast<unsigned>(*loopback_);
    const std::uint8_t load[]{*crystal};
    const std::uint8_t control[]{static_cast<std::uint8_t>(plan.output.control | 0x80)};
    if (!masked_write(15, 0x0c, 0, deadline) || !checked_write(183, load, deadline) ||
        !masked_write(149, 0x80, 0, deadline) || !masked_write(24, 0x3f, 0, deadline) ||
        !checked_write(34, plan.pll.registers, deadline) ||
        !checked_write(static_cast<std::uint8_t>(42 + output * 8), plan.output.multisynth.registers,
                       deadline) ||
        !masked_write(23, 0x40, plan.pll.numerator == 0 && plan.pll.integer % 2 == 0 ? 0x40 : 0,
                      deadline) ||
        !checked_write(static_cast<std::uint8_t>(16 + output), control, deadline))
        return false;
    std::uint8_t previous = 0, observed = 0;
    if (!bus_.read(177, std::span(&previous, 1), deadline)) {
        fault();
        return false;
    }
    const std::uint8_t reset = static_cast<std::uint8_t>((previous & 0x5f) | 0x80);
    if (!bus_.write(177, std::span(&reset, 1), deadline) ||
        !bus_.read(177, std::span(&observed, 1), deadline) ||
        (observed & 0x5f) != (previous & 0x5f)) {
        fault();
        return false;
    }
    configured_ = true;
    configuration_ = config;
    return true;
}
bool Device::locked(std::uint64_t deadline) {
    if (!configured_)
        return false;
    std::uint8_t status = 0xff;
    if (!bus_.read(0, std::span(&status, 1), deadline)) {
        fault();
        return false;
    }
    // SYS_INIT and LOS_XTAL affect both PLLs. PLLB lock loss must not pretend
    // the independent transmit PLLA is lost, or authorize a reference output.
    transmit_locked_ = transmit_configured_ && !(status & 0xb0);
    reference_locked_ = loopback_ && !(status & 0xd0);
    return transmit_locked_;
}
bool Device::transmit_tone(const Tone& tone, std::uint64_t deadline) {
    if (!configured_ || !transmit_configured_ || pending_ != Pending::None || (tone.control & 0xa0))
        return false;
    const auto output = static_cast<unsigned>(transmit_);
    const bool active = states_[output] == ClockOutputState::RegisterEnabled;
    const std::uint8_t control[]{static_cast<std::uint8_t>(tone.control | (active ? 0 : 0x80))};
    transmit_primed_ = false;
    return checked_write(static_cast<std::uint8_t>(42 + output * 8), tone.multisynth.registers,
                         deadline) &&
           checked_write(static_cast<std::uint8_t>(16 + output), control, deadline);
}
bool Device::enabled(Output output, bool value, std::uint64_t deadline) {
    if (!configured_ || (value && pending_ != Pending::None) ||
        (value &&
         (output == transmit_ ? !transmit_locked_ || !transmit_configured_ : !reference_locked_)))
        return false;
    const auto index = static_cast<unsigned>(output);
    states_[index] = ClockOutputState::Unknown;
    if (value) {
        if (!masked_write(static_cast<std::uint8_t>(16 + index), 0x80, 0, deadline) ||
            !masked_write(3, static_cast<std::uint8_t>(1u << index), 0, deadline))
            return false;
    } else {
        // Try both shutdown mechanisms even when the mask write fails.
        const bool mask = masked_write(3, static_cast<std::uint8_t>(1u << index),
                                       static_cast<std::uint8_t>(1u << index), deadline);
        const bool power =
            masked_write(static_cast<std::uint8_t>(16 + index), 0x80, 0x80, deadline);
        if (!mask || !power)
            return false;
    }
    states_[index] = value ? ClockOutputState::RegisterEnabled : ClockOutputState::RegisterDisabled;
    if (output == transmit_) {
        pending_ = Pending::None;
        transmit_primed_ = false;
    }
    return true;
}
bool Device::prime_transmit(std::uint64_t deadline) {
    const auto index = static_cast<unsigned>(transmit_);
    if (!configured_ || !transmit_configured_ || !transmit_locked_ || pending_ != Pending::None ||
        states_[index] != ClockOutputState::RegisterDisabled || !enable_mask_ ||
        !(*enable_mask_ & (1u << index)))
        return false;
    if (transmit_primed_)
        return true;
    if (!verify_transmit(deadline) ||
        !masked_write(static_cast<std::uint8_t>(16 + index), 0x80, 0, deadline))
        return false;
    transmit_primed_ = true;
    return true;
}
bool Device::request_transmit_enabled(bool value, std::uint64_t deadline) {
    const auto index = static_cast<unsigned>(transmit_);
    if (!configured_ || !enable_mask_ ||
        (value &&
         (!transmit_configured_ || !transmit_primed_ || !transmit_locked_ ||
          pending_ != Pending::None || states_[index] != ClockOutputState::RegisterDisabled)))
        return false;
    const auto bit = static_cast<std::uint8_t>(1u << index);
    const auto mask = static_cast<std::uint8_t>(value ? *enable_mask_ & ~bit : *enable_mask_ | bit);
    states_[index] = ClockOutputState::Unknown;
    if (!bus_.write(3, std::span(&mask, 1), deadline)) {
        fault();
        return false;
    }
    enable_mask_ = mask;
    pending_ = value ? Pending::Enable : Pending::Disable;
    return true;
}
bool Device::verify_transmit(std::uint64_t deadline) {
    if (!configured_ || !enable_mask_)
        return false;
    std::uint8_t mask = 0, control = 0;
    const auto index = static_cast<unsigned>(transmit_);
    if (!bus_.read(3, std::span(&mask, 1), deadline) ||
        !bus_.read(static_cast<std::uint8_t>(16 + index), std::span(&control, 1), deadline) ||
        mask != *enable_mask_ || (transmit_control_ && control != *transmit_control_)) {
        fault();
        return false;
    }
    const bool enabled = !(mask & (1u << index)) && !(control & 0x80);
    if ((pending_ == Pending::Enable && !enabled) || (pending_ == Pending::Disable && enabled)) {
        fault();
        return false;
    }
    states_[index] =
        enabled ? ClockOutputState::RegisterEnabled : ClockOutputState::RegisterDisabled;
    transmit_control_ = control;
    transmit_primed_ = transmit_configured_ && !enabled && !(control & 0x80);
    pending_ = Pending::None;
    return true;
}
bool Device::transmit_enabled(bool value, std::uint64_t deadline) {
    return enabled(transmit_, value, deadline);
}
bool Device::reference_enabled(bool value, std::uint64_t deadline) {
    return loopback_ ? enabled(*loopback_, value, deadline) : !value;
}
} // namespace wsprrypico::rf::si5351

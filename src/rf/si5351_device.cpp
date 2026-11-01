// SPDX-License-Identifier: MIT
#include "rf/si5351_device.hpp"

#include <algorithm>

namespace wsprrypico::rf::si5351 {
void Device::fault() {
    states_.fill(ClockOutputState::Unknown);
    configured_ = false;
    unassigned_outputs_disabled_ = false;
    transmit_locked_ = reference_locked_ = false;
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
    if (!quiesce(deadline))
        return false;
    transmit_ = config.transmit;
    loopback_ = config.loopback;
    const std::uint8_t load[]{*crystal};
    if (!masked_write(15, 0x0c, 0, deadline) || !checked_write(183, load, deadline) ||
        !masked_write(149, 0x80, 0, deadline) || !masked_write(24, 0x3f, 0, deadline) ||
        !checked_write(26, plan.transmit_pll.registers, deadline) ||
        !masked_write(22, 0x40,
                      plan.transmit_pll.numerator == 0 && plan.transmit_pll.integer % 2 == 0 ? 0x40
                                                                                             : 0,
                      deadline))
        return false;
    if (loopback_) {
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
    const std::uint8_t reset[]{
        static_cast<std::uint8_t>((previous & 0x5f) | (loopback_ ? 0xa0 : 0x20))};
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
    if (!transmit_tone(plan.tones().front(), deadline))
        return false;
    return true; // Lock acquisition is a separate, bounded owner operation.
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
    transmit_locked_ = !(status & 0xb0);
    reference_locked_ = loopback_ && !(status & 0xd0);
    return transmit_locked_;
}
bool Device::transmit_tone(const Tone& tone, std::uint64_t deadline) {
    if (!configured_ || (tone.control & 0xa0))
        return false;
    const auto output = static_cast<unsigned>(transmit_);
    const bool active = states_[output] == ClockOutputState::RegisterEnabled;
    const std::uint8_t control[]{static_cast<std::uint8_t>(tone.control | (active ? 0 : 0x80))};
    return checked_write(static_cast<std::uint8_t>(42 + output * 8), tone.multisynth.registers,
                         deadline) &&
           checked_write(static_cast<std::uint8_t>(16 + output), control, deadline);
}
bool Device::enabled(Output output, bool value, std::uint64_t deadline) {
    if (!configured_ || (value && (output == transmit_ ? !transmit_locked_ : !reference_locked_)))
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
    return true;
}
bool Device::transmit_enabled(bool value, std::uint64_t deadline) {
    return enabled(transmit_, value, deadline);
}
bool Device::reference_enabled(bool value, std::uint64_t deadline) {
    return loopback_ ? enabled(*loopback_, value, deadline) : !value;
}
} // namespace wsprrypico::rf::si5351

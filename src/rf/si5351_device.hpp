// SPDX-License-Identifier: MIT
#pragma once
#include "rf/si5351_plan.hpp"

namespace wsprrypico::rf::si5351 {
class Bus {
  public:
    virtual ~Bus() = default;
    // Absolute raw-monotonic deadline applies to the complete transaction,
    // including repeated start/readback, not separately to every byte.
    virtual bool read(std::uint8_t reg, std::span<std::uint8_t>, std::uint64_t deadline_ns) = 0;
    virtual bool write(std::uint8_t reg, std::span<const std::uint8_t>,
                       std::uint64_t deadline_ns) = 0;
};
enum class ClockOutputState { Unknown, RegisterDisabled, RegisterEnabled };
// One execution owner. No method may run concurrently with symbol changes.
// These observations establish register control only, never physical RF state.
class Device {
  public:
    explicit Device(Bus& bus) : bus_(bus) {}
    Device(const Device&) = delete;
    Device& operator=(const Device&) = delete;
    bool quiesce(std::uint64_t deadline_ns);
    bool configure(const Configuration&, const Plan&, std::uint64_t deadline_ns);
    // Idle reference startup programs only PLLB and its assigned output; it
    // does not prepare a dummy transmit frequency or enable the TX clock.
    bool configure_reference(const Configuration&, const ReferencePlan&, std::uint64_t deadline_ns);
    bool locked(std::uint64_t deadline_ns);
    bool reference_locked() const {
        return reference_locked_;
    }
    bool transmit_tone(const Tone&, std::uint64_t deadline_ns);
    bool prime_transmit(std::uint64_t deadline_ns);
    // One bounded mask write. A successful ACK remains Unknown until verified;
    // it never establishes physical RF inactivity or terminal job success.
    bool request_transmit_enabled(bool, std::uint64_t deadline_ns);
    bool verify_transmit(std::uint64_t deadline_ns);
    bool transmit_configured() const {
        return transmit_configured_;
    }
    bool transmit_enabled(bool, std::uint64_t deadline_ns);
    bool reference_enabled(bool, std::uint64_t deadline_ns);
    ClockOutputState transmit_state() const {
        return states_[static_cast<unsigned>(transmit_)];
    }
    ClockOutputState reference_state() const {
        return loopback_                      ? states_[static_cast<unsigned>(*loopback_)]
               : unassigned_outputs_disabled_ ? ClockOutputState::RegisterDisabled
                                              : ClockOutputState::Unknown;
    }
    bool configured() const {
        return configured_;
    }

  private:
    bool checked_write(std::uint8_t, std::span<const std::uint8_t>, std::uint64_t);
    bool masked_write(std::uint8_t reg, std::uint8_t mask, std::uint8_t bits, std::uint64_t);
    bool enabled(Output, bool, std::uint64_t);
    void fault();
    Bus& bus_;
    std::array<ClockOutputState, 3> states_{ClockOutputState::Unknown, ClockOutputState::Unknown,
                                            ClockOutputState::Unknown};
    Output transmit_ = Output::Clk0;
    std::optional<Output> loopback_;
    std::optional<Configuration> configuration_;
    std::optional<Divider> transmit_pll_, transmit_multisynth_;
    bool configured_ = false;
    bool unassigned_outputs_disabled_ = false;
    bool transmit_locked_ = false, reference_locked_ = false;
    bool transmit_configured_ = false, transmit_primed_ = false;
    enum class Pending { None, Enable, Disable };
    Pending pending_ = Pending::None;
    std::optional<std::uint8_t> enable_mask_, transmit_control_;
};
} // namespace wsprrypico::rf::si5351

#pragma once

#include "provisioning/storage.hpp"

#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {

enum class ConsumerClaimState { None, Identify, Granted, Trial, Terminal };

struct ConsumerClaimBinding {
    std::string device_id;
    std::string boot_id;
    std::string slot_id;
    std::string owner_public_key;
    std::string browser_public_key;
    std::string browser_nonce;
    std::string origin;
    ProfileSource source = ProfileSource::LegacyBootstrap;
    std::uint64_t generation = 0;
    bool operator==(const ConsumerClaimBinding&) const = default;
};

// Portable one-transaction slot. The HTTP/Pico adapter independently validates
// the ephemeral P-256 point, X25519/AEAD transcript, exact journal/boot
// identity and idle output before start/consume. Legacy gesture helpers remain
// for their existing tests, but the open-AP setup route grants without them.
class ConsumerClaimSlot {
  public:
    static constexpr std::uint64_t physical_window_ms = 60'000;
    static constexpr std::uint64_t submit_window_ms = 60'000;
    static constexpr std::uint64_t trial_window_ms = 90'000;
    static constexpr std::uint64_t terminal_window_ms = 60'000;
    // Mechanical bounce and a stuck button are device-side limits, not a
    // timed action for the person performing the claim.
    static constexpr std::uint64_t minimum_press_ms = 20;
    static constexpr std::uint64_t maximum_press_ms = 10'000;

    ConsumerClaimSlot() = default;
    ~ConsumerClaimSlot() {
        cancel();
    }
    ConsumerClaimSlot(const ConsumerClaimSlot&) = delete;
    ConsumerClaimSlot& operator=(const ConsumerClaimSlot&) = delete;
    ConsumerClaimSlot(ConsumerClaimSlot&&) = delete;
    ConsumerClaimSlot& operator=(ConsumerClaimSlot&&) = delete;

    bool start(ConsumerClaimBinding binding, std::uint64_t now_ms, bool sampler_safe,
               bool button_pressed, bool idle_output);
    void sample(std::uint64_t now_ms, bool sampler_safe, bool button_pressed, bool idle_output);
    // The target's flash-safe callback observes the whole press and release
    // before returning to XIP. Its validity includes the bounded prompt
    // window; this transition must not resample a held BOOTSEL button.
    bool grant_captured(std::uint64_t now_ms, bool sampler_safe, bool valid_press,
                        std::uint32_t duration_ms, bool idle_output);
    // Open-AP setup starts only when the user submits the filled form. There
    // is no physical gesture or retained browser principal in this policy.
    bool grant_open_setup(std::uint64_t now_ms, bool idle_output);
    bool consume(const ConsumerClaimBinding& current, std::string_view request_id,
                 std::uint64_t now_ms, bool sampler_safe, bool idle_output);
    bool finish(bool committed, std::string_view request_sha256, std::uint64_t generation,
                std::uint64_t now_ms, bool idle_output);
    void expire(std::uint64_t now_ms);
    void cancel();

    ConsumerClaimState state() const {
        return state_;
    }
    const ConsumerClaimBinding* binding() const {
        return state_ == ConsumerClaimState::Identify || state_ == ConsumerClaimState::Granted ||
                       state_ == ConsumerClaimState::Trial
                   ? &binding_
                   : nullptr;
    }
    bool committed() const {
        return state_ == ConsumerClaimState::Terminal && committed_;
    }
    bool trial_request_matches(std::string_view request_id) const {
        return state_ == ConsumerClaimState::Trial && request_id_ == request_id;
    }
    std::uint64_t committed_generation() const {
        return committed() ? committed_generation_ : 0;
    }
    std::string_view request_sha256() const {
        return state_ == ConsumerClaimState::Terminal ? request_sha256_ : std::string_view{};
    }

  private:
    ConsumerClaimState state_ = ConsumerClaimState::None;
    ConsumerClaimBinding binding_;
    std::string request_id_;
    std::string request_sha256_;
    std::uint64_t started_ms_ = 0, pressed_ms_ = 0, granted_ms_ = 0, trial_ms_ = 0,
                  terminal_ms_ = 0, committed_generation_ = 0;
    bool saw_press_ = false, committed_ = false;
};
} // namespace wsprrypico::provisioning

#pragma once

#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::network {
enum class BootstrapSlotState { None, Identify, Granted, Trial, Terminal };

struct BootstrapSlotBinding {
    std::string device_id;
    std::string boot_id;
    std::string slot_id;
    std::string browser_public_key;
    std::string request_nonce;
};

// Portable authority state only. The target adapter owns ephemeral keys,
// cryptographic validation, flash and network I/O. Open setup grants a slot
// directly; the older physical-confirmation path remains for historical tests.
class BootstrapSlot {
  public:
    BootstrapSlot() = default;
    ~BootstrapSlot() {
        cancel();
    }
    BootstrapSlot(const BootstrapSlot&) = delete;
    BootstrapSlot& operator=(const BootstrapSlot&) = delete;
    BootstrapSlot(BootstrapSlot&&) = delete;
    BootstrapSlot& operator=(BootstrapSlot&&) = delete;
    static constexpr std::uint64_t tap_window_ms = 60'000;
    static constexpr std::uint64_t slot_window_ms = 180'000;
    static constexpr std::uint64_t terminal_window_ms = 60'000;
    static constexpr std::uint64_t minimum_press_ms = 20;
    static constexpr std::uint64_t maximum_press_ms = 10'000;

    bool start(BootstrapSlotBinding binding, std::uint64_t now_ms, bool sample_safe,
               bool button_pressed);
    bool grant_open_setup(std::uint64_t now_ms);
    void sample(std::uint64_t now_ms, bool sample_safe, bool button_pressed);
    bool consume(std::string_view device_id, std::string_view boot_id, std::string_view slot_id,
                 std::string_view request_id, std::string_view request_id_digest,
                 std::string_view ciphertext_digest, std::uint64_t now_ms);
    bool finish(bool committed, std::uint64_t now_ms);
    // The adapter validates exact request fields and the retained derived
    // HMAC verifier before passing valid_tag. Terminal state keeps no IDs.
    bool acknowledge(bool valid_tag, std::uint64_t now_ms);
    void cancel();
    void expire(std::uint64_t now_ms);

    BootstrapSlotState state() const {
        return state_;
    }
    const BootstrapSlotBinding* binding() const {
        return state_ == BootstrapSlotState::Identify || state_ == BootstrapSlotState::Granted ||
                       state_ == BootstrapSlotState::Trial
                   ? &binding_
                   : nullptr;
    }
    std::string_view request_id() const {
        return request_id_;
    }
    std::string_view request_id_digest() const {
        return request_id_digest_;
    }
    std::string_view ciphertext_digest() const {
        return ciphertext_digest_;
    }
    bool committed() const {
        return committed_;
    }

  private:
    BootstrapSlotState state_ = BootstrapSlotState::None;
    BootstrapSlotBinding binding_;
    std::string request_id_, request_id_digest_, ciphertext_digest_;
    std::uint64_t started_ms_ = 0, pressed_ms_ = 0, terminal_ms_ = 0;
    bool saw_press_ = false, committed_ = false;
};
} // namespace wsprrypico::network

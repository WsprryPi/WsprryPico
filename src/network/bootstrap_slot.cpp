#include "network/bootstrap_slot.hpp"

#include <utility>

namespace wsprrypico::network {
namespace {
bool elapsed(std::uint64_t now, std::uint64_t start, std::uint64_t duration) {
    return now < start || now - start >= duration;
}
void clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
} // namespace

bool BootstrapSlot::start(BootstrapSlotBinding binding, std::uint64_t now_ms, bool sample_safe,
                          bool button_pressed) {
    expire(now_ms);
    if (state_ != BootstrapSlotState::None || !sample_safe || button_pressed ||
        binding.device_id.empty() || binding.boot_id.empty() || binding.slot_id.empty() ||
        binding.browser_public_key.empty() || binding.request_nonce.empty())
        return false;
    binding_ = std::move(binding);
    started_ms_ = now_ms;
    state_ = BootstrapSlotState::Identify;
    return true;
}

bool BootstrapSlot::grant_open_setup(std::uint64_t now_ms) {
    expire(now_ms);
    if (state_ != BootstrapSlotState::Identify || now_ms < started_ms_)
        return false;
    state_ = BootstrapSlotState::Granted;
    return true;
}

void BootstrapSlot::sample(std::uint64_t now_ms, bool sample_safe, bool button_pressed) {
    expire(now_ms);
    if (state_ != BootstrapSlotState::Identify)
        return;
    if (!sample_safe) {
        cancel();
        return;
    }
    if (button_pressed) {
        if (!saw_press_) {
            saw_press_ = true;
            pressed_ms_ = now_ms;
        } else if (elapsed(now_ms, pressed_ms_, maximum_press_ms))
            cancel();
        return;
    }
    if (!saw_press_)
        return;
    if (now_ms < pressed_ms_ || elapsed(now_ms, pressed_ms_, maximum_press_ms)) {
        cancel();
        return;
    }
    if (elapsed(now_ms, pressed_ms_, minimum_press_ms))
        state_ = BootstrapSlotState::Granted;
    else
        saw_press_ = false; // Ignore one short contact bounce.
}

bool BootstrapSlot::consume(std::string_view device_id, std::string_view boot_id,
                            std::string_view slot_id, std::string_view request_id,
                            std::string_view request_id_digest, std::string_view ciphertext_digest,
                            std::uint64_t now_ms) {
    expire(now_ms);
    if (state_ != BootstrapSlotState::Granted || device_id != binding_.device_id ||
        boot_id != binding_.boot_id || slot_id != binding_.slot_id || request_id.empty() ||
        request_id_digest.empty() || ciphertext_digest.empty())
        return false;
    request_id_ = request_id;
    request_id_digest_ = request_id_digest;
    ciphertext_digest_ = ciphertext_digest;
    state_ = BootstrapSlotState::Trial;
    return true;
}

bool BootstrapSlot::finish(bool committed, std::uint64_t now_ms) {
    expire(now_ms);
    if (state_ != BootstrapSlotState::Trial)
        return false;
    committed_ = committed;
    terminal_ms_ = now_ms;
    clear(binding_.device_id);
    clear(binding_.boot_id);
    clear(binding_.slot_id);
    clear(binding_.browser_public_key);
    clear(binding_.request_nonce);
    clear(request_id_);
    clear(ciphertext_digest_);
    state_ = BootstrapSlotState::Terminal;
    return true;
}

bool BootstrapSlot::acknowledge(bool valid_tag, std::uint64_t now_ms) {
    expire(now_ms);
    if (state_ != BootstrapSlotState::Terminal || !committed_ || !valid_tag)
        return false;
    cancel();
    return true;
}

void BootstrapSlot::expire(std::uint64_t now_ms) {
    if (state_ == BootstrapSlotState::None)
        return;
    if ((state_ != BootstrapSlotState::Terminal && elapsed(now_ms, started_ms_, slot_window_ms)) ||
        (state_ == BootstrapSlotState::Identify && elapsed(now_ms, started_ms_, tap_window_ms)) ||
        (state_ == BootstrapSlotState::Terminal &&
         elapsed(now_ms, terminal_ms_, terminal_window_ms)))
        cancel();
}

void BootstrapSlot::cancel() {
    clear(binding_.device_id);
    clear(binding_.boot_id);
    clear(binding_.slot_id);
    clear(binding_.browser_public_key);
    clear(binding_.request_nonce);
    clear(request_id_);
    clear(request_id_digest_);
    clear(ciphertext_digest_);
    state_ = BootstrapSlotState::None;
    started_ms_ = pressed_ms_ = terminal_ms_ = 0;
    saw_press_ = committed_ = false;
}
} // namespace wsprrypico::network

#include "provisioning/consumer_claim.hpp"

#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"

#include <algorithm>
#include <array>
#include <limits>
#include <utility>
#include <vector>

namespace wsprrypico::provisioning {
namespace {
bool hex32(std::string_view text) {
    return text.size() == 32 && std::all_of(text.begin(), text.end(), [](char c) {
               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
           });
}
bool hex64(std::string_view text) {
    return text.size() == 64 && std::all_of(text.begin(), text.end(), [](char c) {
               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
           });
}
bool elapsed(std::uint64_t now, std::uint64_t then, std::uint64_t duration) {
    return now < then || now - then >= duration;
}
void clear(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
void clear(ConsumerClaimBinding& binding) {
    clear(binding.device_id);
    clear(binding.boot_id);
    clear(binding.slot_id);
    clear(binding.owner_public_key);
    clear(binding.browser_public_key);
    clear(binding.browser_nonce);
    clear(binding.origin);
    binding.source = ProfileSource::LegacyBootstrap;
    binding.generation = 0;
}
bool valid(const ConsumerClaimBinding& binding) {
    if (!network::valid_device_id(binding.device_id) || !hex32(binding.boot_id) ||
        !hex32(binding.slot_id) || !hex32(binding.browser_nonce) ||
        binding.origin != "http://192.168.4.1" ||
        !((binding.source == ProfileSource::LegacyBootstrap && binding.generation == 0) ||
          (binding.source == ProfileSource::Unprovisioned && binding.generation > 0) ||
          (binding.source == ProfileSource::NetworkOnly && binding.generation > 0)) ||
        binding.generation == std::numeric_limits<std::uint64_t>::max())
        return false;
    std::vector<std::uint8_t> point;
    if (!network::bootstrap_unb64url(binding.owner_public_key, point, 65, 65) || point[0] != 4)
        return false;
    return network::bootstrap_unb64url(binding.browser_public_key, point, 32, 32);
}
} // namespace

bool ConsumerClaimSlot::start(ConsumerClaimBinding binding, std::uint64_t now_ms, bool sampler_safe,
                              bool button_pressed, bool idle_output) {
    expire(now_ms);
    if (state_ != ConsumerClaimState::None || !sampler_safe || button_pressed || !idle_output ||
        !valid(binding)) {
        clear(binding);
        return false;
    }
    binding_ = std::move(binding);
    started_ms_ = now_ms;
    state_ = ConsumerClaimState::Identify;
    return true;
}

void ConsumerClaimSlot::sample(std::uint64_t now_ms, bool sampler_safe, bool button_pressed,
                               bool idle_output) {
    expire(now_ms);
    if (state_ != ConsumerClaimState::None && state_ != ConsumerClaimState::Terminal &&
        (!sampler_safe || !idle_output)) {
        cancel();
        return;
    }
    if (state_ != ConsumerClaimState::Identify)
        return;
    if (button_pressed) {
        if (!saw_press_) {
            saw_press_ = true;
            pressed_ms_ = now_ms;
        } else if (now_ms < pressed_ms_ || now_ms - pressed_ms_ > maximum_press_ms)
            cancel();
        return;
    }
    if (!saw_press_)
        return;
    if (now_ms < pressed_ms_ || now_ms - pressed_ms_ > maximum_press_ms) {
        cancel();
        return;
    }
    if (now_ms - pressed_ms_ >= minimum_press_ms) {
        granted_ms_ = now_ms;
        state_ = ConsumerClaimState::Granted;
    } else
        saw_press_ = false; // Ignore contact bounce; require a new press.
}

bool ConsumerClaimSlot::grant_captured(std::uint64_t now_ms, bool sampler_safe, bool valid_press,
                                       std::uint32_t duration_ms, bool idle_output) {
    // The capture itself enforces the prompt deadline. Do not run expire(now)
    // here: a valid release near the end of the window can arrive after its
    // start timestamp plus 60 seconds because of debounce and return time.
    if (state_ != ConsumerClaimState::Identify || !sampler_safe || !valid_press || !idle_output ||
        duration_ms < minimum_press_ms || duration_ms > maximum_press_ms) {
        cancel();
        return false;
    }
    granted_ms_ = now_ms;
    state_ = ConsumerClaimState::Granted;
    return true;
}

bool ConsumerClaimSlot::consume(const ConsumerClaimBinding& current, std::string_view request_id,
                                std::uint64_t now_ms, bool sampler_safe, bool idle_output) {
    expire(now_ms);
    if (state_ != ConsumerClaimState::Granted || !sampler_safe || !idle_output ||
        current != binding_ || !hex32(request_id)) {
        if (!sampler_safe || !idle_output)
            cancel();
        return false;
    }
    request_id_ = request_id;
    trial_ms_ = now_ms;
    state_ = ConsumerClaimState::Trial;
    return true;
}

bool ConsumerClaimSlot::finish(bool committed, std::string_view request_sha256,
                               std::uint64_t generation, std::uint64_t now_ms, bool idle_output) {
    expire(now_ms);
    if (!idle_output) {
        cancel();
        return false;
    }
    std::array<std::uint8_t, 16> request{};
    const bool digest_matches = network::bootstrap_unhex(request_id_, request) &&
                                network::bootstrap_digest(request) == request_sha256;
    if (state_ != ConsumerClaimState::Trial ||
        (committed &&
         (!hex64(request_sha256) || !digest_matches || generation != binding_.generation + 1)) ||
        (!committed && (generation != 0 || !request_sha256.empty())))
        return false;
    clear(binding_);
    clear(request_id_);
    request_sha256_ = request_sha256;
    committed_generation_ = generation;
    committed_ = committed;
    terminal_ms_ = now_ms;
    state_ = ConsumerClaimState::Terminal;
    return true;
}

void ConsumerClaimSlot::expire(std::uint64_t now_ms) {
    switch (state_) {
    case ConsumerClaimState::None:
        break;
    case ConsumerClaimState::Identify:
        if (elapsed(now_ms, started_ms_, physical_window_ms))
            cancel();
        break;
    case ConsumerClaimState::Granted:
        if (elapsed(now_ms, granted_ms_, submit_window_ms))
            cancel();
        break;
    case ConsumerClaimState::Trial:
        if (elapsed(now_ms, trial_ms_, trial_window_ms))
            cancel();
        break;
    case ConsumerClaimState::Terminal:
        if (elapsed(now_ms, terminal_ms_, terminal_window_ms))
            cancel();
        break;
    }
}

void ConsumerClaimSlot::cancel() {
    clear(binding_);
    clear(request_id_);
    clear(request_sha256_);
    state_ = ConsumerClaimState::None;
    started_ms_ = pressed_ms_ = granted_ms_ = trial_ms_ = terminal_ms_ = committed_generation_ = 0;
    saw_press_ = committed_ = false;
}
} // namespace wsprrypico::provisioning

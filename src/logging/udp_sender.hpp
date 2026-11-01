// SPDX-License-Identifier: MIT
#pragma once
#include "logging/udp_event_policy.hpp"
#include "logging/udp_wire.hpp"

#include <limits>

namespace wsprrypico::logging {
using wsprry::logging::Text;
struct UdpSettings {
    bool enabled = false;
    Text<15> destination_ipv4;
    unsigned destination_port = 5514, maximum_severity = 6, rate = 4, burst = 8;
    std::array<Text<32>, 16> event_codes{};
    std::size_t event_count{};
    bool operator==(const UdpSettings& other) const {
        if (enabled != other.enabled || destination_ipv4.view() != other.destination_ipv4.view() ||
            destination_port != other.destination_port ||
            maximum_severity != other.maximum_severity || rate != other.rate ||
            burst != other.burst || event_count != other.event_count)
            return false;
        for (std::size_t i = 0; i < event_count; ++i)
            if (event_codes[i].view() != other.event_codes[i].view())
                return false;
        return true;
    }
};
inline void increment(std::uint64_t& value, std::uint64_t amount = 1) {
    value += std::min(amount, std::numeric_limits<std::uint64_t>::max() - value);
}
// Canonical IPv4 syntax and intrinsically forbidden classes. Adapter additionally
// rejects local addresses, directed broadcasts, routes and interface mismatches.
inline std::optional<std::uint32_t> udp_ipv4(std::string_view text) {
    std::uint32_t value = 0;
    for (unsigned part = 0; part < 4; ++part) {
        const auto at = text.find('.');
        if ((part < 3 && at == std::string_view::npos) ||
            (part == 3 && at != std::string_view::npos))
            return {};
        const auto word = part == 3 ? text : text.substr(0, at);
        std::uint64_t n{};
        if (!wsprry::logging::decimal(word, n) || n > 255)
            return {};
        value = (value << 8) | static_cast<std::uint32_t>(n);
        if (part < 3)
            text.remove_prefix(at + 1);
    }
    if ((value >> 24) == 0 || (value >> 24) == 127 || (value >> 24) >= 224 || value == 0xffffffffU)
        return {};
    return value;
}
inline bool valid_udp_settings(const UdpSettings& s) {
    if (!s.destination_port || s.destination_port > 65535 || s.maximum_severity > 7 || !s.rate ||
        s.rate > 8 || !s.burst || s.burst > 16 || s.event_count > 16 ||
        (s.enabled && s.destination_ipv4.view().empty()) ||
        (!s.destination_ipv4.view().empty() && !udp_ipv4(s.destination_ipv4.view())))
        return false;
    for (std::size_t i = 0; i < s.event_count; ++i) {
        if (!wsprry::logging::token(s.event_codes[i].view(), 32))
            return false;
        for (std::size_t j = 0; j < i; ++j)
            if (s.event_codes[i].view() == s.event_codes[j].view())
                return false;
    }
    return true;
}
struct UdpCounters {
    std::uint64_t generated{}, filtered{}, redacted_rejected{}, queued{}, overflow{}, expired{},
        reconfigured_drops{}, truncated{}, attempted{}, locally_submitted{}, locally_failed{};
};
enum class UdpState {
    Disabled,
    AwaitingNetwork,
    InvalidDestination,
    Ready,
    SubmissionFailed,
    Unavailable
};
// One core-0 owner; caller controls network generation and validates the route.
// send(data) submits locally once. No retry, acknowledgment, heap or RF calls.
class UdpSender {
  public:
    UdpSender(std::string_view device, std::string_view boot, std::string_view name) {
        identity_.origin.assign(device);
        identity_.boot.assign(boot);
        identity_.hostname.assign(name);
    }
    bool configure(const UdpSettings& s) {
        if (!valid_udp_settings(s))
            return false;
        if (!(settings_ == s)) {
            clear();
            settings_ = s;
            credits_ = std::uint64_t(s.burst) * 1'000'000'000ULL;
            last_refill_.reset();
        }
        state_ = s.enabled ? UdpState::AwaitingNetwork : UdpState::Disabled;
        return true;
    }
    void network(std::uint64_t generation, bool up, bool destination_valid) {
        const bool changed = !generation_ || *generation_ != generation;
        if (changed) {
            clear();
            generation_ = generation;
        }
        if (!changed && up && destination_valid && settings_.enabled &&
            state_ == UdpState::SubmissionFailed)
            return;
        state_ = !settings_.enabled   ? UdpState::Disabled
                 : !up                ? UdpState::AwaitingNetwork
                 : !destination_valid ? UdpState::InvalidDestination
                                      : UdpState::Ready;
    }
    void event(std::uint64_t sequence, unsigned severity, std::string_view code,
               std::string_view message, std::uint64_t monotonic, std::uint64_t utc,
               std::uint64_t dropped) {
        increment(counters_.generated);
        bool selected = settings_.event_count == 0;
        for (std::size_t i = 0; i < settings_.event_count; ++i)
            selected |= code == settings_.event_codes[i].view();
        if (!settings_.enabled || severity > settings_.maximum_severity || !selected) {
            increment(counters_.filtered);
            return;
        }
        if (!sequence || severity > 7 || !wsprry::logging::token(code, 32) ||
            !wsprry::logging::export_safe_pico(code, message)) {
            increment(counters_.redacted_rejected);
            return;
        }
        if (size_ == queue_.size()) {
            increment(counters_.overflow);
            return;
        }
        auto& r = queue_[(head_ + size_) % queue_.size()];
        r = {};
        r.sequence = sequence;
        r.severity = severity;
        r.monotonic = monotonic;
        r.utc = utc;
        r.dropped = dropped;
        r.template_index = wsprry::logging::pico_export_template(code, message);
        ++size_;
        increment(counters_.queued);
    }
    template <typename Send> void poll(std::uint64_t now, Send send) {
        // Expire at most the fixed queue capacity, even while network is down.
        while (size_ && (now < queue_[head_].monotonic ||
                         now - queue_[head_].monotonic >= 5'000'000'000ULL)) {
            pop();
            increment(counters_.expired);
        }
        const auto maximum = std::uint64_t(settings_.burst) * 1'000'000'000ULL;
        if (!last_refill_ || now < *last_refill_) {
            last_refill_ = now;
            credits_ = maximum;
        }
        const auto elapsed = now - *last_refill_;
        if (elapsed > maximum / settings_.rate)
            credits_ = maximum;
        else
            credits_ = std::min<std::uint64_t>(maximum, credits_ + elapsed * settings_.rate);
        last_refill_ = now;
        const auto window = now / 1'000'000'000ULL;
        if (!send_window_ || *send_window_ != window) {
            send_window_ = window;
            window_attempts_ = 0;
        }
        if (!size_ || credits_ < 1'000'000'000ULL || window_attempts_ >= 8 ||
            (state_ != UdpState::Ready && state_ != UdpState::SubmissionFailed))
            return;
        const auto& r = queue_[head_];
        identity_.sequence = r.sequence;
        identity_.severity = r.severity;
        const auto& approved = wsprry::logging::pico_export_templates[r.template_index];
        identity_.code.assign(approved.code);
        identity_.message.assign(approved.message);
        identity_.monotonic_ns = r.monotonic;
        identity_.dropped = r.dropped;
        identity_.utc_ns = r.utc ? std::optional<std::uint64_t>{r.utc} : std::nullopt;
        bool shortened{};
        const auto data = wsprry::logging::encode_udp(identity_, formatted_, shortened);
        credits_ -= 1'000'000'000ULL;
        ++window_attempts_;
        increment(counters_.attempted);
        if (shortened)
            increment(counters_.truncated);
        if (!data.empty() && send(data)) {
            increment(counters_.locally_submitted);
            state_ = UdpState::Ready;
        } else {
            increment(counters_.locally_failed);
            state_ = UdpState::SubmissionFailed;
        }
        pop();
    }
    void resource_unavailable() {
        if (settings_.enabled)
            state_ = UdpState::Unavailable;
    }
    const UdpSettings& settings() const {
        return settings_;
    }
    const UdpCounters& counters() const {
        return counters_;
    }
    UdpState state() const {
        return state_;
    }
    std::size_t queued() const {
        return size_;
    }

  private:
    struct Record {
        std::uint64_t sequence{}, monotonic{}, utc{}, dropped{};
        unsigned severity{};
        unsigned template_index{};
    };
    void pop() {
        head_ = (head_ + 1) % queue_.size();
        --size_;
    }
    void clear() {
        increment(counters_.reconfigured_drops, size_);
        size_ = head_ = 0;
    }
    std::array<Record, 16> queue_{};
    UdpSettings settings_;
    UdpCounters counters_;
    wsprry::logging::UdpEvent identity_;
    std::array<char, 480> formatted_{};
    std::size_t head_{}, size_{};
    std::optional<std::uint64_t> generation_, last_refill_, send_window_;
    std::uint64_t credits_ = 8'000'000'000ULL;
    unsigned window_attempts_ = 0;
    UdpState state_ = UdpState::Disabled;
};
static_assert(sizeof(UdpSender) <= 8 * 1024, "UDP sink static memory budget");
} // namespace wsprrypico::logging

// SPDX-License-Identifier: MIT
#include "logging/logger.hpp"

#include "logging/udp_sender.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <charconv>
#include <cstdio>
#include <limits>
#include <span>

namespace wsprrypico::logging {
namespace {
std::string clean(std::string_view text, std::size_t limit, bool token = false) {
    std::string result;
    for (unsigned char byte : text.substr(0, limit))
        result +=
            byte >= (token ? 33 : 32) && byte <= 126 && (!token || (byte != '"' && byte != '\\'))
                ? static_cast<char>(byte)
                : '_';
    return result.empty() ? "-" : result;
}
// UTC conversion uses fixed integer arithmetic and no C timezone machinery.
// Civil-date arithmetic adapts Howard Hinnant's public-domain civil_from_days:
// https://howardhinnant.github.io/date_algorithms.html#civil_from_days
std::array<char, 32> timestamp(std::uint64_t utc) {
    std::array<char, 32> text{};
    if (!utc) {
        text[0] = '-';
        return text;
    }
    const auto seconds = utc / 1'000'000'000ULL;
    const auto days = seconds / 86400;
    const auto z = static_cast<std::int64_t>(days) + 719468;
    const auto era = z / 146097, doe = z - era * 146097;
    const auto yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    auto year = yoe + era * 400;
    const auto doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    const auto mp = (5 * doy + 2) / 153;
    const auto day = doy - (153 * mp + 2) / 5 + 1;
    const auto month = mp + (mp < 10 ? 3 : -9);
    year += month <= 2;
    std::snprintf(text.data(), text.size(), "%04u-%02u-%02uT%02u:%02u:%02uZ",
                  static_cast<unsigned>(year), static_cast<unsigned>(month),
                  static_cast<unsigned>(day), static_cast<unsigned>(seconds / 3600 % 24),
                  static_cast<unsigned>(seconds / 60 % 60), static_cast<unsigned>(seconds % 60));
    return text;
}
template <std::size_t N>
void copy_clean(std::array<char, N>& output, std::string_view input, bool token) {
    std::size_t size = 0;
    for (unsigned char c : input.substr(0, N - 1))
        output[size++] = c >= (token ? 33 : 32) && c <= 126 && (!token || (c != '"' && c != '\\'))
                             ? static_cast<char>(c)
                             : '_';
    if (!size)
        output[size++] = '-';
    output[size] = 0;
}
class Format {
  public:
    explicit Format(std::span<char> output) : output_(output) {}
    void append(std::string_view text) {
        if (text.size() > output_.size() - size_) {
            failed_ = true;
            return;
        }
        std::copy(text.begin(), text.end(), output_.begin() + size_);
        size_ += text.size();
    }
    void number(std::uint64_t value) {
        std::array<char, 24> text{};
        const auto result = std::to_chars(text.data(), text.data() + text.size(), value);
        append({text.data(), static_cast<std::size_t>(result.ptr - text.data())});
    }
    void quoted(std::string_view text) {
        append("\"");
        for (char c : text) {
            if (c == '"' || c == '\\')
                append("\\");
            append({&c, 1});
        }
        append("\"");
    }
    std::string_view result() const {
        return failed_ ? std::string_view{} : std::string_view(output_.data(), size_);
    }

  private:
    std::span<char> output_;
    std::size_t size_ = 0;
    bool failed_ = false;
};
} // namespace
Logger::Logger(std::string device, std::string boot, std::string hostname)
    : device_(std::move(device)), boot_(std::move(boot)), hostname_(clean(hostname, 63, true)) {}
void Logger::connected(bool value) {
    if (!value || value != connected_)
        stop();
    connected_ = value;
}
bool Logger::start(std::string_view device, std::string_view boot) {
    if (!connected_ || device != device_ || boot != boot_)
        return false;
    streaming_ = true;
    return true;
}
void Logger::stop() {
    streaming_ = false;
    increment(dropped_, size_);
    head_ = size_ = 0;
}
void Logger::event(unsigned severity, std::string_view code, std::string_view message,
                   std::uint64_t monotonic, std::uint64_t utc) {
    // Never wrap event identity in a boot. Exhaustion disables admission.
    if (severity > 7 || sequence_ == std::numeric_limits<std::uint64_t>::max())
        return;
    const auto sequence = ++sequence_;
    if (udp_)
        udp_->event(sequence, severity, code, message, monotonic, utc, dropped_);
    if (!settings_.enabled || severity > settings_.maximum_severity)
        return;
    const auto window = monotonic / 1'000'000'000ULL;
    if (window != window_) {
        window_ = window;
        burst_ = 0;
    }
    // Maximum eight events/second, including faults; no blocking or recursion.
    if (burst_ >= 8 || size_ == capacity) {
        increment(dropped_);
        return;
    }
    ++burst_;
    auto& record = queue_[(head_ + size_) % capacity];
    record = {};
    record.sequence = sequence;
    record.monotonic = monotonic;
    record.utc = utc;
    // The origin count belongs to this event, not to a later sink delivery.
    record.dropped = dropped_;
    record.severity = severity;
    copy_clean(record.code, code, true);
    copy_clean(record.message, message, false);
    ++size_;
}
std::string_view Logger::front() const {
    if (!connected_ || !streaming_ || !size_ || !settings_.enabled)
        return {};
    const auto& r = queue_[head_];
    // Reserve room before the record for the project serial length prefix.
    Format record{std::span<char>(formatted_).subspan(24, formatted_.size() - 25)};
    record.append("<");
    record.number(23 * 8 + r.severity);
    record.append(">1 ");
    const auto time = timestamp(r.utc);
    record.append(time.data());
    record.append(" ");
    record.append(hostname_);
    record.append(" WsprryPico - ");
    record.append(r.code.data());
    record.append(" - {\"schema\":\"wsprry-log/1\",\"origin_kind\":\"pico\",\"origin_id\":");
    record.quoted(device_);
    record.append(",\"origin_name\":");
    record.quoted(hostname_);
    record.append(",\"boot_id\":");
    record.quoted(boot_);
    record.append(",\"sequence\":\"");
    record.number(r.sequence);
    record.append("\",\"event\":");
    record.quoted(r.code.data());
    record.append(",\"severity\":");
    record.number(r.severity);
    record.append(",\"facility\":23,\"utc_ns\":");
    if (r.utc) {
        record.append("\"");
        record.number(r.utc);
        record.append("\"");
    } else
        record.append("null");
    record.append(",\"monotonic_ns\":\"");
    record.number(r.monotonic);
    record.append("\",\"dropped\":\"");
    record.number(r.dropped);
    record.append("\",\"message\":");
    record.quoted(r.message.data());
    record.append("}");
    const auto bytes = record.result();
    if (bytes.empty())
        return {};
    std::array<char, 24> header{};
    const auto count = std::snprintf(header.data(), header.size(), "@SYSLOG %u ",
                                     static_cast<unsigned>(bytes.size()));
    const auto start = 24 - static_cast<std::size_t>(count);
    std::copy_n(header.data(), count, formatted_.begin() + start);
    formatted_[24 + bytes.size()] = '\n';
    return {formatted_.data() + start, static_cast<std::size_t>(count) + bytes.size() + 1};
}
void Logger::consume() {
    if (size_) {
        head_ = (head_ + 1) % capacity;
        --size_;
    }
}
std::string Logger::status() const {
    return "{\"enabled\":" + std::string(settings_.enabled ? "true" : "false") +
           ",\"maximum_severity\":" + std::to_string(settings_.maximum_severity) +
           ",\"streaming\":" + (streaming_ ? "true" : "false") +
           ",\"connected\":" + (connected_ ? "true" : "false") +
           ",\"queued\":" + std::to_string(size_) +
           ",\"dropped\":" + wtp::json::quote(std::to_string(dropped_)) + "}";
}
} // namespace wsprrypico::logging

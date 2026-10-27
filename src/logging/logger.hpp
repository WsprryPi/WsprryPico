// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <string_view>

namespace wsprrypico::logging {
struct Settings {
    bool enabled = false;
    unsigned maximum_severity = 6;
    bool operator==(const Settings&) const = default;
};
// Core-0 owner only. Events contain fixed, caller-selected text, never requests,
// configuration, credentials or authentication material. No IRQ/RF-core calls.
class Logger {
  public:
    static constexpr std::size_t capacity = 16, message_bytes = 192;
    Logger(std::string device, std::string boot, std::string hostname);
    void settings(Settings value) {
        settings_ = value;
    }
    Settings settings() const {
        return settings_;
    }
    void connected(bool value);
    bool start(std::string_view device, std::string_view boot);
    void stop();
    bool streaming() const {
        return streaming_;
    }
    void event(unsigned severity, std::string_view code, std::string_view message,
               std::uint64_t monotonic_ns, std::uint64_t utc_ns = 0);
    // One complete serialized record. Retain it until an all-or-nothing Console
    // enqueue succeeds; the USB adapter owns physical short-write recovery.
    std::string_view front() const;
    void consume();
    std::uint64_t dropped() const {
        return dropped_;
    }
    std::size_t queued() const {
        return size_;
    }
    std::string status() const;

  private:
    struct Record {
        std::uint64_t sequence{}, monotonic{}, utc{};
        unsigned severity{};
        std::array<char, 33> code{};
        std::array<char, message_bytes + 1> message{};
    };
    std::string device_, boot_, hostname_;
    Settings settings_;
    std::array<Record, capacity> queue_{};
    std::size_t head_ = 0, size_ = 0;
    std::uint64_t sequence_ = 0, dropped_ = 0, window_ = 0;
    unsigned burst_ = 0;
    bool connected_ = false, streaming_ = false;
    mutable std::array<char, 1400> formatted_{};
};
static_assert(sizeof(Logger) <= 7 * 1024, "USB logger static memory budget");
} // namespace wsprrypico::logging

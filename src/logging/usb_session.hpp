// SPDX-License-Identifier: MIT
#pragma once

#include "logging/logger.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <array>
#include <span>

namespace wsprrypico::logging {
// A distinct, closed USB-Logging/1 carrier. Only STATUS/START/STOP are allowed;
// firmware settings continue through the independently versioned management API.
// Single core-0 owner, bounded RX and one atomic output admission per poll.
class UsbSession {
  public:
    UsbSession(Logger& logger, std::string device, std::string boot)
        : logger_(logger), device_(std::move(device)), boot_(std::move(boot)) {}

    template <typename Read, typename Write>
    void poll(bool connected, bool reset, Read&& read, Write&& write, std::uint64_t now) {
        if (reset || !connected) {
            logger_.connected(false);
            length_ = input_size_ = input_offset_ = 0;
            overflow_ = false;
            reply_.clear();
            line_.fill(0);
        }
        logger_.connected(connected);
        if (!connected)
            return;
        if (reply_.empty() && input_offset_ == input_size_) {
            input_size_ = read(input_);
            input_offset_ = 0;
        }
        while (reply_.empty() && input_offset_ < input_size_) {
            const auto byte = input_[input_offset_++];
            if (byte == '\n') {
                command(now);
                line_.fill(0);
                length_ = 0;
                overflow_ = false;
            } else {
                if (byte < 32 || byte > 126 || length_ == line_.size())
                    overflow_ = true;
                else if (!overflow_)
                    line_[length_++] = static_cast<char>(byte);
            }
        }
        if (!reply_.empty()) {
            if (write(reply_))
                reply_.clear();
        } else {
            const auto record = logger_.front();
            if (!record.empty() && write(record))
                logger_.consume();
        }
    }

  private:
    std::string prefix() const {
        return "{\"schema\":\"usb-logging/1\",\"target\":{\"device_id\":" +
               wtp::json::quote(device_) + ",\"boot_id\":" + wtp::json::quote(boot_) + "}";
    }
    void command(std::uint64_t now) {
        const std::string_view text(line_.data(), length_);
        if (!overflow_ && text == "SYSLOG STATUS") {
            reply_ = prefix() + ",\"active\":" + logger_.status() + "}\n";
        } else if (!overflow_ && text == "SYSLOG STOP") {
            logger_.stop();
            reply_ = prefix() + ",\"streaming\":false}\n";
        } else if (!overflow_ && text == "SYSLOG START " + device_ + " " + boot_ &&
                   logger_.start(device_, boot_)) {
            logger_.event(5, "USB_LOG", "Logging session started", now);
            reply_ = prefix() + ",\"streaming\":true}\n";
        } else {
            reply_ = "{\"schema\":\"usb-logging/1\",\"error\":\"logging_command_refused\"}\n";
        }
    }
    Logger& logger_;
    std::string device_, boot_, reply_;
    std::array<char, 128> line_{};
    std::array<std::uint8_t, 64> input_{};
    std::size_t length_ = 0, input_size_ = 0, input_offset_ = 0;
    bool overflow_ = false;
};
static_assert(sizeof(UsbSession) <= 512, "Logging session static memory budget");
} // namespace wsprrypico::logging

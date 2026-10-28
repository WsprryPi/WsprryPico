// SPDX-License-Identifier: MIT
#pragma once
#include "logging/udp_sender.hpp"
#include "standalone/storage.hpp"
#include "wtp/json.hpp"
namespace wsprrypico::logging {
std::optional<UdpSettings> parse_udp_settings(wtp::json::Value value);
std::string udp_settings_json(const UdpSettings& value);
std::string udp_active_json(const UdpSender& sender, std::string_view revision);
class UdpStore {
  public:
    explicit UdpStore(standalone::Flash& flash) : flash_(flash), journal_(flash, 0, 2048) {}
    bool load();
    bool save(const UdpSettings& value);
    bool clear();
    bool healthy() const {
        return healthy_ && journal_.healthy();
    }
    const UdpSettings& settings() const {
        return settings_;
    }
    std::uint64_t sequence() const {
        return journal_.sequence();
    }

  private:
    standalone::Flash& flash_;
    standalone::Journal journal_;
    UdpSettings settings_;
    bool healthy_ = false;
};
} // namespace wsprrypico::logging

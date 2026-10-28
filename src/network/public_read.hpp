// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <string_view>
namespace wsprrypico::network {
inline constexpr std::array<std::string_view, 33> public_read_resources = {
    "capabilities",
    "pins",
    "pins/2",
    "operations",
    "status",
    "config",
    "config/2",
    "config/3",
    "config/4",
    "application",
    "application/2",
    "application/3",
    "application/4",
    "station",
    "station/2",
    "hardware",
    "hardware/2",
    "hardware/3",
    "progress",
    "progress/2",
    "progress/3",
    "rf-calibration",
    "standalone-frequency",
    "gpio-drive",
    "ntp-timeout",
    "hostname",
    "logging",
    "udp-logging",
    "udp-logging/capabilities",
    "udp-logging/test/capabilities",
    "message-schedule",
    "consumer/password",
    "consumer/setup/api/owner/v1/public-status",
};
inline constexpr std::array<std::string_view, 1> public_read_resources_v2 = {"amplifier-timing"};
} // namespace wsprrypico::network

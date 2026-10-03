#pragma once
#include "standalone/config.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::application {
inline constexpr std::size_t max_update_bytes = 1024;
inline constexpr std::string_view application_schema = "transmitter-application/1";
inline constexpr std::string_view station_schema = "transmitter-station/1";
inline constexpr std::string_view hardware_schema = "transmitter-hardware/1";

enum class Envelope { Valid, Invalid, UnsupportedSchema, TargetMismatch };
Envelope validate_envelope(wtp::json::Value root, std::string_view schema, std::string_view payload,
                           std::string_view device, std::string_view boot);
std::string target(std::string_view device, std::string_view boot);
std::string station(const standalone::Config& config);
std::string capabilities();
} // namespace wsprrypico::application

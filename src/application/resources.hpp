#pragma once
#include "standalone/config.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::application {
inline constexpr std::size_t max_update_bytes = 1024;
inline constexpr std::size_t max_capabilities_bytes = 8192;
inline constexpr std::string_view application_schema = "application";
inline constexpr std::string_view station_schema = "station";
inline constexpr std::string_view hardware_schema = "hardware";

enum class Envelope { Valid, Invalid, UnsupportedSchema, TargetMismatch };
Envelope validate_envelope(wtp::json::Value root, std::string_view schema, std::string_view payload,
                           std::string_view device, std::string_view boot);
std::string target(std::string_view device, std::string_view boot);
std::string gpio_drive_capabilities();
std::string amplifier_capabilities(bool physical);
std::string amplifier_timing_capabilities();
std::string amplifier_observation(const rf::AmplifierObservation& observation);
std::string station(const standalone::Config& config);
std::string capabilities();
std::string wspr_plan(const standalone::Config& config);
} // namespace wsprrypico::application

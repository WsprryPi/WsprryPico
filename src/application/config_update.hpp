#pragma once
#include "application/resources.hpp"

namespace wsprrypico::application {
inline constexpr std::size_t max_config_update_bytes = 2048;
inline constexpr std::string_view config_update_schema = "transmitter-config-update/1";
enum class ConfigWrite { Legacy, Merge, Replace };

Envelope validate_config_update(wtp::json::Value root, std::string_view device,
                                std::string_view boot);
// Construct only supported fields; the caller must validate the complete result
// and use the existing scheduler/journal authority before reporting success.
std::optional<std::string> config_candidate(wtp::json::Value supplied,
                                            const std::optional<standalone::Config>& current,
                                            ConfigWrite mode);
std::string config_update_capabilities();
} // namespace wsprrypico::application

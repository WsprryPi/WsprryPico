#pragma once
#include "wtp/job_service.hpp"
#include "wtp/json.hpp"

namespace wsprrypico::wtp {
// Invalid envelope has no safely echoable identity and closes without a response.
std::optional<Request> decode_request(json::Value root, std::string_view principal,
                                      std::span<const std::uint8_t> payload);
std::string encode_response(const Request& request, const Response& response,
                            const ServiceConfig& config, std::string_view device_id,
                            std::string_view firmware_version);
std::string error_json(ErrorCode code);
std::string status_json(const ServiceStatus& status);
std::string state_name(State state);
} // namespace wsprrypico::wtp

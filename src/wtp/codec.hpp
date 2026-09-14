#pragma once
#include "wtp/job_service.hpp"
#include "wtp/json.hpp"
#include "wtp/output_buffer.hpp"

namespace wsprrypico::wtp {
// Invalid envelope has no safely echoable identity and closes without a response.
std::optional<Request> decode_request(json::Value root, std::string_view principal,
                                      InputView payload);
std::string encode_response(const Request& request, const Response& response,
                            const ServiceConfig& config, std::string_view device_id,
                            std::string_view firmware_version);
// A maximum LOAD reply uses the nullable wire-buffer allocator. Empty means
// insufficient working space; the endpoint must close and permit reconciliation.
OutputBuffer encode_load_response_buffer(const Request& request, const Response& response,
                                         bool browser = false);
std::string error_json(ErrorCode code);
std::string status_json(const ServiceStatus& status);
std::string state_name(State state);
} // namespace wsprrypico::wtp

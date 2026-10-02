#pragma once

#include "network/http.hpp"

#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::network {
struct BootstrapStartRequest {
    std::string device_id, browser_public_key, request_nonce;
};
struct BootstrapSubmitRequest {
    std::string device_id, boot_id, slot_id, request_id;
    std::string aead_nonce, ciphertext, tag;
};
struct BootstrapAckRequest {
    std::string device_id, boot_id, slot_id, request_id, ack_tag;
};
struct BootstrapTimeRequest {
    std::string device_id;
    std::uint64_t utc_ms = 0;
    std::uint64_t challenge_ns = 0;
};

bool bootstrap_mutation_admitted(const HttpRequest& request, std::string_view route);
std::optional<BootstrapStartRequest> parse_bootstrap_start(const HttpRequest& request);
std::optional<BootstrapSubmitRequest> parse_bootstrap_submit(const HttpRequest& request,
                                                             std::size_t minimum_ciphertext = 11,
                                                             std::size_t maximum_ciphertext = 351);
std::optional<BootstrapStartRequest> parse_recovery_start(const HttpRequest& request);
std::optional<BootstrapSubmitRequest> parse_recovery_submit(const HttpRequest& request);
std::optional<BootstrapAckRequest> parse_bootstrap_ack(const HttpRequest& request);
std::optional<BootstrapTimeRequest> parse_bootstrap_time(const HttpRequest& request);
} // namespace wsprrypico::network

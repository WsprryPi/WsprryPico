#include "network/bootstrap_wire.hpp"

#include "wtp/json.hpp"

#include <algorithm>

namespace wsprrypico::network {
namespace {
int base64url_digit(char c) {
    if (c >= 'A' && c <= 'Z')
        return c - 'A';
    if (c >= 'a' && c <= 'z')
        return c - 'a' + 26;
    if (c >= '0' && c <= '9')
        return c - '0' + 52;
    if (c == '-')
        return 62;
    if (c == '_')
        return 63;
    return -1;
}
bool canonical_base64url(std::string_view value, std::size_t minimum, std::size_t maximum) {
    if (value.empty() || value.size() % 4 == 1 ||
        !std::all_of(value.begin(), value.end(), [](char c) { return base64url_digit(c) >= 0; }))
        return false;
    const auto size = value.size() * 3 / 4;
    if (size < minimum || size > maximum)
        return false;
    const auto trailing = value.size() % 4 == 2 ? 4 : value.size() % 4 == 3 ? 2 : 0;
    return !trailing || !(base64url_digit(value.back()) & ((1 << trailing) - 1));
}
bool lowercase_hex(std::string_view value, std::size_t size) {
    return value.size() == size * 2 && std::all_of(value.begin(), value.end(), [](char c) {
               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
           });
}
std::optional<std::string> field(wtp::json::Value root, std::string_view name) {
    const auto value = root.get(name);
    if (!value || value->type() != '"')
        return {};
    return value->string();
}
bool version_one(wtp::json::Value root) {
    const auto version = root.get("version");
    return version && version->raw == "1";
}
} // namespace

bool bootstrap_mutation_admitted(const HttpRequest& request, std::string_view route) {
    return request.method == "POST" && request.path == route &&
           request.header("host") == "192.168.4.1" &&
           request.header("origin") == "http://192.168.4.1" &&
           request.header("content-type") == "application/json" &&
           request.header("x-wsprrypico-bootstrap") == "1" &&
           !request.headers.contains("transfer-encoding") &&
           request.body_view().size() <= (route == "/api/bootstrap/v1/submit" ? 768 : 512);
}

std::optional<BootstrapStartRequest> parse_bootstrap_start(const HttpRequest& request) {
    if (!bootstrap_mutation_admitted(request, "/api/bootstrap/v1/start"))
        return {};
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !version_one(*root) ||
        !wtp::json::fields(*root, {"version", "device_id", "browser_public_key", "request_nonce"}))
        return {};
    const auto device = field(*root, "device_id"), key = field(*root, "browser_public_key"),
               nonce = field(*root, "request_nonce");
    if (!device || !key || !nonce || !lowercase_hex(*device, 16) ||
        !canonical_base64url(*key, 32, 32) || !lowercase_hex(*nonce, 16))
        return {};
    return BootstrapStartRequest{*device, *key, *nonce};
}

std::optional<BootstrapSubmitRequest> parse_bootstrap_submit(const HttpRequest& request,
                                                             std::size_t minimum_ciphertext,
                                                             std::size_t maximum_ciphertext) {
    if (!bootstrap_mutation_admitted(request, "/api/bootstrap/v1/submit"))
        return {};
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !version_one(*root) ||
        !wtp::json::fields(*root, {"version", "device_id", "boot_id", "slot_id", "request_id",
                                   "aead_nonce", "ciphertext", "tag"}))
        return {};
    const auto device = field(*root, "device_id"), boot = field(*root, "boot_id"),
               slot = field(*root, "slot_id"), request_id = field(*root, "request_id"),
               nonce = field(*root, "aead_nonce"), ciphertext = field(*root, "ciphertext"),
               tag = field(*root, "tag");
    if (!device || !boot || !slot || !request_id || !nonce || !ciphertext || !tag ||
        !lowercase_hex(*device, 16) || !lowercase_hex(*boot, 16) || !lowercase_hex(*slot, 16) ||
        !lowercase_hex(*request_id, 16) || !canonical_base64url(*nonce, 12, 12) ||
        !canonical_base64url(*ciphertext, minimum_ciphertext, maximum_ciphertext) ||
        !canonical_base64url(*tag, 16, 16))
        return {};
    return BootstrapSubmitRequest{*device, *boot, *slot, *request_id, *nonce, *ciphertext, *tag};
}

std::optional<BootstrapStartRequest> parse_recovery_start(const HttpRequest& request) {
    if (!bootstrap_mutation_admitted(request, "/api/recovery/v1/start"))
        return {};
    auto copy = request;
    copy.path = "/api/bootstrap/v1/start";
    return parse_bootstrap_start(copy);
}
std::optional<BootstrapSubmitRequest> parse_recovery_submit(const HttpRequest& request) {
    if (!bootstrap_mutation_admitted(request, "/api/recovery/v1/submit"))
        return {};
    auto copy = request;
    copy.path = "/api/bootstrap/v1/submit";
    return parse_bootstrap_submit(copy, 9, 22);
}

std::optional<BootstrapAckRequest> parse_bootstrap_ack(const HttpRequest& request) {
    if (!bootstrap_mutation_admitted(request, "/api/bootstrap/v1/ack"))
        return {};
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !version_one(*root) ||
        !wtp::json::fields(*root,
                           {"version", "device_id", "boot_id", "slot_id", "request_id", "ack_tag"}))
        return {};
    const auto device = field(*root, "device_id"), boot = field(*root, "boot_id"),
               slot = field(*root, "slot_id"), request_id = field(*root, "request_id"),
               tag = field(*root, "ack_tag");
    if (!device || !boot || !slot || !request_id || !tag || !lowercase_hex(*device, 16) ||
        !lowercase_hex(*boot, 16) || !lowercase_hex(*slot, 16) || !lowercase_hex(*request_id, 16) ||
        !canonical_base64url(*tag, 32, 32))
        return {};
    return BootstrapAckRequest{*device, *boot, *slot, *request_id, *tag};
}

std::optional<BootstrapTimeRequest> parse_bootstrap_time(const HttpRequest& request) {
    if (!bootstrap_mutation_admitted(request, "/api/bootstrap/v1/time"))
        return {};
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !version_one(*root) ||
        !wtp::json::fields(*root, {"version", "device_id", "utc_ms", "challenge_ns"}))
        return {};
    const auto device = field(*root, "device_id");
    const auto utc = root->get("utc_ms");
    const auto challenge = root->get("challenge_ns");
    std::uint64_t utc_ms = 0, challenge_ns = 0;
    if (!device || !utc || !challenge || !lowercase_hex(*device, 16) ||
        !wtp::json::decimal(*utc, utc_ms, true) ||
        !wtp::json::decimal(*challenge, challenge_ns, true) || !challenge_ns)
        return {};
    return BootstrapTimeRequest{*device, utc_ms, challenge_ns};
}
} // namespace wsprrypico::network

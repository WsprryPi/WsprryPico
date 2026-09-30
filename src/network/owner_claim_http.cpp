#include "network/owner_claim_http.hpp"

#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "provisioning/runtime.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <array>
#include <string_view>
#include <vector>

namespace wsprrypico::network {
namespace {
bool hex16(std::string_view value) {
    return value.size() == 32 && std::all_of(value.begin(), value.end(), [](char c) {
               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
           });
}
std::optional<std::string> field(wtp::json::Value value, std::string_view key) {
    const auto child = value.get(key);
    return child && child->type() == '"' ? std::optional(child->string()) : std::nullopt;
}
bool b64(std::string_view value, std::size_t minimum, std::size_t maximum,
         bool owner_point = false) {
    std::vector<std::uint8_t> decoded;
    const bool valid = bootstrap_unb64url(value, decoded, minimum, maximum) &&
                       (!owner_point || decoded.front() == 4);
    std::fill(decoded.begin(), decoded.end(), 0);
    return valid;
}
bool common(const HttpRequest& request, std::string_view route, bool post) {
    if (request.path != route || request.header("host") != "192.168.4.1" ||
        request.method != (post ? "POST" : "GET") || request.headers.contains("authorization") ||
        request.headers.contains("cookie") || request.headers.contains("proxy-authorization") ||
        request.headers.contains("transfer-encoding") || request.headers.contains("upgrade") ||
        request.headers.contains("expect"))
        return false;
    for (const auto& [name, value] : request.headers) {
        (void)value;
        if (name.starts_with("x-wsprrypico-") && name != "x-wsprrypico-owner")
            return false;
    }
    return post ? request.header("origin") == "http://192.168.4.1" &&
                      request.header("content-type") == "application/json" &&
                      request.header("x-wsprrypico-owner") == "1" &&
                      request.body_view().size() <= 1024
                : request.body_view().empty();
}
} // namespace

void OwnerResultRestart::begin(std::uint64_t generation, std::string_view digest,
                               std::uint64_t now_ms) {
    generation_ = generation;
    committed_ms_ = now_ms;
    delivered_ = false;
    pending_ = true;
    digest_valid_ =
        digest.size() == digest_.size() && std::all_of(digest.begin(), digest.end(), [](char c) {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        });
    if (digest_valid_)
        std::copy(digest.begin(), digest.end(), digest_.begin());
}

bool OwnerResultRestart::matches(provisioning::ProfileSource source, std::uint64_t generation,
                                 std::string_view digest) const {
    return pending_ && digest_valid_ && generation_ &&
           source == provisioning::ProfileSource::ConsumerProfile && generation == generation_ &&
           digest.size() == digest_.size() &&
           std::equal(digest.begin(), digest.end(), digest_.begin());
}

void OwnerResultRestart::delivered(bool committed_reply, std::uint64_t now_ms) {
    if (pending_ && committed_reply && !delivered_ && now_ms >= committed_ms_) {
        delivered_ = true;
        delivered_ms_ = now_ms;
    }
}

bool OwnerResultRestart::ready(std::uint64_t now_ms) const {
    if (!pending_ || now_ms < committed_ms_)
        return false;
    // Give the browser time to render the received result before AP withdrawal.
    return delivered_ ? now_ms >= delivered_ms_ && now_ms - delivered_ms_ >= 3'000
                      : now_ms - committed_ms_ >= 60'000;
}

bool owner_public_get_admitted(const HttpRequest& request, std::string_view route) {
    return (route == "/api/owner/v1/public-status" || route == "/api/owner/v1/claim/status") &&
           common(request, route, false);
}

std::string owner_saved_station_json(const provisioning::ProfileStore& store,
                                     const provisioning::RuntimeProfile& runtime,
                                     std::string_view device_id) {
    const auto* saved = runtime.consumer_profile();
    if (!store.healthy() || store.source() != provisioning::ProfileSource::ConsumerProfile ||
        !store.sequence() || runtime.source() != provisioning::RuntimeSource::ConsumerPreClock ||
        runtime.generation() != store.sequence() || !saved || saved->device_id != device_id)
        return "null";
    return "{\"callsign\":" + wtp::json::quote(saved->callsign) +
           ",\"locator\":" + wtp::json::quote(saved->locator) +
           ",\"power_dbm\":" + std::to_string(saved->power_dbm) + "}";
}

std::optional<OwnerIdentifyRequest> parse_owner_identify(const HttpRequest& request) {
    if (!common(request, "/api/owner/v1/identify", true))
        return {};
    const auto root = wtp::json::parse(request.body_view());
    if (!root || !wtp::json::fields(*root, {"version", "device_id", "boot_id", "request_id"}) ||
        root->get("version")->raw != "1")
        return {};
    const auto device = field(*root, "device_id"), boot = field(*root, "boot_id"),
               request_id = field(*root, "request_id");
    if (!device || !network::valid_device_id(*device) || !boot || !hex16(*boot) || !request_id ||
        !hex16(*request_id))
        return {};
    return OwnerIdentifyRequest{*device, *boot, *request_id};
}

std::optional<OwnerClaimStartRequest> parse_owner_claim_start(const HttpRequest& request) {
    if (!common(request, "/api/owner/v1/claim/start", true))
        return {};
    const auto root = wtp::json::parse(request.body_view());
    if (!root ||
        !wtp::json::fields(*root, {"version", "device_id", "owner_public_key", "browser_public_key",
                                   "browser_nonce", "profile_source", "generation"}) ||
        root->get("version")->raw != "1")
        return {};
    const auto device = field(*root, "device_id"), owner = field(*root, "owner_public_key"),
               browser = field(*root, "browser_public_key"), nonce = field(*root, "browser_nonce");
    const auto generation = root->get("generation"), source = root->get("profile_source");
    std::uint64_t sequence = 0;
    if (!device || !network::valid_device_id(*device) || !owner || !b64(*owner, 65, 65, true) ||
        !browser || !b64(*browser, 32, 32) || !nonce || !hex16(*nonce) || !generation ||
        !wtp::json::decimal(*generation, sequence, false) || !source)
        return {};
    provisioning::ProfileSource selected;
    if (source->raw == "0" && sequence == 0)
        selected = provisioning::ProfileSource::LegacyBootstrap;
    else if (source->raw == "2" && sequence > 0)
        selected = provisioning::ProfileSource::Unprovisioned;
    else if (source->raw == "4" && sequence > 0)
        selected = provisioning::ProfileSource::NetworkOnly;
    else if (source->raw == "5" && sequence > 0)
        selected = provisioning::ProfileSource::ConsumerProfile;
    else
        return {};
    return OwnerClaimStartRequest{*device, *owner, *browser, *nonce, selected, sequence};
}

std::optional<OwnerClaimSubmitRequest> parse_owner_claim_submit(const HttpRequest& request) {
    if (!common(request, "/api/owner/v1/claim/submit", true))
        return {};
    const auto root = wtp::json::parse(request.body_view());
    if (!root ||
        !wtp::json::fields(*root, {"version", "device_id", "boot_id", "slot_id", "request_id",
                                   "aead_nonce", "ciphertext", "tag"}) ||
        root->get("version")->raw != "1")
        return {};
    const auto device = field(*root, "device_id"), boot = field(*root, "boot_id"),
               slot = field(*root, "slot_id"), request_id = field(*root, "request_id"),
               nonce = field(*root, "aead_nonce"), cipher = field(*root, "ciphertext"),
               tag = field(*root, "tag");
    if (!device || !boot || !slot || !request_id || !nonce || !cipher || !tag ||
        !network::valid_device_id(*device) || !hex16(*boot) || !hex16(*slot) ||
        !hex16(*request_id) || !b64(*nonce, 12, 12) || !b64(*cipher, 11, 109) || !b64(*tag, 16, 16))
        return {};
    return OwnerClaimSubmitRequest{*device, *boot, *slot, *request_id, *nonce, *cipher, *tag};
}
} // namespace wsprrypico::network

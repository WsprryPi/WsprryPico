#include "network/bootstrap_codec.hpp"
#include "network/http.hpp"
#include "network/owner_claim_http.hpp"
#include "wtp/json.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <span>
#include <string>
#include <string_view>

using namespace wsprrypico;

namespace {
constexpr auto device = "0123456789abcdef0123456789abcdef";
constexpr auto boot = "11111111111111111111111111111111";
constexpr auto slot = "22222222222222222222222222222222";
constexpr auto request_id = "33333333333333333333333333333333";

network::HttpRequest post(std::string_view route, std::string body) {
    network::HttpRequest request;
    request.method = "POST";
    request.path = route;
    request.body = std::move(body);
    request.headers.emplace("host", "192.168.4.1");
    request.headers.emplace("origin", "http://192.168.4.1");
    request.headers.emplace("content-type", "application/json");
    request.headers.emplace("x-wsprrypico-owner", "1");
    return request;
}

std::string wire(const network::HttpRequest& request) {
    std::string value = request.method + " " + request.path + " HTTP/1.1\r\n";
    for (const auto& [key, item] : request.headers)
        value += key + ": " + item + "\r\n";
    return value + "Content-Length: " + std::to_string(request.body.size()) + "\r\n\r\n" +
           request.body;
}

bool parsed(const network::HttpRequest& request) {
    network::HttpParser parser;
    const auto message = wire(request);
    const auto bytes =
        std::span(reinterpret_cast<const std::uint8_t*>(message.data()), message.size());
    (void)parser.receive(bytes);
    return parser.ready() && !parser.failed();
}
} // namespace

int main() {
    std::array<std::uint8_t, 65> owner{};
    owner[0] = 4;
    std::array<std::uint8_t, 32> browser{};
    browser[0] = 1;
    std::array<std::uint8_t, 12> nonce{};
    nonce[0] = 1;
    std::array<std::uint8_t, 20> ciphertext{};
    ciphertext[0] = 1;
    std::array<std::uint8_t, 16> tag{};
    tag[0] = 1;
    const auto owner_key = network::bootstrap_b64url(owner);
    const auto browser_key = network::bootstrap_b64url(browser);
    const auto nonce_key = network::bootstrap_b64url(nonce);
    const auto cipher_key = network::bootstrap_b64url(ciphertext);
    const auto tag_key = network::bootstrap_b64url(tag);
    const auto start_body = std::string("{\"version\":1,\"device_id\":\"") + device +
                            "\",\"owner_public_key\":" + wtp::json::quote(owner_key) +
                            ",\"browser_public_key\":" + wtp::json::quote(browser_key) +
                            ",\"browser_nonce\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"," +
                            "\"profile_source\":4,\"generation\":\"1\"}";
    auto start = post("/api/owner/v1/claim/start", start_body);
    assert(parsed(start));
    const auto admitted = network::parse_owner_claim_start(start);
    assert(admitted && admitted->device_id == device && admitted->generation == 1 &&
           admitted->source == provisioning::ProfileSource::NetworkOnly);
    auto changed = start;
    changed.body.replace(changed.body.find("\"profile_source\":4"), 18, "\"profile_source\":5");
    assert(network::parse_owner_claim_start(changed));

    auto identify = post("/api/owner/v1/identify", std::string("{\"version\":1,\"device_id\":\"") +
                                                       device + "\",\"boot_id\":\"" + boot +
                                                       "\",\"request_id\":\"" + request_id + "\"}");
    const auto identified = network::parse_owner_identify(identify);
    assert(identified && identified->device_id == device && identified->boot_id == boot);
    identify.headers["origin"] = "http://other.local";
    assert(!network::parse_owner_identify(identify));
    identify.headers["origin"] = "http://192.168.4.1";
    identify.body.insert(identify.body.size() - 1, ",\"extra\":1");
    assert(!network::parse_owner_identify(identify));

    changed = start;
    changed.headers["host"] = "captive.apple.com";
    assert(!network::parse_owner_claim_start(changed));
    changed = start;
    changed.headers["origin"] = "http://evil.local";
    assert(!network::parse_owner_claim_start(changed));
    changed = start;
    changed.headers["x-wsprrypico-other"] = "1";
    assert(!network::parse_owner_claim_start(changed));
    changed = start;
    changed.headers["cookie"] = "session=1";
    assert(!network::parse_owner_claim_start(changed));
    changed = start;
    changed.body.replace(changed.body.find("\"profile_source\":4"), 18, "\"profile_source\":0");
    assert(!network::parse_owner_claim_start(changed));
    changed = start;
    changed.body.replace(changed.body.find("\"version\":1"), 11, "\"version\":2");
    assert(!network::parse_owner_claim_start(changed));
    changed = start;
    changed.body.insert(changed.body.size() - 1, ",\"extra\":1");
    assert(!network::parse_owner_claim_start(changed));
    changed = start;
    changed.body.insert(changed.body.size() - 1, ",\"version\":1");
    assert(!network::parse_owner_claim_start(changed));
    network::HttpParser duplicate_header;
    const std::string duplicate_wire =
        "POST /api/owner/v1/claim/start HTTP/1.1\r\nHost: 192.168.4.1\r\n"
        "Host: 192.168.4.1\r\nContent-Length: 0\r\n\r\n";
    (void)duplicate_header.receive(std::span(
        reinterpret_cast<const std::uint8_t*>(duplicate_wire.data()), duplicate_wire.size()));
    assert(duplicate_header.failed());
    changed = start;
    changed.body += std::string(1025, ' ');
    assert(!parsed(changed));
    assert(!network::parse_owner_claim_start(changed));

    const auto submit_body = std::string("{\"version\":1,\"device_id\":\"") + device +
                             "\",\"boot_id\":\"" + boot + "\",\"slot_id\":\"" + slot +
                             "\",\"request_id\":\"" + request_id +
                             "\",\"aead_nonce\":" + wtp::json::quote(nonce_key) +
                             ",\"ciphertext\":" + wtp::json::quote(cipher_key) +
                             ",\"tag\":" + wtp::json::quote(tag_key) + "}";
    auto submit = post("/api/owner/v1/claim/submit", submit_body);
    assert(parsed(submit));
    assert(network::parse_owner_claim_submit(submit));
    changed = submit;
    changed.body.replace(changed.body.find(cipher_key), cipher_key.size(), "AA");
    assert(!network::parse_owner_claim_submit(changed));
    changed = submit;
    changed.body.replace(changed.body.find(tag_key), tag_key.size(), "AA");
    assert(!network::parse_owner_claim_submit(changed));
    changed = submit;
    changed.path += '/';
    assert(!network::parse_owner_claim_submit(changed));
    changed = submit;
    changed.headers["content-type"] = "application/json; charset=utf-8";
    assert(!network::parse_owner_claim_submit(changed));

    network::HttpRequest get;
    get.method = "GET";
    get.path = "/api/owner/v1/public-status";
    get.headers.emplace("host", "192.168.4.1");
    assert(network::owner_public_get_admitted(get, get.path));
    get.path += '/';
    assert(!network::owner_public_get_admitted(get, get.path));

    auto ordinary = post("/api/owner/v1/readback", std::string(4097, 'x'));
    assert(!parsed(ordinary));
    ordinary.body.pop_back();
    assert(parsed(ordinary));
    ordinary.path = "/api/owner/v1/clients/enroll";
    ordinary.body += std::string(2048, 'x');
    assert(parsed(ordinary));
    ordinary.body += 'x';
    assert(!parsed(ordinary));
    return 0;
}

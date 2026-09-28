#include "network/bootstrap_wire.hpp"

#include <cassert>
#include <cstdint>
#include <span>
#include <string>

namespace {
using wsprrypico::network::HttpParser;
using wsprrypico::network::HttpRequest;
using wsprrypico::network::parse_bootstrap_ack;
using wsprrypico::network::parse_bootstrap_start;
using wsprrypico::network::parse_bootstrap_submit;
using wsprrypico::network::parse_bootstrap_time;

constexpr auto device = "00112233445566778899aabbccddeeff";
constexpr auto boot = "102132435465768798a9bacbdcedfe0f";
constexpr auto slot = "2031425364758697a8b9cadbecfd0e1f";
constexpr auto request_id = "405162738495a6b7c8d9eafb0c1d2e3f";

HttpRequest post(std::string path, std::string body) {
    HttpRequest request;
    request.method = "POST";
    request.path = std::move(path);
    request.body = std::move(body);
    request.headers = {{"host", "192.168.4.1"},
                       {"origin", "http://192.168.4.1"},
                       {"content-type", "application/json"},
                       {"x-wsprrypico-bootstrap", "1"}};
    return request;
}

void valid_envelopes_and_admission() {
    auto start = post("/api/bootstrap/v1/start",
                      "{\"version\":1,\"device_id\":\"00112233445566778899aabbccddeeff\","
                      "\"browser_public_key\":\"hSDwCYkwp1R0i33ctD73Wg2_Og0mOBr066SpjqqbTmo\","
                      "\"request_nonce\":\"30415263748596a7b8c9daebfc0d1e2f\"}");
    assert(parse_bootstrap_start(start));
    start.headers["origin"] = "http://evil.example";
    assert(!parse_bootstrap_start(start));
    start.headers["origin"] = "http://192.168.4.1";
    start.headers["content-type"] = "text/plain";
    assert(!parse_bootstrap_start(start));
    start.headers["content-type"] = "application/json";
    start.body.insert(start.body.size() - 1, ",\"ssid\":\"Secret\"");
    assert(!parse_bootstrap_start(start));

    auto submit = post("/api/bootstrap/v1/submit",
                       "{\"version\":1,\"device_id\":\"00112233445566778899aabbccddeeff\","
                       "\"boot_id\":\"102132435465768798a9bacbdcedfe0f\","
                       "\"slot_id\":\"2031425364758697a8b9cadbecfd0e1f\","
                       "\"request_id\":\"405162738495a6b7c8d9eafb0c1d2e3f\","
                       "\"aead_nonce\":\"AAECAwQFBgcICQoL\","
                       "\"ciphertext\":\"FJTGUpCIDXYs7-VUUQFFmyqG1ZUYQ9izbcY\","
                       "\"tag\":\"eckho4uf45mkproym74R4w\"}");
    const auto parsed = parse_bootstrap_submit(submit);
    assert(parsed && parsed->device_id == device && parsed->boot_id == boot &&
           parsed->slot_id == slot && parsed->request_id == request_id);
    auto noncanonical = submit;
    noncanonical.body.replace(noncanonical.body.size() - 3, 1, "x");
    assert(!parse_bootstrap_submit(noncanonical));
    auto duplicate = submit;
    duplicate.body.insert(duplicate.body.size() - 1, ",\"version\":1");
    assert(!parse_bootstrap_submit(duplicate));

    auto ack = post("/api/bootstrap/v1/ack",
                    "{\"version\":1,\"device_id\":\"00112233445566778899aabbccddeeff\","
                    "\"boot_id\":\"102132435465768798a9bacbdcedfe0f\","
                    "\"slot_id\":\"2031425364758697a8b9cadbecfd0e1f\","
                    "\"request_id\":\"405162738495a6b7c8d9eafb0c1d2e3f\","
                    "\"ack_tag\":\"_K8U3rQ2TFQKR5GuNIUe1_wX-r_bt6dDeO6oSjqYsGk\"}");
    assert(parse_bootstrap_ack(ack));
    ack.headers["host"] = "evil.example";
    assert(!parse_bootstrap_ack(ack));

    auto time = post("/api/bootstrap/v1/time",
                     "{\"version\":1,\"device_id\":\"00112233445566778899aabbccddeeff\","
                     "\"utc_ms\":\"1800000000000\",\"challenge_ns\":\"1234567890\"}");
    const auto hint = parse_bootstrap_time(time);
    assert(hint && hint->device_id == device && hint->utc_ms == 1'800'000'000'000ULL &&
           hint->challenge_ns == 1'234'567'890ULL);
    time.headers["origin"] = "http://other.example";
    assert(!parse_bootstrap_time(time));
    time.headers["origin"] = "http://192.168.4.1";
    time.body.insert(time.body.size() - 1, ",\"extra\":1");
    assert(!parse_bootstrap_time(time));
    time.body = "{\"version\":1,\"device_id\":\"00112233445566778899aabbccddeeff\","
                "\"utc_ms\":1800000000000,\"challenge_ns\":\"1234567890\"}";
    assert(!parse_bootstrap_time(time));
}

void parser_rejects_oversize_before_body_allocation() {
    HttpParser parser;
    const std::string request = "POST /api/bootstrap/v1/submit HTTP/1.1\r\nHost: 192.168.4.1\r\n"
                                "Content-Length: 769\r\n\r\n";
    const auto bytes =
        std::span(reinterpret_cast<const std::uint8_t*>(request.data()), request.size());
    (void)parser.receive(bytes);
    assert(parser.failed());
    assert(!parser.request().buffered_body);

    const std::string maximal_body =
        "{\"version\":1,\"device_id\":\"00112233445566778899aabbccddeeff\","
        "\"boot_id\":\"102132435465768798a9bacbdcedfe0f\","
        "\"slot_id\":\"2031425364758697a8b9cadbecfd0e1f\","
        "\"request_id\":\"405162738495a6b7c8d9eafb0c1d2e3f\","
        "\"aead_nonce\":\"AAECAwQFBgcICQoL\",\"ciphertext\":\"" +
        std::string(468, 'A') + "\",\"tag\":\"eckho4uf45mkproym74R4w\"}";
    assert(maximal_body.size() <= 768 && maximal_body.size() > 512);
    const std::string headers = "POST /api/bootstrap/v1/submit HTTP/1.1\r\nHost: 192.168.4.1\r\n"
                                "Origin: http://192.168.4.1\r\nContent-Type: application/json\r\n"
                                "X-WsprryPico-Bootstrap: 1\r\nContent-Length: " +
                                std::to_string(maximal_body.size()) + "\r\n\r\n";
    const auto complete = headers + maximal_body;
    HttpParser streamed;
    const auto first = std::span(reinterpret_cast<const std::uint8_t*>(complete.data()), 600);
    const auto rest = std::span(reinterpret_cast<const std::uint8_t*>(complete.data() + 600),
                                complete.size() - 600);
    (void)streamed.receive(first);
    assert(!streamed.failed() && !streamed.ready());
    (void)streamed.receive(rest);
    assert(streamed.ready() && parse_bootstrap_submit(streamed.request()));

    HttpParser duplicates;
    const std::string repeated = "POST /api/bootstrap/v1/start HTTP/1.1\r\nHost: 192.168.4.1\r\n"
                                 "Origin: http://192.168.4.1\r\nOrigin: http://192.168.4.1\r\n"
                                 "Content-Length: 2\r\n\r\n{}";
    (void)duplicates.receive(
        std::span(reinterpret_cast<const std::uint8_t*>(repeated.data()), repeated.size()));
    assert(duplicates.failed());
}
} // namespace

int main() {
    valid_envelopes_and_admission();
    parser_rejects_oversize_before_body_allocation();
}

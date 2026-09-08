#include "network/http.hpp"
#include "network_support.hpp"
#include "wtp/codec.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/frame_parser.hpp"
#include "wtp/memory_budget.hpp"
using namespace wsprrypico;
using namespace network_test;
namespace {
std::span<const std::uint8_t> bytes(std::string_view text) {
    return {reinterpret_cast<const std::uint8_t*>(text.data()), text.size()};
}
network::HttpRequest request(std::string method, std::string path, std::string body = {}) {
    return {std::move(method),
            std::move(path),
            std::move(body),
            {{"host", "127.0.0.1:8443"},
             {"origin", "https://127.0.0.1:8443"},
             {"x-wsprrypico-request", "1"},
             {"content-type", "application/json"}}};
}
void framing() {
    const std::string wire = "PUT /api/v1/network HTTP/1.1\r\nHost: "
                             "127.0.0.1:8443\r\nContent-Length: 16\r\n\r\n{\"enabled\":true}";
    for (std::size_t split = 0; split <= wire.size(); ++split) {
        network::HttpParser parser;
        REQUIRE(parser.receive(bytes(wire).first(split)) == split);
        REQUIRE(parser.receive(bytes(wire).subspan(split)) == wire.size() - split);
        REQUIRE(parser.ready() && !parser.failed());
        REQUIRE(parser.request().body == "{\"enabled\":true}");
    }
    const auto bad = [](std::string text) {
        network::HttpParser parser;
        parser.receive(bytes(text));
        REQUIRE(parser.failed());
    };
    bad("GET / HTTP/1.0\r\nHost: x\r\n\r\n");
    bad("GET / HTTP/1.1\nHost: x\n\n");
    bad("GET / HTTP/1.1\rX");
    bad("GET / HTTP/1.1\r\n\r\n");
    for (const auto& header :
         {"Host: x\r\nhost: y", "Host : x", "Host: x\r\nTransfer-Encoding: chunked",
          "Host: x\r\nExpect: 100-continue", "Host: x\r\nContent-Length: 1",
          "Host: x\r\nContent-Length: ", "Host: x\r\nContent-Length: -1",
          "Host: x\r\nContent-Length: 9999999999999999999999999999",
          "Host: x\r\nContent-Length: 0\r\nContent-Length: 0"})
        bad("GET / HTTP/1.1\r\n" + std::string(header) + "\r\n\r\n");
    bad("GET http://evil/ HTTP/1.1\r\nHost: x\r\n\r\n");
    bad("GET /%61pi HTTP/1.1\r\nHost: x\r\n\r\n");
    bad("GET / HTTP/1.1\r\nHost: x\r\n\r\nGET / HTTP/1.1\r\nHost: x\r\n\r\n");
    bad("GET / HTTP/1.1\r\nHost: " + std::string(2048, 'x'));
    bad("PUT / HTTP/1.1\r\nHost: x\r\nContent-Length: 65537\r\n\r\n");
    network::HttpParser partial;
    partial.receive(bytes("PUT / HTTP/1.1\r\nHost: x\r\nContent-Length: 10\r\n\r\n{"));
    REQUIRE(!partial.ready() && !partial.failed());
    const auto response = network::http_error(403, "forbidden").wire();
    REQUIRE(response.find("Connection: close\r\n") != response.npos);
    REQUIRE(response.find("Access-Control-Allow-Origin") == response.npos);
}
void api_checks() {
    Fixture f;
    const auto call = [&](network::HttpRequest r, std::string principal = "cert-a") {
        return f.api.handle(r, principal, "127.0.0.1:8443");
    };
    auto r = request("GET", "/api/v1/config");
    REQUIRE(call(r, "").status == 401);
    r.headers["host"] = "evil.test";
    REQUIRE(call(r).status == 403);
    r = request("PUT", "/api/v1/config", config);
    const auto initial = f.api.revision();
    REQUIRE(call(r).status == 428);
    r.headers["if-match"] = "stale";
    REQUIRE(call(r).status == 412);
    r.headers["if-match"] = initial;
    for (auto name : {"origin", "content-type", "x-wsprrypico-request"}) {
        auto bad = r;
        bad.headers.erase(name);
        REQUIRE(call(bad).status == 403);
    }
    auto bad = r;
    bad.headers["origin"] = "https://evil.test";
    REQUIRE(call(bad).status == 403);
    bad = r;
    bad.headers["sec-fetch-site"] = "cross-site";
    REQUIRE(call(bad).status == 403);
    auto saved = call(r);
    REQUIRE(saved.status == 200 && saved.etag != initial);
    REQUIRE(f.store.config()->password == "test-password");
    REQUIRE(saved.body.find("test-password") == saved.body.npos);
    auto value = wtp::json::parse(saved.body);
    REQUIRE(value);
    REQUIRE(value->get("config")->get("wifi")->get("password")->raw == "null");
    REQUIRE(call(r).status == 412);
    for (auto path : {"/api/v1/status", "/api/v1/jobs", "/api/v1/network", "/api/v1/schedules",
                      "/api/v1/capabilities"}) {
        auto result = call(request("GET", path));
        REQUIRE(result.status == 200);
        REQUIRE(wtp::json::parse(result.body));
        REQUIRE(result.body.find("test-password") == result.body.npos);
    }
    auto preserved = request("PUT", "/api/v1/config", std::string(value->get("config")->raw));
    preserved.headers["if-match"] = f.api.revision();
    REQUIRE(call(preserved).status == 200);
    REQUIRE(f.store.config()->password == "test-password");
    auto schedules =
        request("PUT", "/api/v1/schedules", R"({"schedules":[{"period_s":240,"phase_s":0}]})");
    schedules.headers["if-match"] = f.api.revision();
    REQUIRE(call(schedules).status == 200);
    REQUIRE(f.store.config()->schedules[0].period_s == 240);
    schedules.headers["if-match"] = f.api.revision();
    schedules.body = R"({"schedules":[{"period_s":120,"phase_s":0},{"period_s":240,"phase_s":0}]})";
    REQUIRE(call(schedules).status == 400);
    auto off = request("PUT", "/api/v1/network", "{\"enabled\":false}");
    off.headers["if-match"] = f.api.revision();
    REQUIRE(call(off).status == 200);
    REQUIRE(f.network.enabled);
    f.api.finish_request();
    REQUIRE(!f.network.enabled);
    REQUIRE(call(off).status == 412);
    f.flash.fail = true;
    preserved.headers["if-match"] = f.api.revision();
    preserved.body = config;
    REQUIRE(call(preserved).status == 503);
}
void deferred() {
    Fixture f;
    auto off = request("PUT", "/api/v1/network", "{\"enabled\":false}");
    off.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(off, "cert-a", "127.0.0.1:8443", 17).status == 200);
    f.api.finish_request(18); // Unrelated response, close and reused slot.
    f.api.finish_request(16, false);
    REQUIRE(f.network.enabled && f.network.pending && f.network.applied == 0);
    f.api.finish_request(17, false); // Initiating link loss cancels, never applies.
    REQUIRE(f.network.enabled && !f.network.pending);
    off.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(off, "cert-a", "127.0.0.1:8443", 19).status == 200);
    // USB and browser share authority; claim arriving before ACK cancels change.
    wtp::Request hello;
    hello.principal = "usb-physical";
    hello.session_id = std::string(32, '7');
    hello.request_id = std::string(32, '8');
    hello.operation = "HELLO";
    hello.payload_digest[0] = 1;
    hello.body = wtp::HelloBody{{"WTP/1"}};
    REQUIRE(f.service.handle(hello).ok);
    hello.request_id = std::string(32, '9');
    hello.operation = "CLAIM";
    hello.body = wtp::ClaimBody{std::string(32, '7'), 60000};
    REQUIRE(f.service.handle(hello).ok);
    wtp::available_memory = []() -> std::size_t { return 50000; };
    hello.request_id = std::string(32, 'a');
    hello.operation = "NOT_AN_OPERATION";
    REQUIRE(f.service.handle(hello).error == wtp::ErrorCode::UnknownOperation);
    hello.request_id = std::string(32, 'b');
    hello.operation = "LOAD";
    wtp::Job plan;
    plan.job_id = std::string(32, 'c');
    plan.mode = "tone";
    plan.total_duration_ns = 1000000;
    plan.events.push_back({0, 1000000, true, 1000000});
    hello.body = plan;
    REQUIRE(f.service.handle(hello).error == wtp::ErrorCode::InternalError);
    REQUIRE(f.service.status().state == wtp::State::Empty);
    wtp::available_memory = nullptr;
    f.api.finish_request(19);
    REQUIRE(f.network.enabled && !f.network.pending && f.network.applied == 0);
    off.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(off, "cert-a", "127.0.0.1:8443", 20).status == 409);
}
void jobs() {
    Fixture f;
    unsigned seq = 0;
    const std::string session(32, '1'), job_id(32, '2');
    auto send = [&](std::string op, std::string body, std::string principal = "cert-a") {
        auto r = request("POST", "/api/v1/jobs",
                         " {\"session_id\":\"" + session + "\",\"request_id\":\"" +
                             std::string(28, '0') + std::to_string(1000 + ++seq) +
                             "\",\"operation\":\"" + op + "\",\"body\":" + body + "} ");
        return f.api.handle(r, principal, "127.0.0.1:8443");
    };
    REQUIRE(send("HELLO",
                 "{\"versions\":[\"WTP/1\"],\"client_name\":\"test\",\"client_version\":\"1\"}")
                .status == 200);
    REQUIRE(send("CLAIM", "{\"owner_id\":\"" + session + "\",\"lease_ms\":5000}").status == 200);
    auto mutation = request("PUT", "/api/v1/config", config);
    mutation.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(mutation, "cert-b", "127.0.0.1:8443").status == 409);
    const auto plan = "{\"job_id\":\"" + job_id +
                      "\",\"profile\":\"rf-events/1\",\"mode\":\"tone\","
                      "\"total_duration_ns\":\"1000000000\",\"events\":[{\"offset_ns\":\"0\","
                      "\"duration_ns\":\"1000000000\","
                      "\"rf_on\":true,\"frequency_nhz\":\"3570100000000000\"}],\"allow_frequency_"
                      "adjustment\":false}";
    REQUIRE(send("LOAD", plan).status == 200);
    auto start = f.clock.snapshot().utc_now_ns + 2'000'000'000ULL;
    REQUIRE(send("ARM", "{\"job_id\":\"" + job_id + "\",\"start_utc_ns\":\"" +
                            std::to_string(start) + "\",\"max_start_uncertainty_ns\":\"1000\"}")
                .status == 200);
    REQUIRE(send("ABORT", "{\"job_id\":\"" + job_id + "\"}", "cert-b").status == 409);
    f.clock.now += 2'000'000'000ULL;
    f.service.poll();
    REQUIRE(f.service.status().state == wtp::State::Running);
    f.clock.now += 1'000'000'000ULL;
    f.service.poll();
    REQUIRE(f.service.status().state == wtp::State::Complete);
    REQUIRE(!f.service.status().output_active);
    REQUIRE(send("RELEASE", "{}").status == 200);
}
} // namespace
int main() {
    framing();
    api_checks();
    jobs();
    deferred();
    // JSON scratch admission must not silently narrow WTP's body grammar.
    std::string many_keys = "{";
    for (unsigned i = 0; i < 40; ++i)
        many_keys +=
            (i ? "," : "") + wtp::json::quote(std::string(129, 'k') + std::to_string(i)) + ":0";
    many_keys += '}';
    REQUIRE(wtp::json::parse(many_keys));
    const auto unknown_wire = "{\"type\":\"request\",\"protocol\":\"WTP/1\",\"session_id\":\"" +
                              std::string(32, '1') + "\",\"request_id\":\"" + std::string(32, '2') +
                              "\",\"op\":\"UNKNOWN\",\"body\":" + many_keys + "}";
    const auto unknown = wtp::json::parse(unknown_wire);
    REQUIRE(unknown);
    const auto decoded = wtp::decode_request(*unknown, "cert-a", bytes(unknown->raw));
    REQUIRE(decoded && decoded->operation == "UNKNOWN");
    {
        Fixture f;
        wtp::Endpoint endpoint(f.service, std::string(32, 'a'), "test");
        endpoint.connect("cert-a");
        const auto hello = wtp::encode_frame(bytes(
            R"({"type":"request","protocol":"WTP/1","session_id":"11111111111111111111111111111111","request_id":"22222222222222222222222222222222","op":"HELLO","body":{"versions":["WTP/1"],"client_name":"pressure","client_version":"1"}})"));
        std::size_t offset = 0;
        while (offset < hello.size()) {
            const auto used = endpoint.receive(std::span(hello).subspan(offset), 0);
            REQUIRE(used != 0);
            offset += used;
        }
        while (!endpoint.output().empty())
            endpoint.consume_output(endpoint.output().size(), 0);
        wtp::Request claim;
        claim.principal = "cert-a";
        claim.session_id = std::string(32, '1');
        claim.request_id = std::string(32, '3');
        claim.operation = "CLAIM";
        claim.payload_digest[0] = 1;
        claim.body = wtp::ClaimBody{std::string(32, '1'), 60000};
        REQUIRE(f.service.handle(claim).ok);
        wtp::Job plan;
        plan.job_id = std::string(32, '4');
        plan.mode = "tone";
        plan.total_duration_ns = 1000000;
        plan.events.push_back({0, 1000000, true, 1000000});
        claim.request_id = std::string(32, '4');
        claim.operation = "LOAD";
        claim.payload_digest[0] = 2;
        claim.body = plan;
        REQUIRE(f.service.handle(claim).ok);
        wtp::available_memory = []() -> std::size_t { return 0; };
        endpoint.poll(1); // Memory pressure drops advisory output, never authority.
        REQUIRE(endpoint.output().empty() && !endpoint.closed());
        REQUIRE(f.service.status().owner_id == std::string(32, '1'));
        REQUIRE(f.service.status().state == wtp::State::Loaded);
        wtp::available_memory = nullptr;
    }
    wtp::available_memory = []() -> std::size_t { return 0; };
    network::HttpParser starved;
    starved.receive(bytes("PUT / HTTP/1.1\r\nHost: x\r\nContent-Length: 32768\r\n\r\n"));
    REQUIRE(starved.exhausted());
    wtp::FrameParser frame;
    frame.feed(bytes("W"), 0);
    REQUIRE(frame.closed());
    Fixture f;
    REQUIRE(f.api.handle(request("GET", "/api/v1/status"), "cert", "127.0.0.1:8443").status == 503);
    wtp::available_memory = nullptr;
    std::cout << "HTTP/API adversarial behavior checks passed\n";
}

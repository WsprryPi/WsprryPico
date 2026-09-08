#include "network/http.hpp"
#include "network_support.hpp"
#include "wtp/codec.hpp"
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
    REQUIRE(!f.network.enabled);
    REQUIRE(call(off).status == 412);
    f.flash.fail = true;
    preserved.headers["if-match"] = f.api.revision();
    preserved.body = config;
    REQUIRE(call(preserved).status == 503);
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
    std::cout << "HTTP/API adversarial behavior checks passed\n";
}

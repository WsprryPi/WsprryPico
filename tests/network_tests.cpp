#include "encoding/morse.hpp"
#include "network/assets.hpp"
#include "network/http.hpp"
#include "network/identity.hpp"
#include "network_support.hpp"
#include "rf/stream_engine.hpp"
#include "runtime/memory_budget.hpp"

#include <new>

static std::size_t largest_new = 0;
static bool bounded_http = false;
static std::size_t bounded_http_limit = 8192;
void* operator new(std::size_t size) {
    largest_new = std::max(largest_new, size);
    if (bounded_http && size > bounded_http_limit)
        throw std::bad_alloc();
    if (auto* result = std::malloc(size ? size : 1))
        return result;
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept {
    std::free(memory);
}
void operator delete(void* memory, std::size_t) noexcept {
    std::free(memory);
}

using namespace wsprrypico;
using namespace network_test;
namespace {
std::size_t available_asset_memory = 0;
unsigned asset_allocation_calls = 0;
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
    const std::string wire = "PUT /api/control/v1/network HTTP/1.1\r\nHost: "
                             "127.0.0.1:8443\r\nContent-Length: 16\r\n\r\n{\"enabled\":true}";
    for (std::size_t split = 0; split <= wire.size(); ++split) {
        network::HttpParser parser;
        REQUIRE(parser.receive(bytes(wire).first(split)) == split);
        REQUIRE(parser.receive(bytes(wire).subspan(split)) == wire.size() - split);
        REQUIRE(parser.ready() && !parser.failed());
        REQUIRE(parser.request().body_view() == "{\"enabled\":true}");
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
void maximum_http_allocation() {
    Fixture f;
    auto body = network_test::control_request(request("POST", "/api/control/v1/unregistered", R"({"purpose":"bounded input"})")).body;
    body.resize(network::max_http_body, ' ');
    const std::string wire = "POST /api/control/v1/unregistered HTTP/1.1\r\nHost: 127.0.0.1:8443\r\n"
                             "Origin: https://127.0.0.1:8443\r\nX-WsprryPico-Request: 1\r\n"
                             "Content-Type: application/json\r\nContent-Length: 32768\r\n\r\n" +
                             body;
    largest_new = 0;
    bounded_http = true;
    network::HttpParser parser;
    for (std::size_t offset = 0; offset < wire.size();) {
        const auto part =
            bytes(wire).subspan(offset).first(std::min<std::size_t>(1023, wire.size() - offset));
        REQUIRE(parser.receive(part) == part.size());
        offset += part.size();
    }
    REQUIRE(parser.ready() && !parser.failed());
    REQUIRE(largest_new <= 4096);
    const auto response = f.api.handle(parser.request(), "cert", "127.0.0.1:8443");
    REQUIRE(response.status == 404);
    REQUIRE(f.service.status().state == execution::State::Empty);
    // Unregistered routes leave the execution service idle.
    REQUIRE(largest_new <= 8192);
    bounded_http = false;
}
std::size_t body_pages_live = 0;
unsigned body_page_calls = 0, body_page_failure = 0;
void http_body_failure_and_lifetime() {
    const auto allocate = execution::allocate_input;
    const auto deallocate = execution::deallocate_input;
    execution::allocate_input = [](std::size_t size) -> void* {
        REQUIRE(size <= 4096);
        if (++body_page_calls == body_page_failure)
            return nullptr;
        auto* page = std::malloc(size);
        if (page)
            ++body_pages_live;
        return page;
    };
    execution::deallocate_input = [](void* page) {
        if (page) {
            REQUIRE(body_pages_live > 0);
            --body_pages_live;
        }
        std::free(page);
    };
    const std::string header =
        "POST /api/control/v1/jobs HTTP/1.1\r\nHost: x\r\nContent-Length: 32768\r\n\r\n";
    std::string body(network::max_http_body, ' ');
    body.replace(4093, 11, "{\"value\":1}"); // Deliberately crosses a page boundary.
    for (unsigned failure = 1; failure <= 8; ++failure) {
        body_page_calls = 0;
        body_page_failure = failure;
        network::HttpParser parser;
        REQUIRE(parser.receive(bytes(header)) == header.size());
        REQUIRE(parser.failed() && parser.exhausted() && !parser.ready());
        REQUIRE(body_page_calls == failure && body_pages_live == 0);
        REQUIRE(parser.request().body_view().empty());
        REQUIRE(parser.receive(bytes(body)) == 0);
    }
    body_page_failure = body_page_calls = 0;
    {
        network::HttpRequest retained;
        {
            network::HttpParser parser;
            parser.receive(bytes(header));
            REQUIRE(!parser.ready() && !parser.failed());
            for (const auto c : body) {
                const std::uint8_t value = static_cast<std::uint8_t>(c);
                REQUIRE(parser.receive(std::span(&value, 1)) == 1);
            }
            REQUIRE(parser.ready() && !parser.failed());
            retained = parser.request();
            parser = {};
            REQUIRE(body_pages_live == 8);
        }
        REQUIRE(retained.body_view() == body);
        const auto parsed = execution::json::parse(retained.body_view());
        REQUIRE(parsed && parsed->get("value") && parsed->get("value")->raw == "1");
        retained = {};
        REQUIRE(body_pages_live == 0);
    }
    body_page_calls = 0;
    {
        network::HttpParser oversized;
        oversized.receive(bytes("POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 32769\r\n\r\n"));
        REQUIRE(oversized.failed() && !oversized.exhausted() && body_page_calls == 0);
        network::HttpParser empty;
        empty.receive(bytes("GET / HTTP/1.1\r\nHost: x\r\n\r\n"));
        REQUIRE(empty.ready() && body_page_calls == 0);
        execution::available_memory = []() -> std::size_t { return 32768 + 32768 + 1023; };
        network::HttpParser refused;
        refused.receive(bytes(header));
        REQUIRE(refused.exhausted() && body_page_calls == 0);
        execution::available_memory = nullptr;
    }
    REQUIRE(body_pages_live == 0);
    execution::allocate_input = allocate;
    execution::deallocate_input = deallocate;
}
void streamed_asset_admission() {
    Fixture f;
    const auto asset = network::web_asset("/");
    REQUIRE(asset && asset->body.size() > 16384);
    std::string expected;
    for (const auto part : asset->parts)
        expected += part;
    REQUIRE(expected.size() > 65536 && expected.find("hostname-form") != expected.npos);
    REQUIRE(expected.find("monitorRestart") != expected.npos);
    REQUIRE(expected.find("WsprryPicoPresentation=") < expected.find("pageIdentity="));
    REQUIRE(expected.find("id=\"station-area\"") < expected.find("id=\"saved-settings\""));
    REQUIRE(expected.find("id=\"saved-settings\"") < expected.find("id=\"device-diagnostics\""));
    REQUIRE(expected.find("id=\"device-diagnostics\"") < expected.find("id=\"wifi-host-area\""));
    const auto presentation = network::web_asset("/device-presentation.js");
    REQUIRE(presentation && presentation->body.find("WsprryPicoPresentation=") != expected.npos);
    // The generated asset is immutable static storage. Only bounded transport
    // scratch and the independent authority reserve consume target heap.
    // Static asset requests retain 16 KiB of processing scratch; that is the
    // controlling bound for this zero-body GET.
    available_asset_memory = 16384 + 32768;
    execution::available_memory = []() -> std::size_t { return available_asset_memory; };
    const auto allocator = execution::allocate_input;
    asset_allocation_calls = 0;
    execution::allocate_input = [](std::size_t size) -> void* {
        ++asset_allocation_calls;
        return std::malloc(size);
    };
    {
        const auto response = f.api.handle(network_test::control_request(request("GET", "/")), "cert", "127.0.0.1:8443");
        REQUIRE(response.status == 200 && response.body_size() == expected.size());
        REQUIRE(response.static_body.data() == asset->body.data());
        REQUIRE(response.buffered_body.empty() && response.body.empty());
        std::string delivered;
        for (std::size_t offset = 0; offset < response.body_size();) {
            const auto chunk = response.body_at(offset).first(
                std::min<std::size_t>(1024, response.body_at(offset).size()));
            delivered.append(reinterpret_cast<const char*>(chunk.data()), chunk.size());
            offset += chunk.size();
        }
        REQUIRE(delivered == expected);
        REQUIRE(response.wire_headers().find("Content-Length: " + std::to_string(expected.size()) +
                                             "\r\n") != std::string::npos);
    }
    REQUIRE(asset_allocation_calls == 0);
    --available_asset_memory;
    REQUIRE(f.api.handle(network_test::control_request(request("GET", "/")), "cert", "127.0.0.1:8443").status == 503);
    ++available_asset_memory;
    const auto direct = f.api.handle(network_test::control_request(request("GET", "/")), "cert", "127.0.0.1:8443");
    REQUIRE(direct.status == 200 && direct.static_body == asset->body);
    REQUIRE(asset_allocation_calls == 0);
    execution::allocate_input = allocator;
    REQUIRE(f.api.handle(network_test::control_request(request("GET", "/")), "cert", "127.0.0.1:8443").body_text() == expected);
    REQUIRE(f.service.status().state == execution::State::Empty && !f.service.status().output_active);
    execution::available_memory = nullptr;
}
void identities() {
    using network::canonical_local_hostname;
    const auto name = network::default_hostname("88:A2:9E:0A:60:DF");
    REQUIRE(name == "wpico-60df.local");
    REQUIRE(network::default_hostname("02:00:00:00:00:01") == "wpico-0001.local");
    // A suffix collision must not collapse independent full device identities.
    REQUIRE(network::default_hostname("02:00:00:0a:60:df") == name);
    REQUIRE(network::deployment_identity_matches(std::string(32, 'a'), std::string(32, 'a'), name));
    REQUIRE(network::deployment_identity_matches(std::string(32, 'a'), "", ""));
    REQUIRE(
        !network::deployment_identity_matches(std::string(32, 'b'), std::string(32, 'a'), name));
    REQUIRE(!network::deployment_identity_matches(std::string(32, 'a'), "", name));
    REQUIRE(!network::deployment_identity_matches("bad", "bad", name));
    for (const auto* bad :
         {"bad", "00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff", "89:a2:9e:0a:60:df", "88-a2-9e-0a-60-df",
          "88:a2:9e:0a:60:dg", "88:a2:9e:0a:60:df\n", "88:a2:9e:0a:60:+f"})
        REQUIRE(network::default_hostname(bad).empty());
    REQUIRE(
        !network::deployment_identity_matches(std::string(32, 'g'), std::string(32, 'g'), name));
    REQUIRE(canonical_local_hostname("PICO-A.LOCAL.") == "pico-a.local");
    REQUIRE(canonical_local_hostname(std::string(63, 'a') + ".local"));
    REQUIRE(!canonical_local_hostname(std::string(64, 'a') + ".local"));
    for (const auto* bad : {"", "-a.local", "a-.local", "a..local", "a.local..", "*.local",
                            "a.local.evil", "a_b.local", "a.local:443", "a\n.local"})
        REQUIRE(!canonical_local_hostname(bad));
    Fixture f;
    f.api.hostname_authority("pico-a.local:8443");
    auto r = request("GET", "/api/control/v1/status");
    const auto call = [&] { return f.api.handle(network_test::control_request(r), "cert", "127.0.0.1:8443").status; };
    for (const auto* host : {"pico-a.local:8443", "PICO-A.LOCAL.:8443", "127.0.0.1:8443"}) {
        r.headers["host"] = host;
        r.headers["origin"] = "https://" + std::string(host);
        REQUIRE(call() == 200);
    }
    for (const auto* bad :
         {"pico-b.local:8443", "pico-a.local", "pico-a.local:443", "pico-a.local:08443",
          "pico-a.local:8443/", "127.0.0.2:8443", "user@pico-a.local:8443",
          "pico-a.local.:8443.evil", "127.000.0.1:8443", "[::1]:8443"}) {
        r.headers["host"] = bad;
        r.headers["origin"] = "https://" + std::string(bad);
        REQUIRE(call() == 403);
    }
    for (const auto* origin : {"https://127.0.0.1:8443", "http://pico-a.local:8443",
                               "https://pico-a.local:8443/", "null", ""}) {
        r.headers["host"] = "pico-a.local:8443";
        r.headers["origin"] = origin;
        REQUIRE(call() == 403);
    }
    r.headers.erase("origin");
    REQUIRE(call() == 200);
    r.method = "PUT";
    r.path = "/api/control/v1/network";
    r.body = "{}";
    REQUIRE(call() == 403);
    r.headers["origin"] = "https://PICO-A.LOCAL.:8443";
    r.path = "/api/control/v1/network";
    r.body = "{\"enabled\":true}";
    REQUIRE(call() == 428); // Passed authority, revision still required.
    r.headers["host"] = "127.0.0.1:8443";
    REQUIRE(call() == 403); // Both aliases allowed independently, never mixed.
    REQUIRE(f.api.handle(network_test::control_request(request("GET", "/api/control/v1/status")), "cert", "127.0.0.2:8443").status == 403);
    REQUIRE(network::canonical_authority("PICO-A.LOCAL.") == "pico-a.local");
    REQUIRE(!network::canonical_authority("pico-a.local:443"));
}
void api_checks() {
    Fixture f;
    const auto call = [&](network::HttpRequest r, std::string principal = "cert-a") {
        return f.api.handle(network_test::control_request(r), principal, "127.0.0.1:8443");
    };
    auto r = request("GET", "/api/control/v1/config");
    REQUIRE(call(r, "").status == 401);
    r.headers["host"] = "evil.test";
    REQUIRE(call(r).status == 403);
    r = request("POST", "/api/control/v1/config/update", network_test::configuration_update(config));
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
    REQUIRE(saved.body_text().find("test-password") == saved.body_text().npos);
    auto value = execution::json::parse(saved.body_view());
    REQUIRE(value);
    REQUIRE(value->get("config")->get("wifi")->get("password")->raw == "null");
    REQUIRE(call(r).status == 412);
    for (auto path : {"/api/control/v1/status", "/api/control/v1/network", "/api/control/v1/schedules",
                      "/api/control/v1/capabilities"}) {
        auto result = call(request("GET", path));
        REQUIRE(result.status == 200);
        REQUIRE(execution::json::parse(result.body_view()));
        REQUIRE(result.body_text().find("test-password") == result.body_text().npos);
    }
    auto preserved = request("POST", "/api/control/v1/config/update", network_test::configuration_update(std::string(value->get("config")->raw)));
    // Redacted password offsets retain the original leading whitespace when
    // a paged configuration is materialized within the existing config limit.
    preserved.body.insert(0, 50, ' ');
    auto config_pages = std::make_shared<execution::FrameBuffer>();
    REQUIRE(config_pages->reserve(preserved.body.size()));
    config_pages->append(bytes(preserved.body));
    preserved.buffered_body = std::move(config_pages);
    preserved.body.clear();
    preserved.headers["if-match"] = f.api.revision();
    REQUIRE(call(preserved).status == 200);
    REQUIRE(f.store.config()->password == "test-password");
    auto schedules =
        request("PUT", "/api/control/v1/schedules", R"({"schedules":[{"period_s":240,"phase_s":0}]})");
    schedules.headers["if-match"] = f.api.revision();
    REQUIRE(call(schedules).status == 200);
    REQUIRE(f.store.config()->schedules[0].period_s == 240);
    schedules.headers["if-match"] = f.api.revision();
    schedules.body = R"({"schedules":[{"period_s":120,"phase_s":0},{"period_s":240,"phase_s":0}]})";
    REQUIRE(call(schedules).status == 400);
    auto off = request("PUT", "/api/control/v1/network", "{\"enabled\":false}");
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
    auto off = request("PUT", "/api/control/v1/network", "{\"enabled\":false}");
    off.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(off), "cert-a", "127.0.0.1:8443", 17).status == 200);
    f.api.finish_request(18); // Unrelated response, close and reused slot.
    f.api.finish_request(16, false);
    REQUIRE(f.network.enabled && f.network.pending && f.network.applied == 0);
    f.api.finish_request(17, false); // Initiating link loss cancels, never applies.
    REQUIRE(f.network.enabled && !f.network.pending);
    off.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(off), "cert-a", "127.0.0.1:8443", 19).status == 200);
    // USB and browser share authority; claim arriving before ACK cancels change.
    execution::Request hello;
    hello.principal = "usb-physical";
    hello.session_id = std::string(32, '7');
    hello.request_id = std::string(32, '8');
    hello.operation = "HELLO";
    hello.payload_digest[0] = 1;
    hello.body = execution::HelloBody{{"native-execution/1"}};
    REQUIRE(f.service.handle(hello).ok);
    hello.request_id = std::string(32, '9');
    hello.operation = "CLAIM";
    hello.body = execution::ClaimBody{std::string(32, '7'), 60000};
    REQUIRE(f.service.handle(hello).ok);
    execution::available_memory = []() -> std::size_t { return 50000; };
    hello.request_id = std::string(32, 'a');
    hello.operation = "NOT_AN_OPERATION";
    REQUIRE(f.service.handle(hello).error == execution::ErrorCode::UnknownOperation);
    hello.request_id = std::string(32, 'b');
    hello.operation = "LOAD";
    execution::Job plan;
    plan.job_id = std::string(32, 'c');
    plan.mode = "tone";
    plan.total_duration_ns = 1000000;
    plan.events.push_back({0, 1000000, true, 1000000});
    hello.body = plan;
    REQUIRE(f.service.handle(hello).error == execution::ErrorCode::InternalError);
    REQUIRE(f.service.status().state == execution::State::Empty);
    execution::available_memory = nullptr;
    f.api.finish_request(19);
    REQUIRE(f.network.enabled && !f.network.pending && f.network.applied == 0);
    off.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(off), "cert-a", "127.0.0.1:8443", 20).status == 409);
}
void restart_tests() {
    Fixture f;
    unsigned resets = 0;
    f.api.restart_control(
        [](void* context) {
            ++*static_cast<unsigned*>(context);
            return true;
        },
        &resets);
    auto restart = request("POST", "/api/control/v1/restart", "{}");
    REQUIRE(f.api.handle(network_test::control_request(restart), "cert-a", "127.0.0.1:8443", 31).status == 428);
    restart.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(restart), "", "127.0.0.1:8443", 31).status == 401);
    REQUIRE(f.api.handle(network_test::control_request(restart), "cert-a", "127.0.0.1:8443", 31).status == 202);
    REQUIRE(resets == 0);
    f.api.finish_request(32);
    REQUIRE(resets == 0);
    auto changed = request("POST", "/api/control/v1/config/update", network_test::configuration_update(config));
    changed.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(changed), "cert-a", "127.0.0.1:8443", 32).status == 409);
    f.api.finish_request(31, false);
    REQUIRE(resets == 0);
    REQUIRE(f.api.handle(network_test::control_request(restart), "cert-a", "127.0.0.1:8443", 33).status == 412);
    restart.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(restart), "cert-a", "127.0.0.1:8443", 33).status == 202);
    f.api.finish_request(33);
    f.api.finish_request(33);
    REQUIRE(resets == 1);
    restart.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(restart), "cert-a", "127.0.0.1:8443", 34).status == 202);
    execution::Request r;
    r.payload_digest[0] = 1;
    r.principal = "usb-physical";
    r.session_id = std::string(32, '7');
    r.request_id = std::string(32, '8');
    r.operation = "HELLO";
    r.body = execution::HelloBody{{"native-execution/1"}};
    REQUIRE(f.service.handle(r).ok);
    r.request_id = std::string(32, '9');
    r.operation = "CLAIM";
    r.body = execution::ClaimBody{std::string(32, '7'), 60000};
    REQUIRE(f.service.handle(r).ok);
    f.api.finish_request(34);
    REQUIRE(resets == 1);
}
void operations_tests() {
    Fixture f;
    auto get = request("GET", "/api/control/v1/operations");
    REQUIRE(f.api.handle(network_test::control_request(get), "", "127.0.0.1:8443").status == 401);
    REQUIRE(
        f.api.handle(network_test::control_request(get), "cert", "127.0.0.1:8443", 0, network::ManagementCarrier::EngineeringField)
            .status == 403);
    auto caps = f.api.handle(network_test::control_request(request("GET", "/api/control/v1/capabilities")), "cert", "127.0.0.1:8443", 0,
                             network::ManagementCarrier::EngineeringField);
    REQUIRE(caps.body_text().find("operations_status") == caps.body_text().npos);
    auto observed = f.api.handle(network_test::control_request(get), "cert", "127.0.0.1:8443");
    REQUIRE(observed.status == 200 && !observed.etag.empty());
    REQUIRE(observed.body_text().find("operations") != observed.body_text().npos);
    REQUIRE(observed.body_text().find("\"accepted\":null") != observed.body_text().npos);
    REQUIRE(f.api.public_status().body_text().find("correction") == std::string::npos);
    REQUIRE(f.api.public_status().body_text().find("accepted") == std::string::npos);
    f.api.restart_control([](void*) { return true; }, nullptr);
    unsigned seq = 0;
    auto send = [&](std::string operation, execution::RequestBody body) {
        execution::Request r;
        r.session_id = std::string(32, '1');
        r.principal = "test";
        r.request_id = std::string(30, '0') + std::to_string(10 + ++seq);
        r.operation = std::move(operation);
        r.body = std::move(body);
        r.payload_digest[0] = seq;
        return f.service.handle(r);
    };
    auto full_config = *standalone::parse_config(config);
    full_config.wspr_dial_frequency_hz = 14095600;
    full_config.schedules.clear();
    for (unsigned i = 0; i < 8; ++i)
        full_config.schedules.push_back({1920, i * 120});
    REQUIRE(f.store.save(full_config));
    REQUIRE(send("HELLO", execution::HelloBody{{"native-execution/1"}}).ok);
    REQUIRE(send("CLAIM", execution::ClaimBody{std::string(32, '1'), 60000}).ok);
    encoding::MorseMessage m;
    m.job_id = std::string(32, '2');
    m.mode = "dfcw";
    m.text = std::string(32, 'E');
    m.mark_frequency_nhz = 135505000000000ULL;
    m.space_frequency_nhz = 135500000000000ULL;
    m.dot_ns = 3000000000;
    m.dash_ns = 9000000000;
    m.intra_gap_ns = 1000000000;
    m.character_gap_ns = 3000000000;
    m.word_gap_ns = 7000000000;
    standalone::MessageSchedule saved;
    saved.first_start_utc_ns = f.clock.snapshot().utc_now_ns + 2000000000ULL;
    saved.period_s = 86400;
    saved.message = m;
    saved.message.mark_frequency_nhz = 135500000000000ULL;
    saved.message.space_frequency_nhz = 135505000000000ULL;
    REQUIRE(f.store.save_message_schedule(saved));
    auto compiled = encoding::compile_message(m);
    REQUIRE(compiled.job);
    REQUIRE(send("LOAD", std::move(*compiled.job)).ok);
    const auto start = f.clock.snapshot().utc_now_ns + 2000000000ULL;
    REQUIRE(send("ARM", execution::ArmBody{m.job_id, start, 1000}).ok);
    auto reset = request("POST", "/api/control/v1/restart", "{}");
    reset.headers["if-match"] = f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(reset), "cert", "127.0.0.1:8443").status == 409);
    f.clock.now += 2000000000ULL;
    f.service.poll();
    REQUIRE(f.service.status().state == execution::State::Running);
    REQUIRE(!f.service.status().output_active); // Inhibited RF-off job remains running.
    const auto watermark = f.store.watermark();
    const auto revision = f.api.revision();
    largest_new = 0;
    bounded_http = true;
    observed = f.api.handle(network_test::control_request(get), "cert", "127.0.0.1:8443");
    bounded_http = false;
    REQUIRE(largest_new <= 8192);
    REQUIRE(observed.body_text().find("\"text\":\"" + m.text + "\"") != observed.body_text().npos);
    REQUIRE(observed.body_text().find("\"frequency_nhz\":\"135505000000000\"") != observed.body_text().npos);
    REQUIRE(observed.body_text().find("\"dash_ns\":\"3000000000\"") != observed.body_text().npos);
    REQUIRE(observed.body_text().find("\"reset_allowed\":false") != observed.body_text().npos);
    REQUIRE(observed.body.size() < 6144);
    REQUIRE(f.store.watermark() == watermark && f.api.revision() == revision);
    REQUIRE(f.api.handle(network_test::control_request(reset), "cert", "127.0.0.1:8443").status == 409);
    std::cout << "Operations running message response bytes: " << observed.body.size() << '\n';
}

void jobs() {
    Fixture f;
    const std::string session(32,'1'),job_id(32,'2');
    const auto command=[&](std::string op,execution::RequestBody body={},std::string principal="cert-a"){
        return internal_command(f.service,std::move(op),std::move(body),std::move(principal),session);
    };
    REQUIRE(command("HELLO",execution::HelloBody{{"native-execution/1"}}).ok);
    REQUIRE(command("CLAIM",execution::ClaimBody{session,5000}).ok);
    auto mutation=request("POST","/api/control/v1/config/update",configuration_update(config));
    mutation.headers["if-match"]=f.api.revision();
    REQUIRE(f.api.handle(control_request(mutation),"cert-b","127.0.0.1:8443").status==409);
    execution::Job job;job.job_id=job_id;job.mode="tone";job.total_duration_ns=1'000'000'000;
    job.events.push_back({0,job.total_duration_ns,true,3'570'100'000'000'000});
    REQUIRE(command("LOAD",std::move(job)).ok);
    REQUIRE(command("ARM",execution::ArmBody{job_id,f.clock.snapshot().utc_now_ns+2'000'000'000,1000}).ok);
    REQUIRE(command("ABORT",execution::AbortBody{job_id},"cert-b").error==execution::ErrorCode::AuthenticationRequired);
    REQUIRE(f.service.status().state==execution::State::Armed);
    f.clock.now+=2'000'000'000;f.service.poll();REQUIRE(f.service.status().state==execution::State::Running);
    f.clock.now+=1'000'000'000;f.service.poll();REQUIRE(f.service.status().state==execution::State::Complete);
    REQUIRE(!f.service.status().output_active);REQUIRE(command("RELEASE").ok);
}
void maximum_http_job() {
    Fixture f;
    const auto header=[](std::size_t size){return "POST /api/control/v1/jobs HTTP/1.1\r\nHost: 127.0.0.1:8443\r\nContent-Length: "+std::to_string(size)+"\r\n\r\n";};
    const std::string body(network::max_http_body,' ');
    network::HttpParser parser;const auto wire=header(body.size())+body;
    REQUIRE(parser.receive(bytes(wire))==wire.size()&&parser.ready()&&!parser.failed());
    execution::available_memory=[]()->std::size_t{return 90000;};
    REQUIRE(f.api.handle(parser.request(),"cert-a","127.0.0.1:8443").status==404);
    execution::available_memory=nullptr;
    network::HttpParser oversized;oversized.receive(bytes(header(body.size()+1)));
    REQUIRE(oversized.failed()&&!oversized.ready());
    REQUIRE(f.service.status().state==execution::State::Empty&&!f.service.status().owner_id);
}
void fragmented_raw_browser_load() {
    Fixture f;
    auto value=request("POST","/api/control/v1/jobs",std::string(17000,'x'));
    auto storage=std::make_shared<execution::FrameBuffer>();REQUIRE(storage->reserve(value.body.size()));
    storage->append(bytes(value.body));value.buffered_body=storage;value.body.clear();
    largest_new=0;bounded_http_limit=4096;bounded_http=true;
    const auto result=f.api.handle(value,"cert-a","127.0.0.1:8443");
    bounded_http=false;bounded_http_limit=8192;
    REQUIRE(result.status==404&&largest_new<=4096);
    REQUIRE(f.service.status().state==execution::State::Empty&&!f.service.status().owner_id);
}
std::string compact_body(std::string message,std::string mode="fskcw") {
    return "{\"job_id\":\"44444444444444444444444444444444\",\"mode\":"+execution::json::quote(mode)+
        ",\"message\":"+execution::json::quote(message)+
        R"(,"frequency_nhz":"10140005000000000","space_frequency_nhz":"10140000000000000","timing":{"dot_ns":"3000000000","dash_ns":"9000000000","intra_gap_ns":"3000000000","character_gap_ns":"9000000000","word_gap_ns":"21000000000"},"repeat_count":1,"repeat_gap_ns":"0","allow_frequency_adjustment":true})";
}
void message_jobs() {
    Fixture f;const std::string session(32,'a');
    REQUIRE(!internal_message(f.service,compact_body(std::string(32,'?'))).ok);
    REQUIRE(internal_command(f.service,"HELLO",execution::HelloBody{{"native-execution/1"}},"cert",session).ok);
    REQUIRE(internal_command(f.service,"CLAIM",execution::ClaimBody{session,60000},"cert",session).ok);
    REQUIRE(!internal_message(f.service,compact_body(std::string(33,'?'))).ok);
    REQUIRE(f.service.status().state==execution::State::Empty);
    REQUIRE(internal_message(f.service,compact_body(std::string(32,'?'))).ok);
    REQUIRE(f.service.status().state==execution::State::Loaded&&!f.service.status().output_active);
    REQUIRE(internal_command(f.service,"RELEASE",{},"cert",session).ok);
}
void compact_message_actual_admission() {
    Fixture f;const std::string session(32,'a');
    REQUIRE(internal_command(f.service,"HELLO",execution::HelloBody{{"native-execution/1"}},"cert",session).ok);
    REQUIRE(internal_command(f.service,"CLAIM",execution::ClaimBody{session,60000},"cert",session).ok);
    execution::available_memory=[]()->std::size_t{return 67000;};
    const auto loaded=internal_message(f.service,compact_body("ET E"));
    execution::available_memory=nullptr;REQUIRE(loaded.ok);
    REQUIRE(f.service.status().state==execution::State::Loaded&&!f.service.status().output_active);
    REQUIRE(internal_command(f.service,"RELEASE",{},"cert",session).ok);
}

void status_read_admission() {
    Fixture f;
    execution::available_memory = []() -> std::size_t { return 32768 + 8192; };
    REQUIRE(f.api.handle(network_test::control_request(request("GET", "/api/control/v1/status")), "cert", "127.0.0.1:8443").status == 200);
    execution::available_memory = []() -> std::size_t { return 32768 + 8192 - 1; };
    REQUIRE(f.api.handle(network_test::control_request(request("GET", "/api/control/v1/status")), "cert", "127.0.0.1:8443").status == 503);
    execution::available_memory = nullptr;
}

void message_jobs_with_resident_heap_pressure() {
    // LOAD alone must never submit samples or arm the sink.
    struct Sink final : rf::BlockSink {
        bool stop(std::uint64_t) override {
            return true;
        }
        bool submit(std::uint64_t, std::uint64_t, std::span<const std::uint32_t>,
                    std::uint64_t) override {
            std::abort();
        }
        bool arm(std::uint64_t, std::uint64_t, std::uint64_t, rf::LaunchGuard) override {
            std::abort();
        }
        rf::SinkReport poll(std::uint64_t) override {
            return {};
        }
        bool output_active() const override {
            return false;
        }
    } sink;
    rf::StreamEngine engine(sink);
    Fixture f(0, std::string(32, 'a'), &engine);
    const std::string session(32,'a');
    const auto send=[&](std::string op,execution::RequestBody body={}){
        return internal_command(f.service,std::move(op),std::move(body),"cert",session);
    };
    REQUIRE(send("HELLO",execution::HelloBody{{"native-execution/1"}}).ok);
    for (const auto mode : {"qrss", "fskcw", "dfcw"}) {
        REQUIRE(send("CLAIM",execution::ClaimBody{session,60000}).ok);
        const auto body =
            "{\"job_id\":\"" + std::string(32, '8') + "\",\"mode\":\"" + mode +
            "\",\"message\":\"CQ CQ DE AA0NT EM18 QRSS TEST 73\","
            "\"frequency_nhz\":\"10140005000000000\",\"space_frequency_nhz\":\"10140000000000000\","
            "\"timing\":{\"dot_ns\":\"3000000000\",\"dash_ns\":\"9000000000\","
            "\"intra_gap_ns\":\"3000000000\",\"character_gap_ns\":\"9000000000\","
            "\"word_gap_ns\":\"21000000000\"},\"repeat_count\":1,"
            "\"repeat_gap_ns\":\"3000000000\",\"allow_frequency_adjustment\":true}";
        // The resident event pages and transport/history allocations leave
        // less than the old fixed 64 KiB gate, but enough for this actual plan
        // plus the unchanged independent 32 KiB reserve.
        execution::available_memory = []() -> std::size_t { return 60000; };
        const auto loaded = internal_message(f.service, body);
        execution::available_memory = nullptr;
        REQUIRE(loaded.ok);
        REQUIRE(f.service.status().state == execution::State::Loaded);
        REQUIRE(!f.service.status().output_active);
        REQUIRE(send("RELEASE").ok);
        REQUIRE(!f.service.status().owner_id);
    }
}
} // namespace
int main() {
    message_jobs_with_resident_heap_pressure();
    identities();
    framing();
    maximum_http_allocation();
    http_body_failure_and_lifetime();
    streamed_asset_admission();
    api_checks();
    jobs();
    maximum_http_job();
    fragmented_raw_browser_load();
    message_jobs();
    compact_message_actual_admission();
    status_read_admission();
    deferred();
    restart_tests();
    operations_tests();
    // JSON scratch admission must not silently narrow the JSON object grammar.
    std::string many_keys = "{";
    for (unsigned i = 0; i < 40; ++i)
        many_keys +=
            (i ? "," : "") + execution::json::quote(std::string(129, 'k') + std::to_string(i)) + ":0";
    many_keys += '}';
    REQUIRE(execution::json::parse(many_keys));
    execution::available_memory = []() -> std::size_t { return 0; };
    network::HttpParser starved;
    starved.receive(bytes("PUT / HTTP/1.1\r\nHost: x\r\nContent-Length: 32768\r\n\r\n"));
    REQUIRE(starved.exhausted());
    Fixture f;
    REQUIRE(f.api.handle(network_test::control_request(request("GET", "/api/control/v1/status")), "cert", "127.0.0.1:8443").status == 503);
    execution::available_memory = nullptr;
    std::cout << "HTTP/API adversarial behavior checks passed\n";
}

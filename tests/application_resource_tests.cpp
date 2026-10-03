#include "application/resources.hpp"
#include "network_support.hpp"
#include "wtp/json.hpp"

using namespace wsprrypico;
namespace {
network::HttpRequest request(std::string method, std::string path, std::string body = {}) {
    return {std::move(method),
            std::move(path),
            std::move(body),
            {{"host", "127.0.0.1:8443"},
             {"origin", "https://127.0.0.1:8443"},
             {"content-type", "application/json"},
             {"x-wsprrypico-request", "1"}}};
}
struct Member {
    network_test::Fixture f;
    standalone::Scheduler scheduler;
    network::BrowserApi api;
    standalone::Store& initial_store() {
        auto config = standalone::parse_config(network_test::config);
        REQUIRE(config && f.store.save(*config));
        REQUIRE(f.store.reserve(1'800'000'000'000'000'000ULL));
        return f.store;
    }
    Member()
        : scheduler(initial_store(), f.service),
          api(f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test") {}
    network::HttpResponse call(network::HttpRequest r) {
        return api.handle(r, "test", "127.0.0.1:8443");
    }
    std::string envelope(std::string_view schema, std::string_view field, std::string payload) {
        return "{\"schema\":" + wtp::json::quote(schema) + ",\"target\":" +
               application::target(std::string(32, 'a'), f.service.status().boot_id) + ',' +
               wtp::json::quote(field) + ':' + payload + '}';
    }
    network::HttpRequest station() {
        auto r = request("PUT", "/api/v1/station",
                         envelope(application::station_schema, "station",
                                  R"({"callsign":"K1ABC","locator":"FN42AB","power_dbm":10})"));
        r.headers["if-match"] = api.revision();
        return r;
    }
    network::HttpRequest hardware(hardware::PinPlan pins = {}) {
        auto r =
            request("PUT", "/api/v1/hardware",
                    envelope(application::hardware_schema, "pins", hardware::serialize_plan(pins)));
        r.headers["if-match"] = api.revision();
        return r;
    }
};
void readings_and_scoped_saves() {
    Member m;
    auto enabled = *m.f.store.config();
    enabled.enabled = true;
    enabled.expires_utc_s = 1'900'000'000;
    REQUIRE(m.f.store.save(enabled));
    const auto initial = *m.f.store.config();
    const auto watermark = m.f.store.watermark();
    const auto revision = m.api.revision();
    network::BrowserApi other(m.f.service, m.f.store, m.scheduler, m.f.network,
                              std::string(32, 'b'), "test");
    REQUIRE(other.revision() != revision);
    for (const auto path : {"/api/v1/application", "/api/v1/station", "/api/v1/hardware"}) {
        const auto response = m.call(request("GET", path));
        REQUIRE(response.status == 200 && response.etag == revision);
        REQUIRE(wtp::json::parse(response.body));
        REQUIRE(response.body.size() < 4096);
        REQUIRE(response.body.find("test-password") == response.body.npos);
        REQUIRE(response.body.find("test-network") == response.body.npos);
    }
    REQUIRE(m.scheduler.command("STOP").find("\"suspended\":true") != std::string::npos);
    const auto saved = m.call(m.station());
    REQUIRE(saved.status == 200 && saved.etag != revision);
    REQUIRE(m.f.store.config()->callsign == "K1ABC" && m.f.store.config()->power_dbm == 10);
    REQUIRE(m.f.store.config()->password == initial.password);
    REQUIRE(m.f.store.config()->ssid == initial.ssid &&
            m.f.store.config()->ntp_ipv4 == initial.ntp_ipv4);
    REQUIRE(m.f.store.config()->enabled == initial.enabled);
    REQUIRE(m.f.store.config()->schedules == initial.schedules);
    REQUIRE(m.f.store.config()->expires_utc_s == initial.expires_utc_s);
    REQUIRE(m.f.store.config()->pins == initial.pins && m.f.store.watermark() == watermark);
    REQUIRE(m.scheduler.status().find("\"suspended\":true") != std::string::npos);
    standalone::Store reload(m.f.flash);
    REQUIRE(reload.load() && reload.config() == m.f.store.config() &&
            reload.watermark() == watermark);
}
void authentication_and_revisions() {
    Member m;
    for (auto r : {m.station(), m.hardware()}) {
        const auto original = m.f.flash.bytes;
        REQUIRE(m.api.handle(r, "", "127.0.0.1:8443").status == 401);
        const auto good_origin = r.headers["origin"];
        r.headers["origin"] = "https://evil.example";
        REQUIRE(m.call(r).status == 403);
        r.headers["origin"] = good_origin;
        r.headers.erase("if-match");
        REQUIRE(m.call(r).status == 428);
        r.headers["if-match"] = "stale";
        REQUIRE(m.call(r).status == 412);
        REQUIRE(m.f.flash.bytes == original);
    }
    const auto old = m.station();
    const auto a = *m.f.store.config();
    REQUIRE(m.call(old).status == 200);
    auto restore = request("PUT", "/api/v1/config", standalone::serialize_config(a));
    restore.headers["if-match"] = m.api.revision();
    REQUIRE(m.call(restore).status == 200);
    REQUIRE(m.call(old).status == 412); // A-B-A does not revive the A token.
    const auto token = m.api.revision();
    restore.headers["if-match"] = token;
    REQUIRE(m.call(restore).status == 200);
    REQUIRE(m.api.revision() != token); // Identical saves consume journal generation too.
    auto before_boot = m.station();
    m.f.service.reset();
    REQUIRE(m.call(before_boot).status == 412);
}
void rejection_is_atomic() {
    Member m;
    auto invalid = m.station();
    const auto original = m.f.flash.bytes;
    const auto revision = m.api.revision();
    const auto reject = [&](network::HttpRequest r, unsigned status) {
        REQUIRE(m.call(r).status == status);
        REQUIRE(m.f.flash.bytes == original && m.api.revision() == revision);
    };
    for (const auto field : {"scope", "device_id", "boot_id"}) {
        auto value = wtp::json::parse(invalid.body);
        const auto part = value->get("target")->get(field)->raw;
        auto r = invalid;
        r.body.replace(part.offset(), part.size(), "\"wrong\"");
        reject(r, 409);
    }
    auto r = invalid;
    r.body.replace(r.body.find("transmitter-station/1"), 21, "transmitter-station/2");
    reject(r, 400);
    r = invalid;
    r.body.insert(r.body.size() - 1, ",\"enabled\":true");
    reject(r, 400);
    r = invalid;
    r.body.insert(r.body.size() - 1, ",\"schema\":\"transmitter-station/1\"");
    reject(r, 400);
    for (const auto power : {"true", "13.0", "-1", "4294967296", "11", "\"10\""}) {
        r = invalid;
        r.body.replace(r.body.find("\"power_dbm\":10") + 12, 2, power);
        reject(r, 400);
    }
    r = invalid;
    r.body.replace(r.body.find("K1ABC"), 5, "K1ABC/P");
    reject(r, 400);
    r = invalid;
    r.body.resize(application::max_update_bytes + 1, ' ');
    reject(r, 413);
    hardware::PinPlan p;
    p.rf = 14;
    reject(m.hardware(p), 400);
    const auto conflict = m.call(m.hardware(p));
    REQUIRE(conflict.etag.empty());
    const auto details = wtp::json::parse(conflict.body);
    REQUIRE(details && details->get("error")->string() == "pin_conflict");
    REQUIRE(details->get("gp")->raw == "14" && details->get("owner")->string() == "rf");
    auto legacy = *m.f.store.config();
    legacy.pins = p;
    auto legacy_request = request("PUT", "/api/v1/config", standalone::serialize_config(legacy));
    legacy_request.headers["if-match"] = revision;
    const auto legacy_error = m.call(legacy_request);
    REQUIRE(legacy_error.status == 400 && legacy_error.etag.empty());
    REQUIRE(wtp::json::parse(legacy_error.body)->get("error")->string() == "pin_conflict");
    p = {};
    p.amplifier = 5;
    reject(m.hardware(p), 400);
    p = {};
    p.lpf = {5};
    reject(m.hardware(p), 400);
    p = {};
    p.engine = hardware::PinPlan::Engine::I2c;
    p.rf.reset();
    p.i2c_pair = 0;
    reject(m.hardware(p), 400);
}
void ownership_and_pending_changes() {
    Member m;
    auto r = request("PUT", "/api/v1/network", "{\"enabled\":false}");
    r.headers["if-match"] = m.api.revision();
    REQUIRE(m.call(r).status == 200);
    REQUIRE(m.call(m.station()).status == 409);
    REQUIRE(m.call(m.hardware()).status == 409);
    m.api.finish_request(0, false);
    unsigned sequence = 0;
    auto invoke = [&](std::string operation, wtp::RequestBody body) {
        wtp::Request request;
        request.principal = "usb";
        request.session_id = std::string(32, 'b');
        request.request_id = std::string(31, '0') + std::to_string(++sequence);
        request.operation = std::move(operation);
        request.body = std::move(body);
        request.payload_digest[0] = sequence;
        return m.f.service.handle(request);
    };
    REQUIRE(invoke("HELLO", wtp::HelloBody{{"WTP/1"}}).ok);
    REQUIRE(invoke("CLAIM", wtp::ClaimBody{std::string(32, 'b'), 60000}).ok);
    const auto flash = m.f.flash.bytes;
    REQUIRE(m.call(m.station()).status == 409);
    wtp::Job job{std::string(32, 'c'), "rf-events/1", "tone", 1'000'000'000, {}, false};
    REQUIRE(job.events.push_back({0, job.total_duration_ns, true, 7'040'000'000'000'000ULL}));
    REQUIRE(invoke("LOAD", std::move(job)).ok);
    REQUIRE(m.f.service.status().state == wtp::State::Loaded);
    REQUIRE(m.call(m.hardware()).status == 409);
    REQUIRE(invoke("ARM", wtp::ArmBody{std::string(32, 'c'),
                                       m.f.clock.snapshot().utc_now_ns + 3'000'000'000, 1000})
                .ok);
    REQUIRE(m.call(m.station()).status == 409);
    REQUIRE(m.f.flash.bytes == flash);
}
void saved_active_and_failures() {
    Member m;
    auto p = hardware::PinPlan{};
    p.rf = 28;
    const auto boot_active = m.call(request("GET", "/api/v1/hardware"));
    auto response = m.call(m.hardware(p));
    REQUIRE(response.status == 200 && m.f.service.output_inhibited());
    auto parsed = wtp::json::parse(response.body);
    REQUIRE(parsed->get("saved")->get("rf_gp")->raw == "28");
    REQUIRE(parsed->get("active")->get("rf_gp")->raw == "2");
    REQUIRE(parsed->get("pending_restart")->boolean());
    REQUIRE(parsed->get("active_revision")->string() ==
            wtp::json::parse(boot_active.body)->get("active_revision")->string());
    REQUIRE(m.call(m.station()).status == 200 && m.f.service.output_inhibited());
    REQUIRE(m.call(m.hardware()).status == 200); // Restore old pins; latch remains.
    REQUIRE(m.scheduler.hardware_restart_required() && m.f.service.output_inhibited());
    Member failure;
    const auto before = failure.f.store.config();
    auto mutation = failure.station();
    failure.f.flash.fail = true;
    REQUIRE(failure.call(mutation).status == 503);
    REQUIRE(failure.f.store.config() == before);
    REQUIRE(!failure.f.store.healthy());
    const auto read = failure.call(request("GET", "/api/v1/hardware"));
    parsed = wtp::json::parse(read.body);
    REQUIRE(parsed->get("saved")->raw == "null" && !parsed->get("storage_healthy")->boolean());
    failure.f.flash.fail = false;
    standalone::Store recovered(failure.f.flash);
    REQUIRE(recovered.load() && recovered.config() == before);
    network_test::Fixture blank;
    auto r =
        request("PUT", "/api/v1/station",
                m.envelope(application::station_schema, "station", application::station(*before)));
    r.headers["if-match"] = blank.api.revision();
    REQUIRE(blank.api.handle(r, "test", "127.0.0.1:8443").status == 409);
    REQUIRE(blank.api.handle(request("GET", "/api/v1/hardware"), "test", "127.0.0.1:8443")
                .body.find("\"active\":null") != std::string::npos);
}
void samples() {
    Member m;
    std::cout << '{';
    bool comma = false;
    const auto emit = [&](std::string_view name, network::HttpResponse result) {
        if (comma)
            std::cout << ',';
        comma = true;
        std::cout << wtp::json::quote(name) << ':' << result.body;
    };
    emit("application", m.call(request("GET", "/api/v1/application")));
    emit("station", m.call(request("GET", "/api/v1/station")));
    emit("hardware", m.call(request("GET", "/api/v1/hardware")));
    hardware::PinPlan p;
    p.rf = 28;
    emit("pending", m.call(m.hardware(p)));
    network_test::Fixture blank;
    emit("blank",
         blank.api.handle(request("GET", "/api/v1/application"), "test", "127.0.0.1:8443"));
    m.f.flash.fail = true;
    REQUIRE(m.call(m.station()).status == 503);
    emit("unhealthy", m.call(request("GET", "/api/v1/application")));
    std::cout << "}\n";
}
class DisableEngine final : public wtp::RfEngine {
  public:
    bool can_disable = true;
    wtp::PrepareResult prepare(const wtp::Job&) override {
        return {true, {}};
    }
    bool begin(const wtp::Job&, std::uint64_t) override {
        return false;
    }
    wtp::EngineReport poll(std::uint64_t) override {
        return {};
    }
    bool disable(std::uint64_t) override {
        return can_disable;
    }
    bool output_active() const override {
        return false;
    }
};
void disable_failure_and_maximum_response(bool emit_fault = false) {
    Member m;
    DisableEngine engine;
    network_test::Identity identity;
    wtp::JobService service(m.f.clock, engine, identity);
    standalone::Scheduler scheduler(m.f.store, service);
    network::BrowserApi api(service, m.f.store, scheduler, m.f.network, std::string(32, 'a'),
                            "test");
    auto p = hardware::PinPlan{};
    p.rf = 28;
    auto update = m.hardware(p);
    update.headers["if-match"] = api.revision();
    engine.can_disable = false;
    const auto failure = api.handle(update, "test", "127.0.0.1:8443");
    REQUIRE(failure.status == 503 &&
            failure.body.find("output_disable_failed") != std::string::npos);
    REQUIRE(service.output_inhibited() && scheduler.hardware_application_failed());
    const auto readback = api.handle(request("GET", "/api/v1/hardware"), "test", "127.0.0.1:8443");
    REQUIRE(wtp::json::parse(readback.body)->get("application_error")->string() ==
            "output_disable_failed");
    if (emit_fault)
        std::cout << readback.body << '\n';
    REQUIRE(m.f.store.config()->pins.rf == 28 && scheduler.active_pins().rf == 2);
    auto station = m.station();
    station.headers["if-match"] = api.revision();
    REQUIRE(api.handle(station, "test", "127.0.0.1:8443").status == 409);
    Member maximum;
    auto config = *maximum.f.store.config();
    config.expires_utc_s = 2'147'483'647ULL; // Existing Config v1 signed JSON integer bound.
    config.schedules.clear();
    for (unsigned i = 0; i < 8; ++i)
        config.schedules.push_back({960, i * 120});
    REQUIRE(maximum.f.store.save(config));
    auto result = maximum.call(request("GET", "/api/v1/application"));
    REQUIRE(result.status == 200 && result.body.size() < 4096);
    const auto parsed = wtp::json::parse(result.body);
    REQUIRE(parsed->get("recurrence")->get("expires_utc_s")->string() == "2147483647");
    REQUIRE(parsed->get("recurrence")->get("schedules")->elements().size() == 8);
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--fault") {
        disable_failure_and_maximum_response(true);
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--samples") {
        samples();
        return 0;
    }
    if (argc == 4 && std::string_view(argv[1]) == "--request") {
        Member m;
        auto r = request("PUT", argv[2], argv[3]);
        r.headers["if-match"] = m.api.revision();
        const auto response = m.call(r);
        std::cout << "{\"status\":" << response.status << ",\"body\":";
        if (response.body.empty())
            std::cout << "null";
        else
            std::cout << response.body;
        std::cout << "}\n";
        return 0;
    }
    readings_and_scoped_saves();
    authentication_and_revisions();
    rejection_is_atomic();
    ownership_and_pending_changes();
    saved_active_and_failures();
    disable_failure_and_maximum_response();
}

// SPDX-License-Identifier: MIT
#include "application/resources.hpp"
#include "network/local_usb_api.hpp"
#include "network/test_tone_query.hpp"
#include "network_support.hpp"
#include "rf/waveform.hpp"
#include "si5351_test_tone_fixture.hpp"
#include "usb/management_endpoint.hpp"

#include <fstream>

using namespace wsprrypico;
namespace {
struct Engine : wtp::RfEngine {
    standalone::DryRunEngine native;
    network_test::Clock& clock;
    unsigned drive = 12, prepares = 0, schedules = 0, disables = 0;
    bool fail_disable = false, fail_prepare = false, bad_pad = false, missing_pad = false;
    bool stale_pad = false;
    wtp::PadObservation pad;
    explicit Engine(network_test::Clock& c) : clock(c) {}
    wtp::PrepareResult prepare(const wtp::Job& job) override {
        ++prepares;
        if (fail_prepare)
            return {};
        REQUIRE(job.mode == "tone" && job.events.size() == 1);
        REQUIRE(job.events[0].offset_ns == 0 && job.events[0].duration_ns == job.total_duration_ns);
        const auto increment = rf::frequency_increment(*job.events[0].frequency_nhz);
        REQUIRE(increment);
        return {true, {{0, *job.events[0].frequency_nhz, rf::realized_nhz(*increment)}}};
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const wtp::Job& job, std::uint64_t at,
                  const wtp::LocalStartConditions& c) override {
        ++schedules;
        pad = {stale_pad ? 1U : schedules, clock.now, 2, bad_pad ? 4 : int(drive)};
        if (missing_pad)
            pad = {};
        return native.schedule(job, at, c);
    }
    wtp::PadObservation pad_observation() const override {
        return pad;
    }
    bool begin(const wtp::Job&, std::uint64_t) override {
        return false;
    }
    wtp::EngineReport poll(std::uint64_t at) override {
        return native.poll(at);
    }
    bool disable(std::uint64_t at) override {
        ++disables;
        return !fail_disable && native.disable(at);
    }
    bool output_active() const override {
        return false;
    }
};
struct Fixture {
    network_test::Flash flash;
    standalone::Store store{flash};
    network_test::Clock clock;
    Engine raw{clock};
    standalone::FrequencyPolicyEngine policy;
    network_test::Identity identity;
    wtp::JobService service;
    standalone::Scheduler scheduler;
    network_test::Network network;
    network::BrowserApi api;
    static wtp::ServiceConfig limits() {
        wtp::ServiceConfig c;
        c.capability_engine = "pio-dma-gp2";
        c.minimum_frequency_nhz = rf::minimum_frequency_nhz;
        c.maximum_frequency_nhz = rf::maximum_frequency_nhz;
        c.max_job_duration_ns = rf::max_duration_ns;
        return c;
    }
    standalone::Store& initialize(unsigned drive, bool absent_station) {
        REQUIRE(store.load());
        auto config = *standalone::parse_config(network_test::config);
        config.gpio_drive_ma = drive;
        if (absent_station) {
            config.callsign.clear();
            config.locator.clear();
        }
        REQUIRE(store.save(config));
        raw.drive = drive;
        return store;
    }
    explicit Fixture(unsigned drive = 12, bool absent_station = false)
        : policy(raw, initialize(drive, absent_station), rf::minimum_frequency_nhz,
                 rf::maximum_frequency_nhz),
          service(clock, policy, identity, limits()), scheduler(store, service),
          api(service, store, scheduler, network, std::string(32, 'a'), "test") {
        api.test_tone_policy(policy);
    }
    std::string target() {
        return application::target(std::string(32, 'a'), service.status(false).boot_id);
    }
    std::string review_body(std::string carrier = "5366200", std::string duration = "1000",
                            std::string drive = "12") {
        return "{\"contract\":\"Wsprry-Control/1\",\"schema\":\"test-tone-review\",\"target\":" +
               target() + ",\"tone\":{\"engine\":\"pio-dma-gp2\",\"carrier_hz\":" + carrier +
               ",\"duration_ms\":" + duration + ",\"proposed_drive_ma\":" + drive + "}}";
    }
    std::string start_body(std::string id = std::string(32, '1'), std::string duration = "1000",
                           unsigned drive = 12) {
        auto body = review_body("5366200", duration, std::to_string(drive));
        body.replace(body.find("test-tone-review"), 16, "test-tone-start");
        body.replace(body.find("proposed_drive_ma"), 17, "expected_drive_ma");
        body.insert(body.find("\"tone\""), "\"request_id\":\"" + id + "\",");
        return body;
    }
    network::HttpRequest request(std::string method, std::string path, std::string body = {},
                                 std::string match = {}) {
        return {std::move(method),
                std::move(path),
                std::move(body),
                {{"host", "127.0.0.1:8443"},
                 {"origin", "https://127.0.0.1:8443"},
                 {"content-type", "application/json"},
                 {"x-wsprrypico-request", "1"},
                 {"if-match", std::move(match)}}};
    }
    network::HttpResponse send(network::HttpRequest r, std::string principal = "cert") {
        return api.handle(r, principal, "127.0.0.1:8443");
    }
    network::HttpResponse review(std::string body = {}) {
        return send(request("POST", "/api/control/v1/test-tone/review",
                            body.empty() ? review_body() : body));
    }
    network::HttpResponse start(std::string body = {}, std::string revision = {}) {
        return send(request("POST", "/api/control/v1/test-tone/start",
                            body.empty() ? start_body() : body,
                            revision.empty() ? api.revision() : revision));
    }
    std::string selector(std::string id, bool job = false) {
        return "/api/control/v1/test-tone/status?device_id=" + std::string(32, 'a') +
               "&boot_id=" + service.status(false).boot_id + (job ? "&job_id=" : "&request_id=") +
               id;
    }
    network::HttpResponse status(std::string id = std::string(32, '1'), bool job = false,
                                 std::string principal = "cert") {
        return send(request("GET", selector(id, job)), principal);
    }
    network::HttpResponse stop(std::string job, std::string revision,
                               std::string principal = "cert") {
        return send(
            request("POST", "/api/control/v1/test-tone/stop",
                    "{\"contract\":\"Wsprry-Control/1\",\"schema\":\"test-tone-stop\",\"target\":" +
                        target() + ",\"job_id\":\"" + job + "\"}",
                    revision),
            principal);
    }
    void background(std::uint64_t at) {
        clock.now = at;
        service.poll();
        api.poll_test_tone();
    }
};
std::string field(const network::HttpResponse& r, std::string_view name) {
    const auto text = r.body_text();
    const auto value = wtp::json::parse(text);
    REQUIRE(value);
    return value->get("job")->get(name)->string();
}
std::uint64_t timing(const network::HttpResponse& r, std::string_view name) {
    std::uint64_t n;
    const auto text = r.body_text();
    const auto value = wtp::json::parse(text);
    REQUIRE(value);
    REQUIRE(wtp::json::decimal(*value->get("job")->get(name), n));
    return n;
}
void station_free_reviews() {
    Fixture f(12, true);
    const auto before = f.flash.bytes;
    for (unsigned drive : {2, 4, 8, 12})
        for (unsigned carrier : {137500, 475700, 1900000, 3600000, 5366200, 7100000, 10120000,
                                 14100000, 18100000, 21100000, 24920000, 28100000, 50100000}) {
            auto r =
                f.review(f.review_body(std::to_string(carrier), "12000", std::to_string(drive)));
            REQUIRE(r.status == 200);
            REQUIRE(r.body_text().find(drive == 12 ? "\"admission\":\"ready\""
                                                   : "\"admission\":\"requires_restart\"") !=
                    std::string::npos);
        }
    REQUIRE(before == f.flash.bytes && !f.raw.prepares && !f.raw.schedules);
}
void lifecycle() {
    for (bool absent_station : {false, true})
        for (unsigned drive : {2, 4, 8, 12}) {
            Fixture f(drive, absent_station);
            const auto before = f.flash.bytes;
            const auto revision = f.api.revision();
            const auto review = f.review(f.review_body("5366200", "120000", std::to_string(drive)));
            REQUIRE(review.status == 200 &&
                    review.body_text().find("\"admission\":\"ready\"") != std::string::npos);
            REQUIRE(f.raw.prepares == 0 && f.raw.schedules == 0 && f.flash.bytes == before);
            const auto body = f.start_body(std::string(32, '1'), "120000", drive);
            const auto accepted = f.start(body, revision);
            REQUIRE(accepted.status == 202);
            const auto job = field(accepted, "job_id"), control = accepted.etag;
            REQUIRE(field(accepted, "phase") == "accepted");
            REQUIRE(accepted.body_text().find("\"drive_ma\":" + std::to_string(drive)) !=
                    std::string::npos);
            REQUIRE(f.api.revision() != revision);
            // Lost Start reply: same retained request, same original binding; no new native work.
            REQUIRE(f.start(body, revision).status == 202 && f.raw.schedules == 1);
            auto conflict = body;
            conflict.replace(conflict.find("120000"), 6, "119999");
            REQUIRE(f.start(conflict, revision).body_text().find("request_conflict") !=
                    std::string::npos);
            const auto at = timing(accepted, "scheduled_monotonic_ns");
            f.background(at + 1'000'000);
            REQUIRE(field(f.status(), "phase") == "running");
            // No client traffic across lease expiry: native ownership remains exclusive.
            f.background(at + 90'000'000'000ULL);
            REQUIRE(f.service.activity().owned);
            REQUIRE(f.start(f.start_body(std::string(32, '2'), "1000", drive)).status == 409);
            f.background(at + 120'001'000'000ULL);
            REQUIRE(!f.service.activity().owned);
            const auto ended = f.status();
            REQUIRE(field(ended, "outcome") == "completed");
            REQUIRE(ended.body_text().find("\"output_inactive_confirmed\":true") !=
                    std::string::npos);
            const auto calls = f.raw.disables;
            REQUIRE(f.stop(job, control).status == 200 && f.raw.disables == calls);
            REQUIRE(f.flash.bytes == before);
        }
}
void stops_and_replay() {
    Fixture f;
    auto first = f.start();
    REQUIRE(first.status == 202);
    const auto job = field(first, "job_id");
    const auto revision = first.etag;
    const auto forged = f.stop(job, revision, "other");
    REQUIRE(forged.status == 403);
    REQUIRE(f.stop(job, "\"stale\"").status == 412);
    REQUIRE(f.stop(job, revision).status == 200);
    REQUIRE(field(f.status(), "outcome") == "stopped");
    auto second = f.start(f.start_body(std::string(32, '2')));
    REQUIRE(second.status == 202);
    const auto calls = f.raw.disables;
    REQUIRE(f.stop(job, revision).status == 200 && f.raw.disables == calls);
    REQUIRE(f.service.status().job_id == field(second, "job_id"));
    auto running_at = timing(second, "scheduled_monotonic_ns");
    f.background(running_at + 1);
    REQUIRE(f.stop(field(second, "job_id"), second.etag).status == 200);
    // Capacity and age eviction never restore the original admission revision.
    const auto old_match = f.api.revision();
    const auto old_request = f.start_body(std::string(32, '3'));
    auto old = f.start(old_request, old_match);
    REQUIRE(old.status == 202);
    REQUIRE(f.stop(field(old, "job_id"), old.etag).status == 200);
    for (unsigned i = 4; i < 15; ++i) {
        std::string id(32, '0');
        id.back() = "0123456789abcdef"[i];
        auto accepted = f.start(f.start_body(id));
        REQUIRE(accepted.status == 202);
        REQUIRE(f.stop(field(accepted, "job_id"), accepted.etag).status == 200);
    }
    REQUIRE(f.status(std::string(32, '3')).status == 404);
    REQUIRE(f.start(old_request, old_match).status == 412);
    f.background(f.clock.now + application::TestTone::retention_ns + 1);
    REQUIRE(f.status(std::string(31, '0') + 'e').status == 404);
}
void shutdown_and_pad_failures() {
    Fixture f;
    auto accepted = f.start();
    REQUIRE(accepted.status == 202);
    f.raw.fail_disable = true;
    auto stopped = f.stop(field(accepted, "job_id"), accepted.etag);
    REQUIRE(stopped.status == 200);
    REQUIRE(stopped.body_text().find("\"recovery_required\":true") != std::string::npos);
    REQUIRE(stopped.body_text().find("\"output_inactive_confirmed\":false") != std::string::npos);
    f.background(f.clock.now + application::TestTone::retention_ns * 2);
    REQUIRE(f.start(f.start_body(std::string(32, '2'))).status == 409);
    REQUIRE(f.status().status == 200); // unresolved receipt pinned, native fault persists
    for (bool missing : {false, true}) {
        Fixture p;
        p.raw.bad_pad = !missing;
        p.raw.missing_pad = missing;
        auto rejected = p.start();
        REQUIRE(rejected.status == 202);
        REQUIRE(field(rejected, "outcome") == "failed");
        REQUIRE(p.service.activity().state == wtp::State::Failed &&
                !p.service.activity().output_active);
    }
    Fixture prep;
    prep.raw.fail_prepare = true;
    REQUIRE(field(prep.start(), "outcome") == "failed");
    REQUIRE(!prep.service.activity().owned);
    prep.raw.fail_prepare = false;
    REQUIRE(prep.start(prep.start_body(std::string(32, '2'))).status == 202);
}
void restart_and_stale_evidence() {
    Fixture f;
    auto first = f.start();
    REQUIRE(first.status == 202);
    REQUIRE(f.stop(field(first, "job_id"), first.etag).status == 200);
    f.raw.stale_pad = true;
    const auto rejected = f.start(f.start_body(std::string(32, '2')));
    REQUIRE(field(rejected, "outcome") == "failed");
    const auto text = rejected.body_text();
    REQUIRE(wtp::json::parse(text)->get("job")->get("pad_readback")->get("drive_ma")->raw ==
            "null");
    REQUIRE(f.status().body_text().find("\"stage\":\"verified\"") != std::string::npos);
    REQUIRE(f.service.activity().state == wtp::State::Failed);
    const auto old_boot = f.service.status(false).boot_id;
    f.service.reset();
    f.api.poll_test_tone();
    REQUIRE(f.service.status(false).boot_id != old_boot && f.status().status == 404);

    Fixture drive;
    auto config = *drive.store.config();
    config.gpio_drive_ma = 4;
    REQUIRE(drive.scheduler.command("CONFIG " + standalone::serialize_config(config))
                .find("\"ok\":true") != std::string::npos);
    config.gpio_drive_ma = 12;
    REQUIRE(drive.scheduler.command("CONFIG " + standalone::serialize_config(config))
                .find("\"ok\":true") != std::string::npos);
    const auto bytes = drive.flash.bytes;
    const auto prepares = drive.raw.prepares;
    REQUIRE(drive.review(drive.review_body("5366200", "1000", "4"))
                .body_text()
                .find("requires_restart") != std::string::npos);
    REQUIRE(drive.start().status == 409 && drive.flash.bytes == bytes &&
            drive.raw.prepares == prepares);
    config.pins.rf = 3;
    REQUIRE(drive.scheduler.command("CONFIG " + standalone::serialize_config(config))
                .find("\"ok\":true") != std::string::npos);
    REQUIRE(drive.review().body_text().find("other_hardware_pending_restart") != std::string::npos);

    Fixture missed;
    const auto accepted = missed.start();
    missed.clock.uncertainty = 2'000'000;
    missed.background(timing(accepted, "scheduled_monotonic_ns") + 1);
    REQUIRE(field(missed.status(), "outcome") == "missed" && missed.raw.schedules == 1);
}

void maintenance_reconciliation() {
    Fixture f;
    const auto revision = f.api.revision(), body = f.start_body();
    const auto accepted = f.start(body, revision);
    REQUIRE(accepted.status == 202);
    REQUIRE(f.stop(field(accepted, "job_id"), accepted.etag).status == 200);
    REQUIRE(f.service.begin_maintenance());
    REQUIRE(f.start(body, revision).status == 202); // retained replay has no native effect
    REQUIRE(f.stop(field(accepted, "job_id"), accepted.etag).status == 200);
    REQUIRE(f.start(f.start_body(std::string(32, '2'))).status == 409);
    REQUIRE(f.raw.schedules == 1);
    f.service.end_maintenance();
}

void validation() {
    Fixture f;
    for (const auto& path :
         {f.selector(std::string(32, '1')), std::string("/api/control/v1/status?x=1"),
          f.selector(std::string(32, '1')) + "&job_id=" + std::string(32, '2')}) {
        network::HttpParser parser;
        const auto wire = "GET " + path + " HTTP/1.1\r\nHost: 127.0.0.1:8443\r\n\r\n";
        (void)parser.receive({reinterpret_cast<const std::uint8_t*>(wire.data()), wire.size()});
        REQUIRE(parser.ready() == network::test_tone_query(path).has_value());
        REQUIRE(parser.failed() != parser.ready());
    }
    const auto before = f.flash.bytes;
    auto rejected =
        f.send(f.request("POST", "/api/control/v1/test-tone/review", f.review_body()), "");
    REQUIRE(rejected.status == 401);
    for (const auto token :
         {"0", "120001", "1.5", "-1", "true", "\"1000\"", "1e3", "18446744073709551616"}) {
        auto body = f.start_body();
        body.replace(body.find("\"duration_ms\":1000"), 18,
                     "\"duration_ms\":" + std::string(token));
        REQUIRE(f.start(body).status >= 400);
    }
    for (const auto change : {"extra", "duplicate", "wrong_target", "wrong_contract"}) {
        auto body = f.start_body();
        if (std::string_view(change) == "extra")
            body.insert(body.size() - 1, ",\"events\":[]");
        if (std::string_view(change) == "duplicate")
            body.insert(body.size() - 1, ",\"request_id\":\"" + std::string(32, '1') + "\"");
        if (std::string_view(change) == "wrong_target")
            body.replace(body.find(std::string(32, 'a')), 32, std::string(32, 'b'));
        if (std::string_view(change) == "wrong_contract")
            body.replace(body.find("Control/1"), 9, "Control/2");
        REQUIRE(f.start(body).status >= 400);
    }
    for (const auto suffix : {"&job_id=00000000000000000000000000000000", "&x=1", "&", "%00"})
        REQUIRE(!network::test_tone_query(f.selector(std::string(32, '1')) + suffix));
    REQUIRE(f.raw.prepares == 0 && f.flash.bytes == before);
    auto config = *f.store.config();
    config.enabled = true;
    REQUIRE(f.store.save(config));
    REQUIRE(f.start().body_text().find("native_schedules_enabled") != std::string::npos);
    config.enabled = false;
    REQUIRE(f.store.save(config));
    f.clock.uncertainty = 1'000'001;
    REQUIRE(f.review().body_text().find("CLOCK_UNCERTAIN") != std::string::npos);
    REQUIRE(f.start().status == 409);
}
void usb_framing_reconnect() {
    Fixture f;
    network::LocalUsbApi api(f.api);
    const auto target = f.target();
    auto open = [&](std::string session, std::string path, std::string method, std::string body,
                    std::string revision, bool acknowledge) {
        usb::ManagementEndpoint endpoint(
            std::string(32, 'a'), f.service.status(false).boot_id, "test",
            [&](const network::HttpRequest& request, std::uint64_t tx) {
                return api.handle(request, tx);
            },
            [&](std::uint64_t tx, bool delivered) { api.finish(tx, delivered); });
        endpoint.connect(session);
        const auto exchange = [&](std::string text) {
            std::string wire = "UMP1";
            for (int shift : {24, 16, 8, 0})
                wire.push_back(char(text.size() >> shift));
            wire += text;
            for (unsigned char c : wire)
                REQUIRE(endpoint.receive({&c, 1}, 1) == 1);
            for (unsigned i = 0; endpoint.output().empty() && i < 100; ++i)
                endpoint.poll(1);
            REQUIRE(!endpoint.closed() && !endpoint.output().empty());
            std::string result;
            while (!endpoint.output().empty()) {
                auto bytes = endpoint.output();
                auto n = std::min<std::size_t>(7, bytes.size());
                result.append(reinterpret_cast<const char*>(bytes.data()), n);
                endpoint.consume_output(n);
            }
            REQUIRE(result.starts_with("UMP1"));
            return result.substr(8);
        };
        (void)exchange(R"({"schema":"usb-management/1","id":1,"operation":"hello"})");
        const auto common =
            "{\"schema\":\"usb-management/1\",\"id\":2,\"session\":" + wtp::json::quote(session) +
            ",\"target\":" + target;
        const auto result =
            exchange(common + ",\"operation\":\"request\",\"method\":" + wtp::json::quote(method) +
                     ",\"path\":" + wtp::json::quote(path) + ",\"body\":" + wtp::json::quote(body) +
                     ",\"if_match\":" + wtp::json::quote(revision) + "}");
        if (acknowledge)
            (void)exchange(common + ",\"operation\":\"ack\"}");
        return result;
    };
    const auto lost = open(std::string(32, 'b'), "/api/control/v1/test-tone/start", "POST",
                           f.start_body(), f.api.revision(), false);
    REQUIRE(wtp::json::parse(lost)->get("status")->integer() == 202 && f.raw.schedules == 1);
    const auto read =
        open(std::string(32, 'c'), f.selector(std::string(32, '1')), "GET", "", "", true);
    REQUIRE(wtp::json::parse(read)->get("status")->integer() == 200 && f.raw.schedules == 1);
    const auto logical = wtp::json::parse(read)->get("body")->string();
    REQUIRE(wtp::json::parse(logical)->get("job")->get("request_id")->string() ==
            std::string(32, '1'));
}

void carriers_and_documents(const char* output) {
    Fixture f;
    network::LocalUsbApi usb(f.api);
    auto accepted = usb.handle(
        f.request("POST", "/api/control/v1/test-tone/start", f.start_body(), f.api.revision()));
    REQUIRE(accepted.status == 202);
    // Carrier scopes remain separate; an HTTPS principal cannot take USB work.
    REQUIRE(f.status().status == 403);
    const auto read = usb.handle(f.request("GET", f.selector(std::string(32, '1'))));
    REQUIRE(read.status == 200);
    const auto stopped = usb.handle(
        f.request("POST", "/api/control/v1/test-tone/stop",
                  "{\"contract\":\"Wsprry-Control/1\",\"schema\":\"test-tone-stop\",\"target\":" +
                      f.target() + ",\"job_id\":\"" + field(accepted, "job_id") + "\"}",
                  accepted.etag));
    REQUIRE(stopped.status == 200);
    if (output) {
        std::ofstream stream(output);
        const auto caps = f.send(f.request("GET", "/api/control/v1/capabilities"));
        stream << '[' << caps.body_text() << ',' << f.review().body_text() << ','
               << accepted.body_text() << ',' << read.body_text() << ',' << stopped.body_text();
        for (const auto& document : synthesis_tone_test::exercise())
            stream << ',' << document;
        stream << ']';
    }
}
} // namespace
int main(int argc, char** argv) {
    station_free_reviews();
    lifecycle();
    stops_and_replay();
    shutdown_and_pad_failures();
    restart_and_stale_evidence();
    maintenance_reconciliation();
    validation();
    usb_framing_reconnect();
    if (argc <= 1)
        (void)synthesis_tone_test::exercise();
    carriers_and_documents(argc > 1 ? argv[1] : nullptr);
    std::cout << "PASS Test Tone API: drives, native expiry, lost replies, exact Stop, faults, "
                 "schemas, USB scope\n";
}

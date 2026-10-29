#include "application/config_update.hpp"
#include "network_support.hpp"

#include <iterator>

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
    standalone::Store& initialize() {
        auto c = *standalone::parse_config(network_test::config);
        c.pins.rf = 28;
        c.allow_unqualified_frequency = c.allow_non_amateur_frequency = true;
        c.expires_utc_s = 1'900'000'000;
        REQUIRE(f.store.save(c));
        REQUIRE(f.store.reserve(1'800'000'000'000'000'000ULL));
        return f.store;
    }
    standalone::Scheduler scheduler{initialize(), f.service};
    network::BrowserApi api{f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test"};
    network::HttpResponse call(network::HttpRequest r) {
        return api.handle(r, "test", "127.0.0.1:8443");
    }
    network::HttpRequest legacy(std::string body = network_test::config) {
        auto r = request("PUT", "/api/v1/config", std::move(body));
        r.headers["if-match"] = api.revision();
        return r;
    }
    network::HttpRequest update(std::string body, std::string mode = "merge") {
        auto r = request("POST", "/api/v1/config/update",
                         "{\"schema\":\"transmitter-config-update/1\",\"target\":" +
                             application::target(std::string(32, 'a'), f.service.status().boot_id) +
                             ",\"mode\":" + wtp::json::quote(mode) + ",\"config\":" + body + '}');
        r.headers["if-match"] = api.revision();
        return r;
    }
};
void advertised_contract_and_individual_omissions() {
    Member m;
    const auto response = m.call(request("GET", "/api/v1/capabilities"));
    REQUIRE(response.status == 200 && response.body.size() <= application::max_capabilities_bytes);
    const auto capabilities = wtp::json::parse(response.body);
    REQUIRE(capabilities);
    const auto updates = capabilities->get("configuration_updates");
    REQUIRE(updates && updates->raw == application::config_update_capabilities());
    REQUIRE(updates->get("schema")->string() == application::config_update_schema);
    REQUIRE(updates->get("method")->string() == "POST");
    REQUIRE(updates->get("path")->string() == "/api/v1/config/update");
    REQUIRE(updates->get("max_update_bytes")->raw == "2048");
    REQUIRE(updates->get("max_config_bytes")->raw == "1800");
    REQUIRE(updates->get("modes")->raw == "[\"merge\",\"replace\"]");
    REQUIRE(updates->get("legacy_put_omission")->string() == "preserve_optional");
    const auto before = *m.f.store.config();
    const auto serialized = standalone::serialize_config(before);
    for (const auto name : {"pins", "allow_unqualified_frequency", "allow_non_amateur_frequency",
                            "expires_utc_s", "ntp_ipv4"}) {
        auto body = serialized;
        const auto parsed = wtp::json::parse(body);
        const auto object = name == std::string_view("ntp_ipv4") ? *parsed->get("wifi") : *parsed;
        const auto value = object.get(name);
        REQUIRE(value);
        // Canonical optionals follow another member, so remove the preceding comma too.
        const auto start = value->raw.offset() - std::string_view(name).size() - 4;
        REQUIRE(body[start] == ',');
        body.erase(start, value->raw.offset() + value->raw.size() - start);
        REQUIRE(m.call(m.legacy(body)).status == 200);
        standalone::Store reload(m.f.flash);
        REQUIRE(reload.load() && reload.config() == before);
    }
    auto replacement = serialized;
    const auto password = wtp::json::parse(replacement)->get("wifi")->get("password")->raw;
    replacement.replace(password.offset(), password.size(), "null");
    REQUIRE(m.call(m.update(replacement, "replace")).status == 200);
    REQUIRE(m.f.store.config() == before);
}
void preserved_legacy_and_defaults() {
    Member m;
    const auto before = *m.f.store.config();
    const auto cursor = m.f.store.watermark();
    REQUIRE(m.scheduler.command("STOP").find("\"suspended\":true") != std::string::npos);
    auto old = m.legacy();
    const auto original_revision = old.headers["if-match"];
    REQUIRE(m.call(old).status == 200);
    REQUIRE(m.f.store.config() == before && m.api.revision() != original_revision);
    REQUIRE(m.call(old).status == 412);
    REQUIRE(m.f.store.watermark() == cursor);
    REQUIRE(m.scheduler.status().find("\"suspended\":true") != std::string::npos);
    REQUIRE(!m.scheduler.hardware_restart_required());
    // Older optional time-server/expiry omission is preservation at the API only.
    auto raw = network_test::config;
    const auto time = raw.find(",\"ntp_ipv4\"");
    raw.erase(time, raw.find('}', time) - time);
    REQUIRE(m.call(m.legacy(raw)).status == 200);
    REQUIRE(m.f.store.config() == before);
    const auto decoded = standalone::parse_config(raw);
    REQUIRE(decoded && decoded->pins == hardware::PinPlan{} &&
            !decoded->allow_unqualified_frequency && !decoded->allow_non_amateur_frequency &&
            decoded->expires_utc_s == 0 && decoded->ntp_ipv4 == standalone::default_time_server);
    network_test::Fixture blank;
    auto initial = request("PUT", "/api/v1/config", raw);
    initial.headers["if-match"] = blank.api.revision();
    REQUIRE(blank.api.handle(initial, "test", "127.0.0.1:8443").status == 200);
    REQUIRE(blank.store.config() == decoded);
    // Console CONFIG remains an explicit complete replacement.
    REQUIRE(m.scheduler.command("CONFIG " + raw).find("\"ok\":true") != std::string::npos);
    REQUIRE(m.f.store.config() == decoded && m.f.store.watermark() == cursor);
}
void merges_and_explicit_resets() {
    Member m;
    auto expected = *m.f.store.config();
    REQUIRE(m.call(m.update(R"({"station":{"callsign":"K1ABC"}})")).status == 200);
    expected.callsign = "K1ABC";
    REQUIRE(m.f.store.config() == expected);
    REQUIRE(m.call(m.update(R"({"wifi":{"ntp_ipv4":"pool.ntp.org","password":null}})")).status ==
            200);
    expected.ntp_ipv4 = "pool.ntp.org";
    REQUIRE(m.f.store.config() == expected && m.scheduler.reboot_required());
    REQUIRE(
        m
            .call(m.update(
                R"({"allow_unqualified_frequency":false,"allow_non_amateur_frequency":false,"expires_utc_s":0,"schedules":[]})"))
            .status == 200);
    expected.allow_unqualified_frequency = expected.allow_non_amateur_frequency = false;
    expected.expires_utc_s = 0;
    expected.schedules.clear();
    REQUIRE(m.f.store.config() == expected);
    REQUIRE(m.call(m.update("{\"pins\":" + hardware::serialize_plan({}) + '}')).status == 200);
    expected.pins = {};
    REQUIRE(m.f.store.config() == expected && m.scheduler.hardware_restart_required());
    REQUIRE(m.f.service.output_inhibited());
    REQUIRE(m.call(m.update(R"({"station":{"power_dbm":10}})")).status == 200);
    REQUIRE(m.scheduler.hardware_restart_required() && m.f.service.output_inhibited());
    expected.power_dbm = 10;
    standalone::Store reload(m.f.flash);
    REQUIRE(reload.load() && reload.config() == expected &&
            reload.watermark() == m.f.store.watermark());

    Member replacement;
    REQUIRE(replacement.call(replacement.update(network_test::config, "replace")).status == 200);
    const auto defaults = standalone::parse_config(network_test::config);
    REQUIRE(replacement.f.store.config() == defaults);
    REQUIRE(replacement.scheduler.hardware_restart_required());
    Member explicit_legacy;
    REQUIRE(explicit_legacy
                .call(explicit_legacy.legacy(
                    network_test::config.substr(0, network_test::config.size() - 1) +
                    ",\"pins\":" + hardware::serialize_plan({}) +
                    ",\"allow_unqualified_frequency\":false,\"allow_non_amateur_frequency\":false,"
                    "\"expires_utc_s\":0}"))
                .status == 200);
    REQUIRE(explicit_legacy.f.store.config() == defaults);
}
void invalid_is_atomic() {
    Member m;
    const auto original = m.f.flash.bytes;
    const auto revision = m.api.revision();
    const auto reject = [&](network::HttpRequest r, unsigned status) {
        const auto response = m.call(std::move(r));
        if (response.status != status)
            std::cerr << "Expected HTTP " << status << ", got " << response.status << ": "
                      << response.body << '\n';
        REQUIRE(response.status == status);
        REQUIRE(response.body.find("test-password") == std::string::npos);
        REQUIRE(m.f.flash.bytes == original && m.api.revision() == revision);
    };
    for (const auto body :
         {"{}", "null", "[]", R"({"unknown":1})", R"({"station":{}})", R"({"wifi":{}})",
          R"({"station":{"extra":true}})", R"({"wifi":{"ssid":null}})",
          R"({"wifi":{"password":false}})", R"({"pins":null})",
          R"({"allow_unqualified_frequency":null})", R"({"enabled":true,"schedules":[]})",
          R"({"station":{"power_dbm":11}})",
          R"({"schedules":[{"period_s":120,"phase_s":0},{"period_s":120,"phase_s":0}]})",
          R"({"enabled":false,"enabled":true})", R"({"enabled":false,"enabl\u0065d":true})",
          R"({"station":{"callsign":"K1ABC","callsign":"W1AW"}})"})
        reject(m.update(body), 400);
    reject(m.update("{}", "replace"), 400);
    reject(m.update(R"({"enabled":false})", "patch"), 400);
    auto r = m.update(R"({"enabled":false})");
    r.body.insert(r.body.size() - 1, ",\"other\":1");
    reject(r, 400);
    r = m.update(R"({"enabled":false})");
    r.body.replace(r.body.find("transmitter-config-update/1"), 27, "transmitter-config-update/2");
    reject(r, 400);
    for (const auto field : {"scope", "device_id", "boot_id"}) {
        r = m.update(R"({"enabled":false})");
        const auto root = wtp::json::parse(r.body);
        const auto raw = root->get("target")->get(field)->raw;
        r.body.replace(raw.offset(), raw.size(), "\"wrong\"");
        reject(r, 409);
    }
    r = m.update(R"({"enabled":false})");
    r.headers.erase("if-match");
    reject(r, 428);
    r.headers["if-match"] = "stale";
    reject(r, 412);
    r = m.update(R"({"enabled":false})");
    r.headers["origin"] = "https://evil.example";
    reject(r, 403);
    r = m.update(R"({"enabled":false})");
    REQUIRE(m.api.handle(r, "", "127.0.0.1:8443").status == 401);
    r.body.resize(application::max_config_update_bytes + 1, ' ');
    reject(r, 413);
    r = m.legacy();
    r.body.resize(standalone::max_config_bytes + 1, ' ');
    reject(r, 400);
    auto too_deep = std::string(40, '[') + "0" + std::string(40, ']');
    reject(m.update("{\"station\":" + too_deep + '}'), 400);
    auto legacy_unknown = m.legacy();
    legacy_unknown.body.insert(legacy_unknown.body.size() - 1, ",\"future\":false");
    reject(legacy_unknown, 400);
    // A small partial request can produce an oversized raw complete candidate.
    std::string host;
    for (unsigned label = 0; label < 4; ++label) {
        if (label)
            host += '.';
        host += std::string(60, 'a');
    }
    REQUIRE(standalone::valid_time_server(host));
    std::string escaped;
    for (char c : host)
        escaped += c == 'a' ? "\\u0061" : ".";
    auto result_too_large = m.update("{\"wifi\":{\"ntp_ipv4\":\"" + escaped + "\"}}");
    REQUIRE(result_too_large.body.size() <= application::max_config_update_bytes);
    reject(result_too_large, 400);
    legacy_unknown = m.legacy();
    const auto wifi = legacy_unknown.body.find("\"ssid\"");
    legacy_unknown.body.insert(wifi, "\"future\":false,");
    reject(legacy_unknown, 400);
    auto exact = m.update(R"({"enabled":false})");
    exact.body.resize(application::max_config_update_bytes, ' ');
    REQUIRE(m.call(exact).status == 200);
}
void revisions_pending_and_storage() {
    Member m;
    auto stale = m.update(R"({"enabled":false})");
    const auto original = *m.f.store.config();
    REQUIRE(m.call(m.update(R"({"station":{"power_dbm":10}})")).status == 200);
    REQUIRE(m.call(m.update(standalone::serialize_config(original), "replace")).status == 200);
    REQUIRE(m.call(stale).status == 412); // A-B-A does not revive A.
    auto same = m.update(R"({"enabled":false})");
    REQUIRE(m.call(same).status == 200 && m.call(same).status == 412);
    auto rebooted = m.update(R"({"enabled":false})");
    m.f.service.reset();
    REQUIRE(m.call(rebooted).status == 412);
    auto queued = request("PUT", "/api/v1/network", "{\"enabled\":false}");
    queued.headers["if-match"] = m.api.revision();
    REQUIRE(m.call(queued).status == 200);
    auto blocked = m.update(R"({"enabled":false})");
    REQUIRE(m.call(blocked).status == 409);
    m.api.finish_request(0, false);
    REQUIRE(m.call(blocked).status == 200);
    auto mutation = m.update(R"({"station":{"power_dbm":10}})");
    const auto saved = m.f.store.config();
    const auto cursor = m.f.store.watermark();
    m.f.flash.fail = true;
    REQUIRE(m.call(mutation).status == 503 && !m.f.store.healthy());
    m.f.flash.fail = false;
    standalone::Store reload(m.f.flash);
    REQUIRE(reload.load() && reload.config() == saved && reload.watermark() == cursor);
    // A lost delivery acknowledgement does not roll back an already committed write.
    Member lost;
    auto applied = lost.update(R"({"station":{"power_dbm":10}})");
    REQUIRE(lost.call(applied).status == 200);
    lost.api.finish_request(0, false);
    REQUIRE(lost.f.store.config()->power_dbm == 10 && lost.call(applied).status == 412);
    network_test::Fixture blank;
    auto new_request = lost.update(R"({"enabled":false})");
    new_request.headers["if-match"] = blank.api.revision();
    REQUIRE(blank.api.handle(new_request, "test", "127.0.0.1:8443").status == 409);
    auto no_password = request(
        "PUT", "/api/v1/config",
        R"({"version":1,"enabled":false,"station":{"callsign":"AA0NT","locator":"EM18","power_dbm":37},"wifi":{"ssid":"test-network","password":null},"schedules":[]})");
    no_password.headers["if-match"] = blank.api.revision();
    REQUIRE(
        blank.api.handle(no_password, "test", "127.0.0.1:8443").body.find("password_required") !=
        std::string::npos);
}
void paged_and_password() {
    Member m;
    auto r = m.update(R"({"wifi":{"password":null}})");
    auto pages = std::make_shared<wtp::FrameBuffer>();
    REQUIRE(pages->reserve(r.body.size() + 600));
    pages->append(wtp::InputView(std::string(600, ' ')));
    pages->append(wtp::InputView(r.body));
    r.selected_body = pages->view().substr(600);
    r.buffered_body = std::move(pages);
    r.body.clear();
    const auto result = m.call(r);
    REQUIRE(result.status == 200 && result.body.size() < 4096);
    REQUIRE(result.body.find("test-password") == std::string::npos);
    REQUIRE(m.f.store.config()->password == "test-password");
    REQUIRE(m.call(m.update(R"({"wifi":{"password":"new-password"}})")).status == 200);
    REQUIRE(m.f.store.config()->password == "new-password");
}
void ownership_and_restart_exclusions() {
    Member m;
    unsigned sequence = 0;
    const auto invoke = [&](std::string operation, wtp::RequestBody body) {
        wtp::Request r;
        r.principal = "usb";
        r.session_id = std::string(32, 'b');
        r.request_id = std::string(31, '0') + std::to_string(++sequence);
        r.operation = std::move(operation);
        r.body = std::move(body);
        r.payload_digest[0] = sequence;
        return m.f.service.handle(std::move(r));
    };
    const auto saved = m.f.flash.bytes;
    REQUIRE(invoke("HELLO", wtp::HelloBody{{"WTP/1"}}).ok);
    REQUIRE(invoke("CLAIM", wtp::ClaimBody{std::string(32, 'b'), 60000}).ok);
    REQUIRE(m.call(m.update(R"({"enabled":false})")).status == 409);
    wtp::Job job{std::string(32, 'c'), "rf-events/1", "tone", 1'000'000'000, {}, false};
    REQUIRE(job.events.push_back({0, job.total_duration_ns, true, 7'040'000'000'000'000ULL}));
    REQUIRE(invoke("LOAD", std::move(job)).ok);
    REQUIRE(m.f.service.status().state == wtp::State::Loaded);
    REQUIRE(m.call(m.update(R"({"enabled":false})")).status == 409);
    REQUIRE(invoke("ARM", wtp::ArmBody{std::string(32, 'c'),
                                       m.f.clock.snapshot().utc_now_ns + 3'000'000'000, 1000})
                .ok);
    REQUIRE(m.call(m.update(R"({"enabled":false})")).status == 409);
    m.f.clock.now += 3'000'000'000;
    m.f.service.poll();
    REQUIRE(m.f.service.status().state == wtp::State::Running);
    REQUIRE(m.call(m.update(R"({"enabled":false})")).status == 409);
    REQUIRE(m.f.flash.bytes == saved);

    Member pending;
    pending.api.restart_control([](void*) { return true; }, nullptr);
    auto restart = request("POST", "/api/v1/restart", "{}");
    restart.headers["if-match"] = pending.api.revision();
    REQUIRE(pending.call(restart).status == 202);
    const auto unchanged = pending.f.flash.bytes;
    REQUIRE(pending.call(pending.update(R"({"enabled":false})")).status == 409);
    REQUIRE(pending.f.flash.bytes == unchanged);
    pending.api.finish_request(0, false);
    REQUIRE(pending.call(pending.update(R"({"enabled":false})")).status == 200);
}
class DisableFailure final : public wtp::RfEngine {
  public:
    bool disable_ok = true, active = false;
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
        return disable_ok;
    }
    bool output_active() const override {
        return active;
    }
};
void application_failure() {
    Member m;
    DisableFailure engine;
    network_test::Identity identity;
    wtp::JobService service(m.f.clock, engine, identity);
    standalone::Scheduler scheduler(m.f.store, service);
    network::BrowserApi api(service, m.f.store, scheduler, m.f.network, std::string(32, 'a'),
                            "test");
    auto r = m.update("{\"pins\":" + hardware::serialize_plan({}) + '}');
    r.headers["if-match"] = api.revision();
    const auto saved = m.f.flash.bytes;
    engine.active = true;
    REQUIRE(api.handle(r, "test", "127.0.0.1:8443").status == 409);
    REQUIRE(m.f.flash.bytes == saved);
    engine.active = false;
    engine.disable_ok = false;
    const auto response = api.handle(r, "test", "127.0.0.1:8443");
    REQUIRE(response.status == 503 &&
            response.body.find("output_disable_failed") != std::string::npos);
    REQUIRE(m.f.store.config()->pins == hardware::PinPlan{} && scheduler.active_pins().rf == 28);
    REQUIRE(scheduler.hardware_application_failed() && scheduler.hardware_restart_required());
    REQUIRE(service.output_inhibited());
    auto after = m.update(R"({"station":{"power_dbm":10}})");
    after.headers["if-match"] = api.revision();
    REQUIRE(api.handle(after, "test", "127.0.0.1:8443").status == 409);
}
struct TornFlash : network_test::Flash {
    int remaining = -1;
    bool program(std::size_t offset, std::span<const std::uint8_t> data) override {
        if (remaining == 0)
            return false;
        if (remaining > 0)
            --remaining;
        return network_test::Flash::program(offset, data);
    }
};
void interrupted_journal() {
    for (int pages = 0; pages <= 8; ++pages) {
        TornFlash flash;
        standalone::Store store(flash);
        REQUIRE(store.load());
        const auto original = *standalone::parse_config(network_test::config);
        REQUIRE(store.save(original) && store.reserve(1'800'000'000'000'000'000ULL));
        const auto cursor_bytes = flash.bytes;
        network_test::Clock clock;
        standalone::DryRunEngine engine;
        network_test::Identity identity;
        wtp::JobService service(clock, engine, identity);
        standalone::Scheduler scheduler(store, service);
        network_test::Network network;
        network::BrowserApi api(service, store, scheduler, network, std::string(32, 'a'), "test");
        Member producer;
        auto mutation = producer.update(R"({"allow_unqualified_frequency":true})");
        mutation.headers["if-match"] = api.revision();
        flash.remaining = pages;
        const auto result = api.handle(mutation, "test", "127.0.0.1:8443");
        REQUIRE(result.status == (pages == 8 ? 200U : 503U));
        REQUIRE(
            std::equal(flash.bytes.begin() + 8192, flash.bytes.end(), cursor_bytes.begin() + 8192));
        standalone::Store rebooted(flash);
        if (pages == 0) {
            REQUIRE(rebooted.load() && rebooted.config() == original);
        } else if (pages < 8) {
            REQUIRE(!rebooted.load() && !rebooted.healthy() && !rebooted.config());
        } else {
            REQUIRE(rebooted.load() && rebooted.config()->allow_unqualified_frequency);
            REQUIRE(rebooted.watermark() == 1'800'000'000'000'000'000ULL);
        }
    }
}
} // namespace
int main(int argc, char** argv) {
    if (argc > 1) {
        Member m;
        if (std::string(argv[1]) == "--pi-context") {
            std::cout << "{\"etag\":" << wtp::json::quote(m.api.revision())
                      << ",\"response\":" << m.call(request("GET", "/api/v1/config")).body << "}\n";
            return 0;
        }
        if (std::string(argv[1]) == "--raw-update") {
            const std::string raw{std::istreambuf_iterator<char>(std::cin), {}};
            auto r = request("POST", "/api/v1/config/update", raw);
            r.headers["if-match"] = m.api.revision();
            const auto result = m.call(r);
            std::cout << "{\"status\":" << result.status << ",\"body\":" << result.body << "}\n";
            return 0;
        }
        if (std::string(argv[1]) == "--request") {
            const std::string raw{std::istreambuf_iterator<char>(std::cin), {}};
            const auto value = wtp::json::parse(raw);
            REQUIRE(value && wtp::json::fields(*value, {"method", "path", "body", "revision"}));
            auto r = request(value->get("method")->string(), value->get("path")->string(),
                             std::string(value->get("body")->raw));
            r.headers["if-match"] = value->get("revision")->type() == '"'
                                        ? value->get("revision")->string()
                                        : m.api.revision();
            const auto before = *m.f.store.config();
            const auto result = m.call(r);
            standalone::Store reload(m.f.flash);
            REQUIRE(reload.load());
            const auto after = *reload.config();
            std::cout << "{\"status\":" << result.status << ",\"body\":" << result.body
                      << ",\"extensions_preserved\":"
                      << (after.pins == before.pins && after.allow_unqualified_frequency &&
                                  after.allow_non_amateur_frequency &&
                                  after.password == before.password &&
                                  reload.watermark() == m.f.store.watermark()
                              ? "true"
                              : "false")
                      << "}\n";
            return 0;
        }
        return 2;
    }
    advertised_contract_and_individual_omissions();
    preserved_legacy_and_defaults();
    merges_and_explicit_resets();
    invalid_is_atomic();
    revisions_pending_and_storage();
    paged_and_password();
    ownership_and_restart_exclusions();
    application_failure();
    interrupted_journal();
    std::cout << "Configuration update and legacy preservation checks passed\n";
}

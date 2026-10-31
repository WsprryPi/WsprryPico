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
        return api.handle(network_test::control_request(r), "test", "127.0.0.1:8443");
    }
    network::HttpRequest complete_update(std::string body = network_test::config) {
        auto r = request("POST", "/api/control/v1/config/update",
            network_test::configuration_update(std::move(body), f.service.status().boot_id));
        r.headers["if-match"] = api.revision(); return r;
    }
    network::HttpRequest update(std::string body, std::string mode = "merge") {
        auto r = request("POST", "/api/control/v1/config/update",
                         "{\"schema\":\"config-update\",\"target\":" +
                             application::target(std::string(32, 'a'), f.service.status().boot_id) +
                             ",\"mode\":" + wtp::json::quote(mode) + ",\"config\":" + body + '}');
        r.headers["if-match"] = api.revision();
        return r;
    }
};
void advertised_contract_and_individual_omissions() {
    Member m;
    const auto response=m.call(request("GET","/api/control/v1/capabilities"));
    REQUIRE(response.status==200 && response.body_size()<=application::max_capabilities_bytes);
    const auto caps=wtp::json::parse(response.body_view());
    REQUIRE(caps && caps->get("contract")->string()=="Wsprry-Control/1");
    const auto updates=caps->get("configuration_updates");
    REQUIRE(updates && updates->raw==application::config_update_capabilities());
    REQUIRE(updates->get("modes")->raw=="[\"merge\"]");
    REQUIRE(updates->get("path")->string()=="/api/control/v1/config/update");
    REQUIRE(!updates->get("legacy_put_omission"));
    const auto before=*m.f.store.config();
    REQUIRE(m.call(m.update(R"({"station":{"power_dbm":10}})")).status==200);
    auto expected=before; expected.power_dbm=10;
    REQUIRE(m.f.store.config()==expected);
    REQUIRE(m.call(m.update(R"({"wifi":{"password":null}})")).status==200);
    REQUIRE(m.f.store.config()==expected);
    standalone::Store reload(m.f.flash);
    REQUIRE(reload.load() && reload.config()==expected);
}
void creation_and_stale_revision() {
    network_test::Fixture f;
    auto create=request("POST","/api/control/v1/config/update",
        network_test::configuration_update(network_test::config,f.service.status().boot_id));
    create.headers["if-match"]=f.api.revision();
    REQUIRE(f.api.handle(network_test::control_request(create),"test","127.0.0.1:8443").status==200);
    REQUIRE(f.store.config() && !f.store.config()->enabled);
    const auto saved=f.flash.bytes;
    REQUIRE(f.api.handle(network_test::control_request(create),"test","127.0.0.1:8443").status==412);
    REQUIRE(f.flash.bytes==saved);
    const auto read=f.api.handle(request("GET","/api/control/v1/config"),"test","127.0.0.1:8443");
    REQUIRE(read.body_text().find("\"version\"")==std::string::npos);
}
void merge_and_replace_refusal() {
    Member m; const auto before=*m.f.store.config();
    REQUIRE(m.call(m.update(R"({"station":{"power_dbm":10}})","replace")).status==400);
    REQUIRE(m.f.store.config()==before);
    REQUIRE(m.call(m.update(R"({"enabled":false,"allow_unqualified_frequency":false,"allow_non_amateur_frequency":false,"expires_utc_s":0})")).status==200);
    auto expected=before;expected.allow_unqualified_frequency=false;expected.allow_non_amateur_frequency=false;expected.expires_utc_s=0;
    REQUIRE(m.f.store.config()==expected);
}
void invalid_is_atomic() {
    Member m;
    const auto original = m.f.flash.bytes;
    const auto revision = m.api.revision();
    const auto reject = [&](network::HttpRequest r, unsigned status) {
        const auto response = m.call(std::move(r));
        if (response.status != status)
            std::cerr << "Expected HTTP " << status << ", got " << response.status << ": "
                      << response.body_text() << '\n';
        REQUIRE(response.status == status);
        REQUIRE(response.body_text().find("test-password") == std::string::npos);
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
    r.body.replace(r.body_text().find("config-update"), 27, "config-update");
    reject(r, 400);
    for (const auto field : {"scope", "device_id", "boot_id"}) {
        r = m.update(R"({"enabled":false})");
        const auto root = wtp::json::parse(r.body_view());
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
    REQUIRE(m.api.handle(network_test::control_request(r), "", "127.0.0.1:8443").status == 401);
    r.body.resize(application::max_config_update_bytes + 1, ' ');
    reject(r, 413);
    auto too_deep = std::string(40, '[') + "0" + std::string(40, ']');
    reject(m.update("{\"station\":" + too_deep + '}'), 400);
    auto legacy_unknown = m.complete_update();
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
    legacy_unknown = m.complete_update();
    const auto wifi = legacy_unknown.body_text().find("\"ssid\"");
    legacy_unknown.body.insert(wifi, "\"future\":false,");
    reject(legacy_unknown, 400);
    auto exact = network_test::control_request(m.update(R"({"enabled":false})"));
    exact.body.resize(application::max_config_update_bytes, ' ');
    REQUIRE(m.call(exact).status == 200);
}
void revisions_pending_and_storage() {
    Member m;
    auto stale = m.update(R"({"enabled":false})");
    const auto original = *m.f.store.config();
    REQUIRE(m.call(m.update(R"({"station":{"power_dbm":10}})")).status == 200);
    REQUIRE(m.call(m.complete_update(standalone::serialize_config(original))).status == 200);
    REQUIRE(m.call(stale).status == 412); // A-B-A does not revive A.
    auto same = m.update(R"({"enabled":false})");
    REQUIRE(m.call(same).status == 200 && m.call(same).status == 412);
    auto rebooted = m.update(R"({"enabled":false})");
    m.f.service.reset();
    REQUIRE(m.call(rebooted).status == 412);
    auto queued = request("PUT", "/api/control/v1/network", "{\"enabled\":false}");
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
    REQUIRE(blank.api.handle(network_test::control_request(new_request), "test", "127.0.0.1:8443").status == 400);
    auto no_password = request(
        "POST", "/api/control/v1/config/update",
        network_test::configuration_update(R"({"enabled":false,"station":{"callsign":"AA0NT","locator":"EM18","power_dbm":37},"wifi":{"ssid":"test-network","password":null},"schedules":[]})"));
    no_password.headers["if-match"] = blank.api.revision();
    REQUIRE(
        blank.api.handle(network_test::control_request(no_password), "test", "127.0.0.1:8443").body_text().find("password_required") !=
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
    REQUIRE(result.status == 200 && result.body_size() < 4096);
    REQUIRE(result.body_text().find("test-password") == std::string::npos);
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
    auto restart = request("POST", "/api/control/v1/restart", "{}");
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
    REQUIRE(api.handle(network_test::control_request(r), "test", "127.0.0.1:8443").status == 409);
    REQUIRE(m.f.flash.bytes == saved);
    engine.active = false;
    engine.disable_ok = false;
    const auto response = api.handle(network_test::control_request(r), "test", "127.0.0.1:8443");
    REQUIRE(response.status == 503 &&
            response.body_text().find("output_disable_failed") != std::string::npos);
    REQUIRE(m.f.store.config()->pins == hardware::PinPlan{} && scheduler.active_pins().rf == 28);
    REQUIRE(scheduler.hardware_application_failed() && scheduler.hardware_restart_required());
    REQUIRE(service.output_inhibited());
    auto after = m.update(R"({"station":{"power_dbm":10}})");
    after.headers["if-match"] = api.revision();
    REQUIRE(api.handle(network_test::control_request(after), "test", "127.0.0.1:8443").status == 409);
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
        const auto result = api.handle(network_test::control_request(mutation), "test", "127.0.0.1:8443");
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
    if (argc==2 && std::string(argv[1])=="--raw-update") {
        Member m;
        const std::string input(std::istreambuf_iterator<char>(std::cin),{});
        auto raw=request("POST","/api/control/v1/config/update",input);
        raw.headers["if-match"]=m.api.revision();
        const auto result=m.api.handle(raw,"test","127.0.0.1:8443");
        std::cout<<"{\"status\":"<<result.status<<",\"body\":"<< result.body_text()<<"}\n";
        return 0;
    }

    advertised_contract_and_individual_omissions();
    creation_and_stale_revision();
    merge_and_replace_refusal();
    invalid_is_atomic();
    revisions_pending_and_storage();
    paged_and_password();
    ownership_and_restart_exclusions();
    application_failure();
    interrupted_journal();
    std::cout << "Current control configuration transaction checks passed\n";
}

#include "application/config_update.hpp"
#include "network_support.hpp"
#include "standalone/wtp_profile.hpp"
#include "time/utc_discipline.hpp"

#include <tuple>

using namespace wsprrypico;
using namespace wtp::json;
namespace {
struct Member {
    network_test::Fixture f;
    standalone::Store& init() {
        REQUIRE(f.store.save(*standalone::parse_config(network_test::config)));
        return f.store;
    }
    standalone::Scheduler scheduler{init(), f.service};
    network::BrowserApi api{f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test"};
    network::HttpResponse call(std::string method, std::string path, std::string body = {}) {
        network::HttpRequest r{method,
                               path,
                               body,
                               {{"host", "127.0.0.1:8443"},
                                {"origin", "https://127.0.0.1:8443"},
                                {"content-type", "application/json"},
                                {"x-wsprrypico-request", "1"},
                                {"if-match", api.revision()}}};
        return api.handle(r, "test", "127.0.0.1:8443");
    }
    network::HttpResponse save(std::string value, bool unlimited = false) {
        return call("PUT", unlimited ? "/api/v1/ntp-timeout/2" : "/api/v1/ntp-timeout",
                    "{\"schema\":\"transmitter-ntp-timeout/" + std::string(unlimited ? "2" : "1") +
                        "\",\"target\":" +
                        application::target(std::string(32, 'a'), f.service.status().boot_id) +
                        ",\"timeout_s\":" + value + "}");
    }
};
void persistence() {
    Member m;
    const auto initial = m.call("GET", "/api/v1/ntp-timeout");
    REQUIRE(initial.status == 200 && !initial.etag.empty());
    REQUIRE(parse(initial.body)->get("saved_timeout_s")->integer() == 3600);
    for (const auto bad :
         {"0", "59", "61", "86401", "-60", "60.0", "6e1", "true", "null", "\"60\""}) {
        const auto seq = m.f.store.config_sequence();
        REQUIRE(m.save(bad).status == 400);
        REQUIRE(m.f.store.config_sequence() == seq);
    }
    for (const auto seconds : {60, 900, 3600, 86400}) {
        REQUIRE(m.save(std::to_string(seconds)).status == 200);
        REQUIRE(m.f.store.config()->ntp_timeout_s == unsigned(seconds));
        const auto view = m.call("GET", "/api/v1/ntp-timeout");
        REQUIRE(parse(view.body)->get("active_timeout_s")->integer() == 3600);
        REQUIRE(parse(view.body)->get("pending_restart")->boolean() == (seconds != 3600));
        for (const auto route :
             {"/api/v1/config", "/api/v1/config/2", "/api/v1/config/3", "/api/v1/config/4"})
            REQUIRE(m.call("GET", route).body.find("ntp_timeout_s") == std::string::npos);
        REQUIRE(m.call("PUT", "/api/v1/config", network_test::config).status == 200);
        REQUIRE(m.f.store.config()->ntp_timeout_s == unsigned(seconds));
        const auto text = standalone::serialize_config(*m.f.store.config());
        REQUIRE(standalone::parse_config(text)->ntp_timeout_s == unsigned(seconds));
        standalone::Store rebooted(m.f.flash);
        REQUIRE(rebooted.load() && rebooted.config()->ntp_timeout_s == unsigned(seconds));
    }
    REQUIRE(m.save("900").status == 200);
    const auto replace = "{\"schema\":\"transmitter-config-update/1\",\"target\":" +
                         application::target(std::string(32, 'a'), m.f.service.status().boot_id) +
                         ",\"mode\":\"replace\",\"config\":" + network_test::config + "}";
    REQUIRE(m.call("POST", "/api/v1/config/update", replace).status == 200);
    REQUIRE(m.f.store.config()->ntp_timeout_s == 900);
    const auto sequence = m.f.store.config_sequence();
    const auto wrong_target =
        "{\"schema\":\"transmitter-ntp-timeout/1\",\"target\":" +
        application::target(std::string(32, 'c'), m.f.service.status().boot_id) +
        ",\"timeout_s\":3600}";
    REQUIRE(m.call("PUT", "/api/v1/ntp-timeout", wrong_target).status == 409);
    REQUIRE(m.f.store.config_sequence() == sequence);
}
void unlimited_persistence() {
    Member m;
    REQUIRE(m.save("0", true).status == 200);
    REQUIRE(m.f.store.config()->ntp_timeout_s == 0);
    REQUIRE(m.call("GET", "/api/v1/ntp-timeout").status == 409);
    const auto view = m.call("GET", "/api/v1/ntp-timeout/2");
    REQUIRE(view.status == 200);
    REQUIRE(parse(view.body)->get("schema")->string() == "transmitter-ntp-timeout/2");
    REQUIRE(parse(view.body)->get("saved_timeout_s")->integer() == 0);
    const auto stored = standalone::serialize_config(*m.f.store.config());
    REQUIRE(parse(stored)->get("version")->integer() == 2);
    REQUIRE(standalone::parse_config(stored)->ntp_timeout_s == 0);
    auto legacy_zero = stored;
    legacy_zero.replace(legacy_zero.find("\"version\":2"), 11, "\"version\":1");
    REQUIRE(!standalone::parse_config(legacy_zero));
    auto invalid_new = stored;
    invalid_new.replace(invalid_new.find("\"ntp_timeout_s\":0"), 17, "\"ntp_timeout_s\":60");
    REQUIRE(!standalone::parse_config(invalid_new));
    const auto sequence = m.f.store.config_sequence();
    REQUIRE(m.save("0").status == 400);
    REQUIRE(m.f.store.config_sequence() == sequence);
    for (const auto bad : {"-60", "59", "61", "86401", "0.0", "0e0", "true", "null", "\"0\""}) {
        REQUIRE(m.save(bad, true).status == 400);
        REQUIRE(m.f.store.config_sequence() == sequence);
    }
    REQUIRE(m.call("GET", "/api/v1/ntp-timeout/3").status == 404);
    for (const auto route :
         {"/api/v1/config", "/api/v1/config/2", "/api/v1/config/3", "/api/v1/config/4"}) {
        REQUIRE(parse(m.call("GET", route).body)->get("config")->get("version")->integer() == 1);
        REQUIRE(m.call("PUT", route, network_test::config).status == 200);
        REQUIRE(m.f.store.config()->ntp_timeout_s == 0);
    }
    for (const auto mode : {"merge", "replace"}) {
        const auto body = "{\"schema\":\"transmitter-config-update/1\",\"target\":" +
                          application::target(std::string(32, 'a'), m.f.service.status().boot_id) +
                          ",\"mode\":\"" + mode + "\",\"config\":" + network_test::config + "}";
        REQUIRE(m.call("POST", "/api/v1/config/update", body).status == 200);
        REQUIRE(m.f.store.config()->ntp_timeout_s == 0);
    }
    standalone::Store rebooted(m.f.flash);
    REQUIRE(rebooted.load() && rebooted.config()->ntp_timeout_s == 0);
    standalone::Scheduler active(rebooted, m.f.service);
    network::BrowserApi api(m.f.service, rebooted, active, m.f.network, std::string(32, 'a'),
                            "test");
    network::HttpRequest read{"GET", "/api/v1/ntp-timeout", {}, {{"host", "127.0.0.1:8443"}}};
    REQUIRE(api.handle(read, "test", "127.0.0.1:8443").status == 409);
    const auto before_refusal = rebooted.config_sequence();
    network::HttpRequest old_write{
        "PUT",
        "/api/v1/ntp-timeout",
        "{\"schema\":\"transmitter-ntp-timeout/1\",\"target\":" +
            application::target(std::string(32, 'a'), m.f.service.status().boot_id) +
            ",\"timeout_s\":60}",
        {{"host", "127.0.0.1:8443"},
         {"origin", "https://127.0.0.1:8443"},
         {"content-type", "application/json"},
         {"x-wsprrypico-request", "1"},
         {"if-match", api.revision()}}};
    REQUIRE(api.handle(old_write, "test", "127.0.0.1:8443").status == 409);
    REQUIRE(rebooted.config_sequence() == before_refusal);

    REQUIRE(m.save("3600", true).status == 200);
    REQUIRE(parse(standalone::serialize_config(*m.f.store.config()))->get("version")->integer() ==
            1);
}

void unlimited_holdover() {
    constexpr auto ns = 1'000'000'000ULL;
    std::uint64_t mono = 0;
    const auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
    time::UtcDiscipline clock(now, &mono, standalone::clock_profile(0));
    REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    REQUIRE(clock.observe(1'792'800'000ULL * ns, 0, 1'000'000, wtp::LeapState::Normal));
    mono = (30ULL * 86'400 + 116) * ns;
    const auto snapshot = clock.snapshot();
    REQUIRE(snapshot.state == wtp::ClockState::Holdover);
    REQUIRE(snapshot.uncertainty_ns > time::standalone_max_uncertainty_ns);
    REQUIRE(snapshot.sync_age_ns == mono);
    network_test::Flash flash;
    standalone::Store store(flash);
    REQUIRE(store.load());
    auto config = *standalone::parse_config(network_test::config);
    config.enabled = true;
    config.ntp_timeout_s = 0;
    config.wspr_dial_frequency_hz = 3'568'600;
    config.schedules = {{120, 0}};
    REQUIRE(store.save(config));
    standalone::DryRunEngine engine;
    network_test::Identity ids;
    wtp::JobService service(clock, engine, ids, standalone::wtp_profile(false, 0));
    standalone::Scheduler scheduler(store, service);
    scheduler.poll();
    REQUIRE(service.status().state == wtp::State::Armed);
    REQUIRE(!service.status().output_active);
    REQUIRE(store.watermark());
    REQUIRE(service.config().maximum_holdover_age_ns == UINT64_MAX);
    REQUIRE(service.config().maximum_arm_uncertainty_ns == UINT64_MAX);
    // Disabling NTP expiry never creates a clock on an unsynchronized boot.
    clock.invalidate();
    REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
}

void holdover() {
    constexpr auto ns = 1'000'000'000ULL;
    for (const unsigned seconds : {60U, 900U, 3600U, 86400U}) {
        std::uint64_t mono = 0;
        const auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
        time::UtcDiscipline clock(now, &mono, standalone::clock_profile(seconds));
        REQUIRE(clock.observe(1'792'800'000ULL * ns, 0, 1'000'000, wtp::LeapState::Normal));
        mono = std::uint64_t{seconds} * ns;
        REQUIRE(clock.snapshot().state != wtp::ClockState::Unsynchronized);
        REQUIRE(standalone::wtp_profile(false, seconds).maximum_holdover_age_ns == mono);
        ++mono;
        REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    }
    std::uint64_t mono = 0;
    const auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
    time::UtcDiscipline clock(now, &mono, standalone::clock_profile());
    REQUIRE(clock.observe(1'792'800'000ULL * ns, 0, 1'000'000, wtp::LeapState::Normal));
    mono = 116 * ns;
    REQUIRE(clock.snapshot().state == wtp::ClockState::Holdover);
    REQUIRE(clock.snapshot().sync_age_ns < standalone::wtp_profile(false).maximum_holdover_age_ns);
    REQUIRE(clock.snapshot().uncertainty_ns < time::standalone_max_uncertainty_ns);
}
void scheduled_holdover() {
    constexpr auto ns = 1'000'000'000ULL;
    for (const auto& [age, uncertainty, admitted] :
         {std::tuple{116ULL, 1'000'000ULL, true}, std::tuple{116ULL, 499'000'000ULL, false},
          std::tuple{3716ULL, 1'000'000ULL, false}}) {
        std::uint64_t mono = 0;
        const auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
        time::UtcDiscipline clock(now, &mono, standalone::clock_profile());
        REQUIRE(clock.observe(1'792'800'000ULL * ns, 0, uncertainty, wtp::LeapState::Normal));
        network_test::Flash flash;
        standalone::Store store(flash);
        REQUIRE(store.load());
        auto config = *standalone::parse_config(network_test::config);
        config.enabled = true;
        config.wspr_dial_frequency_hz = 3'568'600;
        config.schedules = {{120, 0}};
        REQUIRE(store.save(config));
        standalone::DryRunEngine engine;
        network_test::Identity ids;
        wtp::JobService service(clock, engine, ids, standalone::wtp_profile(false));
        standalone::Scheduler scheduler(store, service);
        mono = age * ns;
        scheduler.poll();
        REQUIRE(service.status().state == (admitted ? wtp::State::Armed : wtp::State::Empty));
        REQUIRE(!service.status().output_active);
        REQUIRE(bool(store.watermark()) == admitted);
    }
}
void controller_freshness() {
    std::uint64_t mono = 0;
    const auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
    for (const auto source :
         {time::ObservationSource::Controller, time::ObservationSource::Browser}) {
        mono = 0;
        time::UtcDiscipline clock(now, &mono, standalone::clock_profile(0));
        REQUIRE(clock.observe(source, 1'792'800'000'000'000'000ULL, 0, 1'000'000,
                              wtp::LeapState::Normal, {}, {}));
        mono = 90'000'000'000ULL;
        REQUIRE(clock.snapshot().state != wtp::ClockState::Unsynchronized);
        ++mono;
        REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    }
}
} // namespace
int main(int argc, char**) {
    persistence();
    unlimited_persistence();
    unlimited_holdover();
    holdover();
    scheduled_holdover();
    controller_freshness();
    if (argc > 1) {
        Member m;
        std::cout << m.call("GET", "/api/v1/ntp-timeout").body << '\n';
        REQUIRE(m.save("900").status == 200);
        std::cout << m.call("GET", "/api/v1/ntp-timeout").body << '\n';
        REQUIRE(m.save("0", true).status == 200);
        std::cout << m.call("GET", "/api/v1/ntp-timeout/2").body << '\n';
    }
}

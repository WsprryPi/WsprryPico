#include "application/config_update.hpp"
#include "network_support.hpp"
#include "standalone/progress.hpp"
#include <limits>

using namespace wsprrypico;
using namespace wtp::json;
namespace {
constexpr std::uint64_t ns = 1'000'000'000;
struct Engine : wtp::RfEngine {
    standalone::DryRunEngine dry;
    std::vector<wtp::Job> jobs;
    wtp::PrepareResult prepare(const wtp::Job& job) override {
        jobs.push_back(job);
        return dry.prepare(job);
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const wtp::Job& job, std::uint64_t start,
                  const wtp::LocalStartConditions& conditions) override {
        return dry.schedule(job, start, conditions);
    }
    bool begin(const wtp::Job&, std::uint64_t) override {
        return false;
    }
    wtp::EngineReport poll(std::uint64_t now) override {
        return dry.poll(now);
    }
    bool disable(std::uint64_t deadline) override {
        return dry.disable(deadline);
    }
    bool output_active() const override {
        return dry.output_active();
    }
};
struct Member {
    network_test::Flash flash;
    standalone::Store store{flash};
    network_test::Clock clock;
    Engine engine;
    network_test::Identity identity;
    static wtp::ServiceConfig limits(std::uint64_t maximum) {
        wtp::ServiceConfig result;
        result.minimum_frequency_nhz = 100000 * ns;
        result.maximum_frequency_nhz = maximum;
        return result;
    }
    wtp::JobService service;
    standalone::Scheduler scheduler;
    network_test::Network network;
    network::BrowserApi api;
    standalone::Store& initialize(bool inherited) {
        REQUIRE(store.load());
        auto c = *standalone::parse_config(network_test::config);
        c.enabled = inherited;
        REQUIRE(store.save(c));
        return store;
    }
    explicit Member(bool inherited = false, std::uint64_t maximum = 68999999 * ns)
        : service(clock, engine, identity, limits(maximum)), scheduler(initialize(inherited), service),
          api(service, store, scheduler, network, std::string(32, 'a'), "test") {}
    network::HttpResponse request(std::string method, std::string path, std::string body = {},
                                  std::string match = {}) {
        network::HttpRequest request{method,
                                     path,
                                     body,
                                     {{"host", "127.0.0.1:8443"},
                                      {"origin", "https://127.0.0.1:8443"},
                                      {"content-type", "application/json"},
                                      {"x-wsprrypico-request", "1"},
                                      {"if-match", match.empty() ? api.revision() : match}}};
        return api.handle(network_test::control_request(request), "test", "127.0.0.1:8443");
    }
    std::string envelope(std::string value) {
        return "{\"schema\":\"standalone-frequency\",\"target\":" +
               application::target(std::string(32, 'a'), service.status().boot_id) +
               ",\"frequency_hz\":" + value + "}";
    }
    network::HttpResponse frequency(std::string value) {
        return request("PUT", "/api/control/v1/standalone-frequency", envelope(value));
    }
};
// Independent production guard/persistence coverage; no browser gating involved.
void first_use_requires_explicit_station_application() {
    network_test::Fixture f;
    network_test::Flash drafts;
    standalone::Progress progress(drafts);
    REQUIRE(progress.load());
    f.api.progress_settings(progress);
    auto request = [&](std::string method, std::string path, std::string body = "") {
        return f.api.handle(network_test::control_request({method,
                             path,
                             body,
                             {{"host", "127.0.0.1:8443"},
                              {"origin", "https://127.0.0.1:8443"},
                              {"content-type", "application/json"},
                              {"x-wsprrypico-request", "1"},
                              {"if-match", f.api.revision()}}}),
                            "test", "127.0.0.1:8443");
    };
    const auto target = application::target(std::string(32, 'a'), f.service.status().boot_id);
    const auto frequency =
        "{\"schema\":\"standalone-frequency\",\"target\":" + target +
        ",\"frequency_hz\":14095600}";
    REQUIRE(!f.store.config() && f.store.healthy());
    REQUIRE(request("GET", "/api/control/v1/standalone-frequency").body.find("\"frequency_hz\":null") !=
            std::string::npos);
    REQUIRE(request("PUT", "/api/control/v1/standalone-frequency", frequency).status == 409);
    REQUIRE(f.store.config_sequence() == 0 && !f.store.config());
    const auto draft = request(
        "POST", "/api/control/v1/progress/update",
        "{\"schema\":\"progress\",\"target\":" + target + ",\"request_id\":\"" +
            std::string(32, 'd') +
            "\",\"fields\":{\"callsign\":\"AA0NT\",\"locator\":\"EM18\",\"power_dbm\":37}}");
    REQUIRE(draft.status == 200 &&
            draft.body.find("\"station_complete\":true") != std::string::npos);
    REQUIRE(draft.body.find("\"applied_station\":null") != std::string::npos);
    const auto refused = request("PUT", "/api/control/v1/standalone-frequency", frequency);
    REQUIRE(refused.status == 409 && refused.body.find("not_configured") != std::string::npos);
    REQUIRE(f.store.config_sequence() == 0 && !f.store.config());
    const auto applied =
        request("POST", "/api/control/v1/progress/apply",
                "{\"schema\":\"progress\",\"target\":" + target +
                    ",\"application\":{\"draft_revision\":\"" +
                    std::to_string(progress.sequence()) + "\",\"domain\":\"station\"}}");
    REQUIRE(applied.status == 200 && f.store.config() && !f.store.config()->enabled);
    REQUIRE(f.store.config()->wspr_dial_frequency_hz == 14'095'600);
    REQUIRE(request("PUT", "/api/control/v1/standalone-frequency", frequency).status == 200);
    standalone::Store reboot(f.flash);
    REQUIRE(reboot.load() && reboot.config()->wspr_dial_frequency_hz == 14095600);
    REQUIRE(!reboot.config()->enabled && !f.service.activity().owned && !f.engine.output_active());
}
void identity_atomicity_and_old_journal() {
    Member m;
    REQUIRE(m.frequency("3568737").status == 200);
    const auto first_revision = m.api.revision();
    auto wrong = m.envelope("14095600");
    const auto boot = m.service.status().boot_id;
    wrong.replace(wrong.find(boot), boot.size(), std::string(32,'f'));
    const auto committed = *m.store.config();
    REQUIRE(m.request("PUT", "/api/control/v1/standalone-frequency", wrong).status == 409);
    REQUIRE(*m.store.config() == committed);
    REQUIRE(m.frequency("14095600").status == 200);
    REQUIRE(m.frequency("3568737").status == 200);
    REQUIRE(m.api.revision() != first_revision);
    REQUIRE(m.request("PUT", "/api/control/v1/standalone-frequency",m.envelope("14095600"),first_revision).status == 412);
    // The latest valid-CRC record with an unknown old member fails ordinary
    // strict parsing; the loader must not resurrect a prior enabled record.
    network_test::Flash flash;
    standalone::Store original(flash);
    REQUIRE(original.load());
    auto enabled = committed; enabled.enabled = true;
    REQUIRE(original.save(enabled));
    standalone::Journal journal(flash,0,2048);
    REQUIRE(journal.load());
    auto old = standalone::serialize_config(enabled);
    old.replace(old.find("wspr_dial_frequency_hz"),22,"wspr_base_frequency_hz");
    REQUIRE(journal.append(old));
    standalone::Store reboot(flash);
    REQUIRE(!reboot.load() && !reboot.healthy() && !reboot.config());
    const auto last = *m.store.config();
    const auto sequence = m.store.config_sequence();
    m.flash.fail = true;
    REQUIRE(m.frequency("14095600").status == 503);
    REQUIRE(*m.store.config() == last && m.store.config_sequence() == sequence && !m.store.healthy());
    REQUIRE(!m.service.activity().owned && m.engine.jobs.empty());
    m.flash.fail = false;
    REQUIRE(m.frequency("14095600").status == 409); // Failed service state remains blocked.
    REQUIRE(!m.store.healthy() && !m.service.activity().owned);
    REQUIRE(*m.store.config() == last);
}
void blocked_dial_survives_unrelated_updates() {
    Member m;
    auto config = *m.store.config();
    config.allow_unqualified_frequency = config.allow_non_amateur_frequency = true;
    REQUIRE(m.store.save(config));
    REQUIRE(m.frequency("1000000").status == 200);
    // Explicit false values revoke permissions without erasing the saved dial.
    const auto envelope = "{\"schema\":\"config-update\",\"target\":" +
        application::target(std::string(32,'a'),m.service.status().boot_id) +
        ",\"mode\":\"merge\",\"config\":{\"allow_unqualified_frequency\":false,\"allow_non_amateur_frequency\":false}}";
    REQUIRE(m.request("POST","/api/control/v1/config/update",envelope).status == 200);
    REQUIRE(m.store.config()->wspr_dial_frequency_hz == 1000000);
    REQUIRE(!m.store.config()->allow_unqualified_frequency && !m.store.config()->allow_non_amateur_frequency);
    REQUIRE(m.request("GET","/api/control/v1/standalone-frequency").body.find("\"allowed\":false") != std::string::npos);
    REQUIRE(m.scheduler.command("CONFIG " + network_test::config).find("\"ok\":true") != std::string::npos);
    REQUIRE(m.store.config()->wspr_dial_frequency_hz == 1000000);
    auto changed = *m.store.config(); changed.wspr_dial_frequency_hz = 1000001;
    REQUIRE(m.scheduler.command("CONFIG " + standalone::serialize_config(changed)).find("frequency_not_allowed") != std::string::npos);
    REQUIRE(m.store.config()->wspr_dial_frequency_hz == 1000000);
}
void absolute_jobs_ignore_standalone_dial() {
    Member m;
    unsigned sequence = 0;
    auto send = [&](std::string operation, wtp::RequestBody body = {}) {
        wtp::Request request;
        request.principal = "remote";
        request.session_id = std::string(32,'c');
        ++sequence;
        request.request_id = std::string(30,'0') + (sequence < 10 ? "0" : "") + std::to_string(sequence);
        request.payload_digest[0] = 1;
        request.operation = operation; request.body = std::move(body);
        return m.service.handle(std::move(request));
    };
    for (const auto dial : {"3568737", "14095600"}) {
        REQUIRE(m.frequency(dial).status == 200);
        REQUIRE(send("HELLO",wtp::HelloBody{{"WTP/1"}}).ok);
        REQUIRE(send("CLAIM",wtp::ClaimBody{std::string(32,'c'),30000}).ok);
        wtp::Job job{std::string(32,'d'),"rf-events/1","wspr",ns,{},true};
        REQUIRE(job.events.push_back({0,ns,true,14095600123456789ULL}));
        REQUIRE(send("LOAD",job).ok);
        REQUIRE(m.engine.jobs.back().events[0].frequency_nhz == 14095600123456789ULL);
        REQUIRE(m.frequency("7038600").status == 409);
        REQUIRE(send("RELEASE").ok);
    }
}
void api_engine_boundaries() {
    for (const auto upper : {65999999ULL,68999999ULL,74999999ULL}) {
        Member m(false,upper*ns);
        auto config = *m.store.config();
        config.allow_unqualified_frequency = config.allow_non_amateur_frequency = true;
        REQUIRE(m.store.save(config));
        REQUIRE(m.frequency("98503").status == 200);
        REQUIRE(m.store.config()->wspr_dial_frequency_hz == 98503);
        auto sequence = m.store.config_sequence();
        REQUIRE(m.frequency("98502").status == 400 && m.store.config_sequence() == sequence);
        REQUIRE(m.frequency(std::to_string(upper-1503)).status == 200);
        REQUIRE(m.store.config()->wspr_dial_frequency_hz == upper-1503);
        sequence = m.store.config_sequence();
        REQUIRE(m.frequency(std::to_string(upper-1502)).status == 400 && m.store.config_sequence() == sequence);
    }
}
void arithmetic_bounds_and_policy() {
    const std::array<std::uint64_t, 4> expected{
        14097097802734375ULL, 14097099267578125ULL,
        14097100732421875ULL, 14097102197265625ULL};
    REQUIRE(standalone::wspr_tones(14095600) == expected);
    REQUIRE(!standalone::wspr_tones(0));
    REQUIRE(!standalone::wspr_tones(std::numeric_limits<std::uint64_t>::max()));
    REQUIRE(!standalone::wspr_tones(18446742572ULL));
    standalone::Config c;
    c.allow_unqualified_frequency = c.allow_non_amateur_frequency = true;
    for (const auto upper : {65'999'999ULL, 68'999'999ULL, 74'999'999ULL}) {
        c.wspr_dial_frequency_hz = 98503;
        REQUIRE(standalone::wspr_frequency_allowed(c, 100000 * ns, upper * ns));
        c.wspr_dial_frequency_hz = 98502;
        REQUIRE(!standalone::wspr_frequency_allowed(c, 100000 * ns, upper * ns));
        c.wspr_dial_frequency_hz = upper - 1503;
        REQUIRE(standalone::wspr_frequency_allowed(c, 100000 * ns, upper * ns));
        c.wspr_dial_frequency_hz = upper - 1502;
        REQUIRE(!standalone::wspr_frequency_allowed(c, 100000 * ns, upper * ns));
    }
    c.allow_unqualified_frequency = c.allow_non_amateur_frequency = false;
    // Every emitted tone must be inside policy; D itself is only a reference.
    for (const auto& [dial, accepted] : std::array<std::pair<unsigned,bool>,4>{
             {{128503,true},{128502,false},{188497,true},{188498,false}}}) {
        c.wspr_dial_frequency_hz = dial;
        REQUIRE(standalone::wspr_frequency_allowed(c, 100000 * ns, 68999999 * ns) == accepted);
    }
    c.wspr_dial_frequency_hz = 40500000;
    REQUIRE(!standalone::wspr_frequency_allowed(c, 100000 * ns, 68999999 * ns));
    c.allow_unqualified_frequency = true;
    REQUIRE(standalone::wspr_frequency_allowed(c, 100000 * ns, 68999999 * ns));
    c.wspr_dial_frequency_hz = 1000000;
    REQUIRE(!standalone::wspr_frequency_allowed(c, 100000 * ns, 68999999 * ns));
    c.allow_non_amateur_frequency = true;
    REQUIRE(standalone::wspr_frequency_allowed(c, 100000 * ns, 68999999 * ns));
}
void single_frame_and_closed_views() {
    Member m;
    REQUIRE(m.frequency("3568737").status == 200);
    const auto saved = *m.store.config();
    for (const auto path : {"/api/control/v1/application", "/api/control/v1/application",
                            "/api/control/v1/application", "/api/control/v1/application"}) {
        const auto r = m.request("GET", path);
        REQUIRE(r.status == 200);
        REQUIRE(r.body.find("\"schedule_dial_frequency_nhz\":\"3568737000000000\"") != std::string::npos);
        REQUIRE(r.body.find("schedule_base_frequency_nhz") == std::string::npos);
    }
    for (const auto path : {"/api/control/v1/config", "/api/control/v1/config", "/api/control/v1/config", "/api/control/v1/config"}) {
        const auto r = m.request("GET", path);
        REQUIRE(r.status == 200 && r.body.find("wspr_dial_frequency_hz") == std::string::npos);
    }
    auto old = standalone::serialize_config(saved);
    old.replace(old.find("wspr_dial_frequency_hz"), 22, "wspr_base_frequency_hz");
    REQUIRE(!standalone::parse_config(old));
    REQUIRE(m.scheduler.command("CONFIG " + old).find("invalid_config") != std::string::npos);
    REQUIRE(*m.store.config() == saved);
    REQUIRE(m.scheduler.command("STOP").find("\"suspended\":true") != std::string::npos);
    REQUIRE(m.frequency("14095600").status == 200);
    REQUIRE(m.scheduler.suspended() && !m.store.config()->enabled && !m.service.activity().owned);
    // A fresh member exercises actual single-frame events at a nondefault dial.
    Member single;
    auto c = *single.store.config();
    c.wspr_dial_frequency_hz = 3568737;
    c.enabled = true; c.schedules = {{240,0}};
    REQUIRE(single.store.save(c));
    single.clock.now = 236 * ns; single.scheduler.poll();
    const auto plan = encoding::wspr_plan(c.callsign,c.locator,c.power_dbm);
    REQUIRE(plan && plan->count == 1 && single.engine.jobs.size() == 1);
    const std::array<std::uint64_t,4> expected{
        3570234802734375ULL,3570236267578125ULL,
        3570237732421875ULL,3570239197265625ULL};
    for (unsigned i=0;i<162;++i)
        REQUIRE(single.engine.jobs[0].events[i].frequency_nhz == expected[plan->frames[0].symbols[i]]);
    REQUIRE(single.frequency("14095600").status == 409);
    REQUIRE(single.store.config()->wspr_dial_frequency_hz == 3568737);
}
void console_first_selection_is_disabled() {
    Member m(true);
    auto c = *m.store.config(); c.wspr_dial_frequency_hz = 14095600;
    REQUIRE(c.enabled);
    REQUIRE(m.scheduler.command("CONFIG " + standalone::serialize_config(c)).find("\"ok\":true") != std::string::npos);
    REQUIRE(m.store.config()->wspr_dial_frequency_hz == 14095600 && !m.store.config()->enabled);
    REQUIRE(m.engine.jobs.empty() && !m.service.activity().owned);
    // A later explicit schedule operation owns enabled, with the saved dial intact.
    REQUIRE(m.scheduler.command("CONFIG " + standalone::serialize_config(c)).find("\"ok\":true") != std::string::npos);
    REQUIRE(m.store.config()->enabled && m.engine.jobs.empty());
}
void unset_is_nontransmitting() {
    Member m(true);
    REQUIRE(!m.store.config()->wspr_dial_frequency_hz);
    for (unsigned second = 1; second < 500; ++second) {
        m.clock.now = second * ns;
        m.scheduler.poll();
    }
    REQUIRE(m.engine.jobs.empty() && !m.store.watermark() && !m.service.activity().owned);
    const auto read = m.request("GET", "/api/control/v1/standalone-frequency");
    const auto value = parse(read.body);
    REQUIRE(read.status == 200 && value->get("frequency_hz")->raw == "null");
    REQUIRE(value->get("configured")->raw == "false" && value->get("allowed")->raw == "false");
    REQUIRE(m.scheduler.status().find("\"frequency_required\":true") != std::string::npos);
    REQUIRE(m.request("GET", "/api/control/v1/application")
                .body.find("\"schedule_dial_frequency_nhz\":\"0\"") != std::string::npos);
    // First selection is explicit and cannot resume the inherited enabled flag.
    REQUIRE(m.frequency("14095600").status == 200);
    REQUIRE(!m.store.config()->enabled && m.store.config()->wspr_dial_frequency_hz == 14095600);
    m.clock.now = 596 * ns;
    m.scheduler.poll();
    REQUIRE(m.engine.jobs.empty() && !m.store.watermark());
}
void validation_and_preservation() {
    Member m;
    const auto generation = m.store.config_sequence();
    for (auto bad : {"null", "true", "false", "\"14095600\"", "14095600.0", "1.40956e7", "0", "-1",
                     "014095600", "98502", "74998497", "4294967296", "3999999", "68998497", "18446744073709551616", "14095600.5", "14095600Hz"}) {
        REQUIRE(m.frequency(bad).status == 400);
        REQUIRE(m.store.config_sequence() == generation);
    }
    for (auto frequency : {136000, 472700, 1836600, 3568737, 5287200, 7038600, 10138700, 14095600,
                           18104600, 21094600, 24924600, 28124600, 50293000}) {
        REQUIRE(m.frequency(std::to_string(frequency)).status == 200);
        standalone::Store reboot(m.flash);
        REQUIRE(reboot.load() && reboot.config()->wspr_dial_frequency_hz == unsigned(frequency));
        REQUIRE(m.request("GET", "/api/control/v1/config").body.find("wspr_dial_frequency_hz") ==
                std::string::npos);
        REQUIRE(m.request("POST", "/api/control/v1/config/update", network_test::configuration_update(network_test::config)).status == 200);
        REQUIRE(m.store.config()->wspr_dial_frequency_hz == unsigned(frequency));
        REQUIRE(m.scheduler.command("CONFIG " + network_test::config).find("\"ok\":true") !=
                std::string::npos);
        REQUIRE(m.store.config()->wspr_dial_frequency_hz == unsigned(frequency));
        const auto supplied = parse(R"({"enabled":false})");
        auto candidate = application::config_candidate(*supplied, m.store.config(),
                                                       application::ConfigWrite::Merge);
        REQUIRE(candidate && standalone::parse_config(*candidate)->wspr_dial_frequency_hz ==
                                 unsigned(frequency));
    }
    auto wrong = m.envelope("14095600");
    wrong.replace(wrong.find(std::string(32, 'a')), 32, std::string(32, 'c'));
    REQUIRE(m.request("PUT", "/api/control/v1/standalone-frequency", wrong).status == 409);
    REQUIRE(
        m.request("PUT", "/api/control/v1/standalone-frequency", m.envelope("14095600"), "stale").status ==
        412);
    auto proposed = *m.store.config();
    proposed.wspr_dial_frequency_hz = 68'998'497;
    proposed.allow_unqualified_frequency = proposed.allow_non_amateur_frequency = true;
    REQUIRE(!standalone::wspr_frequency_allowed(proposed, 100'000 * ns, 68'999'999 * ns));
    proposed.wspr_dial_frequency_hz = 68'998'496;
    REQUIRE(standalone::wspr_frequency_allowed(proposed, 100'000 * ns, 68'999'999 * ns));
    const auto previous = m.store.config()->wspr_dial_frequency_hz;
    m.flash.fail = true;
    REQUIRE(m.frequency("14095600").status == 503);
    REQUIRE(m.store.config()->wspr_dial_frequency_hz == previous);
}
void pair_uses_selected_frequency() {
    Member m;
    REQUIRE(m.frequency("14095600").status == 200);
    auto config = *m.store.config();
    config.enabled = true;
    config.callsign = "AA0NT/P";
    config.locator = "EM18AA";
    config.schedules = {{240, 0}};
    REQUIRE(m.store.save(config));
    m.clock.now = 236 * ns;
    m.scheduler.poll();
    REQUIRE(m.engine.jobs.size() == 1 && m.service.activity().owned);
    REQUIRE(m.frequency("7038600").status == 409);
    for (unsigned second = 237; second <= 472; ++second) {
        m.clock.now = second * ns;
        m.scheduler.poll();
    }
    REQUIRE(m.engine.jobs.size() == 2 && m.scheduler.idle());
    const std::array<std::uint64_t, 4> expected{
        14097097802734375ULL, 14097099267578125ULL,
        14097100732421875ULL, 14097102197265625ULL};
    const auto plan = encoding::wspr_plan(config.callsign, config.locator, config.power_dbm);
    REQUIRE(plan && plan->count == 2);
    std::array<bool, 4> symbols{};
    for (unsigned frame = 0; frame < 2; ++frame) {
        const auto& job = m.engine.jobs[frame];
        REQUIRE(job.events.size() == 162);
        for (unsigned i = 0; i < job.events.size(); ++i) {
            const auto symbol = plan->frames[frame].symbols[i];
            symbols[symbol] = true;
            REQUIRE(job.events[i].frequency_nhz == expected[symbol]);
        }
    }
    REQUIRE(std::all_of(symbols.begin(), symbols.end(), [](bool v) { return v; }));
    REQUIRE(m.frequency("7038600").status == 200);
    m.clock.now = 476 * ns;
    m.scheduler.poll();
    REQUIRE(m.engine.jobs.size() == 3);
    const std::array<std::uint64_t, 4> next{
        7040097802734375ULL, 7040099267578125ULL,
        7040100732421875ULL, 7040102197265625ULL};
    for (unsigned i = 0; i < 162; ++i)
        REQUIRE(m.engine.jobs.back().events[i].frequency_nhz == next[plan->frames[0].symbols[i]]);
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--samples") {
        Member m;
        const auto unset = m.request("GET", "/api/control/v1/standalone-frequency");
        const auto selected = m.frequency("14095600");
        std::cout << '[' << unset.body << ',' << selected.body << "]\n";
        return 0;
    }
    first_use_requires_explicit_station_application();
    blocked_dial_survives_unrelated_updates();
    identity_atomicity_and_old_journal();
    absolute_jobs_ignore_standalone_dial();
    api_engine_boundaries();
    arithmetic_bounds_and_policy();
    single_frame_and_closed_views();
    console_first_selection_is_disabled();
    unset_is_nontransmitting();
    validation_and_preservation();
    pair_uses_selected_frequency();
    std::cout << "Standalone runtime frequency checks passed\n";
}

#include "application/config_update.hpp"
#include "network_support.hpp"

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
    wtp::JobService service{clock, engine, identity};
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
    explicit Member(bool inherited = false)
        : scheduler(initialize(inherited), service),
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
        return api.handle(request, "test", "127.0.0.1:8443");
    }
    std::string envelope(std::string value) {
        return "{\"schema\":\"transmitter-standalone-frequency/1\",\"target\":" +
               application::target(std::string(32, 'a'), service.status().boot_id) +
               ",\"frequency_hz\":" + value + "}";
    }
    network::HttpResponse frequency(std::string value) {
        return request("PUT", "/api/v1/standalone-frequency", envelope(value));
    }
};
void unset_is_nontransmitting() {
    Member m(true);
    REQUIRE(!m.store.config()->wspr_base_frequency_hz);
    for (unsigned second = 1; second < 500; ++second) {
        m.clock.now = second * ns;
        m.scheduler.poll();
    }
    REQUIRE(m.engine.jobs.empty() && !m.store.watermark() && !m.service.activity().owned);
    const auto read = m.request("GET", "/api/v1/standalone-frequency");
    const auto value = parse(read.body);
    REQUIRE(read.status == 200 && value->get("frequency_hz")->raw == "null");
    REQUIRE(value->get("configured")->raw == "false" && value->get("allowed")->raw == "false");
    REQUIRE(m.scheduler.status().find("\"frequency_required\":true") != std::string::npos);
    REQUIRE(m.request("GET", "/api/v1/application/4")
                .body.find("\"schedule_base_frequency_nhz\":\"0\"") != std::string::npos);
    // First selection is explicit and cannot resume the inherited enabled flag.
    REQUIRE(m.frequency("14097100").status == 200);
    REQUIRE(!m.store.config()->enabled && m.store.config()->wspr_base_frequency_hz == 14097100);
    m.clock.now = 596 * ns;
    m.scheduler.poll();
    REQUIRE(m.engine.jobs.empty() && !m.store.watermark());
}
void validation_and_preservation() {
    Member m;
    const auto generation = m.store.config_sequence();
    for (auto bad : {"null", "true", "false", "\"14097100\"", "14097100.0", "1.40971e7", "0", "-1",
                     "014097100", "99999", "74999995", "4294967296", "3999999"}) {
        REQUIRE(m.frequency(bad).status == 400);
        REQUIRE(m.store.config_sequence() == generation);
    }
    for (auto frequency : {137500, 474200, 1838100, 3570100, 5288700, 7040100, 10140200, 14097100,
                           18106100, 21096100, 24926100, 28126100, 50294500}) {
        REQUIRE(m.frequency(std::to_string(frequency)).status == 200);
        standalone::Store reboot(m.flash);
        REQUIRE(reboot.load() && reboot.config()->wspr_base_frequency_hz == unsigned(frequency));
        REQUIRE(m.request("GET", "/api/v1/config/4").body.find("wspr_base_frequency_hz") ==
                std::string::npos);
        REQUIRE(m.request("PUT", "/api/v1/config", network_test::config).status == 200);
        REQUIRE(m.store.config()->wspr_base_frequency_hz == unsigned(frequency));
        REQUIRE(m.scheduler.command("CONFIG " + network_test::config).find("\"ok\":true") !=
                std::string::npos);
        REQUIRE(m.store.config()->wspr_base_frequency_hz == unsigned(frequency));
        const auto supplied = parse(network_test::config);
        auto candidate = application::config_candidate(*supplied, m.store.config(),
                                                       application::ConfigWrite::Replace);
        REQUIRE(candidate && standalone::parse_config(*candidate)->wspr_base_frequency_hz ==
                                 unsigned(frequency));
    }
    auto wrong = m.envelope("14097100");
    wrong.replace(wrong.find(std::string(32, 'a')), 32, std::string(32, 'c'));
    REQUIRE(m.request("PUT", "/api/v1/standalone-frequency", wrong).status == 409);
    REQUIRE(
        m.request("PUT", "/api/v1/standalone-frequency", m.envelope("14097100"), "stale").status ==
        412);
    auto proposed = *m.store.config();
    proposed.wspr_base_frequency_hz = 68'999'995;
    proposed.allow_unqualified_frequency = proposed.allow_non_amateur_frequency = true;
    REQUIRE(!standalone::wspr_frequency_allowed(proposed, 100'000 * ns, 68'999'999 * ns));
    proposed.wspr_base_frequency_hz = 68'999'994;
    REQUIRE(standalone::wspr_frequency_allowed(proposed, 100'000 * ns, 68'999'999 * ns));
    const auto previous = m.store.config()->wspr_base_frequency_hz;
    m.flash.fail = true;
    REQUIRE(m.frequency("14097100").status == 503);
    REQUIRE(m.store.config()->wspr_base_frequency_hz == previous);
}
void pair_uses_selected_frequency() {
    Member m;
    REQUIRE(m.frequency("14097100").status == 200);
    auto config = *m.store.config();
    config.enabled = true;
    config.callsign = "AA0NT/P";
    config.locator = "EM18AA";
    config.schedules = {{240, 0}};
    REQUIRE(m.store.save(config));
    m.clock.now = 236 * ns;
    m.scheduler.poll();
    REQUIRE(m.engine.jobs.size() == 1 && m.service.activity().owned);
    REQUIRE(m.frequency("7040100").status == 409);
    for (unsigned second = 237; second <= 472; ++second) {
        m.clock.now = second * ns;
        m.scheduler.poll();
    }
    REQUIRE(m.engine.jobs.size() == 2 && m.scheduler.idle());
    for (const auto& job : m.engine.jobs)
        for (const auto& event : job.events) {
            REQUIRE(event.frequency_nhz);
            REQUIRE(*event.frequency_nhz >= 14'097'100 * ns &&
                    *event.frequency_nhz <= 14'097'100 * ns + 3 * 1'464'843'750ULL);
        }
    REQUIRE(m.frequency("7040100").status == 200);
    m.clock.now = 476 * ns;
    m.scheduler.poll();
    REQUIRE(m.engine.jobs.size() == 3);
    REQUIRE(*m.engine.jobs.back().events[0].frequency_nhz >= 7'040'100 * ns);
    REQUIRE(*m.engine.jobs.back().events[0].frequency_nhz < 7'040'105 * ns);
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--samples") {
        Member m;
        const auto unset = m.request("GET", "/api/v1/standalone-frequency");
        const auto selected = m.frequency("14097100");
        std::cout << '[' << unset.body << ',' << selected.body << "]\n";
        return 0;
    }
    unset_is_nontransmitting();
    validation_and_preservation();
    pair_uses_selected_frequency();
    std::cout << "Standalone runtime frequency checks passed\n";
}

#include "application/frequency_policy.hpp"
#include "application/resources.hpp"
#include "network_support.hpp"
#include "standalone/frequency_policy_engine.hpp"
#include "standalone/progress.hpp"
#include "wtp/json.hpp"

#include <tuple>

using namespace wsprrypico;
namespace {
constexpr std::uint64_t hz = 1'000'000'000;
// Spy around a real lifecycle simulator; rejected jobs must never be prepared
// or launched, and the decorator must preserve local timing capabilities.
struct SpyEngine : wtp::RfEngine {
    standalone::DryRunEngine simulator;
    unsigned preparations = 0, schedules = 0, begins = 0, disables = 0;
    bool accept = true;
    std::vector<wtp::FrequencyAdjustment> adjustments;
    wtp::PrepareResult prepare(const wtp::Job&) override {
        ++preparations;
        return {accept, adjustments};
    }
    bool set_frequency_correction_ppb(std::int32_t ppb) override {
        return ppb == 0;
    }
    std::string_view diagnostic() const override {
        return "spy";
    }
    bool schedules_locally() const override {
        return true;
    }
    bool owns_execution_plan() const override {
        return true;
    }
    std::uint64_t start_resolution_ns() const override {
        return 1000;
    }
    std::uint64_t completion_acknowledgement_ns() const override {
        return 5000;
    }
    bool schedule(const wtp::Job& job, std::uint64_t start,
                  const wtp::LocalStartConditions& conditions) override {
        ++schedules;
        return simulator.schedule(job, start, conditions);
    }
    bool begin(const wtp::Job&, std::uint64_t) override {
        ++begins;
        return true;
    }
    wtp::EngineReport poll(std::uint64_t now) override {
        return simulator.poll(now);
    }
    bool disable(std::uint64_t deadline) override {
        ++disables;
        return simulator.disable(deadline);
    }
    bool output_active() const override {
        return simulator.output_active();
    }
};
struct Fixture {
    network_test::Flash flash;
    standalone::Store store{flash};
    network_test::Flash progress_flash;
    standalone::Progress progress{progress_flash};
    network_test::Clock clock;
    SpyEngine raw;
    network_test::Identity identities;
    static wtp::ServiceConfig profile(std::uint64_t maximum) {
        wtp::ServiceConfig result;
        result.minimum_frequency_nhz = 100000 * hz;
        result.maximum_frequency_nhz = maximum;
        result.supported_modes = {"tone", "wspr", "qrss", "fskcw", "dfcw"};
        return result;
    }
    wtp::ServiceConfig limits;
    standalone::FrequencyPolicyEngine engine;
    wtp::JobService service;
    standalone::Store& initial_store() {
        REQUIRE(store.load());
        REQUIRE(store.save(*standalone::parse_config(network_test::config)));
        return store;
    }
    standalone::Scheduler scheduler;
    network_test::Network network;
    network::BrowserApi api;
    unsigned sequence = 1000;
    explicit Fixture(std::uint64_t maximum = 74999999 * hz)
        : limits(profile(maximum)),
          engine(raw, store, limits.minimum_frequency_nhz, limits.maximum_frequency_nhz),
          service(clock, engine, identities, limits), scheduler(initial_store(), service),
          api(service, store, scheduler, network, std::string(32, 'b'), "test") {
        REQUIRE(progress.load());
        api.progress_settings(progress);
    }
    std::string id() {
        return std::string(28, '0') + std::to_string(++sequence);
    }
    wtp::Job job(std::uint64_t frequency, std::string mode = "tone") {
        wtp::Job result;
        result.job_id = id();
        result.mode = std::move(mode);
        result.total_duration_ns = hz;
        result.events.push_back({0, hz, true, frequency});
        result.allow_frequency_adjustment = true;
        return result;
    }
    wtp::Response send(std::string operation, wtp::RequestBody body = {}) {
        wtp::Request request;
        request.session_id = std::string(32, 'a');
        request.request_id = id();
        request.principal = "cert";
        request.payload_digest[0] = 1;
        request.operation = std::move(operation);
        request.body = std::move(body);
        return service.handle(request);
    }
    void claim() {
        REQUIRE(send("HELLO", wtp::HelloBody{{"WTP/1"}}).ok);
        REQUIRE(send("CLAIM", wtp::ClaimBody{std::string(32, 'a'), 30000}).ok);
    }
    network::HttpResponse call(std::string method, std::string path, std::string body = {}) {
            network::HttpRequest request{std::move(method),
                                     std::move(path),
                                     std::move(body),
                                     {{"host", "127.0.0.1:8443"},
                                      {"origin", "https://127.0.0.1:8443"},
                                      {"content-type", "application/json"},
                                      {"x-wsprrypico-request", "1"},
                                      {"if-match", api.revision()}}};
        return api.handle(network_test::control_request(request), "cert", "127.0.0.1:8443");
    }
    void fail_progress_write() {
        const auto applied = *store.config();
        const auto config_sequence = store.config_sequence();
        const auto watermark = store.watermark();
        progress_flash.fail = true;
        const auto response =
            call("POST", "/api/control/v1/progress/update",
                 "{\"schema\":\"progress\",\"target\":" +
                     application::target(std::string(32, 'b'), service.status().boot_id) +
                     ",\"request_id\":\"" + id() + "\",\"fields\":{\"callsign\":\"BB1BB\"}}");
        REQUIRE(response.status == 503 && response.body.find("storage_fault") != std::string::npos);
        progress_flash.fail = false;
        REQUIRE(!progress.healthy() && !store.healthy());
        REQUIRE(*store.config() == applied && store.config_sequence() == config_sequence &&
                store.watermark() == watermark);
    }
    void flags(bool unqualified, bool non_amateur) {
        auto config = *store.config();
        config.allow_unqualified_frequency = unqualified;
        config.allow_non_amateur_frequency = non_amateur;
        const auto response = scheduler.command("CONFIG " + standalone::serialize_config(config));
        REQUIRE(wtp::json::parse(response)->get("ok")->boolean());
        REQUIRE(!scheduler.reboot_required());
    }
};
void config_and_storage() {
    auto parsed = standalone::parse_config(network_test::config);
    REQUIRE(parsed && !parsed->allow_unqualified_frequency && !parsed->allow_non_amateur_frequency);
    const auto legacy = standalone::serialize_config(*parsed);
    REQUIRE(legacy.find("allow_") == legacy.npos);
    for (const auto flag : {"allow_unqualified_frequency", "allow_non_amateur_frequency"}) {
        for (const auto value : {"0", "1", "null", "\"true\"", "[]", "{}"}) {
            auto text = legacy;
            text.insert(1, std::string("\"") + flag + "\":" + value + ',');
            REQUIRE(!standalone::parse_config(text));
        }
        auto duplicate = legacy;
        duplicate.insert(1, std::string("\"") + flag + "\":true,\"" + flag + "\":false,");
        REQUIRE(!standalone::parse_config(duplicate));
        auto explicit_false = legacy;
        explicit_false.insert(1, std::string("\"") + flag + "\":false,");
        REQUIRE(standalone::serialize_config(*standalone::parse_config(explicit_false)) == legacy);
    }
    Fixture f;
    REQUIRE(f.store.reserve(1800000000000000000ULL));
    const auto watermark = f.store.watermark();
    f.flags(true, true);
    standalone::Store reloaded(f.flash);
    REQUIRE(reloaded.load() && reloaded.config()->allow_unqualified_frequency &&
            reloaded.config()->allow_non_amateur_frequency && reloaded.watermark() == watermark);
    auto reading = f.call("GET", "/api/control/v1/config");
    REQUIRE(reading.body.find("test-password") == reading.body.npos);
    REQUIRE(wtp::json::parse(reading.body)
                ->get("config")
                ->get("allow_unqualified_frequency")
                ->boolean());
    const auto station =
        "{\"schema\":" + wtp::json::quote(application::station_schema) +
        ",\"target\":" + application::target(std::string(32, 'b'), f.service.status().boot_id) +
        ",\"station\":{\"callsign\":\"K1ABC\",\"locator\":\"FN42\",\"power_dbm\":20}}";
    REQUIRE(f.call("PUT", "/api/control/v1/station", station).status == 200);
    REQUIRE(f.store.config()->allow_unqualified_frequency &&
            f.store.config()->allow_non_amateur_frequency);
    REQUIRE(f.call("PUT", "/api/control/v1/schedules", R"({"schedules":[{"period_s":240,"phase_s":0}]})")
                .status == 200);
    REQUIRE(f.store.config()->allow_unqualified_frequency &&
            f.store.config()->allow_non_amateur_frequency);
    REQUIRE(f.store.watermark() == watermark);
    f.flags(false, false);
    REQUIRE(standalone::serialize_config(*f.store.config()).find("allow_") == std::string::npos);
    REQUIRE(f.scheduler.status().find("\"allow_unqualified_frequency\":false") !=
            std::string::npos);
}
void band_and_engine_limits() {
    using application::frequency_allowed;
    using application::frequency_disposition;
    using application::FrequencyDisposition;
    for (const auto ordinary :
         {135500ULL, 475700ULL, 1838100ULL, 3570100ULL, 5288700ULL, 7040100ULL, 10140200ULL,
          14097100ULL, 18106100ULL, 21096100ULL, 24926100ULL, 28126100ULL, 50294500ULL})
        REQUIRE(frequency_allowed(ordinary * hz, false, false));
    for (const auto unqualified :
         {40000000ULL, 40000995ULL, 40001000ULL, 54000001ULL, 60000995ULL, 60001000ULL, 69900000ULL,
          70500000ULL, 144000000ULL, 219000000ULL, 420000000ULL}) {
        REQUIRE(frequency_disposition(unqualified * hz) ==
                FrequencyDisposition::UnqualifiedAmateur);
        REQUIRE(!frequency_allowed(unqualified * hz, false, true));
        REQUIRE(frequency_allowed(unqualified * hz, true, false));
    }
    REQUIRE(frequency_allowed(54000000 * hz, false, false));
    REQUIRE(frequency_disposition(54000000 * hz + 1) == FrequencyDisposition::NonAmateur);
    REQUIRE(!frequency_allowed(0, true, true));
    for (const auto non_amateur : {100000ULL, 1000000ULL, 69000000ULL}) {
        REQUIRE(!frequency_allowed(non_amateur * hz, false, false));
        REQUIRE(!frequency_allowed(non_amateur * hz, true, false));
        REQUIRE(!frequency_allowed(non_amateur * hz, false, true));
        REQUIRE(frequency_allowed(non_amateur * hz, true, true));
    }
    for (const auto maximum : {65999999ULL, 68999999ULL, 74999999ULL}) {
        Fixture f(maximum * hz);
        f.flags(true, true);
        REQUIRE(!f.engine.prepare(f.job(144490000 * hz)).accepted);
        REQUIRE(!f.engine.prepare(f.job(99999 * hz)).accepted);
        REQUIRE(!f.engine.prepare(f.job(maximum * hz + 1)).accepted);
        REQUIRE(f.engine.prepare(f.job(70400000 * hz)).accepted == (maximum == 74999999));
        f.raw.accept = false;
        REQUIRE(!f.engine.prepare(f.job(3570100 * hz)).accepted);
    }
    Fixture f;
    f.flags(false, true);
    REQUIRE(!f.engine.prepare(f.job(70400000 * hz)).accepted);
    REQUIRE(!f.engine.prepare(f.job(1000000 * hz)).accepted);
    f.flags(true, false);
    REQUIRE(!f.engine.prepare(f.job(1000000 * hz)).accepted);
    f.flags(true, true);
    REQUIRE(f.engine.prepare(f.job(1000000 * hz)).accepted);
    f.flags(false, false);
    f.raw.preparations = 0;
    auto mark_space = f.job(3570100 * hz, "fskcw");
    mark_space.events[0].duration_ns = hz / 2;
    mark_space.events.push_back({hz / 2, hz / 2, true, 40000000 * hz});
    REQUIRE(!f.engine.prepare(mark_space).accepted && f.raw.preparations == 0);
    f.flags(true, false);
    REQUIRE(f.engine.prepare(mark_space).accepted);
    f.flags(false, false);
    f.raw.adjustments = {{0, 190000 * hz, 190000 * hz + 1}};
    REQUIRE(!f.engine.prepare(f.job(190000 * hz)).accepted);
    f.flags(true, true);
    REQUIRE(f.engine.prepare(f.job(190000 * hz)).accepted);
    f.raw.adjustments = {{0, 3570100 * hz, 75000000 * hz + 1}};
    REQUIRE(!f.engine.prepare(f.job(3570100 * hz)).accepted);
    f.raw.adjustments.clear();
    // Unhealthy flash cannot retain experimental authority in RAM.
    f.flash.fail = true;
    REQUIRE(!f.store.save(*f.store.config()) && !f.store.healthy());
    REQUIRE(!f.engine.prepare(f.job(70400000 * hz)).accepted);
}
void admission_and_revocation() {
    for (const auto mode : {"tone", "wspr", "qrss", "fskcw", "dfcw"}) {
        Fixture f;
        f.claim();
        REQUIRE(f.send("LOAD", f.job(70400000 * hz, mode)).error ==
                wtp::ErrorCode::FrequencyRejected);
        REQUIRE(f.raw.preparations == 0 && f.service.status().state == wtp::State::Empty);
        auto c = *f.store.config();
        c.allow_unqualified_frequency = true;
        REQUIRE(f.call("POST", "/api/control/v1/config/update", network_test::configuration_update(standalone::serialize_config(c))).status == 409);
        REQUIRE(!f.store.config()->allow_unqualified_frequency);
        REQUIRE(f.send("RELEASE").ok);
        f.flags(true, false);
        f.claim();
        const auto job = f.job(70400000 * hz, mode);
        REQUIRE(f.send("LOAD", job).ok);
        const auto start = f.clock.snapshot().utc_now_ns + 3000000000ULL;
        REQUIRE(f.send("ARM", wtp::ArmBody{job.job_id, start, 1000}).ok);
        REQUIRE(f.raw.schedules == 1 && f.service.status().state == wtp::State::Armed);
        REQUIRE(f.send("ABORT", wtp::AbortBody{job.job_id}).ok);
        REQUIRE(f.send("RELEASE").ok);
        f.flags(false, false);
        f.claim();
        REQUIRE(f.send("LOAD", f.job(70400000 * hz, mode)).error ==
                wtp::ErrorCode::FrequencyRejected);
        REQUIRE(f.raw.schedules == 1); // Revoking consent cannot launch a fresh job.
    }
    Fixture f;
    f.flags(true, true);
    REQUIRE(f.engine.schedules_locally() && f.engine.owns_execution_plan());
    REQUIRE(f.engine.start_resolution_ns() == 1000 &&
            f.engine.completion_acknowledgement_ns() == 5000);
    REQUIRE(!f.engine.set_frequency_correction_ppb(123) && f.engine.diagnostic() == "spy");
    REQUIRE(f.engine.begin(f.job(3570100 * hz), 0) && f.raw.begins == 1);
    const auto previous_disables = f.raw.disables;
    REQUIRE(f.engine.disable(100000) && f.raw.disables == previous_disables + 1 &&
            !f.engine.output_active());
    REQUIRE(f.engine.poll(0).state == wtp::EngineState::Idle);
    // Compact browser messages pass through the same guarded LOAD preparation.
    f.claim();
    const auto compact =
        "{\"job_id\":\"" + f.id() +
        "\",\"mode\":\"qrss\",\"message\":\"E\",\"frequency_nhz\":\"70400000000000000\","
        "\"space_frequency_nhz\":\"0\",\"timing\":{\"dot_ns\":\"1000000000\","
        "\"dash_ns\":\"3000000000\",\"intra_gap_ns\":\"1000000000\","
        "\"character_gap_ns\":\"3000000000\",\"word_gap_ns\":\"7000000000\"},"
        "\"repeat_count\":1,\"repeat_gap_ns\":\"0\",\"allow_frequency_adjustment\":true}";
    REQUIRE(f.send("RELEASE").ok);
    f.flags(false, false);
    f.claim();
    auto browser =
        f.call("POST", "/api/control/v1/jobs",
               "{\"session_id\":\"" + std::string(32, 'a') + "\",\"request_id\":\"" + f.id() +
                   "\",\"operation\":\"LOAD_MESSAGE\",\"body\":" + compact + '}');
    REQUIRE(browser.status == 409 && browser.body.find("FREQUENCY_REJECTED") != browser.body.npos);
    REQUIRE(f.service.status().state == wtp::State::Empty);
    REQUIRE(f.send("RELEASE").ok);
    f.flags(true, false);
    f.claim();
    browser = f.call("POST", "/api/control/v1/jobs",
                     "{\"session_id\":\"" + std::string(32, 'a') + "\",\"request_id\":\"" + f.id() +
                         "\",\"operation\":\"LOAD_MESSAGE\",\"body\":" + compact + '}');
    REQUIRE(browser.status == 200 && f.service.status().state == wtp::State::Loaded);
}
void progress_storage_fault_admission() {
    // A failed real draft append must revoke ordinary qualified-band execution,
    // not merely revoke the experimental frequency permissions.
    for (const auto mode : {"tone", "wspr", "qrss", "fskcw", "dfcw"}) {
        Fixture f;
        f.fail_progress_write();
        f.claim();
        REQUIRE(f.send("LOAD", f.job(3570100 * hz, mode)).error ==
                wtp::ErrorCode::FrequencyRejected);
        REQUIRE(f.raw.preparations == 0 && f.raw.schedules == 0 && f.raw.begins == 0);
        REQUIRE(f.service.status().state == wtp::State::Empty);
        REQUIRE(f.send("RELEASE").ok);
    }
    // Recheck health at both launch entry points: preparation can precede the
    // storage failure. Recovery/cleanup must still reach the underlying engine.
    Fixture f;
    const auto job = f.job(3570100 * hz);
    REQUIRE(f.engine.prepare(job).accepted && f.raw.preparations == 1);
    f.fail_progress_write();
    const auto now = f.clock.snapshot();
    REQUIRE(!f.engine.schedule(job, now.monotonic_now_ns + 3 * hz,
                               {&f.clock, now.utc_now_ns + 3 * hz, 1000, 0}));
    REQUIRE(!f.engine.begin(job, now.monotonic_now_ns));
    REQUIRE(f.raw.preparations == 1 && f.raw.schedules == 0 && f.raw.begins == 0);
    const auto disables = f.raw.disables;
    REQUIRE(f.engine.disable(now.monotonic_now_ns + hz) && f.raw.disables == disables + 1);
    REQUIRE(f.engine.poll(now.monotonic_now_ns).state == wtp::EngineState::Idle);
    REQUIRE(!f.engine.output_active());
}
void message_frequency_policy() {
    // The browser cannot waive per-event policy, engine bounds or ownership.
    const auto body = [](std::string mode, std::uint64_t first, std::uint64_t second) {
        return "{\"job_id\":\"" + std::string(32, '7') + "\",\"mode\":" + wtp::json::quote(mode) +
               ",\"message\":\"A E\",\"frequency_nhz\":\"" + std::to_string(first) +
               "\",\"space_frequency_nhz\":\"" + std::to_string(second) +
               "\",\"timing\":{\"dot_ns\":\"3000000000\",\"dash_ns\":\"9000000000\","
               "\"intra_gap_ns\":\"3000000000\",\"character_gap_ns\":\"9000000000\","
               "\"word_gap_ns\":\"21000000000\"},\"repeat_count\":2,"
               "\"repeat_gap_ns\":\"7000000000\",\"allow_frequency_adjustment\":true}";
    };
    for (const auto mode : {"qrss", "fskcw", "dfcw"}) {
        for (const auto& [first, second, allowed] :
             {std::tuple{14096905 * hz, 14096900 * hz, true},
              std::tuple{14096900 * hz, 14096905 * hz, std::string_view(mode) != "fskcw"},
              std::tuple{14000000 * hz, 14000000 * hz - 1, std::string_view(mode) == "qrss"},
              std::tuple{14350000 * hz + 1, 14096900 * hz, false},
              std::tuple{14096900 * hz, 74999999 * hz + 1, std::string_view(mode) == "qrss"},
              std::tuple{100000 * hz - 1, 14096900 * hz, false},
              std::tuple{74999999 * hz + 1, 14096900 * hz, false}}) {
            Fixture f;
            const auto compact = body(mode, first, second);
            const auto send = [&] {
                return f.call("POST", "/api/control/v1/jobs",
                              "{\"session_id\":\"" + std::string(32, 'a') + "\",\"request_id\":\"" +
                                  f.id() + "\",\"operation\":\"LOAD_MESSAGE\",\"body\":" + compact +
                                  '}');
            };
            REQUIRE(send().status ==
                    (std::string_view(mode) == "fskcw" && first <= second ? 400U : 409U));
            REQUIRE(f.raw.preparations == 0);
            f.claim();
            REQUIRE((send().status == 200) == allowed);
            REQUIRE(f.raw.preparations == (allowed ? 1U : 0U));
            REQUIRE(f.service.status().state == (allowed ? wtp::State::Loaded : wtp::State::Empty));
        }
    }
    // Explicit consent permits a large positive shift; no subtraction rule.
    Fixture f;
    f.flags(true, true);
    f.claim();
    const auto compact = body("dfcw", 100000 * hz, 200000 * hz);
    REQUIRE(f.call("POST", "/api/control/v1/jobs",
                   "{\"session_id\":\"" + std::string(32, 'a') + "\",\"request_id\":\"" + f.id() +
                       "\",\"operation\":\"LOAD_MESSAGE\",\"body\":" + compact + '}')
                .status == 200);
}
void autonomous_admission() {
    Fixture f;
    const auto period = 120 * hz;
    const auto next = (f.clock.snapshot().utc_now_ns / period + 1) * period + hz;
    f.clock.utc = next - 5 * hz - f.clock.now;
    auto config = *f.store.config();
    config.wspr_dial_frequency_hz = 3'568'600;
    config.enabled = true;
    REQUIRE(
        f.scheduler.command("CONFIG " + standalone::serialize_config(config)).find("\"ok\":true") !=
        std::string::npos);
    REQUIRE(!f.store.config()->enabled); // First dial selection cannot enable recurrence.
    REQUIRE(f.scheduler.command("CONFIG " + standalone::serialize_config(config)).find("\"ok\":true") != std::string::npos);
    f.scheduler.poll();
    const auto base = 3'570'097'802'734'375ULL;
    if (application::frequency_allowed(base, false, false)) {
        REQUIRE(f.service.status().state == wtp::State::Armed && f.raw.schedules == 1);
    } else {
        REQUIRE(f.service.status().state == wtp::State::Empty && f.raw.preparations == 0);
        REQUIRE(f.scheduler.status().find("FREQUENCY_REJECTED") != std::string::npos);
        REQUIRE(f.store.watermark() == next); // Failed occurrence is never retried.
        f.flags(true, false);
        f.scheduler.poll();
        REQUIRE(f.raw.schedules == 0);
        f.clock.utc += period;
        f.scheduler.poll();
        REQUIRE(f.service.status().state == wtp::State::Armed && f.raw.schedules == 1);
        REQUIRE(f.store.watermark() == next + period);
    }
}
} // namespace
int main() {
    config_and_storage();
    band_and_engine_limits();
    admission_and_revocation();
    progress_storage_fault_admission();
    message_frequency_policy();
    autonomous_admission();
    std::cout << "frequency policy checks passed\n";
}

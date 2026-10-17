#include "application/config_update.hpp"
#include "network_support.hpp"
#include "rf/calibration.hpp"
#include "rf/waveform.hpp"
#include "standalone/frequency_policy_engine.hpp"
#include "standalone/wtp_profile.hpp"
#include "time/controller_time.hpp"
#include "time/mapping.hpp"
#include "time/ntp_filter.hpp"
#include "time/sntp.hpp"

#include <charconv>
#include <iostream>
#include <sstream>

using namespace wsprrypico;
static_assert(sizeof(time::UtcDiscipline) <= 192);
static_assert(sizeof(time::NtpFilter) <= 6144);
namespace {
constexpr std::uint64_t ns = 1'000'000'000, epoch = 1'800'000'000 * ns;
std::uint64_t now(void* p) {
    return *static_cast<std::uint64_t*>(p);
}
void manual() {
    for (const auto& [text, expected] : {std::pair{"+10", 10000},
                                         {"-0.001", -1},
                                         {"100.000", 100000},
                                         {"-100", -100000},
                                         {"0", 0}}) {
        REQUIRE(rf::parse_ppm(text) == expected);
        REQUIRE(rf::parse_ppm(rf::format_ppm(expected)) == expected);
    }
    for (const auto bad : {"", "nan", "inf", "1e1", "100.001", "-100.001", "1.0000", " 1", "1 ",
                           ".1", "1.", "+", "100000000000", "--1"})
        REQUIRE(!rf::parse_ppm(bad));
    REQUIRE(rf::frequency_increment(3'570'100 * ns, 10000) <
            rf::frequency_increment(3'570'100 * ns, 0));
    network_test::Fixture f;
    REQUIRE(f.store.save(*standalone::parse_config(network_test::config)));
    const auto target = application::target(std::string(32, 'a'), f.service.status().boot_id);
    auto request = [&](std::string ppm, std::string mode = "manual") {
        network::HttpRequest r{"PUT",
                               "/api/v1/rf-calibration",
                               "{\"schema\":\"transmitter-rf-calibration/1\",\"target\":" + target +
                                   ",\"calibration\":{\"manual_ppm\":" + wtp::json::quote(ppm) +
                                   ",\"mode\":" + wtp::json::quote(mode) + "}}",
                               {{"host", "127.0.0.1:8443"},
                                {"origin", "https://127.0.0.1:8443"},
                                {"content-type", "application/json"},
                                {"x-wsprrypico-request", "1"},
                                {"if-match", f.api.revision()}}};
        return f.api.handle(r, "test", "127.0.0.1:8443");
    };
    REQUIRE(request("10.125").status == 200);
    REQUIRE(f.store.config()->manual_correction_ppb == 10125);
    standalone::Store reboot(f.flash);
    REQUIRE(reboot.load() && reboot.config()->manual_correction_ppb == 10125);
    REQUIRE(request("0", "ntp").status == 200);
    REQUIRE(f.store.config()->manual_correction_ppb == 0 && f.store.config()->ntp_rf_calibration);
    REQUIRE(request("-100.001").status == 400);
    REQUIRE(request("1.2345").status == 400);
    REQUIRE(request("0", "automatic").status == 400);
    const auto old = standalone::parse_config(network_test::config);
    auto extended = *old;
    extended.manual_correction_ppb = -10125;
    extended.ntp_rf_calibration = true;
    const auto supplied = wtp::json::parse(network_test::config);
    const auto legacy =
        application::config_candidate(*supplied, extended, application::ConfigWrite::Legacy);
    REQUIRE(standalone::parse_config(*legacy)->manual_correction_ppb == -10125);
    const auto replaced =
        application::config_candidate(*supplied, extended, application::ConfigWrite::Replace);
    REQUIRE(standalone::parse_config(*replaced)->manual_correction_ppb == 0);
    REQUIRE(!standalone::parse_config(*replaced)->ntp_rf_calibration);
    REQUIRE(f.store.save(extended));
    REQUIRE(wtp::json::parse(f.scheduler.command("CONFIG " + network_test::config))
                ->get("ok")
                ->boolean());
    REQUIRE(f.store.config()->manual_correction_ppb == -10125);
    // Every journal page failure fails closed instead of resurrecting old settings.
    struct TornFlash : network_test::Flash {
        int pages = -1;
        bool program(std::size_t offset, std::span<const std::uint8_t> bytes) override {
            if (pages == 0)
                return false;
            if (pages > 0)
                --pages;
            return network_test::Flash::program(offset, bytes);
        }
    };
    for (int page = 0; page < 8; ++page) {
        TornFlash flash;
        standalone::Store store(flash);
        REQUIRE(store.load() && store.save(*old));
        flash.pages = page;
        REQUIRE(!store.save(extended));
        standalone::Store recovered(flash);
        if (page == 0) {
            REQUIRE(recovered.load() && recovered.config()->manual_correction_ppb == 0);
        } else
            REQUIRE(!recovered.load());
    }
    // Closed old config views never leak new fields to strict old clients.
    network::HttpRequest get{"GET", "/api/v1/config", {}, {{"host", "127.0.0.1:8443"}}};
    REQUIRE(f.api.handle(get, "test", "127.0.0.1:8443").body.find("correction") ==
            std::string::npos);
}
time::NtpSample sample(unsigned i, std::int32_t slope = -10000) {
    time::NtpSample result;
    result.id = i + 1;
    result.epoch = 1;
    result.raw_ns = (i + 1) * 64 * ns;
    result.send_ns = result.raw_ns - 2'000'000;
    std::uint64_t elapsed{};
    REQUIRE(time::elapsed_utc(result.raw_ns, slope, elapsed));
    result.utc_ns = epoch + elapsed;
    result.uncertainty_ns = 2'000'000;
    result.rtt_ns = 1'000'000;
    return result;
}
void callback_latency() {
    std::uint64_t raw = 0;
    time::UtcDiscipline clock(now, &raw, standalone::clock_profile());
    time::Sntp sntp(clock);
    const auto request = sntp.request(raw, 1234);
    std::array<std::uint8_t, 48> reply{};
    reply[0] = 0x24;
    reply[1] = 2;
    reply[3] = 0xec;
    std::copy(request.begin() + 40, request.end(), reply.begin() + 24);
    for (unsigned offset : {16, 32, 40}) {
        const auto stamp = 1'800'000'000ULL + 2'208'988'800ULL;
        for (unsigned j = 0; j < 4; ++j)
            reply[offset + j] = std::uint8_t(stamp >> ((3 - j) * 8));
    }
    raw = 52'000'000; // 2 ms network plus 50 ms local receive processing delay.
    REQUIRE(sntp.receive(reply, raw));
    const auto snap = clock.snapshot();
    REQUIRE(snap.utc_now_ns == epoch + 26'000'000);
    REQUIRE(snap.uncertainty_ns >= 53'000'000);
    const auto truth = epoch + 51'000'000;
    REQUIRE(truth - snap.utc_now_ns <= snap.uncertainty_ns);
    REQUIRE(sntp.observations_json().find("52000000") != std::string::npos);
    const auto good = reply;
    for (unsigned fault : {0, 1}) {
        time::Sntp invalidated(clock);
        (void)invalidated.request(raw, 1234);
        raw += 1'000'000;
        REQUIRE(invalidated.receive(good, raw));
        (void)invalidated.request(raw, 1234);
        raw += 1'000'000;
        reply = good;
        if (fault == 0)
            reply[1] = 0;
        else
            reply[0] |= 0x40;
        REQUIRE(!invalidated.receive(reply, raw));
        REQUIRE(invalidated.observations_json().find("\"filter_selected\":null") !=
                std::string::npos);
        REQUIRE(invalidated.observations_json().find("\"anchor_observation_id\":\"0\"") !=
                std::string::npos);
        REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    }
    sntp.reset_peer();
    REQUIRE(sntp.observations_json().find("peer_reset") != std::string::npos);
    REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
}
void filtering() {
    time::NtpFilter filter;
    REQUIRE(!filter.rate(0).qualified);
    for (unsigned i = 0; i < 32; ++i)
        REQUIRE(filter.add(sample(i)));
    const auto estimate = filter.rate(sample(31).raw_ns);
    REQUIRE(estimate.qualified && std::abs(estimate.utc_rate_ppb + 10000) <= 1);
    REQUIRE(estimate.uncertainty_ppb >= 2000 && estimate.uncertainty_ppb <= 5000);
    REQUIRE(!filter.add(sample(31)));
    REQUIRE(!filter.rate(estimate.sampled_ns + time::ntp_fresh_ns + 1).qualified);
    auto changed = sample(32);
    changed.epoch = 2;
    REQUIRE(filter.add(changed) && !filter.rate(changed.raw_ns).qualified);
    REQUIRE(filter.rate(changed.raw_ns).samples == 1);
    auto restarted = sample(0);
    restarted.epoch = 3;
    REQUIRE(filter.add(restarted) && filter.rate(restarted.raw_ns).samples == 1);
    auto stepped = sample(33);
    stepped.epoch = 2;
    stepped.utc_ns += 2 * ns;
    REQUIRE(filter.add(stepped) && filter.rate(stepped.raw_ns).samples == 1);
    time::NtpFilter low_delay;
    auto a = sample(0), b = sample(1);
    b.raw_ns = a.raw_ns + 2 * ns;
    b.send_ns = b.raw_ns - 100'000'000;
    b.utc_ns = a.utc_ns + 2 * ns - 20000;
    b.rtt_ns = 100'000'000;
    REQUIRE(low_delay.add(a) && low_delay.add(b));
    REQUIRE(low_delay.selected(b.raw_ns)->id == a.id);
    REQUIRE(low_delay.selected(b.raw_ns)->raw_ns == a.raw_ns);
    REQUIRE(!low_delay.selected(b.raw_ns + time::ntp_fresh_ns + 1));
    for (const auto slope : {-20000, 0, 20000}) {
        time::NtpFilter f;
        for (unsigned i = 0; i < 32; ++i)
            REQUIRE(f.add(sample(i, slope)));
        const auto rate = f.rate(sample(31).raw_ns);
        const auto correction = time::oscillator_correction(rate);
        REQUIRE(rate.qualified && correction);
        REQUIRE((slope < 0 && *correction > 0) || (slope == 0 && *correction == 0) ||
                (slope > 0 && *correction < 0));
    }
    time::RateEstimate boundary{true, -100000};
    REQUIRE(!time::oscillator_correction(boundary)); // reciprocal > +100 ppm; never clamp.
    // A small regression residual cannot discard systematic source uncertainty.
    time::NtpFilter biased;
    for (unsigned i = 0; i < 32; ++i) {
        auto s = sample(i);
        s.utc_ns += 20'000'000;
        s.uncertainty_ns = 100'000'000;
        REQUIRE(biased.add(s));
    }
    REQUIRE(!biased.rate(sample(31).raw_ns).qualified);
}
void mapping() {
    std::uint64_t raw = 100 * ns;
    time::UtcDiscipline clock(now, &raw, standalone::clock_profile());
    REQUIRE(clock.observe_rate(epoch, raw, 2'000'000, -10000, 2500, 1));
    raw += 64 * ns;
    auto snapshot = clock.snapshot();
    REQUIRE(snapshot.utc_now_ns == epoch + 64 * ns - 640000);
    REQUIRE(snapshot.sync_age_ns == 64 * ns && snapshot.rate_ppb == -10000);
    REQUIRE(snapshot.uncertainty_ns >= 2'000'000 + 64 * 52500);
    std::uint64_t target{};
    REQUIRE(time::inverse(snapshot, epoch + 70 * ns, target));
    std::uint64_t projected{}, prior{};
    REQUIRE(time::project(snapshot, target, projected) && projected >= epoch + 70 * ns);
    REQUIRE(time::project(snapshot, target - 1, prior) && prior < epoch + 70 * ns);
    const auto generation = snapshot.model_generation;
    clock.invalidate();
    REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    REQUIRE(clock.snapshot().model_generation > generation);
    REQUIRE(clock.observe_rate(epoch + 64 * ns, raw, 2'000'000, -10000, 2500, 1));
    REQUIRE(clock.snapshot().model_generation > generation + 1);
    raw += 117 * ns;
    REQUIRE(clock.snapshot().state == wtp::ClockState::Holdover);
    raw += 64 * ns;
    REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    REQUIRE(clock.snapshot().model_generation > generation);
    time::UtcDiscipline cold(now, &raw, standalone::clock_profile());
    REQUIRE(cold.snapshot().state == wtp::ClockState::Unsynchronized);
    snapshot.monotonic_now_ns = UINT64_MAX - 1;
    snapshot.utc_now_ns = epoch;
    REQUIRE(!time::inverse(snapshot, epoch + ns, target));
    snapshot.rate_ppb = INT32_MIN;
    REQUIRE(!time::inverse(snapshot, epoch, target));
}
struct CorrectionEngine : wtp::RfEngine {
    std::int32_t correction = 0;
    unsigned prepares = 0;
    bool set_frequency_correction_ppb(std::int32_t ppb) override {
        correction = ppb;
        return true;
    }
    wtp::PrepareResult prepare(const wtp::Job& job) override {
        ++prepares;
        const auto plan = rf::plan_job(job, correction);
        return plan ? wtp::PrepareResult{true, {}} : wtp::PrepareResult{};
    }
    bool begin(const wtp::Job&, std::uint64_t) override {
        return false;
    }
    wtp::EngineReport poll(std::uint64_t) override {
        return {};
    }
    bool disable(std::uint64_t) override {
        return true;
    }
    bool output_active() const override {
        return false;
    }
};
void freeze() {
    network_test::Flash flash;
    standalone::Store store(flash);
    REQUIRE(store.load());
    auto c = *standalone::parse_config(network_test::config);
    c.manual_correction_ppb = 10000;
    REQUIRE(store.save(c));
    CorrectionEngine raw;
    standalone::FrequencyPolicyEngine engine(raw, store, 100000 * ns, 74000000 * ns);
    wtp::Job job{
        std::string(32, 'a'), "rf-events/1", "tone", ns, {{0, ns, true, 3'570'100 * ns}}, true};
    engine.freeze_pair_calibration(true);
    REQUIRE(engine.prepare(job).accepted && raw.correction == 10000);
    c.manual_correction_ppb = -10000;
    REQUIRE(store.save(c)); // Unit-level bypass of idle guard tests pair freeze.
    REQUIRE(engine.prepare(job).accepted && raw.correction == 10000);
    job.allow_frequency_adjustment = false;
    REQUIRE(!engine.prepare(job).accepted);
    engine.calibration_boundary();
    job.allow_frequency_adjustment = true;
    REQUIRE(engine.prepare(job).accepted && raw.correction == -10000);
    c.ntp_rf_calibration = true;
    REQUIRE(store.save(c));
    network_test::Clock clock;
    time::RateEstimate r{true, -10000, 1000, 42, clock.now, 2000 * ns, 32, "qualified_software"};
    engine.ntp_candidate(r, clock, true);
    engine.calibration_boundary();
    REQUIRE(engine.prepare(job).accepted && raw.correction == -10000);
    REQUIRE(engine.calibration_status(clock.now).find("independent_rf_unverified") !=
            std::string::npos);
    REQUIRE(engine.calibration_status(clock.now + time::ntp_fresh_ns + 1).find("stale") !=
            std::string::npos);
    engine.ntp_candidate(r, clock, false);
    REQUIRE(engine.calibration_status(clock.now).find("unsupported_clock_topology") !=
            std::string::npos);
    c.manual_correction_ppb = 0;
    c.ntp_rf_calibration = false;
    REQUIRE(store.save(c));
    engine.calibration_boundary();
    REQUIRE(engine.prepare(job).accepted && raw.correction == 0);
}
void replay() {
    std::uint64_t raw = 0;
    const auto config = standalone::clock_profile();
    time::UtcDiscipline clocks[] = {{now, &raw, config}, {now, &raw, config}, {now, &raw, config}};
    time::ControllerTimeArbiter arbiters[] = {{clocks[0], now, &raw, "replay"},
                                              {clocks[1], now, &raw, "replay"},
                                              {clocks[2], now, &raw, "replay"}};
    time::NtpFilter filters[2];
    std::uint64_t applied[3] = {}, previous_epoch = 0;
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream in(line);
        time::NtpSample s;
        std::uint64_t probe{}, truth{};
        unsigned accepted{};
        if (!(in >> s.id >> s.epoch >> s.raw_ns >> s.utc_ns >> s.uncertainty_ns >> s.rtt_ns >>
              probe >> truth >> accepted))
            std::exit(2);
        raw = s.raw_ns;
        s.send_ns = raw - s.rtt_ns;
        if (previous_epoch && s.epoch != previous_epoch) {
            for (auto& filter : filters)
                filter.reset();
            for (auto& arbiter : arbiters)
                arbiter.invalidate(time::ObservationSource::Sntp);
            std::fill(std::begin(applied), std::end(applied), 0);
        }
        previous_epoch = s.epoch;
        if (accepted) {
            for (unsigned mode = 0; mode < 3; ++mode) {
                auto chosen = std::optional{s};
                time::RateEstimate rate;
                if (mode) {
                    auto& filter = filters[mode - 1];
                    if (!filter.add(s))
                        continue;
                    chosen = filter.selected(raw);
                    rate = filter.rate(raw);
                }
                if (chosen && chosen->id > applied[mode]) {
                    if (arbiters[mode].observe_rate(
                            chosen->utc_ns, chosen->raw_ns, chosen->uncertainty_ns,
                            mode == 2 && rate.qualified ? rate.utc_rate_ppb : 0,
                            mode == 2 && rate.qualified ? rate.uncertainty_ppb : 0,
                            rate.generation))
                        applied[mode] = chosen->id;
                    else if (mode) {
                        filters[mode - 1].reset();
                        applied[mode] = 0;
                    }
                }
            }
        }
        raw = probe;
        for (unsigned mode = 0; mode < 3; ++mode) {
            const auto snap = clocks[mode].snapshot();
            const bool usable = snap.state != wtp::ClockState::Unsynchronized &&
                                snap.sync_age_ns <= time::ntp_fresh_ns &&
                                snap.uncertainty_ns <= 500'000'000;
            const auto error = snap.utc_now_ns >= truth ? std::int64_t(snap.utc_now_ns - truth)
                                                        : -std::int64_t(truth - snap.utc_now_ns);
            std::cout << mode << ' ' << s.id << ' ' << error << ' ' << snap.uncertainty_ns << ' '
                      << snap.sync_age_ns << ' ' << usable << ' ' << snap.rate_ppb << '\n';
        }
    }
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "replay") {
        replay();
        return 0;
    }
    if (argc == 6 && std::string_view(argv[1]) == "map") {
        wtp::ClockSnapshot anchor;
        anchor.monotonic_now_ns = std::stoull(argv[2]);
        anchor.utc_now_ns = std::stoull(argv[3]);
        anchor.rate_ppb = std::stoi(argv[4]);
        std::uint64_t raw{}, projected{};
        if (!time::inverse(anchor, std::stoull(argv[5]), raw) ||
            !time::project(anchor, raw, projected))
            std::cout << "invalid\n";
        else
            std::cout << raw << " " << projected << "\n";
        return 0;
    }
    manual();
    callback_latency();
    filtering();
    mapping();
    freeze();
    std::cout << "NTP work deterministic checks passed\n";
}

#include "application/config_update.hpp"
#include "network_support.hpp"
#include "rf/calibration.hpp"
#include "rf/waveform.hpp"
#include "standalone/frequency_policy_engine.hpp"
#include "standalone/ntp_retention.hpp"
#include "standalone/wtp_profile.hpp"
#include "time/controller_time.hpp"
#include "time/mapping.hpp"
#include "time/ntp_filter.hpp"
#include "time/sntp.hpp"

#include <charconv>
#include <iostream>
#include <sstream>

using namespace wsprrypico;
static_assert(sizeof(time::UtcDiscipline) <= 320);
static_assert(sizeof(microchrony::Engine) <= 32768);
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
    const auto rejected = request("0", "ntp");
    REQUIRE(rejected.status == 400 && rejected.body.find("ntp_rf_rejected") != std::string::npos);
    REQUIRE(f.store.config()->manual_correction_ppb == 10125 &&
            !f.store.config()->ntp_rf_calibration);
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
    const auto legacy_view =
        f.api.handle({"GET", "/api/v1/rf-calibration", {}, {{"host", "127.0.0.1:8443"}}}, "test",
                     "127.0.0.1:8443");
    REQUIRE(legacy_view.status == 200 &&
            legacy_view.body.find("\"mode\":\"manual\"") != std::string::npos);
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
std::array<std::uint8_t, 48> ntp_reply(const std::array<std::uint8_t, 48>& request,
                                       std::uint64_t utc) {
    std::array<std::uint8_t, 48> result{};
    result[0] = 0x24;
    result[1] = 2;
    result[3] = 0xec;
    std::copy(request.begin() + 40, request.end(), result.begin() + 24);
    const auto seconds = utc / ns + 2'208'988'800ULL;
    const auto fraction = ((utc % ns) << 32) / ns;
    for (unsigned offset : {16, 32, 40})
        for (unsigned j = 0; j < 4; ++j) {
            result[offset + j] = std::uint8_t(seconds >> ((3 - j) * 8));
            result[offset + 4 + j] = std::uint8_t(fraction >> ((3 - j) * 8));
        }
    return result;
}
void diagnostic_pages(bool emit_packets = false) {
    std::uint64_t raw = 0;
    time::UtcDiscipline clock(now, &raw, standalone::clock_profile());
    time::NtpClient client(clock);
    for (unsigned i = 0; i < 80; ++i) {
        raw = (i + 1) * 64 * ns;
        const auto request = client.request(raw, i + 1);
        raw += 2'000'000;
        REQUIRE(client.receive(ntp_reply(request, epoch + raw - 1'000'000), raw));
    }
    REQUIRE(client.engine().history(0).size() <= 64);
    REQUIRE(client.learning_json(raw).size() < 1100);
    const time::NtpDiagnosticBinding binding{"device", "boot", "image", "revision", "server"};
    unsigned cursor = 0, count = 0;
    std::string token = "-";
    do {
        const auto wire = client.history_page(binding, token + " " + std::to_string(cursor), raw);
        REQUIRE(wire.size() <= 4096);
        const auto page = wtp::json::parse(wire);
        REQUIRE(page && page->get("ok")->boolean());
        token = std::string(page->get("token")->string());
        REQUIRE(page->get("records")->elements().size() <= 4);
        count += page->get("records")->elements().size();
        const auto next = unsigned(page->get("next_cursor")->integer());
        REQUIRE(next >= cursor);
        cursor = next;
        if (!page->get("more")->boolean())
            break;
        REQUIRE(count <= 64);
    } while (true);
    REQUIRE(count == client.engine().history(0).size());
    const auto audit_wire = client.packet_page(binding, "0", raw);
    const auto audit = wtp::json::parse(audit_wire);
    REQUIRE(audit && audit->get("ok")->boolean());
    REQUIRE(audit->get("lost_before")->string() == "48");
    REQUIRE(audit->get("oldest_id")->string() == "49");
    REQUIRE(audit->get("overwritten")->string() == "48");
    const auto first = audit->get("records")->elements().front();
    REQUIRE(first.get("id")->string() == "49");
    REQUIRE(first.get("accepted")->boolean());
    REQUIRE(first.get("prefix_hex")->string().size() == 96);
    REQUIRE(client.configure(0, 123, raw));
    const auto same_wire = client.packet_page(binding, "48", raw);
    const auto same = wtp::json::parse(same_wire);
    REQUIRE(same->get("records")->elements().front().get("endpoint")->string() == "1");
    REQUIRE(same->get("records")->elements().front().get("clock_epoch")->string() == "1");
    std::array<std::uint8_t, 49> malformed{};
    malformed[0] = 0xe4;
    REQUIRE(!client.receive(0, malformed, ++raw, true, 300));
    const auto rejected_wire = client.packet_page(binding, "80", raw);
    const auto rejected = wtp::json::parse(rejected_wire);
    const auto bad = rejected->get("records")->elements().front();
    REQUIRE(!bad.get("accepted")->boolean() && bad.get("truncated")->boolean());
    REQUIRE(bad.get("prefix_hex")->string().starts_with("e4"));
    REQUIRE(bad.get("length")->integer() == 300);
    REQUIRE(bad.get("endpoint")->string() == "123");
    REQUIRE(bad.get("clock_epoch")->string() == "2");
    REQUIRE(bad.get("request_raw_ns")->string() == "0");
    REQUIRE(bad.get("request_token")->string() == "0");
    REQUIRE(bad.get("reason")->string() == "correlation");
    REQUIRE(client.packet_page(binding, "80", raw).size() < 4096);
    for (const auto cursor_text : {"01", "-1", "82", "18446744073709551615", " 0"})
        REQUIRE(client.packet_page(binding, cursor_text, raw).find("ntp_packet_cursor") !=
                std::string::npos);
    const auto other = client.history_page(binding, "@1 - 0", raw);
    REQUIRE(wtp::json::parse(other)->get("count")->integer() == 0);
    client.reset_peer();
    REQUIRE(client.history_page(binding, token + " 60", raw).find("ntp_history_changed") !=
            std::string::npos);
    REQUIRE(client.history_page(binding, "- 01", raw).find("ntp_history_cursor") !=
            std::string::npos);
    if (emit_packets) {
        std::string packet_cursor = "0";
        for (unsigned i = 0; i < 8; ++i) {
            const auto wire = client.packet_page(binding, packet_cursor, raw);
            std::cout << wire;
            const auto page = wtp::json::parse(wire);
            REQUIRE(page && page->get("ok")->boolean());
            packet_cursor = page->get("next_cursor")->string();
            if (!page->get("more")->boolean())
                return;
        }
        REQUIRE(false);
    }
}
void selected_source_freshness() {
    std::uint64_t raw = 0;
    time::UtcDiscipline clock(now, &raw, standalone::clock_profile());
    time::NtpClient client(clock);
    REQUIRE(client.configure(1, 2, 0));
    for (unsigned i = 1; i <= 12; ++i) {
        raw = i * 66 * ns;
        const auto request = client.request(raw, i);
        raw += 2'000'000;
        REQUIRE(client.receive(ntp_reply(request, epoch + raw - 1'000'000), raw));
        raw += ns;
        const auto other = client.scheduled_request(1, raw, i + 100);
        REQUIRE(other);
        raw += 4'000'000;
        REQUIRE(client.receive(1, ntp_reply(*other, epoch + raw - 2'000'000), raw));
    }
    REQUIRE(client.selected_slot(raw) == 0);
    REQUIRE(client.engine().status(1, raw).combined);
    const auto before = client.engine().tracking(raw);
    const auto source = before.source_raw_ns;
    raw = source + 66 * ns;
    const auto request = client.request(raw, 1000);
    const auto server = epoch + raw + 1'000'000;
    raw += 200'000'000;
    REQUIRE(!client.receive(ntp_reply(request, server), raw)); // One-way queue fails admission.
    REQUIRE(client.engine().last_measurement(0)->rejection ==
            microchrony::Rejection::DelayDeviation);
    raw = source + 67 * ns;
    const auto other = client.scheduled_request(1, raw, 1001);
    REQUIRE(other);
    raw += 4'000'000;
    REQUIRE(client.receive(1, ntp_reply(*other, epoch + raw - 2'000'000), raw));
    REQUIRE(client.engine().tracking(raw).generation == before.generation);
    REQUIRE(client.engine().tracking(raw).source_raw_ns == source);
    raw = source + time::ntp_fresh_ns;
    REQUIRE(client.apply(raw));
    REQUIRE(clock.snapshot().state == wtp::ClockState::Synchronized);
    ++raw;
    REQUIRE(client.apply(raw));
    REQUIRE(clock.snapshot().state == wtp::ClockState::Holdover);
    REQUIRE(!client.peer_fresh(raw) && !client.rate(raw).qualified);
    raw = source + 132 * ns;
    const auto recovered = client.request(raw, 1002);
    raw += 2'000'000;
    REQUIRE(client.receive(ntp_reply(recovered, epoch + raw - 1'000'000), raw));
    REQUIRE(clock.snapshot().state == wtp::ClockState::Synchronized);
    REQUIRE(client.engine().tracking(raw).generation > before.generation);
}
void model_import() {
    std::uint64_t raw = 10 * ns;
    time::UtcDiscipline clock(now, &raw, standalone::clock_profile());
    time::ControllerTimeArbiter arbiter(clock, now, &raw, "test");
    wtp::ClockSnapshot model;
    model.state = wtp::ClockState::Synchronized;
    model.utc_now_ns = epoch;
    model.monotonic_now_ns = raw;
    model.uncertainty_ns = 11'000'000;
    model.sync_age_ns = ns;
    model.leap = wtp::LeapState::Normal;
    model.rate_ppb = 1'000'000;
    model.rate_uncertainty_ppb = 1000;
    model.model_generation = 1;
    model.rate_until_monotonic_ns = raw + 10 * ns;
    model.subsequent_rate_ppb = -20000;
    time::RateObservation source{epoch - ns + 10'000'000, raw - ns, 1'000'000, 0, 1000, 1};
    REQUIRE(arbiter.observe_ntp_model(source, model, 1000));
    const auto generation = clock.snapshot().model_generation;
    raw += 5 * ns;
    REQUIRE(clock.snapshot().sync_age_ns == 6 * ns);
    REQUIRE(clock.snapshot().utc_now_ns == epoch + 5 * ns + 5'000'000);
    raw += 10 * ns;
    const auto snapshot = clock.snapshot();
    REQUIRE(snapshot.utc_now_ns == epoch + 15 * ns + 10'000'000 - 100000);
    REQUIRE(snapshot.rate_ppb == -20000 && snapshot.rate_until_monotonic_ns == UINT64_MAX);
    REQUIRE(snapshot.model_generation == generation && snapshot.sync_age_ns == 16 * ns);
    REQUIRE(!arbiter.observe_ntp_model(source, model, 1000)); // Old import anchor.
    clock.invalidate();
    REQUIRE(clock.observe(epoch, raw, 1000000, wtp::LeapState::Normal));
    REQUIRE(clock.snapshot().subsequent_rate_ppb == 0);
    REQUIRE(clock.snapshot().rate_until_monotonic_ns == UINT64_MAX);

    time::UtcDiscipline other_clock(now, &raw, standalone::clock_profile());
    time::ControllerTimeArbiter other(other_clock, now, &raw, "other");
    REQUIRE(other.observe(time::ObservationSource::Controller, epoch, raw, 1'000'000,
                          wtp::LeapState::Normal, {}, "controller"));
    model.monotonic_now_ns = raw;
    model.utc_now_ns = epoch; // Slewed control can agree while NTP truth disagrees.
    model.rate_until_monotonic_ns = UINT64_MAX;
    model.sync_age_ns = 0;
    source = {epoch + ns, raw, 1'000'000, 0, 1000, 1};
    model.uncertainty_ns = ns + 1'000'000;
    REQUIRE(!other.observe_ntp_model(source, model, 1000));
    REQUIRE(other.status().disagreement);
    REQUIRE(!other.observe_ntp_model(source, model, 1000));
    REQUIRE(!other.observe_ntp_model(source, model, 1000)); // Same evidence cannot recover.
    raw += ns;
    source.raw_ns = model.monotonic_now_ns = raw;
    source.utc_ns += ns;
    model.utc_now_ns += ns;
    source.generation = model.model_generation = 2;
    REQUIRE(other.observe_ntp_model(source, model, 1000));
    REQUIRE(!other.status().disagreement);
}

void retention() {
    using Cache = standalone::NtpRetention;
    const auto device = std::string(32, 'a');
    constexpr std::uint64_t topology = (std::uint64_t(138000000) << 32) | 138000000;
    Cache::Provenance source{std::string(32, 'b'), 0xc0000201, 4, 10, epoch};
    Cache::RfPrior rf{-10000, 1000, 32, 2000 * ns, source};
    network_test::Flash flash;
    Cache cache(flash, device, topology);
    REQUIRE(cache.load() && !cache.record());
    REQUIRE(cache.save(-10000, source, rf, ns));
    REQUIRE(cache.sequence() == 1);
    REQUIRE(!cache.save(-11000, source, {}, 299 * ns));
    REQUIRE(cache.save(-11000, source, {}, 301 * ns));
    REQUIRE(cache.record()->rf == rf);
    auto bad_rf = rf;
    bad_rf.uncertainty_ppb = 5001;
    REQUIRE(!cache.save(-12000, source, bad_rf, 1000 * ns));
    REQUIRE(cache.healthy());
    bad_rf = rf;
    bad_rf.utc_rate_ppb = -100000;
    REQUIRE(!cache.save(-12000, source, bad_rf, 1000 * ns));
    // A transient strict RF result survives cooldown and later UTC-only updates.
    network_test::Flash staged_flash;
    Cache staged(staged_flash, device, topology);
    REQUIRE(staged.load() && staged.save(-1000, source, {}, ns));
    REQUIRE(staged.stage({}, source, rf));
    REQUIRE(!staged.flush(2 * ns));
    REQUIRE(staged.stage(-2000, source, {}));
    REQUIRE(staged.flush(301 * ns) && staged.record()->rf == rf);
    network_test::Flash rf_only_flash;
    Cache rf_only(rf_only_flash, device, topology);
    REQUIRE(rf_only.load() && rf_only.stage({}, source, rf) && rf_only.flush(0));
    REQUIRE(rf_only.record()->rf == rf);
    Cache cold(flash, device, topology);
    REQUIRE(cold.load() && cold.record()->utc_rate_ppb == -11000);
    REQUIRE(cold.record()->rf == rf);
    // Migrate an actual version-1 payload, preserving RF provenance and
    // broadening its unavailable UTC skew instead of inventing confidence.
    standalone::Journal current_journal(flash, 0, 256);
    REQUIRE(current_journal.load(true));
    const auto& current = current_journal.data();
    auto legacy = current.substr(0, 46);
    legacy[4] = 1;
    legacy += char(1);
    legacy += current.substr(46, 4);
    legacy += current.substr(54, 60);
    legacy += current.substr(114, 9);
    legacy += current.substr(123, 1) + std::string(3, '\0');
    legacy += current.substr(124);
    network_test::Flash legacy_flash;
    standalone::Journal legacy_journal(legacy_flash, 0, 256);
    REQUIRE(legacy_journal.load(true) && legacy_journal.append(legacy));
    Cache migrated(legacy_flash, device, topology);
    REQUIRE(migrated.load() && migrated.record()->utc_rate_ppb == -11000);
    REQUIRE(migrated.record()->utc_skew_ppb == 2'000'000 && migrated.record()->rf == rf);
    REQUIRE(migrated.save(-11000, source, {}, 0, 1000)); // Significant skew improvement.
    Cache migrated_cold(legacy_flash, device, topology);
    REQUIRE(migrated_cold.load() && migrated_cold.record()->utc_skew_ppb == 1000);
    REQUIRE(migrated_cold.record()->rf == rf);
    Cache foreign(flash, std::string(32, 'c'), topology);
    REQUIRE(!foreign.load() && !foreign.record());
    REQUIRE(!foreign.save(1000, source, {}, 1000 * ns));
    Cache incompatible(flash, device, topology + 1);
    REQUIRE(!incompatible.load());
    // A saved slope cannot establish UTC or resurrect calibration history.
    std::uint64_t raw = 0;
    time::UtcDiscipline clock(now, &raw, standalone::clock_profile());
    time::Sntp ntp(clock);
    ntp.seed_rate(cold.record()->utc_rate_ppb);
    REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    for (unsigned i = 0; i < 3; ++i) {
        const auto request = ntp.request(raw, i + 1);
        raw += 2'000'000;
        REQUIRE(ntp.receive(ntp_reply(request, epoch + raw - 1'000'000), raw));
        if (i < 2)
            REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
        raw += 64 * ns;
    }
    REQUIRE(ntp.control_model().learned && ntp.rate(raw).qualified);
    ntp.reset_peer();
    REQUIRE(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    REQUIRE(!ntp.rate(raw).qualified);
    // The manual value and cache are independent media and authorities.
    network_test::Flash manual_flash;
    standalone::Store store(manual_flash);
    REQUIRE(store.load());
    auto config = *standalone::parse_config(network_test::config);
    config.manual_correction_ppb = 12345;
    REQUIRE(store.save(config));
    standalone::Store manual_cold(manual_flash);
    REQUIRE(manual_cold.load() && manual_cold.config()->manual_correction_ppb == 12345);
    struct Torn : network_test::Flash {
        bool fail = false;
        bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
            if (!fail)
                return Flash::program(offset, page);
            std::copy_n(page.begin(), 128, bytes.begin() + offset);
            return false;
        }
    };
    for (unsigned writes : {1U, 16U, 32U}) {
        Torn media;
        Cache first(media, device, topology);
        REQUIRE(first.load());
        for (unsigned i = 0; i < writes; ++i)
            REQUIRE(first.save(-10000 + int(i) * 100, source, rf, (1 + i * 300) * ns));
        const auto retained = first.record()->utc_rate_ppb;
        media.fail = true;
        REQUIRE(!first.save(20000, source, {}, (1 + writes * 300) * ns));
        media.fail = false;
        Cache recovered(media, device, topology);
        REQUIRE(recovered.load() && recovered.record()->utc_rate_ppb == retained);
        REQUIRE(recovered.record()->rf == rf);
    }
    // Unknown cache versions never make operational configuration unhealthy.
    standalone::Journal journal(flash, 0, 256);
    REQUIRE(journal.load(true));
    auto unknown = journal.data();
    unknown[4] = 3;
    REQUIRE(journal.append(unknown));
    Cache future(flash, device, topology);
    REQUIRE(!future.load() && manual_cold.healthy());
    REQUIRE(future.erase() && future.erased());
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
    REQUIRE(clock.snapshot().state == wtp::ClockState::Holdover);
    raw += 3420 * ns;
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
    // Separate cache media avoids aliasing the real config journal in this test.
    network_test::Flash learned_flash;
    standalone::NtpRetention cached(learned_flash, std::string(32, 'a'), 138000000);
    REQUIRE(cached.load());
    standalone::NtpRetention::Provenance provenance{std::string(32, 'b'), 1, 1, 1, epoch};
    REQUIRE(cached.save(-10000, provenance,
                        standalone::NtpRetention::RfPrior{-10000, 1000, 32, 2000 * ns, provenance},
                        0));
    // A legacy opt-in and retained RF prior have no route to the RF engine.
    engine.calibration_boundary();
    REQUIRE(engine.prepare(job).accepted && raw.correction == -10000);
    REQUIRE(engine.calibration_status(clock.now).find("\"saved_ntp_available\":false") !=
            std::string::npos);
    REQUIRE(engine.calibration_status(clock.now).find("ntp_rf_rejected") != std::string::npos);
    REQUIRE(engine.calibration_status(clock.now).find("\"next_source\":\"manual\"") !=
            std::string::npos);
    REQUIRE(
        engine.calibration_status(clock.now + time::ntp_fresh_ns + 1).find("\"next_ppb\":-10000") !=
        std::string::npos);
    REQUIRE(cached.record()->rf.has_value()); // Historical bytes stay readable, never applied.
    c.manual_correction_ppb = 0;
    c.ntp_rf_calibration = false;
    REQUIRE(store.save(c));
    engine.calibration_boundary();
    REQUIRE(engine.prepare(job).accepted && raw.correction == 0);
}
} // namespace
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "packet-evidence") {
        diagnostic_pages(true);
        return 0;
    }
    if ((argc == 6 || argc == 8) && std::string_view(argv[1]) == "map") {
        wtp::ClockSnapshot anchor;
        anchor.monotonic_now_ns = std::stoull(argv[2]);
        anchor.utc_now_ns = std::stoull(argv[3]);
        anchor.rate_ppb = std::stoi(argv[4]);
        if (argc == 8) {
            anchor.rate_until_monotonic_ns = std::stoull(argv[6]);
            anchor.subsequent_rate_ppb = std::stoi(argv[7]);
        }
        std::uint64_t raw{}, projected{};
        if (!time::inverse(anchor, std::stoull(argv[5]), raw) ||
            !time::project(anchor, raw, projected))
            std::cout << "invalid\n";
        else
            std::cout << raw << " " << projected << "\n";
        return 0;
    }
    manual();
    model_import();
    diagnostic_pages();
    selected_source_freshness();
    retention();
    mapping();
    freeze();
    std::cout << "NTP work deterministic checks passed\n";
}

#include "application/resources.hpp"
#include "network/local_usb_api.hpp"
#include "network_support.hpp"
#include "standalone/message_schedule.hpp"

#include <cassert>
#include <iostream>
using namespace wsprrypico;
namespace {
constexpr std::uint64_t ns = 1'000'000'000ULL;
standalone::MessageSchedule schedule(std::uint64_t first, unsigned period = 60) {
    standalone::MessageSchedule s;
    s.enabled = true;
    s.first_start_utc_ns = first;
    s.period_s = period;
    s.message.job_id = std::string(32, '0');
    s.message.mode = "qrss";
    s.message.text = "E";
    s.message.mark_frequency_nhz = 10140000000000000ULL;
    s.message.dot_ns = ns;
    s.message.dash_ns = 3 * ns;
    s.message.intra_gap_ns = ns;
    s.message.character_gap_ns = 3 * ns;
    s.message.word_gap_ns = 7 * ns;
    s.message.repeat_count = 1;
    s.message.allow_frequency_adjustment = true;
    return s;
}
network::HttpResponse call(network_test::Fixture& f, std::string method, std::string path,
                           std::string body = {}, std::string revision = {}) {
    network::HttpRequest r;
    r.method = std::move(method);
    r.path = std::move(path);
    r.body = std::move(body);
    r.headers = {{"host", "127.0.0.1:8443"},
                 {"origin", "https://127.0.0.1:8443"},
                 {"x-wsprrypico-request", "1"},
                 {"content-type", "application/json"}};
    if (!revision.empty())
        r.headers["if-match"] = revision;
    auto result = f.api.handle(network_test::control_request(r), "peer", "127.0.0.1:8443");
    if (result.status >= 400 && r.path == "/api/control/v1/jobs")
        std::cerr << result.status << ": " << result.body << std::endl;
    return result;
}
std::string envelope(network_test::Fixture& f, const standalone::MessageSchedule& s) {
    return "{\"schema\":\"message-schedule\",\"target\":" +
           application::target(std::string(32, 'a'), f.service.status().boot_id) +
           ",\"schedule\":" + standalone::serialize_message_schedule(s) + "}";
}
void advance(network_test::Fixture& f, std::uint64_t monotonic) {
    f.clock.now = monotonic;
    f.scheduler.poll();
}
} // namespace
int main() {
    using Daylight = hardware::GpsSettings::Daylight;
    const auto anchor = 1793001605000000000ULL;
    {
        network_test::Fixture f;
        auto config = *standalone::parse_config(network_test::config);
        assert(f.store.save(config));
        const auto before = call(f, "GET", "/api/control/v1/gray-line");
        const auto bytes = f.flash.bytes;
        const auto sequence = f.store.config_sequence();
        const auto target = application::target(std::string(32, 'a'), f.service.status().boot_id);
        for (unsigned fault = 0; fault < 4; ++fault) {
            auto settings = standalone::GrayLine{};
            if (fault == 0)
                settings.morning.wspr_dial_frequency_hz = 1'234'567;
            if (fault == 1)
                settings.evening.message_frequency_nhz = 1;
            if (fault == 2)
                settings.morning.message_frequency_nhz = UINT64_MAX;
            if (fault == 3)
                settings.evening.wspr_dial_frequency_hz = 159'998'496;
            const auto json = standalone::serialize_gray_line(settings);
            const auto body =
                "{\"schema\":\"gray-line\",\"target\":" + target + ",\"settings\":" + json + "}";
            const auto refused = call(f, "PUT", "/api/control/v1/gray-line", body, before.etag);
            assert(refused.status == 400);
            assert(refused.body.find("frequency_not_allowed") != std::string::npos);
            const auto update = "{\"schema\":\"config-update\",\"target\":" + target +
                                ",\"mode\":\"merge\",\"config\":{\"gray_line\":" + json + "}}";
            assert(call(f, "POST", "/api/control/v1/config/update", update, before.etag).status ==
                   400);
            config.gray_line = settings;
            assert(f.scheduler.command("CONFIG " + standalone::serialize_config(config))
                       .find("frequency_not_allowed") != std::string::npos);
            assert(f.flash.bytes == bytes && f.store.config_sequence() == sequence);
            assert(call(f, "GET", "/api/control/v1/gray-line").etag == before.etag);
        }
        auto settings = standalone::GrayLine{};
        settings.morning.wspr_dial_frequency_hz = 1'234'567;
        settings.evening.message_frequency_nhz = 1'234'567'000'000'000ULL;
        const auto update = "{\"schema\":\"config-update\",\"target\":" + target +
                            ",\"mode\":\"merge\",\"config\":{\"allow_unqualified_frequency\":true,"
                            "\"allow_non_amateur_frequency\":true,\"gray_line\":" +
                            standalone::serialize_gray_line(settings) + "}}";
        assert(call(f, "POST", "/api/control/v1/config/update", update, before.etag).status == 200);
        assert(f.store.config()->gray_line == settings && !f.store.config()->enabled);
        // Restored values can become unusable under another engine/policy.
        // Disabling that period must not require replacing its saved frequency.
        config = *f.store.config();
        config.gray_line.evening.enabled = true;
        config.gray_line.evening.message_frequency_nhz = UINT64_MAX;
        assert(f.store.save(config));
        const auto restored = call(f, "GET", "/api/control/v1/gray-line");
        config.gray_line.evening.enabled = false;
        const auto disable =
            "{\"schema\":\"gray-line\",\"target\":" + target + ",\"settings\":" +
            standalone::serialize_gray_line(config.gray_line) + "}";
        assert(call(f, "PUT", "/api/control/v1/gray-line", disable, restored.etag).status == 200);
        assert(f.store.config()->gray_line == config.gray_line);
    }
    {
        network_test::Fixture f;
        auto config = standalone::parse_config(network_test::config);
        assert(config);
        config->enabled = false;
        config->ssid = std::string(32, 's');
        config->password = std::string(63, 'p');
        config->ntp_ipv4 = std::string(29, 'n') + ".example.test";
        config->schedules.clear();
        for (unsigned i = 0; i < 8; ++i)
            config->schedules.push_back({86400, (712 + i) * 120});
        auto message = schedule(anchor, 3600);
        message.enabled = false;
        message.message.text = std::string(32, 'E');
        hardware::FilterSettings filters;
        filters.output_count = 3;
        filters.range_count = 8;
        for (unsigned i = 0; i < filters.output_count; ++i)
            filters.outputs[i] = {i + 1, 10 + i, "Filter GPIO " + std::to_string(i + 1), true};
        for (unsigned i = 0; i < filters.range_count; ++i)
            filters.ranges[i] = {"Beacon band " + std::to_string(i + 1), i % 3 + 1,
                                 100'000 * (i + 1), 100'000 * (i + 1) + 1'000};
        assert(f.store.save(*config));
        assert(f.store.save_message_schedule(message));
        assert(f.store.save_filters(filters));
        const auto payload_size = [&] {
            const auto offset = f.store.config_offset();
            return f.flash.bytes[offset + 16] + 256u * f.flash.bytes[offset + 17];
        };
        assert(payload_size() == standalone::Store::max_state_bytes);
        {
            auto settings = standalone::GrayLine{};
            settings.morning.enabled = true;
            const auto read = call(f, "GET", "/api/control/v1/gray-line");
            assert(read.status == 200);
            const auto sequence = f.store.config_sequence();
            const auto bytes = f.flash.bytes;
            const auto edit =
                "{\"schema\":\"gray-line\",\"target\":" +
                application::target(std::string(32, 'a'), f.service.status().boot_id) +
                ",\"settings\":" + standalone::serialize_gray_line(settings) + "}";
            assert(call(f, "PUT", "/api/control/v1/gray-line", edit, read.etag).status == 413);
            assert(f.store.config_sequence() == sequence && f.flash.bytes == bytes);
            assert(call(f, "PUT", "/api/control/v1/gray-line", std::string(2049, 'x'), read.etag)
                       .status == 413);
            assert(f.store.config_sequence() == sequence && f.flash.bytes == bytes);
        }

        const auto target = application::target(std::string(32, 'a'), f.service.status().boot_id);
        for (const auto policy : {hardware::GpsSettings::Daylight::DayManual,
                                  hardware::GpsSettings::Daylight::NightManual,
                                  hardware::GpsSettings::Daylight::Always}) {
            const auto get = call(f, "GET", "/api/control/v1/config");
            config->gps.reset();
            if (policy != hardware::GpsSettings::Daylight::Always) {
                config->gps = hardware::GpsSettings{};
                config->gps->daylight = policy;
            }
            const auto gps = config->gps ? hardware::serialize_gps(*config->gps) : "null";
            const auto result = call(
                f, "POST", "/api/control/v1/config/update",
                "{\"schema\":\"config-update\",\"target\":" + target +
                    ",\"mode\":\"merge\",\"config\":{\"gps\":" + gps + "}}",
                get.etag);
            assert(result.status == 200);
            assert(payload_size() <= standalone::Store::max_state_bytes);
            standalone::Store restored(f.flash);
            assert(restored.load());
            assert(restored.config() && standalone::serialize_config(*restored.config()) ==
                   standalone::serialize_config(*config));
            assert(restored.message_schedule() &&
                   standalone::serialize_message_schedule(*restored.message_schedule()) ==
                       standalone::serialize_message_schedule(message));
            assert(restored.filters() == filters);
        }
        const auto before = f.store.config_sequence();
        const auto get = call(f, "GET", "/api/control/v1/config");
        const auto invalid = call(
            f, "POST", "/api/control/v1/config/update",
            "{\"schema\":\"config-update\",\"target\":" + target +
                ",\"mode\":\"merge\",\"config\":{\"gps\":\"day_manual\"}}",
            get.etag);
        assert(invalid.status == 400 && f.store.config_sequence() == before);

        network_test::Flash old_flash;
        standalone::Journal old_journal(old_flash, 0, 2048);
        assert(old_journal.load());
        config->gps = hardware::GpsSettings{};
        config->gps->daylight = hardware::GpsSettings::Daylight::DayManual;
        const auto old_config = standalone::serialize_config(*config);
        assert(old_journal.append(old_config));
        standalone::Store restored(old_flash);
        assert(restored.load() && restored.config());
        assert(standalone::serialize_config(*restored.config()) == old_config);

        network_test::Flash legacy_flash;
        standalone::Journal legacy(legacy_flash, 0, 2048);
        assert(legacy.load());
        const auto gps = hardware::serialize_gps(*config->gps);
        auto prior_candidate = old_config;
        prior_candidate.replace(prior_candidate.find(gps), gps.size(), "\"day_manual\"");
        assert(legacy.append(prior_candidate));
        standalone::Store migrated(legacy_flash);
        assert(migrated.load() && migrated.config() == config);

        config->ntp_timeout_s = 0;
        config->gps->receiver = hardware::GpsSettings::Receiver::E108;
        config->gps->daylight = hardware::GpsSettings::Daylight::NightManual;
        assert(migrated.save(*config));
        assert(migrated.load() && migrated.config() == config);
        auto base = *config;
        base.gps.reset();
        auto stored = standalone::serialize_config(base);
        stored.replace(0, std::string_view("{\"version\":2").size(), "{\"beacon\":0");
        for (const auto& corrupt : {
                 std::string{"{\"beacon\":5"} + stored.substr(std::string_view("{\"beacon\":0").size()),
                 stored.substr(0, stored.size() - 1) + ",\"gps\":null}",
                 stored.substr(0, stored.size() - 1) + ",\"gps\":{\"daylight\":\"always\"}}",
                 stored.substr(0, stored.size() - 1) + ",\"gps\":{\"enabled\":\"false\"}}",
                 stored.substr(0, stored.size() - 1) + ",\"version\":2}"}) {
            network_test::Flash damaged;
            standalone::Journal invalid(damaged, 0, 2048);
            assert(invalid.load() && invalid.append(corrupt));
            standalone::Store refused(damaged);
            assert(!refused.load());
        }
    }
    {
        // A legacy full GPS record can fill flash even though its radio settings
        // are small enough for the settings API. Changing policy must still fit.
        network_test::Fixture f;
        auto config = *standalone::parse_config(network_test::config);
        config.ssid = std::string(32, 's');
        config.password = std::string(63, 'p');
        config.ntp_ipv4 = std::string(59, 'n') + "." + std::string(51, 'n');
        config.schedules.clear();
        for (unsigned i = 0; i < 8; ++i)
            config.schedules.push_back({86400, (712 + i) * 120});
        config.gps.emplace();
        config.gps->enabled = true;
        config.gps->daylight = Daylight::Day;
        auto message = schedule(anchor, 3600);
        message.enabled = false;
        message.message.text = std::string(32, 'E');
        hardware::FilterSettings filters;
        filters.output_count = 3;
        filters.range_count = 1;
        for (unsigned i = 0; i < 3; ++i)
            filters.outputs[i] = {i + 1, 10 + i, "Filter GPIO " + std::to_string(i + 1), true};
        filters.ranges[0] = {"Beacon band 1", 1, 100'000, 101'000};
        const auto legacy = "{\"schema\":\"standalone-state/4\",\"config\":" +
            standalone::serialize_config(config) + ",\"message_schedule\":" +
            standalone::serialize_message_schedule(message) +
            ",\"logging\":{\"enabled\":false,\"maximum_severity\":6},\"filter_selector\":" +
            hardware::serialize_filters(filters) + "}";
        assert(legacy.size() == 1982);
        standalone::Journal journal(f.flash, 0, 2048);
        assert(journal.load() && journal.append(legacy) && f.store.load());
        const auto target = application::target(std::string(32, 'a'), f.service.status().boot_id);
        for (const auto policy : {Daylight::DayManual, Daylight::NightManual,
                                  Daylight::Always, Daylight::Night, Daylight::Day}) {
            const auto get = call(f, "GET", "/api/control/v1/config");
            config.gps->daylight = policy;
            const auto saved = call(f, "POST", "/api/control/v1/config/update",
                "{\"schema\":\"config-update\",\"target\":" + target +
                ",\"mode\":\"merge\",\"config\":{\"gps\":" + hardware::serialize_gps(*config.gps) + "}}",
                get.etag);
            assert(saved.status == 200);
            standalone::Store restored(f.flash);
            assert(restored.load() && restored.config() == config && restored.filters() == filters);
            assert(restored.message_schedule() &&
                   standalone::serialize_message_schedule(*restored.message_schedule()) ==
                       standalone::serialize_message_schedule(message));
        }
    }
    {
        network_test::Fixture f;
        auto config = *standalone::parse_config(network_test::config);
        config.ssid = std::string(32, '"');
        config.password = std::string(63, '"');
        config.ntp_ipv4 = std::string(63, 'a') + "." + std::string(63, 'b') + "." +
                          std::string(63, 'c') + "." + std::string(61, 'd');
        config.schedules.clear();
        for (unsigned i = 0; i < 8; ++i)
            config.schedules.push_back({86400, (712 + i) * 120});
        config.locator = "EM18AX";
        config.power_dbm = 60;
        config.expires_utc_s = 1800000001;
        config.allow_unqualified_frequency = config.allow_non_amateur_frequency = true;
        config.gpio_drive_ma = 12;
        config.manual_correction_ppb = -100000;
        config.ntp_rf_calibration = true;
        config.wspr_dial_frequency_hz = 14095600;
        config.ntp_timeout_s = 86400;
        config.amplifier_timing = {1000, 1000};
        config.pins.engine = hardware::PinPlan::Engine::I2c;
        config.pins.rf.reset();
        config.pins.i2c_pair = 1;
        config.pins.amplifier = 12;
        config.pins.amplifier_active_high = false;
        config.pins.indicator = hardware::PinPlan::Indicator::External;
        config.pins.indicator_gp = 13;
        config.pins.indicator_active_high = false;
        config.si5351.emplace();
        config.si5351->synthesis.reference_hz = 25000000;
        config.si5351->synthesis.reference = rf::si5351::Reference::ExternalXa;
        config.si5351->synthesis.drive_ma = 8;
        config.si5351->synthesis.loopback = rf::si5351::Output::Clk2;
        config.si5351->loopback_input = 7;
        config.si5351->gate_active_high = false;
        config.si5351->manual_correction_ppb = -100000;
        assert(standalone::serialize_config(config).size() == 1709);
        assert(f.store.save(config));
        const auto get = call(f, "GET", "/api/control/v1/config");
        config.gps.emplace();
        config.gps->daylight = Daylight::NightManual;
        assert(standalone::serialize_config(config).size() == 2145);
        const auto saved = call(f, "POST", "/api/control/v1/config/update",
            "{\"schema\":\"config-update\",\"target\":" +
            application::target(std::string(32, 'a'), f.service.status().boot_id) +
            ",\"mode\":\"merge\",\"config\":{\"gps\":" + hardware::serialize_gps(*config.gps) + "}}",
            get.etag);
        assert(saved.status == 200);
        standalone::Store restored(f.flash);
        assert(restored.load() && restored.config() == config);
        assert(!standalone::parse_config(std::string(4097, ' ')));
    }
    for (const unsigned minutes : {7U, 20U, 90U}) {
        const auto s = schedule(anchor, minutes * 60);
        const auto period = std::uint64_t{minutes} * 60 * ns;
        assert(standalone::next_message_slot(s, anchor, 0) == anchor);
        assert(standalone::next_message_slot(s, anchor + 1, 0) == anchor + period);
        assert(standalone::next_message_slot(s, anchor + period, anchor + period) ==
               anchor + 2 * period);
        assert(standalone::next_message_slot(s, anchor + 86400 * ns, 0) ==
               anchor + ((86400 * ns + period - 1) / period) * period);
        assert(!standalone::next_message_slot(s, anchor, UINT64_MAX));
    }
    {
        auto s = schedule(anchor);
        s.message.mode = "dfcw";
        s.message.space_frequency_nhz = s.message.mark_frequency_nhz + 5 * ns;
        const auto encoded = standalone::serialize_message_schedule(s);
        assert(standalone::parse_message_schedule(*wtp::json::parse(encoded)));
        s.message.text = "E\tE";
        const auto control = standalone::serialize_message_schedule(s);
        assert(!standalone::parse_message_schedule(*wtp::json::parse(control)));
        s.message.text = "E";
        s.message.space_frequency_nhz = s.message.mark_frequency_nhz - 5 * ns;
        const auto negative = standalone::serialize_message_schedule(s);
        assert(!standalone::parse_message_schedule(*wtp::json::parse(negative)));
    }
    {
        network_test::Fixture f;
        const auto s = schedule(f.clock.snapshot().utc_now_ns + 60 * ns);
        assert(f.store.save_message_schedule(s));
        f.flash.fail = true;
        advance(f, 56 * ns);
        assert(f.service.status().state == wtp::State::Empty);
        assert(!f.store.healthy() && f.scheduler.message_recovery_required());
    }
    struct SolarCase {
        const char* grid;
        std::uint64_t utc_s;
        Daylight policy;
        bool allowed;
    };
    // In Arctic summer only the day policy can start. At 06:00 UTC near
    // the equinox, the east and west edges of JJ00 fall on opposite sides
    // of sunrise. Using only the first four characters would miss this.
    for (const auto& [grid, utc_s, policy, allowed] : {
             SolarCase{"RR99XX", 1'782'043'200, Daylight::DayManual, true},
             SolarCase{"RR99XX", 1'782'043'200, Daylight::NightManual, false},
             SolarCase{"JJ00AA", 1'773'986'400, Daylight::DayManual, false},
             SolarCase{"JJ00XA", 1'773'986'400, Daylight::DayManual, true}}) {
        network_test::Fixture f;
        auto config = standalone::parse_config(network_test::config);
        assert(config);
        config->locator = grid;
        config->gps.emplace();
        config->gps->daylight = policy;
        assert(f.store.save(*config));
        assert(f.store.load());
        assert(!f.store.config()->gps->enabled && f.store.config()->gps->daylight == policy);
        f.clock.utc = utc_s * ns;
        const auto start = f.clock.snapshot().utc_now_ns + 5 * ns;
        assert(f.store.save_message_schedule(schedule(start)));
        assert(f.scheduler.next_message_start().has_value() == allowed);
        const auto observed = call(f, "GET", "/api/control/v1/message-schedule");
        assert(observed.status == 200);
        const auto body = wtp::json::parse(observed.body);
        assert(body && body->get("state")->string() ==
                           (allowed ? "waiting" : "waiting_for_beacon_window"));
        assert((body->get("next_start_utc_ns")->raw != "null") == allowed);
        f.scheduler.poll();
        assert(f.service.status().state == (allowed ? wtp::State::Armed : wtp::State::Empty));
        assert(f.store.message_in_flight() == allowed);
    }
    {
        network_test::Fixture f;
        auto config = standalone::parse_config(network_test::config);
        assert(config);
        config->gps.emplace();
        config->gps->enabled = true;
        config->gps->daylight = Daylight::Day;
        assert(f.store.save(*config));
        const auto start = f.clock.snapshot().utc_now_ns + 5 * ns;
        auto message = schedule(start);
        assert(f.store.save_message_schedule(message));
        const auto status = [&] {
            const auto text = f.scheduler.message_status();
            const auto body = wtp::json::parse(text);
            assert(body && body->get("next_start_utc_ns")->raw == "null");
            return body->get("state")->string();
        };
        assert(status() == "waiting_for_gps_fix");
        f.clock.now = 31 * ns;
        f.scheduler.gps_position(time::gps::Position{0, 0, 0});
        assert(status() == "waiting_for_gps_fix");
        message.expires_utc_s = start / ns + 2;
        assert(f.store.save_message_schedule(message));
        assert(status() == "expired");
    }
    {
        auto s = schedule(anchor);
        auto encoded = standalone::serialize_message_schedule(s);
        assert(standalone::parse_message_schedule(*wtp::json::parse(encoded)));
        s.message.text = std::string(33, 'E');
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.message.dot_ns = 59 * ns; // Tail and preparation cannot fit a minute.
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.period_s = 61;
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.expires_utc_s = anchor / ns + 1;
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.message.repeat_count = 512;
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
    }
    {
        network_test::Fixture f;
        auto c = standalone::parse_config(network_test::config);
        assert(c && f.store.save(*c));
        auto s = schedule(f.clock.snapshot().utc_now_ns + 5 * ns);
        assert(f.store.save_message_schedule(s));
        auto changed = *c;
        changed.locator = "EM19";
        assert(f.store.save(changed));
        standalone::Store loaded(f.flash);
        assert(loaded.load());
        assert(loaded.config()->locator == "EM19" && loaded.message_schedule()->enabled);
        c->enabled = true;
        assert(!f.store.save(*c));
        f.scheduler.poll();
        assert(f.service.status().state == wtp::State::Armed && f.store.message_in_flight());
        const auto first = f.store.watermark();
        network_test::Fixture reboot;
        reboot.flash.bytes = f.flash.bytes;
        assert(reboot.store.load());
        assert(reboot.scheduler.message_recovery_required());
        reboot.scheduler.poll();
        assert(reboot.service.status().state == wtp::State::Empty);
        assert(reboot.scheduler.pause_message());
        assert(!reboot.store.message_in_flight() && !reboot.store.message_schedule()->enabled);
        advance(f, 6 * ns);
        assert(f.service.status().state == wtp::State::Running);
        assert(f.scheduler.pause_message() && f.scheduler.message_pause_pending());
        assert(f.service.status().state == wtp::State::Running &&
               f.store.message_schedule()->enabled);
        advance(f, 7 * ns + 1000);
        assert(!f.store.message_in_flight());
        assert(!f.store.message_schedule()->enabled && !f.scheduler.message_pause_pending());
        advance(f, 126 * ns);
        assert(f.store.watermark() == first);
    }
    {
        network_test::Fixture f;
        auto s = schedule(f.clock.snapshot().utc_now_ns + 5 * ns);
        s.expires_utc_s = s.first_start_utc_ns / ns + 65;
        assert(f.store.save_message_schedule(s));
        f.scheduler.poll();
        const auto first = f.store.watermark();
        advance(f, 6 * ns);
        advance(f, 7 * ns + 1000);
        assert(!f.store.message_in_flight());
        advance(f, 61 * ns);
        assert(f.service.status().state == wtp::State::Armed &&
               f.store.watermark() == first + 60 * ns);
        advance(f, 66 * ns);
        advance(f, 67 * ns + 1000);
        advance(f, 121 * ns);
        assert(f.store.watermark() == first + 60 * ns);
        assert(f.scheduler.message_status().find("expired") != std::string::npos);
    }
    {
        network_test::Fixture f;
        auto s = schedule(f.clock.snapshot().utc_now_ns + 5 * ns);
        assert(f.store.save_message_schedule(s));
        f.scheduler.poll();
        advance(f, 8 * ns); // Miss launch window: must retain a recovery barrier.
        assert(f.store.message_in_flight() && f.scheduler.message_recovery_required());
        const auto consumed = f.store.watermark();
        advance(f, 61 * ns);
        assert(f.store.watermark() == consumed);
    }
    {
        network_test::Fixture f;
        auto c = standalone::parse_config(network_test::config);
        assert(c && f.store.save(*c));
        f.flash.fail = true;
        assert(!f.store.save_message_schedule(schedule(anchor)));
        standalone::Store after(f.flash);
        assert(after.load() && !after.message_schedule()); // Refusal before the first page
                                                           // preserves the legacy record.
    }
    {
        struct CutFlash : network_test::Flash {
            int remaining = -1;
            bool program(std::size_t offset, std::span<const std::uint8_t> data) override {
                if (remaining == 0)
                    return false;
                if (remaining > 0)
                    --remaining;
                return network_test::Flash::program(offset, data);
            }
        };
        for (int cut = 0; cut < 8; ++cut) {
            CutFlash flash;
            standalone::Store store(flash);
            assert(store.load());
            auto c = standalone::parse_config(network_test::config);
            assert(c && store.save(*c));
            flash.remaining = cut;
            assert(!store.save_message_schedule(schedule(anchor)));
            standalone::Store reboot(flash);
            if (cut == 0)
                assert(reboot.load() && !reboot.message_schedule());
            else
                assert(!reboot.load());
        }
    }
    {
        network_test::Fixture f;
        auto s = schedule(f.clock.snapshot().utc_now_ns + 60 * ns);
        assert(f.store.save_message_schedule(s));
        const auto session = std::string(32, 'b');
        assert(call(f, "POST", "/api/control/v1/jobs",
                    "{\"session_id\":\"" + session + "\",\"request_id\":\"" + std::string(32, 'c') +
                        "\",\"operation\":\"HELLO\",\"body\":{\"versions\":[\"WTP/"
                        "1\"],\"client_name\":\"test\",\"client_version\":\"1\"}}")
                   .status == 200);
        assert(call(f, "POST", "/api/control/v1/jobs",
                    "{\"session_id\":\"" + session + "\",\"request_id\":\"" + std::string(32, 'd') +
                        "\",\"operation\":\"CLAIM\",\"body\":{\"owner_id\":\"" + session +
                        "\",\"lease_ms\":60000}}")
                   .status == 200);
        advance(f, 56 * ns);
        assert(f.store.watermark() == 0 && f.service.status().owner_id == session);
        assert(f.scheduler.pause_message() && f.scheduler.message_pause_pending());
        assert(f.service.status().owner_id == session); // Pausing never releases another owner.
        advance(f, 65 * ns);
        assert(!f.store.message_schedule()->enabled);
    }
    {
        network_test::Fixture f;
        assert(f.scheduler.command("STOP").find("true") != std::string::npos);
        assert(f.scheduler.pause_message());
        assert(f.scheduler.suspended()); // No phantom resume.
    }
    {
        network_test::Fixture f;
        auto read = call(f, "GET", "/api/control/v1/message-schedule");
        assert(read.status == 200);
        auto s = schedule(f.clock.snapshot().utc_now_ns + 60 * ns);
        const auto body = envelope(f, s);
        assert(call(f, "PUT", "/api/control/v1/message-schedule", body).status == 428);
        assert(call(f, "PUT", "/api/control/v1/message-schedule", body, "\"wrong\"").status == 412);
        auto wrong = body;
        wrong.replace(wrong.find(std::string(32, 'a')), 32, std::string(32, 'b'));
        assert(call(f, "PUT", "/api/control/v1/message-schedule", wrong, read.etag).status == 409);
        auto unknown = body;
        unknown.insert(1, "\"unknown\":true,");
        assert(call(f, "PUT", "/api/control/v1/message-schedule", unknown, read.etag).status == 400);
        assert(
            call(f, "PUT", "/api/control/v1/message-schedule", std::string(2049, 'x'), read.etag).status ==
            413);
        network::LocalUsbApi usb(f.api);
        network::HttpRequest request;
        request.path = "/api/control/v1/message-schedule";
        request.method = "GET";
        assert(usb.handle(network_test::control_request(request)).status == 200);
        const auto accepted = call(f, "PUT", "/api/control/v1/message-schedule", body, read.etag);
        assert(accepted.status == 200);
        assert(accepted.etag != read.etag);
        assert(call(f, "PUT", "/api/control/v1/message-schedule", body, read.etag).status == 412);
        network::HttpRequest anonymous;
        anonymous.method = "GET";
        anonymous.path = "/api/control/v1/message-schedule";
        assert(f.api.handle(network_test::control_request(anonymous), "", "127.0.0.1:8443").status != 200);
        const auto pause = "{\"schema\":\"message-schedule\",\"target\":" +
                           application::target(std::string(32, 'a'), f.service.status().boot_id) +
                           ",\"pause\":true}";
        assert(call(f, "POST", "/api/control/v1/message-schedule/pause", pause, accepted.etag).status ==
               200);
        assert(!f.store.message_schedule()->enabled);
    }
    std::cout << "UTC recurrence, persistence, dispatch recovery, expiry, deferred pause and API "
                 "admission passed\n";
}

// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/si5351_qualification.hpp"
#include "rf/si5351_engine.hpp"
#include "standalone/execution_profile.hpp"

namespace synthesis_tone_test {
using namespace wsprrypico;
struct Platform : rf::si5351::ExecutionPlatform {
    network_test::Clock& clock;
    explicit Platform(network_test::Clock& value) : clock(value) {}
    std::uint64_t now_ns() const override {
        return clock.now;
    }
    bool initialize() override {
        return true;
    }
    bool set_gate(bool) override {
        return true;
    }
    bool gate_active_or_unknown() const override {
        return false;
    }
    bool arm_cutoff(std::uint64_t end) override {
        return end > clock.now;
    }
    void cancel_cutoff() override {}
    bool pause_reference(std::uint64_t) override {
        return true;
    }
    void service_reference(bool) override {}
    void inhibit_reference() override {}
};
struct Bus : rf::si5351::Bus {
    network_test::Clock& clock;
    std::array<std::uint8_t, 256> registers{};
    unsigned operations = 0;
    bool unavailable = false, wrong_drive = false;
    explicit Bus(network_test::Clock& value) : clock(value) {}
    bool read(std::uint8_t reg, std::span<std::uint8_t> bytes, std::uint64_t end) override {
        ++operations;
        clock.now += (bytes.size() + 3) * 90'000;
        if (unavailable || clock.now > end)
            return false;
        std::copy_n(registers.begin() + reg, bytes.size(), bytes.begin());
        if (wrong_drive && reg == 16)
            bytes[0] ^= 1;
        return true;
    }
    bool write(std::uint8_t reg, std::span<const std::uint8_t> bytes, std::uint64_t end) override {
        ++operations;
        clock.now += (bytes.size() + 2) * 90'000;
        if (unavailable || clock.now > end)
            return false;
        std::copy(bytes.begin(), bytes.end(), registers.begin() + reg);
        if (reg == 177)
            registers[177] &= 0x5f;
        return true;
    }
};
struct Flash : network_test::Flash {
    unsigned writes = 0;
    bool erase(std::size_t offset) override {
        ++writes;
        return network_test::Flash::erase(offset);
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> bytes) override {
        ++writes;
        return network_test::Flash::program(offset, bytes);
    }
};
struct Settings {
    bool allow_unqualified_frequency = true;
    bool engineering = false;
    std::int32_t correction_ppb = 0;
};
struct Fixture {
    Flash flash;
    standalone::Store store{flash};
    network_test::Clock clock;
    Platform platform{clock};
    Bus bus{clock};
    rf::si5351::Device device{bus};
    standalone::Config config;
    const bool ordinary_profile;
    rf::si5351::Engine raw;
    standalone::FrequencyPolicyEngine policy;
    network_test::Identity identity;
    execution::JobService service;
    standalone::Scheduler scheduler;
    network_test::Network network;
    network::BrowserApi api;
    standalone::Config initialize(unsigned drive, Settings settings) {
        REQUIRE(store.load());
        auto selected = *standalone::parse_config(network_test::config);
        selected.pins.engine = hardware::PinPlan::Engine::I2c;
        selected.pins.rf.reset();
        selected.pins.i2c_pair = 1;
        selected.si5351.emplace();
        selected.si5351->synthesis = {settings.engineering ? 27'000'000u : 25'000'000u,
                                     rf::si5351::Reference::ExternalXa, {},
                                     rf::si5351::Output::Clk0, {}, drive};
        selected.si5351->manual_correction_ppb = settings.correction_ppb;
        selected.enabled = false;
        selected.callsign.clear();
        selected.locator.clear();
        selected.allow_unqualified_frequency = settings.allow_unqualified_frequency;
        REQUIRE(store.save(selected));
        return selected;
    }
    explicit Fixture(unsigned drive, Settings settings = {})
        : config(initialize(drive, settings)),
          ordinary_profile(hardware::si5351_ordinary_qualified(
              config.pins, *config.si5351, rf::sample_rate, store.filters())),
          raw(config.si5351->synthesis, device, platform, settings.engineering, nullptr, nullptr,
              nullptr, ordinary_profile),
          policy(raw, store, 8'000'000'000'000ULL, 160'000'000'000'000'000ULL, ordinary_profile),
          service(clock, policy, identity,
                  standalone::execution_profile(true, standalone::default_ntp_timeout_s,
                                          hardware::PinPlan::Engine::I2c, settings.engineering,
                                          ordinary_profile)),
          scheduler(store, service),
          api(service, store, scheduler, network, std::string(32, 'a'), "test") {
        REQUIRE(ordinary_profile != settings.engineering);
        REQUIRE(raw.disable(clock.now + 100'000'000));
        api.test_tone_policy(policy);
    }
    std::string target() {
        return application::target(std::string(32, 'a'), service.status(false).boot_id);
    }
    network::HttpResponse send(std::string method, std::string path, std::string body = {},
                               std::string revision = {}) {
        return api.handle({std::move(method),
                           std::move(path),
                           std::move(body),
                           {{"host", "127.0.0.1:8443"},
                            {"origin", "https://127.0.0.1:8443"},
                            {"content-type", "application/json"},
                            {"x-wsprrypico-request", "1"},
                            {"if-match", std::move(revision)}}},
                          "cert", "127.0.0.1:8443");
    }
    std::string body(bool start, unsigned drive, unsigned duration = 120000,
                     unsigned carrier_hz = 14'097'100) {
        return "{\"contract\":\"Wsprry-Control/1\",\"schema\":\"test-tone-" +
               std::string(start ? "start" : "review") + "\",\"target\":" + target() +
               (start ? ",\"request_id\":\"" + std::string(32, '1') + "\"" : "") +
               ",\"tone\":{\"engine\":\"si5351\",\"carrier_hz\":" + std::to_string(carrier_hz) +
               ",\"duration_ms\":" + std::to_string(duration) +
               (start ? ",\"expected_drive_ma\":" : ",\"proposed_drive_ma\":") +
               std::to_string(drive) + "}}";
    }
    network::HttpResponse status() {
        return send("GET", "/api/control/v1/test-tone/status?device_id=" + std::string(32, 'a') +
                               "&boot_id=" + service.status(false).boot_id +
                               "&request_id=" + std::string(32, '1'));
    }
    void advance(std::uint64_t at) {
        clock.now = at;
        service.poll();
        api.poll_test_tone();
    }
};
inline std::string job_field(const network::HttpResponse& response, std::string_view field) {
    const auto text = response.body_text();
    const auto document = execution::json::parse(text);
    REQUIRE(document);
    return document->get("job")->get(field)->string();
}
inline std::uint64_t launch(const network::HttpResponse& response) {
    std::uint64_t at = 0;
    const auto text = response.body_text();
    const auto document = execution::json::parse(text);
    REQUIRE(document);
    REQUIRE(execution::json::decimal(*document->get("job")->get("scheduled_monotonic_ns"), at));
    return at;
}
inline std::vector<std::string> exercise() {
    std::vector<std::string> documents;
    for (const unsigned drive : {2u, 4u, 6u, 8u}) {
        Fixture f(drive);
        const auto bytes = f.flash.bytes;
        const auto operations = f.bus.operations;
        auto review = f.send("POST", "/api/control/v1/test-tone/review", f.body(false, drive));
        REQUIRE(review.status == 200 &&
                review.body_text().find("\"admission\":\"ready\"") != std::string::npos);
        REQUIRE(f.bus.operations == operations && f.flash.bytes == bytes);
        REQUIRE(f.send("POST", "/api/control/v1/test-tone/start", f.body(true, drive, 9),
                       f.api.revision())
                    .status == 409);
        const auto revision = f.api.revision();
        auto accepted =
            f.send("POST", "/api/control/v1/test-tone/start", f.body(true, drive), revision);
        REQUIRE(accepted.status == 202);
        REQUIRE(accepted.body_text().find("\"synthesis_readback\":{\"epoch\":\"1\"") !=
                std::string::npos);
        REQUIRE(accepted.body_text().find("\"stage\":\"verified\"") != std::string::npos);
        REQUIRE(accepted.body_text().find("\"pad_readback\":null") != std::string::npos);
        const auto at = launch(accepted);
        f.advance(at);
        REQUIRE(job_field(f.status(), "phase") == "running");
        f.advance(at + 90'000'000'000ULL);
        REQUIRE(f.service.activity().owned); // Running after lease expiry; no renewal.
        f.advance(at + 120'001'000'000ULL);
        const auto done = f.status();
        REQUIRE(job_field(done, "outcome") == "completed");
        REQUIRE(done.body_text().find("\"output_inactive_confirmed\":true") != std::string::npos);
        REQUIRE(!f.service.activity().owned && !f.raw.output_active());
        REQUIRE(f.flash.bytes == bytes);
        documents.push_back(f.send("GET", "/api/control/v1/capabilities").body_text());
        documents.push_back(review.body_text());
        documents.push_back(accepted.body_text());
        documents.push_back(done.body_text());
        REQUIRE(f.send("POST", "/api/control/v1/test-tone/start", f.body(true, drive), revision)
                    .status == 202);
        auto changed = *f.store.config();
        changed.si5351->synthesis.drive_ma = drive == 2 ? 4 : 2;
        const auto update =
            "{\"contract\":\"Wsprry-Control/1\",\"schema\":\"config-update\",\"target\":" +
            f.target() +
            ",\"mode\":\"merge\",\"config\":{\"pins\":" + hardware::serialize_plan(changed.pins) +
            ",\"si5351\":" + hardware::serialize_si5351(*changed.si5351) + "}}";
        const auto saved =
            f.send("POST", "/api/control/v1/config/update", update, f.api.revision());
        if (saved.status != 200)
            std::cerr << saved.status << " " << saved.body_text() << "\n";
        REQUIRE(saved.status == 200);
        REQUIRE(f.store.config()->callsign.empty() && f.store.config()->locator.empty());
        REQUIRE(!f.store.config()->enabled && f.scheduler.reboot_required());
        REQUIRE(f.scheduler.active_si5351()->synthesis.drive_ma == drive);

        Fixture minimum(drive);
        auto shortest = minimum.send("POST", "/api/control/v1/test-tone/start",
                                     minimum.body(true, drive, 10), minimum.api.revision());
        REQUIRE(shortest.status == 202);
        const auto shortest_launch = launch(shortest);
        minimum.advance(shortest_launch);
        minimum.advance(shortest_launch + 11'000'000);
        REQUIRE(job_field(minimum.status(), "outcome") == "completed");
        for (const bool failed_bus : {false, true}) {
            Fixture stopped(drive);
            auto start = stopped.send("POST", "/api/control/v1/test-tone/start",
                                      stopped.body(true, drive), stopped.api.revision());
            REQUIRE(start.status == 202);
            stopped.advance(launch(start));
            stopped.bus.unavailable = failed_bus;
            auto stop = stopped.send(
                "POST", "/api/control/v1/test-tone/stop",
                "{\"contract\":\"Wsprry-Control/1\",\"schema\":\"test-tone-stop\",\"target\":" +
                    stopped.target() + ",\"job_id\":\"" + job_field(start, "job_id") + "\"}",
                start.etag);
            REQUIRE(stop.status == 200);
            REQUIRE(stop.body_text().find(failed_bus ? "\"recovery_required\":true"
                                                     : "\"output_inactive_confirmed\":true") !=
                    std::string::npos);
            REQUIRE(stopped.raw.output_active() == failed_bus);
        }
        Fixture wrong(drive);
        wrong.bus.wrong_drive = true;
        auto refused = wrong.send("POST", "/api/control/v1/test-tone/start",
                                  wrong.body(true, drive), wrong.api.revision());
        REQUIRE(refused.status == 202 && job_field(refused, "outcome") == "failed");
        REQUIRE(wrong.raw.synthesis_observation().epoch == 0);
    }
    return documents;
}
} // namespace synthesis_tone_test

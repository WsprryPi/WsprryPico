// SPDX-License-Identifier: MIT
#include "hardware/si5351_qualification.hpp"
#include "network_support.hpp"
#include "rf/si5351_observation.hpp"
#include "standalone/frequency_policy_engine.hpp"
#include "standalone/wtp_profile.hpp"

#include <iostream>

using namespace wsprrypico;
namespace {
hardware::Si5351Settings settings() {
    hardware::Si5351Settings value;
    value.synthesis = {25'000'000,
                       rf::si5351::Reference::ExternalXa,
                       {},
                       rf::si5351::Output::Clk0,
                       rf::si5351::Output::Clk2,
                       2};
    value.loopback_input = 7;
    value.manual_correction_ppb = -1234;
    return value;
}
std::string replace(std::string text, std::string from, std::string to) {
    const auto at = text.find(from);
    REQUIRE(at != std::string::npos);
    text.replace(at, from.size(), to);
    return text;
}
void strict_settings() {
    const auto value = settings();
    const auto text = hardware::serialize_si5351(value);
    REQUIRE(hardware::parse_si5351(text) == value);
    REQUIRE(!hardware::parse_si5351("null"));
    for (auto [from, to] : std::array<std::pair<std::string, std::string>, 16>{
             {{"\"address\":96", "\"address\":97"},
              {"\"drive_ma\":2", "\"drive_ma\":12"},
              {"\"transmit_output\":0", "\"transmit_output\":2"},
              {"\"loopback_output\":2", "\"loopback_output\":3"},
              {"\"loopback_input_gp\":7", "\"loopback_input_gp\":6"},
              {"\"loopback_output\":2", "\"loopback_output\":null"},
              {"\"reference_source\":\"external_xa\"", "\"reference_source\":\"clkin\""},
              {"\"reference_source\":\"external_xa\"", "\"reference_source\":\"crystal\""},
              {"\"crystal_load_pf\":null", "\"crystal_load_pf\":8"},
              {"\"reference_hz\":25000000", "\"reference_hz\":25000000.0"},
              {"\"reference_hz\":25000000", "\"reference_hz\":\"25000000\""},
              {"\"manual_correction_ppb\":-1234", "\"manual_correction_ppb\":100001"},
              {"\"automatic_calibration\":false", "\"automatic_calibration\":null"},
              {"\"rf_gate_gp\":null", "\"rf_gate_gp\":7"},
              {"\"reference_use\":\"measurement_only\"", "\"reference_use\":\"trusted_local\""},
              {"\"trusted_uncertainty_ppb\":null", "\"trusted_uncertainty_ppb\":100"}}})
        REQUIRE(!hardware::parse_si5351(replace(text, from, to)));
    REQUIRE(!hardware::parse_si5351(text.substr(0, text.size() - 1) + ",\"extra\":1}"));
    REQUIRE(!hardware::parse_si5351(text.substr(0, text.size() - 1) + ",\"address\":96}"));
    auto zero = value;
    zero.synthesis.transmit = rf::si5351::Output::Clk1;
    zero.synthesis.loopback = rf::si5351::Output::Clk0;
    REQUIRE(hardware::parse_si5351(hardware::serialize_si5351(zero)) == zero);
    zero.synthesis.loopback.reset();
    zero.loopback_input.reset();
    REQUIRE(hardware::parse_si5351(hardware::serialize_si5351(zero)) == zero);
}
void qualification_scope() {
    auto pins = hardware::PinPlan{};
    pins.engine = hardware::PinPlan::Engine::I2c;
    pins.rf.reset();
    pins.i2c_pair = 1;
    auto s = settings();
    s.synthesis.drive_ma = hardware::si5351_support::drive_ma;
    REQUIRE(hardware::si5351_profile_matches(pins, s, 138'000'000));
    REQUIRE(!hardware::si5351_profile_matches(pins, s, 132'000'000));
    pins.i2c_pair = 2;
    REQUIRE(!hardware::si5351_profile_matches(pins, s, 138'000'000));
    pins.i2c_pair = 1;
    s.synthesis.drive_ma = 4;
    REQUIRE(!hardware::si5351_profile_matches(pins, s, 138'000'000));
    s = settings();
    s.synthesis.drive_ma = hardware::si5351_support::drive_ma;
    s.synthesis.reference_hz = 27'000'000;
    REQUIRE(!hardware::si5351_profile_matches(pins, s, 138'000'000));
    s = settings();
    s.synthesis.drive_ma = hardware::si5351_support::drive_ma;
    s.synthesis.loopback.reset();
    s.loopback_input.reset();
    REQUIRE(hardware::si5351_profile_matches(pins, s, 138'000'000));
    REQUIRE(hardware::si5351_ordinary_qualified(pins, s, 138'000'000) ==
            hardware::si5351_support::qualified);
}
void measurement_publication_age() {
    const auto m =
        rf::measure_reference({1, 10000000001ULL, 10000000, 1000, 1, true}, 1000000, 1, {});
    REQUIRE(m.valid());
    rf::si5351::Engine::Observation observation;
    auto text =
        rf::si5351::observation_json(observation, m, {}, m.observed_raw_ns + 30'000'000'000ULL);
    REQUIRE(text.find("\"reference_measurement\":null") == std::string::npos);
    text = rf::si5351::observation_json(observation, m, {}, m.observed_raw_ns + 30'000'000'001ULL);
    REQUIRE(text.find("\"reference_measurement\":null") != std::string::npos);
    REQUIRE(text.find("stale_or_invalid_measurement") != std::string::npos);
    auto invalid = m;
    invalid.observed_hz = 1e30L;
    REQUIRE(!invalid.valid());
    invalid = m;
    invalid.policy.use = rf::ReferenceUse::TrustedLocal;
    REQUIRE(!invalid.valid());
}
void atomic_save_and_reboot_latch() {
    network_test::Fixture f;
    auto config = *standalone::parse_config(network_test::config);
    config.manual_correction_ppb = 5678;
    REQUIRE(f.store.save(config));
    standalone::Scheduler scheduler(f.store, f.service);
    network::BrowserApi api(f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test");
    auto save = [&](const standalone::Config& supplied, std::string revision = "") {
        auto wire = supplied;
        wire.manual_correction_ppb = 0;
        const auto body = standalone::serialize_config(wire, true);
        network::HttpRequest request;
        request.method = "POST";
        request.path = "/api/control/v1/config/update";
        request.headers = {{"host", "127.0.0.1:8443"},
                           {"origin", "https://127.0.0.1:8443"},
                           {"content-type", "application/json"},
                           {"x-wsprrypico-request", "1"}};
        request.headers["if-match"] = revision.empty() ? api.revision() : revision;
        request.body = network_test::configuration_update(body, f.service.status().boot_id);
        auto response =
            api.handle(network_test::control_request(request), "test", "127.0.0.1:8443");
        return response;
    };
    auto selected = config;
    selected.si5351 = settings();
    selected.pins.engine = hardware::PinPlan::Engine::I2c;
    selected.pins.rf.reset();
    selected.pins.i2c_pair = 1;
    const auto before = f.flash.bytes;
    auto conflict = selected;
    conflict.pins.i2c_pair = 7;
    REQUIRE(save(conflict).status == 400);
    REQUIRE(f.flash.bytes == before && f.store.config() == config);
    REQUIRE(save(selected, "wrong").status == 412);
    REQUIRE(f.flash.bytes == before);
    REQUIRE(save(selected).status == 200);
    REQUIRE(f.store.config() == selected);
    REQUIRE(scheduler.hardware_restart_required() && f.service.output_inhibited());
    REQUIRE(scheduler.active_pins() == config.pins);
    // A/B/A cannot cancel the restart interlock or overwrite frozen boot wiring.
    auto returned = selected;
    returned.pins = config.pins;
    REQUIRE(save(returned).status == 200);
    REQUIRE(scheduler.hardware_restart_required() && scheduler.active_pins() == config.pins);
    REQUIRE(f.store.config()->manual_correction_ppb == 5678);
    REQUIRE(f.store.config()->si5351->manual_correction_ppb == -1234);
    standalone::Store reloaded(f.flash);
    REQUIRE(reloaded.load() && reloaded.config() == returned);
    // Inactive drafts own no pins; activation validates every current owner.
    auto inactive = returned;
    inactive.si5351->loopback_input = 5;
    REQUIRE(f.store.save(inactive));
    auto active = inactive;
    active.pins = selected.pins;
    const auto state = f.flash.bytes;
    REQUIRE(!f.store.save(active) && f.flash.bytes == state);
    REQUIRE(f.store.config() == inactive);
}
} // namespace
int main(int argc, char** argv) {
    if (argc > 1) {
        network_test::Fixture f;
        auto config = *standalone::parse_config(network_test::config);
        config.pins.engine = hardware::PinPlan::Engine::I2c;
        config.pins.rf.reset();
        config.pins.i2c_pair = 1;
        config.si5351 = settings();
        const bool matched_profile = std::string_view(argv[1]) == "--qualified-samples";
        if (matched_profile)
            config.si5351->synthesis.drive_ma = hardware::si5351_support::drive_ma;
        REQUIRE(f.store.save(config));
        const auto service_policy = standalone::wtp_profile(
            matched_profile, standalone::default_ntp_timeout_s,
            hardware::PinPlan::Engine::I2c, false,
            hardware::si5351_ordinary_qualified(config.pins, *config.si5351, rf::sample_rate));
        wtp::JobService service(f.clock, f.engine, f.identities, service_policy);
        standalone::Scheduler scheduler(f.store, service);
        network::BrowserApi api(service, f.store, scheduler, f.network, std::string(32, 'a'),
                                "test");
        rf::si5351::Engine::Observation observation;
        observation.transmit = observation.reference =
            rf::si5351::ClockOutputState::RegisterDisabled;
        rf::ReferencePolicy policy;
        const auto measured =
            rf::measure_reference({1, 10000000001ULL, 10000000, 1000, 1, true}, 1000000, 1, policy);
        REQUIRE(measured.valid());
        auto runtime = rf::si5351::observation_json(observation, measured, {}, 10000000002ULL);
        api.si5351_observer([](void* value) { return *static_cast<std::string*>(value); },
                            &runtime);
        network::HttpRequest request;
        request.method = "GET";
        request.path = "/api/control/v1/si5351";
        request.headers["host"] = "127.0.0.1:8443";
        const auto response = api.handle(request, "test", "127.0.0.1:8443");
        REQUIRE(response.status == 200);
        std::cout << response.body_text() << '\n';
        return 0;
    }
    strict_settings();
    qualification_scope();
    measurement_publication_age();
    atomic_save_and_reboot_latch();
    std::cout
        << "Si5351 exact settings, atomic allocation, persistence and restart checks passed\n";
}

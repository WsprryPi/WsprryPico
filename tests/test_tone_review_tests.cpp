// SPDX-License-Identifier: MIT
#include "application/test_tone_review.hpp"
#include "network_support.hpp"
#include "rf/arm_admission.hpp"

#include <cmath>

using namespace wsprrypico;
namespace {
struct Flash : network_test::Flash {
    unsigned writes = 0;
    bool erase(std::size_t offset) override {
        ++writes;
        return network_test::Flash::erase(offset);
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> data) override {
        ++writes;
        return network_test::Flash::program(offset, data);
    }
};
struct Engine : execution::RfEngine {
    mutable unsigned calls = 0;
    execution::PrepareResult prepare(const execution::Job&) override {
        ++calls;
        return {true, {}};
    }
    bool set_frequency_correction_ppb(std::int32_t) override {
        ++calls;
        return true;
    }
    bool begin(const execution::Job&, std::uint64_t) override {
        ++calls;
        return true;
    }
    execution::EngineReport poll(std::uint64_t) override {
        ++calls;
        return {execution::EngineState::Idle};
    }
    bool disable(std::uint64_t) override {
        ++calls;
        return true;
    }
    bool output_active() const override {
        ++calls;
        return false;
    }
};
struct Fixture {
    Flash flash;
    standalone::Store store{flash};
    Engine raw;
    standalone::FrequencyPolicyEngine policy;
    application::TestToneContext context;
    execution::ServiceConfig limits;
    network_test::Clock clock;
    standalone::Store& initialize(unsigned drive, hardware::FilterSettings filters) {
        REQUIRE(store.load());
        auto config = *standalone::parse_config(network_test::config);
        config.gpio_drive_ma = drive;
        REQUIRE(store.save(config));
        if (filters != hardware::FilterSettings{})
            REQUIRE(store.save_filters(filters));
        return store;
    }
    explicit Fixture(unsigned drive = 12, hardware::FilterSettings filters = {})
        : policy(raw, initialize(drive, filters), rf::minimum_frequency_nhz,
                 rf::maximum_frequency_nhz) {
        context.physical_direct = true;
        context.boot_drive_ma = drive;
        context.start_resolution_ns = 1000;
        limits.minimum_frequency_nhz = rf::minimum_frequency_nhz;
        limits.maximum_frequency_nhz = rf::maximum_frequency_nhz;
        limits.max_job_duration_ns = rf::max_duration_ns;
    }
    application::TestToneReview review(application::TestToneProposal proposal) {
        const auto bytes = flash.bytes;
        const auto writes = flash.writes, calls = raw.calls;
        const auto config = standalone::serialize_config(*store.config());
        const auto result =
            application::review_test_tone(proposal, context, policy, limits, clock.snapshot());
        REQUIRE(flash.bytes == bytes && flash.writes == writes);
        REQUIRE(raw.calls == calls);
        REQUIRE(standalone::serialize_config(*store.config()) == config);
        REQUIRE(!policy.prepared_correction());
        return result;
    }
};
bool refused(const application::TestToneReview& r, std::string_view reason) {
    return std::find(r.refusals.begin(), r.refusals.begin() + r.refusal_count, reason) !=
           r.refusals.begin() + r.refusal_count;
}
void campaign_and_projection() {
    // Representative software points, not an authoritative HP bench campaign.
    constexpr std::array<std::uint64_t, 13> carriers{
        137'500,    475'700,    1'900'000,  3'600'000,  5'366'200,  7'100'000, 10'120'000,
        14'100'000, 18'100'000, 21'100'000, 24'920'000, 28'100'000, 50'100'000};
    unsigned points = 0;
    for (const unsigned drive : {2, 4, 8, 12}) {
        Fixture f(drive);
        for (const auto carrier : carriers) {
            const auto r = f.review({carrier, 10'000, drive});
            REQUIRE(r.admission == application::TestToneAdmission::Ready);
            REQUIRE(r.maximum_duration_ms == 120'000);
            REQUIRE(r.frequency.programmed_nhz && r.frequency.increment);
            REQUIRE(r.requested_nhz == carrier * 1'000'000'000ULL);
            // Independent rational-frequency oracle, not the production
            // integer-nHz packing formula. No offset/random placement exists.
            const long double realized =
                static_cast<long double>(*r.frequency.increment) * rf::sample_rate / 4294967296.L;
            REQUIRE(std::fabs(realized - carrier) <= r.quantization_bound_nhz / 1e9L);
            REQUIRE(std::fabs(realized - *r.frequency.programmed_nhz / 1e9L) <=
                    0.5e-9L + 4 * std::numeric_limits<long double>::epsilon() * realized);
            if (carrier == 5'366'200)
                REQUIRE(r.requested_nhz == 5'366'200'000'000'000ULL);
            REQUIRE(r.launch_monotonic_ns && r.launch_utc_ns);
            ++points;
        }
        for (const unsigned proposed : {2, 4, 8, 12}) {
            const auto r = f.review({5'366'200, 1000, proposed});
            REQUIRE(r.admission == (proposed == drive
                                        ? application::TestToneAdmission::Ready
                                        : application::TestToneAdmission::RequiresRestart));
        }
        f.context.restart_required = true; // Sticky restart, even A/B/A.
        REQUIRE(f.review({5'366'200, 1000, drive}).admission ==
                application::TestToneAdmission::RequiresRestart);
    }
    REQUIRE(points == 52);
}
void refusals_and_limits() {
    Fixture f;
    REQUIRE(f.review({5'366'200, 120'000, 12}).admission == application::TestToneAdmission::Ready);
    for (const auto duration : std::array<std::uint64_t, 3>{0, 120'001, UINT64_MAX})
        REQUIRE(refused(f.review({5'366'200, duration, 12}), "invalid_duration"));
    for (const unsigned ma : {0, 1, 3, 6, 16})
        REQUIRE(refused(f.review({5'366'200, 1000, ma}), "invalid_gpio_drive"));
    REQUIRE(refused(f.review({0, 1000, 12}), "invalid_carrier"));
    REQUIRE(refused(f.review({UINT64_MAX, 1000, 12}), "invalid_carrier"));
    REQUIRE(refused(f.review({rf::maximum_frequency_nhz / 1'000'000'000 + 1, 1000, 12}),
                    "frequency_out_of_range"));
    REQUIRE(refused(f.review({41'000'000, 1000, 12}), "unqualified_frequency_not_permitted"));
    REQUIRE(refused(f.review({1'000'000, 1000, 12}), "non_amateur_frequency_not_permitted"));
    auto config = *f.store.config();
    config.allow_unqualified_frequency = true;
    REQUIRE(f.store.save(config));
    REQUIRE(f.review({41'000'000, 1000, 12}).admission == application::TestToneAdmission::Ready);
    REQUIRE(refused(f.review({1'000'000, 1000, 12}), "non_amateur_frequency_not_permitted"));
    config.allow_non_amateur_frequency = true;
    config.manual_correction_ppb = 10'000;
    REQUIRE(f.store.save(config));
    const auto corrected = f.review({5'366'200, 1000, 12});
    REQUIRE(corrected.admission == application::TestToneAdmission::Ready);
    REQUIRE(corrected.frequency.correction->ppb == 10'000);
    const long double nominal = 5'366'200.L / 1.000010L;
    REQUIRE(std::fabs(*corrected.frequency.programmed_nhz / 1e9L - nominal) <=
            corrected.quantization_bound_nhz / 1e9L);
    f.limits.max_job_duration_ns = 2'500'000;
    REQUIRE(f.review({5'366'200, 2, 12}).maximum_duration_ms == 2);
    REQUIRE(refused(f.review({5'366'200, 3, 12}), "invalid_duration"));
    f.limits.minimum_frequency_nhz = 6'000'000'000'000'000ULL;
    REQUIRE(refused(f.review({5'366'200, 2, 12}), "native_frequency_out_of_range"));
    f.limits.minimum_frequency_nhz = rf::minimum_frequency_nhz;
    f.limits.maximum_frequency_nhz = 5'000'000'000'000'000ULL;
    REQUIRE(refused(f.review({5'366'200, 2, 12}), "native_frequency_out_of_range"));
    f.limits.maximum_frequency_nhz = rf::maximum_frequency_nhz;
    f.limits.minimum_frequency_nhz = 5'366'200'000'000'000ULL;
    REQUIRE(refused(f.review({5'366'200, 2, 12}), "native_frequency_out_of_range"));
}
void context_refusals() {
    Fixture f;
    const auto original = f.context;
    for (const auto flag :
         {&application::TestToneContext::wspr_enabled,
          &application::TestToneContext::message_enabled, &application::TestToneContext::owned,
          &application::TestToneContext::busy, &application::TestToneContext::faulted,
          &application::TestToneContext::maintenance,
          &application::TestToneContext::other_hardware_pending,
          &application::TestToneContext::recovery_inhibited}) {
        f.context = original;
        f.context.*flag = true;
        const auto r = f.review({5'366'200, 1000, 4});
        REQUIRE(r.admission == application::TestToneAdmission::Refused);
        REQUIRE(r.frequency.programmed_nhz); // Numerical review is still useful.
    }
    f.context = original;
    f.context.physical_direct = false;
    REQUIRE(refused(f.review({5'366'200, 1000, 12}), "inactive_direct_engine"));
    f.context = original;
    f.context.boot_pins.button = 2;
    REQUIRE(refused(f.review({5'366'200, 1000, 12}), "invalid_boot_pins"));
    f.context = original;
    f.limits.supported_modes = {"wspr"};
    REQUIRE(refused(f.review({5'366'200, 1000, 12}), "tone_not_supported"));
}
void filters_calibration_and_storage() {
    hardware::FilterSettings filters;
    filters.required = true;
    filters.output_count = 1;
    filters.outputs[0] = {1, 15, "60m", true};
    filters.range_count = 1;
    filters.ranges[0] = {"60m", 1, 5'250'000, 5'450'000};
    Fixture filtered(12, filters);
    REQUIRE(filtered.review({5'366'200, 1000, 12}).admission ==
            application::TestToneAdmission::Ready);
    REQUIRE(refused(filtered.review({7'100'000, 1000, 12}), "filter_coverage_required"));

    Fixture f;
    auto config = *f.store.config();
    config.gps.emplace();
    config.gps->enabled = true;
    config.gps->pairing_qualified = true;
    config.gps->automatic_rf_calibration = true;
    config.gps->calibration_maximum_age_s = 30;
    REQUIRE(f.store.save(config));
    REQUIRE(refused(f.review({5'366'200, 1000, 12}), "gps_calibration_required"));
    time::gps::Calibration learned{20'000, 1000, 30'000'000'000ULL, 20'000'000'000ULL, 1};
    f.policy.gps_calibration(learned, 35'000'000'000ULL, true, false);
    REQUIRE(f.review({5'366'200, 1000, 12}).frequency.correction->generation == 1);
    execution::Job job{std::string(32, '4'), "rf-events/1", "tone", 1'000'000'000, {}, true};
    REQUIRE(job.events.push_back({0, job.total_duration_ns, true, 5'366'200'000'000'000ULL}));
    REQUIRE(f.policy.prepare(job).accepted);
    const auto calls = f.raw.calls;
    const auto frozen = *f.policy.prepared_correction();
    learned.generation = 2;
    learned.oscillator_error_ppb = -20'000;
    f.policy.gps_calibration(learned, 36'000'000'000ULL, true, false);
    auto reviewed = application::review_test_tone({5'366'200, 1000, 4}, f.context, f.policy,
                                                  f.limits, f.clock.snapshot());
    REQUIRE(reviewed.frequency.correction->generation == 2);
    REQUIRE(f.policy.prepared_correction()->generation == frozen.generation);
    REQUIRE(f.policy.prepared_correction()->ppb == frozen.ppb);
    REQUIRE(f.raw.calls == calls);
    f.policy.gps_calibration(learned, 61'000'000'000ULL, true, false);
    reviewed = application::review_test_tone({5'366'200, 1000, 4}, f.context, f.policy, f.limits,
                                             f.clock.snapshot());
    REQUIRE(refused(reviewed, "gps_calibration_required"));
    REQUIRE(f.policy.prepared_correction()->generation == frozen.generation);

    Fixture faulty;
    faulty.flash.fail = true;
    REQUIRE(!faulty.store.save(*faulty.store.config()));
    REQUIRE(refused(faulty.review({5'366'200, 1000, 12}), "storage_fault"));

    Flash blank_flash;
    standalone::Store blank(blank_flash);
    REQUIRE(blank.load() && !blank.config());
    Engine raw;
    standalone::FrequencyPolicyEngine policy(raw, blank, rf::minimum_frequency_nhz,
                                             rf::maximum_frequency_nhz);
    const auto unconfigured = application::review_test_tone({5'366'200, 1000, 12}, f.context,
                                                            policy, f.limits, f.clock.snapshot());
    REQUIRE(unconfigured.admission == application::TestToneAdmission::Ready);
    REQUIRE(!blank.config() && blank_flash.writes == 0 && raw.calls == 0);
}
void clock_and_native_arm() {
    Fixture f;
    auto now = f.clock.snapshot();
    const auto base = now;
    const auto check = [&](execution::ErrorCode expected) {
        const auto r = application::review_test_tone({5'366'200, 1000, 12}, f.context, f.policy,
                                                     f.limits, now);
        REQUIRE(r.clock_error == expected);
        REQUIRE(r.admission == (expected == execution::ErrorCode::None
                                    ? application::TestToneAdmission::Ready
                                    : application::TestToneAdmission::Refused));
    };
    check(execution::ErrorCode::None);
    now.state = execution::ClockState::Unsynchronized;
    check(execution::ErrorCode::ClockUnsynchronized);
    now = base;
    now.state = execution::ClockState::Holdover;
    check(execution::ErrorCode::ClockUnsynchronized);
    now = base;
    now.uncertainty_ns = f.limits.maximum_arm_uncertainty_ns + 1;
    check(execution::ErrorCode::ClockUncertain);
    now = base;
    now.leap = execution::LeapState::Unknown;
    check(execution::ErrorCode::LeapUnsafe);
    now = base;
    now.valid_until_utc_ns = now.utc_now_ns + 1'000'000'000;
    check(execution::ErrorCode::LeapUnsafe);
    now = base;
    f.context.start_resolution_ns = 0;
    check(execution::ErrorCode::DeviceFault);
    f.context.start_resolution_ns = 1000;
    now.utc_now_ns = UINT64_MAX - 10;
    REQUIRE(refused(
        application::review_test_tone({5'366'200, 1000, 12}, f.context, f.policy, f.limits, now),
        "launch_time_overflow"));

    // Actual native ARM and a prospective review use the same clock rules.
    network_test::Identity identities;
    execution::JobService service(f.clock, f.policy, identities, f.limits);
    REQUIRE(network_test::internal_command(service, "HELLO", execution::HelloBody{{"native-execution/1"}}).ok);
    REQUIRE(network_test::internal_command(service, "CLAIM",
                                           execution::ClaimBody{std::string(32, '2'), 60'000})
                .ok);
    execution::Job job{std::string(32, '3'), "rf-events/1", "tone", 1'000'000'000, {}, true};
    REQUIRE(job.events.push_back({0, job.total_duration_ns, true, 5'366'200'000'000'000ULL}));
    REQUIRE(network_test::internal_command(service, "LOAD", job).ok);
    const auto reviewed = application::review_test_tone({5'366'200, 1000, 12}, f.context, f.policy,
                                                        f.limits, f.clock.snapshot());
    const auto armed = network_test::internal_command(
        service, "ARM",
        execution::ArmBody{job.job_id, *reviewed.launch_utc_ns, f.limits.maximum_arm_uncertainty_ns});
    REQUIRE(armed.ok && armed.start_monotonic_ns == reviewed.launch_monotonic_ns);
    REQUIRE(network_test::internal_command(service, "ABORT", execution::AbortBody{job.job_id}).ok);
}
void si5351_numerical_groundwork() {
    Flash flash;
    standalone::Store store(flash);
    REQUIRE(store.load());
    auto config = *standalone::parse_config(network_test::config);
    config.pins.engine = hardware::PinPlan::Engine::I2c;
    config.pins.rf.reset();
    config.pins.i2c_pair = 1;
    config.si5351 = hardware::Si5351Settings{};
    config.si5351->synthesis = {
        25'000'000, rf::si5351::Reference::ExternalXa, {}, rf::si5351::Output::Clk0, {}, 8};
    config.allow_unqualified_frequency = true;
    REQUIRE(store.save(config));
    Engine raw;
    standalone::FrequencyPolicyEngine policy(raw, store, 8'000'000'000'000ULL,
                                             160'000'000'000'000'000ULL);
    constexpr std::array<std::uint64_t, 17> carriers{
        137500,   475700,   1838100,  3570100,  5288700,  7050000,  10140200, 14097100, 18106100,
        21096100, 24926100, 28126100, 40001000, 50294500, 60001000, 70400000, 144490500};
    for (const int correction : {-10000, 0, 10000}) {
        config.si5351->manual_correction_ppb = correction;
        REQUIRE(store.save(config));
        for (const unsigned drive : {2u, 4u, 6u, 8u}) {
            for (const auto carrier : carriers) {
                const auto bytes = flash.bytes;
                const auto writes = flash.writes;
                const auto r = policy.assess_si5351_tone(carrier * 1'000'000'000ULL, drive);
                REQUIRE(r.refusal.empty() && r.programmed_nhz && r.correction);
                REQUIRE(!raw.calls && flash.bytes == bytes && flash.writes == writes);
                REQUIRE(!policy.prepared_correction());
                REQUIRE(r.correction->ppb == correction);
                const long double target = carrier / (1 + correction / 1e9L);
                REQUIRE(std::fabs(*r.programmed_nhz / 1e9L - target) <=
                        r.numerical_bound_nhz / 1e9L);
            }
        }
    }
    for (const unsigned invalid : {0u, 1u, 3u, 12u})
        REQUIRE(!policy.assess_si5351_tone(14'097'100'000'000'000ULL, invalid).refusal.empty());
    REQUIRE(!policy.assess_si5351_tone(0, 8).refusal.empty());
    REQUIRE(!policy.assess_si5351_tone(UINT64_MAX, 8).refusal.empty());
    Fixture direct;
    REQUIRE(direct.policy.assess_si5351_tone(14'097'100'000'000'000ULL, 8).refusal ==
            "inactive_si5351_engine");
}
void unattached_policy_refuses_execution() {
    network_test::Fixture f;
    const auto before = f.flash.bytes;
    const auto capabilities =
        f.api.handle({"GET",
                      "/api/control/v1/capabilities",
                      "",
                      {{"host", "127.0.0.1:8443"}, {"origin", "https://127.0.0.1:8443"}}},
                     "test", "127.0.0.1:8443");
    REQUIRE(capabilities.status == 200);
    REQUIRE(capabilities.body_text().find("test_tone") != std::string::npos);
    for (const auto path : {"/api/control/v1/test-tone/review", "/api/control/v1/test-tone/start",
                            "/api/control/v1/test-tone/stop"}) {
        const auto response = f.api.handle({"POST",
                                            path,
                                            R"({"contract":"Wsprry-Control/1"})",
                                            {{"host", "127.0.0.1:8443"},
                                             {"origin", "https://127.0.0.1:8443"},
                                             {"content-type", "application/json"},
                                             {"x-wsprrypico-request", "1"}}},
                                           "test", "127.0.0.1:8443");
        REQUIRE(response.status >= 400 && response.status < 500);
    }
    REQUIRE(f.flash.bytes == before);
    const auto activity = f.service.activity();
    REQUIRE(!activity.owned && !activity.output_active && activity.state == execution::State::Empty);
}
} // namespace
int main() {
    campaign_and_projection();
    refusals_and_limits();
    context_refusals();
    filters_calibration_and_storage();
    clock_and_native_arm();
    unattached_policy_refuses_execution();
    si5351_numerical_groundwork();
    std::cout << "PASS pure Test Tone groundwork: 52 points, projections, policy, clock, no "
                 "writes/preparation\n";
}

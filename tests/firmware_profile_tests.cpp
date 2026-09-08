#include "rf/stream_engine.hpp"
#include "standalone/dry_run_engine.hpp"
#include "standalone/wtp_profile.hpp"

#include <iostream>
#include <stdexcept>

using namespace wsprrypico;
#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x))                                                                                  \
            throw std::runtime_error(#x);                                                          \
    } while (false)

namespace {
struct Identity : wtp::IdentitySource {
    std::string new_boot_id() override {
        return std::string(32, 'b');
    }
};
struct Sink : rf::BlockSink {
    bool stop(std::uint64_t) override {
        return true;
    }
    bool submit(std::uint64_t, std::uint64_t, std::span<const std::uint32_t>,
                std::uint64_t) override {
        return false;
    }
    bool arm(std::uint64_t, std::uint64_t, std::uint64_t, rf::LaunchGuard) override {
        return false;
    }
    rf::SinkReport poll(std::uint64_t) override {
        return {};
    }
    bool output_active() const override {
        return false;
    }
};
wtp::Job job(std::string mode = "tone") {
    return {std::string(32, 'c'),
            "rf-events/1",
            std::move(mode),
            1'000'000'000,
            {{0, 1'000'000'000, true, 137'500'000'000'000ULL}},
            true};
}
struct Fixture {
    std::uint64_t now = 0;
    static std::uint64_t tick(void* self) {
        return static_cast<Fixture*>(self)->now;
    }
    time::UtcDiscipline clock{tick, this, standalone::clock_profile()};
    Identity identity;
    standalone::DryRunEngine engine;
    wtp::JobService service{clock, engine, identity, standalone::wtp_profile(false)};
    unsigned sequence = 0;
    wtp::Response request(std::string op, wtp::RequestBody body = {}) {
        wtp::Request r;
        r.session_id = std::string(32, '1');
        r.request_id = std::string(24, '0') + std::to_string(10000000 + ++sequence);
        r.principal = "test";
        r.payload_digest.fill(1);
        r.operation = std::move(op);
        r.body = std::move(body);
        return service.handle(r);
    }
    Fixture() {
        CHECK(request("HELLO", wtp::HelloBody{{"WTP/1"}}).ok);
        CHECK(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 60000}).ok);
    }
};
void limits() {
    const auto config = standalone::wtp_profile(true);
    CHECK(config.capability_engine == "pio-dma-gp2");
    CHECK(config.max_events == 162 && config.max_job_duration_ns == 110'592'000'000);
    CHECK(config.minimum_frequency_nhz == 100'000'000'000'000ULL);
    CHECK(config.maximum_frequency_nhz == (rf::sample_rate / 2 - 1) * 1'000'000'000ULL);
    CHECK(config.maximum_arm_uncertainty_ns == 500'000'000);
    CHECK(config.maximum_holdover_age_ns == 90'000'000'000ULL);
    Fixture f;
    auto good = job();
    CHECK(f.request("LOAD", good).ok);
    auto bad = good;
    bad.job_id = std::string(32, 'd');
    bad.mode = "cw";
    CHECK(f.request("LOAD", bad).error == wtp::ErrorCode::UnsupportedMode);
    bad.mode = "tone";
    bad.events.assign(163, {0, 1, false, {}});
    CHECK(f.request("LOAD", bad).error == wtp::ErrorCode::JobLimitExceeded);
    bad = good;
    bad.job_id = std::string(32, 'd');
    bad.total_duration_ns = bad.events[0].duration_ns = 110'592'000'001;
    CHECK(f.request("LOAD", bad).error == wtp::ErrorCode::JobLimitExceeded);
    bad = good;
    bad.job_id = std::string(32, 'd');
    bad.events[0].frequency_nhz = config.maximum_frequency_nhz + 1;
    CHECK(f.request("LOAD", bad).error == wtp::ErrorCode::FrequencyRejected);
    CHECK(f.service.status().job_id == good.job_id);
    CHECK(!f.service.status().output_active);
}
void physical_planner() {
    Sink sink;
    rf::StreamEngine engine(sink);
    for (const auto& mode : standalone::wtp_profile(true).supported_modes) {
        auto j = job(mode);
        auto result = engine.prepare(j);
        CHECK(result.accepted);
        CHECK(!result.adjustments.empty());
        CHECK(result.adjustments[0].requested_frequency_nhz == *j.events[0].frequency_nhz);
        CHECK(engine.disable(0));
        j.allow_frequency_adjustment = false;
        CHECK(!engine.prepare(j).accepted);
    }
    auto too_many = job();
    too_many.total_duration_ns = 5'000'000'000;
    too_many.events.clear();
    for (unsigned i = 0; i < 5; ++i)
        too_many.events.push_back({i * 1'000'000'000ULL, 1'000'000'000, true,
                                   137'500'000'000'000ULL + i * 1'000'000'000ULL});
    CHECK(!engine.prepare(too_many).accepted);
    // Positive event duration that is not representable on any supported sample grid.
    auto sub_sample = job();
    sub_sample.total_duration_ns = sub_sample.events[0].duration_ns = 1;
    CHECK(!engine.prepare(sub_sample).accepted);
    CHECK(!engine.output_active());
    // Exercise physical planner adjustments through the actual service/profile,
    // not just the planner API or the more permissive inhibited engine.
    Fixture clock_source;
    Identity ids;
    wtp::JobService service(clock_source.clock, engine, ids, standalone::wtp_profile(true));
    unsigned sequence = 0;
    auto send = [&](std::string operation, wtp::RequestBody body) {
        wtp::Request r;
        r.session_id = std::string(32, '1');
        r.request_id = std::string(24, '0') + std::to_string(10000000 + ++sequence);
        r.principal = "test";
        r.payload_digest.fill(1);
        r.operation = std::move(operation);
        r.body = std::move(body);
        return service.handle(r);
    };
    CHECK(send("HELLO", wtp::HelloBody{{"WTP/1"}}).ok);
    CHECK(send("CLAIM", wtp::ClaimBody{std::string(32, '2'), 60000}).ok);
    auto accepted = job("qrss");
    const auto loaded = send("LOAD", accepted);
    CHECK(loaded.ok && !loaded.adjustments.empty());
    auto rejected = job("dfcw");
    rejected.job_id = std::string(32, 'd');
    rejected.allow_frequency_adjustment = false;
    CHECK(send("LOAD", rejected).error == wtp::ErrorCode::FrequencyRejected);
    CHECK(service.status().job_id == accepted.job_id);
    CHECK(send("ABORT", wtp::AbortBody{accepted.job_id}).ok);
    CHECK(service.status().state == wtp::State::Aborted && !service.status().output_active);
}
void clocks() {
    constexpr std::uint64_t utc = 1'800'000'000'000'000'000ULL;
    Fixture f;
    CHECK(f.request("LOAD", job()).ok);
    CHECK(f.request("ARM", wtp::ArmBody{job().job_id, utc + 1'000'000'000, 500'000'000}).error ==
          wtp::ErrorCode::ClockUnsynchronized);
    CHECK(f.clock.observe(utc, f.now, 3'000'000, wtp::LeapState::Normal));
    CHECK(f.request("ARM", wtp::ArmBody{job().job_id, utc + 1'000'000'000, 1'000'000}).error ==
          wtp::ErrorCode::ClockUncertain);
    CHECK(f.request("ARM", wtp::ArmBody{job().job_id, utc + 1'000'000'000, 500'000'000}).ok);
    f.clock.invalidate();
    f.now = 1'000'000'000;
    f.service.poll();
    CHECK(f.service.status().state == wtp::State::Missed && !f.engine.output_active());
    Fixture aged;
    CHECK(aged.clock.observe(utc, 0, 499'999'999, wtp::LeapState::Normal));
    CHECK(aged.request("LOAD", job()).ok);
    CHECK(aged.request("ARM", wtp::ArmBody{job().job_id, utc + 1'000'000'000, 500'000'000}).ok);
    aged.now = 1'000'000'000;
    aged.service.poll();
    CHECK(aged.service.status().state == wtp::State::Missed && !aged.engine.output_active());
    Fixture old;
    CHECK(old.clock.observe(utc, 0, 3'000'000, wtp::LeapState::Normal));
    old.now = 90'000'000'001ULL;
    // Reclaim after idle lease expiry; an old SNTP observation still cannot arm.
    CHECK(old.request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 60000}).ok);
    CHECK(old.request("LOAD", job()).ok);
    CHECK(
        !old.request("ARM", wtp::ArmBody{job().job_id, utc + old.now + 1'000'000'000, 500'000'000})
             .ok);
    CHECK(!old.engine.output_active());
}
} // namespace
int main() {
    try {
        limits();
        physical_planner();
        clocks();
        std::cout << "Firmware profile, planner and clock gates passed at " << rf::sample_rate
                  << " Hz\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

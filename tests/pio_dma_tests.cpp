#include "provisioning/field_runtime.hpp"
#include "rf/pio_dma_sink.hpp"
#include "time/utc_discipline.hpp"

#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

using namespace wsprrypico;
#define CHECK(expr)                                                                                \
    do {                                                                                           \
        if (!(expr))                                                                               \
            throw std::runtime_error(#expr);                                                       \
    } while (false)

namespace {
class Hardware final : public rf::PioDmaHardware {
  public:
    Handler handler = nullptr;
    void* context = nullptr;
    std::uint64_t time = 1'000'000, epoch = 0, sequence = 0;
    std::uint64_t last_alarm = 0, last_launch_target = 0;
    std::optional<std::uint64_t> launch_observed_override;
    bool launch_on_unlock = false;
    bool enabled = false, busy = false, repeat = false, txstall = false;
    bool fail_open = false, fail_dma = false, fail_alarm = false, fail_halt = false;
    bool unsafe_halt = false;
    unsigned opened = 0, launches = 0, alarm_requests = 0, depth = 0;
    const std::uint32_t* data = nullptr;
    std::uint32_t count = 0;
    struct Pending {
        const std::uint32_t* data;
        std::uint32_t count;
        bool increment;
        std::uint64_t epoch, sequence;
    };
    std::optional<Pending> pending;
    std::uint32_t lock() override {
        return depth++;
    }
    void unlock(std::uint32_t previous) override {
        CHECK(depth == previous + 1);
        --depth;
        if (depth == 0 && launch_on_unlock) {
            launch_on_unlock = false;
            alarm_event(1);
        }
    }
    bool open(Handler h, void* c) override {
        CHECK(depth > 0);
        ++opened;
        if (fail_open) {
            return false;
        }
        handler = h;
        context = c;
        return true;
    }
    bool halt(std::uint64_t) override {
        CHECK(depth > 0);
        if (!unsafe_halt)
            enabled = false;
        if (fail_halt) {
            return false;
        }
        busy = false;
        pending.reset();
        txstall = false;
        return true;
    }
    bool dma(const std::uint32_t* p, std::uint32_t n, bool increment, std::uint64_t e,
             std::uint64_t s) override {
        CHECK(depth > 0 && !pending);
        if (fail_dma) {
            return false;
        }
        if (busy) {
            pending = Pending{p, n, increment, e, s};
            return true;
        }
        data = p;
        count = n;
        repeat = !increment;
        epoch = e;
        sequence = s;
        busy = true;
        return true;
    }
    bool alarm(std::uint64_t start, std::uint64_t) override {
        ++alarm_requests;
        last_alarm = start;
        return !fail_alarm;
    }
    bool retry_alarm(std::uint64_t when, std::uint64_t epoch) override {
        return alarm(when, epoch);
    }
    std::uint64_t launch_observed_ns() const override {
        return launch_observed_override.value_or(time);
    }
    rf::LaunchResult launch(std::uint64_t start, std::uint64_t deadline) override {
        CHECK(depth > 0);
        if (time >= deadline)
            return rf::LaunchResult::Rejected;
        if (time < start && start - time > 250000)
            return alarm(start, epoch) ? rf::LaunchResult::Rescheduled : rf::LaunchResult::Rejected;
        time = std::max(time, start);
        enabled = true;
        ++launches;
        last_launch_target = start;
        return rf::LaunchResult::Launched;
    }
    std::uint64_t now_ns() const override {
        return time;
    }
    bool stalled() const override {
        return txstall;
    }
    bool active() const override {
        return enabled;
    }
    void alarm_event(std::uint64_t e) {
        handler(context, {rf::DriverEventKind::Alarm, e, 0});
    }
    void complete() {
        CHECK(busy);
        const auto done_epoch = epoch, done_sequence = sequence;
        busy = pending.has_value();
        if (pending) {
            data = pending->data;
            count = pending->count;
            repeat = !pending->increment;
            epoch = pending->epoch;
            sequence = pending->sequence;
            pending.reset();
        }
        handler(context, {rf::DriverEventKind::DmaComplete, done_epoch, done_sequence});
    }
    void stop_tail_before_irq() {
        CHECK(busy && repeat && !pending);
        enabled = false; // Chained stop-channel write has executed.
        busy = false;    // Tail DMA completed; its IRQ remains pending.
    }
    void deliver_completion_irq() {
        handler(context, {rf::DriverEventKind::DmaComplete, epoch, sequence});
    }
};

std::uint64_t ns_at(std::uint64_t samples) {
    return (samples * 1000000000ULL + rf::sample_rate / 2) / rf::sample_rate;
}
wtp::Job job(std::uint64_t samples) {
    return {std::string(32, '3'),
            "rf-events/1",
            "tone",
            ns_at(samples),
            {{0, ns_at(samples), true, rf::base_nhz}},
            true};
}

void queue_test() {
    Hardware hw;
    rf::PioDmaSink sink(hw);
    std::array<std::uint32_t, rf::block_words> a{}, b{};
    a.fill(0x55aa55aaU);
    b.fill(0x12345678U);
    CHECK(sink.stop(hw.time));
    CHECK(hw.opened == 0);
    CHECK(!sink.submit(0, 0, a, rf::block_samples));
    CHECK(!sink.submit(1, 1, a, rf::block_samples));
    CHECK(sink.submit(1, 0, a, rf::block_samples));
    CHECK(sink.submit(1, 1, b, rf::block_samples));
    CHECK(!sink.submit(1, 2, a, rf::block_samples));
    CHECK(!sink.arm(1, hw.time + 1001, 2 * rf::block_samples));
    const auto start = hw.time + 1'000'000;
    CHECK(sink.arm(1, start, 2 * rf::block_samples));
    CHECK(hw.data == a.data() && hw.count == rf::block_words && !hw.repeat);
    hw.time = start - 50'000;
    hw.alarm_event(0); // Stale timer cannot launch this job.
    CHECK(hw.launches == 0);
    hw.alarm_event(1);
    CHECK(hw.launches == 1 && hw.enabled);
    hw.complete();
    CHECK(hw.data == b.data());
    hw.handler(hw.context, {rf::DriverEventKind::DmaComplete, 1, 0}); // Duplicate.
    CHECK(hw.data == b.data() && hw.busy);
    hw.time = start + ((ns_at(rf::block_samples) + 999) / 1000) * 1000;
    auto progress = sink.poll(hw.time);
    CHECK(progress.completed_blocks == 1 && progress.consumed_samples == rf::block_samples);
    hw.complete();
    CHECK(hw.repeat && hw.count == 10 && *hw.data == 0);
    hw.time = start + ((ns_at(2 * rf::block_samples) + 999) / 1000) * 1000;
    hw.complete();
    progress = sink.poll(hw.time);
    CHECK(progress.state == wtp::EngineState::Complete && !hw.enabled);
    CHECK(progress.consumed_samples == 2 * rf::block_samples);
    CHECK(sink.stop(hw.time));
    CHECK(sink.submit(2, 0, a, rf::block_samples));
    CHECK(sink.arm(2, hw.time + 1'000'000, rf::block_samples));
    hw.handler(hw.context, {rf::DriverEventKind::DmaComplete, 1, 1});
    CHECK(sink.poll(hw.time).state == wtp::EngineState::Armed);
    CHECK(sink.stop(hw.time));
}

void failures_test() {
    for (unsigned fault = 0; fault < 9; ++fault) {
        Hardware hw;
        rf::PioDmaSink sink(hw);
        std::array<std::uint32_t, rf::block_words> words{};
        if (fault == 0) {
            hw.fail_open = true;
            CHECK(!sink.submit(1, 0, words, rf::block_samples));
            continue;
        }
        CHECK(sink.submit(1, 0, words, rf::block_samples));
        if (fault == 1) {
            hw.fail_dma = true;
        }
        if (fault == 2) {
            hw.fail_alarm = true;
        }
        const auto start = hw.time + 1'000'000;
        const auto ok = sink.arm(1, start, rf::block_samples * 2);
        if (fault <= 2) {
            CHECK(!ok);
            CHECK(sink.stop(hw.time));
            continue;
        }
        CHECK(ok);
        hw.time = start + (fault == 3 ? 1000 : 0);
        if (fault == 8)
            hw.launch_observed_override = start - 1;
        hw.alarm_event(1);
        if (fault == 3) {
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Missed && !hw.enabled);
        } else if (fault == 4) {
            hw.complete(); // Missing next buffer: fail without replay.
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
            CHECK(sink.diagnostic() == "refill_starved");
            CHECK(!sink.submit(1, 1, words, rf::block_samples));
            CHECK(sink.diagnostic() == "refill_starved");
            CHECK(sink.stop(hw.time));
            CHECK(sink.diagnostic() == "refill_starved");
        } else if (fault == 5) {
            hw.txstall = true;
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
        } else if (fault == 6) {
            hw.fail_halt = true;
            CHECK(!sink.stop(hw.time));
            CHECK(!sink.submit(1, 1, words, rf::block_samples));
            hw.fail_halt = false;
        } else if (fault == 7) {
            hw.handler(hw.context, {rf::DriverEventKind::DmaError, 1, 0});
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
        } else {
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
            CHECK(sink.diagnostic() == "invalid_launch_boundary");
            CHECK(!hw.enabled);
        }
        CHECK(sink.stop(hw.time));
    }
    Hardware hw;
    rf::PioDmaSink sink(hw);
    std::array<std::uint32_t, 1> tail{0xffffffffU};
    CHECK(!sink.submit(1, 0, tail, 3)); // Dirty padding would emit beyond the job.
    tail[0] = 5;
    CHECK(sink.submit(1, 0, tail, 3));
    CHECK(sink.arm(1, hw.time + 1000000, 3));
    hw.complete(); // Short DMA can complete into the FIFO before launch.
    CHECK(hw.repeat && !hw.enabled);
    hw.time += 1000000;
    hw.alarm_event(1);
    hw.time += 1000;
    hw.complete();
    CHECK(sink.poll(hw.time).consumed_samples == 3);
    CHECK(sink.stop(hw.time));
}

class Clock final : public wtp::Clock {
  public:
    Hardware& hw;
    bool synchronized = true;
    std::uint64_t uncertainty = 0, utc_offset = 0, age = 0;
    bool holdover = false;
    wtp::LeapState leap = wtp::LeapState::Normal;
    std::optional<std::uint64_t> transition;
    explicit Clock(Hardware& h) : hw(h) {}
    wtp::ClockSnapshot snapshot() const override {
        return {holdover ? wtp::ClockState::Holdover
                         : (synchronized ? wtp::ClockState::Synchronized
                                         : wtp::ClockState::Unsynchronized),
                hw.time + utc_offset,
                hw.time,
                uncertainty,
                age,
                leap,
                transition};
    }
};
class Identity final : public wtp::IdentitySource {
  public:
    unsigned generation = 0;
    std::string new_boot_id() override {
        return std::string(32, static_cast<char>('1' + generation++));
    }
};
wtp::Request request(std::string op, wtp::RequestBody body, char id) {
    return {"WTP/1",
            std::string(32, '1'),
            std::string(32, id),
            "test",
            std::move(op),
            wtp::sha256(std::span(reinterpret_cast<const std::uint8_t*>(&id), 1)),
            std::move(body)};
}

void fractional_start_test() {
    for (unsigned action = 0; action < 6; ++action) {
        Hardware hw;
        hw.time = 2'000'000'000;
        Clock clock(hw);
        clock.utc_offset = 333;
        clock.uncertainty = 100;
        Identity identity;
        rf::PioDmaSink sink(hw);
        rf::StreamEngine engine(sink);
        wtp::JobService service(clock, engine, identity);
        CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
        CHECK(service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 5000}, 'b')).ok);
        const auto payload = job(rf::block_samples * 2);
        CHECK(service.handle(request("LOAD", payload, 'c')).ok);
        const auto start = hw.time + 100'000'000;
        if (action == 5) {
            clock.leap = wtp::LeapState::InsertPending;
            clock.transition = start - 1'000'000'000 + 1000;
        }
        // UTC request and clock mapping produce a monotonic target 562 ns
        // after a timer tick. Admission includes the upward timer adjustment.
        const auto response = service.handle(request(
            "ARM", wtp::ArmBody{payload.job_id, start + 895, action == 1 ? 537ULL : 538ULL}, 'd'));
        if (action == 1 || action == 5) {
            CHECK(!response.ok && response.error == (action == 1 ? wtp::ErrorCode::ClockUncertain
                                                                 : wtp::ErrorCode::LeapUnsafe));
            CHECK(service.status().state == wtp::State::Loaded && !hw.enabled);
        } else {
            CHECK(response.ok && response.start_monotonic_ns == start + 562);
            hw.time = start - 50'000;
            if (action == 2)
                ++clock.uncertainty;
            if (action == 3)
                hw.time = 3'000'000'000;
            if (action == 4) {
                clock.leap = wtp::LeapState::InsertPending;
                clock.transition = start - 1'000'000'000 + 1000;
            }
            hw.alarm_event(1);
            CHECK(hw.enabled == (action == 0));
            CHECK(hw.launches == (action == 0 ? 1U : 0U));
            if (action == 0)
                CHECK(hw.time == start + 1000); // Rounded up, never the earlier tick.
        }
        CHECK(engine.disable(hw.time));
    }
}

void c4_clock_refinement_replay_test() {
    // C4 raw ARM clock and the final pre-launch INFO sample. This replays
    // recorded conditions through the production guard; it is not the missing
    // interrupt-time snapshot or proof of the historical rejection branch.
    for (bool refined : {false, true}) {
        Hardware hw;
        hw.time = 254'425'705'000ULL;
        Clock clock(hw);
        clock.utc_offset = 1'789'402'676'877'225'000ULL;
        clock.uncertainty = 59'575'773;
        Identity identity;
        rf::PioDmaSink sink(hw);
        rf::StreamEngine engine(sink);
        wtp::ServiceConfig config;
        config.maximum_arm_uncertainty_ns = 500'000'000; // Deployed standalone policy.
        wtp::JobService service(clock, engine, identity, config);
        CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
        CHECK(
            service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 60000}, 'b')).ok);
        const auto payload = job(rf::sample_rate * 90ULL);
        CHECK(service.handle(request("LOAD", payload, 'c')).ok);
        const auto ack = service.handle(request(
            "ARM", wtp::ArmBody{payload.job_id, 1'789'402'941'273'883'000ULL, 500'000'000}, 'd'));
        if (!ack.ok)
            std::cerr << "C4 replay ARM error: " << static_cast<int>(ack.error) << '\n';
        CHECK(ack.ok && ack.start_monotonic_ns == 264'396'658'000ULL);
        if (refined) {
            clock.utc_offset += 25'805'000;
            clock.uncertainty = 9'629'566;
        }
        hw.time = 264'396'458'000ULL; // Driver offers its alarm 200 us early.
        hw.alarm_event(1);
        hw.time = 264'396'668'000ULL;
        service.poll();
        CHECK(hw.launches == 1);
        CHECK(hw.last_launch_target == (refined ? 264'396'458'000ULL : 264'396'658'000ULL));
        CHECK(service.status().state == wtp::State::Running);
        CHECK(engine.disable(hw.time));
    }

    // A refinement that moves the same UTC instant later must reproject the
    // local timer, not transmit at the stale early target or issue a new ARM.
    Hardware hw;
    hw.time = 254'425'705'000ULL;
    Clock clock(hw);
    clock.utc_offset = 1'789'402'676'877'225'000ULL;
    clock.uncertainty = 59'575'773;
    Identity identity;
    rf::PioDmaSink sink(hw);
    rf::StreamEngine engine(sink);
    wtp::ServiceConfig config;
    config.maximum_arm_uncertainty_ns = 500'000'000;
    wtp::JobService service(clock, engine, identity, config);
    CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
    CHECK(service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 60000}, 'b')).ok);
    const auto payload = job(rf::sample_rate * 90ULL);
    CHECK(service.handle(request("LOAD", payload, 'c')).ok);
    const auto ack = service.handle(request(
        "ARM", wtp::ArmBody{payload.job_id, 1'789'402'941'273'883'000ULL, 500'000'000}, 'd'));
    CHECK(ack.ok && ack.start_monotonic_ns == 264'396'658'000ULL);
    clock.utc_offset -= 25'805'000;
    clock.uncertainty = 9'629'566;
    hw.time = 264'396'458'000ULL;
    hw.alarm_event(1);
    CHECK(hw.launches == 0 && service.status().state == wtp::State::Armed);
    CHECK(hw.alarm_requests == 2 && hw.last_alarm == 264'422'463'000ULL);
    hw.time = 264'422'263'000ULL;
    hw.alarm_event(1);
    service.poll();
    CHECK(hw.launches == 1 && service.status().state == wtp::State::Running);
    CHECK(hw.last_launch_target == 264'422'463'000ULL);
    CHECK(engine.disable(hw.time));
}

void quantized_end_leap_test() {
    Hardware hw;
    Clock clock(hw);
    Identity identity;
    rf::PioDmaSink sink(hw);
    rf::StreamEngine engine(sink);
    wtp::JobService service(clock, engine, identity);
    CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
    CHECK(service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 5000}, 'b')).ok);
    auto payload = job(rf::block_samples * 2);
    --payload.total_duration_ns;
    --payload.events.back().duration_ns;
    CHECK(service.handle(request("LOAD", payload, 'c')).ok);
    const auto start = hw.time + 100'000'000;
    CHECK(service.handle(request("ARM", wtp::ArmBody{payload.job_id, start, 1000}, 'd')).ok);
    hw.time = start - 50'000;
    clock.leap = wtp::LeapState::InsertPending;
    clock.transition = start + ns_at(rf::block_samples * 2) + 1'000'000'000;
    hw.alarm_event(1);
    CHECK(!hw.enabled && hw.launches == 0);
    CHECK(engine.disable(hw.time));
}

void local_launch_test() {
    for (unsigned action = 0; action < 12; ++action) {
        Hardware hw;
        Clock clock(hw);
        Identity identity;
        rf::PioDmaSink sink(hw);
        rf::StreamEngine engine(sink);
        wtp::JobService service(clock, engine, identity);
        CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
        CHECK(service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 5000}, 'b')).ok);
        const auto payload = job(rf::block_samples * 2);
        CHECK(service.handle(request("LOAD", payload, 'c')).ok);
        const auto start = hw.time + 100'000'000;
        if (action >= 10) {
            hw.fail_alarm = true;
            hw.fail_halt = action == 11;
            const auto response =
                service.handle(request("ARM", wtp::ArmBody{payload.job_id, start, 1000}, 'd'));
            CHECK(!response.ok &&
                  response.error == (action == 10 ? wtp::ErrorCode::DeviceFault
                                                  : wtp::ErrorCode::OutputStateUnknown));
            CHECK(service.status().state == wtp::State::Failed && !hw.enabled);
            hw.fail_halt = false;
            CHECK(engine.disable(hw.time));
            continue;
        }
        CHECK(service.handle(request("ARM", wtp::ArmBody{payload.job_id, start, 1000}, 'd')).ok);
        CHECK(hw.busy && !hw.enabled); // Already prearmed; no foreground start required.
        CHECK(service.handle(request("ARM", wtp::ArmBody{payload.job_id, start, 1000}, 'e')).ok);
        if (action == 3) {
            CHECK(service.handle(request("ABORT", wtp::AbortBody{payload.job_id}, 'f')).ok);
        } else if (action == 4) {
            service.reset();
        }
        hw.time = start - 50'000;
        if (action == 1) {
            clock.synchronized = false;
        }
        if (action == 2) {
            hw.time = 1'000'000'000;
        }
        if (action == 5)
            clock.uncertainty = 1001;
        if (action == 6)
            clock.utc_offset = 1000;
        if (action == 7)
            clock.leap = wtp::LeapState::Unknown;
        if (action == 8) {
            clock.leap = wtp::LeapState::InsertPending;
            clock.transition = start;
        }
        if (action == 9) {
            clock.holdover = true;
            clock.age = ~std::uint64_t{0};
        }
        hw.alarm_event(1);
        if (action == 3 || action == 4) {
            CHECK(!hw.enabled && hw.launches == 0);
            continue;
        }
        // Foreground polling intentionally misses the exact launch instant.
        hw.time = start + 10'000;
        service.poll();
        if (action == 1 || action == 2 || action == 5 || action >= 7) {
            CHECK(service.status().state == wtp::State::Missed);
            CHECK(!hw.enabled && hw.launches == 0);
        } else {
            CHECK(hw.launches == 1 && service.status().state == wtp::State::Running);
            hw.complete();
            hw.time = start + ((ns_at(rf::block_samples) + 999) / 1000) * 1000;
            service.poll();
            hw.complete();
            hw.time = start + payload.total_duration_ns;
            hw.complete();
            service.poll();
            CHECK(service.status().state == wtp::State::Complete);
        }
        CHECK(!engine.output_active());
    }
}
void late_launch_window_test() {
    // UTC mapping is deliberately offset from the hardware timer. The cutoff
    // comes from the requested UTC second, not a monotonic second or +1 s.
    for (const auto delay : {0ULL, 293'000ULL, 249'999'000ULL, 250'000'000ULL}) {
        Hardware hw;
        Clock clock(hw);
        const auto start = hw.time + 100'000'000;
        clock.utc_offset = 1'750'000'000 - start;
        clock.uncertainty = 100;
        Identity identity;
        rf::PioDmaSink sink(hw);
        rf::StreamEngine engine(sink);
        wtp::JobService service(clock, engine, identity);
        CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
        CHECK(service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 5000}, 'b')).ok);
        const auto payload = job(2 * rf::block_samples);
        CHECK(service.handle(request("LOAD", payload, 'c')).ok);
        CHECK(service.handle(request("ARM", wtp::ArmBody{payload.job_id, 1'750'000'000, 1000}, 'd'))
                  .ok);
        // A delayed foreground read must not reject an otherwise valid alarm.
        hw.time = start + std::min(delay, 249'999'000ULL);
        service.poll();
        CHECK(service.status().state == wtp::State::Armed);
        hw.time = start + delay;
        hw.alarm_event(1);
        service.poll();
        if (delay == 250'000'000) {
            CHECK(service.status().state == wtp::State::Missed);
            CHECK(!hw.enabled && hw.launches == 0);
        } else {
            CHECK(service.status().state == wtp::State::Running && hw.launches == 1);
            CHECK(engine.poll(hw.time).launch_monotonic_ns == start + delay);
            const auto actual = start + delay;
            hw.complete();
            hw.time = actual + ((ns_at(rf::block_samples) + 999) / 1000) * 1000;
            service.poll();
            CHECK(service.status().state == wtp::State::Running);
            hw.complete();
            hw.time = actual + payload.total_duration_ns;
            hw.complete();
            service.poll();
            CHECK(service.status().state == wtp::State::Complete && !hw.enabled);
        }
    }
    CHECK(wtp::start_window_ns(2'000'000'000) == 1'000'000'000);
    CHECK(wtp::start_window_ns(2'999'999'999) == 1);
    Hardware hw;
    Clock clock(hw);
    clock.utc_offset = 1;
    Identity identity;
    rf::PioDmaSink sink(hw);
    rf::StreamEngine engine(sink);
    wtp::JobService service(clock, engine, identity);
    CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
    CHECK(service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 5000}, 'b')).ok);
    const auto payload = job(2 * rf::block_samples);
    CHECK(service.handle(request("LOAD", payload, 'c')).ok);
    // No representable microsecond remains inside this one-nanosecond window.
    const auto reply =
        service.handle(request("ARM", wtp::ArmBody{payload.job_id, 1'999'999'999, 1000}, 'd'));
    CHECK(!reply.ok && reply.error == wtp::ErrorCode::InvalidMessage && !hw.enabled);
}

void launch_snapshot_test() {
    Hardware hw;
    rf::PioDmaSink sink(hw);
    rf::StreamEngine engine(sink);
    const auto payload = job(2 * rf::block_samples);
    CHECK(engine.prepare(payload).accepted);
    const auto start = hw.time + 1000000;
    CHECK(engine.begin(payload, start));
    hw.time = start - 1000;
    hw.launch_on_unlock = true;
    const auto snapshot = engine.poll(hw.time);
    CHECK(hw.enabled); // Alarm fired as the sink released its snapshot lock.
    CHECK(snapshot.state == wtp::EngineState::Armed && !snapshot.output_active);
    CHECK(engine.poll(hw.time).state == wtp::EngineState::Running);
    CHECK(engine.disable(hw.time));
}
void more_than_final_pending_test() {
    Hardware hw;
    rf::PioDmaSink sink(hw);
    rf::StreamEngine engine(sink);
    const auto payload = job(2 * rf::block_samples);
    CHECK(engine.prepare(payload).accepted);
    const auto start = hw.time + 1000000;
    CHECK(engine.begin(payload, start));
    hw.time = start;
    hw.alarm_event(1);
    hw.time = start + payload.total_duration_ns + 61000;
    // Two outstanding blocks cannot use the final-acknowledgement allowance.
    CHECK(engine.poll(hw.time).state == wtp::EngineState::Failed);
    CHECK(!engine.output_active());
}
void delayed_tail_irq_after_hardware_stop_test() {
    Hardware hw;
    rf::PioDmaSink sink(hw);
    rf::StreamEngine engine(sink);
    const auto payload = job(2 * rf::block_samples);
    CHECK(engine.prepare(payload).accepted);
    const auto start = hw.time + 1000000;
    CHECK(engine.begin(payload, start));
    hw.time = start;
    hw.alarm_event(1);
    hw.complete();
    hw.complete();
    CHECK(hw.repeat && hw.enabled);
    hw.stop_tail_before_irq();
    hw.time = start + payload.total_duration_ns + 100001;
    const auto report = engine.poll(hw.time);
    CHECK(report.state == wtp::EngineState::Complete && !report.output_active);
    // A late IRQ is harmless after the same stop has already been observed.
    hw.deliver_completion_irq();
    CHECK(engine.poll(hw.time).state == wtp::EngineState::Complete);
    CHECK(engine.disable(hw.time));
}
void refill_test(bool missing_tail = false, bool delayed_final_data = false) {
    Hardware hw;
    rf::PioDmaSink sink(hw);
    rf::StreamEngine engine(sink);
    const auto payload = job(4 * rf::block_samples + 403);
    const auto plan = rf::plan_job(payload);
    CHECK(plan.has_value());
    rf::Waveform oracle;
    oracle.reset(*plan);
    std::array<std::uint32_t, rf::block_words> expected{};
    CHECK(engine.prepare(payload).accepted);
    const auto start = hw.time + 1000000;
    CHECK(engine.begin(payload, start));
    hw.time = start;
    hw.alarm_event(1);
    // Timer IRQ may launch after the caller snapshots time but before sink polling.
    CHECK(engine.poll(start - 50000).state == wtp::EngineState::Running);
    for (unsigned block = 0; block < 5; ++block) {
        const auto samples = oracle.render(expected);
        CHECK(hw.count == (samples + 31) / 32 && !hw.repeat);
        CHECK(std::equal(expected.begin(), expected.begin() + hw.count, hw.data));
        if (block == 4 && delayed_final_data) {
            // Hardware may already have drained the final block while its IRQ
            // is still pending. Progress is conservative until that IRQ runs.
            hw.time = start + payload.total_duration_ns + 61000;
            CHECK(engine.poll(hw.time).state == wtp::EngineState::Running);
            if (missing_tail) {
                hw.time = start + payload.total_duration_ns + 100001;
                CHECK(engine.poll(hw.time).state == wtp::EngineState::Failed);
                CHECK(!engine.output_active());
                CHECK(engine.disable(hw.time));
                return;
            }
        }
        // DMA delivers a block slightly ahead of its last sample leaving the FIFO.
        hw.complete();
        if (block == 0) {
            hw.time = start + 1000000;
            CHECK(sink.poll(hw.time).consumed_samples == rf::sample_rate / 1000);
        }
        if (block < 4) {
            hw.time = start + ((ns_at((block + 1) * rf::block_samples) + 999) / 1000) * 1000;
            CHECK(engine.poll(hw.time).state == wtp::EngineState::Running);
        }
    }
    CHECK(hw.repeat && hw.count == 10);
    hw.time = start + payload.total_duration_ns + 70000;
    CHECK(engine.poll(hw.time).state == wtp::EngineState::Running);
    if (missing_tail) {
        hw.time = start + payload.total_duration_ns + 100001;
        CHECK(engine.poll(hw.time).state == wtp::EngineState::Failed);
        CHECK(!engine.output_active());
    } else {
        hw.time = start + payload.total_duration_ns + 75000;
        hw.complete();
        CHECK(engine.poll(hw.time).state == wtp::EngineState::Complete);
    }
    CHECK(engine.disable(hw.time));
}

class Led final : public provisioning::IndicatorOutput {
  public:
    bool on = false, succeeds = true;
    std::vector<bool> writes;
    std::function<void()> during_write;
    bool write(bool value) override {
        writes.push_back(value);
        if (during_write) {
            auto callback = std::move(during_write);
            callback();
        }
        if (succeeds)
            on = value;
        return succeeds;
    }
};

void indicator_launch_and_shutdown() {
    Hardware hw;
    rf::IndicatorGate gate;
    rf::PioDmaSink sink(hw, &gate);
    Led led;
    provisioning::IndicatorController indicator(led, "device");
    indicator.softap_ready(true);
    CHECK(indicator.identify("one", "device", true, true, 0) == provisioning::IndicatorCode::Ok);
    indicator.poll_transmit(gate, 1'200); // Neither Identify nor AP is on here.
    CHECK(!led.on && !gate.requested());
    std::array<std::uint32_t, 32> words{};
    words.fill(0xaaaaaaaa);
    CHECK(sink.submit(1, 0, words, words.size() * 32));
    const auto start = hw.time + 1'000'000;
    CHECK(sink.arm(1, start, words.size() * 32, {nullptr, nullptr, start + 1'000'000'000}));
    indicator.poll_transmit(gate, 1'200);
    CHECK(!led.on && !gate.requested() && !hw.enabled);
    hw.time = start - 200'000;
    hw.alarm_event(1);
    CHECK(hw.last_alarm == start && !gate.requested() && !hw.enabled);
    hw.time = start;
    hw.alarm_event(1);
    CHECK(gate.requested() && !gate.ready() && !hw.enabled && hw.launches == 0);
    // An arbitrarily delayed management owner cannot start RF without the LED.
    for (unsigned i = 0; i < 10; ++i) {
        hw.time += 100'000;
        hw.alarm_event(1);
        CHECK(!hw.enabled && !led.on);
    }
    led.succeeds = false;
    indicator.poll_transmit(gate, 1'200);
    CHECK(!gate.ready() && !indicator.status(1'200).output_known &&
          indicator.status(1'200).output_fault);
    hw.time += 100'000;
    hw.alarm_event(1);
    CHECK(!hw.enabled);
    led.succeeds = true;
    indicator.poll_transmit(gate, 1'200);
    CHECK(led.on && gate.ready() && indicator.status(1'200).output_fault);
    hw.time += 100'000;
    hw.alarm_event(1);
    CHECK(hw.enabled && hw.launches == 1);
    const auto writes = led.writes.size();
    for (unsigned ms = 1'200; ms <= 15'200; ms += 50) {
        indicator.poll_transmit(gate, ms);
        CHECK(led.on); // Identify expires without interrupting solid TX.
    }
    CHECK(led.writes.size() == writes);
    hw.fail_halt = hw.unsafe_halt = true;
    CHECK(!sink.stop(hw.time));
    CHECK(hw.enabled && gate.requested());
    indicator.poll_transmit(gate, 15'200);
    CHECK(led.on);
    hw.fail_halt = false; // A lying success is also rejected while output stays active.
    CHECK(!sink.stop(hw.time) && gate.requested());
    CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
    hw.enabled = false; // Independently confirmed late physical stop.
    (void)sink.poll(hw.time);
    CHECK(!gate.requested());
    hw.fail_halt = hw.unsafe_halt = false;
    CHECK(sink.stop(hw.time));
    CHECK(!hw.enabled && !gate.requested());
    led.succeeds = false;
    indicator.poll_transmit(gate, 15'200);
    CHECK(led.on && !indicator.status(15'200).output_known);
    CHECK(indicator.status(15'200).output_on); // Last checked value, not fabricated off.
    led.succeeds = true;
    indicator.poll_transmit(gate, 15'200);
    CHECK(!led.on && indicator.status(15'200).output_known);
}

void indicator_stale_ack_and_timeout() {
    rf::IndicatorGate gate;
    CHECK(!gate.request_launch());
    const auto old = gate.requested();
    gate.inactive();
    CHECK(!gate.request_launch());
    const auto current = gate.requested();
    CHECK(old != current);
    gate.acknowledge(old); // An on write completed after cancel/rearm.
    CHECK(!gate.ready() && !gate.request_launch());
    gate.acknowledge(current);
    CHECK(gate.ready() && gate.request_launch());
    gate.inactive();
    gate.acknowledge(current); // Delayed acknowledgement cannot revive a cancelled job.
    CHECK(!gate.requested() && !gate.ready());

    // Cancel/rearm on the RF owner during a slow indicator write. The real
    // controller acknowledges only the old ticket that it sampled before I/O.
    Led led;
    provisioning::IndicatorController indicator(led, "device");
    CHECK(!gate.request_launch());
    led.during_write = [&] {
        gate.inactive();
        CHECK(!gate.request_launch());
    };
    indicator.poll_transmit(gate, 0);
    CHECK(led.on && !gate.ready());
    indicator.poll_transmit(gate, 1);
    CHECK(gate.ready());
    gate.inactive();

    for (const bool broken_alarm : {false, true}) {
        Hardware hw;
        rf::IndicatorGate pending;
        rf::PioDmaSink sink(hw, &pending);
        std::array<std::uint32_t, 32> words{};
        CHECK(sink.submit(1, 0, words, words.size() * 32));
        const auto start = hw.time + 1'000'000, deadline = start + 1'000'000;
        CHECK(sink.arm(1, start, words.size() * 32, {nullptr, nullptr, deadline}));
        hw.time = start;
        hw.fail_alarm = broken_alarm;
        hw.alarm_event(1);
        if (!broken_alarm) {
            CHECK(pending.requested() && !hw.enabled);
            hw.time = deadline;
            hw.alarm_event(1);
        }
        CHECK(sink.poll(hw.time).state == wtp::EngineState::Missed);
        CHECK(!pending.requested() && !hw.enabled && hw.launches == 0);
        CHECK(sink.stop(hw.time));
    }
}

void indicator_cancel_before_launch() {
    for (const bool clock_rejected : {false, true}) {
        Hardware hw;
        rf::IndicatorGate gate;
        rf::PioDmaSink sink(hw, &gate);
        Led led;
        provisioning::IndicatorController indicator(led, "device");
        std::array<std::uint32_t, 32> words{};
        CHECK(sink.submit(1, 0, words, words.size() * 32));
        const auto start = hw.time + 1'000'000;
        struct Projection {
            std::uint64_t start;
            bool valid = true;
        } projection{start};
        rf::LaunchGuard guard{[](void* value) {
                                  const auto& p = *static_cast<Projection*>(value);
                                  return rf::LaunchTarget{p.valid, p.start};
                              },
                              &projection, start + 1'000'000'000};
        CHECK(sink.arm(1, start, words.size() * 32, guard));
        hw.time = start;
        hw.alarm_event(1);
        indicator.poll_transmit(gate, 1'200);
        CHECK(led.on && gate.ready() && !hw.enabled);
        if (clock_rejected) {
            projection.valid = false;
            hw.time += 100'000;
            hw.alarm_event(1);
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Missed);
        } else {
            CHECK(sink.stop(hw.time)); // Abort/STOP during indicator activation.
            hw.alarm_event(1);         // A cancelled alarm cannot revive the job.
        }
        CHECK(!gate.requested() && !hw.enabled && hw.launches == 0);
        indicator.poll_transmit(gate, 1'200);
        CHECK(!led.on);
    }
}

void indicator_modes_and_tail() {
    // RF-producing warmup is an ordinary tone through this same launch gate.
    // Synthetic plans exercise engine gating; existing encoder/service tests
    // separately establish each mode's full job shape and content.
    for (const auto mode : {"tone", "wspr", "qrss", "fskcw", "dfcw"}) {
        for (const bool enabled : {true, false}) {
            Hardware hw;
            rf::IndicatorGate gate(enabled);
            rf::PioDmaSink sink(hw, &gate);
            rf::StreamEngine engine(sink);
            Led led;
            provisioning::IndicatorController indicator(led, "device");
            indicator.enabled(enabled);
            indicator.poll_transmit(gate, 1'200);
            auto payload = job(3 * rf::block_samples);
            payload.mode = mode;
            if (payload.mode == "qrss" || payload.mode == "dfcw") {
                const auto block_ns = ns_at(rf::block_samples);
                payload.events = {{0, block_ns, true, rf::base_nhz},
                                  {block_ns, block_ns, false, {}},
                                  {2 * block_ns, block_ns, true, rf::base_nhz}};
                payload.total_duration_ns = 3 * block_ns;
            }
            CHECK(engine.prepare(payload).accepted);
            CHECK(!gate.requested() && !led.on); // LOAD/preparation never requests TX.
            const auto start = hw.time + 1'000'000;
            // Production uses the existing one-second WTP launch window.
            time::UtcDiscipline clock([](void* p) { return static_cast<Hardware*>(p)->time; }, &hw);
            CHECK(clock.observe(1'800'000'000'000'000'000ULL, hw.time, 1'000,
                                wtp::LeapState::Normal));
            CHECK(engine.schedule(
                payload, start,
                {&clock, clock.snapshot().utc_now_ns + 1'000'000, 1'000'000, 0, 0}));
            CHECK(!gate.requested() && !led.on);
            hw.time = start;
            hw.alarm_event(1);
            if (enabled) {
                CHECK(!hw.enabled && gate.requested());
                indicator.poll_transmit(gate, 1'200);
                CHECK(led.on);
                hw.time += 100'000;
                hw.alarm_event(1);
            }
            CHECK(hw.enabled && hw.launches == 1);
            const auto launched = hw.time;
            CHECK(engine.poll(hw.time).state == wtp::EngineState::Running);
            for (unsigned block = 0; block < 3; ++block) {
                hw.complete();
                hw.time = launched + ((ns_at((block + 1) * rf::block_samples) + 999) / 1000) * 1000;
                CHECK(engine.poll(hw.time).state == wtp::EngineState::Running);
                indicator.poll_transmit(gate, 1'200);
                CHECK(hw.enabled && led.on == enabled); // Includes zero-rendered mode gaps.
            }
            CHECK(hw.repeat);
            hw.stop_tail_before_irq();
            // Hardware stopped first; delayed tail IRQ cannot extend RF/retain TX.
            CHECK(engine.poll(hw.time).state == wtp::EngineState::Complete);
            CHECK(!gate.requested());
            indicator.poll_transmit(gate, 1'200);
            CHECK(!led.on);
            hw.deliver_completion_irq();
            CHECK(engine.disable(hw.time));
        }
    }
}
} // namespace
int main() {
    try {
        queue_test();
        failures_test();
        fractional_start_test();
        c4_clock_refinement_replay_test();
        quantized_end_leap_test();
        local_launch_test();
        late_launch_window_test();
        launch_snapshot_test();
        more_than_final_pending_test();
        delayed_tail_irq_after_hardware_stop_test();
        refill_test();
        refill_test(true);
        refill_test(false, true);
        refill_test(true, true);
        indicator_launch_and_shutdown();
        indicator_stale_ack_and_timeout();
        indicator_cancel_before_launch();
        indicator_modes_and_tail();
        std::cout << "PIO/DMA checks passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}

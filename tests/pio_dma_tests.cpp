#include "rf/pio_dma_sink.hpp"

#include <algorithm>
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
    bool enabled = false, busy = false, repeat = false, txstall = false;
    bool fail_open = false, fail_dma = false, fail_alarm = false, fail_halt = false;
    unsigned opened = 0, launches = 0, depth = 0;
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
    bool alarm(std::uint64_t, std::uint64_t) override {
        return !fail_alarm;
    }
    bool launch(std::uint64_t start) override {
        CHECK(depth > 0);
        if (time > start || start - time > 50000) {
            return false;
        }
        time = start;
        enabled = true;
        ++launches;
        return true;
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
};

std::uint64_t ns_at(std::uint64_t samples) {
    return (samples * 20 + 1) / 3;
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
    for (unsigned fault = 0; fault < 8; ++fault) {
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
        hw.alarm_event(1);
        if (fault == 3) {
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Missed && !hw.enabled);
        } else if (fault == 4) {
            hw.complete(); // Missing next buffer: fail without replay.
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
        } else if (fault == 5) {
            hw.txstall = true;
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
        } else if (fault == 6) {
            hw.fail_halt = true;
            CHECK(!sink.stop(hw.time));
            CHECK(!sink.submit(1, 1, words, rf::block_samples));
            hw.fail_halt = false;
        } else {
            hw.handler(hw.context, {rf::DriverEventKind::DmaError, 1, 0});
            CHECK(sink.poll(hw.time).state == wtp::EngineState::Failed);
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
            hw.time = start + 1000;
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
        if (action == 1 || action == 2 || action >= 5) {
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
void refill_test() {
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
        // DMA delivers a block slightly ahead of its last sample leaving the FIFO.
        hw.complete();
        if (block < 4) {
            hw.time = start + ((ns_at((block + 1) * rf::block_samples) + 999) / 1000) * 1000;
            CHECK(engine.poll(hw.time).state == wtp::EngineState::Running);
        }
    }
    CHECK(hw.repeat && hw.count == 10);
    hw.time = start + ((payload.total_duration_ns + 999) / 1000) * 1000 + 1000;
    hw.complete();
    CHECK(engine.poll(hw.time).state == wtp::EngineState::Complete);
    CHECK(engine.disable(hw.time));
}

} // namespace
int main() {
    try {
        queue_test();
        failures_test();
        local_launch_test();
        refill_test();
        std::cout << "PIO/DMA checks passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}

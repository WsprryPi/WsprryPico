#include "rf/worker.hpp"

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <thread>
using namespace wsprrypico;
#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x)) {                                                                                \
            std::cerr << __LINE__ << ": " #x "\n";                                                 \
            std::abort();                                                                          \
        }                                                                                          \
    } while (false)
namespace {
std::uint64_t now() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}
std::uint64_t clock_now(void*) {
    return now();
}
void wait() {
    std::this_thread::yield();
}
void failure() {
    std::abort();
}
std::uint32_t mask() {
    return 0;
}
void restore(std::uint32_t) {}
struct Engine : wtp::RfEngine {
    std::atomic<unsigned> polls{0}, launches{0}, completions{0};
    wtp::EngineState state = wtp::EngineState::Idle;
    std::uint64_t start = 0;
    wtp::LocalStartConditions conditions;
    bool fail_disable = false;
    wtp::PrepareResult prepare(const wtp::Job&) override {
        return {true, {}};
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const wtp::Job&, std::uint64_t when,
                  const wtp::LocalStartConditions& c) override {
        start = when;
        conditions = c;
        state = wtp::EngineState::Armed;
        return true;
    }
    bool begin(const wtp::Job&, std::uint64_t) override {
        return false;
    }
    wtp::EngineReport poll(std::uint64_t t) override {
        ++polls;
        if (state == wtp::EngineState::Armed && t >= start) {
            const auto clock = conditions.clock->snapshot();
            state = clock.state == wtp::ClockState::Unsynchronized ? wtp::EngineState::Missed
                                                                   : wtp::EngineState::Running;
            if (state == wtp::EngineState::Running)
                ++launches;
        }
        if (state == wtp::EngineState::Running && t >= start + 10'000'000) {
            state = wtp::EngineState::Complete;
            ++completions;
        }
        return {state, output_active()};
    }
    bool disable(std::uint64_t) override {
        if (fail_disable)
            return false;
        state = wtp::EngineState::Idle;
        return true;
    }
    bool output_active() const override {
        return state == wtp::EngineState::Running;
    }
};
} // namespace
rf::WorkerEngine* recursive = nullptr;
void reentrant_wait() {
    (void)recursive->poll(now());
}
int main(int argc, char** argv) {
    Engine physical;
    time::UtcDiscipline clock(clock_now, nullptr);
    CHECK(clock.observe(1'800'000'000'000'000'000ULL, now(), 1000, wtp::LeapState::Normal));
    rf::WorkerEngine proxy(physical, clock, now, wait, failure, mask, restore);
    wtp::Job job;
    if (argc > 1) {
        if (std::string_view(argv[1]) == "--reentrant") {
            rf::WorkerEngine nested(physical, clock, now, reentrant_wait, failure, mask, restore);
            recursive = &nested;
            (void)nested.prepare(job);
        } else
            (void)proxy.prepare(job); // No consumer: bounded non-returning recovery.
        return 1;
    }
    std::atomic<bool> stop{false};
    std::atomic<unsigned> probes{0};
    proxy.set_probe(
        [](rf::WorkerEngine::Metrics& metrics, void* context) {
            ++*static_cast<std::atomic<unsigned>*>(context);
            metrics.stack_used_bytes = 1234;
        },
        &probes);
    std::thread owner([&] {
        while (!stop.load())
            proxy.step();
    });
    CHECK(proxy.prepare(job).accepted);
    wtp::LocalStartConditions c{&clock, clock.snapshot().utc_now_ns + 10'000'000, 1000000, 0, 0};
    CHECK(proxy.schedule(job, now() + 10'000'000, c));
    // Simulate arbitrarily busy TLS/JSON owner: no RPC or authority polling.
    std::this_thread::sleep_for(std::chrono::milliseconds(40));
    CHECK(physical.launches == 1 && physical.completions == 1);
    CHECK(proxy.poll(now()).state == wtp::EngineState::Complete);
    CHECK(proxy.disable(now() + 100000000));
    // Coherent clock invalidation reaches the independently aging launch clock.
    CHECK(proxy.prepare(job).accepted);
    CHECK(proxy.schedule(job, now() + 20'000'000, c));
    clock.invalidate();
    (void)proxy.poll(now());
    std::this_thread::sleep_for(std::chrono::milliseconds(30));
    CHECK(proxy.poll(now()).state == wtp::EngineState::Missed);
    CHECK(physical.launches == 1);
    CHECK(proxy.disable(now() + 100000000));
    physical.fail_disable = true;
    CHECK(!proxy.disable(now() + 100000000));
    physical.fail_disable = false;
    CHECK(proxy.disable(now() + 100000000));
    for (unsigned i = 0; i < 1000; ++i)
        CHECK(proxy.prepare(job).accepted);
    // The normal lifecycle, output inspection and 1,000 reused commands must
    // not invoke the expensive target probe. Explicit snapshots remain coherent.
    CHECK(!proxy.output_active());
    CHECK(probes == 0);
    const auto first = proxy.metrics();
    CHECK(first.commands >= 1000 && first.probes == 1 && first.stack_used_bytes == 1234);
    CHECK(probes == 1);
    (void)proxy.poll(now());
    CHECK(probes == 1);
    const auto second = proxy.metrics();
    CHECK(second.probes == 2 && second.commands == first.commands + 2);
    CHECK(second.max_probe_ns >= first.max_probe_ns);
    stop = true;
    owner.join();
    std::cout << "RF rendezvous ownership, delayed producer, local completion, clock invalidation "
                 "and reuse passed\n";
}

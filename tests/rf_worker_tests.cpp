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
    bool fail_disable = false, unsafe_disable = false;
    bool* inhibit_on_prepare = nullptr;
    bool* inhibit_on_schedule = nullptr;
    std::uint64_t duration_ns = 10'000'000;
    unsigned prepares = 0, schedules = 0;
    bool independent_plan = false;
    bool owns_execution_plan() const override {
        return independent_plan;
    }
    wtp::PrepareResult prepare(const wtp::Job&) override {
        ++prepares;
        if (inhibit_on_prepare)
            *inhibit_on_prepare = true;
        return {true, {}};
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const wtp::Job&, std::uint64_t when,
                  const wtp::LocalStartConditions& c) override {
        ++schedules;
        start = when;
        conditions = c;
        state = wtp::EngineState::Armed;
        if (inhibit_on_schedule)
            *inhibit_on_schedule = true;
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
        if (state == wtp::EngineState::Running && t >= start + duration_ns) {
            state = wtp::EngineState::Complete;
            ++completions;
        }
        return {state, output_active()};
    }
    bool disable(std::uint64_t) override {
        if (fail_disable)
            return false;
        if (!unsafe_disable)
            state = wtp::EngineState::Idle;
        return true;
    }
    bool output_active() const override {
        return state == wtp::EngineState::Running;
    }
};
} // namespace
namespace {
std::uint64_t manual_ns = 1'000'000;
rf::WorkerEngine* manual_worker = nullptr;
std::uint64_t manual_now() {
    return manual_ns;
}
std::uint64_t manual_clock(void*) {
    return manual_ns;
}
void manual_wait() {
    manual_worker->step();
}
bool safety_requested(void* context) {
    return *static_cast<bool*>(context);
}

void independent_worker_safety(bool armed) {
    manual_ns = 1'000'000;
    Engine engine;
    time::UtcDiscipline clock(manual_clock, nullptr);
    CHECK(clock.observe(1'800'000'000'000'000'000ULL, manual_ns, 1000, wtp::LeapState::Normal));
    rf::WorkerEngine proxy(engine, clock, manual_now, manual_wait, failure, mask, restore);
    manual_worker = &proxy;
    bool request = false;
    proxy.set_safety(safety_requested, &request);
    wtp::Job job;
    CHECK(proxy.prepare(job).accepted);
    wtp::LocalStartConditions conditions{&clock, clock.snapshot().utc_now_ns + 100'000'000, 1000000,
                                         0, 0};
    CHECK(proxy.schedule(job, 101'000'000, conditions));
    if (!armed) {
        manual_ns = 102'000'000;
        proxy.step();
        CHECK(engine.output_active() && engine.launches == 1);
    }
    // Core 0 does no RPC/authority polling while the independent worker stops.
    request = true;
    manual_ns += 1'000;
    proxy.step();
    CHECK(proxy.safety_inhibited() && !engine.output_active());
    CHECK(engine.state == wtp::EngineState::Idle);
    request = false;
    manual_ns = 200'000'000;
    proxy.step();
    CHECK(engine.launches == (armed ? 0u : 1u));
    CHECK(!proxy.prepare(job).accepted && !proxy.schedule(job, 300'000'000, conditions));
    CHECK(engine.prepares == 1 && engine.schedules == 1);
    CHECK(proxy.disable(manual_ns + 100'000'000));
    CHECK(proxy.safety_inhibited());
    const auto metrics = proxy.metrics();
    CHECK(metrics.safety_requested_ns && metrics.safety_stopped_ns >= metrics.safety_requested_ns);
    CHECK(proxy.diagnostic() == "gp14_safety_inhibit");
}

void safety_during_prepare() {
    manual_ns = 1'000'000;
    Engine engine;
    bool request = false;
    engine.inhibit_on_prepare = &request;
    time::UtcDiscipline clock(manual_clock, nullptr);
    rf::WorkerEngine proxy(engine, clock, manual_now, manual_wait, failure, mask, restore);
    manual_worker = &proxy;
    proxy.set_safety(safety_requested, &request);
    CHECK(!proxy.prepare({}).accepted);
    CHECK(proxy.safety_inhibited() && engine.prepares == 1 && !engine.output_active());
}
void safety_during_schedule() {
    manual_ns = 1'000'000;
    Engine engine;
    bool request = false;
    engine.inhibit_on_schedule = &request;
    time::UtcDiscipline clock(manual_clock, nullptr);
    rf::WorkerEngine proxy(engine, clock, manual_now, manual_wait, failure, mask, restore);
    manual_worker = &proxy;
    proxy.set_safety(safety_requested, &request);
    CHECK(proxy.prepare({}).accepted);
    wtp::LocalStartConditions conditions{&clock, 200'000'000, 1000000, 0, 0};
    CHECK(!proxy.schedule({}, 101'000'000, conditions));
    manual_ns = 102'000'000;
    proxy.step();
    CHECK(proxy.safety_inhibited() && engine.launches == 0 && !engine.output_active());
}
void threaded_safety_with_busy_producer() {
    Engine engine;
    engine.duration_ns = 500'000'000;
    time::UtcDiscipline clock(clock_now, nullptr);
    CHECK(clock.observe(1'800'000'000'000'000'000ULL, now(), 1000, wtp::LeapState::Normal));
    rf::WorkerEngine proxy(engine, clock, now, wait, failure, mask, restore);
    std::atomic<bool> request{false}, finish{false};
    proxy.set_safety([](void* value) { return static_cast<std::atomic<bool>*>(value)->load(); },
                     &request);
    std::thread owner([&] {
        while (!finish.load())
            proxy.step();
    });
    CHECK(proxy.prepare({}).accepted);
    wtp::LocalStartConditions conditions{&clock, clock.snapshot().utc_now_ns + 5'000'000, 1000000,
                                         0, 0};
    CHECK(proxy.schedule({}, now() + 5'000'000, conditions));
    const auto deadline = now() + 200'000'000;
    while (!engine.launches.load() && now() < deadline)
        wait();
    CHECK(engine.launches == 1);
    request.store(true);
    // No producer RPC: only the engine owner can observe input and halt output.
    while (!proxy.safety_inhibited() && now() < deadline)
        wait();
    CHECK(proxy.safety_inhibited());
    CHECK(!proxy.output_active());
    CHECK(!proxy.prepare({}).accepted);
    finish.store(true);
    owner.join();
}
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
    CHECK(!proxy.owns_execution_plan());
    Engine owned;
    owned.independent_plan = true;
    rf::WorkerEngine owned_proxy(owned, clock, now, wait, failure, mask, restore);
    CHECK(owned_proxy.owns_execution_plan());
    owned.independent_plan = false;
    // Capability is frozen before worker startup, never a cross-core query.
    CHECK(owned_proxy.owns_execution_plan());
    wtp::Job job;
    if (argc > 1) {
        if (std::string_view(argv[1]) == "--safety-failure" ||
            std::string_view(argv[1]) == "--safety-unsafe-success") {
            bool request = true;
            physical.state = wtp::EngineState::Running;
            physical.start = now();
            physical.fail_disable = std::string_view(argv[1]) == "--safety-failure";
            physical.unsafe_disable = !physical.fail_disable;
            proxy.set_safety(safety_requested, &request);
            proxy.step(); // Failed disable / active output after success never returns.
        } else if (std::string_view(argv[1]) == "--reentrant") {
            rf::WorkerEngine nested(physical, clock, now, reentrant_wait, failure, mask, restore);
            recursive = &nested;
            (void)nested.prepare(job);
        } else
            (void)proxy.prepare(job); // No consumer: bounded non-returning recovery.
        return 1;
    }
    independent_worker_safety(true);
    independent_worker_safety(false);
    safety_during_prepare();
    safety_during_schedule();
    threaded_safety_with_busy_producer();
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

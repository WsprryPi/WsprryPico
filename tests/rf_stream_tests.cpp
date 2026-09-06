#include "rf/stream_engine.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
#include <vector>

using namespace wsprrypico;

static std::size_t allocations = 0;
void* operator new(std::size_t size) {
    ++allocations;
    if (auto* result = std::malloc(size ? size : 1)) {
        return result;
    }
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept {
    std::free(memory);
}
void operator delete(void* memory, std::size_t) noexcept {
    std::free(memory);
}

#define CHECK(expr)                                                                                \
    do {                                                                                           \
        if (!(expr))                                                                               \
            throw std::runtime_error(#expr);                                                       \
    } while (false)

namespace {
std::uint64_t ns_at(std::uint64_t samples) {
    return (samples * 1000000000ULL + rf::sample_rate / 2) / rf::sample_rate;
}

wtp::Job job_for(std::span<const std::uint64_t> lengths) {
    wtp::Job job;
    job.job_id = std::string(32, '3');
    job.mode = "wspr";
    job.allow_frequency_adjustment = true;
    std::uint64_t cursor = 0;
    for (std::size_t i = 0; i < lengths.size(); ++i) {
        const auto start = ns_at(cursor);
        cursor += lengths[i];
        job.events.push_back(
            {start, ns_at(cursor) - start, true, rf::base_nhz + (i % 4) * rf::spacing_nhz});
    }
    job.total_duration_ns = ns_at(cursor);
    return job;
}

wtp::Job tone_job(std::uint64_t samples) {
    return job_for(std::array{samples});
}

std::uint64_t checksum(std::span<const std::uint32_t> words) {
    std::uint64_t result = 0;
    for (auto word : words) {
        result = result * 31 + word;
    }
    return result;
}

class TestSink final : public rf::BlockSink {
  public:
    struct Slot {
        std::uint64_t sequence = 0;
        std::span<const std::uint32_t> words;
        std::uint64_t samples = 0;
        std::uint64_t digest = 0;
        bool held = false;
    };
    std::array<Slot, 2> slots{};
    rf::SinkReport report;
    std::uint64_t total = 0;
    std::uint64_t start = 0;
    bool active = false;
    bool reject_stop = false;
    bool reject_submit = false;
    bool reject_arm = false;
    unsigned stop_calls = 0;

    bool stop(std::uint64_t) override {
        ++stop_calls;
        if (reject_stop) {
            return false;
        }
        active = false;
        slots = {};
        report = {};
        return true;
    }
    bool submit(std::uint64_t epoch, std::uint64_t sequence, std::span<const std::uint32_t> words,
                std::uint64_t samples) override {
        if (reject_submit) {
            return false;
        }
        auto& slot = slots[sequence % 2];
        CHECK(!slot.held);
        CHECK(samples > 0 && samples <= rf::block_samples);
        slot = {sequence, words, samples, checksum(words), true};
        report.epoch = epoch;
        return true;
    }
    bool arm(std::uint64_t epoch, std::uint64_t start_ns, std::uint64_t samples,
             rf::LaunchGuard = {}) override {
        if (reject_arm) {
            return false;
        }
        report = {wtp::EngineState::Armed, epoch, 0, 0};
        start = start_ns;
        total = samples;
        return true;
    }
    rf::SinkReport poll(std::uint64_t now) override {
        for (const auto& slot : slots) {
            if (slot.held) {
                CHECK(checksum(slot.words) == slot.digest);
            }
        }
        if (now >= start && report.state == wtp::EngineState::Armed) {
            report.state = wtp::EngineState::Running;
        }
        return report;
    }
    bool output_active() const override {
        return active;
    }
    void consume() {
        auto& slot = slots[report.completed_blocks % 2];
        CHECK(slot.held && slot.sequence == report.completed_blocks);
        CHECK(checksum(slot.words) == slot.digest);
        slot.held = false;
        report.consumed_samples += slot.samples;
        ++report.completed_blocks;
        report.state = report.consumed_samples == total ? wtp::EngineState::Complete
                                                        : wtp::EngineState::Running;
    }
};

void oracle_test() {
    const std::array<std::uint64_t, 12> lengths{1,      31, 33,    524291, 97,    13,
                                                524300, 41, 65537, 65539,  65541, 65543};
    auto job = job_for(lengths);
    job.events[4].rf_on = false;
    job.events[4].frequency_nhz.reset();
    const auto plan = rf::plan_job(job);
    CHECK(plan);
    for (auto chunk : {1U, 7U, 16384U}) {
        rf::Waveform generator;
        generator.reset(*plan);
        std::vector<std::uint32_t> words(chunk);
        std::uint32_t phase = 0;
        std::uint64_t cursor = 0;
        std::size_t segment = 0;
        while (cursor < plan->total_samples) {
            const auto count = generator.render(words);
            CHECK(count > 0);
            for (std::uint64_t i = 0; i < count; ++i) {
                const auto increment = plan->segments[segment].increment;
                const auto expected = increment == 0 ? 0 : phase >> 31;
                CHECK(((words[i / 32] >> (i % 32)) & 1U) == expected);
                phase += increment;
                if (++cursor == plan->segments[segment].end_sample) {
                    ++segment;
                }
            }
            for (auto i = count; i < words.size() * 32; ++i) {
                CHECK(((words[i / 32] >> (i % 32)) & 1U) == 0);
            }
            CHECK(generator.phase() == phase);
        }
        CHECK(generator.render(words) == 0);
        CHECK(std::all_of(words.begin(), words.end(), [](auto word) { return word == 0; }));
    }
}

void planner_test() {
    // Independent exact-rational Python fixtures for each supported clock.
    constexpr std::array<std::array<std::uint64_t, 4>, 3> fixtures{
        {{3570100014097989ULL, 3570101458579302ULL, 3570102933794260ULL, 3570104409009218ULL},
         {3570100004319102ULL, 3570101450197399ULL, 3570102928206325ULL, 3570104406215250ULL},
         {3570100001525134ULL, 3570101468358189ULL, 3570102935191244ULL, 3570104402024299ULL}}};
    const auto& expected = fixtures[rf::sample_rate == 132000000   ? 0
                                    : rf::sample_rate == 138000000 ? 1
                                                                   : 2];
    for (std::size_t i = 0; i < 4; ++i)
        CHECK(rf::realized_nhz(rf::increments[i]) == expected[i]);
    auto job = tone_job((rf::sample_rate / 375 * 256));
    auto plan = rf::plan_job(job);
    CHECK(plan && plan->total_samples == (rf::sample_rate / 375 * 256));
    auto invalid = job;
    invalid.allow_frequency_adjustment = false;
    CHECK(!rf::plan_job(invalid));
    invalid.events[0].frequency_nhz = rf::realized_nhz(rf::increments[0]);
    CHECK(rf::plan_job(invalid));
    for (unsigned kind = 0; kind < 12; ++kind) {
        invalid = job;
        switch (kind) {
        case 0:
            invalid.events[0].frequency_nhz = std::numeric_limits<std::uint64_t>::max();
            break;
        case 1:
            invalid.events[0].duration_ns = std::numeric_limits<std::uint64_t>::max();
            break;
        case 2:
            invalid.total_duration_ns = std::numeric_limits<std::uint64_t>::max();
            break;
        case 3:
            invalid.events[0].offset_ns = 1;
            break;
        case 4:
            invalid.mode = "qrss";
            break;
        case 5:
            invalid.events.clear();
            break;
        case 6:
            invalid.events[0].rf_on = false;
            break;
        case 7:
            invalid.events[0].frequency_nhz.reset();
            break;
        case 8:
            invalid.total_duration_ns = invalid.events[0].duration_ns = 1;
            break;
        case 10:
            invalid.job_id = std::string(5000, 'a');
            break;
        case 11:
            invalid.job_id = std::string(32, '0');
            break;
        case 9:
            invalid.profile = "other";
            break;
        }
        CHECK(!rf::plan_job(invalid));
    }
    std::array<std::uint64_t, 162> frame;
    frame.fill((rf::sample_rate / 375 * 256));
    plan = rf::plan_job(job_for(frame));
    CHECK(plan && plan->total_samples == rf::sample_rate / 125 * 13824);
    invalid = job_for(frame);
    invalid.events.push_back(invalid.events.back());
    CHECK(!rf::plan_job(invalid));
}

void correction_test() {
    CHECK(rf::corrected_increment(4, 0) == 0);
    CHECK(rf::corrected_increment(0, -1000000000) == 0);
    const auto job = job_for(std::array<std::uint64_t, 4>{100003, 100007, 100009, 100019});
    const auto normal = rf::plan_job(job);
    for (const auto ppb : {-100000, -2222, 0, 2222, 100000}) {
        const auto plan = rf::plan_job(job, ppb);
        CHECK(plan && plan->total_samples == normal->total_samples);
        rf::Waveform corrected, independent;
        corrected.reset(*plan);
        independent.reset(*normal);
        std::uint32_t phase = 0;
        std::uint64_t position = 0;
        std::size_t segment = 0;
        std::array<std::uint32_t, 257> words{};
        while (position < plan->total_samples) {
            const auto count = corrected.render(words);
            for (std::uint64_t bit = 0; bit < count; ++bit) {
                CHECK(((words[bit / 32] >> (bit % 32)) & 1U) == phase >> 31);
                phase += plan->segments[segment].increment;
                if (++position == plan->segments[segment].end_sample)
                    ++segment;
            }
            // Interleaved default rendering cannot replace corrected tables.
            (void)independent.render(words);
        }
        for (unsigned tone = 0; tone < 4; ++tone) {
            const auto exact = static_cast<long double>(rf::increments[tone]) * 1000000000.L /
                               (1000000000.L + ppb);
            CHECK(std::abs(static_cast<long double>(plan->tone_increments[tone]) - exact) <= .5L);
        }
    }
    CHECK(!rf::plan_job(job, 100001) && !rf::plan_job(job, -100001));
    auto strict = job;
    strict.allow_frequency_adjustment = false;
    CHECK(!rf::plan_job(strict, 2222));
    TestSink sink;
    rf::StreamEngine engine(sink);
    CHECK(!engine.set_frequency_correction_ppb(100001));
    CHECK(engine.set_frequency_correction_ppb(2222));
    CHECK(engine.prepare(job).accepted);
    CHECK(!engine.set_frequency_correction_ppb(0));
    CHECK(engine.begin(job, 100));
    CHECK(!engine.set_frequency_correction_ppb(0));
    CHECK(engine.disable(200));
    CHECK(engine.set_frequency_correction_ppb(0));
}

void lifecycle_test() {
    TestSink sink;
    rf::StreamEngine engine(sink);
    const auto job = tone_job(rf::block_samples * 4 + 17);
    auto prepared = engine.prepare(job);
    CHECK(prepared.accepted && prepared.adjustments.size() == 1);
    CHECK(prepared.adjustments[0].realized_frequency_nhz == rf::realized_nhz(rf::increments[0]));
    auto invalid = job;
    invalid.events[0].frequency_nhz = 1;
    CHECK(!engine.prepare(invalid).accepted);
    CHECK(!engine.begin(invalid, 100));
    const auto before = allocations;
    CHECK(engine.begin(job, 100));
    CHECK(!engine.begin(job, 100));
    CHECK(engine.poll(99).state == wtp::EngineState::Armed);
    CHECK(engine.poll(100).state == wtp::EngineState::Running);
    CHECK(!engine.prepare(job).accepted);
    while (sink.report.consumed_samples < sink.total) {
        sink.consume();
        const auto report = engine.poll(100 + ns_at(sink.report.consumed_samples));
        CHECK(report.state == (sink.report.consumed_samples == sink.total
                                   ? wtp::EngineState::Complete
                                   : wtp::EngineState::Running));
    }
    CHECK(engine.disable(100 + job.total_duration_ns));
    CHECK(allocations == before);
    CHECK(!engine.begin(job, 100)); // Disable invalidates prepared data.
    CHECK(engine.prepare(job).accepted);
    CHECK(!engine.begin(job, std::numeric_limits<std::uint64_t>::max()));
    CHECK(engine.begin(job, 100));
    CHECK(engine.disable(101));
    CHECK(engine.poll(102).state == wtp::EngineState::Idle);
}

void faults_test() {
    for (unsigned kind = 0; kind < 12; ++kind) {
        TestSink sink;
        rf::StreamEngine engine(sink);
        auto job = tone_job(rf::block_samples * 4);
        CHECK(engine.prepare(job).accepted);
        CHECK(engine.begin(job, 100));
        CHECK(engine.poll(100).state == wtp::EngineState::Running);
        switch (kind) {
        case 0:
            ++sink.report.epoch;
            break;
        case 1:
            sink.report.completed_blocks = 100;
            break;
        case 2:
            sink.report.state = wtp::EngineState::Failed;
            break;
        case 3:
            sink.consume();
            sink.consume();
            break; // Both buffers exhausted.
        case 4:
            sink.report.state = wtp::EngineState::Complete;
            break;
        case 5:
            sink.report.consumed_samples = sink.total + 1;
            break;
        case 6:
            sink.consume();
            sink.reject_submit = true;
            break;
        case 7:
            sink.consume();
            CHECK(engine.poll(100 + ns_at(rf::block_samples)).state == wtp::EngineState::Running);
            sink.report.completed_blocks = 0;
            break;
        case 9:
            sink.report.consumed_samples = rf::block_samples;
            break; // A completed block was not released in the atomic snapshot.
        case 10:
            sink.report.consumed_samples = 1;
            break; // Progress before the launch time.
        case 11:
            sink.consume();
            CHECK(engine.poll(100 + ns_at(rf::block_samples)).state == wtp::EngineState::Running);
            sink.report.consumed_samples = 0;
            break;
        case 8:
            break; // Missing completion at the job's hard end.
        }
        const auto now =
            kind == 8 ? 100 + job.total_duration_ns : 100 + ns_at(rf::block_samples * 2);
        CHECK(engine.poll(kind == 10 ? 99 : now).state == wtp::EngineState::Failed);
        CHECK(!engine.begin(job, now));
        CHECK(engine.disable(now));
    }
    for (unsigned kind = 0; kind < 3; ++kind) {
        TestSink sink;
        rf::StreamEngine engine(sink);
        const auto job = tone_job(1000);
        CHECK(engine.prepare(job).accepted);
        if (kind == 0) {
            sink.reject_submit = true;
        }
        if (kind == 1) {
            sink.reject_arm = true;
        }
        if (kind == 2) {
            sink.reject_stop = true;
            sink.active = true;
        }
        CHECK(!engine.begin(job, 100));
        CHECK(engine.poll(100).state == wtp::EngineState::Failed);
        if (kind == 2) {
            CHECK(engine.output_active());
            CHECK(!engine.disable(101));
            CHECK(!engine.prepare(job).accepted);
        }
        sink.reject_stop = false;
        CHECK(engine.disable(102));
    }
}

class Clock final : public wtp::Clock {
  public:
    std::uint64_t now = 1'000'000'000;
    wtp::ClockSnapshot snapshot() const override {
        return {wtp::ClockState::Synchronized, now, now, 0, 0, wtp::LeapState::Normal, {}};
    }
};
class Identity final : public wtp::IdentitySource {
  public:
    std::string new_boot_id() override {
        return std::string(32, '9');
    }
};
wtp::Request request(std::string op, wtp::RequestBody body, char id) {
    return {"WTP/1",
            std::string(32, '1'),
            std::string(32, id),
            "local",
            std::move(op),
            wtp::sha256(std::span(reinterpret_cast<const std::uint8_t*>(&id), 1)),
            std::move(body)};
}

void service_test() {
    for (unsigned action = 0; action < 4; ++action) {
        Clock clock;
        Identity identity;
        TestSink sink;
        rf::StreamEngine engine(sink);
        wtp::JobService service(clock, engine, identity);
        CHECK(service.handle(request("HELLO", wtp::HelloBody{{"WTP/1"}}, 'a')).ok);
        CHECK(service.handle(request("CLAIM", wtp::ClaimBody{std::string(32, '2'), 5000}, 'b')).ok);
        const auto job = tone_job(rf::block_samples * 3);
        const auto load = service.handle(request("LOAD", job, 'c'));
        CHECK(load.ok && load.adjustments.size() == 1);
        const auto start = clock.now + 100'000'000;
        CHECK(service.handle(request("ARM", wtp::ArmBody{job.job_id, start, 1000}, 'd')).ok);
        clock.now = start;
        service.poll();
        CHECK(service.status().state == wtp::State::Running);
        if (action == 2 || action == 3) {
            sink.report.state = wtp::EngineState::Failed;
            if (action == 3) {
                sink.reject_stop = true;
                sink.active = true;
            }
            service.poll();
            CHECK(service.status().state == wtp::State::Failed);
            CHECK(service.status().terminal_records.back().error ==
                  (action == 3 ? wtp::ErrorCode::OutputStateUnknown : wtp::ErrorCode::DeviceFault));
            CHECK(service.status().output_active == (action == 3));
            sink.reject_stop = false;
            CHECK(engine.disable(clock.now));
        } else if (action == 1) {
            CHECK(service.handle(request("ABORT", wtp::AbortBody{job.job_id}, 'e')).ok);
            CHECK(service.status().state == wtp::State::Aborted);
        } else {
            for (unsigned block = 1; block <= 3; ++block) {
                sink.consume();
                clock.now = start + ns_at(block * rf::block_samples);
                service.poll();
            }
            CHECK(service.status().state == wtp::State::Complete);
        }
        CHECK(!service.status().output_active);
    }
}

void benchmark() {
    std::array<std::uint64_t, 162> lengths;
    lengths.fill((rf::sample_rate / 375 * 256));
    const auto job = job_for(lengths);
    const auto plan = rf::plan_job(job);
    CHECK(plan);
    rf::Waveform generator;
    generator.reset(*plan);
    std::array<std::uint32_t, rf::block_words> words;
    std::uint64_t digest = 0;
    double maximum_us = 0;
    std::size_t blocks = 0;
    const auto start = std::chrono::steady_clock::now();
    while (generator.position() < plan->total_samples) {
        const auto before = std::chrono::steady_clock::now();
        (void)generator.render(words);
        const auto after = std::chrono::steady_clock::now();
        maximum_us =
            std::max(maximum_us, std::chrono::duration<double, std::micro>(after - before).count());
        digest ^= checksum(words);
        ++blocks;
    }
    const auto elapsed =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    std::cout << "HOST ONLY: blocks=" << blocks << " elapsed_s=" << elapsed
              << " max_render_us=" << maximum_us << " checksum=" << digest
              << " sizeof_plan=" << sizeof(rf::Plan)
              << " sizeof_engine=" << sizeof(rf::StreamEngine)
              << "\nNo RP2350 timing qualification.\n";
}
} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && std::string_view(argv[1]) == "--benchmark") {
            benchmark();
            return 0;
        }
        CHECK(argc == 1);
        oracle_test();
        planner_test();
        correction_test();
        lifecycle_test();
        faults_test();
        service_test();
        std::cout << "RF stream checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

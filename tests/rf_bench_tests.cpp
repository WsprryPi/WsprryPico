#include "encoding/wspr.hpp"
#include "rf/bench.hpp"

#include <iostream>
#include <stdexcept>

using namespace wsprrypico;
#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x))                                                                                  \
            throw std::runtime_error(#x);                                                          \
    } while (false)
class Clock final : public rf::BenchClock {
  public:
    mutable std::uint64_t now = 1000000;
    std::uint64_t now_ns() const override {
        return now;
    }
};
class Engine final : public wtp::RfEngine {
  public:
    unsigned begins = 0, prepares = 0, stops = 0;
    bool fail_stop = false, fail_prepare = false, fail_begin = false, active = false;
    std::uint64_t start = 0;
    wtp::Job prepared_job;
    wtp::EngineState state = wtp::EngineState::Idle;
    bool set_frequency_correction_ppb(std::int32_t) override {
        return !active;
    }
    wtp::PrepareResult prepare(const wtp::Job& job) override {
        ++prepares;
        prepared_job = job;
        CHECK(rf::plan_job(job).has_value());
        return {!fail_prepare, {}};
    }
    bool begin(const wtp::Job&, std::uint64_t when) override {
        ++begins;
        start = when;
        state = wtp::EngineState::Armed;
        return !fail_begin;
    }
    wtp::EngineReport poll(std::uint64_t) override {
        return {state, active};
    }
    bool disable(std::uint64_t) override {
        ++stops;
        if (!fail_stop)
            active = false;
        return !fail_stop;
    }
    bool output_active() const override {
        return active;
    }
};
bool ok(const std::string& text) {
    return text.find("\"ok\":true") != text.npos;
}
int main() {
    try {
        const auto encoded = encoding::wspr_type1("AA0NT", "EM18", 20);
        CHECK(encoded);
        constexpr std::string_view golden =
            "13200002302011100030232111300002223001230022201211203321000310302221301030323003003233"
            "2021321030223220203223221310310213010221110002210302110200222310303320011002";
        for (unsigned i = 0; i < 162; ++i)
            CHECK((*encoded)[i] == golden[i] - '0');
        const auto encoded37 = encoding::wspr_type1("AA0NT", "EM18", 37);
        CHECK(encoded37);
        constexpr std::string_view golden37 =
            "13220200302213120030232311300200223201230220201213223121020110322221321030323001023231"
            "2023321232223022203021221110310011010221130002210302110202202112323320031202";
        for (unsigned i = 0; i < 162; ++i)
            CHECK((*encoded37)[i] == golden37[i] - '0');
        for (auto call : {"", "A", "AA", "AAAAAA", "AA0NT/1", "aa0nt", "AA0 N", "AA0NTXQ", "AA0"})
            CHECK(!encoding::wspr_type1(call, "EM18", 20));
        for (auto grid : {"", "EM18IG", "SM18", "EM1A", "em18"})
            CHECK(!encoding::wspr_type1("AA0NT", grid, 20));
        CHECK(!encoding::wspr_type1("AA0NT", "EM18", 21));
        CHECK(!encoding::wspr_type1("AA0NT", "EM18", 61));
        CHECK(encoding::wspr_type1("K1ABC", "AA00", 0));
        CHECK(encoding::wspr_type1("A12ABC", "RR99", 60));
        rf::prepare_word_tables();
        for (unsigned tone = 0; tone < 4; ++tone) {
            const auto check = [tone](std::uint32_t phase) {
                const auto original = phase;
                std::uint32_t word = 0;
                for (unsigned bit = 0; bit < 32; ++bit) {
                    word |= (phase >> 31) << bit;
                    phase += rf::increments[tone];
                }
                CHECK(rf::packed_word(original, tone) == word);
            };
            for (unsigned bit = 0; bit < 32; ++bit)
                for (std::uint32_t edge : {0U, 0x80000000U})
                    for (std::uint32_t delta : {0xffffffffU, 0U, 1U})
                        check(edge - bit * rf::increments[tone] + delta);
            for (unsigned bucket = 0; bucket < 1024; ++bucket)
                for (std::uint32_t delta : {0xffffffffU, 0U, 1U})
                    check((bucket << 22) + delta);
        }
        const auto frame = rf::diagnostic_frame();
        CHECK(frame.events.size() == 162 && frame.total_duration_ns == 110592000000ULL);
        const auto frame_plan = rf::plan_job(frame);
        CHECK(frame_plan && frame_plan->total_samples == rf::sample_rate / 125 * 13824);
        for (unsigned i = 0; i < 162; ++i) {
            CHECK(frame_plan->segments[i].end_sample ==
                  (std::uint64_t{i} + 1) * (rf::sample_rate / 375 * 256));
            CHECK(frame_plan->segments[i].increment == rf::increments[i % 4]);
        }
        Clock clock;
        Engine engine;
        rf::Bench bench(engine, clock);
        CHECK(bench.command("CAPS").find("\"sample_rate_hz\":" + std::to_string(rf::sample_rate)) !=
              std::string::npos);
        CHECK(ok(bench.command("CAPS")) && ok(bench.command("STATUS")));
        for (auto text : {"FRAME", "FRAME 99", "FRAME 10001", "FRAME 100 extra", "RUN",
                          "RUN -1 10 100", "RUN 4 10 100", "RUN 0 0 100", "RUN 0 10001 100",
                          "RUN 0 1 99", "RUN 0 1 10001", "RUN 0 1 100 extra", "RUN 0 1 100\nSTOP",
                          "RUN 9999999999999999999999 1 100", "BENCH 0", "BENCH 4097", "BENCH 2x"})
            CHECK(!ok(bench.command(text)));
        CHECK(!ok(bench.command("CORRECTION 100001")));
        CHECK(!ok(bench.command("CORRECTION NaN")));
        CHECK(ok(bench.command("CORRECTION 2222")));
        CHECK(bench.status().find("\"correction_ppb\":2222") != std::string::npos);
        CHECK(ok(bench.command("CORRECTION 0")));
        CHECK(engine.begins == 0 && engine.prepares == 0);
        CHECK(ok(bench.command("BENCH 3")));
        CHECK(!ok(bench.command("RUN 0 100 100")));
        for (unsigned i = 0; i < 3; ++i) {
            clock.now += 1000;
            bench.poll();
        }
        CHECK(!bench.busy() && engine.begins == 0);
        CHECK(bench.status().find("benchmark_complete") != std::string::npos);
        CHECK(bench.status().find("\"benchmark_blocks\":3") != std::string::npos);
        CHECK(ok(bench.command("RUN 2 100 100")));
        CHECK(engine.start == clock.now + 100000000 && !engine.active);
        CHECK(!ok(bench.command("RUN 0 100 100")) && engine.begins == 1);
        engine.state = wtp::EngineState::Running;
        engine.active = true;
        clock.now = engine.start;
        bench.poll();
        CHECK(bench.busy());
        CHECK(!ok(bench.command("CORRECTION 2222")));
        engine.state = wtp::EngineState::Complete;
        engine.active = false;
        clock.now += 100000000;
        bench.poll();
        CHECK(!bench.busy() && bench.status().find("\"state\":\"complete\"") != std::string::npos);
        engine.fail_begin = true;
        CHECK(!ok(bench.command("RUN 0 1 100")));
        engine.fail_begin = false;
        CHECK(!ok(bench.command("RUN 0 1 100"))); // Failed run needs lifecycle recovery.
        CHECK(ok(bench.command("STOP")));
        CHECK(ok(bench.command("RUN 0 1 100")));
        engine.fail_stop = true;
        CHECK(!ok(bench.command("STOP")) && !bench.busy());
        engine.fail_stop = false;
        CHECK(ok(bench.command("STOP")));
        CHECK(ok(bench.command("BENCH 4096")));
        CHECK(ok(bench.command("STOP")) && !bench.busy());
        CHECK(!ok(bench.command("WSPR AA0NT EM18 21 100")));
        CHECK(!ok(bench.command("WSPR AA0NT EM18 20 100 extra")));
        CHECK(ok(bench.command("WSPR AA0NT EM18 20 100")));
        CHECK(engine.prepared_job.events.size() == 162);
        CHECK(engine.prepared_job.total_duration_ns == 110592000000ULL);
        for (unsigned i = 0; i < 162; ++i)
            CHECK(engine.prepared_job.events[i].frequency_nhz ==
                  rf::base_nhz + (*encoded)[i] * rf::spacing_nhz);
        CHECK(bench.busy());
        CHECK(!ok(bench.command("WSPR AA0NT EM18 20 100")));
        CHECK(ok(bench.command("STOP")));
        CHECK(ok(bench.command("FRAME 100")));
        CHECK(bench.busy());
        CHECK(!ok(bench.command("FRAME 100")));
        CHECK(ok(bench.command("STOP")));
        CHECK(ok(bench.command("FRAME 100")));
        CHECK(ok(bench.command("STOP")));
        std::cout << "RF bench checks passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

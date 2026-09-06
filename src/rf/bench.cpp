#include "rf/bench.hpp"

#include <algorithm>
#include <charconv>
#include <limits>

namespace wsprrypico::rf {
namespace {
std::optional<unsigned> number(std::string_view text) {
    if (text.empty())
        return {};
    unsigned value = 0;
    const auto result = std::from_chars(text.data(), text.data() + text.size(), value);
    if (result.ec != std::errc{} || result.ptr != text.data() + text.size())
        return {};
    return value;
}
wtp::Job tone(unsigned index, unsigned duration_ms) {
    const auto ns = std::uint64_t{duration_ms} * 1000000;
    return {std::string(32, 'b'),
            "rf-events/1",
            "tone",
            ns,
            {{0, ns, true, base_nhz + index * spacing_nhz}},
            true};
}
std::string error(std::string_view reason) {
    return "{\"ok\":false,\"error\":\"" + std::string(reason) + "\"}\n";
}
} // namespace

wtp::Job diagnostic_frame() {
    wtp::Job job{std::string(32, 'b'), "rf-events/1", "wspr", 110592000000ULL, {}, true};
    job.events.reserve(162);
    for (unsigned i = 0; i < 162; ++i) {
        const auto start = (std::uint64_t{i} * 2048000000 + 1) / 3;
        const auto end = (std::uint64_t{i + 1} * 2048000000 + 1) / 3;
        job.events.push_back({start, end - start, true, base_nhz + (i % 4) * spacing_nhz});
    }
    return job;
}

std::string Bench::status() const {
    return "{\"ok\":true,\"diagnostic\":\"" + std::string(engine_.diagnostic()) +
           "\",\"state\":\"" + state_ +
           "\",\"output_active\":" + (engine_.output_active() ? "true" : "false") +
           ",\"correction_ppb\":" + std::to_string(correction_ppb_) +
           ",\"start_ns\":" + std::to_string(start_ns_) +
           ",\"ended_ns\":" + std::to_string(ended_ns_) +
           ",\"max_poll_gap_ns\":" + std::to_string(max_poll_gap_ns_) +
           ",\"benchmark_blocks\":" + std::to_string(rendered_) +
           ",\"max_render_ns\":" + std::to_string(max_render_ns_) +
           ",\"benchmark_ns\":" + std::to_string(benchmark_ns_) +
           ",\"checksum\":" + std::to_string(checksum_) + "}\n";
}

std::string Bench::command(std::string_view line) {
    if (line == "STATUS")
        return status();
    if (line == "CAPS") {
        return "{\"ok\":true,\"interface\":\"pico-rf-bench/1\",\"engine\":\"pio-dma-gp2\","
               "\"clock\":\"monotonic-relative-only\",\"sample_rate_hz\":" +
               std::to_string(sample_rate) +
               ","
               "\"gpio\":2,\"header_pin\":4,\"tones\":4,\"base_hz\":3570100,"
               "\"spacing_hz\":1.46484375,\"duration_ms\":[1,10000],"
               "\"delay_ms\":[100,10000],\"benchmark_blocks\":[1,4096],"
               "\"correction_ppb_range\":[-100000,100000],\"frame\":\"cycle4-162\",\"frame_"
               "duration_ns\":110592000000}\n";
    }
    if (line == "STOP") {
        benchmarking_ = running_ = false;
        const auto now = clock_.now_ns();
        const bool stopped = engine_.disable(now + 10000000) && !engine_.output_active();
        state_ = stopped ? "stopped" : "failed";
        ended_ns_ = clock_.now_ns();
        return stopped ? status() : error("stop_failed");
    }
    if (busy())
        return error("busy");
    if (state_ == "failed")
        return error("stop_required_after_failure");
    if (line.starts_with("CORRECTION ")) {
        const auto text = line.substr(11);
        std::int32_t ppb = 0;
        const auto parsed = std::from_chars(text.data(), text.data() + text.size(), ppb);
        if (text.empty() || parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size() ||
            ppb < -max_correction_ppb || ppb > max_correction_ppb)
            return error("invalid_correction");
        if (!engine_.set_frequency_correction_ppb(ppb))
            return error("correction_rejected");
        correction_ppb_ = ppb;
        return status();
    }
    if (line.starts_with("BENCH ")) {
        const auto count = number(line.substr(6));
        if (!count || *count == 0 || *count > 4096)
            return error("invalid_benchmark");
        if (engine_.output_active())
            return error("output_active");
        plan_ = plan_job(tone(0, 10000), correction_ppb_);
        if (!plan_)
            return error("plan_failed");
        waveform_.reset(*plan_);
        remaining_ = *count;
        rendered_ = 0;
        checksum_ = max_render_ns_ = benchmark_ns_ = max_poll_gap_ns_ = 0;
        start_ns_ = last_poll_ns_ = clock_.now_ns();
        ended_ns_ = 0;
        benchmarking_ = true;
        state_ = "benchmarking";
        return status();
    }
    const bool frame = line.starts_with("FRAME ");
    unsigned index = 0, duration = 0;
    std::optional<unsigned> delay;
    if (frame) {
        delay = number(line.substr(6));
    } else {
        if (!line.starts_with("RUN "))
            return error("unknown_command");
        auto rest = line.substr(4);
        const auto first = rest.find(' ');
        if (first == rest.npos)
            return error("invalid_run");
        const auto tone_index = number(rest.substr(0, first));
        rest.remove_prefix(first + 1);
        const auto second = rest.find(' ');
        if (second == rest.npos)
            return error("invalid_run");
        const auto length = number(rest.substr(0, second));
        delay = number(rest.substr(second + 1));
        if (!tone_index || *tone_index > 3 || !length || *length < 1 || *length > 10000)
            return error("invalid_run");
        index = *tone_index;
        duration = *length;
    }
    if (!delay || *delay < 100 || *delay > 10000)
        return error("invalid_delay");
    const auto now = clock_.now_ns();
    constexpr auto reserve = std::uint64_t{121'000'001'000};
    if (now > std::numeric_limits<std::uint64_t>::max() - reserve)
        return error("clock_overflow");
    if (!engine_.disable(now + 10000000) || engine_.output_active()) {
        state_ = "failed";
        return error("stop_failed");
    }
    const auto job = frame ? diagnostic_frame() : tone(index, duration);
    if (!engine_.prepare(job).accepted)
        return error("prepare_failed");
    // Preparation can be expensive: choose the epoch only after it completes.
    const auto prepared = clock_.now_ns();
    if (prepared > std::numeric_limits<std::uint64_t>::max() - reserve) {
        (void)engine_.disable(prepared);
        state_ = "failed";
        return error("clock_overflow");
    }
    start_ns_ = ((prepared + 999) / 1000) * 1000 + std::uint64_t{*delay} * 1000000;
    ended_ns_ = max_poll_gap_ns_ = 0;
    last_poll_ns_ = prepared;
    if (!engine_.begin(job, start_ns_)) {
        (void)engine_.disable(clock_.now_ns() + 10000000);
        state_ = "failed";
        return error("begin_failed");
    }
    running_ = true;
    state_ = "armed";
    return status();
}

void Bench::poll() {
    if (!busy())
        return;
    const auto now = clock_.now_ns();
    if (now < last_poll_ns_) {
        benchmarking_ = running_ = false;
        (void)engine_.disable(now + 10000000);
        state_ = "failed";
        return;
    }
    max_poll_gap_ns_ = std::max(max_poll_gap_ns_, now - last_poll_ns_);
    last_poll_ns_ = now;
    if (benchmarking_) {
        if (waveform_.position() == plan_->total_samples)
            waveform_.reset(*plan_);
        const auto before = clock_.now_ns();
        const auto samples = waveform_.render(buffer_);
        const auto elapsed = clock_.now_ns() - before;
        max_render_ns_ = std::max(max_render_ns_, elapsed);
        benchmark_ns_ += elapsed;
        for (std::size_t i = 0; i < (samples + 31) / 32; ++i)
            checksum_ += buffer_[i];
        ++rendered_;
        if (--remaining_ == 0) {
            benchmarking_ = false;
            state_ = "benchmark_complete";
            ended_ns_ = clock_.now_ns();
        }
        return;
    }
    const auto report = engine_.poll(now);
    if (report.state == wtp::EngineState::Armed)
        return;
    if (report.state == wtp::EngineState::Running) {
        state_ = "running";
        return;
    }
    running_ = false;
    ended_ns_ = clock_.now_ns();
    const auto stopped = engine_.disable(ended_ns_ + 10000000) && !engine_.output_active();
    state_ = !stopped                                     ? "failed"
             : report.state == wtp::EngineState::Complete ? "complete"
             : report.state == wtp::EngineState::Missed   ? "missed"
                                                          : "failed";
}
} // namespace wsprrypico::rf

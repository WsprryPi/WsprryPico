// SPDX-License-Identifier: MIT
#include "application/resources.hpp"
#include "hardware/gpio.h"
#include "hardware/pico/filter_outputs.hpp"
#include "network_support.hpp"
#include "rf/pio_dma_sink.hpp"
#include "standalone/frequency_policy_engine.hpp"

#include <tuple>
using namespace wsprrypico;
namespace {
bool levels[30]{}, directions[30]{};
unsigned wrong_gp = 99;
std::vector<std::string> gpio_trace;
hardware::FilterSettings selected() {
    hardware::FilterSettings s;
    s.required = true;
    s.output_count = 2;
    s.outputs[0] = {1, 3, "HF", true};
    s.outputs[1] = {2, 4, "LF", false};
    s.range_count = 2;
    s.ranges[0] = {"20m", 1, 14'000'000, 14'350'000};
    s.ranges[1] = {"40m", 2, 7'000'000, 7'300'000};
    return s;
}
struct Member {
    network_test::Fixture f;
    standalone::Store& initialize() {
        REQUIRE(f.store.save(*standalone::parse_config(network_test::config)));
        return f.store;
    }
    standalone::Scheduler scheduler{initialize(), f.service};
    network::BrowserApi api{f.service, f.store, scheduler, f.network, std::string(32, 'a'), "test"};
    network::HttpResponse call(std::string method, std::string body = {},
                               std::string version = "transmitter-filter-selector/1",
                               bool stale = false, bool wrong = false) {
        const auto target =
            application::target(std::string(32, wrong ? 'b' : 'a'), f.service.status().boot_id);
        network::HttpRequest r{method,
                               "/api/v1/filter-selector",
                               body.empty()
                                   ? ""
                                   : "{\"schema\":" + wtp::json::quote(version) +
                                         ",\"target\":" + target + ",\"settings\":" + body + "}",
                               {{"host", "127.0.0.1:8443"},
                                {"origin", "https://127.0.0.1:8443"},
                                {"content-type", "application/json"},
                                {"x-wsprrypico-request", "1"},
                                {"if-match", stale ? "\"stale\"" : api.revision()}}};
        return api.handle(r, "test", "127.0.0.1:8443");
    }
};
void management_storage() {
    Member m;
    const auto initial = m.call("GET");
    REQUIRE(initial.status == 200);
    const auto sequence = m.f.store.config_sequence();
    const auto s = selected();
    const auto json = hardware::serialize_filters(s);
    REQUIRE(hardware::parse_filters(json) == s);
    for (const auto bad : {"null", "[]", "{}", "{\"policy\":true}",
                           "{\"policy\":\"required\",\"release_ms\":0,\"release_ms\":0,\"settle_"
                           "ms\":0,\"selectors\":[],\"ranges\":[]}"}) {
        REQUIRE(m.call("PUT", bad).status == 400);
        REQUIRE(m.f.store.config_sequence() == sequence);
    }
    for (const auto version : {"transmitter-filter-selector/0", "transmitter-filter-selector/2"})
        REQUIRE(m.call("PUT", json, version).status == 400);
    REQUIRE(m.call("PUT", json, "transmitter-filter-selector/1", true).status == 412);
    REQUIRE(m.call("PUT", json, "transmitter-filter-selector/1", false, true).status == 409);
    for (unsigned gp : {2U, 14U, 23U, 25U, 29U}) {
        auto bad = s;
        bad.outputs[0].gp = gp;
        REQUIRE(m.call("PUT", hardware::serialize_filters(bad)).status == 400);
    }
    auto bad = s;
    bad.outputs[1].gp = 3;
    REQUIRE(m.call("PUT", hardware::serialize_filters(bad)).status == 400);
    bad = s;
    bad.ranges[1].low_hz = 14'000'000;
    bad.ranges[1].high_hz = 15'000'000;
    REQUIRE(m.call("PUT", hardware::serialize_filters(bad)).status == 400);
    bad = s;
    bad.release_ms = 251;
    REQUIRE(m.call("PUT", hardware::serialize_filters(bad)).status == 400);
    REQUIRE(m.f.store.config_sequence() == sequence);
    REQUIRE(m.call("PUT", json).status == 200);
    REQUIRE(m.f.store.filters() == s && m.scheduler.hardware_restart_required() &&
            m.f.service.output_inhibited());
    REQUIRE(m.scheduler.active_filters() == hardware::FilterSettings{});
    const auto saved_config = m.f.store.config();
    REQUIRE(m.f.store.save_logging({true, 4}));
    REQUIRE(m.f.store.reserve(10'000'000'000));
    standalone::Store reboot(m.f.flash);
    REQUIRE(reboot.load() && reboot.filters() == s && reboot.config() == saved_config);
    REQUIRE(reboot.logging_settings().enabled && reboot.watermark() == 10'000'000'000);
    // Ordinary current Config and logging writes preserve the independent settings.
    auto config = *m.f.store.config();
    config.power_dbm = 30;
    REQUIRE(m.f.store.save(config));
    REQUIRE(m.f.store.filters() == s);
    config.pins.rf = 3;
    const auto seq = m.f.store.config_sequence();
    REQUIRE(!m.f.store.save(config));
    REQUIRE(m.f.store.config_sequence() == seq);
    REQUIRE(m.call("PUT", hardware::serialize_filters({})).status == 200);
    REQUIRE(m.scheduler.hardware_restart_required()); // A/B/A remains inhibited.
    Member damaged;
    REQUIRE(damaged.call("PUT", json).status == 200);
    damaged.f.flash.bytes[damaged.f.store.config_offset() + 32] ^= 1;
    standalone::Store corrupt(damaged.f.flash);
    REQUIRE(!corrupt.load());
    Member failed;
    failed.f.flash.fail = true;
    REQUIRE(failed.call("PUT", json).status == 503);
    REQUIRE(!failed.f.store.healthy());
}
void admission_and_adapter() {
    auto s = selected();
    rf::FilterCoverage coverage(s);
    coverage.include(14'100'000'000'000'000, 14'100'000'000'000'000);
    REQUIRE(coverage.selection() == 0);
    coverage.include(7'100'000'000'000'000, 7'100'000'000'000'000);
    REQUIRE(coverage.selection() == -2);
    rf::FilterCoverage corrected(s);
    corrected.include(14'000'000'000'000'000, 13'999'999'999'999'999);
    REQUIRE(corrected.selection() == -2);
    s.range_count = 3;
    s.ranges[2] = {"17m", 1, 18'068'000, 18'168'000};
    rf::FilterCoverage shared(s);
    shared.include(14'100'000'000'000'000, 14'100'000'000'000'000);
    shared.include(18'100'000'000'000'000, 18'100'000'000'000'000);
    REQUIRE(shared.selection() == 0);
    hardware::PicoFilterOutputs outputs(s, {});
    REQUIRE(outputs.initialize_inactive());
    REQUIRE(!levels[3] && levels[4]);
    REQUIRE(outputs.activate(1) && !levels[3] && !levels[4]);
    REQUIRE(outputs.inactive() && !levels[3] && levels[4]);
    REQUIRE(outputs.activate(0) && levels[3] && levels[4]);
    wrong_gp = 3;
    REQUIRE(!outputs.verify(0) && !outputs.inactive());
    wrong_gp = 99;
    REQUIRE(outputs.inactive());
    auto invalid = s;
    invalid.outputs[0].gp = 2;
    gpio_trace.clear();
    hardware::PicoFilterOutputs conflict(invalid, {});
    REQUIRE(!conflict.initialize_inactive() && gpio_trace.empty());
}
struct Outputs : rf::FilterOutputs {
    bool active = false, fail = false, bad_verify = false;
    unsigned activated = 0;
    std::uint64_t* now = nullptr;
    std::vector<std::pair<std::string, std::uint64_t>>* trace = nullptr;
    bool initialize_inactive() override {
        return inactive();
    }
    bool inactive() override {
        active = false;
        if (trace)
            trace->push_back({"filter-off", *now});
        return !fail;
    }
    bool activate(unsigned) override {
        active = true;
        ++activated;
        if (trace)
            trace->push_back({"filter-on", *now});
        return !fail;
    }
    bool verify(unsigned) const override {
        return active && !bad_verify;
    }
};
struct Amp : rf::EnableOutput {
    bool active = false, fail = false;
    std::uint64_t* now;
    std::vector<std::pair<std::string, std::uint64_t>>* trace;
    Amp(std::uint64_t& n, std::vector<std::pair<std::string, std::uint64_t>>& t)
        : now(&n), trace(&t) {}
    bool initialize_inactive() override {
        return write(false);
    }
    bool write(bool a) override {
        active = a;
        trace->push_back({a ? "amp-on" : "amp-off", *now});
        return !fail;
    }
    bool verify_active() const override {
        return active;
    }
};
struct Driver : rf::PioDmaHardware {
    Handler handler = nullptr;
    void* context = nullptr;
    std::uint64_t now = 1'000'000'000, wake = 0, epoch = 0, launched = 0;
    bool active_ = false, alarm_fail = false, halt_fail = false;
    std::vector<std::pair<std::string, std::uint64_t>> trace;
    std::uint32_t lock() override {
        return 0;
    }
    void unlock(std::uint32_t) override {}
    bool open(Handler h, void* c) override {
        handler = h;
        context = c;
        return true;
    }
    void force_inactive() override {
        active_ = false;
        trace.push_back({"rf-off", now});
    }
    bool halt(std::uint64_t) override {
        trace.push_back({"halt", now});
        return !halt_fail;
    }
    bool dma(const std::uint32_t*, std::uint32_t, bool, std::uint64_t, std::uint64_t) override {
        return true;
    }
    bool alarm(std::uint64_t at, std::uint64_t e) override {
        wake = at;
        epoch = e;
        return !alarm_fail;
    }
    bool retry_alarm(std::uint64_t at, std::uint64_t e) override {
        return at > now && alarm(at, e);
    }
    rf::LaunchResult launch(std::uint64_t at, std::uint64_t deadline,
                            rf::LaunchEnable enable) override {
        now = std::max(now, at);
        if (now >= deadline || !enable.activate())
            return rf::LaunchResult::Rejected;
        active_ = true;
        launched = now;
        trace.push_back({"rf-on", now});
        return rf::LaunchResult::Launched;
    }
    std::uint64_t launch_observed_ns() const override {
        return launched;
    }
    std::uint64_t now_ns() const override {
        return now;
    }
    bool stalled() const override {
        return false;
    }
    bool active() const override {
        return active_;
    }
    void fire() {
        now = wake;
        handler(context, {rf::DriverEventKind::Alarm, epoch, 0});
    }
};
wtp::Job tone() {
    wtp::Job j;
    j.job_id = std::string(32, '3');
    j.mode = "tone";
    j.allow_frequency_adjustment = true;
    j.events.push_back({0, 1'000'000, true, 14'100'000'000'000'000});
    j.total_duration_ns = 1'000'000;
    return j;
}
void production_admission() {
    network_test::Flash flash;
    standalone::Store store(flash);
    REQUIRE(store.load() && store.save(*standalone::parse_config(network_test::config)));
    REQUIRE(store.save_filters(selected()));
    Driver hw;
    Outputs outputs;
    rf::FilterSelector filters(store.filters(), &outputs);
    REQUIRE(filters.initialize());
    rf::PioDmaSink sink(hw, nullptr, nullptr, &filters);
    rf::StreamEngine stream(sink, &filters);
    standalone::FrequencyPolicyEngine engine(stream, store, 100'000'000'000'000,
                                             68'999'999'000'000'000);
    auto job = tone();
    REQUIRE(engine.prepare(job).accepted);
    REQUIRE(outputs.activated == 0 && !sink.output_active());
    job.events.push_back({1'000'000, 1'000'000, true, 7'100'000'000'000'000});
    job.total_duration_ns = 2'000'000;
    REQUIRE(!engine.prepare(job).accepted && engine.diagnostic() == "filter_coverage_required");
    REQUIRE(outputs.activated == 0 && !sink.output_active());
    job = tone();
    REQUIRE(engine.prepare(job).accepted && engine.diagnostic().empty());
    // A save cannot alter the boot-frozen coverage, even before restart.
    REQUIRE(store.save_filters({}));
    job.events[0].frequency_nhz = 10'140'000'000'000'000;
    REQUIRE(!engine.prepare(job).accepted);
    REQUIRE(outputs.activated == 0);
}
void completion_and_cleanup() {
    for (const bool fail_cleanup : {false, true}) {
        Driver hw;
        Outputs pins;
        pins.now = &hw.now;
        pins.trace = &hw.trace;
        const auto settings = selected();
        rf::FilterSelector filters(settings, &pins);
        REQUIRE(filters.initialize());
        auto job = tone();
        auto plan = rf::plan_job(job);
        REQUIRE(plan && filters.prepare(job, *plan));
        Amp amp_output(hw.now, hw.trace);
        rf::AmplifierEnable amp(&amp_output, {0, 200});
        REQUIRE(amp.initialize());
        rf::PioDmaSink sink(hw, nullptr, &amp, &filters);
        std::array<std::uint32_t, 1> words{};
        REQUIRE(sink.submit(1, 0, words, 32) && sink.arm(1, 2'000'000'000, 32));
        for (unsigned i = 0; i < 10 && !hw.active(); ++i)
            hw.fire();
        REQUIRE(hw.active() && pins.active && amp_output.active);
        hw.handler(hw.context, {rf::DriverEventKind::DmaComplete, 1, 0});
        hw.active_ = false; // Actual driver's zero-tail stop observation.
        hw.handler(hw.context, {rf::DriverEventKind::DmaComplete, 1, 1});
        REQUIRE(sink.poll(hw.now).chain_phase == wtp::ChainPhase::Tail);
        REQUIRE(pins.active && amp_output.active && pins.activated == 1);
        hw.trace.clear();
        amp_output.fail = pins.fail = hw.halt_fail = fail_cleanup;
        hw.fire();
        const auto report = sink.poll(hw.now);
        REQUIRE(report.state ==
                (fail_cleanup ? wtp::EngineState::Failed : wtp::EngineState::Complete));
        REQUIRE(!pins.active && !amp_output.active && !hw.active());
        // Every cleanup attempt runs, in order, even when an earlier one fails.
        REQUIRE(hw.trace.size() >= 4);
        REQUIRE(hw.trace[0].first == "rf-off" && hw.trace[1].first == "amp-off" &&
                hw.trace[2].first == "filter-off" && hw.trace[3].first == "halt");
        REQUIRE(report.filter_selector == (fail_cleanup ? -2 : -1));
        REQUIRE(sink.output_active() == fail_cleanup);
    }
}
void execution() {
    for (const auto& delays : {std::pair{20U, 20U}, std::pair{0U, 0U}, std::pair{250U, 250U}})
        for (const bool amp_enabled : {false, true}) {
            auto s = selected();
            s.release_ms = delays.first;
            s.settle_ms = delays.second;
            Driver hw;
            Outputs pins;
            pins.now = &hw.now;
            pins.trace = &hw.trace;
            rf::FilterSelector filters(s, &pins);
            REQUIRE(filters.initialize());
            auto job = tone();
            auto plan = rf::plan_job(job);
            REQUIRE(plan && filters.prepare(job, *plan));
            Amp amp_output(hw.now, hw.trace);
            rf::AmplifierEnable amplifier(amp_enabled ? &amp_output : nullptr, {200, 0});
            REQUIRE(amplifier.initialize());
            rf::PioDmaSink sink(hw, nullptr, &amplifier, &filters);
            std::array<std::uint32_t, 1> words{};
            REQUIRE(sink.stop(hw.now) && sink.submit(1, 0, words, 32));
            const auto start = 2'000'000'000ULL;
            REQUIRE(sink.arm(1, start, 32));
            for (unsigned i = 0; i < 10 && !hw.active(); ++i)
                hw.fire();
            REQUIRE(hw.active() && hw.launched == start && filters.observation() == 1 &&
                    pins.activated == 1);
            std::uint64_t on = 0, off = 0, amp_on = 0;
            for (const auto& [kind, time] : hw.trace) {
                if (kind == "filter-off" && !on)
                    off = time;
                if (kind == "filter-on")
                    on = time;
                if (kind == "amp-on")
                    amp_on = time;
            }
            REQUIRE(on >= off + std::uint64_t(s.release_ms) * 1'000'000);
            REQUIRE((amp_enabled ? amp_on : start) >= on + std::uint64_t(s.settle_ms) * 1'000'000);
            if (amp_enabled)
                REQUIRE(start >= amp_on + 200'000'000);
            REQUIRE(sink.stop(hw.now));
            REQUIRE(!pins.active && !amp_output.active && !sink.output_active());
            // Interrupted preparation cancels its alarms and never activates a relay.
            REQUIRE(filters.prepare(job, *plan));
            REQUIRE(sink.submit(2, 0, words, 32));
            REQUIRE(sink.arm(2, 3'000'000'000ULL, 32));
            REQUIRE(sink.stop(hw.now));
            hw.fire();
            REQUIRE(!sink.output_active());
        }
    // Late preparation and failed output verification cannot launch RF.
    auto s = selected();
    Driver hw;
    Outputs pins;
    pins.now = &hw.now;
    rf::FilterSelector filters(s, &pins);
    REQUIRE(filters.initialize());
    auto j = tone();
    auto p = rf::plan_job(j);
    REQUIRE(p && filters.prepare(j, *p));
    rf::PioDmaSink sink(hw, nullptr, nullptr, &filters);
    std::array<std::uint32_t, 1> words{};
    REQUIRE(sink.submit(1, 0, words, 32));
    REQUIRE(sink.arm(1, 2'000'000'000ULL, 32));
    hw.now = 1'999'999'999;
    hw.handler(hw.context, {rf::DriverEventKind::Alarm, 1, 0});
    REQUIRE(!hw.active() && !sink.output_active());
    REQUIRE(sink.stop(hw.now) && filters.prepare(j, *p) && sink.submit(2, 0, words, 32) &&
            sink.arm(2, 3'000'000'000ULL, 32));
    hw.fire();
    pins.bad_verify = true;
    hw.fire();
    hw.fire();
    REQUIRE(!hw.active());
    REQUIRE(!sink.output_active());
}
} // namespace
void gpio_init(unsigned gp) {
    gpio_trace.push_back("init" + std::to_string(gp));
    directions[gp] = false;
}
void gpio_put(unsigned gp, bool v) {
    gpio_trace.push_back("put" + std::to_string(gp));
    levels[gp] = v;
}
void gpio_set_dir(unsigned gp, bool out) {
    gpio_trace.push_back("dir" + std::to_string(gp));
    directions[gp] = out;
}
bool gpio_get(unsigned gp) {
    return gp == wrong_gp ? !levels[gp] : levels[gp];
}
unsigned gpio_get_function(unsigned) {
    return GPIO_FUNC_SIO;
}
bool gpio_is_dir_out(unsigned gp) {
    return directions[gp];
}
int main(int argc, char** argv) {
    if (argc == 2 && std::string_view(argv[1]) == "--capabilities") {
        Member m;
        network::HttpRequest r{"GET",
                               "/api/v1/capabilities",
                               {},
                               {{"host", "127.0.0.1:8443"},
                                {"origin", "https://127.0.0.1:8443"},
                                {"x-wsprrypico-request", "1"}}};
        std::cout << m.api.handle(r, "test", "127.0.0.1:8443").body;
        return 0;
    }
    if (argc == 2 && std::string_view(argv[1]) == "--documents") {
        Member m;
        std::cout << hardware::filter_capabilities() << '\n' << m.call("GET").body << '\n';
        std::cout << "{\"schema\":\"transmitter-filter-selector/1\",\"target\":"
                  << application::target(std::string(32, 'a'), m.f.service.status().boot_id)
                  << ",\"settings\":" << hardware::serialize_filters(selected()) << "}\n";
        std::cout << m.call("PUT", hardware::serialize_filters(selected())).body << '\n';
        return 0;
    }
    management_storage();
    admission_and_adapter();
    production_admission();
    execution();
    completion_and_cleanup();
    std::cout
        << "Filter settings, storage, management, coverage, adapter and local sequencing passed\n";
}

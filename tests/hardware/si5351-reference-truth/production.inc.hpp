// SPDX-License-Identifier: MIT
// Included inside the fixture namespace; no production application interface.
wsprrypico::rf::PicoReferenceCapture production_counter;
wsprrypico::time::PicoGpsInput production_gps;
struct ProductionObservation {
    wsprrypico::time::gps::Observation pps;
    wsprrypico::time::gps::CycleSnapshot count;
};
ProductionObservation observations[320];
unsigned observation_count = 0;
std::atomic<bool> capture_done{false}, capture_stop{false}, load_phase{false}, worker_done{false},
    capture_armed{false};
wsprrypico::time::gps::PairingDiagnostic pairing_trace[3200];
unsigned pairing_trace_count = 0;
std::uint64_t next_pairing_trace = 0;
std::uint64_t maximum_pairing_trace_work_us = 0;
bool pairing_trace_ok = true;
void trace_pairing(std::uint64_t now) {
    if (now < next_pairing_trace)
        return;
    next_pairing_trace = now + 100000000ULL;
    const auto started = time_us_64();
    const auto value = wsprrypico::time::gps::pairing_diagnostic(production_gps.status(now), now);
    maximum_pairing_trace_work_us = std::max(maximum_pairing_trace_work_us, time_us_64() - started);
    if (!value || pairing_trace_count == 3200) {
        pairing_trace_ok = false;
        capture_stop.store(true, std::memory_order_release);
        return;
    }
    pairing_trace[pairing_trace_count++] = *value;
}
unsigned truth_count = 0;
std::uint64_t capture_start = 0;
bool initial_load = false, production_coherent = true;
struct AuxiliaryPulse {
    std::uint64_t low_us, high_us;
};
AuxiliaryPulse qlg_pulses[320];
unsigned qlg_count = 0;
bool qlg_prior = false, qlg_started = false, qlg_valid = true;
std::uint64_t qlg_prior_us = 0;
void trace_qlg_pps() {
    if (!external_reference)
        return;
    const auto before = time_us_64();
    const auto high = gpio_get(3);
    const auto after = time_us_64() + 1;
    if (qlg_started && high && !qlg_prior) {
        if (qlg_count == 320) {
            qlg_valid = false;
            capture_stop.store(true, std::memory_order_release);
        } else
            qlg_pulses[qlg_count++] = {qlg_prior_us, after};
    }
    qlg_prior = high;
    qlg_prior_us = before;
    qlg_started = true;
}
void observe_production(const wsprrypico::time::gps::Observation& pps, void*) {
    if (observation_count == 320) {
        capture_stop.store(true, std::memory_order_release);
        return;
    }
    observations[observation_count++] = {
        pps, production_gps.cycle().value_or(wsprrypico::time::gps::CycleSnapshot{})};
}
void capture_worker() {
    while (!capture_armed.load(std::memory_order_acquire) &&
           !capture_stop.load(std::memory_order_acquire))
        tight_loop_contents();
    if (capture_stop.load(std::memory_order_acquire)) {
        capture_done.store(true, std::memory_order_release);
        worker_done.store(true, std::memory_order_release);
        return;
    }
    production_coherent = production_counter.begin(1);
    previous_count = 0;
    previous_us = 0;
    extended_count = max_gap = 0;
    coherent = true;
    Endpoint prior = snapshot();
    trace_qlg_pps();
    while (production_coherent && coherent && truth_count < 301 &&
           time_us_64() - capture_start < 310000000ULL &&
           !capture_stop.load(std::memory_order_acquire)) {
        production_coherent = production_counter.poll(1);
        trace_qlg_pps();
        const auto current = snapshot();
        if (current.high && !prior.high) {
            pulses[truth_count++] = {prior, current};
            load_phase.store(initial_load ^ (((truth_count - 1) / 60) & 1),
                             std::memory_order_release);
        }
        prior = current;
    }
    capture_done.store(true, std::memory_order_release);
    // Keep publication alive while core 0 drains labels for the last edge.
    // Finishing immediately can retire its snapshot before the PPS IRQ reads it.
    while (production_coherent && coherent && truth_count == 301 &&
           !capture_stop.load(std::memory_order_acquire) &&
           time_us_64() - capture_start < 313000000ULL) {
        production_coherent = production_counter.poll(1);
        trace_qlg_pps();
    }
    (void)production_counter.finish();
    worker_done.store(true, std::memory_order_release);
}
void test_production(bool loaded) {
    if (used) {
        puts("ERROR one_test_per_boot");
        return;
    }
    used = true;
    if (!setup() || (!external_reference && (!write(18, 0x4c) || !write(3, 0xfb)))) {
        printf("END_PRODUCTION error=setup restored=%u\n", unsigned(restore()));
        return;
    }
    wsprrypico::hardware::PinPlan pins;
    pins.engine = wsprrypico::hardware::PinPlan::Engine::I2c;
    pins.rf.reset();
    pins.i2c_pair = 1;
    wsprrypico::hardware::Si5351Settings settings;
    settings.synthesis = {25'000'000,
                          wsprrypico::rf::si5351::Reference::ExternalXa,
                          {},
                          wsprrypico::rf::si5351::Output::Clk0,
                          wsprrypico::rf::si5351::Output::Clk2,
                          2};
    settings.loopback_input = input_gp;
    wsprrypico::hardware::GpsSettings gps;
    gps.enabled = gps.pairing_qualified = true;
    gps.pps_gp = pps_gp;
    gps.minimum_message_delay_ms = 600;
    gps.maximum_message_delay_ms = 1200;
    production_gps.cycle_capture(+[] { return production_counter.pps_snapshot(); });
    if (!production_counter.open(pins, settings)) {
        printf("END_PRODUCTION error=counter_open restored=%u\n", unsigned(restore()));
        return;
    }
    // Complete the ROM core-launch handshake before enabling GPS UART ingress.
    multicore_launch_core1(capture_worker);
    if (!production_gps.open(pins, settings, gps)) {
        capture_stop.store(true, std::memory_order_release);
        multicore_reset_core1();
        production_counter.close();
        printf("END_PRODUCTION error=gps_open restored=%u\n", unsigned(restore()));
        return;
    }
    // UART setup can begin in the middle of an existing character/sentence.
    // Retain startup health, then measure deltas over the defined capture.
    const auto settling = time_us_64();
    while (time_us_64() - settling < 3000000ULL)
        production_gps.poll(time_us_64() * 1000, observe_production, nullptr);
    const auto baseline_status = production_gps.status(time_us_64() * 1000);
    observation_count = 0;
    capture_start = time_us_64();
    initial_load = loaded;
    load_phase.store(loaded, std::memory_order_release);
    capture_armed.store(true, std::memory_order_release);
    trace_pairing(time_us_64() * 1000);
    unsigned writes = 0;
    auto next_load = capture_start + 10000;
    constexpr char load[] = "LOAD 0123456789012345678901234567890123456789012345678901234567\n";
    static_assert(sizeof(load) - 1 == 64);
    while (!capture_done.load(std::memory_order_acquire)) {
        const auto now = time_us_64();
        production_gps.poll(now * 1000, observe_production, nullptr);
        trace_pairing(time_us_64() * 1000);
        if (now - capture_start > 312000000ULL)
            capture_stop.store(true, std::memory_order_release);
        if (load_phase.load(std::memory_order_acquire) && now >= next_load) {
            next_load = now + 10000;
            if (stdio_usb_connected() && tud_cdc_write_available() >= sizeof(load) - 1) {
                stdio_usb.out_chars(load, sizeof(load) - 1);
                ++writes;
            }
        }
        tight_loop_contents();
    }
    // Drain labels already associated with the final captured edge. Arrival
    // never replaces the original pulse/count endpoint.
    const auto drain = time_us_64();
    while (time_us_64() - drain < 2000000ULL) {
        production_gps.poll(time_us_64() * 1000, observe_production, nullptr);
        trace_pairing(time_us_64() * 1000);
    }
    capture_stop.store(true, std::memory_order_release);
    const auto stopping = time_us_64();
    while (!worker_done.load(std::memory_order_acquire) && time_us_64() - stopping < 1000000ULL)
        tight_loop_contents();
    if (!worker_done.load(std::memory_order_acquire))
        production_coherent = false;
    multicore_reset_core1();
    const auto status = production_gps.status(time_us_64() * 1000);
    production_gps.close();
    production_counter.close();
    const bool clean = restore();
    printf("BEGIN_PRODUCTION first_loaded=%u pattern=alternating_60pps\n", unsigned(loaded));
    for (unsigned i = 0; i < truth_count; ++i) {
        const auto& p = pulses[i];
        printf("PULSE i=%u raw_low=%llu raw_high=%llu count_low=%llu count_high=%llu\n", i,
               (unsigned long long)p.low.before_us, (unsigned long long)p.high.after_us,
               (unsigned long long)p.low.count_low, (unsigned long long)p.high.count_high);
    }
    for (unsigned i = 0; i < observation_count; ++i) {
        const auto& o = observations[i];
        printf("PROD seq=%llu raw_ns=%llu utc_ns=%llu uncertainty_ns=%llu coherent=%u "
               "edges=%llu count_raw_ns=%llu count_bound_ns=%llu plan=%llu capture=%llu\n",
               (unsigned long long)o.pps.sequence, (unsigned long long)o.pps.raw_ns,
               (unsigned long long)o.pps.utc_ns, (unsigned long long)o.pps.uncertainty_ns,
               unsigned(o.count.coherent), (unsigned long long)o.count.edges,
               (unsigned long long)o.count.raw_ns, (unsigned long long)o.count.uncertainty_ns,
               (unsigned long long)o.count.plan_generation, (unsigned long long)o.count.capture_id);
    }
    // Status is private evidence: it can contain receiver position.
    printf("GPS_BASELINE_STATUS %s\n", baseline_status.c_str());
    printf("GPS_STATUS %s\n", status.c_str());
    if (external_reference) {
        printf("BEGIN_AUX_PPS gp=3 pulses=%u valid=%u\n", qlg_count, unsigned(qlg_valid));
        for (unsigned i = 0; i < qlg_count; ++i)
            printf("AUX_PPS i=%u raw_low_us=%llu raw_high_us=%llu\n", i,
                   (unsigned long long)qlg_pulses[i].low_us,
                   (unsigned long long)qlg_pulses[i].high_us);
        puts("END_AUX_PPS");
    }
    printf("BEGIN_PAIRING_TRACE samples=%u valid=%u period_ns=100000000 max_work_us=%llu\n",
           pairing_trace_count, unsigned(pairing_trace_ok),
           (unsigned long long)maximum_pairing_trace_work_us);
    for (unsigned i = 0; i < pairing_trace_count; ++i) {
        const auto& t = pairing_trace[i];
        const auto error = wsprrypico::time::gps::pairing_diagnostic_errors[t.error];
        printf("PAIRING i=%u raw_ns=%llu candidate_utc_ns=%llu candidate_raw_ns=%llu "
               "candidate_pps_ns=%llu observation_raw_ns=%llu observations=%u rejected=%u "
               "uart_errors=%u dropped=%u capture_rejections=%u flags=%u error=%s\n",
               i, (unsigned long long)t.raw_ns, (unsigned long long)t.candidate_utc_ns,
               (unsigned long long)t.candidate_raw_ns, (unsigned long long)t.candidate_pps_ns,
               (unsigned long long)t.observation_raw_ns, t.observations, t.rejected_sentences,
               t.uart_errors, t.dropped, t.capture_rejections, unsigned(t.flags),
               error.empty() ? "none" : error.data());
    }
    puts("END_PAIRING_TRACE");
    printf("END_PRODUCTION pulses=%u observations=%u coherent=%u max_gap_us=%llu "
           "restored=%u first_loaded=%u load_writes=%u\n",
           truth_count, observation_count,
           unsigned(coherent && production_coherent && pairing_trace_ok && qlg_valid),
           (unsigned long long)max_gap, unsigned(clean), unsigned(loaded), writes);
    fflush(stdout);
}

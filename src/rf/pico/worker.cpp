#include "rf/pico/worker.hpp"

#include "hardware/gpio.h"
#include "hardware/structs/watchdog.h"
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
#include "provisioning/button_safety.hpp"
#endif
#include "hardware/sync.h"
#include "pico/flash.h"
#include "pico/multicore.h"
#include "pico/time.h"
#include "rf/pico/pico_pio_dma.hpp"
#include "runtime/pico/stack_guard.h"

#include <algorithm>

namespace wsprrypico::rf {
namespace {
alignas(8) std::uint32_t worker_stack[4096];
WorkerEngine* worker = nullptr;
std::atomic<unsigned> ready{0};
std::optional<unsigned> emergency_rf, emergency_amplifier;
bool emergency_amplifier_high = true;
std::array<std::pair<unsigned, bool>, hardware::FilterSettings::maximum_outputs>
    emergency_filters{};
unsigned emergency_filter_count = 0;
std::uint64_t now() {
    return time_us_64() * 1000ULL;
}
void wait() {
    tight_loop_contents();
}
[[noreturn]] void failure() {
    // A missing RF-core acknowledgement cannot use another mailbox command.
    // Latch admission first, then override the immutable validated boot pins.
    // The amplifier override persists across a late worker SIO write. Retain
    // fault/ownership and let the watchdog enter inhibited recovery.
    if (worker)
        worker->latch_output_inhibit();
    if (emergency_rf) {
        gpio_set_outover(*emergency_rf, GPIO_OVERRIDE_LOW);
        // Final launch changes OUTOVER, never OEOVER. Keep an emergency
        // clamp effective even if another core resumes between instructions.
        gpio_set_oeover(*emergency_rf, GPIO_OVERRIDE_LOW);
    }
    if (emergency_amplifier)
        gpio_set_outover(*emergency_amplifier,
                         emergency_amplifier_high ? GPIO_OVERRIDE_LOW : GPIO_OVERRIDE_HIGH);
    for (unsigned i = 0; i < emergency_filter_count; ++i)
        gpio_set_outover(emergency_filters[i].first,
                         emergency_filters[i].second ? GPIO_OVERRIDE_LOW : GPIO_OVERRIDE_HIGH);
    watchdog_hw->scratch[2] = 0x52464331; // RFC1: missing RF-core acknowledgement.
    while (true)
        tight_loop_contents(); // Existing watchdog enters inhibited recovery.
}
void run() {
    if (!wsprry_stack_guard_snapshot().valid)
        failure();
    if (!flash_safe_execute_core_init())
        failure();
    ready.store(1, std::memory_order_release);
    while (true)
        worker->step();
}
} // namespace
namespace {
PicoPioDma* drive_hardware = nullptr;
}
int gpio_drive_observation() {
    return drive_hardware ? drive_hardware->drive_observation() : -1;
}
WorkerEngine& start_worker(time::UtcDiscipline& clock, const hardware::PinPlan& pins,
                           bool storage_healthy, IndicatorGate& indicator, unsigned drive_ma,
                           AmplifierEnable* amplifier, FilterSelector* filters) {
    if (!hardware::operational(pins))
        failure();
    static PicoPioDma hardware(*pins.rf, drive_ma);
    drive_hardware = &hardware;
    static PioDmaSink sink(hardware, &indicator, amplifier, filters);
    static StreamEngine engine(sink, filters);
    static WorkerEngine proxy(engine, clock, now, wait, failure, save_and_disable_interrupts,
                              restore_interrupts);
    if (worker)
        failure();
    if (storage_healthy) {
        emergency_rf = pins.rf;
        emergency_amplifier = pins.amplifier;
        emergency_amplifier_high = pins.amplifier_active_high;
        if (filters) {
            emergency_filter_count = filters->settings().output_count;
            for (unsigned i = 0; i < emergency_filter_count; ++i) {
                const auto& output = filters->settings().outputs[i];
                emergency_filters[i] = {output.gp, output.active_high};
            }
        }
    }
    static const bool boot_safe = storage_healthy &&
                                  (!amplifier || !amplifier->output_active_or_unknown()) &&
                                  (!filters || !filters->output_active_or_unknown());
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
    static const auto button = pins.button;
    if (button) {
        gpio_init(*button);
        gpio_set_dir(*button, GPIO_IN);
        gpio_pull_up(*button);
    }
    static provisioning::ButtonSafety safety;
    proxy.set_safety(
        [](void* context) {
            return !boot_safe || static_cast<provisioning::ButtonSafety*>(context)->observe(
                                     time_us_64(), button && !gpio_get(*button));
        },
        &safety);
#else
    proxy.set_safety([](void*) { return !boot_safe; }, nullptr);
#endif
    hardware.set_output_inhibit(proxy.safety_latch());
    std::fill(std::begin(worker_stack), std::end(worker_stack), 0xa59c37e1U);
    proxy.set_probe(
        [](WorkerEngine::Metrics& result, void* context) {
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
            result.safety_input_requested_us = safety.requested_at_us();
            result.safety_input_duration_us = safety.duration_us();
            result.safety_input_reset = safety.reset();
            result.safety_input_fault = safety.fault();
#endif
            const auto driver = static_cast<PicoPioDma*>(context)->metrics();
            result.amplifier = sink.timing_observation();
            result.dma_irqs = driver.dma_irqs;
            result.max_irq_ns = driver.max_irq_ns;
            result.launch_ns = driver.launch_ns;
            result.launch_epoch = driver.launch_epoch;
            result.launch_target_ns = driver.launch_target_ns;
            result.alarm_irqs = driver.alarm_irqs;
            result.max_alarm_irq_ns = driver.max_alarm_irq_ns;
            result.tail_irqs = driver.tail_irqs;
            result.dma_errors = driver.dma_errors;
            result.refill = driver.refill;
            std::size_t free = 0;
            while (free < std::size(worker_stack) && worker_stack[free] == 0xa59c37e1U)
                ++free;
            result.stack_used_bytes = sizeof(worker_stack) - free * sizeof(worker_stack[0]);
            const auto guard = wsprry_stack_guard_snapshot();
            result.stack_guard_bottom = guard.bottom;
            result.stack_guard_limit = guard.limit;
            result.stack_fault_status = guard.fault_status;
            result.stack_guard_valid =
                guard.valid && guard.bottom == reinterpret_cast<std::uintptr_t>(worker_stack);
        },
        &hardware);
    worker = &proxy;
    multicore_launch_core1_with_stack(run, worker_stack, sizeof(worker_stack));
    const auto started = now();
    while (!ready.load(std::memory_order_acquire)) {
        if (now() - started >= 100'000'000ULL)
            failure();
        wait();
    }
    return proxy;
}
} // namespace wsprrypico::rf

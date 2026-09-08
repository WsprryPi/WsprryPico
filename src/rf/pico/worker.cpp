#include "rf/pico/worker.hpp"

#include "hardware/structs/watchdog.h"
#include "hardware/sync.h"
#include "pico/flash.h"
#include "pico/multicore.h"
#include "pico/time.h"
#include "rf/pico/pico_pio_dma.hpp"

#include <algorithm>

namespace wsprrypico::rf {
namespace {
alignas(8) std::uint32_t worker_stack[4096];
WorkerEngine* worker = nullptr;
std::atomic<unsigned> ready{0};
std::uint64_t now() {
    return time_us_64() * 1000ULL;
}
void wait() {
    tight_loop_contents();
}
[[noreturn]] void failure() {
    watchdog_hw->scratch[2] = 0x52464331; // RFC1: missing RF-core acknowledgement.
    while (true)
        tight_loop_contents(); // Existing watchdog enters inhibited recovery.
}
void run() {
    if (!flash_safe_execute_core_init())
        failure();
    ready.store(1, std::memory_order_release);
    while (true)
        worker->step();
}
} // namespace
WorkerEngine& start_worker(time::UtcDiscipline& clock) {
    static PicoPioDma hardware;
    static PioDmaSink sink(hardware);
    static StreamEngine engine(sink);
    static WorkerEngine proxy(engine, clock, now, wait, failure, save_and_disable_interrupts,
                              restore_interrupts);
    if (worker)
        failure();
    std::fill(std::begin(worker_stack), std::end(worker_stack), 0xa59c37e1U);
    proxy.set_probe(
        [](WorkerEngine::Metrics& result, void* context) {
            const auto driver = static_cast<PicoPioDma*>(context)->metrics();
            result.dma_irqs = driver.dma_irqs;
            result.max_irq_ns = driver.max_irq_ns;
            result.launch_ns = driver.launch_ns;
            std::size_t free = 0;
            while (free < std::size(worker_stack) && worker_stack[free] == 0xa59c37e1U)
                ++free;
            result.stack_used_bytes = sizeof(worker_stack) - free * sizeof(worker_stack[0]);
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

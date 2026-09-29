#include "hardware/exception.h"
#include "hardware/gpio.h"
#include "hardware/structs/m33.h"
#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "pico/multicore.h"
#include "pico/platform.h"
#include "pico/stdio_usb.h"
#include "pico/stdlib.h"
#include "provisioning/button_diagnostic.hpp"
#include "runtime/pico/stack_guard.h"

#include <array>
#include <atomic>
#include <cinttypes>
#include <cstdint>
#include <cstdio>

namespace {
constexpr unsigned button_pin = 14;
#if WSPRRY_GP14_DIAG_INJECT_WATCHDOG
constexpr std::uint32_t scratch_magic = 0x47503149; // GP1I
#else
constexpr std::uint32_t scratch_magic = 0x47503134; // GP14
#endif
constexpr std::uint32_t core1_stalled = 0x43315354;     // C1ST
constexpr std::uint32_t input_clock_fault = 0x434c4b46; // CLKF
constexpr std::uint32_t hardfault_flag = 1u << 31u;
#if WSPRRY_GP14_DIAG_INJECT_WATCHDOG
constexpr std::uint32_t injected_watchdog = 0x5744494e; // WDIN
#endif
constexpr std::uint32_t reset_flag = 1u << 31u;
constexpr std::uint32_t stop_flag = 1u << 30u;
constexpr std::uint32_t ap_flag = 1u << 29u;
constexpr std::uint32_t duration_mask = (1u << 29u) - 1u;
constexpr unsigned probe_words = 8192; // 32 KiB exceeds the RP2350 XIP cache.
constexpr unsigned event_capacity = 16;
alignas(8) std::uint32_t core1_stack[2048];

constexpr std::array<std::uint32_t, probe_words> make_probe_data() {
    std::array<std::uint32_t, probe_words> result{};
    std::uint32_t value = 0x92f35a17;
    for (auto& word : result) {
        value = value * 1664525u + 1013904223u;
        word = value;
    }
    return result;
}
__attribute__((used)) constinit const auto flash_probe_words = make_probe_data();

std::atomic<std::uint32_t> core0_reads{0}, core1_reads{0};
std::atomic<std::uint32_t> core0_digest{0}, core1_digest{0};
std::atomic<bool> core1_ready{false};

// Both cores execute this function from XIP and traverse flash data larger
// than the cache. GP14 has no electrical connection to flash chip select.
std::uint32_t __attribute__((noinline, used)) flash_probe_step(std::uint32_t sequence,
                                                               std::uint32_t digest) {
    const auto* words = reinterpret_cast<volatile const std::uint32_t*>(flash_probe_words.data());
    const auto value = words[(sequence * 8191u) & (probe_words - 1u)];
    return (digest << 5u) ^ (digest >> 27u) ^ value ^ sequence;
}

[[noreturn]] void __no_inline_not_in_flash_func(button_hardfault)() {
    watchdog_hw->scratch[2] = hardfault_flag | m33_hw->cfsr;
    watchdog_hw->scratch[7] = m33_hw->hfsr;
    while (true)
        __asm volatile("nop"); // Let the watchdog preserve this fault record.
}

void core1_main() {
    exception_set_exclusive_handler(HARDFAULT_EXCEPTION, button_hardfault);
    if (!wsprry_stack_guard_snapshot().valid) {
        watchdog_hw->scratch[2] = 0x43314744; // C1GD
        while (true)
            tight_loop_contents();
    }
    core1_ready.store(true, std::memory_order_release);
    std::uint32_t sequence = 4096, digest = 0;
    while (true) {
        for (unsigned i = 0; i < 256; ++i)
            digest = flash_probe_step(sequence++, digest);
        core1_digest.store(digest, std::memory_order_relaxed);
        core1_reads.store(sequence - 4096, std::memory_order_release);
        watchdog_hw->scratch[6] = sequence - 4096;
    }
}

struct Record {
    std::uint32_t sequence = 0;
    const char* kind = "";
    std::uint64_t time_us = 0;
    std::uint64_t duration_us = 0;
    std::uint32_t reads0 = 0, reads1 = 0, digest0 = 0, digest1 = 0;
};

std::array<Record, event_capacity> records{};
std::uint32_t record_sequence = 0;

void record(const char* kind, std::uint64_t now_us, std::uint64_t duration_us = 0) {
    auto& row = records[record_sequence % event_capacity];
    row = {++record_sequence,
           kind,
           now_us,
           duration_us,
           core0_reads.load(std::memory_order_acquire),
           core1_reads.load(std::memory_order_acquire),
           core0_digest.load(std::memory_order_relaxed),
           core1_digest.load(std::memory_order_relaxed)};
    watchdog_hw->scratch[5] = row.reads0;
    watchdog_hw->scratch[6] = row.reads1;
}

void report(std::uint32_t boot, bool previous_watchdog, std::uint32_t previous_fault,
            std::uint32_t previous_hfsr, std::uint32_t previous_press,
            std::uint32_t previous_reads0, std::uint32_t previous_reads1,
            std::uint32_t previous_reason, bool held, std::uint64_t max_poll_gap_us,
            std::uint32_t& next_report_sequence) {
    std::printf(
        "GP14_DIAG boot=%" PRIu32 " prior_watchdog=%u prior_reason=%08" PRIx32
        " prior_fault_word=%08" PRIx32 " prior_hfsr=%08" PRIx32 " prior_duration_ms=%" PRIu32
        " prior_reset=%u prior_stop=%u prior_ap=%u prior_reads=%" PRIu32 ",%" PRIu32
        " held=%u reads=%" PRIu32 ",%" PRIu32 " digest=%08" PRIx32 ",%08" PRIx32
        " max_poll_gap_us=%" PRIu64 " events=%" PRIu32 "\r\n",
        boot, previous_watchdog, previous_reason, previous_fault, previous_hfsr,
        previous_press & duration_mask, !!(previous_press & reset_flag),
        !!(previous_press & stop_flag), !!(previous_press & ap_flag), previous_reads0,
        previous_reads1, held, core0_reads.load(std::memory_order_acquire),
        core1_reads.load(std::memory_order_acquire), core0_digest.load(std::memory_order_relaxed),
        core1_digest.load(std::memory_order_relaxed), max_poll_gap_us, record_sequence);
    const auto first = record_sequence > event_capacity ? record_sequence - event_capacity : 0;
    if (next_report_sequence < first)
        std::printf("GP14_EVENTS_LOST count=%" PRIu32 "\r\n", first - next_report_sequence);
    for (auto sequence = next_report_sequence > first ? next_report_sequence : first;
         sequence < record_sequence; ++sequence) {
        const auto& row = records[sequence % event_capacity];
        std::printf("GP14_EVENT seq=%" PRIu32 " kind=%s at_us=%" PRIu64 " duration_us=%" PRIu64
                    " reads=%" PRIu32 ",%" PRIu32 " digest=%08" PRIx32 ",%08" PRIx32 "\r\n",
                    row.sequence, row.kind, row.time_us, row.duration_us, row.reads0, row.reads1,
                    row.digest0, row.digest1);
    }
    next_report_sequence = record_sequence;
}
} // namespace

int main() {
    static_assert(button_pin == 14);
    gpio_init(button_pin);
    gpio_set_dir(button_pin, GPIO_IN);
    gpio_pull_up(button_pin);
    wsprrypico::provisioning::ButtonDiagnostic button;
    button.observe(time_us_64(), !gpio_get(button_pin));
    exception_set_exclusive_handler(HARDFAULT_EXCEPTION, button_hardfault);

    const auto previous_reason = watchdog_hw->reason;
    const bool previous_watchdog =
        watchdog_enable_caused_reboot() && watchdog_hw->scratch[0] == scratch_magic;
    const auto previous_fault = previous_watchdog ? watchdog_hw->scratch[2] : 0u;
    const auto previous_hfsr = previous_watchdog ? watchdog_hw->scratch[7] : 0u;
    const auto previous_press = previous_watchdog ? watchdog_hw->scratch[3] : 0u;
    const auto previous_reads0 = previous_watchdog ? watchdog_hw->scratch[5] : 0u;
    const auto previous_reads1 = previous_watchdog ? watchdog_hw->scratch[6] : 0u;
    const auto boot = previous_watchdog ? watchdog_hw->scratch[1] + 1u : 1u;
    watchdog_hw->scratch[0] = scratch_magic;
    watchdog_hw->scratch[1] = boot;
    watchdog_hw->scratch[2] = 0;
    watchdog_hw->scratch[3] = 0;
    watchdog_hw->scratch[5] = 0;
    watchdog_hw->scratch[6] = 0;
    watchdog_hw->scratch[7] = 0;

    stdio_init_all();
    watchdog_enable(4000, false);
    multicore_launch_core1_with_stack(core1_main, core1_stack, sizeof(core1_stack));
    while (!core1_ready.load(std::memory_order_acquire))
        tight_loop_contents(); // Watchdog resets a failed core-1 launch.

    std::uint32_t sequence = 0, digest = 0;
    std::uint64_t last_feed_us = time_us_64(), last_report_us = last_feed_us;
#if WSPRRY_GP14_DIAG_INJECT_WATCHDOG
    const auto started_us = last_feed_us;
#endif
    std::uint64_t last_observe_us = last_feed_us, max_poll_gap_us = 0;
    std::uint64_t post_release_us = 0;
    std::uint32_t last_core1_reads = core1_reads.load(std::memory_order_acquire);
    std::uint32_t action_flags = 0, next_report_sequence = 0;
    bool was_active = false;
    while (true) {
        for (unsigned i = 0; i < 256; ++i)
            digest = flash_probe_step(sequence++, digest);
        core0_digest.store(digest, std::memory_order_relaxed);
        core0_reads.store(sequence, std::memory_order_release);
        watchdog_hw->scratch[5] = sequence;

        const auto now_us = time_us_64();
        if (now_us - last_observe_us > max_poll_gap_us)
            max_poll_gap_us = now_us - last_observe_us;
        last_observe_us = now_us;
        const auto events = button.observe(now_us, !gpio_get(button_pin));
        if (button.fault()) {
            watchdog_hw->scratch[2] = input_clock_fault;
            while (true)
                tight_loop_contents();
        }
        if (button.active() && !was_active) {
            action_flags = 0;
            record("press", now_us);
        }
        if (events.request_reset) {
            action_flags |= reset_flag;
            record("would_reset", now_us, events.duration_us);
        }
        if (events.request_stop) {
            action_flags |= stop_flag;
            record("would_stop", now_us, events.duration_us);
        }
        if (events.request_setup_ap) {
            action_flags |= ap_flag;
            record("would_setup_ap", now_us, events.duration_us);
        }
        if (events.released) {
            record("release", now_us, events.duration_us);
            post_release_us = now_us + 1'000'000u;
        }
        if (button.active() || events.released) {
            const auto millis = events.duration_us / 1000u;
            watchdog_hw->scratch[3] =
                action_flags |
                static_cast<std::uint32_t>(millis > duration_mask ? duration_mask : millis);
        }
        was_active = button.active();
        if (post_release_us && now_us >= post_release_us) {
            record("post_release", now_us);
            post_release_us = 0;
        }
#if WSPRRY_GP14_DIAG_INJECT_WATCHDOG
        if (boot == 1 && now_us - started_us >= 15'000'000u) {
            watchdog_hw->scratch[2] = injected_watchdog;
            while (true)
                tight_loop_contents();
        }
#endif
        if (now_us - last_feed_us >= 500'000u) {
            const auto current = core1_reads.load(std::memory_order_acquire);
            if (current == last_core1_reads) {
                watchdog_hw->scratch[2] = core1_stalled;
                while (true)
                    tight_loop_contents();
            }
            last_core1_reads = current;
            watchdog_update();
            last_feed_us = now_us;
        }
        if (now_us - last_report_us >= 2'000'000u && stdio_usb_connected()) {
            report(boot, previous_watchdog, previous_fault, previous_hfsr, previous_press,
                   previous_reads0, previous_reads1, previous_reason, button.held(),
                   max_poll_gap_us, next_report_sequence);
            last_report_us = now_us;
        }
    }
}

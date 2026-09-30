// MIT. Explicit diagnostic: no RF, network or settings writer is linked.
#include "firmware_identity.hpp"
#include "hardware/clocks.h"
#include "hardware/exception.h"
#include "hardware/flash.h"
#include "hardware/structs/m33.h"
#include "hardware/structs/timer.h"
#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "pico/bootrom.h"
#include "pico/flash.h"
#include "pico/multicore.h"
#include "pico/rand.h"
#include "pico/stdlib.h"
#include "pico/unique_id.h"
#include "provisioning/pico/gp14_capture.hpp"
#include "runtime/pico/stack_guard.h"
#include "standalone/pico/flash_layout.hpp"

#include <array>
#include <atomic>
#include <cinttypes>
#include <cstdio>
#include <cstring>

#ifndef WSPRRY_PICO_GP14_ROBUSTNESS
#error "Test hooks belong only in the separate robustness image"
#endif
#ifdef WSPRRY_PICO_STANDALONE_RF
#error "Robustness test must never link physical RF"
#endif
namespace {
using wsprrypico::provisioning::PicoGp14Capture;
namespace layout = wsprrypico::standalone::flash_layout;
constexpr std::uint32_t scratch_offset = layout::access_base - FLASH_SECTOR_SIZE;
static_assert(scratch_offset == 0x3f2000 && FLASH_SECTOR_SIZE == 4096);
constexpr std::uint32_t magic = 0x47505242; // GPRB, diagnostic-only breadcrumbs 0..3.
enum class Action : unsigned {
    Idle,
    Short,
    Middle,
    Long,
    Stuck,
    Flash,
    DmaStop,
    PioStop,
    Overrun,
    Reset,
    Watchdog,
    Fault,
    BootHeld,
    Reload,
    Bootsel
};
constexpr const char* names[] = {"IDLE",     "SHORT",    "MIDDLE",    "LONG",    "STUCK",
                                 "FLASH",    "DMA_STOP", "PIO_STOP",  "OVERRUN", "RESET",
                                 "WATCHDOG", "FAULT",    "BOOT_HELD", "RELOAD",  "BOOTSEL"};
constexpr auto probe_data() {
    std::array<std::uint32_t, 8192> result{};
    std::uint32_t v = 0x92f35a17;
    for (auto& word : result) {
        v = v * 1664525u + 1013904223u;
        word = v;
    }
    return result;
}
__attribute__((used)) constinit const auto robustness_flash_words = probe_data();
alignas(8) std::uint32_t core1_stack[2048];
std::atomic<std::uint32_t> reads1{0}, ready1{0};
std::uint32_t reads0 = 0, digest0 = 0;
std::uint32_t __attribute__((noinline, used)) robustness_flash_probe(std::uint32_t n,
                                                                     std::uint32_t digest) {
    const auto* data =
        reinterpret_cast<const volatile std::uint32_t*>(robustness_flash_words.data());
    return (digest << 5) ^ (digest >> 27) ^ data[(n * 8191u) & 8191u];
}
[[noreturn]] void __no_inline_not_in_flash_func(robustness_hardfault)() {
    watchdog_hw->scratch[3] = m33_hw->cfsr | 0x80000000U;
    while (true)
        __asm volatile("nop");
}
void robustness_core1() {
    exception_set_exclusive_handler(HARDFAULT_EXCEPTION, robustness_hardfault);
    if (!wsprry_stack_guard_snapshot().valid || !flash_safe_execute_core_init()) {
        ready1.store(2, std::memory_order_release);
        while (true)
            tight_loop_contents();
    }
    ready1.store(1, std::memory_order_release);
    std::uint32_t n = 0, digest = 0;
    while (true) {
        for (unsigned i = 0; i < 256; ++i)
            digest = robustness_flash_probe(n++, digest);
        reads1.store(n, std::memory_order_release);
    }
}
std::uint32_t settings_hash() {
    // FNV continuity checksum, not authentication. Include access/BTstack/profile/
    // standalone storage; exclude the boot ROM's E10 workaround sector.
    const auto* data =
        reinterpret_cast<const volatile std::uint8_t*>(XIP_BASE + layout::access_base);
    std::uint32_t hash = 2166136261u;
    for (std::size_t i = 0; i < layout::boot_workaround_base - layout::access_base; ++i)
        hash = (hash ^ data[i]) * 16777619u;
    return hash;
}
alignas(4) std::array<std::uint8_t, FLASH_SECTOR_SIZE> saved_sector, pattern;
struct FlashOperation {
    const std::uint8_t* bytes;
    volatile std::uint32_t* instruction;
    bool gesture;
};
void __no_inline_not_in_flash_func(robustness_flash_write)(void* context) {
    const auto& operation = *static_cast<FlashOperation*>(context);
    if (operation.gesture) {
        *operation.instruction = 0x5f61; // IN NULL,1 [31]: pressed, no GPIO write.
        const auto before = timer_hw->timerawl;
        while (static_cast<std::uint32_t>(timer_hw->timerawl - before) < 20'000)
            __asm volatile("nop");
    }
    // Addresses and length are literals; USB cannot choose a flash address.
    flash_range_erase(scratch_offset, FLASH_SECTOR_SIZE);
    flash_range_program(scratch_offset, operation.bytes, FLASH_SECTOR_SIZE);
    if (operation.gesture) {
        const auto before = timer_hw->timerawl;
        while (static_cast<std::uint32_t>(timer_hw->timerawl - before) < 120'000)
            __asm volatile("nop");
        *operation.instruction = 0x5f21; // IN X,1 [31], X=1: released.
    }
}
} // namespace

int main() {
    const bool prior_valid = watchdog_caused_reboot() && watchdog_hw->scratch[0] == magic;
    const auto prior_action = prior_valid ? watchdog_hw->scratch[1] : 0;
    const auto prior_sequence = prior_valid ? watchdog_hw->scratch[2] : 0;
    const auto prior_fault = prior_valid ? watchdog_hw->scratch[3] : 0;
    const bool prior_watchdog = watchdog_enable_caused_reboot();
    const bool boot_held = prior_action == static_cast<unsigned>(Action::BootHeld);
    watchdog_hw->scratch[0] = magic;
    for (unsigned i = 1; i <= 3; ++i)
        watchdog_hw->scratch[i] = 0;
    watchdog_enable(8'000, true);
    exception_set_exclusive_handler(HARDFAULT_EXCEPTION, robustness_hardfault);
    stdio_init_all();
    char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];
    pico_get_unique_board_id_string(serial, sizeof serial);
    const auto boot = time_us_64();
    const auto boot_id = get_rand_64();
    const auto before_settings = settings_hash();
    multicore_launch_core1_with_stack(robustness_core1, core1_stack, sizeof core1_stack);
    while (!ready1.load(std::memory_order_acquire) && time_us_64() - boot < 1'000'000)
        tight_loop_contents();
    const bool cores_ok = ready1.load(std::memory_order_acquire) == 1 &&
                          wsprry_stack_guard_snapshot().valid && flash_safe_execute_core_init();
    static PicoGp14Capture capture;
    const bool started = cores_ok && capture.start(boot_held);
    Action action = boot_held ? Action::BootHeld : Action::Idle;
    std::uint32_t sequence = 0, stops = 0, aps = 0, resets = 0, releases = 0;
    std::uint64_t duration = 0, start_at = boot, low_at = 0, high_at = 0, done_at = 0;
    bool active = boot_held, acted = boot_held, armed = false, flash_ok = false;
    bool stimulus_released = false;
    std::uint64_t arm_until = 0;
    std::uint32_t observed1 = reads1.load(), observed_at = to_ms_since_boot(get_absolute_time());
    char line[128]{};
    unsigned length = 0;
    bool overflow = false;
    auto report = [&](const char* result) {
        std::printf(
            "{\"image\":\"gp14-robustness\",\"synthetic\":1,\"rf_output\":0,\"serial\":\"%s\","
            "\"revision\":\"%s\","
            "\"result\":\"%s\",\"action\":\"%s\",\"active\":%u,\"sequence\":%" PRIu32 ","
            "\"prior_action\":%" PRIu32 ",\"prior_sequence\":%" PRIu32 ",\"prior_watchdog\":%u,"
            "\"boot_id\":%" PRIu64 ",\"prior_fault\":%" PRIu32 ",\"uptime_us\":%" PRIu64
            ",\"clock_hz\":%" PRIu32 ","
            "\"started\":%u,\"capture_fault\":%u,\"fault_code\":%u,\"held\":%u,"
            "\"samples\":%" PRIu64 ",\"blocks\":%" PRIu64 ",\"backlog\":%" PRIu64 ","
            "\"stops\":%" PRIu32 ",\"aps\":%" PRIu32 ",\"would_reset\":%" PRIu32 ","
            "\"releases\":%" PRIu32 ",\"duration_us\":%" PRIu64 ","
            "\"low_at_us\":%" PRIu64 ",\"high_at_us\":%" PRIu64 ","
            "\"reads0\":%" PRIu32 ",\"reads1\":%" PRIu32 ",\"flash_ok\":%u,"
            "\"settings_before\":%" PRIu32 ",\"settings_now\":%" PRIu32 "}\n",
            serial, wsprrypico::firmware::kBuildRevision, result,
            names[static_cast<unsigned>(action)], active, sequence, prior_action, prior_sequence,
            prior_watchdog, boot_id, prior_fault, time_us_64(), clock_get_hz(clk_sys), started,
            capture.fault(), static_cast<unsigned>(capture.fault_code()), capture.held(),
            capture.samples(), capture.completed_blocks(), capture.maximum_backlog_words(), stops,
            aps, resets, releases, duration, low_at, high_at, reads0, reads1.load(), flash_ok,
            before_settings, settings_hash());
    };
    while (true) {
        auto now = time_us_64();
        for (unsigned i = 0; i < 64; ++i)
            digest0 = robustness_flash_probe(reads0++, digest0);
        const auto count1 = reads1.load(std::memory_order_acquire);
        if (count1 != observed1) {
            observed1 = count1;
            observed_at = now / 1000;
        }
        // Losing the other core must not be hidden by a healthy USB loop.
        if (cores_ok && static_cast<std::uint32_t>(now / 1000 - observed_at) < 1000)
            watchdog_update();
        if (active && acted && action == Action::BootHeld && now - start_at >= 12'000'000) {
            capture.sample_override(false);
            high_at = now;
            done_at = now + 100'000;
            action = Action::BootHeld;
            acted = false;
        }
        if (active && !acted && action != Action::BootHeld && now >= start_at) {
            acted = true;
            watchdog_hw->scratch[1] = static_cast<unsigned>(action);
            watchdog_hw->scratch[2] = sequence;
            if (action == Action::Reset) {
                watchdog_reboot(0, 0, 0);
                while (true)
                    tight_loop_contents();
            }
            if (action == Action::Bootsel) {
                reset_usb_boot(0, 0);
                while (true)
                    tight_loop_contents();
            }
            if (action == Action::Watchdog)
                while (true)
                    tight_loop_contents();
            if (action == Action::Fault)
                __asm volatile("udf #0");
            if (action == Action::DmaStop)
                capture.inject_dma_stop();
            if (action == Action::PioStop)
                capture.inject_pio_stop();
            if (action == Action::Short || action == Action::Middle || action == Action::Long ||
                action == Action::Stuck) {
                capture.sample_override(true);
                low_at = now;
                const auto hold = action == Action::Short    ? 200'000ULL
                                  : action == Action::Middle ? 600'000ULL
                                  : action == Action::Long   ? 11'000'000ULL
                                                             : 610'000'000ULL;
                high_at = now + hold;
                done_at = high_at + 100'000;
            } else if (action == Action::Flash) {
                const auto* sector =
                    reinterpret_cast<const std::uint8_t*>(XIP_BASE + scratch_offset);
                std::memcpy(saved_sector.data(), sector, saved_sector.size());
                for (unsigned i = 0; i < pattern.size(); ++i)
                    pattern[i] = static_cast<std::uint8_t>(i ^ sequence);
                FlashOperation operation{pattern.data(), capture.sample_instruction(), true};
                const int write = flash_safe_execute(robustness_flash_write, &operation, 100);
                const bool matched =
                    write == PICO_OK && std::memcmp(sector, pattern.data(), pattern.size()) == 0;
                operation = {saved_sector.data(), capture.sample_instruction(), false};
                const int restore = flash_safe_execute(robustness_flash_write, &operation, 100);
                flash_ok = matched && restore == PICO_OK &&
                           std::memcmp(sector, saved_sector.data(), saved_sector.size()) == 0;
                capture.sample_override(false);
                done_at = time_us_64() + 100'000;
            } else
                done_at = now + (action == Action::Overrun  ? 17'000'000ULL
                                 : action == Action::Reload ? 70'000'000ULL
                                                            : 200'000ULL);
        }
        if (active && low_at && !stimulus_released && now >= high_at) {
            capture.sample_override(false);
            high_at = now;
            stimulus_released = true;
            done_at = now + 100'000;
        }
        if (active && action == Action::Overrun && acted)
            (void)capture.poll_progress();
        else {
            wsprrypico::provisioning::DiagnosticButtonEvents event;
            while (capture.next(event)) {
                stops += event.request_stop;
                aps += event.request_setup_ap;
                resets += event.request_reset;
                if (event.released) {
                    ++releases;
                    duration = event.duration_us;
                }
            }
        }
        if (active && done_at && now >= done_at) {
            active = false;
            report("done");
        }
        // Bound work per pass even if a host floods serial input.
        for (unsigned input = 0; input < 32; ++input) {
            const int ch = getchar_timeout_us(0);
            if (ch == PICO_ERROR_TIMEOUT)
                break;
            if (ch == '\r')
                continue;
            if (ch != '\n') {
                if (length + 1 < sizeof line)
                    line[length++] = static_cast<char>(ch);
                else
                    overflow = true;
                continue;
            }
            line[length] = 0;
            if (overflow) {
                armed = false;
                report("invalid");
            } else if (!std::strcmp(line, "STATUS"))
                report("status");
            else {
                char arm[100];
                std::snprintf(arm, sizeof arm, "ARM %s %s", serial,
                              wsprrypico::firmware::kBuildRevision);
                if (!std::strcmp(line, arm) && !active) {
                    armed = true;
                    arm_until = now + 5'000'000;
                    report("armed");
                } else {
                    Action selected = Action::Idle;
                    for (unsigned i = 1; i < std::size(names); ++i)
                        if (!std::strncmp(line, "RUN ", 4) && !std::strcmp(line + 4, names[i]))
                            selected = static_cast<Action>(i);
                    if (!armed || now > arm_until || active || selected == Action::Idle ||
                        (!started && selected != Action::Bootsel) ||
                        (capture.fault() && selected != Action::Reset &&
                         selected != Action::Bootsel))
                        report("refused");
                    else {
                        action = selected;
                        active = true;
                        acted = false;
                        ++sequence;
                        stops = aps = resets = releases = 0;
                        duration = low_at = high_at = done_at = 0;
                        flash_ok = false;
                        stimulus_released = false;
                        start_at = now + 250'000;
                        // BOOT_HELD is applied only on the next boot, before sampling starts.
                        if (action == Action::BootHeld) {
                            watchdog_hw->scratch[1] = static_cast<unsigned>(action);
                            watchdog_hw->scratch[2] = sequence;
                            report("accepted");
                            sleep_ms(100);
                            watchdog_reboot(0, 0, 0);
                            while (true)
                                tight_loop_contents();
                        }
                        report("accepted");
                    }
                    armed = false;
                }
            }
            length = 0;
            overflow = false;
        }
    }
}

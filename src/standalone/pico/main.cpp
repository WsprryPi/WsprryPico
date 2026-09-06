#include "firmware_identity.hpp"
#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "pico/bootrom.h"
#include "pico/time.h"
#include "pico_adapters.hpp"
#include "standalone/pico/adapters.hpp"
#include "standalone/scheduler.hpp"
#include "tusb.h"
#include "usb/transport.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/json.hpp"
#ifdef WSPRRY_PICO_STANDALONE_RF
#include "hardware/clocks.h"
#include "rf/pico/pico_pio_dma.hpp"
#else
#include "standalone/dry_run_engine.hpp"
static_assert(WSPRRY_PICO_RF_OUTPUT_DISABLED == 1);
#endif
#include <array>

// Capture the exception's PC without allocating or relying on USB. The
// watchdog performs the reset; the next boot inhibits autonomous operation.
extern "C" [[noreturn]] void wsprrypico_hardfault(const std::uint32_t* frame,
                                                  std::uint32_t exception_return) {
    if (!(exception_return & 16))
        frame += 18;
    const auto address = reinterpret_cast<std::uintptr_t>(frame);
    watchdog_hw->scratch[0] = *reinterpret_cast<volatile std::uint32_t*>(0xe000ed28);
    watchdog_hw->scratch[3] = address >= 0x20000000 && address <= 0x20081fe0 ? frame[6] : 1;
    while (true)
        tight_loop_contents();
}
extern "C" __attribute__((naked)) void isr_hardfault() {
    asm volatile("tst lr, #4\n"
                 "ite eq\n"
                 "mrseq r0, msp\n"
                 "mrsne r0, psp\n"
                 "mov r1, lr\n"
                 "b wsprrypico_hardfault\n");
}
// Retain only the constant format string's hash, never formatted arguments.
// The watchdog resets into recovery even when USB is not being serviced.
extern "C" [[noreturn]] void wsprrypico_panic(const char* format, ...) {
    std::uint32_t hash = 2166136261U;
    if (format)
        for (unsigned i = 0; i < 192 && format[i]; ++i)
            hash = (hash ^ static_cast<unsigned char>(format[i])) * 16777619U;
    watchdog_hw->scratch[2] = hash;
    while (true)
        tight_loop_contents();
}
namespace {
std::uint64_t monotonic_now(void*) {
    return time_us_64() * 1000ULL;
}
} // namespace
int main() {
    // SDK uses scratch 4..7 for reboot bookkeeping. Preserve a small diagnostic
    // in 1..2, and enter an unowned, network-free recovery boot after a stall.
    const bool recovery = watchdog_enable_caused_reboot();
    const auto fault_stage = recovery ? watchdog_hw->scratch[1] : 0;
    const auto fault_hash = recovery ? watchdog_hw->scratch[2] : 0;
    const auto fault_pc = recovery ? watchdog_hw->scratch[3] : 0;
    const auto fault_status = recovery ? watchdog_hw->scratch[0] : 0;
    watchdog_hw->scratch[0] = 0;
    watchdog_hw->scratch[2] = 0;
    watchdog_hw->scratch[3] = 0;
    watchdog_hw->scratch[1] = 1;
    watchdog_enable(8000, true);

#ifdef WSPRRY_PICO_STANDALONE_RF
    set_sys_clock_khz(wsprrypico::rf::sample_rate / 1000, true);
#endif
    tud_init(0);
    wsprrypico::time::DisciplineConfig discipline;
    discipline.synchronized_for_ns = 90'000'000'000ULL;
    discipline.holdover_for_ns = 180'000'000'000ULL;
    static wsprrypico::time::UtcDiscipline clock(monotonic_now, nullptr, discipline);
    static wsprrypico::standalone::PicoFlash flash;
    static wsprrypico::standalone::Store store(flash);
    (void)store.load();
    // Both adapters claim PIO/DMA resources through the SDK allocator.
#ifdef WSPRRY_PICO_STANDALONE_RF
    static wsprrypico::rf::PicoPioDma hardware;
    static wsprrypico::rf::PioDmaSink sink(hardware);
    static wsprrypico::rf::StreamEngine engine(sink);
#else
    static wsprrypico::standalone::DryRunEngine engine;
#endif
    static wsprrypico::firmware::PicoIdentitySource identities;
    wsprrypico::wtp::ServiceConfig config;
    config.supported_modes = {"wspr", "tone"};
    config.capability_engine = "inhibited-standalone-simulator";
    config.minimum_frequency_nhz = 3'570'100'000'000'000ULL;
    config.maximum_frequency_nhz = config.minimum_frequency_nhz + 3 * 1'464'843'750ULL;
    config.maximum_arm_uncertainty_ns = wsprrypico::time::standalone_max_uncertainty_ns;
    config.maximum_holdover_age_ns = 90'000'000'000ULL;
#ifdef WSPRRY_PICO_STANDALONE_RF
    config.capability_engine = "pio-dma-gp2";
#endif
    static wsprrypico::wtp::JobService service(clock, engine, identities, config);
    static wsprrypico::wtp::Endpoint endpoint(service, identities.device_id(),
                                              wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::standalone::Scheduler scheduler(store, service);
    static wsprrypico::standalone::PicoNetwork network(clock);
    if (recovery)
        (void)scheduler.command("STOP");
    watchdog_hw->scratch[1] = 2;
    if (!recovery && store.healthy() && store.config())
        (void)network.start(*store.config());
    watchdog_hw->scratch[1] = 3;
    std::array<std::uint8_t, 64> input{};
    std::size_t offset = 0, size = 0;
    std::array<char, wsprrypico::standalone::max_config_bytes + 7> line{};
    std::size_t length = 0;
    bool overflow = false;
    std::uint64_t reboot_at = 0;
    bool bootloader = false;
    auto command = [&](std::string_view text) -> std::string {
        if (text == "INFO") {
            std::string result =
                "{\"ok\":true,\"device_id\":" +
                wsprrypico::wtp::json::quote(identities.device_id()) + ",\"revision\":" +
                wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                ",\"firmware\":" +
                wsprrypico::wtp::json::quote(wsprrypico::firmware::kFirmwareVersion) +
                ",\"recovery_boot\":" + (recovery ? "true" : "false") +
                ",\"fault_stage\":" + std::to_string(fault_stage) +
                ",\"fault_hash\":" + std::to_string(fault_hash) +
                ",\"fault_pc\":" + std::to_string(fault_pc) +
                ",\"fault_status\":" + std::to_string(fault_status) +
                ",\"network\":" + network.status();
#ifdef WSPRRY_PICO_STANDALONE_RF
            const auto metrics = hardware.metrics();
            result +=
                ",\"launch_observed_ns\":\"" + std::to_string(metrics.launch_ns) +
                "\",\"dma_irqs\":" + std::to_string(metrics.dma_irqs) +
                ",\"max_dma_irq_ns\":" + std::to_string(metrics.max_irq_ns) +
                ",\"engine_diagnostic\":" + wsprrypico::wtp::json::quote(engine.diagnostic()) +
                ",\"sink_diagnostic\":" + wsprrypico::wtp::json::quote(sink.diagnostic());
#endif
            auto status = scheduler.status();
            if (!status.empty() && status.back() == '\n')
                status.pop_back();
            return result + ",\"status\":" + status + "}\n";
        }
        if (text == "REBOOT" || text == "BOOTSEL") {
            (void)scheduler.command("STOP");
            if (!scheduler.idle() || !engine.disable(monotonic_now(nullptr) + 100'000'000ULL) ||
                engine.output_active())
                return "{\"ok\":false,\"error\":\"not_idle\"}\n";
            bootloader = text == "BOOTSEL";
            reboot_at = time_us_64() + 250'000;
            return "{\"ok\":true,\"rebooting\":true}\n";
        }
#ifndef WSPRRY_PICO_STANDALONE_RF
        if (text == "WIFI OFF" || text == "WIFI ON") {
            if (!scheduler.idle())
                return "{\"ok\":false,\"error\":\"busy\"}\n";
            return network.set_enabled(text == "WIFI ON")
                       ? "{\"ok\":true}\n"
                       : "{\"ok\":false,\"error\":\"network_unavailable\"}\n";
        }
#endif
        return scheduler.command(text);
    };
    while (true) {
        if (reboot_at && time_us_64() >= reboot_at) {
            if (bootloader)
                reset_usb_boot(0, 0);
            watchdog_reboot(0, 0, 0);
            while (true)
                tight_loop_contents();
        }
        watchdog_update();
        watchdog_hw->scratch[1] = 3;
        // Refill RF first; networking is deferred for the entire armed/frame interval.
        scheduler.poll();
        const auto state = service.status().state;
        if (state != wsprrypico::wtp::State::Armed && state != wsprrypico::wtp::State::Running) {
            watchdog_hw->scratch[1] = 4;
            network.poll();
        }
        watchdog_hw->scratch[1] = 5;
        tud_task();
        wsprrypico::usb::service();
        if (wsprrypico::usb::take_console_reset()) {
            length = 0;
            overflow = false;
        }
        std::array<std::uint8_t, 64> console{};
        const auto count = reboot_at ? 0 : wsprrypico::usb::console_transport_read(console);
        for (std::size_t i = 0; i < count; ++i) {
            const auto b = console[i];
            if (b == '\n') {
                const auto response = overflow ? "{\"ok\":false,\"error\":\"line_too_long\"}\n"
                                               : command(std::string_view(line.data(), length));
                (void)wsprrypico::usb::console_write(response);
                std::fill(line.begin(), line.end(), 0);
                length = 0;
                overflow = false;
            } else if (b != '\r') {
                if (b < 32 || b > 126 || length == line.size())
                    overflow = true;
                else if (!overflow)
                    line[length++] = static_cast<char>(b);
            }
        }
        if (wsprrypico::usb::take_wtp_reset()) {
            offset = size = 0;
            if (wsprrypico::usb::wtp_connected())
                endpoint.connect("usb-physical");
            else
                endpoint.disconnect();
        }
        const auto now_ms = time_us_64() / 1000ULL;
        endpoint.poll(now_ms);
        if (wsprrypico::usb::wtp_connected()) {
            if (!reboot_at && endpoint.can_receive()) {
                if (offset == size) {
                    size = wsprrypico::usb::wtp_transport_read(input);
                    offset = 0;
                }
                offset += endpoint.receive(std::span(input).subspan(offset, size - offset), now_ms);
            }
            endpoint.consume_output(wsprrypico::usb::wtp_transport_write(endpoint.output()),
                                    now_ms);
        }
    }
}

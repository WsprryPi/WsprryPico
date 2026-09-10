#include "firmware_identity.hpp"
#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "network/identity.hpp"
#include "network/pico/server.hpp"
#include "network_credentials.hpp"
#include "pico/bootrom.h"
#include "pico/time.h"
#include "pico_adapters.hpp"
#include "standalone/pico/adapters.hpp"
#include "standalone/scheduler.hpp"
#include "standalone/wtp_profile.hpp"
#include "tusb.h"
#include "usb/transport.hpp"
#include "wtp/codec.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"

#include <malloc.h>
extern "C" char __HeapLimit, __end__, __StackLimit, __StackTop;
#include "hardware/sync.h"
#ifdef WSPRRY_PICO_STANDALONE_RF
#include "hardware/clocks.h"
#include "rf/pico/worker.hpp"
#include "rf/waveform.hpp"
#else
#include "standalone/dry_run_engine.hpp"
static_assert(WSPRRY_PICO_RF_OUTPUT_DISABLED == 1);
#endif
#include <array>
#include <charconv>

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
constexpr std::uint32_t stack_pattern = 0xa59c37e1;
__attribute__((noinline)) void paint_stack() {
    const auto saved = save_and_disable_interrupts();
    std::uintptr_t sp;
    asm volatile("mov %0, sp" : "=r"(sp));
    for (auto p = reinterpret_cast<std::uintptr_t>(&__StackLimit); p + 128 < sp; p += 4)
        *reinterpret_cast<volatile std::uint32_t*>(p) = stack_pattern;
    restore_interrupts(saved);
}
std::size_t stack_used() {
    auto p = reinterpret_cast<std::uintptr_t>(&__StackLimit);
    const auto top = reinterpret_cast<std::uintptr_t>(&__StackTop);
    while (p < top && *reinterpret_cast<volatile std::uint32_t*>(p) == stack_pattern)
        p += 4;
    return top - p;
}
std::size_t heap_peak = 0;
std::uint64_t monotonic_now(void*) {
    return time_us_64() * 1000ULL;
}
} // namespace
int main() {
    paint_stack();
    wsprrypico::wtp::available_memory = []() -> std::size_t {
        const auto capacity = reinterpret_cast<std::uintptr_t>(&__HeapLimit) -
                              reinterpret_cast<std::uintptr_t>(&__end__);
        const auto used = static_cast<std::size_t>(mallinfo().uordblks);
        heap_peak = std::max(heap_peak, used);
        return used < capacity ? capacity - used : 0;
    };
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
    const auto discipline = wsprrypico::standalone::clock_profile();
    static wsprrypico::time::UtcDiscipline clock(monotonic_now, nullptr, discipline);
    static wsprrypico::standalone::PicoFlash flash;
    static wsprrypico::standalone::Store store(flash);
    (void)store.load();
    // Both adapters claim PIO/DMA resources through the SDK allocator.
#ifdef WSPRRY_PICO_STANDALONE_RF
    auto& engine = wsprrypico::rf::start_worker(clock);
#else
    static wsprrypico::standalone::DryRunEngine engine;
#endif
    static wsprrypico::firmware::PicoIdentitySource identities;
#ifdef WSPRRY_PICO_STANDALONE_RF
    const auto config = wsprrypico::standalone::wtp_profile(true);
#else
    const auto config = wsprrypico::standalone::wtp_profile(false);
#endif
    static wsprrypico::wtp::JobService service(clock, engine, identities, config);
    static wsprrypico::wtp::Endpoint endpoint(service, identities.device_id(),
                                              wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::standalone::Scheduler scheduler(store, service);
    const bool deployment_matches = wsprrypico::network::deployment_identity_matches(
        identities.device_id(), wsprrypico::network::credentials::device_id,
        wsprrypico::network::credentials::hostname);
    static wsprrypico::standalone::PicoNetwork network(clock,
                                                       wsprrypico::network::credentials::hostname);
    if (recovery)
        (void)scheduler.command("STOP");
    watchdog_hw->scratch[1] = 2;
    if (!recovery && store.healthy() && store.config())
        (void)network.start(*store.config());
    static wsprrypico::network::BrowserApi browser_api(service, store, scheduler, network,
                                                       identities.device_id(),
                                                       wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::network::PicoServer server(service, browser_api, identities.device_id(),
                                                  wsprrypico::firmware::kFirmwareVersion);
    browser_api.set_active_job_connections(true);
    if (!recovery && deployment_matches && network.initialized())
        (void)server.start();
    network.listener_status(server.configured(), server.listening(), deployment_matches);
    watchdog_hw->scratch[1] = 3;
    std::array<std::uint8_t, 64> input{};
    std::size_t offset = 0, size = 0;
    std::array<char, wsprrypico::standalone::max_config_bytes + 7> line{};
    std::size_t length = 0;
    bool overflow = false;
    std::uint64_t reboot_at = 0;
    bool bootloader = false, browser_reboot = false;
    struct RestartContext {
        wsprrypico::standalone::Scheduler* scheduler;
        wsprrypico::wtp::RfEngine* output_engine;
        std::uint64_t* at;
        bool* browser;
    } restart_context{&scheduler, &engine, &reboot_at, &browser_reboot};
    browser_api.restart_control(
        [](void* context) {
            auto& state = *static_cast<RestartContext*>(context);
            if (*state.at || !state.scheduler->idle())
                return false;
            (void)state.scheduler->command("STOP");
            if (!state.output_engine->disable(monotonic_now(nullptr) + 100'000'000ULL) ||
                state.output_engine->output_active())
                return false;
            *state.browser = true;
            *state.at = time_us_64() + 250'000;
            return true;
        },
        &restart_context);
#ifdef WSPRRY_PICO_STANDALONE_RF
    std::uint64_t last_loop_us = 0, max_loop_us = 0, max_refill_us = 0;
    std::uint64_t max_usb_us = 0, max_request_us = 0;
    auto maximum = [](std::uint64_t& peak, std::uint64_t start) {
        const auto elapsed = time_us_64() - start;
        if (elapsed > peak)
            peak = elapsed;
    };
#endif
    auto command = [&](std::string_view text) -> std::string {
        if (text == "INFO") {
            std::string result =
                "{\"ok\":true,\"device_id\":" +
                wsprrypico::wtp::json::quote(identities.device_id()) + ",\"revision\":" +
                wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                ",\"firmware\":" +
                wsprrypico::wtp::json::quote(wsprrypico::firmware::kFirmwareVersion) +
                ",\"deployment_identity_matches\":" + (deployment_matches ? "true" : "false") +
                ",\"recovery_boot\":" + (recovery ? "true" : "false") +
                ",\"fault_stage\":" + std::to_string(fault_stage) +
                ",\"fault_hash\":" + std::to_string(fault_hash) +
                ",\"fault_pc\":" + std::to_string(fault_pc) +
                ",\"fault_status\":" + std::to_string(fault_status) +
                ",\"network\":" + network.status() +
                ",\"heap_allocated_bytes\":" + std::to_string(mallinfo().uordblks) +
                ",\"heap_available_bytes\":" + std::to_string(wsprrypico::wtp::available_memory()) +
                ",\"heap_sampled_peak_bytes\":" + std::to_string(heap_peak) +
                ",\"core0_stack_used_bytes\":" + std::to_string(stack_used()) +
                ",\"tls_peak_bytes\":" + std::to_string(server.tls_peak()) +
                ",\"tls_allocated_bytes\":" + std::to_string(server.tls_allocated()) +
                ",\"tls_allocation_failures\":" + std::to_string(server.tls_failures());
#ifdef WSPRRY_PICO_STANDALONE_RF
            const auto metrics = engine.metrics();
            result += ",\"launch_observed_ns\":\"" + std::to_string(metrics.launch_ns) + "\"" +
                      ",\"dma_irqs\":" + std::to_string(metrics.dma_irqs) +
                      ",\"max_dma_irq_ns\":" + std::to_string(metrics.max_irq_ns) +
                      ",\"core1_stack_used_bytes\":" + std::to_string(metrics.stack_used_bytes) +
                      ",\"rf_worker_commands\":" + std::to_string(metrics.commands) +
                      ",\"rf_max_service_gap_ns\":\"" + std::to_string(metrics.max_service_gap_ns) +
                      "\",\"rf_max_poll_ns\":\"" + std::to_string(metrics.max_poll_ns) +
                      "\",\"rf_max_roundtrip_ns\":\"" + std::to_string(metrics.max_roundtrip_ns) +
                      "\"" + ",\"max_loop_us\":" + std::to_string(max_loop_us) +
                      ",\"max_authority_poll_us\":" + std::to_string(max_refill_us) +
                      ",\"max_usb_us\":" + std::to_string(max_usb_us) +
                      ",\"max_request_us\":" + std::to_string(max_request_us) +
                      ",\"engine_diagnostic\":" + wsprrypico::wtp::json::quote(engine.diagnostic());
#endif
            auto status = scheduler.status();
            if (!status.empty() && status.back() == '\n')
                status.pop_back();
            return result + ",\"status\":" + status + "}\n";
        }
        if (text == "ABORT") {
            (void)scheduler.command(
                "STOP"); // Suspend autonomous work before physical cancellation.
            const auto result = service.local_abort();
            return result.ok
                       ? scheduler.status()
                       : "{\"ok\":false,\"error\":" + wsprrypico::wtp::error_json(result.error) +
                             "}\n";
        }
        if (text == "REBOOT" || text == "BOOTSEL") {
            (void)scheduler.command("STOP");
            if (!(browser_reboot ? scheduler.idle() : scheduler.reset_permitted()) ||
                !engine.disable(monotonic_now(nullptr) + 100'000'000ULL) || engine.output_active())
                return "{\"ok\":false,\"error\":\"not_idle\"}\n";
            browser_reboot = false;
            bootloader = text == "BOOTSEL";
            reboot_at = time_us_64() + 250'000;
            return "{\"ok\":true,\"rebooting\":true}\n";
        }
#ifndef WSPRRY_PICO_STANDALONE_RF
        if (text == "NETLINK") {
            return "{\"ok\":true,\"device_id\":" +
                   wsprrypico::wtp::json::quote(identities.device_id()) + ",\"revision\":" +
                   wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                   ",\"boot_id\":" + wsprrypico::wtp::json::quote(service.status().boot_id) +
                   ",\"association\":" + network.association() + "}\n";
        }
        if (text.starts_with("NETTRACE ")) {
            std::uint64_t after = 0;
            const auto cursor = text.substr(9);
            const auto parsed = std::from_chars(cursor.data(), cursor.data() + cursor.size(), after);
            if (parsed.ec != std::errc{} || parsed.ptr != cursor.data() + cursor.size())
                return "{\"ok\":false,\"error\":\"trace_cursor\"}\n";
            return "{\"ok\":true,\"device_id\":" + wsprrypico::wtp::json::quote(identities.device_id()) +
                ",\"revision\":" + wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                ",\"boot_id\":" + wsprrypico::wtp::json::quote(service.status().boot_id) +
                ",\"trace\":" + network.trace_page(after) + "}\n";
        }
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
            // Network ownership can change while the response/USB ACK drains.
            // A new owner cancels reset rather than losing its accepted job.
            if (!(browser_reboot ? scheduler.idle() : scheduler.reset_permitted()) ||
                !engine.disable(monotonic_now(nullptr) + 100'000'000ULL) ||
                engine.output_active()) {
                reboot_at = 0;
                bootloader = false;
                browser_reboot = false;
                continue;
            }
            if (bootloader)
                reset_usb_boot(0, 0);
            watchdog_reboot(0, 0, 0);
            while (true)
                tight_loop_contents();
        }
        watchdog_update();
        watchdog_hw->scratch[1] = 3;
#ifdef WSPRRY_PICO_STANDALONE_RF
        const bool measuring = service.status().state == wsprrypico::wtp::State::Running;
        const auto loop_us = time_us_64();
        if (measuring && last_loop_us)
            maximum(max_loop_us, last_loop_us);
        last_loop_us = measuring ? loop_us : 0;
#endif
        // Core 1 owns physical refills/launch. Core 0 reconciles authority and
        // services all transports; packet arrival never times waveform events.
        scheduler.poll();
#ifdef WSPRRY_PICO_STANDALONE_RF
        if (measuring)
            maximum(max_refill_us, loop_us);
#endif
        watchdog_hw->scratch[1] = 4;
        const auto network_state = service.status().state;
        if (server.listening() || (network_state != wsprrypico::wtp::State::Armed &&
                                   network_state != wsprrypico::wtp::State::Running))
            network.poll();
        service.poll();
        server.poll(network.link_up(),
                    network.ipv4() +
                        (server.port() == 443 ? "" : ":" + std::to_string(server.port())));
        service.poll();
        watchdog_hw->scratch[1] = 5;
#ifdef WSPRRY_PICO_STANDALONE_RF
        const auto usb_us = time_us_64();
#endif
        tud_task();
        wsprrypico::usb::service();
#ifdef WSPRRY_PICO_STANDALONE_RF
        if (measuring)
            maximum(max_usb_us, usb_us);
#endif
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
                if (!wsprrypico::usb::console_write(response))
                    (void)wsprrypico::usb::console_write(
                        "{\"ok\":false,\"error\":\"console_response_capacity\"}\n");
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
#ifdef WSPRRY_PICO_STANDALONE_RF
                const auto request_us = time_us_64();
#endif
                offset += endpoint.receive(std::span(input).subspan(offset, size - offset), now_ms);
#ifdef WSPRRY_PICO_STANDALONE_RF
                if (measuring)
                    maximum(max_request_us, request_us);
#endif
            }
            endpoint.consume_output(wsprrypico::usb::wtp_transport_write(endpoint.output()),
                                    now_ms);
        }
    }
}

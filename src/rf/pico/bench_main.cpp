#include "firmware_identity.hpp"
#include "hardware/clocks.h"
#include "hardware/sync.h"
#include "pico/bootrom.h"
#include "pico/unique_id.h"
#include "rf/bench.hpp"
#include "rf/pico/pico_pio_dma.hpp"
#include "tusb.h"
#include "usb/transport.hpp"

#include <array>
#include <cstdio>
#include <malloc.h>

extern "C" char __StackLimit, __StackTop;

namespace {
class Clock final : public wsprrypico::rf::BenchClock {
    std::uint64_t now_ns() const override {
        return time_us_64() * 1000;
    }
};
constexpr std::uint32_t stack_pattern = 0xa59c37e1;
// Paint only unused stack below this function's live frame, before USB starts.
__attribute__((noinline)) void paint_stack() {
    const auto saved = save_and_disable_interrupts();
    std::uintptr_t sp;
    asm volatile("mov %0, sp" : "=r"(sp));
    for (auto p = reinterpret_cast<std::uintptr_t>(&__StackLimit); p + 128 < sp; p += 4)
        *reinterpret_cast<volatile std::uint32_t*>(p) = stack_pattern;
    restore_interrupts(saved);
}
std::uintptr_t stack_used() {
    auto p = reinterpret_cast<std::uintptr_t>(&__StackLimit);
    const auto top = reinterpret_cast<std::uintptr_t>(&__StackTop);
    while (p < top && *reinterpret_cast<volatile std::uint32_t*>(p) == stack_pattern)
        p += 4;
    return top - p;
}
std::string info(wsprrypico::rf::PicoPioDma& hardware) {
    const auto metrics = hardware.metrics();
    std::array<char, 1024> output{};
    std::array<char, 2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1> serial{};
    pico_get_unique_board_id_string(serial.data(), serial.size());
    const auto heap = mallinfo();
    std::snprintf(
        output.data(), output.size(),
        "{\"ok\":true,\"product\":\"WsprryPico-RFBench\",\"revision\":\"%s\","
        "\"sdk\":\"%s\",\"board\":\"pico2_w\",\"serial\":\"%s\","
        "\"sys_hz\":%lu,\"heap_allocated_bytes\":%d,\"heap_free_bytes\":%d,"
        "\"stack_reserved_bytes\":%lu,\"stack_canary_used_bytes\":%lu,"
        "\"dma_irqs\":%llu,\"max_dma_irq_ns\":%llu,\"launch_observed_ns\":%llu,"
        "\"utc_synchronized\":false}\n",
        wsprrypico::firmware::kBuildRevision, wsprrypico::firmware::kPicoSdkVersion, serial.data(),
        static_cast<unsigned long>(clock_get_hz(clk_sys)), heap.uordblks, heap.fordblks,
        static_cast<unsigned long>(reinterpret_cast<std::uintptr_t>(&__StackTop) -
                                   reinterpret_cast<std::uintptr_t>(&__StackLimit)),
        static_cast<unsigned long>(stack_used()), static_cast<unsigned long long>(metrics.dma_irqs),
        static_cast<unsigned long long>(metrics.max_irq_ns),
        static_cast<unsigned long long>(metrics.launch_ns));
    return output.data();
}
} // namespace

int main() {
    paint_stack();
    tud_init(0);
    static Clock clock;
    static wsprrypico::rf::PicoPioDma hardware;
    static wsprrypico::rf::PioDmaSink sink(hardware);
    static wsprrypico::rf::StreamEngine engine(sink);
    static wsprrypico::rf::Bench bench(engine, clock);
    std::array<char, 128> line{};
    std::size_t used = 0, sent = 0;
    bool overflow = false;
    std::string response;
    std::uint64_t reboot_at = 0;
    while (true) {
        if (reboot_at && time_us_64() >= reboot_at)
            reset_usb_boot(0, 0);
        bench.poll();
        tud_task();
        wsprrypico::usb::service();
        if (wsprrypico::usb::take_wtp_reset()) {
            (void)bench.command("STOP");
            used = sent = 0;
            overflow = false;
            response.clear();
        }
        if (!wsprrypico::usb::wtp_connected())
            continue;
        if (sent < response.size()) {
            const auto* bytes = reinterpret_cast<const std::uint8_t*>(response.data());
            sent += wsprrypico::usb::wtp_transport_write(
                std::span(bytes + sent, response.size() - sent));
            continue;
        }
        if (reboot_at)
            continue;
        std::array<std::uint8_t, 1> input{};
        if (wsprrypico::usb::wtp_transport_read(input) == 0)
            continue;
        if (input[0] == '\n') {
            const std::string_view command(line.data(), used);
            response = overflow            ? "{\"ok\":false,\"error\":\"line_too_long\"}\n"
                       : command == "INFO" ? info(hardware)
                                           : bench.command(command);
            if (!overflow && command == "BOOTSEL") {
                response = bench.command("STOP");
                if (response.find("\"ok\":true") != std::string::npos) {
                    response = "{\"ok\":true,\"state\":\"bootloader\"}\n";
                    reboot_at = time_us_64() + 200000;
                }
            }
            sent = used = 0;
            overflow = false;
        } else if (input[0] < 32 || input[0] > 126 || used == line.size()) {
            overflow = true;
        } else if (!overflow) {
            line[used++] = static_cast<char>(input[0]);
        }
    }
}

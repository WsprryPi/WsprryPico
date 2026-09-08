#include "firmware_identity.hpp"
#include "hardware/clocks.h"
#include "pico/bootrom.h"
#include "pico/time.h"
#include "pico_adapters.hpp"
#include "rf/pico/pico_pio_dma.hpp"
#include "rf/wtp_profile.hpp"
#include "time/usb_time_source.hpp"
#include "tusb.h"
#include "usb/transport.hpp"
#include "wtp/codec.hpp"
#include "wtp/endpoint.hpp"

#include <array>
#include <cstdio>
#include <span>
#include <string>

namespace {
std::uint64_t monotonic_now(void*) {
    return time_us_64() * 1000ULL;
}

void console_response(std::string_view response) {
    (void)wsprrypico::usb::console_write(response);
}
} // namespace

int main() {
    set_sys_clock_khz(wsprrypico::rf::sample_rate / 1000, true);
    tud_init(0);
    wsprrypico::time::DisciplineConfig discipline_config;
    discipline_config.synchronized_for_ns = 10'000'000'000ULL;
    discipline_config.holdover_for_ns = 120'000'000'000ULL;
    static wsprrypico::time::UtcDiscipline clock(monotonic_now, nullptr, discipline_config);
    static wsprrypico::time::UsbTimeSource time_source(clock);
    static wsprrypico::rf::PicoPioDma hardware;
    static wsprrypico::rf::PioDmaSink sink(hardware);
    static wsprrypico::rf::StreamEngine engine(sink);
    static wsprrypico::firmware::PicoIdentitySource identities;
    auto service_config = wsprrypico::rf::wtp_profile("pio-dma-gp2");
    service_config.maximum_arm_uncertainty_ns = 20'000'000ULL;
    static wsprrypico::wtp::JobService service(clock, engine, identities, service_config);
    static wsprrypico::wtp::Endpoint endpoint(service, identities.device_id(),
                                              wsprrypico::firmware::kFirmwareVersion);
    std::array<std::uint8_t, 64> wtp_input{};
    std::size_t wtp_offset = 0, wtp_size = 0;
    std::array<char, 192> line{};
    std::size_t line_size = 0;
    bool line_overflow = false, startup = false;
    std::uint64_t reboot_at = 0;

    while (true) {
        if (reboot_at && time_us_64() >= reboot_at)
            reset_usb_boot(0, 0);
        tud_task();
        wsprrypico::usb::service();
        if (wsprrypico::usb::take_console_reset()) {
            time_source.reset();
            line_size = 0;
            line_overflow = false;
            startup = false;
        }
        if (wsprrypico::usb::console_connected() && !startup) {
            console_response("WsprryPico-RFWTP\r\nclock_source: USB sampled\r\n"
                             "engine: RP2350 PIO/DMA GP2\r\nrf_output: inactive\r\n");
            startup = true;
        }
        if (wsprrypico::usb::console_connected() && !reboot_at) {
            std::array<std::uint8_t, 1> byte{};
            if (wsprrypico::usb::console_transport_read(byte)) {
                if (byte[0] == '\n') {
                    const std::string_view command(line.data(), line_size);
                    if (line_overflow)
                        console_response("{\"ok\":false,\"error\":\"line_too_long\"}\n");
                    else if (command == "BOOTSEL") {
                        if (engine.output_active())
                            console_response("{\"ok\":false,\"error\":\"output_active\"}\n");
                        else if (!engine.disable(monotonic_now(nullptr) + 100'000'000ULL))
                            console_response("{\"ok\":false,\"error\":\"disable_failed\"}\n");
                        else {
                            console_response("{\"ok\":true,\"state\":\"bootloader\"}\n");
                            reboot_at = time_us_64() + 200'000;
                        }
                    } else if (command == "INFO") {
                        const auto metrics = hardware.metrics();
                        const auto status = service.status();
                        std::array<char, 640> response{};
                        std::snprintf(
                            response.data(), response.size(),
                            "{\"ok\":true,\"device_id\":\"%s\",\"revision\":\"%s\",\"sample_rate_"
                            "hz\":%llu,\"state\":\"%s\",\"output_active\":%s,"
                            "\"engine_diagnostic\":\"%s\",\"sink_diagnostic\":\"%s\","
                            "\"dma_irqs\":%llu,"
                            "\"max_dma_irq_ns\":%llu,\"launch_observed_ns\":%llu}\n",
                            identities.device_id().c_str(), wsprrypico::firmware::kBuildRevision,
                            static_cast<unsigned long long>(wsprrypico::rf::sample_rate),
                            wsprrypico::wtp::state_name(status.state).c_str(),
                            status.output_active ? "true" : "false", engine.diagnostic().data(),
                            sink.diagnostic().data(),
                            static_cast<unsigned long long>(metrics.dma_irqs),
                            static_cast<unsigned long long>(metrics.max_irq_ns),
                            static_cast<unsigned long long>(metrics.launch_ns));
                        console_response(response.data());
                    } else
                        console_response(time_source.command(command));
                    line_size = 0;
                    line_overflow = false;
                } else if (byte[0] == '\r') {
                } else if (byte[0] < 32 || byte[0] > 126 || line_size == line.size()) {
                    line_overflow = true;
                } else if (!line_overflow) {
                    line[line_size++] = static_cast<char>(byte[0]);
                }
            }
        }
        if (wsprrypico::usb::take_wtp_reset()) {
            wtp_offset = wtp_size = 0;
            if (wsprrypico::usb::wtp_connected())
                endpoint.connect("usb-physical");
            else
                endpoint.disconnect();
        }
        const auto now_ms = time_us_64() / 1000ULL;
        endpoint.poll(now_ms);
        if (wsprrypico::usb::wtp_connected()) {
            // The client avoids status polling during RF, but the endpoint stays
            // available so ABORT and connection-loss semantics remain intact.
            if (endpoint.can_receive()) {
                if (wtp_offset == wtp_size) {
                    wtp_size = wsprrypico::usb::wtp_transport_read(wtp_input);
                    wtp_offset = 0;
                }
                wtp_offset += endpoint.receive(
                    std::span(wtp_input).subspan(wtp_offset, wtp_size - wtp_offset), now_ms);
            }
            endpoint.consume_output(wsprrypico::usb::wtp_transport_write(endpoint.output()),
                                    now_ms);
        }
    }
}

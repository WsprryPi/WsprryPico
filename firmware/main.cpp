#include "firmware_identity.hpp"
#include "pico/time.h"
#include "pico_adapters.hpp"
#include "tusb.h"
#include "usb/transport.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/inhibited_rf_engine.hpp"

#include <array>
#include <cstdint>
#include <cstdio>
#include <span>
#include <string_view>

#ifndef WSPRRY_PICO_RF_OUTPUT_DISABLED
#error "The firmware foundation requires RF output to be disabled"
#endif

static_assert(WSPRRY_PICO_RF_OUTPUT_DISABLED == 1);

namespace {

using wsprrypico::usb::console_write;

void write_startup(const wsprrypico::firmware::PicoIdentitySource& identities,
                   const wsprrypico::wtp::ServiceStatus& status) {
    std::array<char, 192> line{};
    console_write("WsprryPico starting\r\n");
    std::snprintf(line.data(), line.size(), "firmware: %s\r\nrevision: %s\r\n",
                  wsprrypico::firmware::kFirmwareVersion, wsprrypico::firmware::kBuildRevision);
    console_write(line.data());
    std::snprintf(line.data(), line.size(), "board: %s\r\nprocessor: %s\r\nsdk: %s\r\n",
                  wsprrypico::firmware::kBoard, wsprrypico::firmware::kProcessor,
                  wsprrypico::firmware::kPicoSdkVersion);
    console_write(line.data());
    std::snprintf(line.data(), line.size(), "device_id: %s\r\nboot_id: %s\r\n",
                  identities.device_id().c_str(), status.boot_id.c_str());
    console_write(line.data());
    console_write("clock: unsynchronized\r\nengine: inhibited\r\nrf_output: false\r\n");
    console_write(status.state == wsprrypico::wtp::State::Empty ? "job_service: ready\r\n"
                                                                : "job_service: fault\r\n");
    console_write("wtp: WTP/1 endpoint; RF inhibited\r\n");
}

} // namespace

int main() {
    tud_init(0);

    static wsprrypico::firmware::PicoClock clock;
    static wsprrypico::wtp::InhibitedRfEngine engine;
    static wsprrypico::firmware::PicoIdentitySource identities;
    static wsprrypico::wtp::JobService service(clock, engine, identities);
    static wsprrypico::wtp::Endpoint endpoint(service, identities.device_id(),
                                              wsprrypico::firmware::kFirmwareVersion);
    std::array<std::uint8_t, 64> input{};
    std::size_t input_offset = 0, input_size = 0;
    bool startup_written = false;

    while (true) {
        tud_task();
        wsprrypico::usb::service();
        std::array<std::uint8_t, 64> ignored_console{};
        (void)wsprrypico::usb::console_transport_read(ignored_console);
        const bool console_connected = wsprrypico::usb::console_connected();
        if (wsprrypico::usb::take_console_reset()) {
            startup_written = false;
        }
        if (!console_connected) {
            startup_written = false;
        } else if (!startup_written) {
            write_startup(identities, service.status());
            startup_written = true;
        }
        if (wsprrypico::usb::take_wtp_reset()) {
            input_offset = input_size = 0;
            if (wsprrypico::usb::wtp_connected())
                endpoint.connect("usb-physical");
            else
                endpoint.disconnect();
        }
        const auto now_ms = time_us_64() / 1000ULL;
        endpoint.poll(now_ms);
        if (wsprrypico::usb::wtp_connected()) {
            if (endpoint.can_receive()) {
                if (input_offset == input_size) {
                    input_size = wsprrypico::usb::wtp_transport_read(input);
                    input_offset = 0;
                }
                input_offset += endpoint.receive(
                    std::span(input).subspan(input_offset, input_size - input_offset), now_ms);
            }
            endpoint.consume_output(wsprrypico::usb::wtp_transport_write(endpoint.output()),
                                    now_ms);
        }
        if (engine.output_active()) {
            console_write("fatal: inhibited engine reported active output\r\n");
            while (true) {
                tud_task();
                wsprrypico::usb::service();
            }
        }
    }
}

#include "firmware_identity.hpp"
#include "pico/time.h"
#include "pico_adapters.hpp"
#include "tusb.h"
#include "usb/transport.hpp"
#include "wtp/frame_parser.hpp"
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
    console_write("wtp: framing active; JSON adapter unavailable\r\n");
}

void process_wtp(wsprrypico::wtp::FrameParser& parser) {
    std::array<std::uint8_t, 64> input{};
    if (!parser.closed()) {
        const auto count = wsprrypico::usb::wtp_transport_read(input);
        const auto now_ms = time_us_64() / 1000ULL;
        for (const auto& event : parser.feed(std::span(input).first(count), now_ms)) {
            if (event.kind == wsprrypico::wtp::FrameEventKind::Payload) {
                console_write("wtp: valid frame received; request dispatch unavailable\r\n");
            } else if (event.kind == wsprrypico::wtp::FrameEventKind::InvalidFrame) {
                console_write("wtp: invalid frame\r\n");
            } else {
                console_write("wtp: parser closed\r\n");
            }
        }
    }
    if (!parser.closed()) {
        const auto now_ms = time_us_64() / 1000ULL;
        for (const auto& event : parser.check_timeout(now_ms)) {
            if (event.kind == wsprrypico::wtp::FrameEventKind::Closed) {
                console_write("wtp: partial-frame timeout\r\n");
            }
        }
    }
}

} // namespace

int main() {
    tud_init(0);

    wsprrypico::firmware::PicoClock clock;
    wsprrypico::wtp::InhibitedRfEngine engine;
    wsprrypico::firmware::PicoIdentitySource identities;
    wsprrypico::wtp::JobService service(clock, engine, identities);
    wsprrypico::wtp::FrameParser parser;
    bool startup_written = false;

    while (true) {
        tud_task();
        wsprrypico::usb::service();
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
            parser = wsprrypico::wtp::FrameParser{};
        }
        if (wsprrypico::usb::wtp_connected()) {
            process_wtp(parser);
        }
        service.poll();
        if (engine.output_active()) {
            console_write("fatal: inhibited engine reported active output\r\n");
            while (true) {
                tud_task();
                wsprrypico::usb::service();
            }
        }
    }
}

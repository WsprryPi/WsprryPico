#include "firmware_identity.hpp"
#include "pico/time.h"
#include "pico_adapters.hpp"
#include "standalone/pico/adapters.hpp"
#include "standalone/scheduler.hpp"
#include "tusb.h"
#include "usb/transport.hpp"
#include "wtp/endpoint.hpp"
#ifdef WSPRRY_PICO_STANDALONE_RF
#include "hardware/clocks.h"
#include "rf/pico/pico_pio_dma.hpp"
#else
#include "standalone/dry_run_engine.hpp"
static_assert(WSPRRY_PICO_RF_OUTPUT_DISABLED == 1);
#endif
#include <array>

namespace {
std::uint64_t monotonic_now(void*) {
    return time_us_64() * 1000ULL;
}
} // namespace
int main() {
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
    config.maximum_arm_uncertainty_ns = 20'000'000ULL;
    config.maximum_holdover_age_ns = 90'000'000'000ULL;
#ifdef WSPRRY_PICO_STANDALONE_RF
    config.capability_engine = "pio-dma-gp2";
#endif
    static wsprrypico::wtp::JobService service(clock, engine, identities, config);
    static wsprrypico::wtp::Endpoint endpoint(service, identities.device_id(),
                                              wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::standalone::Scheduler scheduler(store, service);
    static wsprrypico::standalone::PicoNetwork network(clock);
    if (store.healthy() && store.config())
        (void)network.start(*store.config());
    std::array<std::uint8_t, 64> input{};
    std::size_t offset = 0, size = 0;
    std::array<char, wsprrypico::standalone::max_config_bytes + 7> line{};
    std::size_t length = 0;
    bool overflow = false;
    while (true) {
        // Refill RF first; networking is deferred for the entire armed/frame interval.
        scheduler.poll();
        const auto state = service.status().state;
        if (state != wsprrypico::wtp::State::Armed && state != wsprrypico::wtp::State::Running)
            network.poll();
        tud_task();
        wsprrypico::usb::service();
        if (wsprrypico::usb::take_console_reset()) {
            length = 0;
            overflow = false;
        }
        std::array<std::uint8_t, 64> console{};
        const auto count = wsprrypico::usb::console_transport_read(console);
        for (std::size_t i = 0; i < count; ++i) {
            const auto b = console[i];
            if (b == '\n') {
                const auto response =
                    overflow ? "{\"ok\":false,\"error\":\"line_too_long\"}\n"
                             : scheduler.command(std::string_view(line.data(), length));
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
            if (endpoint.can_receive()) {
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

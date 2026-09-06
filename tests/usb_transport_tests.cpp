#include "tusb.h"
#include "usb/roles.h"
#include "usb/transport.hpp"
#include "wtp/frame_parser.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <deque>
#include <iostream>
#include <string>
#include <vector>

#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x)) {                                                                                \
            std::cerr << __LINE__ << ": " << #x << '\n';                                           \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
namespace {
struct Port {
    bool connected = false;
    std::size_t capacity = 64;
    std::deque<std::uint8_t> rx;
    std::vector<std::uint8_t> pending;
    std::vector<std::uint8_t> delivered;
};
std::array<Port, 2> ports;
void reset() {
    tud_umount_cb();
    ports = {};
    wsprrypico::usb::service();
    (void)wsprrypico::usb::take_wtp_reset();
}
void open(unsigned port) {
    ports[port].connected = true;
    tud_cdc_line_state_cb(port, true, false);
    wsprrypico::usb::service();
}
} // namespace
extern "C" bool tud_cdc_n_connected(std::uint8_t p) {
    return ports.at(p).connected;
}
extern "C" std::uint32_t tud_cdc_n_write(std::uint8_t p, const void* data, std::uint32_t n) {
    auto& port = ports.at(p);
    auto count = std::min<std::size_t>(n, port.capacity - port.pending.size());
    auto bytes = static_cast<const std::uint8_t*>(data);
    port.pending.insert(port.pending.end(), bytes, bytes + count);
    return count;
}
extern "C" std::uint32_t tud_cdc_n_read(std::uint8_t p, void* data, std::uint32_t n) {
    auto& rx = ports.at(p).rx;
    auto count = std::min<std::size_t>(n, rx.size());
    auto bytes = static_cast<std::uint8_t*>(data);
    for (std::size_t i = 0; i < count; ++i) {
        bytes[i] = rx.front();
        rx.pop_front();
    }
    return count;
}
extern "C" std::uint32_t tud_cdc_n_write_flush(std::uint8_t p) {
    auto& port = ports.at(p);
    port.delivered.insert(port.delivered.end(), port.pending.begin(), port.pending.end());
    auto count = port.pending.size();
    port.pending.clear();
    return count;
}
extern "C" bool tud_cdc_n_write_clear(std::uint8_t p) {
    ports.at(p).pending.clear();
    return true;
}
extern "C" void tud_cdc_n_read_flush(std::uint8_t p) {
    ports.at(p).rx.clear();
}

int main() {
    using namespace wsprrypico::usb;
    reset();
    const std::array<std::uint8_t, 5> binary{0, 255, 10, 13, 128};
    CHECK(!console_write("offline"));
    CHECK(wtp_transport_write(binary) == 0);
    open(USB_CDC_CONSOLE);
    open(USB_CDC_WTP);
    CHECK(take_wtp_reset());
    CHECK(!take_wtp_reset());
    // Startup-sized UTF-8 diagnostic survives short writes; WTP stays silent.
    const std::string banner = "WsprryPico\r\n" + std::string(600, 'x') + " UTF-8: π\r\n";
    ports[0].capacity = 7;
    CHECK(console_write(banner));
    for (unsigned i = 0; i < 200; ++i)
        service();
    CHECK(std::string(ports[0].delivered.begin(), ports[0].delivered.end()) == banner);
    CHECK(ports[1].delivered.empty());
    ports[1].capacity = 2;
    std::size_t sent = 0;
    while (sent < binary.size()) {
        sent += wtp_transport_write(std::span(binary).subspan(sent));
        if (sent < binary.size()) {
            CHECK(wtp_transport_write(binary) == 0);
        }
        service();
    }
    CHECK(ports[1].delivered == std::vector<std::uint8_t>(binary.begin(), binary.end()));
    // Slow console and saturated WTP independently return without blocking.
    ports[0].capacity = 0;
    ports[1].capacity = 0;
    CHECK(console_write(std::string(kConsoleCapacity, 'a')));
    CHECK(!console_write("π"));
    CHECK(wtp_transport_write(binary) == 0);
    for (unsigned i = 0; i < 10; ++i)
        service();
    // A stalled console does not stall binary WTP output, and a stalled WTP
    // does not stall a wrapped, full console ring once Console resumes reading.
    ports[1].capacity = 64;
    CHECK(wtp_transport_write(binary) == binary.size());
    service();
    CHECK(ports[1].delivered.size() == 2 * binary.size());
    ports[1].capacity = 0;
    ports[0].capacity = 13;
    for (unsigned i = 0; i < 200; ++i)
        service();
    CHECK(std::string(ports[0].delivered.begin(), ports[0].delivered.end()) ==
          banner + std::string(kConsoleCapacity, 'a'));
    ports[0].delivered.assign(banner.begin(), banner.end());
    ports[1].delivered.assign(binary.begin(), binary.end());
    ports[0].capacity = 0;
    CHECK(console_write("discard on reconnect"));
    // Console RX is available to an explicit source adapter and cannot consume the WTP frame.
    const std::array<std::uint8_t, 2> payload{'{', '}'};
    auto frame = wsprrypico::wtp::encode_frame(payload);
    ports[0].rx = std::deque<std::uint8_t>(200, 'c');
    ports[1].rx = {frame.begin(), frame.end()};
    service();
    CHECK(ports[0].rx.size() == 200);
    std::array<std::uint8_t, 256> input{};
    CHECK(console_transport_read(input) == kServiceBytes);
    CHECK(ports[0].rx.size() == 200 - kServiceBytes);
    auto count = wtp_transport_read(input);
    CHECK(count == frame.size());
    wsprrypico::wtp::FrameParser parser;
    auto events = parser.feed(std::span(input).first(count), 0);
    CHECK(events.size() == 1);
    CHECK(events[0].payload == std::vector<std::uint8_t>(payload.begin(), payload.end()));
    ports[1].rx = std::deque<std::uint8_t>(200, 'w');
    CHECK(wtp_transport_read(input) == kServiceBytes);
    // Falling/rising DTR between polls must still clear stale data/reset parser.
    ports[1].capacity = 64;
    CHECK(wtp_transport_write(binary) == binary.size());
    tud_cdc_line_state_cb(1, false, false);
    tud_cdc_line_state_cb(1, true, false);
    service();
    CHECK(take_wtp_reset());
    CHECK(ports[1].rx.empty());
    CHECK(ports[1].pending.empty());
    CHECK(ports[1].delivered == std::vector<std::uint8_t>(binary.begin(), binary.end()));
    (void)take_console_reset();
    tud_cdc_line_state_cb(0, false, false);
    CHECK(take_console_reset());
    service();
    ports[0].capacity = 64;
    CHECK(console_write("new session"));
    service();
    CHECK(std::string(ports[0].delivered.begin(), ports[0].delivered.end()) ==
          banner + "new session");
    // USB reconfiguration resets both sessions even if polls miss disconnect.
    ports[1].rx.push_back(99);
    tud_mount_cb();
    CHECK(take_wtp_reset());
    CHECK(take_console_reset());
    CHECK(ports[1].rx.empty());
    reset();
    CHECK(!wtp_connected());
    CHECK(wtp_transport_read(input) == 0);
    std::cout << "USB transport behavior passed\n";
}

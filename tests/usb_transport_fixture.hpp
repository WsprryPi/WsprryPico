#pragma once
#include "tusb.h"
#include "usb/roles.h"
#include "usb/transport.hpp"
#include <algorithm>
#include <array>
#include <deque>
#include <vector>
namespace {
struct Port {
    bool connected = false;
    std::size_t capacity = 64;
    std::deque<std::uint8_t> rx;
    std::vector<std::uint8_t> pending;
    std::vector<std::uint8_t> delivered;
};
std::array<Port, USB_CDC_COUNT> ports;
void reset() {
    tud_umount_cb();
    ports = {};
    wsprrypico::usb::service();
#ifdef WSPRRY_PICO_RF_BENCH
    (void)wsprrypico::usb::take_bench_reset();
#endif
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
extern "C" std::uint32_t tud_cdc_n_write_available(std::uint8_t p) {
    return CFG_TUD_CDC_TX_BUFSIZE - ports.at(p).pending.size();
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

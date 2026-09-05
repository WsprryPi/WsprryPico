#include "usb/transport.hpp"

#include "tusb.h"
#include "usb/roles.h"

#include <algorithm>
#include <array>

namespace wsprrypico::usb {
namespace {
std::array<char, kConsoleCapacity> console_queue{};
std::size_t head = 0;
std::size_t size = 0;
std::array<bool, USB_CDC_COUNT> connected{};
bool wtp_reset = true;
bool console_reset = true;

void disconnect(std::uint8_t port) {
    connected[port] = false;
    tud_cdc_n_write_clear(port);
    tud_cdc_n_read_flush(port);
    if (port == USB_CDC_CONSOLE) {
        console_reset = true;
        head = 0;
        size = 0;
    } else {
        wtp_reset = true;
    }
}
} // namespace

void service() {
    for (std::uint8_t port = 0; port < USB_CDC_COUNT; ++port) {
        const bool now = tud_cdc_n_connected(port);
        if (!now) {
            if (connected[port]) {
                disconnect(port);
            } else {
                tud_cdc_n_read_flush(port);
            }
        } else if (!connected[port]) {
            connected[port] = true;
            if (port == USB_CDC_WTP) {
                wtp_reset = true;
            }
        }
    }
    std::array<std::uint8_t, kServiceBytes> ignored{};
    tud_cdc_n_read(USB_CDC_CONSOLE, ignored.data(), ignored.size());
    if (connected[USB_CDC_CONSOLE] && size != 0) {
        const auto count = std::min({size, console_queue.size() - head, kServiceBytes});
        const auto accepted = tud_cdc_n_write(USB_CDC_CONSOLE, console_queue.data() + head, count);
        head = (head + accepted) % console_queue.size();
        size -= accepted;
    }
    for (std::uint8_t port = 0; port < USB_CDC_COUNT; ++port) {
        if (connected[port]) {
            tud_cdc_n_write_flush(port);
        }
    }
}

bool console_connected() {
    return connected[USB_CDC_CONSOLE];
}
bool wtp_connected() {
    return connected[USB_CDC_WTP];
}
bool take_console_reset() {
    const bool result = console_reset;
    console_reset = false;
    return result;
}
bool take_wtp_reset() {
    const bool result = wtp_reset;
    wtp_reset = false;
    return result;
}
bool console_write(std::string_view text) {
    if (!console_connected() || text.size() > console_queue.size() - size) {
        return false;
    }
    for (char byte : text) {
        console_queue[(head + size) % console_queue.size()] = byte;
        ++size;
    }
    return true;
}
std::size_t wtp_transport_write(std::span<const std::uint8_t> bytes) {
    if (!wtp_connected()) {
        return 0;
    }
    const auto count = std::min(bytes.size(), kServiceBytes);
    return tud_cdc_n_write(USB_CDC_WTP, bytes.data(), count);
}
std::size_t wtp_transport_read(std::span<std::uint8_t> bytes) {
    if (!wtp_connected()) {
        return 0;
    }
    return tud_cdc_n_read(USB_CDC_WTP, bytes.data(), std::min(bytes.size(), kServiceBytes));
}
} // namespace wsprrypico::usb

// Callbacks execute within the same tud_task owner as service(). Clear on the
// falling edge, even if DTR rises again before the next main-loop iteration.
extern "C" void tud_cdc_line_state_cb(std::uint8_t port, bool dtr, bool rts) {
    (void)rts;
    if (port < USB_CDC_COUNT && !dtr) {
        wsprrypico::usb::disconnect(port);
    }
}
extern "C" void tud_umount_cb() {
    for (std::uint8_t port = 0; port < USB_CDC_COUNT; ++port) {
        wsprrypico::usb::disconnect(port);
    }
}

extern "C" void tud_mount_cb() {
    // A bus reset/reconfiguration can complete between main-loop polls.
    for (std::uint8_t port = 0; port < USB_CDC_COUNT; ++port) {
        wsprrypico::usb::disconnect(port);
    }
}

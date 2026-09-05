#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace wsprrypico::usb {

constexpr std::size_t kConsoleCapacity = 2048;
constexpr std::size_t kServiceBytes = 64;

// Single owner: main loop and TinyUSB callbacks dispatched by tud_task only.
// Never call from IRQ, another core, or timing-critical code.
void service();
bool console_connected();
bool wtp_connected();
// Consume a session-reset notification, including a close/open between polls.
bool take_wtp_reset();
bool take_console_reset();
// All-or-nothing enqueue; disconnected/full console drops the entire diagnostic.
bool console_write(std::string_view text);
// Non-blocking prefix acceptance. Caller retains/retries the unaccepted suffix.
// A disconnect aborts the stream; accepted bytes are not delivery acknowledgments.
std::size_t wtp_transport_write(std::span<const std::uint8_t> bytes);
std::size_t wtp_transport_read(std::span<std::uint8_t> bytes);

} // namespace wsprrypico::usb

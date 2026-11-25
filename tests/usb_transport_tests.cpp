#include "tusb.h"
#include "usb/console_reply.hpp"
#include "usb/reply_priority.hpp"
#include "usb/roles.h"
#include "usb/transport.hpp"
#include "runtime/memory_budget.hpp"

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
std::size_t console_allocations = 0, console_releases = 0, free_bytes = 0;
bool refuse_console_allocation = false;
void* console_allocate(std::size_t bytes) {
    if (refuse_console_allocation)
        return nullptr;
    ++console_allocations;
    return std::malloc(bytes);
}
void console_release(void* data) {
    if (data)
        ++console_releases;
    std::free(data);
}
} // namespace
#include "usb_transport_fixture.hpp"

int main() {
    using namespace wsprrypico::usb;
    reset();
    ReplyPriority priority;
    CHECK(!priority.defer_http(0, false));
    CHECK(priority.defer_http(1, true));
    CHECK(priority.defer_http(100'000, true));
    CHECK(priority.defer_http(500'000, true));
    CHECK(!priority.defer_http(500'001, true));
    CHECK(!priority.defer_http(900'000, false));
    CHECK(!priority.defer_http(900'001, true));
    CHECK(priority.defer_http(1'000'001, true));
    CHECK(!priority.defer_http(1'500'001, true));
    ReplyPriority wrapped;
    CHECK(wrapped.defer_http(UINT64_MAX - 50'000, true));
    CHECK(wrapped.defer_http(0, true));
    CHECK(wrapped.defer_http(100'000, true));
    CHECK(wrapped.defer_http(150'000, true));
    CHECK(!wrapped.defer_http(450'000, true));
    CHECK(wrapped.defer_http(1'000'000, true));
    CHECK(!console_output_pending());
    const std::array<std::uint8_t, 5> binary{0, 255, 10, 13, 128};
    CHECK(!console_write("offline"));
    CHECK(bench_transport_write(binary) == 0);
    open(USB_CDC_CONSOLE);
    open(USB_CDC_RESERVED);
    CHECK(take_bench_reset());
    CHECK(!take_bench_reset());
    // Merely connecting does not reserve 8 KiB. Failed optional diagnostics
    // preserve the safety reserve; a successful retry and disconnect release it.
    wsprrypico::execution::allocate_input = console_allocate;
    wsprrypico::execution::deallocate_input = console_release;
    wsprrypico::execution::available_memory = +[] { return free_bytes; };
    CHECK(console_write("") && console_allocations == 0);
    CHECK(console_allocations == 0 && !console_write("pressure"));
    CHECK(console_allocations == 0);
    free_bytes = 65536;
    refuse_console_allocation = true;
    CHECK(!console_write("allocation refused") && !console_output_pending());
    refuse_console_allocation = false;
    CHECK(console_write("retry") && console_allocations == 1);
    ports[USB_CDC_CONSOLE].connected = false;
    service();
    CHECK(console_releases == 1 && !console_output_pending());
    open(USB_CDC_CONSOLE);
    wsprrypico::execution::allocate_input = std::malloc;
    wsprrypico::execution::deallocate_input = std::free;
    wsprrypico::execution::available_memory = nullptr;
    // Startup-sized UTF-8 diagnostic survives short writes; Commands stays silent.
    const std::string banner = "WsprryPico\r\n" + std::string(600, 'x') + " UTF-8: π\r\n";
    ports[0].capacity = 7;
    CHECK(console_write(banner));
    CHECK(console_output_pending());
    for (unsigned i = 0; i < (kConsoleCapacity + 12) / 13 + 1; ++i)
        service();
    CHECK(std::string(ports[0].delivered.begin(), ports[0].delivered.end()) == banner);
    CHECK(ports[1].delivered.empty());
    CHECK(!console_output_pending());
    // Software queue empty, but TinyUSB still has a packet to drain.
    // The RF INFO snapshot crosses the former whole-reply 8 KiB limit when
    // launch/refill counters populate. Keep the real queue fixed and drain a
    // larger UTF-8 reply through short writes without blocking Commands.
    const std::string info = "{\"diagnostic\":\"" + std::string(9'000, 'x') + "π\"}\n";
    ConsoleReply reply;
    CHECK(reply.begin(info));
    CHECK(!reply.begin("must not replace a pending reply\n"));
    ports[0].capacity = 0;
    for (unsigned i = 0; i < 200; ++i) {
        reply.poll(console_write);
        service();
    }
    CHECK(reply.pending());
    ports[0].capacity = 7;
    for (unsigned i = 0; i < 2'000; ++i) {
        reply.poll(console_write);
        service();
    }
    CHECK(!reply.pending() && !console_output_pending());
    CHECK(std::string(ports[0].delivered.begin(), ports[0].delivered.end()) == banner + info);
    CHECK(ports[1].delivered.empty());
    CHECK(!reply.begin(std::string(65'537, 'x')));
    CHECK(!reply.pending());
    CHECK(reply.begin(info));
    reply.reset();
    CHECK(!reply.pending() && reply.begin("fresh session\n"));
    reply.reset();
    // Fragmented heaps may admit 4 KiB pages while rejecting a 16 KiB growth.
    // A paged response preserves exact bytes across page and USB boundaries.
    std::size_t page_calls = 0, live_pages = 0, fail_at = 0;
    static std::size_t *calls, *live, *failure;
    calls = &page_calls;
    live = &live_pages;
    failure = &fail_at;
    wsprrypico::execution::allocate_input = [](std::size_t bytes) -> void* {
        CHECK(bytes <= 4096);
        ++*calls;
        if (*calls == *failure)
            return nullptr;
        ++*live;
        return std::malloc(bytes);
    };
    wsprrypico::execution::deallocate_input = [](void* bytes) {
        if (bytes) {
            --*live;
            std::free(bytes);
        }
    };
    auto paged = ConsoleResponse::paged();
    paged += info.front();
    paged += std::string_view(info).substr(1);
    CHECK(paged.valid() && live_pages == 3);
    CHECK(reply.begin(std::move(paged)));
    reply.poll([](std::string_view) { return false; });
    CHECK(reply.pending() && live_pages == 3);
    std::string delivered;
    while (reply.pending())
        reply.poll([&](std::string_view bytes) {
            delivered += bytes;
            return true;
        });
    CHECK(delivered == info && live_pages == 0);
    for (const auto failed_page : {1u, 2u, 3u}) {
        page_calls = 0;
        fail_at = failed_page;
        auto failed = ConsoleResponse::paged();
        failed += info;
        CHECK(!failed.valid());
        const bool admitted = reply.begin(std::move(failed));
        CHECK(!admitted && !reply.pending() && live_pages == 0);
        CHECK(reply.begin(ConsoleResponse::constant("{\"ok\":false}\n")));
        reply.reset();
        CHECK(live_pages == 0);
    }
    fail_at = 0;
    auto excessive = ConsoleResponse::paged();
    excessive += std::string(65'537, 'x');
    CHECK(!excessive.valid() && live_pages == 0);
    auto complete = ConsoleResponse::paged();
    complete += std::string(65'536, 'x');
    CHECK(complete.valid() && live_pages == 16);
    CHECK(reply.begin(std::move(complete)));
    reply.reset();
    CHECK(live_pages == 0);
    wsprrypico::execution::allocate_input = std::malloc;
    wsprrypico::execution::deallocate_input = std::free;
    ports[0].delivered.assign(banner.begin(), banner.end());
    ports[0].pending.push_back('x');
    CHECK(console_output_pending());
    ports[0].pending.clear();
    ports[1].capacity = 2;
    std::size_t sent = 0;
    while (sent < binary.size()) {
        sent += bench_transport_write(std::span(binary).subspan(sent));
        if (sent < binary.size()) {
            CHECK(bench_transport_write(binary) == 0);
        }
        service();
    }
    CHECK(ports[1].delivered == std::vector<std::uint8_t>(binary.begin(), binary.end()));
    // Slow console and saturated Commands independently return without blocking.
    ports[0].capacity = 0;
    ports[1].capacity = 0;
    CHECK(console_write(std::string(kConsoleCapacity, 'a')));
    CHECK(!console_write("π"));
    CHECK(bench_transport_write(binary) == 0);
    for (unsigned i = 0; i < 10; ++i)
        service();
    // A stalled console does not stall binary Commands output, and a stalled Commands channel
    // does not stall a wrapped, full console ring once Console resumes reading.
    ports[1].capacity = 64;
    CHECK(bench_transport_write(binary) == binary.size());
    service();
    CHECK(ports[1].delivered.size() == 2 * binary.size());
    ports[1].capacity = 0;
    ports[0].capacity = 13;
    for (unsigned i = 0; i < (kConsoleCapacity + 12) / 13 + 1; ++i)
        service();
    CHECK(std::string(ports[0].delivered.begin(), ports[0].delivered.end()) ==
          banner + std::string(kConsoleCapacity, 'a'));
    ports[0].delivered.assign(banner.begin(), banner.end());
    ports[1].delivered.assign(binary.begin(), binary.end());
    ports[0].capacity = 0;
    CHECK(console_write("discard on reconnect"));
    // Console and diagnostic Commands receive their own bytes.
    const std::array<std::uint8_t, 7> command{'S', 'T', 'A', 'T', 'U', 'S', '\n'};
    ports[0].rx = std::deque<std::uint8_t>(200, 'c');
    ports[1].rx = {command.begin(), command.end()};
    service();
    CHECK(ports[0].rx.size() == 200);
    std::array<std::uint8_t, 256> input{};
    CHECK(console_transport_read(input) == kServiceBytes);
    CHECK(ports[0].rx.size() == 200 - kServiceBytes);
    auto count = bench_transport_read(input);
    CHECK(count == command.size());
    CHECK(std::equal(command.begin(), command.end(), input.begin()));
    ports[1].rx = std::deque<std::uint8_t>(200, 'w');
    CHECK(bench_transport_read(input) == kServiceBytes);
    // Falling/rising DTR between polls must still clear stale data/reset parser.
    ports[1].capacity = 64;
    CHECK(bench_transport_write(binary) == binary.size());
    tud_cdc_line_state_cb(1, false, false);
    tud_cdc_line_state_cb(1, true, false);
    service();
    CHECK(take_bench_reset());
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
    // Four independent streams, including stalled Logging and its own DTR reset.
    open(USB_CDC_MANAGEMENT);
    open(USB_CDC_LOGGING);
    (void)take_bench_reset();
    (void)take_console_reset();
    (void)take_management_reset();
    (void)take_logging_reset();
    ports[USB_CDC_LOGGING].capacity = 0;
    CHECK(logging_write(std::string(kLoggingCapacity, 'l')));
    CHECK(!logging_write("overflow"));
    ports[USB_CDC_RESERVED].capacity = 64;
    CHECK(bench_transport_write(binary) == binary.size());
    CHECK(management_transport_write(binary) == binary.size());
    CHECK(console_write("Console while Logging is stalled\n"));
    service();
    CHECK(ports[USB_CDC_MANAGEMENT].delivered ==
          std::vector<std::uint8_t>(binary.begin(), binary.end()));
    CHECK(ports[USB_CDC_LOGGING].delivered.empty());
    ports[USB_CDC_LOGGING].rx = {'L'};
    ports[USB_CDC_CONSOLE].rx = {'C'};
    CHECK(logging_transport_read(input) == 1 && input[0] == 'L');
    CHECK(console_transport_read(input) == 1 && input[0] == 'C');
    tud_cdc_line_state_cb(USB_CDC_LOGGING, false, false);
    CHECK(take_logging_reset());
    CHECK(!take_bench_reset() && !take_console_reset() && !take_management_reset());
    service();
    CHECK(take_logging_reset() && !take_bench_reset());
    CHECK(logging_write("short-write record\n"));
    ports[USB_CDC_LOGGING].capacity = 3;
    for (unsigned i = 0; i < 20; ++i)
        service();
    CHECK(std::string(ports[USB_CDC_LOGGING].delivered.begin(),
                      ports[USB_CDC_LOGGING].delivered.end()) == "short-write record\n");
    tud_cdc_line_state_cb(USB_CDC_CONSOLE, false, false);
    CHECK(take_console_reset() && !take_logging_reset() && !take_bench_reset());
    service();
    CHECK(logging_write("Console closed\n"));
    for (unsigned i = 0; i < 20; ++i)
        service();
    CHECK(logging_connected() && management_connected() && bench_connected());
    // USB reconfiguration resets all sessions even if polls miss disconnect.
    ports[1].rx.push_back(99);
    tud_mount_cb();
    CHECK(take_bench_reset());
    CHECK(take_console_reset());
    CHECK(ports[1].rx.empty());
    CHECK(take_logging_reset() && take_management_reset());
    reset();
    CHECK(!bench_connected());
    CHECK(bench_transport_read(input) == 0);
    std::cout << "USB transport behavior passed\n";
}

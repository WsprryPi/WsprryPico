// SPDX-License-Identifier: MIT
#include "logging/logger.hpp"
#include "logging/usb_session.hpp"
#include "network/local_usb_api.hpp"
#include "network_support.hpp"
#include "wtp/json.hpp"

#include <cassert>
#include <cstdlib>
#include <deque>
#include <limits>
#include <new>
#include <vector>

static bool prohibit_allocation = false;
void* operator new(std::size_t size) {
    if (prohibit_allocation)
        throw std::bad_alloc();
    if (void* result = std::malloc(size ? size : 1))
        return result;
    throw std::bad_alloc();
}
void operator delete(void* pointer) noexcept {
    std::free(pointer);
}
void operator delete(void* pointer, std::size_t) noexcept {
    std::free(pointer);
}
using namespace wsprrypico;
int main() {
    logging::Logger logger(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
    logger.event(6, "BOOT", "disabled", 0);
    assert(logger.queued() == 0);
    logger.settings({true, 6});
    logger.connected(true);
    assert(!logger.start(std::string(32, 'c'), std::string(32, 'b')));
    assert(logger.start(std::string(32, 'a'), std::string(32, 'b')));
    logger.event(6, "TEST", "line\n\r\x1b<script>", 10);
    const std::string first(logger.front());
    assert(first.starts_with("@SYSLOG "));
    const auto separator = first.find(' ', 8);
    assert(std::stoul(first.substr(8, separator - 8)) == first.size() - separator - 2);
    assert(first.find("<190>1 - pico.local WsprryPico - TEST - ") != std::string::npos);
    assert(first.find("line___<script>") != std::string::npos);
    assert(first.find("\"utc_ns\":null") != std::string::npos);
    assert(first.find('\n') == first.size() - 1);
    assert(logger.front() == first); // zero-write retry retains whole record
    logger.consume();
    logger.event(7, "DEBUG", "filtered", 20);
    assert(logger.queued() == 0);
    for (unsigned i = 0; i < 20; ++i)
        logger.event(3, "FAULT", "bounded", 30);
    assert(logger.queued() == 7 && logger.dropped() == 13);
    for (unsigned i = 1; i <= 20; ++i)
        logger.event(6, "STATE", "bounded", i * 1'000'000'000ULL);
    assert(logger.queued() == logging::Logger::capacity);
    const auto dropped = logger.dropped();
    logger.connected(false);
    assert(logger.queued() == 0 && !logger.streaming());
    assert(logger.dropped() == dropped + logging::Logger::capacity);
    logger.connected(true);
    assert(logger.front().empty());
    assert(logger.start(std::string(32, 'a'), std::string(32, 'b')));
    logger.event(5, "UTC", std::string(400, 'x'), 30'000'000'000ULL, 1'700'000'000'000'000'000ULL);
    const auto timed = logger.front();
    assert(timed.find("2023-11-14T22:13:20Z") != std::string::npos);
    assert(timed.size() < 1024);
    logger.consume();
    prohibit_allocation = true;
    logger.event(3, "OOM", "Formatting uses fixed storage", 31'000'000'000ULL);
    assert(!logger.front().empty());
    prohibit_allocation = false;
    logger.stop();
    assert(logger.front().empty());

    // Exercise the production dedicated carrier independently of Console.
    logging::Logger wire_logger(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
    wire_logger.settings({true, 7});
    logging::UsbSession session(wire_logger, std::string(32, 'a'), std::string(32, 'b'));
    std::deque<std::uint8_t> rx;
    std::vector<std::string> tx;
    bool accepting = true;
    const auto wire_read = [&](std::span<std::uint8_t> bytes) {
        const auto count = std::min(bytes.size(), rx.size());
        for (std::size_t i = 0; i < count; ++i) {
            bytes[i] = rx.front();
            rx.pop_front();
        }
        return count;
    };
    const auto wire_write = [&](std::string_view text) {
        if (!accepting)
            return false;
        tx.emplace_back(text);
        return true;
    };
    auto send = [&](std::string text) {
        rx.insert(rx.end(), text.begin(), text.end());
        for (unsigned i = 0; i < 30; ++i)
            session.poll(true, false, wire_read, wire_write, 1);
    };
    send("SYSLOG STATUS\n");
    assert(tx.size() == 1 && tx.back().find("\"schema\":\"usb-logging/1\"") != std::string::npos);
    send("SYSLOG START " + std::string(32, 'c') + " " + std::string(32, 'b') + "\n");
    assert(!wire_logger.streaming() &&
           tx.back().find("logging_command_refused") != std::string::npos);
    accepting = false;
    send("SYSLOG START " + std::string(32, 'a') + " " + std::string(32, 'b') + "\n");
    assert(wire_logger.streaming() && tx.size() == 2);
    accepting = true;
    for (unsigned i = 0; i < 10; ++i)
        session.poll(true, false, wire_read, wire_write, 1);
    assert(tx.size() == 4 && tx[2].find("\"streaming\":true") != std::string::npos);
    assert(tx[3].starts_with("@SYSLOG "));
    send("INFO\nSYSLOG SAVE {}\nSYS\rLOG STATUS\nSYSLOG STATUS\r\n" + std::string(200, 'x') +
         "\nSYSLOG STATUS\n");
    assert(tx.back().find("\"active\":") != std::string::npos);
    assert(tx.size() == 10); // five refused commands, then successful resynchronization
    send("SYSLOG STOP\n");
    assert(!wire_logger.streaming() && tx.back().find("\"streaming\":false") != std::string::npos);
    send("SYSLOG START " + std::string(32, 'a') + " " + std::string(32, 'b') + "\n");
    assert(wire_logger.streaming());
    session.poll(true, true, wire_read, wire_write, 2);
    assert(!wire_logger.streaming());
    send("SYSLOG STATUS\n");
    assert(tx.back().find("\"streaming\":false") != std::string::npos);

    network_test::Fixture fixture;
    const auto config = *standalone::parse_config(network_test::config);
    assert(fixture.store.save(config));
    logging::Logger resource(std::string(32, 'a'), fixture.service.status().boot_id, "pico.local");
    fixture.api.logging_service(resource);
    network::LocalUsbApi api(fixture.api);
    network::HttpRequest request;
    request.method = "GET";
    request.path = "/api/control/v1/logging";
    auto read = api.handle(network_test::control_request(request));
    assert(read.status == 200 && !read.etag.empty());
    const auto body =
        "{\"schema\":\"logging\",\"target\":{\"scope\":\"member\",\"device_id\":" +
        wtp::json::quote(std::string(32, 'a')) +
        ",\"boot_id\":" + wtp::json::quote(fixture.service.status().boot_id) +
        "},\"logging\":{\"enabled\":true,\"maximum_severity\":4}}";
    request.method = "PUT";
    request.body = body;
    assert(api.handle(network_test::control_request(request)).status == 428);
    request.headers["if-match"] = "stale";
    assert(api.handle(network_test::control_request(request)).status == 412);
    request.headers["if-match"] = read.etag;
    assert(api.handle(network_test::control_request(request)).status == 200);
    assert(resource.settings() == (logging::Settings{true, 4}));
    standalone::Store reloaded(fixture.flash);
    assert(reloaded.load() && reloaded.logging_settings() == resource.settings());
    assert(standalone::serialize_config(*reloaded.config()) ==
           standalone::serialize_config(config));
    assert(reloaded.save(config));
    standalone::Store again(fixture.flash);
    assert(again.load() && again.logging_settings().enabled);
    assert(again.save_logging({false, 6}));
    standalone::Store defaults(fixture.flash);
    assert(defaults.load() && !defaults.logging_settings().enabled);
    request.method = "GET";
    read = api.handle(network_test::control_request(request));
    request.method = "PUT";
    request.headers["if-match"] = read.etag;
    fixture.flash.fail = true;
    assert(api.handle(network_test::control_request(request)).status == 503);
}

// SPDX-License-Identifier: MIT
#include "logging/udp_sender.hpp"
#include "logging/usb_control_state.hpp"

#include <cassert>
#include <string>
#include <vector>

using namespace wsprrypico;

int main() {
    const std::string device(32, 'a'), boot(32, 'b');
    for (unsigned maximum : {4U, 5U, 6U, 7U}) {
        logging::Logger logger(device, boot, "pico.local");
        logging::UdpSender udp(device, boot, "pico.local");
        logging::UdpSettings settings;
        settings.enabled = true;
        settings.maximum_severity = maximum;
        settings.destination_ipv4.assign("192.0.2.10");
        assert(udp.configure(settings));
        udp.network(1, true, true);
        logger.udp_sink(udp);
        logger.settings({true, maximum});
        logger.connected(true);
        assert(logger.start(device, boot));
        logging::UsbControlStateLogger observer;
        struct Observation {
            bool wtp, management;
            std::uint64_t monotonic;
            std::vector<std::string> messages;
        };
        // A single short-lived WTP open can expose the host's initial DTR,
        // explicit low interval, deliberate assertion and eventual close.
        // Simultaneous changes must preserve both port identities separately.
        const Observation observations[] = {
            {false, false, 0, {}},
            {true, false, 551'000'000, {"USB WTP port opened"}},
            {false, false, 555'000'000, {"USB WTP port closed"}},
            {true, false, 654'000'000, {"USB WTP port opened"}},
            {false, false, 1'325'000'000, {"USB WTP port closed"}},
            {false, true, 2'000'000'000, {"USB Management port opened"}},
            {true, true, 3'000'000'000, {"USB WTP port opened"}},
            {false, true, 4'000'000'000, {"USB WTP port closed"}},
            {true, false, 5'000'000'000, {"USB WTP port opened", "USB Management port closed"}},
            {false, false, 6'000'000'000, {"USB WTP port closed"}},
            {true, true, 7'000'000'000, {"USB WTP port opened", "USB Management port opened"}},
            {false, false, 8'000'000'000, {"USB WTP port closed", "USB Management port closed"}}};
        for (const auto& sample : observations) {
            const auto utc = sample.monotonic < 1'000'000'000
                                 ? 0
                                 : 1'700'000'000'000'000'000ULL + sample.monotonic;
            observer.observe(logger, sample.wtp, sample.management, sample.monotonic, utc);
            // Polling an unchanged port, including activity on independent
            // Console/Logging functions, must not generate another event.
            observer.observe(logger, sample.wtp, sample.management, sample.monotonic + 1, utc);
            const auto count = maximum == 7 ? sample.messages.size() : 0;
            assert(logger.queued() == count && udp.queued() == count);
            assert(logger.dropped() == 0 && udp.counters().redacted_rejected == 0);
            for (std::size_t index = 0; index < count; ++index) {
                const std::string serial(logger.front());
                assert(serial.find("<191>1 ") != std::string::npos);
                assert(serial.find("\"event\":\"USB_STATE\"") != std::string::npos);
                assert(serial.find("\"severity\":7") != std::string::npos);
                assert(serial.find("\"message\":\"" + sample.messages[index] + "\"") !=
                       std::string::npos);
                assert(serial.find("\"monotonic_ns\":\"" + std::to_string(sample.monotonic) +
                                   "\"") != std::string::npos);
                assert((serial.find("\"utc_ns\":null") != std::string::npos) == (utc == 0));
                logger.consume();
            }
            std::size_t submitted = 0;
            // The production sink submits at most one datagram per poll.
            for (std::size_t attempt = 0; attempt <= count; ++attempt)
                udp.poll(sample.monotonic, [&](std::string_view bytes) {
                    wsprry::logging::UdpEvent event;
                    assert(wsprry::logging::decode_udp(bytes, event));
                    assert(submitted < count);
                    assert(event.code.view() == "USB_STATE" && event.severity == 7);
                    assert(event.message.view() == sample.messages[submitted]);
                    assert(event.monotonic_ns == sample.monotonic);
                    assert(event.utc_ns.has_value() == (utc != 0));
                    ++submitted;
                    return true;
                });
            assert(submitted == count && udp.queued() == 0);
        }
        // Filtered control churn must not consume the INFO/WARNING admission
        // budget or replay when the operator subsequently enables DEBUG.
        for (unsigned i = 0; i < 40; ++i)
            observer.observe(logger, i % 2 == 0, false, 9'000'000'000ULL + i);
        if (maximum < 7) {
            assert(logger.queued() == 0 && udp.queued() == 0 && logger.dropped() == 0);
            logger.settings({true, 7});
            observer.observe(logger, false, false, 9'000'000'100ULL);
            assert(logger.queued() == 0);
            logger.event(4, "CLOCK_STATE", "UTC unavailable", 9'000'000'101ULL);
            assert(logger.queued() == 1);
            assert(logger.front().find("UTC unavailable") != std::string_view::npos);
        }
    }
    // Retain historical forwarding, while admitting only the four new fixed
    // messages. Port labels must never become an arbitrary-text export path.
    assert(wsprry::logging::export_safe_pico("USB_STATE", "USB control connection changed"));
    assert(!wsprry::logging::export_safe_pico("USB_STATE", "USB WTP port opened password=secret"));
    assert(!wsprry::logging::export_safe_pico("USB_STATE", "USB Console port opened"));
    assert(!wsprry::logging::export_safe_pico("UNKNOWN", "USB WTP port opened"));
}

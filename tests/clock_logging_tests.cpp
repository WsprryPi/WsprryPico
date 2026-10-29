// SPDX-License-Identifier: MIT
#include "logging/clock_state.hpp"
#include "logging/udp_sender.hpp"

#include <cassert>
#include <string>

using namespace wsprrypico;
using Clock = wtp::ClockState;

int main() {
    // Exercise the exact observer called by firmware through both production
    // serializers, with the same event sequence at each operator threshold.
    for (unsigned maximum : {4U, 5U, 6U, 7U}) {
        logging::Logger logger(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
        logging::UdpSender udp(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
        logging::UdpSettings settings;
        settings.enabled = true;
        settings.maximum_severity = maximum;
        settings.destination_ipv4.assign("192.0.2.10");
        assert(udp.configure(settings));
        udp.network(1, true, true);
        logger.udp_sink(udp);
        logger.settings({true, maximum});
        logger.connected(true);
        assert(logger.start(std::string(32, 'a'), std::string(32, 'b')));
        logging::ClockStateLogger observer;
        wtp::ClockSnapshot clock;
        observer.observe(logger, clock, 0);
        observer.observe(logger, clock, 1);
        assert(logger.queued() == 0 && udp.queued() == 0);
        struct Transition {
            Clock state;
            unsigned severity;
            const char* message;
        };
        const Transition transitions[] = {{Clock::Synchronized, 6, "UTC synchronized"},
                                          {Clock::Holdover, 7, "UTC holdover"},
                                          {Clock::Synchronized, 7, "UTC synchronized"},
                                          {Clock::Holdover, 7, "UTC holdover"},
                                          {Clock::Unsynchronized, 4, "UTC unavailable"},
                                          {Clock::Synchronized, 6, "UTC synchronized"},
                                          {Clock::Unsynchronized, 4, "UTC unavailable"},
                                          {Clock::Holdover, 6, "UTC holdover"},
                                          {Clock::Synchronized, 7, "UTC synchronized"}};
        std::uint64_t mono = 0;
        for (const auto& expected : transitions) {
            mono += 2'000'000'000ULL;
            clock.state = expected.state;
            clock.utc_now_ns =
                expected.state == Clock::Unsynchronized ? 0 : 1'700'000'000'000'000'000ULL + mono;
            observer.observe(logger, clock, mono);
            observer.observe(logger, clock, mono + 1); // polling is quiet
            const bool admitted = expected.severity <= maximum;
            assert(logger.queued() == unsigned(admitted) && udp.queued() == unsigned(admitted));
            if (!admitted)
                continue;
            const std::string wire(logger.front());
            assert(wire.find("\"event\":\"CLOCK_STATE\"") != std::string::npos);
            assert(wire.find("\"severity\":" + std::to_string(expected.severity)) !=
                   std::string::npos);
            assert(wire.find(expected.message) != std::string::npos);
            assert(wire.find("<" + std::to_string(184 + expected.severity) + ">1 ") !=
                   std::string::npos);
            assert((wire.find("\"utc_ns\":null") != std::string::npos) ==
                   (expected.state == Clock::Unsynchronized));
            logger.consume();
            unsigned sent = 0;
            udp.poll(mono, [&](std::string_view bytes) {
                wsprry::logging::UdpEvent event;
                assert(wsprry::logging::decode_udp(bytes, event));
                assert(event.code.view() == "CLOCK_STATE" &&
                       event.message.view() == expected.message);
                assert(event.severity == expected.severity);
                assert(event.utc_ns.has_value() == (expected.state != Clock::Unsynchronized));
                ++sent;
                return true;
            });
            assert(sent == 1);
        }
    }
    // Retained producer templates remain allowed; new state text is still an
    // exact fixed-template export, never an arbitrary diagnostic body.
    for (const auto text : {"UTC available", "UTC unavailable", "UTC synchronized", "UTC holdover"})
        assert(wsprry::logging::export_safe_pico("CLOCK_STATE", text));
    assert(!wsprry::logging::export_safe_pico("CLOCK_STATE", "UTC synchronized password=secret"));
}

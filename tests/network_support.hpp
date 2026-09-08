#pragma once
#include "network/api.hpp"
#include "standalone/dry_run_engine.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#define REQUIRE(x)                                                                                 \
    do {                                                                                           \
        if (!(x)) {                                                                                \
            std::cerr << __LINE__ << ": " #x "\n";                                                 \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
namespace network_test {
using namespace wsprrypico;
struct Flash : standalone::Flash {
    std::array<std::uint8_t, 16384> bytes{};
    bool fail = false;
    Flash() {
        bytes.fill(255);
    }
    bool read(std::size_t offset, std::span<std::uint8_t> data) override {
        if (offset + data.size() > bytes.size())
            return false;
        std::copy_n(bytes.begin() + offset, data.size(), data.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        if (fail || offset + 4096 > bytes.size())
            return false;
        std::fill_n(bytes.begin() + offset, 4096, 255);
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> data) override {
        if (fail || offset + data.size() > bytes.size())
            return false;
        std::copy(data.begin(), data.end(), bytes.begin() + offset);
        return true;
    }
};
struct Clock : wtp::Clock {
    std::uint64_t now = 1'000'000'000, utc = 1'800'000'000'000'000'000ULL;
    wtp::ClockSnapshot snapshot() const override {
        return {wtp::ClockState::Synchronized, utc + now, now, 1000, 0, wtp::LeapState::Normal, {}};
    }
};
struct Identity : wtp::IdentitySource {
    unsigned boot = 0;
    explicit Identity(unsigned initial = 0) : boot(initial) {}
    std::string new_boot_id() override {
        return std::string(31, '0') + std::to_string(++boot);
    }
};
struct Network : network::NetworkControl {
    bool enabled = true;
    std::optional<bool> pending;
    unsigned applied = 0;
    bool request_enabled(bool value) override {
        pending = value;
        return true;
    }
    void finish_request(bool idle) override {
        if (pending && idle) {
            enabled = *pending;
            ++applied;
        }
        pending.reset();
    }
    bool set_enabled(bool value) override {
        enabled = value;
        return true;
    }
    std::string status() const override {
        return std::string("{\"enabled\":") + (enabled ? "true" : "false") +
               ",\"test_pending\":" + (pending ? "true" : "false") +
               ",\"test_applied\":" + std::to_string(applied) +
               ",\"link_status\":3,\"ipv4\":\"127.0.0.1\"}";
    }
};
struct Fixture {
    Flash flash;
    standalone::Store store{flash};
    Clock clock;
    standalone::DryRunEngine engine;
    Identity identities;
    static wtp::ServiceConfig physical_policy() {
        wtp::ServiceConfig config;
        config.capability_engine = "pio-dma-simulated-worker";
        return config;
    }
    wtp::JobService service{clock, engine, identities, physical_policy()};
    standalone::Scheduler scheduler{store, service};
    Network network;
    network::BrowserApi api;
    Fixture(unsigned boot = 0, std::string device = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        : identities(boot), api(service, store, scheduler, network, device, "test-firmware") {
        REQUIRE(store.load());
    }
};
inline std::string config =
    R"({"version":1,"enabled":false,"station":{"callsign":"AA0NT","locator":"EM18","power_dbm":37},"wifi":{"ssid":"test-network","password":"test-password","ntp_ipv4":"192.0.2.1"},"schedules":[{"period_s":120,"phase_s":0}]})";
} // namespace network_test

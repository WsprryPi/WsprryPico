#pragma once
#include "pico/time.h"
#include "provisioning/consumer_claim_commit.hpp"
#include "standalone/pico/adapters.hpp"
#include "time/controller_time.hpp"
namespace wsprrypico::provisioning {
class PicoConsumerClaimPlatform final : public ConsumerClaimCommitPlatform {
  public:
    explicit PicoConsumerClaimPlatform(standalone::PicoNetwork& n) : network(n) {}
    standalone::PicoNetwork& network;
    bool safe = true;
    unsigned trial_starts = 0;
    void begin_station_trial() {
        ++trial_starts;
    }
    bool safe_to_commit() override {
        return safe;
    }
    std::uint64_t monotonic_now_ms() override {
        return time_us_64() / 1000;
    }
    bool station_ready(std::string_view ssid) override {
        return network.linked && network.ssid == ssid;
    }
    std::optional<std::uint64_t> trusted_utc_now() override {
        return {};
    }
    bool seed_browser_utc(std::uint64_t, std::uint64_t) {
        return false;
    }
    std::string_view local_hostname() override {
        return network.hostname;
    }
    // Point validity itself is exercised by the existing owner crypto suite.
    bool valid_owner_point(std::string_view point) override {
        return point.size() == 87;
    }
    bool generate_tls(std::string_view, std::string_view, std::uint64_t, ConsumerTls&) override {
        return false;
    }
    bool valid_tls(const ConsumerTls&, std::string_view, std::uint64_t) override {
        return false;
    }
};
} // namespace wsprrypico::provisioning

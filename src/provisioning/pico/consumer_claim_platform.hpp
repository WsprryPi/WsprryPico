#pragma once

#include "provisioning/access.hpp"
#include "provisioning/consumer_claim_commit.hpp"
#include "standalone/pico/adapters.hpp"
#include "time/controller_time.hpp"
#include "wtp/job_service.hpp"

#include <string>

namespace wsprrypico::provisioning {
// Fresh target observations for the single irreversible consumer journal
// write. Station trial ownership and response delivery remain with the AP
// server; this adapter never writes a journal by itself.
class PicoConsumerClaimPlatform final : public ConsumerClaimCommitPlatform {
  public:
    PicoConsumerClaimPlatform(const AccessStore& access, standalone::PicoNetwork& network,
                              wtp::JobService& service, time::ControllerTimeArbiter& arbiter,
                              std::string hostname)
        : access_(access), network_(network), service_(service), arbiter_(arbiter),
          hostname_(std::move(hostname)) {}
    void begin_station_trial();
    bool safe_to_commit() override;
    std::uint64_t monotonic_now_ms() override;
    bool station_ready(std::string_view ssid) override;
    std::optional<std::uint64_t> trusted_utc_now() override;
    bool seed_browser_utc(std::uint64_t utc_ms, std::uint64_t challenge_age_ns) {
        return arbiter_.seed_browser_hint(utc_ms, challenge_age_ns);
    }
    std::string_view local_hostname() override {
        return hostname_;
    }
    bool valid_owner_point(std::string_view point_b64url) override;
    bool generate_tls(std::string_view device_id, std::string_view hostname, std::uint64_t utc_now,
                      ConsumerTls& out) override;
    bool valid_tls(const ConsumerTls& tls, std::string_view device_id,
                   std::uint64_t utc_now) override;

  private:
    const AccessStore& access_;
    standalone::PicoNetwork& network_;
    wtp::JobService& service_;
    time::ControllerTimeArbiter& arbiter_;
    std::string hostname_;
};
} // namespace wsprrypico::provisioning

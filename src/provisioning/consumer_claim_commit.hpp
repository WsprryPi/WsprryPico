#pragma once

#include "provisioning/consumer_claim.hpp"
#include "provisioning/consumer_profile.hpp"
#include "provisioning/runtime.hpp"
#include "provisioning/storage.hpp"
#include "standalone/config.hpp"

#include <cstdint>
#include <optional>
#include <string_view>

namespace wsprrypico::provisioning {

struct ConsumerClaimValues {
    std::string_view request_id, ssid, password, callsign, locator;
    unsigned power_dbm = 0;
    std::string_view time_server = standalone::default_time_server;
};

// The Pico adapter supplies fresh observations, not values cached at claim
// start. safe_to_commit includes access-journal, output and sampler safety;
// station_ready includes association and DHCP for the submitted SSID; UTC is
// trusted and bounded by the platform clock policy.
class ConsumerClaimCommitPlatform {
  public:
    virtual ~ConsumerClaimCommitPlatform() = default;
    virtual bool safe_to_commit() = 0;
    virtual std::uint64_t monotonic_now_ms() = 0;
    virtual bool station_ready(std::string_view ssid) = 0;
    virtual std::optional<std::uint64_t> trusted_utc_now() = 0;
    virtual std::string_view local_hostname() = 0;
    virtual bool valid_owner_point(std::string_view point_b64url) = 0;
    virtual bool generate_tls(std::string_view device_id, std::string_view hostname,
                              std::uint64_t utc_now, ConsumerTls& out) = 0;
    virtual bool valid_tls(const ConsumerTls& tls, std::string_view device_id,
                           std::uint64_t utc_now) = 0;
};

enum class ConsumerCommitState { Rejected, Reconcile, Committed };
struct ConsumerCommitResult {
    ConsumerCommitState state = ConsumerCommitState::Rejected;
    std::uint64_t generation = 0;
    std::string request_sha256;
};

// One irreversible boundary: no owner, station setting or TLS identity is
// written before every gate passes. Reconcile means a journal write was
// attempted but the caller must read back the request digest after reboot.
ConsumerCommitResult commit_consumer_claim(ProfileStore& store, ConsumerClaimSlot& slot,
                                           const ConsumerClaimBinding& binding,
                                           const ConsumerClaimValues& values,
                                           ConsumerClaimCommitPlatform& platform,
                                           RuntimeSource runtime_source, std::uint64_t now_ms);
} // namespace wsprrypico::provisioning

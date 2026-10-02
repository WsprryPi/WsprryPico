#pragma once

#include "provisioning/storage.hpp"
#include "standalone/config.hpp"

#include <optional>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
struct NetworkProfile {
    std::string device_id;
    std::string ssid;
    std::string password;
    std::string time_server = standalone::default_time_server;
    std::string request_sha256 = {};
    bool operator==(const NetworkProfile&) const = default;
};

enum class SetupCommitResult { Committed, NotCommitted, Reconcile };
// Verify durable selection after any write failure before allowing rollback.
SetupCommitResult commit_setup_profile(ProfileStore& store, ProfileSource source,
                                       std::string_view payload);
std::string setup_request_digest(const ProfileStore& store, std::string_view device_id);

bool valid_network_profile(const NetworkProfile& profile);
std::optional<NetworkProfile> parse_network_profile(std::string_view text);
std::string serialize_network_profile(const NetworkProfile& profile);
void scrub(NetworkProfile& profile);
} // namespace wsprrypico::provisioning

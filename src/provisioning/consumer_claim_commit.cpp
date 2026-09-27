#include "provisioning/consumer_claim_commit.hpp"

#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "provisioning/network_profile.hpp"
#include "standalone/config.hpp"

#include <array>
#include <limits>
#include <string>

namespace wsprrypico::provisioning {
namespace {
void erase(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
struct Proposal {
    ConsumerProfile value;
    std::string payload;
    ~Proposal() {
        scrub(value);
        erase(payload);
    }
};
bool current_source(const ProfileStore& store, const ConsumerClaimBinding& binding) {
    if (!store.healthy() || store.source() != binding.source ||
        store.sequence() != binding.generation ||
        binding.generation == std::numeric_limits<std::uint64_t>::max())
        return false;
    switch (binding.source) {
    case ProfileSource::LegacyBootstrap:
        return binding.generation == 0 && store.data().empty();
    case ProfileSource::Unprovisioned:
        return binding.generation > 0 && store.data().empty();
    case ProfileSource::NetworkOnly: {
        if (!binding.generation)
            return false;
        auto previous = parse_network_profile(store.data());
        const bool matches = previous && previous->device_id == binding.device_id;
        if (previous)
            scrub(*previous);
        return matches;
    }
    default:
        return false;
    }
}
} // namespace

ConsumerCommitResult commit_consumer_claim(ProfileStore& store, ConsumerClaimSlot& slot,
                                           const ConsumerClaimBinding& binding,
                                           const ConsumerClaimValues& values,
                                           ConsumerClaimCommitPlatform& platform,
                                           RuntimeSource runtime_source, std::uint64_t now_ms) {
    if ((binding.source == ProfileSource::NetworkOnly &&
         runtime_source != RuntimeSource::NetworkOnly) ||
        (binding.source != ProfileSource::NetworkOnly &&
         runtime_source != RuntimeSource::Unprovisioned))
        return {};
    const auto fresh_ms = platform.monotonic_now_ms();
    if (fresh_ms < now_ms)
        return {};
    slot.expire(fresh_ms);
    const auto* active = slot.binding();
    std::array<std::uint8_t, 16> request{};
    if (slot.state() != ConsumerClaimState::Trial || !active || *active != binding ||
        !slot.trial_request_matches(values.request_id) ||
        !network::bootstrap_unhex(values.request_id, request) ||
        !network::valid_device_id(binding.device_id) || !current_source(store, binding) ||
        !platform.safe_to_commit() || !platform.valid_owner_point(binding.owner_public_key) ||
        !standalone::valid_wifi_credentials(values.ssid, values.password,
                                            standalone::default_time_server) ||
        !platform.station_ready(values.ssid))
        return {};
    const auto utc = platform.trusted_utc_now();
    if (!utc || !*utc)
        return {};

    Proposal proposal;
    auto& profile = proposal.value;
    profile.device_id = binding.device_id;
    profile.owner_epoch = 1;
    profile.owners = {binding.owner_public_key};
    profile.ssid = values.ssid;
    profile.password = values.password;
    profile.time_server = standalone::default_time_server;
    profile.callsign = values.callsign;
    profile.locator = values.locator;
    profile.power_dbm = values.power_dbm;
    profile.request_sha256 = network::bootstrap_digest(request);
    const auto hostname = platform.local_hostname();
    const auto canonical_hostname = network::canonical_local_hostname(hostname);
    if (!canonical_hostname || *canonical_hostname != hostname ||
        !platform.generate_tls(binding.device_id, hostname, *utc, profile.tls) ||
        profile.tls.hostname != hostname ||
        !platform.valid_tls(profile.tls, binding.device_id, *utc))
        return {};
    proposal.payload = serialize_consumer_profile(profile);
    if (proposal.payload.empty())
        return {};

    // Slow certificate generation may cross a claim or clock deadline.
    const auto commit_ms = platform.monotonic_now_ms();
    if (commit_ms < fresh_ms)
        return {};
    slot.expire(commit_ms);
    const auto fresh_utc = platform.trusted_utc_now();
    if (slot.state() != ConsumerClaimState::Trial ||
        !slot.trial_request_matches(values.request_id) || !current_source(store, binding) ||
        !platform.safe_to_commit() || !platform.station_ready(values.ssid) || !fresh_utc ||
        !platform.valid_tls(profile.tls, binding.device_id, *fresh_utc))
        return {};

    if (!store.select(ProfileSource::ConsumerProfile, proposal.payload))
        return {ConsumerCommitState::Reconcile, 0, {}};
    const auto generation = binding.generation + 1;
    if (!store.healthy() || store.source() != ProfileSource::ConsumerProfile ||
        store.sequence() != generation || store.data() != proposal.payload)
        return {ConsumerCommitState::Reconcile, 0, {}};
    const auto finished_ms = platform.monotonic_now_ms();
    const bool terminal =
        finished_ms >= commit_ms && slot.finish(true, profile.request_sha256, generation,
                                                finished_ms, platform.safe_to_commit());
    return {terminal ? ConsumerCommitState::Committed : ConsumerCommitState::Reconcile, generation,
            profile.request_sha256};
}
} // namespace wsprrypico::provisioning

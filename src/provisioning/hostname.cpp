#include "provisioning/hostname.hpp"

#include "application/resources.hpp"
#include "network/identity.hpp"
#include "wtp/json.hpp"

#include <limits>

namespace wsprrypico::provisioning {
namespace {
struct Proposal {
    ConsumerProfile profile;
    std::string payload;
    ~Proposal() {
        scrub(profile);
        volatile char* p = payload.data();
        for (std::size_t i = 0; i < payload.size(); ++i)
            p[i] = 0;
    }
};
} // namespace

std::string HostnameSettings::revision_context() const {
    return ":hostname:" + std::to_string(store_.sequence()) + (store_.healthy() ? ":ok" : ":fault");
}

std::string HostnameSettings::readback(std::string_view boot, bool local_usb) const {
    auto parsed = store_.healthy() && store_.source() == ProfileSource::ConsumerProfile
                      ? parse_consumer_profile(store_.data())
                      : std::nullopt;
    const bool consumer = parsed && parsed->device_id == device_;
    const bool local_blank = local_usb && runtime_.control_healthy(store_) &&
                             (runtime_.source() == RuntimeSource::Unprovisioned ||
                              runtime_.source() == RuntimeSource::NetworkOnly);
    const auto saved = consumer ? parsed->tls.hostname : active_.empty() ? default_ : active_;
    const bool writable =
        !default_.empty() &&
        ((consumer && runtime_.consumer_profile() && runtime_.generation() == store_.sequence()) ||
         local_blank);
    const auto reason = !store_.healthy() ? "storage_fault"
                        : writable        ? ""
                        : consumer        ? (writable ? "" : "profile_unavailable")
                        : store_.source() == ProfileSource::NetworkOnly
                            ? "complete_station_setup_first"
                            : "credential_bound_deployment";
    auto result =
        "{\"schema\":\"transmitter-hostname/1\",\"target\":" + application::target(device_, boot) +
        ",\"saved\":" + wtp::json::quote(saved) + ",\"active\":" + wtp::json::quote(active_) +
        ",\"default\":" + wtp::json::quote(default_) +
        ",\"source\":" + wtp::json::quote(consumer ? "consumer_profile" : "deployment") +
        ",\"writable\":" + (writable ? "true" : "false") +
        ",\"reason\":" + wtp::json::quote(reason) +
        ",\"pending_restart\":" + (saved != active_ ? "true" : "false") +
        ",\"generation\":" + wtp::json::quote(std::to_string(store_.sequence())) +
        ",\"storage_healthy\":" + (store_.healthy() ? "true}" : "false}");
    if (parsed)
        scrub(*parsed);
    return result;
}

std::string HostnameSettings::save(const std::optional<std::string>& requested, bool local_usb) {
    const auto name = network::canonical_local_hostname(requested ? *requested : default_);
    if (!name)
        return "invalid_hostname";
    if (!store_.healthy())
        return "storage_fault";
    if (store_.source() != ProfileSource::ConsumerProfile)
        return "hostname_profile_read_only";
    if (default_.empty() || (!local_usb && !platform_.safe_to_commit()) ||
        runtime_.generation() != store_.sequence())
        return "hostname_unavailable";
    Proposal previous, next;
    auto parsed = parse_consumer_profile(store_.data());
    if (!parsed || parsed->device_id != device_ || !runtime_.consumer_profile()) {
        if (parsed)
            scrub(*parsed);
        return "hostname_unavailable";
    }
    next.profile = std::move(*parsed);
    scrub(*parsed);
    if (next.profile.tls.hostname == *name)
        return {}; // Canonical no-op consumes no generation and no entropy.
    if (store_.sequence() == std::numeric_limits<std::uint64_t>::max())
        return "generation_exhausted";
    const auto generation = store_.sequence();
    previous.payload = store_.data();
    if (next.profile.tls_pending) {
        next.profile.tls.hostname = *name;
    } else {
        previous.profile.tls = next.profile.tls;
        const auto now =
            local_usb ? platform_.trusted_local_utc_now() : platform_.trusted_utc_now();
        if (!now || !platform_.rename_tls(device_, *name, *now, next.profile.tls))
            return "hostname_certificate_unavailable";
        const auto fresh =
            local_usb ? platform_.trusted_local_utc_now() : platform_.trusted_utc_now();
        if (!fresh || !platform_.valid_tls(next.profile.tls, device_, *fresh))
            return "hostname_certificate_unavailable";
        const auto& old = previous.profile.tls;
        if (next.profile.tls.ca_certificate != old.ca_certificate ||
            next.profile.tls.ca_private_key != old.ca_private_key ||
            next.profile.tls.ca_not_after_utc != old.ca_not_after_utc ||
            next.profile.tls.server_private_key != old.server_private_key)
            return "hostname_trust_changed";
    }
    if (next.profile.tls.hostname != *name || (!local_usb && !platform_.safe_to_commit()) ||
        !store_.healthy() || store_.source() != ProfileSource::ConsumerProfile ||
        store_.sequence() != generation || store_.data() != previous.payload)
        return "hostname_unavailable";
    next.payload = serialize_consumer_profile(next.profile);
    if (next.payload.empty())
        return "hostname_profile_too_large";
    const auto committed =
        commit_setup_profile(store_, ProfileSource::ConsumerProfile, next.payload);
    // Reconcile the actual durable selection even after a lost flash acknowledgement.
    const bool loaded = runtime_.load(store_, device_, BuildBundleState::Absent);
    if (committed == SetupCommitResult::Reconcile || !loaded)
        return "hostname_reconcile_required";
    return committed == SetupCommitResult::Committed ? "" : "storage_fault";
}
} // namespace wsprrypico::provisioning

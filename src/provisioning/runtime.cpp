#include "provisioning/runtime.hpp"

#include "network/identity.hpp"
#include "wtp/json.hpp"

#include <utility>

namespace wsprrypico::provisioning {
BuildBundleState classify_build_bundle(std::string_view actual_device_id,
                                       const BuildBundleDescriptor& bundle) {
    if (!bundle.port && bundle.device_id.empty() && bundle.hostname.empty() &&
        bundle.certificate.empty() && bundle.private_key.empty() && bundle.client_ca.empty())
        return BuildBundleState::Absent;
    if (bundle.port && bundle.port <= 65535 && network::valid_device_id(bundle.device_id) &&
        !bundle.hostname.empty() && !bundle.certificate.empty() && !bundle.private_key.empty() &&
        !bundle.client_ca.empty() &&
        network::deployment_identity_matches(actual_device_id, bundle.device_id, bundle.hostname))
        return BuildBundleState::Matching;
    return BuildBundleState::Mismatched;
}

RuntimeProfile::~RuntimeProfile() {
    clear();
}

void RuntimeProfile::clear() {
    scrub(profile_);
    has_profile_ = false;
    scrub(network_profile_);
    has_network_profile_ = false;
    scrub(consumer_profile_);
    has_consumer_profile_ = false;
}

bool RuntimeProfile::load(const ProfileStore& store, std::string_view actual_device_id,
                          BuildBundleState build_bundle) {
    clear();
    generation_ = store.sequence();
    source_ = RuntimeSource::Fault;
    fault_ = RuntimeFault::Storage;
    if (!store.healthy())
        return false;
    // Structural admission permits only station association for time and a
    // read-only recovery surface. Owner and TLS authority require separate
    // post-clock validation; source 5 must never fall through to legacy data.
    if (store.source() == ProfileSource::ConsumerProfile) {
        auto parsed = parse_consumer_profile(store.data());
        if (!parsed) {
            fault_ = RuntimeFault::Malformed;
            return false;
        }
        if (parsed->device_id != actual_device_id) {
            fault_ = RuntimeFault::WrongDevice;
            scrub(*parsed);
            return false;
        }
        consumer_profile_ = std::move(*parsed);
        scrub(*parsed);
        has_consumer_profile_ = true;
        source_ = RuntimeSource::ConsumerPreClock;
        fault_ = RuntimeFault::None;
        return true;
    }
    if (store.source() == ProfileSource::Unprovisioned ||
        (store.source() == ProfileSource::LegacyBootstrap && !generation_ &&
         build_bundle == BuildBundleState::Absent)) {
        if (!store.data().empty())
            return false;
        source_ = RuntimeSource::Unprovisioned;
        fault_ = RuntimeFault::None;
        return true;
    }
    if (store.source() == ProfileSource::BuildBundle ||
        (store.source() == ProfileSource::LegacyBootstrap && !generation_)) {
        if (!store.data().empty())
            return false;
        if (build_bundle != BuildBundleState::Matching) {
            fault_ = RuntimeFault::WrongDevice;
            return false;
        }
        source_ = RuntimeSource::Factory;
        fault_ = RuntimeFault::None;
        return true;
    }
    if (store.source() == ProfileSource::NetworkOnly) {
        auto parsed = parse_network_profile(store.data());
        if (!parsed) {
            fault_ = RuntimeFault::Malformed;
            return false;
        }
        if (parsed->device_id != actual_device_id) {
            fault_ = RuntimeFault::WrongDevice;
            scrub(*parsed);
            return false;
        }
        network_profile_ = std::move(*parsed);
        scrub(*parsed);
        has_network_profile_ = true;
        source_ = RuntimeSource::NetworkOnly;
        fault_ = RuntimeFault::None;
        return true;
    }
    auto parsed = parse_profile(store.data());
    if (!parsed) {
        fault_ = RuntimeFault::Malformed;
        return false;
    }
    if (parsed->device_id != actual_device_id) {
        fault_ = RuntimeFault::WrongDevice;
        scrub(*parsed);
        return false;
    }
    profile_ = std::move(*parsed);
    scrub(*parsed);
    has_profile_ = true;
    source_ = RuntimeSource::Provisioned;
    fault_ = RuntimeFault::None;
    return true;
}

std::optional<standalone::Config> RuntimeProfile::overlay(const standalone::Config& base) const {
    if (source_ == RuntimeSource::Fault || source_ == RuntimeSource::Unprovisioned ||
        source_ == RuntimeSource::NetworkOnly)
        return {};
    auto result = base;
    if (has_profile_) {
        result.ssid = profile_.ssid;
        result.password = profile_.password;
        result.ntp_ipv4 = profile_.time_server;
    }
    if (has_consumer_profile_) {
        result.ssid = consumer_profile_.ssid;
        result.password = consumer_profile_.password;
        result.ntp_ipv4 = consumer_profile_.time_server;
        // Keep standalone schedules and watermark data outside the claim.
        result.callsign = consumer_profile_.callsign;
        result.locator = consumer_profile_.locator;
        result.power_dbm = consumer_profile_.power_dbm;
    }
    return result;
}

std::string RuntimeProfile::consumer_readback_json() const {
    if (!has_consumer_profile_)
        return "null";
    const auto& profile = consumer_profile_;
    // Explicit allowlist: the full profile contains Wi-Fi and TLS secrets.
    // Reuse one buffer rather than retaining a chain of string temporaries
    // on the target stack while the outer INFO buffer is also resident.
    std::string result;
    result.reserve(768);
    result += "{\"station\":{\"callsign\":";
    result += wtp::json::quote(profile.callsign);
    result += ",\"locator\":";
    result += wtp::json::quote(profile.locator);
    result += ",\"power_dbm\":";
    result += std::to_string(profile.power_dbm);
    result += "},\"network\":{\"ssid\":";
    result += wtp::json::quote(profile.ssid);
    result += ",\"time_server\":";
    result += wtp::json::quote(profile.time_server);
    result += "},\"owner_count\":";
    result += std::to_string(profile.owners.size());
    result += ",\"owner_epoch\":";
    result += wtp::json::quote(std::to_string(profile.owner_epoch));
    result += ",\"request_sha256\":";
    result += wtp::json::quote(profile.request_sha256);
    result += "}";
    return result;
}
} // namespace wsprrypico::provisioning

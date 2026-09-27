#include "provisioning/runtime.hpp"

#include "network/identity.hpp"

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
}

bool RuntimeProfile::load(const ProfileStore& store, std::string_view actual_device_id,
                          BuildBundleState build_bundle) {
    clear();
    generation_ = store.sequence();
    source_ = RuntimeSource::Fault;
    fault_ = RuntimeFault::Storage;
    if (!store.healthy())
        return false;
    // Source 5 is intentionally inert until the complete owner, certificate
    // and station authority path is installed. Never parse it as legacy data.
    if (store.source() == ProfileSource::ConsumerProfile) {
        fault_ = RuntimeFault::Malformed;
        return false;
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
    return result;
}
} // namespace wsprrypico::provisioning

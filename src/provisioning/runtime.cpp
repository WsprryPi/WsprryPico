#include "provisioning/runtime.hpp"

#include <utility>

namespace wsprrypico::provisioning {
RuntimeProfile::~RuntimeProfile() {
    clear();
}

void RuntimeProfile::clear() {
    scrub(profile_);
    has_profile_ = false;
}

bool RuntimeProfile::load(const ProfileStore& store, std::string_view actual_device_id) {
    clear();
    generation_ = store.sequence();
    source_ = RuntimeSource::Fault;
    fault_ = RuntimeFault::Storage;
    if (!store.healthy())
        return false;
    if (store.source() == ProfileSource::Unprovisioned) {
        if (!store.data().empty())
            return false;
        source_ = RuntimeSource::Unprovisioned;
        fault_ = RuntimeFault::None;
        return true;
    }
    if (store.source() == ProfileSource::BuildBundle || !generation_) {
        if (!store.data().empty())
            return false;
        source_ = RuntimeSource::Factory;
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
    if (source_ == RuntimeSource::Fault)
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

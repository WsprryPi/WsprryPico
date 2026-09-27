#pragma once

#include "provisioning/consumer_profile.hpp"
#include "provisioning/network_profile.hpp"
#include "provisioning/storage.hpp"
#include "standalone/config.hpp"

#include <optional>
#include <string_view>

namespace wsprrypico::provisioning {
enum class RuntimeSource {
    Factory,
    Provisioned,
    NetworkOnly,
    ConsumerPreClock,
    Unprovisioned,
    Fault
};
enum class RuntimeFault { None, Storage, Malformed, WrongDevice };
enum class BuildBundleState { Absent, Matching, Mismatched };

struct BuildBundleDescriptor {
    std::string_view device_id;
    std::string_view hostname;
    unsigned port = 0;
    std::string_view certificate;
    std::string_view private_key;
    std::string_view client_ca;
};

BuildBundleState classify_build_bundle(std::string_view actual_device_id,
                                       const BuildBundleDescriptor& bundle);

// Owns provisioned strings for the complete lifetime of platform adapters.
// Factory requires a matching device-bound build bundle. A generic image with
// an erased profile journal is Unprovisioned; ambiguous storage fails closed.
class RuntimeProfile {
  public:
    RuntimeProfile() = default;
    ~RuntimeProfile();
    RuntimeProfile(const RuntimeProfile&) = delete;
    RuntimeProfile& operator=(const RuntimeProfile&) = delete;
    bool load(const ProfileStore& store, std::string_view actual_device_id,
              BuildBundleState build_bundle);
    RuntimeSource source() const {
        return source_;
    }
    RuntimeFault fault() const {
        return fault_;
    }
    std::uint64_t generation() const {
        return generation_;
    }
    const Profile* profile() const {
        return has_profile_ ? &profile_ : nullptr;
    }
    const NetworkProfile* network_profile() const {
        return has_network_profile_ ? &network_profile_ : nullptr;
    }
    const ConsumerProfile* consumer_profile() const {
        return has_consumer_profile_ ? &consumer_profile_ : nullptr;
    }
    std::optional<standalone::Config> overlay(const standalone::Config& base) const;

  private:
    void clear();
    RuntimeSource source_ = RuntimeSource::Fault;
    RuntimeFault fault_ = RuntimeFault::Storage;
    std::uint64_t generation_ = 0;
    Profile profile_{};
    bool has_profile_ = false;
    NetworkProfile network_profile_{};
    bool has_network_profile_ = false;
    ConsumerProfile consumer_profile_{};
    bool has_consumer_profile_ = false;
};
} // namespace wsprrypico::provisioning

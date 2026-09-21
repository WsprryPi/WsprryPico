#pragma once

#include "provisioning/storage.hpp"
#include "standalone/config.hpp"

#include <optional>

namespace wsprrypico::provisioning {
enum class RuntimeSource {
    Factory,
    Provisioned,
    Fault
};
enum class RuntimeFault {
    None,
    Storage,
    Malformed,
    WrongDevice
};

// Owns provisioned strings for the complete lifetime of platform adapters.
// Factory means no committed profile exists. Fault is fail-closed and never
// revives factory credentials after a committed profile is present.
class RuntimeProfile {
  public:
    RuntimeProfile() = default;
    ~RuntimeProfile();
    RuntimeProfile(const RuntimeProfile&) = delete;
    RuntimeProfile& operator=(const RuntimeProfile&) = delete;
    bool load(const ProfileStore& store, std::string_view actual_device_id);
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
    std::optional<standalone::Config> overlay(const standalone::Config& base) const;

  private:
    void clear();
    RuntimeSource source_ = RuntimeSource::Fault;
    RuntimeFault fault_ = RuntimeFault::Storage;
    std::uint64_t generation_ = 0;
    Profile profile_{};
    bool has_profile_ = false;
};
} // namespace wsprrypico::provisioning

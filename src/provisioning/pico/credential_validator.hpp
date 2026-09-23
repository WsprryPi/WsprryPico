#pragma once

#include "provisioning/profile.hpp"

#include <cstdint>
#include <string>
#include <utility>

namespace wsprrypico::provisioning {
// This validator owns one shared PSA lease only for the duration of validate().
// Its certificate/key contexts remain independent from an active TLS server.
class MbedTlsCredentialValidator final : public CredentialValidator {
  public:
    explicit MbedTlsCredentialValidator(std::string expected_device_id)
        : expected_device_id_(std::move(expected_device_id)) {}
    bool validate(const Profile& profile) override;
    bool validate(CredentialMaterial material);
    // A committed profile was already validated against trusted UTC before it
    // became authoritative. Reboot starts without UTC, so server construction
    // may ignore only certificate not-yet-valid/expired flags; every identity,
    // chain, purpose, algorithm and key-pair check remains mandatory.
    bool validate_for_server_boot(CredentialMaterial material);
    int last_error() const {
        return last_error_;
    }
    std::uint32_t verify_flags() const {
        return verify_flags_;
    }

  private:
    bool validate_impl(CredentialMaterial material, bool allow_time_unknown);
    std::string expected_device_id_;
    int last_error_ = 0;
    std::uint32_t verify_flags_ = 0;
};
} // namespace wsprrypico::provisioning

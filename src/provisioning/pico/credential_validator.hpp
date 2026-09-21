#pragma once

#include "provisioning/profile.hpp"

#include <cstdint>
#include <string>
#include <utility>

namespace wsprrypico::provisioning {
// This validator owns PSA only for the duration of validate(). Callers must
// stop the TLS server before using it for a future live replacement.
class MbedTlsCredentialValidator final : public CredentialValidator {
  public:
    explicit MbedTlsCredentialValidator(std::string expected_device_id)
        : expected_device_id_(std::move(expected_device_id)) {}
    bool validate(const Profile& profile) override;
    bool validate(CredentialMaterial material);
    int last_error() const {
        return last_error_;
    }
    std::uint32_t verify_flags() const {
        return verify_flags_;
    }

  private:
    std::string expected_device_id_;
    int last_error_ = 0;
    std::uint32_t verify_flags_ = 0;
};
} // namespace wsprrypico::provisioning

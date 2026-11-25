#pragma once

#include "rf/job_service.hpp"

#include <string>

namespace wsprrypico::firmware {

class PicoClock final : public execution::Clock {
  public:
    [[nodiscard]] execution::ClockSnapshot snapshot() const override;
};

class PicoIdentitySource final : public execution::IdentitySource {
  public:
    PicoIdentitySource();

    [[nodiscard]] std::string new_boot_id() override;
    [[nodiscard]] const std::string& device_id() const;

  private:
    std::string device_id_;
};

} // namespace wsprrypico::firmware

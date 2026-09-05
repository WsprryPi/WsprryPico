#pragma once

#include "wtp/job_service.hpp"

#include <string>

namespace wsprrypico::firmware {

class PicoClock final : public wtp::Clock {
  public:
    [[nodiscard]] wtp::ClockSnapshot snapshot() const override;
};

class PicoIdentitySource final : public wtp::IdentitySource {
  public:
    PicoIdentitySource();

    [[nodiscard]] std::string new_boot_id() override;
    [[nodiscard]] const std::string& device_id() const;

  private:
    std::string device_id_;
};

} // namespace wsprrypico::firmware

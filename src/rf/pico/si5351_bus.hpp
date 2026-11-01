// SPDX-License-Identifier: MIT
#pragma once
#include "hardware/i2c.h"
#include "hardware/si5351_settings.hpp"
#include "rf/si5351_device.hpp"

namespace wsprrypico::rf::si5351 {
// RF-worker-owned adapter. Construction never accesses pins or the bus.
class PicoBus final : public Bus {
  public:
    PicoBus() = default;
    PicoBus(const PicoBus&) = delete;
    PicoBus& operator=(const PicoBus&) = delete;
    bool open(const hardware::PinPlan&, const hardware::Si5351Settings&,
              const hardware::FilterSettings& filters = {});
    bool read(std::uint8_t, std::span<std::uint8_t>, std::uint64_t) override;
    bool write(std::uint8_t, std::span<const std::uint8_t>, std::uint64_t) override;

  private:
    static std::uint32_t remaining_us(std::uint64_t deadline_ns);
    bool failed();
    i2c_inst_t* bus_ = nullptr;
    unsigned address_ = 0;
};
} // namespace wsprrypico::rf::si5351

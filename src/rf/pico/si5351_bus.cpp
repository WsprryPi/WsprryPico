// SPDX-License-Identifier: MIT
#include "rf/pico/si5351_bus.hpp"

#include "hardware/gpio.h"
#include "pico/time.h"

#include <algorithm>

namespace wsprrypico::rf::si5351 {
bool PicoBus::open(const hardware::PinPlan& pins, const hardware::Si5351Settings& settings,
                   const hardware::FilterSettings& filters) {
    if (bus_ || !hardware::validate_si5351(pins, settings, 0, filters).valid())
        return false;
    const auto pair = hardware::i2c_pairs[*pins.i2c_pair];
    bus_ = pair.controller ? i2c1 : i2c0;
    address_ = settings.address;
    i2c_init(bus_, 100'000);
    gpio_set_function(pair.sda, GPIO_FUNC_I2C);
    gpio_set_function(pair.scl, GPIO_FUNC_I2C);
    // Match the documented 100 kHz bench wiring. Pull-up adequacy and rise
    // time remain electrical qualification questions, not a speed upgrade.
    gpio_pull_up(pair.sda);
    gpio_pull_up(pair.scl);
    return true;
}
std::uint32_t PicoBus::remaining_us(std::uint64_t deadline_ns) {
    const auto now = time_us_64() * 1000ULL;
    if (deadline_ns <= now)
        return 0;
    // Round DOWN so a sub-us remainder cannot extend the absolute deadline.
    return static_cast<std::uint32_t>(std::min<std::uint64_t>((deadline_ns - now) / 1000, 5'000));
}
bool PicoBus::failed() {
    // A timed-out repeated-start transaction must not leave a controller open
    // for unrelated work. Recovery requires a new owner-controlled open;
    // resetting this controller says nothing about the external RF outputs.
    if (bus_)
        i2c_deinit(bus_);
    bus_ = nullptr;
    return false;
}
bool PicoBus::read(std::uint8_t reg, std::span<std::uint8_t> bytes, std::uint64_t deadline) {
    if (!bus_ || bytes.empty() || bytes.size() > 8)
        return false;
    auto remaining = remaining_us(deadline);
    if (!remaining || i2c_write_timeout_us(bus_, address_, &reg, 1, true, remaining) != 1)
        return failed();
    remaining = remaining_us(deadline);
    if (!remaining ||
        i2c_read_timeout_us(bus_, address_, bytes.data(), bytes.size(), false, remaining) !=
            static_cast<int>(bytes.size()) ||
        !remaining_us(deadline))
        return failed();
    return true;
}
bool PicoBus::write(std::uint8_t reg, std::span<const std::uint8_t> bytes, std::uint64_t deadline) {
    if (!bus_ || bytes.empty() || bytes.size() > 8)
        return false;
    std::array<std::uint8_t, 9> payload{reg};
    std::copy(bytes.begin(), bytes.end(), payload.begin() + 1);
    const auto remaining = remaining_us(deadline);
    if (!remaining ||
        i2c_write_timeout_us(bus_, address_, payload.data(), bytes.size() + 1, false, remaining) !=
            static_cast<int>(bytes.size() + 1) ||
        !remaining_us(deadline))
        return failed();
    return true;
}
} // namespace wsprrypico::rf::si5351

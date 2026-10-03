#pragma once
#include <array>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace wsprrypico::hardware {
struct I2cPair {
    unsigned controller, sda, scl;
};
inline constexpr std::array<I2cPair, 12> i2c_pairs{{{0, 0, 1},
                                                    {0, 4, 5},
                                                    {0, 8, 9},
                                                    {0, 12, 13},
                                                    {0, 16, 17},
                                                    {0, 20, 21},
                                                    {1, 2, 3},
                                                    {1, 6, 7},
                                                    {1, 10, 11},
                                                    {1, 14, 15},
                                                    {1, 18, 19},
                                                    {1, 26, 27}}};
constexpr bool eligible(unsigned gp) {
    return gp <= 22 || (gp >= 26 && gp <= 28);
}
struct PinPlan {
    bool operator==(const PinPlan&) const = default;
    enum class Engine { Direct, I2c };
    Engine engine = Engine::Direct;
    std::optional<unsigned> rf = 2, i2c_pair;
    std::optional<unsigned> button = 14, amplifier;
    std::vector<unsigned> lpf;
    enum class Indicator { Onboard, External, Disabled };
    Indicator indicator = Indicator::Onboard;
    std::optional<unsigned> indicator_gp;
    bool indicator_active_high = true;
};
struct Validation {
    std::string error, role, owner;
    std::optional<unsigned> gp;
    std::array<std::string, 29> owners{};
    bool valid() const {
        return error.empty();
    }
};
Validation validate(const PinPlan& plan);
// Closed schema: engine, rf_gp, i2c_pair, button_gp, amplifier_gp,
// lpf_gps, indicator, indicator_gp. Optional resources are explicit JSON null.
std::optional<PinPlan> parse_plan(std::string_view text);
std::string serialize_plan(const PinPlan& plan);
bool operational(const PinPlan& plan);
std::string describe(const PinPlan& plan);
std::string choices();
} // namespace wsprrypico::hardware

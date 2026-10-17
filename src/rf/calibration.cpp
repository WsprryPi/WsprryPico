#include "rf/calibration.hpp"

namespace wsprrypico::rf {
std::optional<std::int32_t> parse_ppm(std::string_view text) {
    if (text.empty() || text.size() > 8)
        return {};
    bool negative = text.front() == '-';
    if (negative || text.front() == '+')
        text.remove_prefix(1);
    if (text.empty())
        return {};
    std::int32_t whole = 0, fraction = 0;
    unsigned digits = 0, decimals = 0;
    bool point = false;
    for (char c : text) {
        if (c == '.' && !point && digits) {
            point = true;
            continue;
        }
        if (c < '0' || c > '9')
            return {};
        if (point) {
            if (++decimals > 3)
                return {};
            fraction = fraction * 10 + c - '0';
        } else {
            if (++digits > 3)
                return {};
            whole = whole * 10 + c - '0';
        }
    }
    if (!digits || (point && !decimals))
        return {};
    for (; decimals < 3; ++decimals)
        fraction *= 10;
    const auto ppb = whole * 1000 + fraction;
    if (ppb > correction_limit_ppb)
        return {};
    return negative ? -ppb : ppb;
}
std::string format_ppm(std::int32_t ppb) {
    const auto n = ppb < 0 ? -std::int64_t(ppb) : std::int64_t(ppb);
    const auto fraction = std::to_string(n % 1000 + 1000).substr(1);
    return std::string(ppb < 0 ? "-" : "") + std::to_string(n / 1000) + "." + fraction;
}
} // namespace wsprrypico::rf

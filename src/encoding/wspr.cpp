// Type 1 packing and sync constants adapted from WsprryPi WSPR-Reference.
// Copyright (c) 2024 Lee Bussy. MIT; see WsprryPi-LICENSE.md.
#include "encoding/wspr.hpp"

#include <algorithm>
#include <bit>

namespace wsprrypico::encoding {
namespace {
constexpr Symbols sync = {1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1,
                          1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0,
                          1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0,
                          1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0,
                          0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1,
                          0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0,
                          0, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0};
constexpr bool letter(char c) {
    return c >= 'A' && c <= 'Z';
}
constexpr bool digit(char c) {
    return c >= '0' && c <= '9';
}
constexpr unsigned code(char c) {
    return digit(c) ? unsigned(c - '0') : letter(c) ? unsigned(c - 'A' + 10) : 36;
}
} // namespace
std::optional<Symbols> wspr_type1(std::string_view call, std::string_view grid, unsigned dbm) {
    constexpr std::array powers{0U,  3U,  7U,  10U, 13U, 17U, 20U, 23U, 27U, 30U,
                                33U, 37U, 40U, 43U, 47U, 50U, 53U, 57U, 60U};
    if (call.size() < 3 || call.size() > 6 || grid.size() != 4 || grid[0] < 'A' || grid[0] > 'R' ||
        grid[1] < 'A' || grid[1] > 'R' || !digit(grid[2]) || !digit(grid[3]) ||
        std::find(powers.begin(), powers.end(), dbm) == powers.end())
        return {};
    std::array<char, 6> padded{' ', ' ', ' ', ' ', ' ', ' '};
    const unsigned offset = digit(call[2]) ? 0 : 1;
    if (offset + call.size() > padded.size())
        return {};
    std::copy(call.begin(), call.end(), padded.begin() + offset);
    if (!(letter(padded[0]) || digit(padded[0]) || padded[0] == ' ') ||
        !(letter(padded[1]) || digit(padded[1])) || !digit(padded[2]) || !letter(padded[3]))
        return {};
    for (unsigned i = 3; i < 6; ++i)
        if (!(letter(padded[i]) || padded[i] == ' '))
            return {};
    // Input cannot contain embedded padding, punctuation or lowercase.
    for (char c : call)
        if (!letter(c) && !digit(c))
            return {};
    std::uint32_t n = code(padded[0]);
    n = n * 36 + code(padded[1]);
    n = n * 10 + code(padded[2]);
    for (unsigned i = 3; i < 6; ++i)
        n = n * 27 + code(padded[i]) - 10;
    const std::uint32_t m = ((179 - 10 * (grid[0] - 'A') - (grid[2] - '0')) * 180 +
                             10 * (grid[1] - 'A') + grid[3] - '0') *
                                128 +
                            dbm + 64;
    const std::uint64_t payload = (std::uint64_t{n} << 22) | m;
    Symbols coded{}, result = sync;
    std::uint32_t shift = 0;
    for (unsigned i = 0; i < 81; ++i) {
        shift = (shift << 1) | (i < 50 ? unsigned((payload >> (49 - i)) & 1) : 0);
        coded[2 * i] = std::popcount(shift & 0xf2d05351U) & 1;
        coded[2 * i + 1] = std::popcount(shift & 0xe4613c47U) & 1;
    }
    unsigned source = 0;
    for (unsigned i = 0; i < 256; ++i) {
        unsigned reversed = 0;
        for (unsigned bit = 0; bit < 8; ++bit)
            reversed = (reversed << 1) | ((i >> bit) & 1);
        if (reversed < 162)
            result[reversed] += 2 * coded[source++];
    }
    return result;
}
} // namespace wsprrypico::encoding

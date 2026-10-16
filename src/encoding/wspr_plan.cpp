// Packing/hash arithmetic adapted from WsprryPi WSPR-Reference at
// a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1, wspr_ref_encoder.cpp.
// Copyright (c) 2024 Lee Bussy. MIT; see WsprryPi-LICENSE.md.
// Hash is Bob Jenkins lookup3/hashlittle with WSPR seed 146 and 15-bit reduction.
#include "encoding/wspr.hpp"

#include <algorithm>
#include <bit>

namespace wsprrypico::encoding {
namespace {
constexpr bool digit(char c) {
    return c >= '0' && c <= '9';
}
constexpr bool letter(char c) {
    return c >= 'A' && c <= 'Z';
}
constexpr unsigned code(char c) {
    return digit(c) ? unsigned(c - '0') : letter(c) ? unsigned(c - 'A' + 10) : 36;
}
std::uint32_t packed_six(const std::array<char, 6>& call) {
    std::uint32_t n = code(call[0]);
    n = n * 36 + code(call[1]);
    n = n * 10 + code(call[2]);
    for (unsigned i = 3; i < 6; ++i)
        n = n * 27 + code(call[i]) - 10;
    return n;
}
std::optional<std::uint32_t> base_call(std::string_view call) {
    // Reuse the exact Type 1 grammar, including its padding rules.
    if (!wspr_type1(call, "AA00", 0))
        return {};
    std::array<char, 6> padded{' ', ' ', ' ', ' ', ' ', ' '};
    std::copy(call.begin(), call.end(), padded.begin() + (digit(call[2]) ? 0 : 1));
    return packed_six(padded);
}
WsprFrame frame(WsprType type, std::uint32_t n, std::uint32_t m) {
    const auto payload = (std::uint64_t{n} << 22) | (m & 0x3fffffU);
    return {type, payload, wspr_channel(payload)};
}
std::optional<WsprFrame> compound(std::string_view call, unsigned dbm) {
    const auto slash = call.find('/');
    if (slash == std::string_view::npos || call.find('/', slash + 1) != std::string_view::npos)
        return {};
    const auto left = call.substr(0, slash), right = call.substr(slash + 1);
    // A three-character prefix can itself be a valid base call (W1A).
    // Choose the suffix branch only when its right-hand grammar also matches.
    if (const auto n = base_call(left);
        n && ((right.size() == 1 && (digit(right[0]) || letter(right[0]))) ||
              (right.size() == 2 && digit(right[0]) && digit(right[1])))) {
        unsigned extension;
        if (right.size() == 1 && (digit(right[0]) || letter(right[0])))
            extension = 60000U + code(right[0]);
        else if (right.size() == 2 && digit(right[0]) && digit(right[1]))
            extension = 60026U + 10U * unsigned(right[0] - '0') + unsigned(right[1] - '0');
        else
            return {};
        // The Type 2 extension occupies 15 bits, with the extra high bit
        // represented by +2 instead of +1 in the power/type field.
        return frame(WsprType::Type2, *n, (extension & 32767U) * 128U + dbm + 66U);
    }
    const auto n = base_call(right);
    if (!n || left.empty() || left.size() > 3 ||
        !std::all_of(left.begin(), left.end(), [](char c) { return letter(c) || digit(c); }))
        return {};
    unsigned extension = 0;
    for (unsigned i = 0; i < 3 - left.size(); ++i)
        extension = extension * 37 + 36;
    for (char c : left)
        extension = extension * 37 + code(c);
    return frame(WsprType::Type2, *n,
                 (extension & 32767U) * 128U + dbm + (extension >= 32768U ? 66U : 65U));
}
WsprFrame hashed(std::string_view call, std::string_view grid, unsigned dbm) {
    std::array<char, 6> rotated{};
    for (unsigned i = 0; i < 6; ++i)
        rotated[i] = grid[(i + 1) % 6];
    return frame(WsprType::Type3, packed_six(rotated),
                 unsigned(wspr_hash(call)) * 128U + 63U - dbm);
}
void mix(std::uint32_t& a, std::uint32_t& b, std::uint32_t& c) {
    a -= c;
    a ^= std::rotl(c, 4);
    c += b;
    b -= a;
    b ^= std::rotl(a, 6);
    a += c;
    c -= b;
    c ^= std::rotl(b, 8);
    b += a;
    a -= c;
    a ^= std::rotl(c, 16);
    c += b;
    b -= a;
    b ^= std::rotl(a, 19);
    a += c;
    c -= b;
    c ^= std::rotl(b, 4);
    b += a;
}
} // namespace
std::uint16_t wspr_hash(std::string_view call) {
    std::uint32_t a = 0xdeadbeefU + static_cast<std::uint32_t>(call.size()) + 146U;
    std::uint32_t b = a, c = a;
    const auto add = [&](std::string_view bytes) {
        for (unsigned i = 0; i < bytes.size(); ++i) {
            auto& word = i < 4 ? a : i < 8 ? b : c;
            word += std::uint32_t{static_cast<unsigned char>(bytes[i])} << (8 * (i % 4));
        }
    };
    while (call.size() > 12) {
        add(call.substr(0, 12));
        mix(a, b, c);
        call.remove_prefix(12);
    }
    if (!call.empty()) {
        add(call);
        c ^= b;
        c -= std::rotl(b, 14);
        a ^= c;
        a -= std::rotl(c, 11);
        b ^= a;
        b -= std::rotl(a, 25);
        c ^= b;
        c -= std::rotl(b, 16);
        a ^= c;
        a -= std::rotl(c, 4);
        b ^= a;
        b -= std::rotl(a, 14);
        c ^= b;
        c -= std::rotl(b, 24);
    }
    return static_cast<std::uint16_t>(c & 32767U);
}
std::optional<WsprPlan> wspr_plan(std::string_view call, std::string_view locator, unsigned dbm) {
    if (!valid_station_details(call, locator, dbm))
        return {};
    WsprPlan plan;
    if (call.front() == '<') {
        if (locator.size() != 6)
            return {};
        const auto inner = call.substr(1, call.size() - 2);
        if (!base_call(inner) && !compound(inner, dbm))
            return {};
        plan.frames[0] = hashed(inner, locator, dbm);
        plan.count = 1;
    } else if (const auto single = wspr_type1_from_station(call, locator, dbm)) {
        const std::uint32_t m =
            ((179U - 10U * unsigned(locator[0] - 'A') - unsigned(locator[2] - '0')) * 180U +
             10U * unsigned(locator[1] - 'A') + unsigned(locator[3] - '0')) *
                128U +
            dbm + 64U;
        plan.frames[0] = {WsprType::Type1, (std::uint64_t{*base_call(call)} << 22) | m, *single};
        plan.count = 1;
    } else if (const auto type2 = compound(call, dbm)) {
        plan.frames[0] = *type2;
        plan.count = locator.size() == 6 ? 2 : 1;
        if (plan.count == 2)
            plan.frames[1] = hashed(call, locator, dbm);
        const auto slash = call.find('/');
        const auto suffix = call.substr(slash + 1);
        const bool letter_overlap = suffix.size() == 1 && suffix[0] >= 'Q' && suffix[0] <= 'Z';
        const bool numeric_overlap = suffix.size() == 2 && suffix[0] == '0' && digit(suffix[1]);
        if (letter_overlap || numeric_overlap) {
            plan.type2_ambiguous = true;
            std::copy_n(call.begin(), slash + 1, plan.alternate_call.begin());
            plan.alternate_length = static_cast<unsigned>(slash + 1);
            if (letter_overlap) {
                plan.alternate_call[plan.alternate_length++] = '0';
                plan.alternate_call[plan.alternate_length++] =
                    static_cast<char>('0' + suffix[0] - 'Q');
            } else
                plan.alternate_call[plan.alternate_length++] =
                    static_cast<char>('Q' + suffix[1] - '0');
        }
    } else
        return {};
    return plan;
}
} // namespace wsprrypico::encoding

#include "network/bootstrap_codec.hpp"

#include "wtp/sha256.hpp"

namespace wsprrypico::network {
namespace {
constexpr char hex_digits[] = "0123456789abcdef";
constexpr char b64_digits[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
int hex_value(char c) {
    if (c >= '0' && c <= '9')
        return c - '0';
    if (c >= 'a' && c <= 'f')
        return c - 'a' + 10;
    return -1;
}
int b64_value(char c) {
    for (int i = 0; i < 64; ++i)
        if (b64_digits[i] == c)
            return i;
    return -1;
}
} // namespace

std::string bootstrap_hex(std::span<const std::uint8_t> bytes) {
    std::string result;
    result.reserve(bytes.size() * 2);
    for (auto byte : bytes) {
        result += hex_digits[byte >> 4];
        result += hex_digits[byte & 15];
    }
    return result;
}
bool bootstrap_unhex(std::string_view text, std::span<std::uint8_t> out) {
    if (text.size() != out.size() * 2)
        return false;
    for (std::size_t i = 0; i < out.size(); ++i) {
        const int high = hex_value(text[i * 2]), low = hex_value(text[i * 2 + 1]);
        if (high < 0 || low < 0)
            return false;
        out[i] = static_cast<std::uint8_t>(high * 16 + low);
    }
    return true;
}
std::string bootstrap_b64url(std::span<const std::uint8_t> bytes) {
    std::string result;
    result.reserve((bytes.size() * 4 + 2) / 3);
    for (std::size_t i = 0; i < bytes.size(); i += 3) {
        const auto a = bytes[i];
        const auto b = i + 1 < bytes.size() ? bytes[i + 1] : 0;
        const auto c = i + 2 < bytes.size() ? bytes[i + 2] : 0;
        result += b64_digits[a >> 2];
        result += b64_digits[((a & 3) << 4) | (b >> 4)];
        if (i + 1 < bytes.size())
            result += b64_digits[((b & 15) << 2) | (c >> 6)];
        if (i + 2 < bytes.size())
            result += b64_digits[c & 63];
    }
    return result;
}
bool bootstrap_unb64url(std::string_view text, std::vector<std::uint8_t>& out, std::size_t minimum,
                        std::size_t maximum) {
    out.clear();
    if (text.empty() || text.size() % 4 == 1 || text.size() * 3 / 4 < minimum ||
        text.size() * 3 / 4 > maximum)
        return false;
    unsigned bits = 0, held = 0;
    for (char c : text) {
        const int digit = b64_value(c);
        if (digit < 0) {
            out.clear();
            return false;
        }
        held = (held << 6) | static_cast<unsigned>(digit);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            out.push_back(static_cast<std::uint8_t>(held >> bits));
            held &= (1U << bits) - 1;
        }
    }
    if (held || out.size() < minimum || out.size() > maximum || bootstrap_b64url(out) != text) {
        out.clear();
        return false;
    }
    return true;
}
std::string bootstrap_digest(std::span<const std::uint8_t> bytes) {
    return bootstrap_hex(wtp::sha256(bytes));
}
} // namespace wsprrypico::network

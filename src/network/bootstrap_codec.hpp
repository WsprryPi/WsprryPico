#pragma once

#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace wsprrypico::network {
std::string bootstrap_hex(std::span<const std::uint8_t> bytes);
bool bootstrap_unhex(std::string_view text, std::span<std::uint8_t> out);
std::string bootstrap_b64url(std::span<const std::uint8_t> bytes);
bool bootstrap_unb64url(std::string_view text, std::vector<std::uint8_t>& out, std::size_t minimum,
                        std::size_t maximum);
std::string bootstrap_digest(std::span<const std::uint8_t> bytes);
} // namespace wsprrypico::network

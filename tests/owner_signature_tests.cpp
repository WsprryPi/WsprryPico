#include "mbedtls/platform.h"
#include "network/bootstrap_codec.hpp"
#include "network/pico/owner_signature.hpp"

#include <array>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <random>
#include <string_view>

extern "C" mbedtls_ms_time_t mbedtls_ms_time(void) {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}
extern "C" int mbedtls_hardware_poll(void*, unsigned char* output, std::size_t count,
                                     std::size_t* received) {
    std::random_device random;
    for (std::size_t i = 0; i < count; ++i)
        output[i] = static_cast<unsigned char>(random());
    *received = count;
    return 0;
}

namespace {
template <std::size_t N> std::array<std::uint8_t, N> decode(std::string_view text) {
    std::array<std::uint8_t, N> bytes{};
    assert(wsprrypico::network::bootstrap_unhex(text, bytes));
    return bytes;
}
} // namespace

int main() {
    // Noble P-256 independently signs the Python hashlib Owner-HTTP/1 digest
    // with fixed test scalar 1. No private scalar is embedded in firmware.
    auto point = decode<65>("046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c2"
                            "964fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5");
    auto digest = decode<32>("2d7abd422c7760352607cf9521a840535e4610b19f11536c0fbfde7338dc337f");
    auto signature = decode<64>("089f7a5717765e2149dcbddbc8064b1adf91b177180675b574b15f03bd95a5981"
                                "5ed308ef6e56ed09ddafffa114a046e197434d6be77001c6cd43d86e75d0d81");
    assert(wsprrypico::network::verify_owner_signature(point, digest, signature));
    digest[0] ^= 1;
    assert(!wsprrypico::network::verify_owner_signature(point, digest, signature));
    digest[0] ^= 1;
    signature[0] ^= 1;
    assert(!wsprrypico::network::verify_owner_signature(point, digest, signature));
    signature[0] ^= 1;
    point[0] = 2;
    assert(!wsprrypico::network::verify_owner_signature(point, digest, signature));
    point[0] = 4;
    point[10] ^= 1;
    assert(!wsprrypico::network::verify_owner_signature(point, digest, signature));
    point[10] ^= 1;
    auto high_s = decode<64>("089f7a5717765e2149dcbddbc8064b1adf91b177180675b574b15f03bd95a598e"
                             "a12cf70091a913062250005eeb5fb91a372c5d6e8a09e6886e58d3c150617d0");
    assert(!wsprrypico::network::verify_owner_signature(point, digest, high_s));
    signature.fill(0);
    assert(!wsprrypico::network::verify_owner_signature(point, digest, signature));
}

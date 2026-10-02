#include "mbedtls/platform.h"
#include "network/bootstrap_codec.hpp"
#include "network/pico/recovery_crypto.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <random>
#include <string_view>
#include <vector>

using namespace wsprrypico;

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
template <std::size_t N> std::array<std::uint8_t, N> hex(std::string_view value) {
    std::array<std::uint8_t, N> result{};
    assert(network::bootstrap_unhex(value, result));
    return result;
}
std::vector<std::uint8_t> b64(std::string_view value, std::size_t expected) {
    std::vector<std::uint8_t> result;
    assert(network::bootstrap_unb64url(value, result, expected, expected));
    return result;
}
template <std::size_t N> std::array<std::uint8_t, N> fixed(std::string_view value) {
    const auto decoded = b64(value, N);
    std::array<std::uint8_t, N> result{};
    std::copy(decoded.begin(), decoded.end(), result.begin());
    return result;
}
} // namespace

int main() {
    const auto private_key =
        hex<32>("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb");
    {
        network::BootstrapTranscriptFields fields;
        fields.device_id = hex<16>("0102030405060708090a0b0c0d0e0f10");
        fields.boot_id = hex<16>("1112131415161718191a1b1c1d1e1f20");
        fields.slot_id = hex<16>("2122232425262728292a2b2c2d2e2f30");
        fields.browser_public_key = fixed<32>("hSDwCYkwp1R0i33ctD73Wg2_Og0mOBr066SpjqqbTmo");
        fields.pico_public_key = fixed<32>("3p7bfXt9wbTTW2HC7OQ1Nz-DQ8hbeGdNrfx-FG-IK08");
        fields.request_nonce = hex<16>("7172737475767778797a7b7c7d7e7f80");
        fields.request_id = hex<16>("bebc2fdea279d2ed7e088e650db7b759");
        const auto nonce = fixed<12>("fzCMy0ZhMgOmufn-");
        const auto ciphertext = b64("2V7II_EJRlVc", 9);
        const auto tag = fixed<16>("UhQFkPvLV4R69Td1YgnKvg");
        std::string command;
        network::PicoRecoveryCrypto crypto;
        assert(crypto.begin_for_test(private_key));
        assert(crypto.open(fields, nonce, ciphertext, tag, command));
        assert(command == "1:1:erase");
        assert(!crypto.open(fields, nonce, ciphertext, tag, command));
        assert(command.empty());
        for (int field = 0; field < 7; ++field) {
            auto changed = fields;
            switch (field) {
            case 0:
                changed.device_id[0] ^= 1;
                break;
            case 1:
                changed.boot_id[0] ^= 1;
                break;
            case 2:
                changed.slot_id[0] ^= 1;
                break;
            case 3:
                changed.request_id[0] ^= 1;
                break;
            case 4:
                changed.request_nonce[0] ^= 1;
                break;
            case 5:
                changed.browser_public_key[0] ^= 1;
                break;
            case 6:
                changed.pico_public_key[0] ^= 1;
                break;
            }
            network::PicoRecoveryCrypto bad;
            assert(bad.begin_for_test(private_key));
            assert(!bad.open(changed, nonce, ciphertext, tag, command));
            assert(command.empty());
            assert(!bad.open(fields, nonce, ciphertext, tag, command));
        }
        auto badtag = tag;
        badtag[0] ^= 1;
        network::PicoRecoveryCrypto bad;
        assert(bad.begin_for_test(private_key));
        assert(!bad.open(fields, nonce, ciphertext, badtag, command));
    }
    {
        network::BootstrapTranscriptFields fields;
        fields.device_id = hex<16>("0102030405060708090a0b0c0d0e0f10");
        fields.boot_id = hex<16>("1112131415161718191a1b1c1d1e1f20");
        fields.slot_id = hex<16>("2122232425262728292a2b2c2d2e2f30");
        fields.browser_public_key = fixed<32>("hSDwCYkwp1R0i33ctD73Wg2_Og0mOBr066SpjqqbTmo");
        fields.pico_public_key = fixed<32>("3p7bfXt9wbTTW2HC7OQ1Nz-DQ8hbeGdNrfx-FG-IK08");
        fields.request_nonce = hex<16>("7172737475767778797a7b7c7d7e7f80");
        fields.request_id = hex<16>("6602b4a423d78c99c05d0a71f55987c1");
        const auto nonce = fixed<12>("n4mHgFmHFfbjyyaN");
        const auto ciphertext = b64("3FVGqA3Nv3iKPTMRG-9bYS3jHA7EoA", 22);
        const auto tag = fixed<16>("EQP6p7OyZTBD-hXKjbfF-A");
        std::string command;
        network::PicoRecoveryCrypto crypto;
        assert(crypto.begin_for_test(private_key));
        assert(crypto.open(fields, nonce, ciphertext, tag, command));
        assert(command == "1:1:reset provisioning");
        assert(!crypto.open(fields, nonce, ciphertext, tag, command));
        assert(command.empty());
        for (int field = 0; field < 7; ++field) {
            auto changed = fields;
            switch (field) {
            case 0:
                changed.device_id[0] ^= 1;
                break;
            case 1:
                changed.boot_id[0] ^= 1;
                break;
            case 2:
                changed.slot_id[0] ^= 1;
                break;
            case 3:
                changed.request_id[0] ^= 1;
                break;
            case 4:
                changed.request_nonce[0] ^= 1;
                break;
            case 5:
                changed.browser_public_key[0] ^= 1;
                break;
            case 6:
                changed.pico_public_key[0] ^= 1;
                break;
            }
            network::PicoRecoveryCrypto bad;
            assert(bad.begin_for_test(private_key));
            assert(!bad.open(changed, nonce, ciphertext, tag, command));
            assert(command.empty());
            assert(!bad.open(fields, nonce, ciphertext, tag, command));
        }
        auto badtag = tag;
        badtag[0] ^= 1;
        network::PicoRecoveryCrypto bad;
        assert(bad.begin_for_test(private_key));
        assert(!bad.open(fields, nonce, ciphertext, badtag, command));
    }
}

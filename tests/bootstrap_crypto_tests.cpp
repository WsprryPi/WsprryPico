#include "mbedtls/chachapoly.h"
#include "mbedtls/platform.h"
#include "network/pico/bootstrap_crypto.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <fstream>
#include <iterator>
#include <random>
#include <string>
#include <vector>

using wsprrypico::network::BootstrapTranscriptFields;
using wsprrypico::network::PicoBootstrapCrypto;

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
std::vector<std::uint8_t> hex(std::string_view input) {
    assert(input.size() % 2 == 0);
    std::vector<std::uint8_t> result;
    for (std::size_t i = 0; i < input.size(); i += 2)
        result.push_back(
            static_cast<std::uint8_t>(std::stoul(std::string(input.substr(i, 2)), nullptr, 16)));
    return result;
}
int digit(char c) {
    if (c >= 'A' && c <= 'Z')
        return c - 'A';
    if (c >= 'a' && c <= 'z')
        return c - 'a' + 26;
    if (c >= '0' && c <= '9')
        return c - '0' + 52;
    if (c == '-')
        return 62;
    if (c == '_')
        return 63;
    return -1;
}
std::vector<std::uint8_t> b64u(std::string_view input) {
    std::vector<std::uint8_t> output;
    unsigned buffer = 0, bits = 0;
    for (char c : input) {
        const auto value = digit(c);
        assert(value >= 0);
        buffer = (buffer << 6) | static_cast<unsigned>(value);
        bits += 6;
        if (bits >= 8) {
            bits -= 8;
            output.push_back(static_cast<std::uint8_t>((buffer >> bits) & 255));
        }
    }
    return output;
}
template <std::size_t N> std::array<std::uint8_t, N> fixed(const std::vector<std::uint8_t>& bytes) {
    assert(bytes.size() == N);
    std::array<std::uint8_t, N> result{};
    std::copy(bytes.begin(), bytes.end(), result.begin());
    return result;
}
std::string field(wsprrypico::wtp::json::Value root, std::string_view key) {
    const auto value = root.get(key);
    assert(value);
    return value->string();
}
} // namespace

int main(int argc, char** argv) {
    assert(argc == 2);
    std::ifstream stream(argv[1]);
    const std::string fixture(std::istreambuf_iterator<char>{stream}, {});
    const auto root = wsprrypico::wtp::json::parse(fixture);
    assert(root);
    const auto private_key = fixed<32>(hex(field(*root, "pico_private_key_hex")));
    const auto expected_public = fixed<32>(b64u(field(*root, "pico_public_key")));
    BootstrapTranscriptFields fields;
    fields.device_id = fixed<16>(hex(field(*root, "device_id")));
    fields.boot_id = fixed<16>(hex(field(*root, "boot_id")));
    fields.slot_id = fixed<16>(hex(field(*root, "slot_id")));
    fields.browser_public_key = fixed<32>(b64u(field(*root, "browser_public_key")));
    fields.pico_public_key = expected_public;
    fields.request_nonce = fixed<16>(hex(field(*root, "request_nonce")));
    fields.request_id = fixed<16>(hex(field(*root, "request_id")));
    const auto nonce = fixed<12>(b64u(field(*root, "aead_nonce")));
    const auto ciphertext = b64u(field(*root, "ciphertext"));
    const auto tag = fixed<16>(b64u(field(*root, "tag")));
    const auto expected_ack = fixed<32>(b64u(field(*root, "ack_tag")));

    PicoBootstrapCrypto crypto;
    assert(crypto.begin_for_test(private_key));
    assert(crypto.public_key() == expected_public);
    std::string ssid, password, time_server;
    std::array<std::uint8_t, 32> ack{};
    assert(crypto.open(fields, nonce, ciphertext, tag, ssid, password, time_server, ack));
    assert(ssid == "LabNet" && password == "test-only-password" && time_server == "pool.ntp.org");
    assert(ack == expected_ack);
    assert(!crypto.open(fields, nonce, ciphertext, tag, ssid, password, time_server, ack));
    assert(ssid.empty() && password.empty() && time_server.empty());

    // The browser's extended sealed payload carries the selected server.
    const auto extended_body = b64u("FJTGUpCIDXYs7-VUUQFFmyqG1ZUYQ9izbcZY10fTV6sJ_HtGa3WmsYxv8Q");
    const auto extended_tag = fixed<16>(b64u("HII10AR1dDkiyuRlftsVQw"));
    PicoBootstrapCrypto extended;
    assert(extended.begin_for_test(private_key));
    assert(extended.open(fields, nonce, extended_body, extended_tag, ssid, password, time_server,
                         ack));
    assert(ssid == "LabNet" && password == "test-only-password" &&
           time_server == "time.example.org" && ack == expected_ack);

    auto rejects = [&](BootstrapTranscriptFields altered, std::array<std::uint8_t, 12> n,
                       std::array<std::uint8_t, 16> t) {
        PicoBootstrapCrypto attempt;
        assert(attempt.begin_for_test(private_key));
        assert(!attempt.open(altered, n, ciphertext, t, ssid, password, time_server, ack));
        assert(ssid.empty() && password.empty());
        assert(std::all_of(ack.begin(), ack.end(), [](std::uint8_t c) { return c == 0; }));
    };
    auto changed = fields;
    changed.device_id[0] ^= 1;
    rejects(changed, nonce, tag);
    changed = fields;
    changed.boot_id[0] ^= 1;
    rejects(changed, nonce, tag);
    changed = fields;
    changed.slot_id[0] ^= 1;
    rejects(changed, nonce, tag);
    changed = fields;
    changed.browser_public_key[0] ^= 1;
    rejects(changed, nonce, tag);
    changed = fields;
    changed.pico_public_key[0] ^= 1;
    rejects(changed, nonce, tag);
    changed = fields;
    changed.request_nonce[0] ^= 1;
    rejects(changed, nonce, tag);
    changed = fields;
    changed.request_id[0] ^= 1;
    rejects(changed, nonce, tag);
    auto bad_nonce = nonce;
    bad_nonce[0] ^= 1;
    rejects(fields, bad_nonce, tag);
    auto bad_tag = tag;
    bad_tag[0] ^= 1;
    rejects(fields, nonce, bad_tag);
    auto bad_ciphertext = ciphertext;
    bad_ciphertext[0] ^= 1;
    PicoBootstrapCrypto changed_body;
    assert(changed_body.begin_for_test(private_key));
    assert(
        !changed_body.open(fields, nonce, bad_ciphertext, tag, ssid, password, time_server, ack));
    assert(ssid.empty() && password.empty());
    assert(std::all_of(ack.begin(), ack.end(), [](std::uint8_t c) { return c == 0; }));
    changed = fields;
    changed.browser_public_key.fill(0);
    rejects(changed, nonce, tag);

    // An authenticated but invalid binary credential payload is still rejected.
    const auto key = fixed<32>(hex(field(*root, "hkdf_key_hex")));
    const auto aad = hex(field(*root, "transcript_hex"));
    std::array<std::uint8_t, 11> invalid_plain{}, invalid_cipher{};
    std::array<std::uint8_t, 16> invalid_tag{};
    mbedtls_chachapoly_context context;
    mbedtls_chachapoly_init(&context);
    assert(mbedtls_chachapoly_setkey(&context, key.data()) == 0);
    assert(mbedtls_chachapoly_encrypt_and_tag(&context, invalid_plain.size(), nonce.data(),
                                              aad.data(), aad.size(), invalid_plain.data(),
                                              invalid_cipher.data(), invalid_tag.data()) == 0);
    mbedtls_chachapoly_free(&context);
    PicoBootstrapCrypto malformed;
    assert(malformed.begin_for_test(private_key));
    assert(!malformed.open(fields, nonce, invalid_cipher, invalid_tag, ssid, password, time_server,
                           ack));
    assert(ssid.empty() && password.empty());
    assert(std::all_of(ack.begin(), ack.end(), [](std::uint8_t c) { return c == 0; }));
}

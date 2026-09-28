#include "network/pico/bootstrap_crypto.hpp"

#include "mbedtls/chachapoly.h"
#include "mbedtls/hkdf.h"
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"
#include "standalone/config.hpp"

#include <algorithm>
#include <array>
#include <cstring>

namespace wsprrypico::network {
namespace {
template <typename T> void erase(T& value) {
    volatile std::uint8_t* bytes = reinterpret_cast<volatile std::uint8_t*>(value.data());
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
}
void erase(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
bool printable(std::span<const std::uint8_t> value, std::size_t low, std::size_t high) {
    return value.size() >= low && value.size() <= high &&
           std::all_of(value.begin(), value.end(),
                       [](std::uint8_t c) { return c >= 32 && c <= 126; });
}
constexpr char transcript_prefix[] = "WsprryPico/WiFi-Bootstrap/1";
constexpr char hkdf_info[] = "WsprryPico network-only AEAD v1";
constexpr char ack_prefix[] = "WsprryPico network-only ACK v1";
constexpr std::size_t transcript_size = sizeof(transcript_prefix) + 16 * 5 + 32 * 2;

std::array<std::uint8_t, transcript_size> transcript(const BootstrapTranscriptFields& fields) {
    std::array<std::uint8_t, transcript_size> bytes{};
    std::size_t at = 0;
    auto append = [&](const void* source, std::size_t size) {
        std::memcpy(bytes.data() + at, source, size);
        at += size;
    };
    append(transcript_prefix, sizeof(transcript_prefix)); // Includes one NUL.
    append(fields.device_id.data(), fields.device_id.size());
    append(fields.boot_id.data(), fields.boot_id.size());
    append(fields.slot_id.data(), fields.slot_id.size());
    append(fields.browser_public_key.data(), fields.browser_public_key.size());
    append(fields.pico_public_key.data(), fields.pico_public_key.size());
    append(fields.request_nonce.data(), fields.request_nonce.size());
    append(fields.request_id.data(), fields.request_id.size());
    return bytes;
}
} // namespace

bool PicoBootstrapCrypto::create(std::span<const std::uint8_t> private_key) {
    clear();
    if (psa_.acquire() != PSA_SUCCESS)
        return false;
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_type(&attributes, PSA_KEY_TYPE_ECC_KEY_PAIR(PSA_ECC_FAMILY_MONTGOMERY));
    psa_set_key_bits(&attributes, 255);
    psa_set_key_usage_flags(&attributes, PSA_KEY_USAGE_DERIVE);
    psa_set_key_algorithm(&attributes, PSA_ALG_ECDH);
    const auto result = private_key.empty() ? psa_generate_key(&attributes, &private_key_)
                                            : psa_import_key(&attributes, private_key.data(),
                                                             private_key.size(), &private_key_);
    psa_reset_key_attributes(&attributes);
    std::size_t public_size = 0;
    if (result != PSA_SUCCESS ||
        psa_export_public_key(private_key_, public_key_.data(), public_key_.size(), &public_size) !=
            PSA_SUCCESS ||
        public_size != public_key_.size()) {
        clear();
        return false;
    }
    return true;
}

bool PicoBootstrapCrypto::begin() {
    return create({});
}
#ifdef WSPRRY_PICO_BOOTSTRAP_CRYPTO_TEST
bool PicoBootstrapCrypto::begin_for_test(std::span<const std::uint8_t, 32> private_key) {
    return create(private_key);
}
#endif

bool PicoBootstrapCrypto::open(const BootstrapTranscriptFields& fields,
                               std::span<const std::uint8_t, 12> nonce,
                               std::span<const std::uint8_t> ciphertext,
                               std::span<const std::uint8_t, 16> tag, std::string& ssid,
                               std::string& password, std::string& time_server,
                               std::array<std::uint8_t, 32>& ack_verifier) {
    erase(ssid);
    erase(password);
    erase(time_server);
    erase(ack_verifier);
    if (!private_key_ || ciphertext.size() < 11 || ciphertext.size() > 351 ||
        fields.pico_public_key != public_key_) {
        clear();
        return false;
    }
    std::array<std::uint8_t, 32> shared{}, salt{}, key{};
    std::array<std::uint8_t, 351> plain{};
    std::array<std::uint8_t, sizeof(ack_prefix) - 1 + transcript_size> ack_input{};
    const auto aad = transcript(fields);
    std::size_t shared_size = 0;
    const auto agreed = psa_raw_key_agreement(
        PSA_ALG_ECDH, private_key_, fields.browser_public_key.data(),
        fields.browser_public_key.size(), shared.data(), shared.size(), &shared_size);
    // A submission consumes the ephemeral key regardless of its outcome.
    const auto destroyed = psa_destroy_key(private_key_) == PSA_SUCCESS;
    if (destroyed)
        private_key_ = 0;
    const auto* md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    bool valid = destroyed && agreed == PSA_SUCCESS && shared_size == shared.size() &&
                 std::any_of(shared.begin(), shared.end(), [](std::uint8_t b) { return b; }) &&
                 md && mbedtls_sha256(aad.data(), aad.size(), salt.data(), 0) == 0 &&
                 mbedtls_hkdf(md, salt.data(), salt.size(), shared.data(), shared.size(),
                              reinterpret_cast<const unsigned char*>(hkdf_info),
                              sizeof(hkdf_info) - 1, key.data(), key.size()) == 0;
    if (valid) {
        mbedtls_chachapoly_context context;
        mbedtls_chachapoly_init(&context);
        valid = mbedtls_chachapoly_setkey(&context, key.data()) == 0 &&
                mbedtls_chachapoly_auth_decrypt(&context, ciphertext.size(), nonce.data(),
                                                aad.data(), aad.size(), tag.data(),
                                                ciphertext.data(), plain.data()) == 0;
        mbedtls_chachapoly_free(&context);
    }
    if (valid) {
        const auto ssid_size = plain[0];
        if (ssid_size >= 1 && ssid_size <= 32 && 1 + ssid_size < ciphertext.size()) {
            const auto password_size = plain[1 + ssid_size];
            const auto after_password = 2 + ssid_size + password_size;
            valid =
                after_password <= ciphertext.size() && password_size >= 8 && password_size <= 63;
            if (valid) {
                auto ssid_bytes = std::span(plain).subspan(1, ssid_size);
                auto password_bytes = std::span(plain).subspan(2 + ssid_size, password_size);
                valid = printable(ssid_bytes, 1, 32) && printable(password_bytes, 8, 63);
                if (valid && after_password == ciphertext.size())
                    time_server = standalone::default_time_server; // Historical v1 payload.
                else if (valid && after_password < ciphertext.size()) {
                    const auto length = plain[after_password];
                    valid = length > 0 && after_password + 1 + length == ciphertext.size();
                    if (valid) {
                        auto bytes = std::span(plain).subspan(after_password + 1, length);
                        time_server.assign(reinterpret_cast<const char*>(bytes.data()),
                                           bytes.size());
                        valid = standalone::valid_time_server(time_server);
                    }
                }
                if (valid) {
                    ssid.assign(reinterpret_cast<const char*>(ssid_bytes.data()),
                                ssid_bytes.size());
                    password.assign(reinterpret_cast<const char*>(password_bytes.data()),
                                    password_bytes.size());
                }
            }
        } else
            valid = false;
    }
    if (valid) {
        std::memcpy(ack_input.data(), ack_prefix, sizeof(ack_prefix) - 1);
        std::memcpy(ack_input.data() + sizeof(ack_prefix) - 1, aad.data(), aad.size());
        valid = mbedtls_md_hmac(md, key.data(), key.size(), ack_input.data(), ack_input.size(),
                                ack_verifier.data()) == 0;
    }
    erase(shared);
    erase(salt);
    erase(key);
    erase(plain);
    erase(ack_input);
    clear();
    if (!valid) {
        erase(ssid);
        erase(password);
        erase(time_server);
        erase(ack_verifier);
    }
    return valid;
}

void PicoBootstrapCrypto::clear() {
    if (private_key_) {
        (void)psa_destroy_key(private_key_);
        private_key_ = 0;
    }
    erase(public_key_);
    psa_.release();
}
} // namespace wsprrypico::network

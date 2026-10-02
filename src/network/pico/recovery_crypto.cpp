#include "network/pico/recovery_crypto.hpp"

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
constexpr char transcript_prefix[] = "WsprryPico/Recovery/1";
constexpr char hkdf_info[] = "WsprryPico recovery AEAD v1";
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

bool PicoRecoveryCrypto::create(std::span<const std::uint8_t> private_key) {
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

bool PicoRecoveryCrypto::begin() {
    return create({});
}
#ifdef WSPRRY_PICO_RECOVERY_CRYPTO_TEST
bool PicoRecoveryCrypto::begin_for_test(std::span<const std::uint8_t, 32> private_key) {
    return create(private_key);
}
#endif

bool PicoRecoveryCrypto::open(const BootstrapTranscriptFields& fields,
                              std::span<const std::uint8_t, 12> nonce,
                              std::span<const std::uint8_t> ciphertext,
                              std::span<const std::uint8_t, 16> tag, std::string& command) {
    erase(command);
    if (!private_key_ || ciphertext.size() < 9 || ciphertext.size() > 22 ||
        fields.pico_public_key != public_key_) {
        clear();
        return false;
    }
    std::array<std::uint8_t, 32> shared{}, salt{}, key{};
    std::array<std::uint8_t, 22> plain{};
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
        command.assign(reinterpret_cast<const char*>(plain.data()), ciphertext.size());
        valid = command == "1:1:erase" || command == "1:1:reset provisioning";
    }
    erase(shared);
    erase(salt);
    erase(key);
    erase(plain);
    clear();
    if (!valid)
        erase(command);
    return valid;
}

void PicoRecoveryCrypto::clear() {
    if (private_key_) {
        (void)psa_destroy_key(private_key_);
        private_key_ = 0;
    }
    erase(public_key_);
    psa_.release();
}
} // namespace wsprrypico::network

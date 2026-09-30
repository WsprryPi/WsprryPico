#include "network/pico/owner_claim_crypto.hpp"

#include "mbedtls/chachapoly.h"
#include "mbedtls/hkdf.h"
#include "mbedtls/md.h"
#include "mbedtls/sha256.h"

#include <algorithm>
#include <array>

namespace wsprrypico::network {
namespace {
constexpr char hkdf_info[] = "WsprryPico owner claim AEAD v1";

template <typename T> void erase(T& value) {
    volatile std::uint8_t* bytes = value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
}
void erase(std::string& value) {
    volatile char* bytes = value.empty() ? nullptr : value.data();
    for (std::size_t i = 0; i < value.size(); ++i)
        bytes[i] = 0;
    std::string{}.swap(value);
}
} // namespace

void OwnerClaimCredentials::clear() {
    erase(ssid);
    erase(password);
    erase(callsign);
    erase(locator);
    power_dbm = 0;
}

bool PicoOwnerClaimCrypto::create(std::span<const std::uint8_t> private_key) {
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

bool PicoOwnerClaimCrypto::begin() {
    return create({});
}
#ifdef WSPRRY_PICO_OWNER_CLAIM_CRYPTO_TEST
bool PicoOwnerClaimCrypto::begin_for_test(std::span<const std::uint8_t, 32> private_key) {
    return create(private_key);
}
#endif

bool PicoOwnerClaimCrypto::open(const OwnerClaimFields& fields,
                                std::span<const std::uint8_t, 12> nonce,
                                std::span<const std::uint8_t> ciphertext,
                                std::span<const std::uint8_t, 16> tag, OwnerClaimCredentials& out) {
    out.clear();
    const auto aad = owner_claim_transcript(fields);
    if (!private_key_ || !aad || fields.pico_public_key != public_key_ || ciphertext.size() < 11 ||
        ciphertext.size() > OwnerClaimEncodedPlaintext::max_size) {
        clear();
        return false;
    }
    std::array<std::uint8_t, 32> shared{}, salt{}, key{};
    std::array<std::uint8_t, OwnerClaimEncodedPlaintext::max_size> plain{};
    std::size_t shared_size = 0;
    const auto agreed = psa_raw_key_agreement(
        PSA_ALG_ECDH, private_key_, fields.browser_public_key.data(),
        fields.browser_public_key.size(), shared.data(), shared.size(), &shared_size);
    const auto destroyed = psa_destroy_key(private_key_) == PSA_SUCCESS;
    if (destroyed)
        private_key_ = 0;
    const auto* md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    bool valid = destroyed && agreed == PSA_SUCCESS && shared_size == shared.size() &&
                 std::any_of(shared.begin(), shared.end(), [](std::uint8_t b) { return b; }) &&
                 md && mbedtls_sha256(aad->bytes.data(), aad->size, salt.data(), 0) == 0 &&
                 mbedtls_hkdf(md, salt.data(), salt.size(), shared.data(), shared.size(),
                              reinterpret_cast<const unsigned char*>(hkdf_info),
                              sizeof(hkdf_info) - 1, key.data(), key.size()) == 0;
    if (valid) {
        mbedtls_chachapoly_context context;
        mbedtls_chachapoly_init(&context);
        valid = mbedtls_chachapoly_setkey(&context, key.data()) == 0 &&
                mbedtls_chachapoly_auth_decrypt(&context, ciphertext.size(), nonce.data(),
                                                aad->bytes.data(), aad->size, tag.data(),
                                                ciphertext.data(), plain.data()) == 0;
        mbedtls_chachapoly_free(&context);
    }
    if (valid) {
        const auto parsed = decode_owner_claim_plaintext(
            std::span<const std::uint8_t>(plain.data(), ciphertext.size()));
        valid = parsed.has_value();
        if (valid) {
            out.ssid = parsed->ssid;
            out.password = parsed->password;
            out.callsign = parsed->callsign;
            out.locator = parsed->locator;
            out.power_dbm = parsed->power_dbm;
        }
    }
    erase(shared);
    erase(salt);
    erase(key);
    erase(plain);
    clear();
    if (!valid)
        out.clear();
    return valid;
}

void PicoOwnerClaimCrypto::clear() {
    if (private_key_) {
        (void)psa_destroy_key(private_key_);
        private_key_ = 0;
    }
    erase(public_key_);
    psa_.release();
}

} // namespace wsprrypico::network

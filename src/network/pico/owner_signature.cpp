#include "network/pico/owner_signature.hpp"

#include "network/pico/psa_lifetime.hpp"

#include <algorithm>
#include <array>

namespace wsprrypico::network {
namespace {
constexpr std::array<std::uint8_t, 32> order{{
    0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xbc, 0xe6, 0xfa, 0xad, 0xa7, 0x17, 0x9e, 0x84, 0xf3, 0xb9, 0xca, 0xc2, 0xfc, 0x63, 0x25, 0x51,
}};
constexpr std::array<std::uint8_t, 32> half_order{{
    0x7f, 0xff, 0xff, 0xff, 0x80, 0x00, 0x00, 0x00, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
    0xde, 0x73, 0x7d, 0x56, 0xd3, 0x8b, 0xcf, 0x42, 0x79, 0xdc, 0xe5, 0x61, 0x7e, 0x31, 0x92, 0xa8,
}};
bool scalar(std::span<const std::uint8_t, 32> value, bool low_s) {
    if (std::all_of(value.begin(), value.end(), [](std::uint8_t b) { return b == 0; }))
        return false;
    if (low_s)
        return !std::lexicographical_compare(half_order.begin(), half_order.end(), value.begin(),
                                             value.end());
    return std::lexicographical_compare(value.begin(), value.end(), order.begin(), order.end());
}
} // namespace

bool valid_owner_public_key(std::span<const std::uint8_t, 65> public_key) {
    if (public_key[0] != 4)
        return false;
    PsaCryptoOwner psa;
    if (psa.acquire() != PSA_SUCCESS)
        return false;
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_type(&attributes, PSA_KEY_TYPE_ECC_PUBLIC_KEY(PSA_ECC_FAMILY_SECP_R1));
    psa_set_key_bits(&attributes, 256);
    psa_set_key_usage_flags(&attributes, PSA_KEY_USAGE_VERIFY_HASH);
    psa_set_key_algorithm(&attributes, PSA_ALG_ECDSA(PSA_ALG_SHA_256));
    psa_key_id_t key = 0;
    const auto imported = psa_import_key(&attributes, public_key.data(), public_key.size(), &key);
    psa_reset_key_attributes(&attributes);
    if (imported != PSA_SUCCESS)
        return false;
    std::array<std::uint8_t, 65> exported{};
    std::size_t exported_size = 0;
    const bool canonical = psa_export_public_key(key, exported.data(), exported.size(),
                                                 &exported_size) == PSA_SUCCESS &&
                           exported_size == exported.size() &&
                           std::equal(exported.begin(), exported.end(), public_key.begin());
    return psa_destroy_key(key) == PSA_SUCCESS && canonical;
}

bool verify_owner_signature(std::span<const std::uint8_t, 65> public_key,
                            std::span<const std::uint8_t, 32> digest,
                            std::span<const std::uint8_t, 64> signature) {
    if (public_key[0] != 4 || !scalar(signature.first<32>(), false) ||
        !scalar(signature.last<32>(), true))
        return false;
    PsaCryptoOwner psa;
    if (psa.acquire() != PSA_SUCCESS)
        return false;
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_type(&attributes, PSA_KEY_TYPE_ECC_PUBLIC_KEY(PSA_ECC_FAMILY_SECP_R1));
    psa_set_key_bits(&attributes, 256);
    psa_set_key_usage_flags(&attributes, PSA_KEY_USAGE_VERIFY_HASH);
    psa_set_key_algorithm(&attributes, PSA_ALG_ECDSA(PSA_ALG_SHA_256));
    psa_key_id_t key = 0;
    const auto imported = psa_import_key(&attributes, public_key.data(), public_key.size(), &key);
    psa_reset_key_attributes(&attributes);
    if (imported != PSA_SUCCESS)
        return false;
    std::array<std::uint8_t, 65> exported{};
    std::size_t exported_size = 0;
    const bool canonical = psa_export_public_key(key, exported.data(), exported.size(),
                                                 &exported_size) == PSA_SUCCESS &&
                           exported_size == exported.size() &&
                           std::equal(exported.begin(), exported.end(), public_key.begin());
    const bool valid = canonical && psa_verify_hash(key, PSA_ALG_ECDSA(PSA_ALG_SHA_256),
                                                    digest.data(), digest.size(), signature.data(),
                                                    signature.size()) == PSA_SUCCESS;
    return psa_destroy_key(key) == PSA_SUCCESS && valid;
}

} // namespace wsprrypico::network

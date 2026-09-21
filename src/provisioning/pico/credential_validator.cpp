#include "provisioning/pico/credential_validator.hpp"

#include "mbedtls/ctr_drbg.h"
#include "mbedtls/entropy.h"
#include "mbedtls/oid.h"
#include "mbedtls/pk.h"
#include "mbedtls/x509_crt.h"
#include "network/identity.hpp"
#include "psa/crypto.h"

#include <string_view>

namespace wsprrypico::provisioning {
namespace {
constexpr int identity_error = -0x7f01;
constexpr int hostname_san_error = -0x7f02;
constexpr int algorithm_error = -0x7f03;
constexpr int purpose_error = -0x7f04;

bool exact_dns_san(const mbedtls_x509_crt& certificate, std::string_view expected) {
    for (auto* entry = &certificate.subject_alt_names; entry && entry->buf.p;
         entry = entry->next) {
        mbedtls_x509_subject_alternative_name parsed{};
        const auto result = mbedtls_x509_parse_subject_alt_name(&entry->buf, &parsed);
        const bool match =
            result == 0 && parsed.type == MBEDTLS_X509_SAN_DNS_NAME &&
            std::string_view(reinterpret_cast<const char*>(parsed.san.unstructured_name.p),
                             parsed.san.unstructured_name.len) == expected;
        if (result == 0)
            mbedtls_x509_free_subject_alt_name(&parsed);
        if (match)
            return true;
    }
    return false;
}

bool p256_key(const mbedtls_pk_context& key) {
    const auto type = mbedtls_pk_get_type(&key);
    if (type != MBEDTLS_PK_ECKEY && type != MBEDTLS_PK_ECDSA)
        return false;
    const auto* ec = mbedtls_pk_ec(key);
    return ec && mbedtls_ecp_keypair_get_group_id(ec) == MBEDTLS_ECP_DP_SECP256R1;
}

bool p256_sha256_certificate(const mbedtls_x509_crt& certificate) {
    return certificate.MBEDTLS_PRIVATE(sig_md) == MBEDTLS_MD_SHA256 &&
           certificate.MBEDTLS_PRIVATE(sig_pk) == MBEDTLS_PK_ECDSA &&
           p256_key(certificate.pk);
}

struct Context {
    mbedtls_x509_crt certificate{};
    mbedtls_x509_crt ca{};
    mbedtls_pk_context key{};
    mbedtls_entropy_context entropy{};
    mbedtls_ctr_drbg_context rng{};
    Context() {
        mbedtls_x509_crt_init(&certificate);
        mbedtls_x509_crt_init(&ca);
        mbedtls_pk_init(&key);
        mbedtls_entropy_init(&entropy);
        mbedtls_ctr_drbg_init(&rng);
    }
    ~Context() {
        mbedtls_x509_crt_free(&certificate);
        mbedtls_x509_crt_free(&ca);
        mbedtls_pk_free(&key);
        mbedtls_ctr_drbg_free(&rng);
        mbedtls_entropy_free(&entropy);
        mbedtls_psa_crypto_free();
    }
};
} // namespace

bool MbedTlsCredentialValidator::validate(const Profile& profile) {
    return validate(credentials(profile));
}

bool MbedTlsCredentialValidator::validate(CredentialMaterial material) {
    last_error_ = 0;
    verify_flags_ = 0;
    if (!network::valid_device_id(expected_device_id_) ||
        material.device_id != expected_device_id_ || !material.port || material.port > 65535 ||
        !network::canonical_local_hostname(material.hostname) || material.server_certificate.empty() ||
        material.server_private_key.empty() || material.client_ca.empty()) {
        last_error_ = identity_error;
        return false;
    }
    Context context;
    const unsigned char personalization[] = "WsprryPico credential validator";
    auto check = [this](int result) {
        if (result && !last_error_)
            last_error_ = result;
        return result != 0;
    };
    if (check(psa_crypto_init()) ||
        check(mbedtls_ctr_drbg_seed(&context.rng, mbedtls_entropy_func, &context.entropy,
                                    personalization, sizeof(personalization))) ||
        check(mbedtls_x509_crt_parse(
            &context.certificate,
            reinterpret_cast<const unsigned char*>(material.server_certificate.data()),
            material.server_certificate.size() + 1)) ||
        check(mbedtls_x509_crt_parse(&context.ca,
                                     reinterpret_cast<const unsigned char*>(material.client_ca.data()),
                                     material.client_ca.size() + 1)) ||
        check(mbedtls_pk_parse_key(
            &context.key,
            reinterpret_cast<const unsigned char*>(material.server_private_key.data()),
            material.server_private_key.size() + 1, nullptr, 0, mbedtls_ctr_drbg_random,
            &context.rng)) ||
        check(mbedtls_pk_check_pair(&context.certificate.pk, &context.key,
                                    mbedtls_ctr_drbg_random, &context.rng)))
        return false;
    if (context.certificate.next || context.ca.next ||
        !p256_sha256_certificate(context.certificate) ||
        !p256_sha256_certificate(context.ca) || !p256_key(context.key)) {
        last_error_ = algorithm_error;
        return false;
    }
    if (!exact_dns_san(context.certificate, material.hostname)) {
        last_error_ = hostname_san_error;
        return false;
    }
    if (mbedtls_x509_crt_check_extended_key_usage(
            &context.certificate, MBEDTLS_OID_SERVER_AUTH,
            MBEDTLS_OID_SIZE(MBEDTLS_OID_SERVER_AUTH)) != 0) {
        last_error_ = purpose_error;
        return false;
    }
    const std::string hostname(material.hostname);
    last_error_ = mbedtls_x509_crt_verify_with_profile(
        &context.certificate, &context.ca, nullptr, &mbedtls_x509_crt_profile_suiteb,
        hostname.c_str(), &verify_flags_, nullptr, nullptr);
    return last_error_ == 0 && verify_flags_ == 0;
}
} // namespace wsprrypico::provisioning

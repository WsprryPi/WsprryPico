#include "provisioning/pico/consumer_tls_validator.hpp"

#include "mbedtls/ctr_drbg.h"
#include "mbedtls/ecp.h"
#include "mbedtls/entropy.h"
#include "mbedtls/md.h"
#include "mbedtls/oid.h"
#include "mbedtls/pk.h"
#include "mbedtls/x509_crt.h"
#include "network/identity.hpp"
#include "network/pico/psa_lifetime.hpp"
#include "provisioning/pico/credential_validator.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <string>
#include <string_view>

namespace wsprrypico::provisioning {
namespace {
using namespace std::chrono;

struct Context {
    mbedtls_x509_crt ca{}, server{};
    mbedtls_pk_context ca_key{}, server_key{};
    mbedtls_entropy_context entropy{};
    mbedtls_ctr_drbg_context rng{};
    Context() {
        mbedtls_x509_crt_init(&ca);
        mbedtls_x509_crt_init(&server);
        mbedtls_pk_init(&ca_key);
        mbedtls_pk_init(&server_key);
        mbedtls_entropy_init(&entropy);
        mbedtls_ctr_drbg_init(&rng);
    }
    ~Context() {
        mbedtls_ctr_drbg_free(&rng);
        mbedtls_entropy_free(&entropy);
        mbedtls_pk_free(&server_key);
        mbedtls_pk_free(&ca_key);
        mbedtls_x509_crt_free(&server);
        mbedtls_x509_crt_free(&ca);
    }
};

bool p256(const mbedtls_pk_context& key) {
    const auto type = mbedtls_pk_get_type(&key);
    if (type != MBEDTLS_PK_ECKEY && type != MBEDTLS_PK_ECDSA)
        return false;
    const auto* ec = mbedtls_pk_ec(key);
    return ec && mbedtls_ecp_keypair_get_group_id(ec) == MBEDTLS_ECP_DP_SECP256R1;
}

bool signature(const mbedtls_x509_crt& certificate) {
    return certificate.MBEDTLS_PRIVATE(sig_md) == MBEDTLS_MD_SHA256 &&
           certificate.MBEDTLS_PRIVATE(sig_pk) == MBEDTLS_PK_ECDSA && p256(certificate.pk);
}

bool name_field(const mbedtls_x509_name& name, std::string_view oid, std::string_view value) {
    unsigned count = 0;
    for (auto* entry = &name; entry; entry = entry->next) {
        if (std::string_view(reinterpret_cast<const char*>(entry->oid.p), entry->oid.len) == oid) {
            if (std::string_view(reinterpret_cast<const char*>(entry->val.p), entry->val.len) !=
                value)
                return false;
            ++count;
        }
    }
    return count == 1;
}

bool exact_san(const mbedtls_x509_crt& certificate, std::string_view hostname) {
    const auto* entry = &certificate.subject_alt_names;
    if (!entry->buf.p || entry->next)
        return false;
    mbedtls_x509_subject_alternative_name parsed{};
    const auto result = mbedtls_x509_parse_subject_alt_name(&entry->buf, &parsed);
    const bool matches =
        result == 0 && parsed.type == MBEDTLS_X509_SAN_DNS_NAME &&
        std::string_view(reinterpret_cast<const char*>(parsed.san.unstructured_name.p),
                         parsed.san.unstructured_name.len) == hostname;
    if (result == 0)
        mbedtls_x509_free_subject_alt_name(&parsed);
    return matches;
}

bool epoch(const mbedtls_x509_time& time, std::uint64_t& result) {
    const year_month_day ymd{year{time.year}, month{static_cast<unsigned>(time.mon)},
                             day{static_cast<unsigned>(time.day)}};
    if (!ymd.ok() || time.hour < 0 || time.hour > 23 || time.min < 0 || time.min > 59 ||
        time.sec < 0 || time.sec > 59)
        return false;
    const auto point = sys_days{ymd} + hours{time.hour} + minutes{time.min} + seconds{time.sec};
    const auto count = duration_cast<seconds>(point.time_since_epoch()).count();
    if (count < 0)
        return false;
    result = static_cast<std::uint64_t>(count);
    return true;
}

bool serial(const mbedtls_x509_crt& certificate) {
    return certificate.serial.p && certificate.serial.len && certificate.serial.len <= 20 &&
           std::any_of(certificate.serial.p, certificate.serial.p + certificate.serial.len,
                       [](unsigned char byte) { return byte != 0; });
}
} // namespace

bool validate_consumer_tls(const ConsumerTls& tls, std::string_view device_id,
                           std::uint64_t utc_now) {
    const auto canonical = network::canonical_local_hostname(tls.hostname);
    if (!network::valid_device_id(device_id) || !canonical || *canonical != tls.hostname ||
        tls.port != 443 || !utc_now || tls.ca_certificate.empty() ||
        tls.server_certificate.empty() || tls.ca_private_key.empty() ||
        tls.server_private_key.empty() || !tls.ca_not_after_utc || !tls.server_not_after_utc ||
        tls.server_not_after_utc > tls.ca_not_after_utc || tls.ca_certificate.size() > 1200 ||
        tls.server_certificate.size() > 1200 || tls.ca_private_key.size() > 512 ||
        tls.server_private_key.size() > 512 ||
        tls.ca_certificate.size() + tls.server_certificate.size() + tls.ca_private_key.size() +
                tls.server_private_key.size() >
            2304)
        return false;
    network::PsaCryptoOwner psa;
    if (psa.acquire() != PSA_SUCCESS)
        return false;
    Context context;
    constexpr unsigned char personalization[] = "WsprryPico consumer validation v1";
    if (mbedtls_ctr_drbg_seed(&context.rng, mbedtls_entropy_func, &context.entropy, personalization,
                              sizeof(personalization) - 1) != 0 ||
        mbedtls_x509_crt_parse(&context.ca,
                               reinterpret_cast<const unsigned char*>(tls.ca_certificate.c_str()),
                               tls.ca_certificate.size() + 1) != 0 ||
        mbedtls_x509_crt_parse(
            &context.server, reinterpret_cast<const unsigned char*>(tls.server_certificate.c_str()),
            tls.server_certificate.size() + 1) != 0 ||
        mbedtls_pk_parse_key(&context.ca_key,
                             reinterpret_cast<const unsigned char*>(tls.ca_private_key.c_str()),
                             tls.ca_private_key.size() + 1, nullptr, 0, mbedtls_ctr_drbg_random,
                             &context.rng) != 0 ||
        mbedtls_pk_parse_key(&context.server_key,
                             reinterpret_cast<const unsigned char*>(tls.server_private_key.c_str()),
                             tls.server_private_key.size() + 1, nullptr, 0, mbedtls_ctr_drbg_random,
                             &context.rng) != 0 ||
        mbedtls_pk_check_pair(&context.ca.pk, &context.ca_key, mbedtls_ctr_drbg_random,
                              &context.rng) != 0 ||
        mbedtls_pk_check_pair(&context.server.pk, &context.server_key, mbedtls_ctr_drbg_random,
                              &context.rng) != 0)
        return false;
    auto& ca = context.ca;
    const auto& server = context.server;
    const std::string ca_cn = "WsprryPico Device CA";
    if (ca.next || server.next || !signature(ca) || !signature(server) || !p256(context.ca_key) ||
        !p256(context.server_key) || !mbedtls_x509_crt_get_ca_istrue(&ca) ||
        mbedtls_x509_crt_get_ca_istrue(&server) ||
        ca.MBEDTLS_PRIVATE(key_usage) != MBEDTLS_X509_KU_KEY_CERT_SIGN ||
        server.MBEDTLS_PRIVATE(key_usage) != MBEDTLS_X509_KU_DIGITAL_SIGNATURE ||
        !name_field(ca.subject, MBEDTLS_OID_AT_CN, ca_cn) ||
        !name_field(ca.subject, MBEDTLS_OID_AT_ORG_UNIT, device_id) ||
        !name_field(ca.issuer, MBEDTLS_OID_AT_CN, ca_cn) ||
        !name_field(ca.issuer, MBEDTLS_OID_AT_ORG_UNIT, device_id) ||
        !name_field(server.subject, MBEDTLS_OID_AT_CN, tls.hostname) ||
        !name_field(server.subject, MBEDTLS_OID_AT_ORG_UNIT, device_id) ||
        !name_field(server.issuer, MBEDTLS_OID_AT_CN, ca_cn) ||
        !name_field(server.issuer, MBEDTLS_OID_AT_ORG_UNIT, device_id) ||
        !exact_san(server, tls.hostname) || !serial(ca) || !serial(server) ||
        (ca.serial.len == server.serial.len &&
         std::equal(ca.serial.p, ca.serial.p + ca.serial.len, server.serial.p)) ||
        mbedtls_x509_crt_check_extended_key_usage(&server, MBEDTLS_OID_SERVER_AUTH,
                                                  MBEDTLS_OID_SIZE(MBEDTLS_OID_SERVER_AUTH)) != 0)
        return false;
    std::uint64_t ca_from = 0, ca_to = 0, server_from = 0, server_to = 0;
    if (!epoch(ca.valid_from, ca_from) || !epoch(ca.valid_to, ca_to) ||
        !epoch(server.valid_from, server_from) || !epoch(server.valid_to, server_to) ||
        ca_from > utc_now || server_from > utc_now || utc_now >= ca_to || utc_now >= server_to ||
        ca_to != tls.ca_not_after_utc || server_to != tls.server_not_after_utc || server_to > ca_to)
        return false;
    std::array<unsigned char, 32> digest{};
    const auto* sha256 = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    if (!sha256 || mbedtls_md(sha256, ca.tbs.p, ca.tbs.len, digest.data()) != 0 ||
        mbedtls_pk_verify(&ca.pk, MBEDTLS_MD_SHA256, digest.data(), digest.size(),
                          ca.MBEDTLS_PRIVATE(sig).p, ca.MBEDTLS_PRIVATE(sig).len) != 0)
        return false;
    const auto ignore_platform_time = [](void*, mbedtls_x509_crt*, int, std::uint32_t* flags) {
        *flags &= ~(MBEDTLS_X509_BADCERT_EXPIRED | MBEDTLS_X509_BADCERT_FUTURE);
        return 0;
    };
    std::uint32_t root_flags = 0;
    if (mbedtls_x509_crt_verify_with_profile(&ca, &ca, nullptr, &mbedtls_x509_crt_profile_suiteb,
                                             nullptr, &root_flags, ignore_platform_time,
                                             nullptr) != 0 ||
        root_flags != 0)
        return false;
    MbedTlsCredentialValidator chain{std::string(device_id)};
    return chain.validate_for_server_boot({device_id, tls.hostname, tls.port,
                                           tls.server_certificate, tls.server_private_key,
                                           tls.ca_certificate});
}
} // namespace wsprrypico::provisioning

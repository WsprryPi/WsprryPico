#include "mbedtls/base64.h"
#include "mbedtls/oid.h"
#include "mbedtls/platform.h"
#include "mbedtls/x509_crt.h"
#include "network/identity.hpp"
#include "provisioning/pico/consumer_tls_generator.hpp"
#include "provisioning/pico/consumer_tls_validator.hpp"
#include "provisioning/pico/credential_validator.hpp"

#include <cassert>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <random>
#include <string>
#include <string_view>
#include <vector>

using namespace wsprrypico;
static bool fail_entropy = false;

extern "C" mbedtls_ms_time_t mbedtls_ms_time(void) {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}
extern "C" int mbedtls_hardware_poll(void*, unsigned char* output, std::size_t count,
                                     std::size_t* received) {
    if (fail_entropy) {
        *received = 0;
        return -1;
    }
    std::random_device random;
    for (std::size_t i = 0; i < count; ++i)
        output[i] = static_cast<unsigned char>(random());
    *received = count;
    return 0;
}

namespace {
bool name_has(const mbedtls_x509_name& name, std::string_view oid, std::string_view value) {
    for (auto* item = &name; item; item = item->next) {
        if (std::string_view(reinterpret_cast<const char*>(item->oid.p), item->oid.len) == oid &&
            std::string_view(reinterpret_cast<const char*>(item->val.p), item->val.len) == value)
            return true;
    }
    return false;
}
std::string change_signature(std::string pem) {
    constexpr std::string_view begin = "-----BEGIN CERTIFICATE-----\n";
    constexpr std::string_view end = "\n-----END CERTIFICATE-----";
    const auto finish = pem.find(end);
    assert(pem.starts_with(begin) && finish != pem.npos);
    const auto encoded = pem.substr(begin.size(), finish - begin.size());
    std::vector<unsigned char> der(1200), rebuilt(2000);
    std::size_t length = 0, encoded_length = 0;
    assert(mbedtls_base64_decode(der.data(), der.size(), &length,
                                 reinterpret_cast<const unsigned char*>(encoded.data()),
                                 encoded.size()) == 0);
    assert(length > 8);
    der[length - 1] ^= 1;
    assert(mbedtls_base64_encode(rebuilt.data(), rebuilt.size(), &encoded_length, der.data(),
                                 length) == 0);
    return std::string(begin) +
           std::string(reinterpret_cast<const char*>(rebuilt.data()), encoded_length) +
           std::string(end) + "\n";
}
} // namespace

int main() {
    constexpr std::string_view device = "fd6127d11d6aca42a9905fa3fb1bf1d5";
    constexpr std::string_view host = "wsprrypico-0a60df.local";
    const auto now = static_cast<std::uint64_t>(std::time(nullptr));
    provisioning::ConsumerTls tls;
    assert(!provisioning::generate_consumer_tls("wrong", host, now, tls));
    assert(!provisioning::generate_consumer_tls(device, "wrong.local", 0, tls));
    assert(!provisioning::generate_consumer_tls(device, "Wsprrypico-0a60df.local", now, tls));
    assert(!provisioning::generate_consumer_tls(device, host, 3'471'292'800, tls));
    assert(provisioning::generate_consumer_tls(device, host, now, tls));
    assert(tls.hostname == host && tls.port == 443 &&
           tls.ca_not_after_utc > tls.server_not_after_utc &&
           tls.server_not_after_utc > now + 360 * 86400);
    assert(tls.ca_private_key != tls.server_private_key);
    assert(provisioning::validate_consumer_tls(tls, device, now));
    assert(!provisioning::validate_consumer_tls(tls, "00000000000000000000000000000000", now));
    assert(!provisioning::validate_consumer_tls(tls, device, tls.server_not_after_utc));
    mbedtls_x509_crt ca{}, server{};
    mbedtls_x509_crt_init(&ca);
    mbedtls_x509_crt_init(&server);
    assert(mbedtls_x509_crt_parse(
               &ca, reinterpret_cast<const unsigned char*>(tls.ca_certificate.c_str()),
               tls.ca_certificate.size() + 1) == 0);
    assert(mbedtls_x509_crt_parse(
               &server, reinterpret_cast<const unsigned char*>(tls.server_certificate.c_str()),
               tls.server_certificate.size() + 1) == 0);
    assert(mbedtls_x509_crt_get_ca_istrue(&ca) && !mbedtls_x509_crt_get_ca_istrue(&server) &&
           !ca.next && !server.next);
    assert(name_has(ca.subject, MBEDTLS_OID_AT_ORG_UNIT, device));
    assert(name_has(server.subject, MBEDTLS_OID_AT_ORG_UNIT, device));
    assert(name_has(server.subject, MBEDTLS_OID_AT_CN, host));
    assert(mbedtls_x509_crt_check_extended_key_usage(
               &server, MBEDTLS_OID_SERVER_AUTH, MBEDTLS_OID_SIZE(MBEDTLS_OID_SERVER_AUTH)) == 0);
    std::uint32_t root_flags = 0;
    assert(mbedtls_x509_crt_verify_with_profile(&ca, &ca, nullptr, &mbedtls_x509_crt_profile_suiteb,
                                                nullptr, &root_flags, nullptr, nullptr) == 0);
    assert(root_flags == 0);
    provisioning::MbedTlsCredentialValidator validator{std::string(device)};
    const provisioning::CredentialMaterial material{
        device, host, 443, tls.server_certificate, tls.server_private_key, tls.ca_certificate};
    assert(validator.validate(material));
    auto wrong = tls;
    wrong.server_private_key = tls.ca_private_key;
    assert(!provisioning::validate_consumer_tls(wrong, device, now));
    assert(!validator.validate({device, host, 443, wrong.server_certificate,
                                wrong.server_private_key, wrong.ca_certificate}));
    wrong = tls;
    wrong.server_not_after_utc += 1;
    assert(!provisioning::validate_consumer_tls(wrong, device, now));
    wrong = tls;
    wrong.ca_certificate = change_signature(tls.ca_certificate);
    assert(!provisioning::validate_consumer_tls(wrong, device, now));
    wrong = tls;
    wrong.server_certificate = change_signature(tls.server_certificate);
    assert(!provisioning::validate_consumer_tls(wrong, device, now));
    wrong = tls;
    wrong.hostname = "other.local";
    assert(!provisioning::validate_consumer_tls(wrong, device, now));
    assert(
        !validator.validate({"00000000000000000000000000000000", host, 443, tls.server_certificate,
                             tls.server_private_key, tls.ca_certificate}));
    const auto first_ca = tls.ca_certificate;
    assert(provisioning::generate_consumer_tls(device, host, now, tls));
    assert(tls.ca_certificate != first_ca);
    fail_entropy = true;
    assert(!provisioning::generate_consumer_tls(device, host, now, tls));
    fail_entropy = false;
    assert(tls.ca_private_key.empty() && tls.server_private_key.empty());
    assert(provisioning::generate_consumer_tls(device, host, 1'709'164'800, tls)); // Leap day.
    assert(tls.server_not_after_utc == 1'740'700'800);                             // 2025-02-28.
    assert(tls.ca_not_after_utc == 2'024'697'600);                                 // 2034-02-28.
    assert(!provisioning::generate_consumer_tls(device, host, 0, tls));
    assert(tls.ca_private_key.empty() && tls.server_private_key.empty() &&
           tls.ca_certificate.empty() && tls.server_certificate.empty());
    mbedtls_x509_crt_free(&server);
    mbedtls_x509_crt_free(&ca);
}

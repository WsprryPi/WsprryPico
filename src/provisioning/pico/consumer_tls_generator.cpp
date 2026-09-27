#include "provisioning/pico/consumer_tls_generator.hpp"

#include "mbedtls/asn1.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/ecp.h"
#include "mbedtls/entropy.h"
#include "mbedtls/oid.h"
#include "mbedtls/pk.h"
#include "mbedtls/x509_crt.h"
#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "network/pico/psa_lifetime.hpp"
#include "provisioning/pico/consumer_tls_validator.hpp"

#include <array>
#include <chrono>
#include <cstdio>
#include <string>

namespace wsprrypico::provisioning {
namespace {
using namespace std::chrono;
constexpr std::uint64_t earliest_utc = 1'704'067'200; // 2024-01-01
constexpr std::uint64_t latest_utc = 3'471'292'800;   // 2080-01-01

template <std::size_t N> void erase(std::array<unsigned char, N>& bytes) {
    volatile unsigned char* target = bytes.data();
    for (std::size_t i = 0; i < N; ++i)
        target[i] = 0;
}

struct Context {
    mbedtls_entropy_context entropy{};
    mbedtls_ctr_drbg_context rng{};
    mbedtls_pk_context ca_key{}, server_key{};
    mbedtls_x509write_cert ca_cert{}, server_cert{};
    Context() {
        mbedtls_entropy_init(&entropy);
        mbedtls_ctr_drbg_init(&rng);
        mbedtls_pk_init(&ca_key);
        mbedtls_pk_init(&server_key);
        mbedtls_x509write_crt_init(&ca_cert);
        mbedtls_x509write_crt_init(&server_cert);
    }
    ~Context() {
        mbedtls_x509write_crt_free(&server_cert);
        mbedtls_x509write_crt_free(&ca_cert);
        mbedtls_pk_free(&server_key);
        mbedtls_pk_free(&ca_key);
        mbedtls_ctr_drbg_free(&rng);
        mbedtls_entropy_free(&entropy);
    }
};

bool date(std::uint64_t epoch, unsigned years_ahead, std::array<char, 15>& out,
          std::uint64_t& expiration) {
    const sys_seconds now{seconds{static_cast<std::int64_t>(epoch)}};
    const auto day = floor<days>(now);
    const year_month_day start{day};
    year_month_day target{start.year() + years{static_cast<int>(years_ahead)}, start.month(),
                          start.day()};
    if (!target.ok())
        target = year_month_day{year_month_day_last{target.year(), month_day_last{target.month()}}};
    const sys_seconds point{sys_days{target} + (now - day)};
    expiration = static_cast<std::uint64_t>(point.time_since_epoch().count());
    const hh_mm_ss time{point - floor<days>(point)};
    return std::snprintf(out.data(), out.size(), "%04d%02u%02u%02d%02d%02d", int(target.year()),
                         unsigned(target.month()), unsigned(target.day()),
                         int(time.hours().count()), int(time.minutes().count()),
                         int(time.seconds().count())) == 14;
}

bool make_key(mbedtls_pk_context& key, mbedtls_ctr_drbg_context& rng) {
    return mbedtls_pk_setup(&key, mbedtls_pk_info_from_type(MBEDTLS_PK_ECKEY)) == 0 &&
           mbedtls_ecp_gen_key(MBEDTLS_ECP_DP_SECP256R1, mbedtls_pk_ec(key),
                               mbedtls_ctr_drbg_random, &rng) == 0;
}

bool write_key(mbedtls_pk_context& key, std::string& out) {
    std::array<unsigned char, 512> buffer{};
    const bool ok = mbedtls_pk_write_key_pem(&key, buffer.data(), buffer.size()) == 0;
    if (ok)
        out.assign(reinterpret_cast<const char*>(buffer.data()));
    erase(buffer);
    return ok;
}

bool write_cert(mbedtls_x509write_cert& cert, mbedtls_ctr_drbg_context& rng, std::string& out) {
    std::array<unsigned char, 1200> buffer{};
    const bool ok = mbedtls_x509write_crt_pem(&cert, buffer.data(), buffer.size(),
                                              mbedtls_ctr_drbg_random, &rng) == 0;
    if (ok)
        out.assign(reinterpret_cast<const char*>(buffer.data()));
    erase(buffer);
    return ok;
}

bool configure_cert(mbedtls_x509write_cert& cert, mbedtls_pk_context& subject_key,
                    mbedtls_pk_context& issuer_key, std::string_view subject,
                    std::string_view issuer, const std::array<char, 15>& before,
                    const std::array<char, 15>& after, mbedtls_ctr_drbg_context& rng) {
    std::array<unsigned char, 16> serial{};
    if (mbedtls_ctr_drbg_random(&rng, serial.data(), serial.size()) != 0)
        return false;
    serial[0] &= 0x7f; // Positive ASN.1 integer.
    serial[0] |= 1;    // Never zero, even if the rest of the serial is zero.
    mbedtls_x509write_crt_set_subject_key(&cert, &subject_key);
    mbedtls_x509write_crt_set_issuer_key(&cert, &issuer_key);
    mbedtls_x509write_crt_set_md_alg(&cert, MBEDTLS_MD_SHA256);
    return mbedtls_x509write_crt_set_serial_raw(&cert, serial.data(), serial.size()) == 0 &&
           mbedtls_x509write_crt_set_subject_name(&cert, std::string(subject).c_str()) == 0 &&
           mbedtls_x509write_crt_set_issuer_name(&cert, std::string(issuer).c_str()) == 0 &&
           mbedtls_x509write_crt_set_validity(&cert, before.data(), after.data()) == 0;
}

bool fits(const ConsumerTls& tls) {
    // Use the same canonical serializer as the journal, including escaped PEM
    // newlines and field names, rather than an optimistic raw-byte sum.
    ConsumerProfile sample;
    sample.device_id = "00000000000000000000000000000001";
    sample.owner_epoch = 1;
    std::array<std::uint8_t, 65> point{};
    point[0] = 4;
    sample.owners = {network::bootstrap_b64url(point)};
    sample.ssid = "test";
    sample.password = "password";
    sample.time_server = "time.example.org";
    sample.callsign = "K1ABC";
    sample.locator = "FN20";
    sample.power_dbm = 30;
    sample.tls = tls;
    sample.request_sha256 = std::string(64, 'a');
    auto serialized = serialize_consumer_profile(sample);
    const bool valid = !serialized.empty();
    volatile char* bytes = serialized.empty() ? nullptr : serialized.data();
    for (std::size_t i = 0; i < serialized.size(); ++i)
        bytes[i] = 0;
    scrub(sample);
    return valid;
}
} // namespace

bool generate_consumer_tls(std::string_view device_id, std::string_view hostname,
                           std::uint64_t utc_now, ConsumerTls& out) {
    scrub(out);
    auto canonical = network::canonical_local_hostname(hostname);
    if (!network::valid_device_id(device_id) || !canonical || *canonical != hostname ||
        utc_now < earliest_utc || utc_now >= latest_utc)
        return false;
    network::PsaCryptoOwner psa;
    if (psa.acquire() != PSA_SUCCESS)
        return false;
    Context context;
    constexpr unsigned char personalization[] = "WsprryPico consumer identity v1";
    if (mbedtls_ctr_drbg_seed(&context.rng, mbedtls_entropy_func, &context.entropy, personalization,
                              sizeof(personalization) - 1) != 0 ||
        !make_key(context.ca_key, context.rng) || !make_key(context.server_key, context.rng))
        return false;
    std::array<char, 15> before{}, ca_after{}, server_after{};
    std::uint64_t ignored = 0;
    if (!date(utc_now, 0, before, ignored) || !date(utc_now, 10, ca_after, out.ca_not_after_utc) ||
        !date(utc_now, 1, server_after, out.server_not_after_utc)) {
        scrub(out);
        return false;
    }
    const std::string ca_name = "CN=WsprryPico Device CA,OU=" + std::string(device_id);
    const std::string server_name = "CN=" + *canonical + ",OU=" + std::string(device_id);
    if (!configure_cert(context.ca_cert, context.ca_key, context.ca_key, ca_name, ca_name, before,
                        ca_after, context.rng) ||
        mbedtls_x509write_crt_set_basic_constraints(&context.ca_cert, 1, 0) != 0 ||
        mbedtls_x509write_crt_set_key_usage(&context.ca_cert, MBEDTLS_X509_KU_KEY_CERT_SIGN) != 0 ||
        !configure_cert(context.server_cert, context.server_key, context.ca_key, server_name,
                        ca_name, before, server_after, context.rng) ||
        mbedtls_x509write_crt_set_basic_constraints(&context.server_cert, 0, -1) != 0 ||
        mbedtls_x509write_crt_set_key_usage(&context.server_cert,
                                            MBEDTLS_X509_KU_DIGITAL_SIGNATURE) != 0) {
        scrub(out);
        return false;
    }
    mbedtls_x509_san_list san{};
    san.node.type = MBEDTLS_X509_SAN_DNS_NAME;
    san.node.san.unstructured_name.p = reinterpret_cast<unsigned char*>(canonical->data());
    san.node.san.unstructured_name.len = canonical->size();
    mbedtls_asn1_sequence eku{};
    eku.buf.tag = MBEDTLS_ASN1_OID;
    eku.buf.p = reinterpret_cast<unsigned char*>(const_cast<char*>(MBEDTLS_OID_SERVER_AUTH));
    eku.buf.len = MBEDTLS_OID_SIZE(MBEDTLS_OID_SERVER_AUTH);
    if (mbedtls_x509write_crt_set_subject_alternative_name(&context.server_cert, &san) != 0 ||
        mbedtls_x509write_crt_set_ext_key_usage(&context.server_cert, &eku) != 0 ||
        !write_key(context.ca_key, out.ca_private_key) ||
        !write_key(context.server_key, out.server_private_key) ||
        !write_cert(context.ca_cert, context.rng, out.ca_certificate) ||
        !write_cert(context.server_cert, context.rng, out.server_certificate)) {
        scrub(out);
        return false;
    }
    out.hostname = *canonical;
    out.port = 443;
    if (!fits(out) || !validate_consumer_tls(out, device_id, utc_now)) {
        scrub(out);
        return false;
    }
    return true;
}
} // namespace wsprrypico::provisioning

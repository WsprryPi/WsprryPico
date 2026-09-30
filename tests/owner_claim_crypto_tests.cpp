#include "mbedtls/platform.h"
#include "network/bootstrap_codec.hpp"
#include "network/pico/owner_claim_crypto.hpp"

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
    // Browser-side Noble X25519/HKDF/ChaCha20-Poly1305 fixture. The fixed
    // private keys and Wi-Fi password are synthetic test-only values.
    const auto private_key =
        hex<32>("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb");
    network::OwnerClaimFields fields;
    fields.device_id = hex<16>("0102030405060708090a0b0c0d0e0f10");
    fields.boot_id = hex<16>("1112131415161718191a1b1c1d1e1f20");
    fields.slot_id = hex<16>("2122232425262728292a2b2c2d2e2f30");
    fields.owner_public_key = fixed<65>(
        "BGsX0fLhLEJH-Lzm5WOkQPJ3A32BLeszoPShOUXYmMKWT-NC4v4af5uO5-tKfA-eFivOM1drMV7Oy7ZAaDe_UfU");
    fields.browser_public_key = fixed<32>("hSDwCYkwp1R0i33ctD73Wg2_Og0mOBr066SpjqqbTmo");
    fields.pico_public_key = fixed<32>("3p7bfXt9wbTTW2HC7OQ1Nz-DQ8hbeGdNrfx-FG-IK08");
    fields.browser_nonce = hex<16>("7172737475767778797a7b7c7d7e7f80");
    fields.request_id = hex<16>("8182838485868788898a8b8c8d8e8f90");
    fields.source = provisioning::ProfileSource::NetworkOnly;
    fields.generation = 1;
    const auto nonce = fixed<12>("AAECAwQFBgcICQoL");
    const auto ciphertext = b64("poQYTuc-kkcbttyiTykRG7zsxSF8GJNhgcuPUE5UjBKnCiyrhw", 37);
    const auto tag = fixed<16>("ig0bDpTZRdWC0LOA6xtetA");
    const auto transcript = network::owner_claim_transcript(fields);
    assert(transcript && network::bootstrap_digest(transcript->view()) ==
                             "2d94b18a297395f36b3fb714e4430cbb02074c37429648a27b72e06d7768697b");

    network::PicoOwnerClaimCrypto crypto;
    assert(crypto.begin_for_test(private_key));
    assert(crypto.public_key() == fields.pico_public_key);
    network::OwnerClaimCredentials out;
    assert(crypto.open(fields, nonce, ciphertext, tag, out));
    assert(out.ssid == "LabNet" && out.password == "test-only-password" &&
           out.callsign == "K1ABC" && out.locator == "FN20" && out.power_dbm == 30);
    assert(!crypto.open(fields, nonce, ciphertext, tag, out));
    assert(out.ssid.empty() && out.password.empty() && out.callsign.empty() && out.locator.empty());

    network::PicoOwnerClaimCrypto station_crypto;
    assert(station_crypto.begin_for_test(private_key));
    const auto station_ciphertext = b64("oMh8Z5gapBYpnZ3mfA", 13);
    const auto station_tag = fixed<16>("Efn-qQlKJWRvZ39KFA-oPQ");
    assert(station_crypto.open(fields, nonce, station_ciphertext, station_tag, out));
    assert(out.ssid.empty() && out.password.empty() && out.callsign == "K1ABC" &&
           out.locator == "FN20" && out.power_dbm == 30);

    const auto rejects = [&](network::OwnerClaimFields candidate,
                             std::array<std::uint8_t, 12> candidate_nonce,
                             std::span<const std::uint8_t> candidate_ciphertext,
                             std::array<std::uint8_t, 16> candidate_tag) {
        network::PicoOwnerClaimCrypto attempt;
        assert(attempt.begin_for_test(private_key));
        assert(!attempt.open(candidate, candidate_nonce, candidate_ciphertext, candidate_tag, out));
        assert(out.ssid.empty() && out.password.empty() && out.callsign.empty() &&
               out.locator.empty());
        assert(!attempt.open(fields, nonce, ciphertext, tag, out));
    };
    auto changed = fields;
    changed.device_id[0] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.boot_id[0] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.slot_id[0] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.owner_public_key[1] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.browser_public_key[0] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.pico_public_key[0] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.browser_nonce[0] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.request_id[0] ^= 1;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.generation = 2;
    rejects(changed, nonce, ciphertext, tag);
    changed = fields;
    changed.source = provisioning::ProfileSource::Unprovisioned;
    rejects(changed, nonce, ciphertext, tag);
    // Independently sealed by the browser's Noble implementation for a later
    // station-only update of consumer generation 3 (the physical regression).
    auto update_fields = fields;
    update_fields.source = provisioning::ProfileSource::ConsumerProfile;
    update_fields.generation = 3;
    const auto update_transcript = network::owner_claim_transcript(update_fields);
    assert(update_transcript &&
           network::bootstrap_digest(update_transcript->view()) ==
               "8d9b7141924fe6a5b3ff430ccb75a9f004989587e20e533a80f515c1398efdb9");
    const auto update_ciphertext = b64("U4dqWEtiMhoFzBnB4A", 13);
    const auto update_tag = fixed<16>("FBv45vIeTQCvbHa4kRE6NA");
    network::PicoOwnerClaimCrypto update_crypto;
    assert(update_crypto.begin_for_test(private_key));
    assert(update_crypto.open(update_fields, nonce, update_ciphertext, update_tag, out));
    assert(out.ssid.empty() && out.password.empty() && out.callsign == "AA0NT" &&
           out.locator == "EM18" && out.power_dbm == 20);
    // Six-character and maximum-size envelopes independently sealed by Noble.
    const auto six_ciphertext = b64("U4dqWEtiMhoFzBnBtfg6", 15);
    const auto six_tag = fixed<16>("XQVKa1R4zGBUIvIM6TAjEA");
    network::PicoOwnerClaimCrypto six_crypto;
    assert(six_crypto.begin_for_test(private_key));
    assert(six_crypto.open(update_fields, nonce, six_ciphertext, six_tag, out));
    assert(out.locator == "EM18AA" && out.power_dbm == 20);
    const auto maximum_ciphertext =
        b64("c8YuWEsTPQ8BwGm4tfhv1wJ0opkd68Mv3bPB6mOzKWDl_Ew3pGkcC_0Xn3eC7gywq0N_JsqSraAK-gs6HLC5"
            "EEGK82O9dhD3n2by2ZeeJsMoekf5PnY1ABUmIsbJPsthb_dkXNPK_HxD4mnn3NGR",
            111);
    const auto maximum_tag = fixed<16>("DBWKeXp9RLkWZZTqUsyAGw");
    network::PicoOwnerClaimCrypto maximum_crypto;
    assert(maximum_crypto.begin_for_test(private_key));
    assert(maximum_crypto.open(update_fields, nonce, maximum_ciphertext, maximum_tag, out));
    assert(out.ssid == std::string(32, 'A') && out.password == std::string(63, 'p') &&
           out.callsign == "KA1BCD" && out.locator == "FN20XX" && out.power_dbm == 60);
    const auto extended_ciphertext =
        b64("c8YuWEsTPQ8BwGm4tfhv1wJ0opkd68Mv3bPB6mOzKWDl_Ew3pGkcC_0Xn3eC7gywq0N_JsqSraAK-gs6HLC5"
            "EEGK82O9dhD3n2by2ZeeJsMoekf5PnY1ABUmIsbJPsthb_1uXNLG6xdE7hiTwc_ow2Dg_nER",
            117);
    const auto extended_tag = fixed<16>("vY0RtxhmK1balnTmctLM7Q");
    network::PicoOwnerClaimCrypto extended_crypto;
    assert(extended_crypto.begin_for_test(private_key));
    assert(extended_crypto.open(update_fields, nonce, extended_ciphertext, extended_tag, out));
    assert(out.callsign == "AA0NT/ABCDEF" && out.locator == "EM18XX" && out.power_dbm == 60);
    auto bad_six_tag = six_tag;
    bad_six_tag[0] ^= 1;
    rejects(update_fields, nonce, six_ciphertext, bad_six_tag);
    changed = update_fields;
    changed.generation = 4;
    rejects(changed, nonce, update_ciphertext, update_tag);
    changed = update_fields;
    changed.source = provisioning::ProfileSource::NetworkOnly;
    rejects(changed, nonce, update_ciphertext, update_tag);
    auto bad_update_tag = update_tag;
    bad_update_tag[0] ^= 1;
    rejects(update_fields, nonce, update_ciphertext, bad_update_tag);
    auto bad_nonce = nonce;
    bad_nonce[0] ^= 1;
    rejects(fields, bad_nonce, ciphertext, tag);
    auto bad_tag = tag;
    bad_tag[0] ^= 1;
    rejects(fields, nonce, ciphertext, bad_tag);
    auto bad_body = ciphertext;
    bad_body[0] ^= 1;
    rejects(fields, nonce, bad_body, tag);
    rejects(fields, nonce, std::span(ciphertext).first(19), tag);
}

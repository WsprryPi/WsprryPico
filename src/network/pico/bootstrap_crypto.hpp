#pragma once

#include "network/pico/psa_lifetime.hpp"

#include <array>
#include <cstdint>
#include <span>
#include <string>

namespace wsprrypico::network {
struct BootstrapTranscriptFields {
    std::array<std::uint8_t, 16> device_id{}, boot_id{}, slot_id{};
    std::array<std::uint8_t, 32> browser_public_key{}, pico_public_key{};
    std::array<std::uint8_t, 16> request_nonce{}, request_id{};
};

// Target crypto for one physically granted slot. The private key is a volatile
// PSA handle and is destroyed by the first open attempt or cancellation.
class PicoBootstrapCrypto {
  public:
    PicoBootstrapCrypto() = default;
    ~PicoBootstrapCrypto() {
        clear();
    }
    PicoBootstrapCrypto(const PicoBootstrapCrypto&) = delete;
    PicoBootstrapCrypto& operator=(const PicoBootstrapCrypto&) = delete;

    bool begin();
#ifdef WSPRRY_PICO_BOOTSTRAP_CRYPTO_TEST
    bool begin_for_test(std::span<const std::uint8_t, 32> private_key);
#endif
    std::array<std::uint8_t, 32> public_key() const {
        return public_key_;
    }
    bool open(const BootstrapTranscriptFields& fields, std::span<const std::uint8_t, 12> nonce,
              std::span<const std::uint8_t> ciphertext, std::span<const std::uint8_t, 16> tag,
              std::string& ssid, std::string& password, std::array<std::uint8_t, 32>& ack_verifier);
    void clear();

  private:
    bool create(std::span<const std::uint8_t> private_key);
    PsaCryptoOwner psa_;
    psa_key_id_t private_key_ = 0;
    std::array<std::uint8_t, 32> public_key_{};
};
} // namespace wsprrypico::network

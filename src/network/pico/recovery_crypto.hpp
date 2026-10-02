#pragma once

#include "network/pico/bootstrap_crypto.hpp"
#include "network/pico/psa_lifetime.hpp"

#include <array>
#include <cstdint>
#include <span>
#include <string>

namespace wsprrypico::network {
// Domain-separated recovery crypto for one bounded open-AP slot. The private key is a volatile
// PSA handle and is destroyed by the first open attempt or cancellation.
class PicoRecoveryCrypto {
  public:
    PicoRecoveryCrypto() = default;
    ~PicoRecoveryCrypto() {
        clear();
    }
    PicoRecoveryCrypto(const PicoRecoveryCrypto&) = delete;
    PicoRecoveryCrypto& operator=(const PicoRecoveryCrypto&) = delete;

    bool begin();
#ifdef WSPRRY_PICO_RECOVERY_CRYPTO_TEST
    bool begin_for_test(std::span<const std::uint8_t, 32> private_key);
#endif
    std::array<std::uint8_t, 32> public_key() const {
        return public_key_;
    }
    bool open(const BootstrapTranscriptFields& fields, std::span<const std::uint8_t, 12> nonce,
              std::span<const std::uint8_t> ciphertext, std::span<const std::uint8_t, 16> tag,
              std::string& command);
    void clear();

  private:
    bool create(std::span<const std::uint8_t> private_key);
    PsaCryptoOwner psa_;
    psa_key_id_t private_key_ = 0;
    std::array<std::uint8_t, 32> public_key_{};
};
} // namespace wsprrypico::network

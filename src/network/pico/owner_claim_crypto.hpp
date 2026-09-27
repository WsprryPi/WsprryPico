#pragma once

#include "network/owner_wire.hpp"
#include "network/pico/psa_lifetime.hpp"

#include <array>
#include <cstdint>
#include <span>
#include <string>

namespace wsprrypico::network {

struct OwnerClaimCredentials {
    std::string ssid, password, callsign, locator;
    unsigned power_dbm = 0;
    ~OwnerClaimCredentials() {
        clear();
    }
    OwnerClaimCredentials() = default;
    OwnerClaimCredentials(const OwnerClaimCredentials&) = delete;
    OwnerClaimCredentials& operator=(const OwnerClaimCredentials&) = delete;
    void clear();
};

// One-use target AEAD opener. The caller must independently validate the
// active physical slot, journal identity, owner point and output safety.
class PicoOwnerClaimCrypto {
  public:
    PicoOwnerClaimCrypto() = default;
    ~PicoOwnerClaimCrypto() {
        clear();
    }
    PicoOwnerClaimCrypto(const PicoOwnerClaimCrypto&) = delete;
    PicoOwnerClaimCrypto& operator=(const PicoOwnerClaimCrypto&) = delete;

    bool begin();
#ifdef WSPRRY_PICO_OWNER_CLAIM_CRYPTO_TEST
    bool begin_for_test(std::span<const std::uint8_t, 32> private_key);
#endif
    std::array<std::uint8_t, 32> public_key() const {
        return public_key_;
    }
    bool open(const OwnerClaimFields& fields, std::span<const std::uint8_t, 12> nonce,
              std::span<const std::uint8_t> ciphertext, std::span<const std::uint8_t, 16> tag,
              OwnerClaimCredentials& out);
    void clear();

  private:
    bool create(std::span<const std::uint8_t> private_key);
    PsaCryptoOwner psa_;
    psa_key_id_t private_key_ = 0;
    std::array<std::uint8_t, 32> public_key_{};
};

} // namespace wsprrypico::network

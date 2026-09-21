#pragma once

#include "psa/crypto.h"

#include <cstddef>

namespace wsprrypico::network {
// Core-0-serialized ownership of Mbed TLS's process-global PSA state. Each
// server or transient validator owns one lease; only the first lease initializes
// PSA and only the last release tears it down.
class PsaCryptoOwner final {
  public:
    PsaCryptoOwner() = default;
    ~PsaCryptoOwner();
    PsaCryptoOwner(const PsaCryptoOwner&) = delete;
    PsaCryptoOwner& operator=(const PsaCryptoOwner&) = delete;

    psa_status_t acquire();
    void release();
    bool owns() const {
        return owns_;
    }
    static std::size_t owners();
    static std::size_t peak_owners();

  private:
    bool owns_ = false;
};
} // namespace wsprrypico::network

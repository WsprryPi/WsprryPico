#include "network/pico/psa_lifetime.hpp"

#include "psa/crypto_extra.h"

#include <algorithm>

namespace wsprrypico::network {
namespace {
std::size_t owner_count = 0;
std::size_t owner_peak = 0;
} // namespace

PsaCryptoOwner::~PsaCryptoOwner() {
    release();
}

psa_status_t PsaCryptoOwner::acquire() {
    if (owns_)
        return PSA_SUCCESS;
    if (!owner_count) {
        const auto result = psa_crypto_init();
        if (result != PSA_SUCCESS) {
            mbedtls_psa_crypto_free();
            return result;
        }
    }
    ++owner_count;
    owner_peak = std::max(owner_peak, owner_count);
    owns_ = true;
    return PSA_SUCCESS;
}

void PsaCryptoOwner::release() {
    if (!owns_)
        return;
    owns_ = false;
    if (--owner_count == 0)
        mbedtls_psa_crypto_free();
}

std::size_t PsaCryptoOwner::owners() {
    return owner_count;
}

std::size_t PsaCryptoOwner::peak_owners() {
    return owner_peak;
}
} // namespace wsprrypico::network

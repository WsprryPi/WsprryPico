// SPDX-License-Identifier: MIT
#include "rf/reference_measurement.hpp"

#include <cassert>
#include <cmath>
#include <limits>

using namespace wsprrypico::rf;
int main() {
    ReferencePolicy policy;
    ReferenceWindow window{1'000'000'000ULL, 11'000'000'000ULL, 10'000'000, 2'000, 1, true};
    auto result = measure_reference(window, 1'000'000, 1, policy);
    assert(result.valid() && result.ratio == 1 && !result.local_rate_ppb);
    assert(result.uncertainty_ppb > 301 && result.uncertainty_ppb < 302);
    assert(reference_fresh(result, policy, 41'000'000'000ULL, 1));
    assert(!reference_fresh(result, policy, 41'000'000'001ULL, 1));
    assert(!reference_fresh(result, policy, 10'000'000'000ULL, 1));
    assert(!reference_fresh(result, policy, 11'000'000'000ULL, 2));
    auto changed_policy = policy;
    changed_policy.maximum_age_ns++;
    assert(!reference_fresh(result, changed_policy, 11'000'000'000ULL, 1));
    assert(!measure_reference(window, 1'000'000, 2, policy).valid());
    assert(!measure_reference(window, std::numeric_limits<long double>::quiet_NaN(), 1, policy)
                .valid());
    policy.use = ReferenceUse::TrustedLocal;
    assert(!valid_reference_policy(policy));
    policy.trusted_uncertainty_ppb = 500;
    assert(valid_reference_policy(policy));
    assert(!reference_fresh(result, policy, 11'000'000'000ULL, 1));
    // A slow raw clock counts more reference edges per raw second. A positive
    // UTC rate is required; assigning the opposite sign would worsen holdover.
    window.edges = 10'000'100;
    result = measure_reference(window, 1'000'000, 1, policy);
    assert(result.valid() && result.local_rate_ppb == 10'000);
    assert(result.uncertainty_ppb > 800 && result.uncertainty_ppb < 803);
    window.edges = 9'999'900;
    result = measure_reference(window, 1'000'000, 1, policy);
    assert(result.valid() && result.local_rate_ppb == -10'000);
    window.coherent = false;
    assert(!measure_reference(window, 1'000'000, 1, policy).valid());
    window.coherent = true;
    window.edges = 0;
    assert(!measure_reference(window, 1'000'000, 1, policy).valid());
    window.edges = std::numeric_limits<std::uint64_t>::max();
    assert(!measure_reference(window, 1'000'000, 1, policy).valid());
    window.edges = 10'000'000;
    window.endpoint_uncertainty_ns = 10'000'000'000ULL;
    assert(!measure_reference(window, 1'000'000, 1, policy).valid());
    window.endpoint_uncertainty_ns = 2'000;
    window.end_raw_ns = window.start_raw_ns + 1'000'000'000;
    assert(!measure_reference(window, 1'000'000, 1, policy).valid());
    // Low-frequency, short windows cannot promise sub-ppm resolution.
    window.end_raw_ns = window.start_raw_ns + 10'000'000'000ULL;
    window.edges = 10'000;
    assert(!measure_reference(window, 1'000, 1, policy).valid());
    policy = {};
    window.edges = 10'100'000;
    window.endpoint_uncertainty_ns = 0;
    result = measure_reference(window, 1'000'000, 1, policy);
    assert(result.valid());
    // One boundary edge over a nominal 10-million-edge interval is 100 ppb,
    // regardless of the observed ratio. Do not divide by 10.1 million edges.
    assert(result.uncertainty_ppb > 100.999L && result.uncertainty_ppb < 101.001L);
}

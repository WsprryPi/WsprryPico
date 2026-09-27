#pragma once

#include "provisioning/consumer_profile.hpp"

#include <cstdint>
#include <string_view>

namespace wsprrypico::provisioning {
// Validate all persisted consumer TLS material against the selected device
// identity and a trusted UTC reading before activation or journal commit.
bool validate_consumer_tls(const ConsumerTls& tls, std::string_view device_id,
                           std::uint64_t utc_now);
} // namespace wsprrypico::provisioning

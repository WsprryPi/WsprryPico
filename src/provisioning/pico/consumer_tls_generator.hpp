#pragma once

#include "provisioning/consumer_profile.hpp"

#include <cstdint>
#include <string_view>

namespace wsprrypico::provisioning {
// Creates a fresh, device-bound CA and a separate station server identity.
// The caller must obtain utc_now from an authenticated, bounded clock before
// invoking this function. No material is persisted until the caller commits
// the complete ConsumerProfile journal transaction.
bool generate_consumer_tls(std::string_view device_id, std::string_view hostname,
                           std::uint64_t utc_now, ConsumerTls& out);
} // namespace wsprrypico::provisioning

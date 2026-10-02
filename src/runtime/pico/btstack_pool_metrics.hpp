#pragma once
#include "runtime/pool_metrics.hpp"

#include <array>
namespace wsprrypico::runtime {
// HCI connections, L2CAP channels/services, SM lookup and whitelist, in order.
std::array<PoolSnapshot, 5> btstack_pool_snapshot();
} // namespace wsprrypico::runtime

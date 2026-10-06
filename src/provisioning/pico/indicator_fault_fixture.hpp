#pragma once

#include <cstdint>

namespace wsprrypico::provisioning {
std::uint32_t indicator_fault_fixture_calls();
std::uint32_t indicator_fault_fixture_injected();
std::uint32_t indicator_fault_fixture_successful_writes();
} // namespace wsprrypico::provisioning

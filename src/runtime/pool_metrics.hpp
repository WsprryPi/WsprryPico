#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace wsprrypico::runtime {
struct PoolSnapshot {
    std::uint32_t used = 0, peak = 0, failures = 0, faults = 0, capacity = 0;
};
// A foreground-only, allocation-free ledger for externally owned fixed pools.
// Null allocations are exhaustion; duplicate allocation/foreign free is a fault.
template <std::size_t Capacity> class PoolMetrics {
  public:
    bool allocated(const void* pointer) {
        if (!pointer) {
            ++metrics_.failures;
            return true;
        }
        for (auto value : pointers_)
            if (value == pointer) {
                ++metrics_.faults;
                return false;
            }
        for (auto& value : pointers_)
            if (!value) {
                value = pointer;
                ++metrics_.used;
                if (metrics_.used > metrics_.peak)
                    metrics_.peak = metrics_.used;
                return true;
            }
        ++metrics_.faults;
        return false;
    }
    bool released(const void* pointer) {
        if (pointer)
            for (auto& value : pointers_)
                if (value == pointer) {
                    value = nullptr;
                    --metrics_.used;
                    return true;
                }
        ++metrics_.faults;
        return false;
    }
    PoolSnapshot snapshot() const {
        auto result = metrics_;
        result.capacity = Capacity;
        return result;
    }

  private:
    std::array<const void*, Capacity> pointers_{};
    PoolSnapshot metrics_{};
};
} // namespace wsprrypico::runtime

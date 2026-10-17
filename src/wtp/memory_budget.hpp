#pragma once
#include <cstddef>
#include <limits>
namespace wsprrypico::wtp {
// Installed once by the serialized application owner. Host default has no
// target heap restriction; tests may inject exhaustion. Preserve scratch for
// authoritative status/abort and a bounded error response before growing input.
inline std::size_t (*available_memory)() = nullptr;
// Only the serialized WTP owner may reclaim optional adapter buffers. Generic
// JSON/application admission stays side-effect-free because its input may be
// owned by that adapter. Reclaim never changes the requested reserve.
inline void (*reclaim_optional_memory)() = nullptr;
inline bool reclaiming_optional_memory = false;
// Input remains resident while core 0 builds INFO or decodes a small request.
// Those stages are serialized: budget 8 KiB for the larger temporary lifetime,
// separately from the unchanged 32 KiB acceptance reserve. An extra KiB covers
// page allocator bookkeeping and parser event storage during admission.
inline constexpr std::size_t input_workspace_bytes = 8192;
inline constexpr std::size_t input_overhead_bytes = 1024;
inline bool memory_admitted(std::size_t bytes, std::size_t reserve = 32768) {
    return !available_memory || (bytes <= std::numeric_limits<std::size_t>::max() - reserve &&
                                 available_memory() >= bytes + reserve);
}
inline bool authoritative_memory_admitted(std::size_t bytes, std::size_t reserve = 32768) {
    if (memory_admitted(bytes, reserve))
        return true;
    if (!reclaim_optional_memory || reclaiming_optional_memory)
        return false;
    reclaiming_optional_memory = true;
    reclaim_optional_memory();
    reclaiming_optional_memory = false;
    return memory_admitted(bytes, reserve);
}
inline bool input_memory_admitted(std::size_t bytes) {
    return bytes <= std::numeric_limits<std::size_t>::max() - input_overhead_bytes &&
           memory_admitted(bytes + input_overhead_bytes, 32768 + input_workspace_bytes);
}
inline bool authoritative_input_memory_admitted(std::size_t bytes) {
    return bytes <= std::numeric_limits<std::size_t>::max() - input_overhead_bytes &&
           authoritative_memory_admitted(bytes + input_overhead_bytes,
                                         32768 + input_workspace_bytes);
}
} // namespace wsprrypico::wtp

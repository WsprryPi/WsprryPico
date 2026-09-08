#pragma once
#include <cstddef>
#include <limits>
namespace wsprrypico::wtp {
// Installed once by the serialized application owner. Host default has no
// target heap restriction; tests may inject exhaustion. Preserve scratch for
// authoritative status/abort and a bounded error response before growing input.
inline std::size_t (*available_memory)() = nullptr;
inline bool memory_admitted(std::size_t bytes, std::size_t reserve = 32768) {
    return !available_memory || (bytes <= std::numeric_limits<std::size_t>::max() - reserve &&
                                 available_memory() >= bytes + reserve);
}
} // namespace wsprrypico::wtp

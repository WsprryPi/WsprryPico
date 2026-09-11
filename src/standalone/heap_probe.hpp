#pragma once
#include <charconv>
#include <cstddef>
#include <limits>
#include <string>
#include <string_view>

namespace wsprrypico::standalone {
// Keep admission before the allocator callback: rejected commands must not
// disturb the heap or the RF worker. One extra byte permits an idle failure test.
template <typename Probe>
std::string heap_probe_command(std::string_view value, std::size_t capacity, bool idle,
                               Probe probe) {
    std::size_t bytes = 0;
    const auto parsed = std::from_chars(value.data(), value.data() + value.size(), bytes);
    if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size() || !bytes ||
        (bytes > capacity &&
         (capacity == std::numeric_limits<std::size_t>::max() || bytes - capacity != 1)))
        return "{\"ok\":false,\"error\":\"probe_range\"}\n";
    if (!idle)
        return "{\"ok\":false,\"error\":\"not_idle\"}\n";
    return probe(bytes) ? "{\"ok\":true,\"allocated\":true}\n"
                        : "{\"ok\":true,\"allocated\":false}\n";
}
} // namespace wsprrypico::standalone

#include "lwip/tcp.h"
#include "pico/time.h"

#include <cassert>
#include <cstdint>
#include <limits>
int main() {
    // Real mode refuses clock mutation. Controlled mode has no host-time scale.
    assert(!mock_tcp_advance_time_us(1));
    mock_tcp_enable_manual_time();
    assert(time_us_64() == 1'000'000);
    assert(mock_tcp_advance_time_us(999));
    assert(time_us_64() == 1'000'999);
    assert(mock_tcp_advance_time_us(1));
    assert(time_us_64() == 1'001'000);
    assert(mock_tcp_advance_time_us(1));
    assert(time_us_64() == 1'001'001);
    assert(!mock_tcp_advance_time_us(std::numeric_limits<std::uint64_t>::max()));
    assert(time_us_64() == 1'001'001); // Failed advance must not change the clock.
}

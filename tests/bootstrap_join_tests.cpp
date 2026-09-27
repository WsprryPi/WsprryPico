#include "network/bootstrap_codec.hpp"
#include "network/bootstrap_join.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <vector>

using namespace wsprrypico::network;

int main() {
    BootstrapJoinGate gate;
    gate.begin(100);
    assert(gate.trial(200, false, false) == BootstrapJoinResult::Waiting);
    assert(gate.trial(300, true, false) == BootstrapJoinResult::Waiting); // DHCP not ready.
    assert(gate.trial(45'100, true, true) == BootstrapJoinResult::TimedOut);
    gate.finish();
    assert(gate.trial(45'200, true, true) == BootstrapJoinResult::TimedOut);
    gate.begin(300'000);
    assert(gate.trial(301'000, true, true) == BootstrapJoinResult::Ready);
    gate.finish();
    assert(gate.trial(301'001, true, true) == BootstrapJoinResult::TimedOut);
    BootstrapJoinGate reboot;
    assert(reboot.trial(1'000, true, true) == BootstrapJoinResult::TimedOut);

    const std::array<std::uint8_t, 4> bytes{0, 0xff, 0x10, 0x42};
    assert(bootstrap_hex(bytes) == "00ff1042");
    std::array<std::uint8_t, 4> decoded{};
    assert(bootstrap_unhex("00ff1042", decoded) && decoded == bytes);
    assert(!bootstrap_unhex("00FF1042", decoded));
    const auto encoded = bootstrap_b64url(bytes);
    std::vector<std::uint8_t> buffer;
    assert(bootstrap_unb64url(encoded, buffer, 4, 4));
    assert(std::equal(buffer.begin(), buffer.end(), bytes.begin()));
    assert(!bootstrap_unb64url(encoded + "=", buffer, 4, 4));
    assert(!bootstrap_unb64url("AB", buffer, 1, 1)); // Nonzero pad bits.
}

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
    gate.finish(false);
    gate.service(45'200, true, true);
    assert(!gate.withdraw(200'000, true, false)); // Failure cannot withdraw AP.
    gate.begin(300'000);
    assert(gate.trial(301'000, true, true) == BootstrapJoinResult::Ready);
    gate.finish(true);
    gate.service(301'000, true, true);
    assert(!gate.withdraw(304'000, true, true)); // Reply still in flight.
    assert(gate.withdraw(304'000, true, false));
    gate.service(304'001, false, false);
    assert(!gate.withdraw(400'000, true, false));
    gate.service(400'001, true, true);
    assert(!gate.withdraw(403'000, true, false));
    assert(gate.withdraw(403'001, true, false));
    BootstrapJoinGate reboot;
    reboot.finish(true);
    reboot.service(1'000, true, true);
    assert(!reboot.withdraw(60'999, false, false));
    assert(reboot.withdraw(61'000, false, false));

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

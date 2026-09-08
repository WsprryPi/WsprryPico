#include "network/pico/server.hpp"
#include "network_support.hpp"
#include "pico/time.h"

#include <csignal>
#include <ctime>
#include <thread>
int main() {
    std::signal(SIGPIPE, SIG_IGN);
    network_test::Fixture fixture;
    fixture.clock.utc = static_cast<std::uint64_t>(std::time(nullptr)) * 1'000'000'000ULL;
    const auto started = time_us_64();
    wsprrypico::network::PicoServer server(fixture.service, fixture.api, "test-device",
                                           "test-firmware");
    if (!server.start()) {
        std::cerr << "TLS start error " << server.last_error() << "\n";
        return 1;
    }
    std::cout << "READY " << server.port() << std::endl;
    while (true) {
        fixture.clock.now = (time_us_64() - started) * 1000;
        mock_tcp_poll();
        server.poll(fixture.network.enabled, "127.0.0.1:" + std::to_string(server.port()));
        std::this_thread::sleep_for(std::chrono::microseconds(100));
    }
}

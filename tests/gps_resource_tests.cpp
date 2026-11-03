// SPDX-License-Identifier: MIT
#include "network_support.hpp"
#include "sdk.hpp"
#include "time/pico/gps_input.hpp"

#include <cstdio>
using namespace wsprrypico;
int main() {
    network_test::Flash flash;
    standalone::Store store(flash);
    REQUIRE(store.load());
    auto config = *standalone::parse_config(network_test::config);
    config.gps.emplace();
    config.gps->enabled = true;
    config.gps->pairing_qualified = true;
    REQUIRE(store.save(config));
    network_test::Clock clock;
    standalone::DryRunEngine engine;
    network_test::Identity identities;
    wtp::JobService service(clock, engine, identities);
    standalone::Scheduler scheduler(store, service);
    network_test::Network network;
    network::BrowserApi api(service, store, scheduler, network, std::string(32, 'a'),
                            "test-firmware");
    time::PicoGpsInput gps;
    REQUIRE(gps.open(config.pins, config.si5351, *config.gps));
    for (unsigned i = 1; i <= 2; ++i) {
        gps_mock::edge(3, false, i * 1'000'000ULL - 900'000);
        gps_mock::us = i * 1'000'000ULL - 899'995;
        gps.pps_interrupt();
        gps_mock::edge(3, true, i * 1'000'000ULL);
        gps_mock::us = i * 1'000'000ULL + 5;
        gps.pps_interrupt();
        char body[100], end[8];
        std::snprintf(body, sizeof(body),
                      "GNRMC,12000%u.00,A,3900.0000,N,09400.0000,W,0,0,021126,,,A", i);
        unsigned checksum = 0;
        for (const char* p = body; *p; ++p)
            checksum ^= unsigned(*p);
        std::snprintf(end, sizeof(end), "*%02X\r\n", checksum);
        const auto wire = "$" + std::string(body) + end;
        gps_mock::us += 100'000;
        for (const auto c : wire) {
            gps_mock::receive.push_back(std::uint8_t(c));
            gps.uart_interrupt();
            gps_mock::us += 1100;
        }
        gps.poll(gps_mock::us * 1000, nullptr, nullptr);
    }
    api.gps_observer(
        [](void* p) {
            auto result = static_cast<time::PicoGpsInput*>(p)->status(gps_mock::us * 1000);
            result.pop_back();
            return result + ",\"timer_calibration\":null,\"synthesizer_calibration\":null}";
        },
        &gps);
    network::HttpRequest request{
        "GET",
        "/api/control/v1/gps",
        "",
        {{"host", "127.0.0.1:8443"}, {"origin", "https://127.0.0.1:8443"}}};
    const auto response = api.handle(request, "cert", "127.0.0.1:8443");
    REQUIRE(response.status == 200 && !response.etag.empty());
    std::cout << response.body_text() << '\n';
    gps.close();
}

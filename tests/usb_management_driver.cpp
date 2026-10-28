// Hardware-free production-pair harness. stdin/stdout carry only UMP1 bytes;
// adapters use volatile in-process flash and no network or Pico SDK facilities.
#include "network/local_usb_api.hpp"
#include "provisioning/local_settings.hpp"
#include "standalone/dry_run_engine.hpp"
#include "time/utc_discipline.hpp"
#include "usb/management_endpoint.hpp"
#include "usb/time_exchange.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <iostream>
#include <poll.h>
#include <unistd.h>

using namespace wsprrypico;
namespace {
constexpr auto device = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
struct Flash : standalone::Flash {
    std::array<std::uint8_t, 16384> data{};
    Flash() {
        data.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> out) override {
        if (at > data.size() || out.size() > data.size() - at)
            return false;
        std::copy_n(data.begin() + at, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        if (at % 4096 || at > data.size() - 4096)
            return false;
        std::fill_n(data.begin() + at, 4096, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> in) override {
        if (at > data.size() || in.size() > data.size() - at)
            return false;
        for (std::size_t i = 0; i < in.size(); ++i)
            data[at + i] &= in[i];
        return true;
    }
};
struct Media : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> data{};
    Media() {
        data.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> out) override {
        if (at > data.size() || out.size() > data.size() - at)
            return false;
        std::copy_n(data.begin() + at, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        if (at % provisioning::profile_slot_size ||
            at > data.size() - provisioning::profile_slot_size)
            return false;
        std::fill_n(data.begin() + at, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> in) override {
        if (at > data.size() || in.size() > data.size() - at)
            return false;
        for (std::size_t i = 0; i < in.size(); ++i)
            data[at + i] &= in[i];
        return true;
    }
};
std::uint64_t monotonic(void*) {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                          std::chrono::steady_clock::now().time_since_epoch())
                                          .count());
}
struct Identity : wtp::IdentitySource {
    std::string new_boot_id() override {
        return std::string(32, 'b');
    }
};
struct Network : network::NetworkControl {
    bool enabled = false;
    std::optional<bool> pending;
    std::string status() const override {
        return std::string("{\"enabled\":") + (enabled ? "true" : "false") +
               ",\"link_status\":0,\"ipv4\":\"0.0.0.0\"}";
    }
    bool set_enabled(bool value) override {
        enabled = value;
        return true;
    }
    bool request_enabled(bool value) override {
        pending = value;
        return true;
    }
    void finish_request(bool apply) override {
        if (apply && pending)
            enabled = *pending;
        pending.reset();
    }
};
struct Platform : provisioning::ConsumerClaimCommitPlatform {
    bool safe_to_commit() override {
        return false;
    }
    std::uint64_t monotonic_now_ms() override {
        return monotonic(nullptr) / 1000000;
    }
    bool station_ready(std::string_view) override {
        return false;
    }
    std::optional<std::uint64_t> trusted_utc_now() override {
        return {};
    }
    std::string_view local_hostname() override {
        return "wsprrypico-aaaaaaaa.local";
    }
    bool valid_owner_point(std::string_view) override {
        return false;
    }
    bool generate_tls(std::string_view, std::string_view, std::uint64_t,
                      provisioning::ConsumerTls&) override {
        return false;
    }
    bool valid_tls(const provisioning::ConsumerTls&, std::string_view, std::uint64_t) override {
        return false;
    }
};
} // namespace
int main() {
    Flash flash, drafts;
    Media media;
    standalone::Store store{flash};
    standalone::Progress progress{drafts};
    provisioning::ProfileStore profiles{media};
    provisioning::RuntimeProfile runtime;
    if (!store.load() || !progress.load() || !profiles.load() ||
        !runtime.load(profiles, device, provisioning::BuildBundleState::Absent))
        return 2;
    time::UtcDiscipline clock(monotonic, nullptr);
    time::ControllerTimeArbiter arbiter(clock, monotonic, nullptr, device);
    standalone::DryRunEngine engine;
    Identity identity;
    wtp::JobService service(clock, engine, identity);
    standalone::Scheduler scheduler(store, service);
    Network network;
    Platform platform;
    network::BrowserApi browser(service, store, scheduler, network, device,
                                "usb-pair-host-harness");
    provisioning::HostnameSettings hostname(profiles, runtime, platform, device,
                                            "wsprrypico-aaaaaaaa.local",
                                            "wsprrypico-aaaaaaaa.local");
    provisioning::LocalSettings settings(profiles, runtime, store, progress, device,
                                         "wsprrypico-aaaaaaaa.local");
    browser.consumer_config(runtime);
    browser.progress_settings(progress);
    browser.hostname_settings(hostname);
    browser.local_usb_settings(settings);
    Flash udp_flash;
    logging::UdpStore udp_store(udp_flash);
    if (!udp_store.load())
        return 2;
    logging::UdpSender udp_sender(device, service.status().boot_id, "pico.local");
    browser.udp_logging_service(udp_store, udp_sender);
    logging::Logger udp_logger(device, service.status().boot_id, "pico.local");
    udp_logger.udp_sink(udp_sender);
    browser.logging_service(udp_logger);
    network::LocalUsbApi api(browser);
    usb::TimeExchange time(arbiter, monotonic, nullptr);
    usb::ManagementEndpoint endpoint(
        device, service.status().boot_id, "usb-pair-host-harness",
        [&](const network::HttpRequest& request, std::uint64_t transaction) {
            if (request.path.starts_with("/api/usb/v1/time/"))
                return time.handle(request, transaction);
            return api.handle(request, transaction);
        },
        [&](std::uint64_t transaction, bool delivered) { api.finish(transaction, delivered); });
    endpoint.connect(std::string(32, 'c'));
    while (!endpoint.closed()) {
        endpoint.poll(monotonic(nullptr) / 1000000);
        service.poll();
        while (!endpoint.output().empty()) {
            const auto bytes = endpoint.output();
            std::cout.write(reinterpret_cast<const char*>(bytes.data()),
                            static_cast<std::streamsize>(bytes.size()));
            std::cout.flush();
            if (!std::cout) {
                endpoint.disconnect();
                return 3;
            }
            endpoint.consume_output(bytes.size());
        }
        pollfd input{STDIN_FILENO, POLLIN, 0};
        const auto ready = ::poll(&input, 1, 20);
        if (ready < 0) {
            endpoint.disconnect();
            return 4;
        }
        if (ready == 0)
            continue;
        if (input.revents & (POLLERR | POLLNVAL)) {
            endpoint.disconnect();
            return 5;
        }
        std::uint8_t byte{};
        if (::read(STDIN_FILENO, &byte, 1) != 1) {
            endpoint.disconnect();
            return 0;
        }
        if (endpoint.receive(std::span(&byte, 1), monotonic(nullptr) / 1000000) != 1) {
            endpoint.disconnect();
            return 6;
        }
    }
    return 0;
}

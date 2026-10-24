#include "mbedtls/platform.h"
#include "network/bootstrap_codec.hpp"
#include "network/identity.hpp"
#include "network/pico/consumer_radio_crypto.hpp"
#include "network/pico/http_server.hpp"
#include "network_support.hpp"
#include "provisioning/consumer_profile.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"
#ifdef WSPRRY_PICO_BOOTSTRAP_RECOVERY_TEST
#include "network/pico/bootstrap_server.hpp"
#include "provisioning/field_runtime.hpp"
#include "provisioning/pico/consumer_claim_platform.hpp"
#endif

#include <cstring>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <source_location>
#include <stdexcept>
#include <vector>

using namespace wsprrypico::network;
namespace {
std::uint64_t now_ms = 0;
tcp_pcb listener;
unsigned freed_packets = 0;
bool bind_fails = false, listen_fails = false, new_fails = false;
void check(bool condition, std::source_location at = std::source_location::current()) {
    if (!condition)
        throw std::runtime_error("HTTP concurrency assertion failed at line " +
                                 std::to_string(at.line()));
}
} // namespace
std::uint64_t time_us_64() {
    return now_ms * 1000;
}
tcp_pcb* tcp_new_ip_type(int) {
    listener = {};
    return new_fails ? nullptr : &listener;
}
err_t tcp_bind(tcp_pcb*, const void*, unsigned port) {
    check(port == 80);
    return bind_fails ? ERR_MEM : ERR_OK;
}
tcp_pcb* tcp_listen_with_backlog(tcp_pcb* pcb, int slots) {
    check(slots == 2);
    pcb->listener = !listen_fails;
    return listen_fails ? nullptr : pcb;
}
void tcp_arg(tcp_pcb* pcb, void* arg) {
    pcb->arg = arg;
}
void tcp_accept(tcp_pcb* pcb, err_t (*callback)(void*, tcp_pcb*, err_t)) {
    pcb->accept = callback;
}
void tcp_recv(tcp_pcb* pcb, err_t (*callback)(void*, tcp_pcb*, pbuf*, err_t)) {
    pcb->receive = callback;
}
void tcp_sent(tcp_pcb* pcb, err_t (*callback)(void*, tcp_pcb*, u16_t)) {
    pcb->sent = callback;
}
void tcp_err(tcp_pcb* pcb, void (*callback)(void*, err_t)) {
    pcb->error = callback;
}
void tcp_abort(tcp_pcb* pcb) {
    check(!pcb->listener && !pcb->closed);
    pcb->aborted = pcb->closed = true;
}
err_t tcp_close(tcp_pcb* pcb) {
    check(!pcb->closed);
    if (pcb->close_fails)
        return ERR_MEM;
    pcb->closed = true;
    return ERR_OK;
}
unsigned tcp_sndbuf(tcp_pcb* pcb) {
    return 5840 - pcb->pending;
}
err_t tcp_write(tcp_pcb* pcb, const void* data, u16_t count, int flags) {
    check(!pcb->closed && count <= 1024 && flags == TCP_WRITE_FLAG_COPY);
    if (pcb->no_memory)
        return ERR_MEM;
    if (pcb->write_fails)
        return ERR_ABRT;
    ++pcb->writes;
    pcb->pending += count;
    check(pcb->pending <= 5840);
    pcb->wire.append(static_cast<const char*>(data), count);
    return ERR_OK;
}
err_t tcp_output(tcp_pcb*) {
    return ERR_OK;
}
void tcp_recved(tcp_pcb* pcb, u16_t) {
    check(!pcb->closed);
}
u16_t pbuf_copy_partial(const pbuf* packet, void* out, u16_t count, u16_t offset) {
    std::memcpy(out, static_cast<const char*>(packet->payload) + offset, count);
    return count;
}
void pbuf_free(pbuf*) {
    ++freed_packets;
}

extern "C" mbedtls_ms_time_t mbedtls_ms_time(void) {
    return now_ms;
}
extern "C" int mbedtls_hardware_poll(void*, unsigned char* out, std::size_t n,
                                     std::size_t* received) {
    std::random_device random;
    for (std::size_t i = 0; i < n; ++i)
        out[i] = random();
    *received = n;
    return 0;
}
namespace wsprrypico::network {
struct ConsumerRadioTestAccess {
    static void exhaust(ConsumerRadioApi& api, std::span<const std::uint8_t, 16> id) {
        const auto header = consumer_radio_header(id, 1);
        wtp::FrameBuffer bytes;
        check(bytes.reserve(44));
        bytes.append(header);
        bytes.append(wtp::InputView(std::string(16, 'x')));
        auto* session = api.select(bytes.view());
        check(session != nullptr);
        session->next_sequence = UINT64_MAX;
    }
};
} // namespace wsprrypico::network
namespace {
using namespace wsprrypico;
struct Media : provisioning::Media {
    std::array<std::uint8_t, 16384> bytes{};
    unsigned programs = 0;
    Media() {
        bytes.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> out) override {
        std::copy_n(bytes.begin() + at, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        std::fill_n(bytes.begin() + at, 8192, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> in) override {
        ++programs;
        std::copy(in.begin(), in.end(), bytes.begin() + at);
        return true;
    }
};
struct Random : provisioning::RandomSource {
    bool fail = false, zero = false;
    bool fill(std::span<std::uint8_t> out) override {
        // Deliberately repeat randomness: boot-local serials must prevent reuse.
        std::fill(out.begin(), out.end(), zero ? 0 : 0x55);
        return !fail;
    }
};
struct HostnamePlatform : provisioning::ConsumerClaimCommitPlatform {
    network_test::Fixture& f;
    explicit HostnamePlatform(network_test::Fixture& fixture) : f(fixture) {}
    bool safe_to_commit() override {
        return f.scheduler.idle();
    }
    std::uint64_t monotonic_now_ms() override {
        return now_ms;
    }
    bool station_ready(std::string_view) override {
        return true;
    }
    std::optional<std::uint64_t> trusted_utc_now() override {
        return {};
    }
    std::string_view local_hostname() override {
        return "wsprrypico-0a60df.local";
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
struct Driver {
    std::string device;
    network_test::Fixture f;
    // Independent engineering adapter boundary for genuine served-page tests.
    network_test::Fixture engineering;
    network_test::Flash engineering_progress_flash;
    standalone::Progress engineering_progress{engineering_progress_flash};
    network_test::Flash progress_flash;
    standalone::Progress progress{progress_flash};
    Media media;
    provisioning::ProfileStore profiles{media};
    provisioning::RuntimeProfile runtime;
    HostnamePlatform hostname_platform{f};
    std::optional<provisioning::HostnameSettings> hostname_settings;
    Random random;
    bool low_memory = false, handler_memory_failure = false;
    std::uint64_t last_transaction = 0;
    unsigned api_restarts = 0;
    PsaCryptoOwner engineering_owner;
    PicoConsumerRadioCrypto crypto[4];
    ConsumerRadioApi radio{f.api,
                           profiles,
                           runtime,
                           random,
                           {&crypto[0], &crypto[1], &crypto[2]},
                           device,
                           f.service.status().boot_id,
                           &crypto[3]};
    std::array<tcp_pcb, 2> sockets;
    std::array<std::string, 2> remaining_input;
    struct AccessMedia : provisioning::AccessMedia {
        std::array<std::uint8_t, 8192> bytes;
        AccessMedia() {
            bytes.fill(255);
        }
        bool read(std::size_t at, std::span<std::uint8_t> out) override {
            std::copy_n(bytes.begin() + at, out.size(), out.begin());
            return true;
        }
        bool erase(std::size_t at) override {
            std::fill_n(bytes.begin() + at, 4096, 255);
            return true;
        }
        bool program(std::size_t at, std::span<const std::uint8_t> in) override {
            std::copy(in.begin(), in.end(), bytes.begin() + at);
            return true;
        }
    } access_media;
    provisioning::AccessStore access{access_media};
#ifdef WSPRRY_PICO_BOOTSTRAP_RECOVERY_TEST
    struct Led : provisioning::IndicatorOutput {
        bool write(bool) override {
            return true;
        }
    } led;
    provisioning::IndicatorController indicator{led, device};
    standalone::PicoNetwork network;
    provisioning::PicoConsumerClaimPlatform platform{network};
    unsigned restarts = 0;
    unsigned recovery_requests = 0;
    PicoBootstrapServer server{device, "p158-host",
                               +[](const tcp_pcb* p, void*) { return p->interface == 1; }, this};
    bool page_setup = true;
    void poll_server() {
        server.poll(true, true, page_setup, true, true);
    }
    unsigned connections() const {
        return server.resources().connected ? 1 : 0;
    }
    std::size_t pending_bytes() const {
        return server.resources().pending_tcp_bytes;
    }
#else
    PicoHttpServer server{this, classify, handle, finish};
    void poll_server() {
        server.poll();
    }
    unsigned connections() const {
        return server.connections();
    }
    std::size_t pending_bytes() const {
        return server.pending_bytes();
    }
#endif
    static ConsumerInterface classify(void*, const tcp_pcb* pcb, bool) {
        return pcb->interface == 1 ? ConsumerInterface::AccessPoint : ConsumerInterface::Station;
    }
    static HttpResponse handle(void* p, const HttpRequest& r, ConsumerInterface i,
                               std::uint64_t tx) {
        auto& self = *static_cast<Driver*>(p);
        self.last_transaction = tx;
        if (self.handler_memory_failure)
            wtp::available_memory = +[]() -> std::size_t { return 0; };
        return self.radio.handle(r, now_ms, tx, i);
    }
    static void finish(void* p, std::uint64_t tx, bool delivered) {
        static_cast<Driver*>(p)->radio.finish_request(tx, delivered);
    }
    Driver(unsigned boot = 0, const Media* retained = nullptr,
           const network_test::Flash* saved = nullptr,
           std::string selected_device = std::string(32, '1'),
           const network_test::Flash* saved_progress = nullptr, bool blank = false,
           const AccessMedia* saved_access = nullptr)
        : device(std::move(selected_device)), f(boot, device) {
        if (retained)
            media = *retained;
        if (saved) {
            f.flash = *saved;
            check(f.store.load());
        }
        provisioning::ConsumerProfile p;
        p.device_id = device;
        p.ssid = "test-network";
        p.password = "test-password";
        p.time_server = "192.0.2.1";
        p.callsign = "AA0NT";
        p.locator = "EM18";
        p.power_dbm = 37;
        p.tls_pending = true;
        p.tls.hostname = "wsprrypico-0a60df.local";
        p.request_sha256 = std::string(64, 'a');
        check(profiles.load());
        if (!retained && !blank)
            check(profiles.select(provisioning::ProfileSource::ConsumerProfile,
                                  provisioning::serialize_consumer_profile(p)));
        check(runtime.load(profiles, p.device_id, provisioning::BuildBundleState::Absent));
        f.api.consumer_config(runtime);
        if (saved_progress)
            progress_flash = *saved_progress;
        check(progress.load());
        f.api.progress_settings(progress);
        check(engineering_progress.load());
        engineering.api.progress_settings(engineering_progress);
        check(engineering.store.save(*standalone::parse_config(network_test::config)));
        const auto* consumer = runtime.consumer_profile();
        const auto hostname =
            consumer ? consumer->tls.hostname : std::string("wsprrypico-0a60df.local");
        if (consumer) {
            hostname_settings.emplace(profiles, runtime, hostname_platform, p.device_id, hostname,
                                      "wsprrypico-0a60df.local");
            f.api.hostname_settings(*hostname_settings);
        }
        f.api.restart_control(
            +[](void* p) {
                ++*static_cast<unsigned*>(p);
                return true;
            },
            &api_restarts);
        if (!saved && !blank)
            check(f.scheduler.command("CONFIG " + network_test::config).find("true") !=
                  std::string::npos);
        if (!saved && !blank)
            check(f.store.reserve(1791970000000000000ULL));
        radio.admission(runtime.control_healthy(profiles) &&
                        runtime.consumer_browser_selected(profiles));
        radio.listeners(true, "192.168.1.53", hostname);
        f.api.management_availability(
            {ManagementProfile::Consumer, 1, true, false, false, true, true});
        for (auto& pcb : sockets)
            pcb.closed = true;
        if (saved_access)
            access_media = *saved_access;
        check(access.load());
        radio.password_storage(access, "wspr-0a60df");
#ifdef WSPRRY_PICO_BOOTSTRAP_RECOVERY_TEST
        network.hostname = hostname;
        server.configure(f.service.status().boot_id, access, profiles, random, indicator, network,
                         runtime, platform, "default-password");
        server.station_classifier(+[](const tcp_pcb* p, void*) { return p->interface == 2; }, this);
        server.radio_control(radio);
        server.progress_control(f.api);
        server.restart_control(
            +[](void* p) {
                ++static_cast<Driver*>(p)->restarts;
                return true; // Accepted request, without claiming a physical reboot.
            },
            this);
#endif
        check(server.start());
#ifdef WSPRRY_PICO_BOOTSTRAP_RECOVERY_TEST
        poll_server();
#endif
    }
    void ack(tcp_pcb& pcb, unsigned count = UINT32_MAX) {
        if (pcb.closed || !pcb.pending)
            return;
        count = std::min(count, pcb.pending);
        pcb.pending -= count;
        check(pcb.sent(pcb.arg, &pcb, count) == ERR_OK);
    }
    void poll(bool acknowledge, tcp_pcb& pcb) {
        for (unsigned i = 0; i < 100 && !pcb.closed; ++i) {
            poll_server();
            if (acknowledge)
                ack(pcb);
        }
    }
    static std::string field(const wtp::json::Value& v, std::string_view key) {
        const auto x = v.get(key);
        check(x && x->type() == '"');
        return x->string();
    }
    std::string command(const wtp::json::Value& v) {
        const auto op = field(v, "op");
        if (op == "engineering_request") {
            std::vector<std::uint8_t> body;
            const auto encoded = field(v, "b64");
            check(encoded.empty() || bootstrap_unb64url(encoded, body, 0, max_http_body));
            HttpRequest request{field(v, "method"),
                                field(v, "path"),
                                std::string(body.begin(), body.end()),
                                {{"host", "127.0.0.1:8443"},
                                 {"origin", "https://127.0.0.1:8443"},
                                 {"x-wsprrypico-request", "1"},
                                 {"content-type", "application/json"},
                                 {"if-match", field(v, "match")}}};
            const auto response =
                engineering.api.handle(request, "engineering-test", "127.0.0.1:8443");
            const auto wire = response.wire();
            return "{\"wire\":" +
                   wtp::json::quote(bootstrap_hex(std::span(
                       reinterpret_cast<const std::uint8_t*>(wire.data()), wire.size()))) +
                   "}";
        }
        if (op == "frequency_state") {
            standalone::Store retained(f.flash);
            check(retained.load());
            const auto& config = retained.config();
            return "{\"saved_dial_hz\":" +
                (config && config->wspr_dial_frequency_hz ? std::to_string(*config->wspr_dial_frequency_hz) : "null") +
                ",\"sequence\":\"" + std::to_string(retained.config_sequence()) +
                "\",\"enabled\":" + (config && config->enabled ? "true" : "false") + "}";
        }
        if (op == "flash_failure") {
            f.flash.fail = v.get("fail")->boolean();
            return "{}";
        }
        if (op == "time") {
            std::uint64_t time;
            check(wtp::json::decimal(*v.get("ms"), time));
            now_ms = time;
            radio.poll(now_ms);
            poll_server();
            return "{}";
        }
        if (op == "listeners") {
            radio.listeners(v.get("ap")->raw == "true", field(v, "ip"), field(v, "host"));
            return "{}";
        }
        if (op == "rng") {
            random.fail = v.get("fail")->raw == "true";
            if (const auto zero = v.get("zero"))
                random.zero = zero->raw == "true";
            return "{}";
        }
        if (op == "exhaust") {
            std::array<std::uint8_t, 16> id{};
            check(bootstrap_unhex(field(v, "id"), id));
            ConsumerRadioTestAccess::exhaust(radio, id);
            return "{}";
        }
        if (op == "delivery") {
            std::uint64_t tx;
            check(wtp::json::decimal(*v.get("tx"), tx));
            radio.finish_request(tx, v.get("apply")->raw == "true");
            return "{}";
        }
        if (op == "handler_memory") {
            handler_memory_failure = v.get("fail")->raw == "true";
            return "{}";
        }
        if (op == "memory") {
            low_memory = v.get("fail")->raw == "true";
            return "{}";
        }
        if (op == "psa_owner") {
            if (v.get("active")->raw == "true")
                check(engineering_owner.acquire() == PSA_SUCCESS);
            else
                engineering_owner.release();
            return "{}";
        }
        if (op == "generation") {
            auto profile = *runtime.consumer_profile();
            profile.ssid = "changed-network";
            profile.request_sha256 = std::string(64, 'b');
            check(profiles.select(provisioning::ProfileSource::ConsumerProfile,
                                  provisioning::serialize_consumer_profile(profile)));
            check(runtime.load(profiles, device, provisioning::BuildBundleState::Absent));
            f.api.management_availability(
                {ManagementProfile::Consumer, profiles.sequence(), true, false, false, true, true});
            radio.poll(now_ms);
            return "{}";
        }
        if (op == "invalidate") {
            radio.admission(false);
            radio.admission(true);
            return "{}";
        }
        if (op == "stats")
            return "{\"api_restarts\":" + std::to_string(api_restarts) +
                   ",\"transaction\":" + wtp::json::quote(std::to_string(last_transaction)) +
                   ",\"connections\":" + std::to_string(connections()) +
                   ",\"pending_bytes\":" + std::to_string(pending_bytes()) +
                   ",\"profile_programs\":" + std::to_string(media.programs) +
                   ",\"profile_generation\":" +
                   wtp::json::quote(std::to_string(profiles.sequence())) + ",\"config_sequence\":" +
                   wtp::json::quote(std::to_string(f.store.config_sequence())) +
#ifdef WSPRRY_PICO_BOOTSTRAP_RECOVERY_TEST
                   ",\"trial_starts\":" + std::to_string(network.starts + platform.trial_starts) +
                   ",\"setup_pending\":" + (server.setup_pending() ? "true" : "false") +
                   ",\"network_slot\":" + std::to_string(server.resources().network_slot_state) +
                   ",\"owner_slot\":" + std::to_string(server.resources().owner_slot_state) +
                   ",\"restarts\":" + std::to_string(restarts) +
                   ",\"recovery_requests\":" + std::to_string(recovery_requests) +
#endif
                   ",\"network_enabled\":" + (f.network.enabled ? "true" : "false") +
                   ",\"network_pending\":" + (f.network.pending ? "true" : "false") +
                   ",\"psa_owners\":" + std::to_string(PsaCryptoOwner::owners()) + "}";
#ifdef WSPRRY_PICO_BOOTSTRAP_RECOVERY_TEST
        if (op == "page_profile") {
            const auto mode = field(v, "mode");
            if (mode != "unavailable") {
                media = Media{};
                check(profiles.load());
            }
            // Virgin blank setup requires an erased generation-zero journal.
            // Selecting an Unprovisioned tombstone creates generation one and
            // correctly fails the production blank-authority gate instead.
            if (mode == "blank" || mode == "recovery")
                network.linked = false;
            else if (mode == "network") {
                network.linked = true;
                check(profiles.select(provisioning::ProfileSource::NetworkOnly,
                                      provisioning::serialize_network_profile(
                                          {device, "Home Net", "test-password"})));
            } else
                check(mode == "unavailable");
            page_setup = mode != "unavailable";
            if (mode != "unavailable")
                check(runtime.load(profiles, device, provisioning::BuildBundleState::Absent));
            if (mode == "unavailable")
                radio.admission(false);
            if (mode == "recovery") {
                server.configure_recovery(f.service.status().boot_id, access, random);
                server.reset_control(
                    +[](provisioning::ResetLevel, const wtp::PayloadDigest&, void* context) {
                        // Board reset is the boundary double. Production crypto,
                        // slot admission and HTTP dispatch remain unchanged.
                        ++static_cast<Driver*>(context)->recovery_requests;
                        return provisioning::ResetResult::Complete;
                    },
                    this);
            }
            poll_server();
            return "{}";
        }
        if (op == "bench_network") {
            network.linked = v.get("linked")->raw == "true";
            platform.safe = v.get("safe")->raw == "true";
            if (const auto start = v.get("start_ok"))
                network.start_ok = start->raw == "true";
            return "{}";
        }
        if (op == "activate") {
            check(runtime.load(profiles, device, provisioning::BuildBundleState::Absent));
            f.api.management_availability(
                {ManagementProfile::Consumer, profiles.sequence(), true, false, false, true, true});
            poll_server();
            return "{}";
        }
#endif
        if (op == "wire") {
            std::uint64_t index;
            check(wtp::json::decimal(*v.get("socket"), index) && index < 2);
            const auto& pcb = sockets[index];
            return "{\"closed\":" + std::string(pcb.closed ? "true" : "false") + ",\"wire\":" +
                   wtp::json::quote(bootstrap_hex(std::span(
                       reinterpret_cast<const std::uint8_t*>(pcb.wire.data()), pcb.wire.size()))) +
                   "}";
        }
        if (op == "continue") {
            std::uint64_t index;
            check(wtp::json::decimal(*v.get("socket"), index) && index < 2);
            auto& pcb = sockets[index];
            const auto input = std::move(remaining_input[index]);
            for (std::size_t at = 0; at < input.size(); at += 317) {
                pbuf packet{static_cast<u16_t>(std::min<std::size_t>(317, input.size() - at)),
                            input.data() + at};
                check(!pcb.closed);
                pcb.receive(pcb.arg, &pcb, &packet, ERR_OK);
            }
            poll(true, pcb);
            return "{}";
        }
        if (op == "complete" || op == "fin" || op == "rst" || op == "ack") {
            std::uint64_t index;
            check(wtp::json::decimal(*v.get("socket"), index) && index < 2);
            auto& pcb = sockets[index];
            if (!pcb.closed) {
                if (op == "complete")
                    poll(true, pcb);
                else if (op == "fin")
                    pcb.receive(pcb.arg, &pcb, nullptr, ERR_OK);
                else if (op == "rst") {
                    auto cb = pcb.error;
                    auto arg = pcb.arg;
                    pcb.closed = true;
                    cb(arg, ERR_ABRT);
                } else {
                    std::uint64_t n;
                    check(wtp::json::decimal(*v.get("bytes"), n));
                    ack(pcb, n);
                }
            }
            return "{}";
        }
        check(op == "request");
        unsigned index = 0;
        while (index < 2 && !sockets[index].closed)
            ++index;
        check(index < 2);
        auto& pcb = sockets[index];
        pcb = {};
        pcb.interface = v.get("ap")->raw == "true" ? 1 : 2;
        check(listener.accept(listener.arg, &pcb, ERR_OK) == ERR_OK);
        std::vector<std::uint8_t> bytes;
        const auto body = field(v, "b64");
        check(body.empty() || bootstrap_unb64url(body, bytes, 0, max_http_body));
        const auto host = field(v, "host");
        const auto marker = v.get("marker") ? field(v, "marker") : "Radio";
        check(marker == "Radio" || marker == "Bootstrap" || marker == "Owner");
        const auto request = field(v, "method") + " " + field(v, "path") +
                             " HTTP/1.1\r\nHost: " + host + "\r\nOrigin: http://" + host +
                             "\r\nX-WsprryPico-" + marker +
                             ": 1\r\nContent-Type: " + field(v, "type") +
                             "\r\nContent-Length: " + std::to_string(bytes.size()) + "\r\n\r\n" +
                             std::string(bytes.begin(), bytes.end());
        wtp::available_memory = low_memory ? +[]() -> std::size_t { return 0; } : nullptr;
        std::uint64_t cutoff = request.size();
        if (const auto cut = v.get("cut"))
            check(wtp::json::decimal(*cut, cutoff) && cutoff < request.size());
        remaining_input[index] = request.substr(cutoff);
        // pbuf fragments exercise the production parser without requiring a real socket.
        for (std::size_t at = 0; at < cutoff && !pcb.closed; at += 317) {
            pbuf packet{static_cast<u16_t>(std::min<std::size_t>(317, cutoff - at)),
                        request.data() + at};
            pcb.receive(pcb.arg, &pcb, &packet, ERR_OK);
        }
        poll(v.get("hold")->raw != "true", pcb);
        wtp::available_memory = nullptr;
        return "{\"socket\":" + std::to_string(index) + ",\"wire\":" +
               wtp::json::quote(bootstrap_hex(std::span(
                   reinterpret_cast<const std::uint8_t*>(pcb.wire.data()), pcb.wire.size()))) +
               "}";
    }
};
} // namespace
int main(int argc, char** argv) {
    const std::string device = argc >= 2 ? argv[1] : std::string(32, '1');
    const bool blank = argc == 3 && std::string_view(argv[2]) == "--blank";
    check(valid_device_id(device));
    unsigned boot = 0;
    auto driver = std::make_unique<Driver>(boot, nullptr, nullptr, device, nullptr, blank);
    std::cerr << "ConsumerRadioApi=" << sizeof(ConsumerRadioApi)
              << " crypto=" << sizeof(PicoConsumerRadioCrypto) << " HTTP=" << sizeof(PicoHttpServer)
              << '\n';
    std::string line;
    while (std::getline(std::cin, line)) {
        const auto root = wsprrypico::wtp::json::parse(line);
        check(bool(root));
        if (root->get("op")->string() == "reboot") {
            const auto media = driver->media;
            const auto flash = driver->f.flash;
            const auto progress_flash = driver->progress_flash;
            const auto access_media = driver->access_media;
            driver.reset();
            driver = std::make_unique<Driver>(++boot, &media, &flash, device, &progress_flash,
                                              false, &access_media);
            std::cout << "{}" << std::endl;
        } else
            std::cout << driver->command(*root) << std::endl;
    }
}

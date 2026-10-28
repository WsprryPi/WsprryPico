// SPDX-License-Identifier: MIT
#include "logging/logger.hpp"
#include "logging/udp_sender.hpp"
#include "logging/udp_settings.hpp"
#include "logging/udp_wire.hpp"
#include "network/local_usb_api.hpp"
#include "network_support.hpp"

#include <cassert>
#include <limits>
#include <string>
#include <vector>
using namespace wsprry::logging;
using namespace std::string_literals;
int main() {
    using namespace wsprrypico::logging;
    for (const auto bad :
         {"", "0.1.2.3", "127.0.0.1", "224.1.2.3", "255.255.255.255", "192.168.01.1", "192.168.1",
          "192.168.1.256", "192.168.1.2 ", "example.com", "::1"})
        assert(!udp_ipv4(bad));
    assert(udp_ipv4("192.168.1.2") == 0xc0a80102U);
    UdpSender sender(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
    UdpSettings settings;
    settings.enabled = true;
    settings.destination_ipv4.assign("192.168.1.2");
    assert(sender.configure(settings));
    sender.network(1, true, true);
    Logger logger(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
    logger.udp_sink(sender);
    logger.event(6, "USB_STATE", "USB control connection changed", 0);
    assert(sender.queued() == 1 && logger.queued() == 0);
    logger.event(6, "USB_STATE", "password=secret", 0);
    assert(sender.counters().redacted_rejected == 1 && sender.queued() == 1);
    logger.connected(false);
    assert(sender.queued() == 1);
    unsigned sent = 0;
    sender.poll(0, [&](std::string_view data) {
        UdpEvent parsed;
        assert(decode_udp(data, parsed));
        ++sent;
        return true;
    });
    assert(sent == 1 && sender.counters().locally_submitted == 1);
    for (unsigned i = 0; i < 20; ++i)
        logger.event(6, "USB_STATE", "USB control connection changed", 1);
    assert(sender.queued() == 16 && sender.counters().overflow == 4);
    sender.poll(1, [](auto) { return false; });
    assert(sender.counters().locally_failed == 1 && sender.queued() == 15);
    sender.network(2, true, true);
    assert(sender.queued() == 0 && sender.counters().reconfigured_drops == 15);
    logger.event(6, "USB_STATE", "USB control connection changed", 2);
    sender.network(2, false, false);
    sender.poll(5'000'000'002ULL, [](auto) {
        assert(false);
        return false;
    });
    assert(sender.counters().expired == 1 && sender.queued() == 0);
    settings.enabled = false;
    assert(sender.configure(settings));
    logger.event(6, "USB_STATE", "USB control connection changed", 3);
    assert(sender.queued() == 0);
    // A delayed USB write must not change an already-created origin record
    // when later USB admissions fail independently of UDP.
    {
        UdpSender independent(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
        settings.enabled = true;
        assert(independent.configure(settings));
        independent.network(1, true, true);
        Logger delayed(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
        delayed.udp_sink(independent);
        delayed.settings({true, 6});
        delayed.connected(true);
        assert(delayed.start(std::string(32, 'a'), std::string(32, 'b')));
        delayed.event(6, "USB_STATE", "USB control connection changed", 0);
        const std::string original(delayed.front());
        for (unsigned i = 0; i < 9; ++i)
            delayed.event(6, "USB_STATE", "USB control connection changed", 1);
        assert(delayed.dropped() == 2);
        assert(delayed.front() == original);
        assert(original.find("\"dropped\":\"0\"") != std::string::npos);
        independent.poll(1, [&](std::string_view data) {
            UdpEvent parsed;
            assert(decode_udp(data, parsed) && parsed.sequence == 1 && parsed.dropped == 0);
            return true;
        });
    }
    // Template-backed queue storage preserves every admitted event even after
    // caller-owned text is overwritten. It never keeps caller string views.
    for (const auto& approved : pico_export_templates) {
        UdpSender compact(std::string(32, 'a'), std::string(32, 'b'), "pico.local");
        assert(compact.configure(settings));
        compact.network(1, true, true);
        std::string code(approved.code), text(approved.message);
        compact.event(1, 6, code, text, 1, 0, 0);
        code.assign("changed");
        text.assign("private caller data");
        bool submitted = false;
        compact.poll(1, [&](std::string_view data) {
            UdpEvent parsed;
            assert(decode_udp(data, parsed));
            assert(parsed.code.view() == approved.code &&
                   parsed.message.view() == approved.message);
            submitted = true;
            return true;
        });
        assert(submitted);
    }
    settings.enabled = true;
    settings.rate = 0;
    assert(!sender.configure(settings) && !sender.settings().enabled);
    UdpEvent e;
    e.origin.assign(std::string(32, 'a'));
    e.boot.assign(std::string(32, 'b'));
    e.hostname.assign("pico.local");
    e.code.assign("BOOT");
    e.message.assign("Hello world");
    e.sequence = 1;
    std::array<char, 480> buffer{};
    bool truncated{};
    const auto packet = std::string(encode_udp(e, buffer, truncated));
    assert(!packet.empty() && !truncated);
    assert(packet.starts_with("<190>1 - pico.local WsprryPico - BOOT - [\"wsprry-udp/1\""));
    UdpEvent received;
    assert(decode_udp(packet, received));
    assert(received.message.view() == e.message.view() && received.sequence == 1 &&
           !received.utc_ns);
    for (auto n :
         {0ULL, 1'700'000'000'123'456'789ULL, std::numeric_limits<unsigned long long>::max()}) {
        e.utc_ns = n;
        assert(decode_udp(encode_udp(e, buffer, truncated), received));
        assert(received.utc_ns == n);
    }
    e.hostname.assign(std::string(63, 'h'));
    e.code.assign(std::string(32, 'E'));
    e.sequence = e.monotonic_ns = e.dropped = std::numeric_limits<std::uint64_t>::max();
    e.relayed = true;
    e.relay_id.assign(std::string(32, 'c'));
    e.relay_receipt_us = e.sequence;
    e.message.assign(std::string(192, '"'));
    const auto bounded = std::string(encode_udp(e, buffer, truncated));
    assert(bounded.size() == 479 && truncated); // 401-byte metadata + 39 two-byte escapes
    assert(decode_udp(bounded, received));
    assert(received.message.size == 39 && received.relay_id.view() == std::string(32, 'c'));
    e.message.assign(std::string(192, 'x'));
    const auto full = std::string(encode_udp(e, buffer, truncated));
    assert(full.size() == 480 && truncated && decode_udp(full, received));
    assert(!decode_udp(full + " ", received));
    assert(!decode_udp(full, received, e.origin.view()));
    assert(!decode_udp(full, received, e.relay_id.view()));
    for (std::size_t i = 0; i < full.size(); ++i)
        assert(!decode_udp(std::string_view(full).substr(0, i), received));
    const auto replace = [&](std::string from, std::string to) {
        auto s = packet;
        const auto at = s.find(from);
        assert(at != std::string::npos);
        s.replace(at, from.size(), to);
        return s;
    };
    const std::vector<std::string> invalid = {
        "",
        "\xef\xbb\xbf" + packet,
        packet + "\n",
        packet + "\0junk"s,
        replace("wsprry-udp/1", "wsprry-udp/2"),
        replace("<190>", "<30>"),
        replace("<190>", "<0190>"),
        replace("\"pico\"", "\"pi\""),
        replace("\"1\"", "\"01\""),
        replace("\"1\"", "1"),
        replace("\"1\"", "true"),
        replace("\"1\"", "\"18446744073709551616\""),
        replace("\"1\"", "\"0\""),
        replace("\"Hello world\"", "{\"message\":\"Hello world\"}"),
        replace("\"Hello world\"", "\"Hello\\nworld\""),
        replace("null]", "null,0]"),
        replace("null]", "[\"cccccccccccccccccccccccccccccccc\",\"1\",\"udp\"]]"),
        replace("<190>1 - ", "<190>1 2023-11-14T22:13:20.000000Z ")};
    for (const auto& bad : invalid) {
        received.sequence = 77;
        assert(!decode_udp(bad, received));
        assert(received.sequence == 77);
    }
    e.pico = false;
    assert(encode_udp(e, buffer, truncated).empty()); // no native-Pi relay
    e.relayed = false;
    assert(decode_udp(encode_udp(e, buffer, truncated), received) && !received.pico);
    network_test::Fixture f;
    network_test::Flash udp_flash;
    UdpStore storage(udp_flash);
    assert(storage.load());
    UdpSender managed(std::string(32, 'a'), f.service.status().boot_id, "pico.local");
    f.api.udp_logging_service(storage, managed);
    Logger managed_logger(std::string(32, 'a'), f.service.status().boot_id, "pico.local");
    managed_logger.udp_sink(managed);
    f.api.logging_service(managed_logger);
    wsprrypico::network::LocalUsbApi usb(f.api);
    wsprrypico::network::HttpRequest req;
    req.method = "GET";
    req.path = "/api/v1/udp-logging/capabilities";
    const auto caps = usb.handle(req);
    assert(caps.status == 200 &&
           caps.body_text().find("udp-logging-capabilities/1") != std::string::npos);
    req.path = "/api/v1/udp-logging";
    auto read = usb.handle(req);
    assert(read.status == 200);
    const auto read_body = read.body_text();
    const auto root = wsprrypico::wtp::json::parse(read_body);
    assert(root && root->get("saved"));
    settings.rate = 4;
    req.method = "PUT";
    req.headers["if-match"] = read.etag;
    const auto envelope = [&](const UdpSettings& config) {
        return "{\"schema\":\"transmitter-udp-logging/1\",\"target\":" +
               std::string(root->get("target")->raw) +
               ",\"settings\":" + udp_settings_json(config) + "}";
    };
    req.body = envelope(settings);
    assert(usb.handle(req).status == 200 && storage.settings().enabled);
    assert(usb.handle(req).status == 412); // stale revision refuses before writes
    UdpStore reboot(udp_flash);
    assert(reboot.load() && reboot.settings() == settings);
    const auto seq = storage.sequence();
    req.method = "GET";
    read = usb.handle(req);
    req.path = "/api/v1/udp-logging/test/capabilities";
    assert(usb.handle(req).status == 200);
    req.path = "/api/v1/udp-logging/test";
    req.method = "POST";
    req.headers["if-match"] = read.etag;
    req.body =
        "{\"schema\":\"udp-logging-test/1\",\"target\":" + std::string(root->get("target")->raw) +
        "}";
    assert(usb.handle(req).status == 200 && managed.queued() == 1 && storage.sequence() == seq);
    assert(usb.handle(req).status == 429 && managed.queued() == 1);
    f.clock.now += 500'000'000;
    req.body.insert(req.body.size() - 1, ",\"extra\":true");
    assert(usb.handle(req).status == 400 && managed.queued() == 1 && storage.sequence() == seq);
    req.path = "/api/v1/udp-logging";

    req.method = "GET";
    read = usb.handle(req);
    req.method = "PUT";
    req.headers["if-match"] = read.etag;
    req.body = envelope(settings);
    req.body.insert(req.body.size() - 1, ",\"extra\":true");
    assert(usb.handle(req).status == 400 && storage.sequence() == seq);
    for (const auto& bad : {"null", "[]", "{}", "true", "{\"enabled\":true}"}) {
        const auto document = wsprrypico::wtp::json::parse(bad);
        assert(!document || !parse_udp_settings(*document));
    }
    struct DeniedNetwork final : network_test::Network {
        bool udp_destination_allowed(std::string_view) const override {
            return false;
        }
    } denied_network;
    wsprrypico::network::BrowserApi denied_api(f.service, f.store, f.scheduler, denied_network,
                                               std::string(32, 'a'), "udp-policy-test");
    denied_api.udp_logging_service(storage, managed);
    wsprrypico::network::LocalUsbApi denied_usb(denied_api);
    req.body = envelope(settings);
    assert(denied_usb.handle(req).status == 400 && storage.sequence() == seq);
    udp_flash.fail = true;
    req.body = envelope(settings);
    assert(usb.handle(req).status == 503 && !managed.settings().enabled && managed.queued() == 0);
    udp_flash.bytes[2048] = 0; // emulate an interrupted second record
    UdpStore damaged(udp_flash);
    assert(!damaged.load());
}

#include "application/resources.hpp"
#include "network/identity.hpp"
#include "network_support.hpp"
#include "provisioning/hostname.hpp"

#include <cassert>
using namespace wsprrypico;
namespace {
constexpr auto device = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
struct MemoryMedia : provisioning::Media {
    std::array<std::uint8_t, provisioning::profile_media_size> bytes{};
    unsigned writes = 0, fail_at = 0, fail_read_after = 0;
    bool fail_erase = false, write_then_fail = false;
    MemoryMedia() {
        bytes.fill(255);
    }
    bool read(std::size_t at, std::span<std::uint8_t> out) override {
        if ((fail_read_after && writes >= fail_read_after) || at > bytes.size() ||
            out.size() > bytes.size() - at)
            return false;
        std::copy_n(bytes.begin() + at, out.size(), out.begin());
        return true;
    }
    bool erase(std::size_t at) override {
        if (fail_erase)
            return false;
        if (at % provisioning::profile_slot_size ||
            at > bytes.size() - provisioning::profile_slot_size)
            return false;
        std::fill_n(bytes.begin() + at, provisioning::profile_slot_size, 255);
        return true;
    }
    bool program(std::size_t at, std::span<const std::uint8_t> page) override {
        const bool failed = ++writes == fail_at;
        if (failed && !write_then_fail)
            return false;
        for (std::size_t i = 0; i < page.size(); ++i)
            bytes[at + i] &= page[i];
        return !failed;
    }
};

struct Platform : provisioning::ConsumerClaimCommitPlatform {
    bool safe = true, generated = true, rotate = false, race = false, tls_valid = true,
         timed = true;
    bool safe_to_commit() override {
        return safe;
    }
    std::uint64_t monotonic_now_ms() override {
        return 1000;
    }
    bool station_ready(std::string_view) override {
        return true;
    }
    std::optional<std::uint64_t> trusted_utc_now() override {
        return timed ? std::optional<std::uint64_t>{1'800'000'000} : std::nullopt;
    }
    std::string_view local_hostname() override {
        return "old.local";
    }
    bool valid_owner_point(std::string_view) override {
        return true;
    }
    bool generate_tls(std::string_view, std::string_view, std::uint64_t,
                      provisioning::ConsumerTls&) override {
        return false;
    }
    bool valid_tls(const provisioning::ConsumerTls&, std::string_view, std::uint64_t) override {
        return tls_valid;
    }
    bool rename_tls(std::string_view, std::string_view name, std::uint64_t,
                    provisioning::ConsumerTls& out) override {
        if (race)
            safe = false;
        if (rotate)
            out.ca_private_key += 'x';
        out.hostname = name;
        return generated;
    }
};
provisioning::ConsumerProfile consumer() {
    provisioning::ConsumerProfile p;
    p.device_id = device;
    p.ssid = "test-network";
    p.password = "test-password";
    p.time_server = "192.0.2.1";
    p.callsign = "AA0NT";
    p.locator = "EM18";
    p.power_dbm = 37;
    p.tls_pending = true;
    p.tls.hostname = "old.local";
    p.request_sha256 = std::string(64, 'a');
    return p;
}
struct Test {
    network_test::Fixture f;
    MemoryMedia media;
    provisioning::ProfileStore store{media};
    provisioning::RuntimeProfile runtime;
    Platform platform;
    provisioning::HostnameSettings settings{store,  runtime,     platform,
                                            device, "old.local", "default.local"};
    Test() {
        assert(store.load());
        assert(store.select(provisioning::ProfileSource::ConsumerProfile,
                            provisioning::serialize_consumer_profile(consumer())));
        assert(runtime.load(store, device, provisioning::BuildBundleState::Absent));
        f.api.consumer_config(runtime);
        f.api.hostname_settings(settings);
    }
    network::HttpResponse request(std::string_view name, std::string revision = "current",
                                  std::string target = device) {
        network::HttpRequest r;
        r.path = "/api/control/v1/hostname";
        r.method = "PUT";
        r.headers = {{"host", "127.0.0.1"},
                     {"origin", "https://127.0.0.1"},
                     {"content-type", "application/json"},
                     {"x-wsprrypico-request", "1"}};
        if (!revision.empty())
            r.headers["if-match"] = revision == "current" ? f.api.revision() : revision;
        r.body = "{\"schema\":\"hostname\",\"target\":" +
                 application::target(target, f.service.status().boot_id) +
                 ",\"hostname\":" + std::string(name) + "}";
        return f.api.handle(network_test::control_request(r), "test", "127.0.0.1");
    }
};
} // namespace
int main() {
    Test t;
    const auto original = t.store.data(), rev = t.f.api.revision();
    const auto watermark = t.f.store.watermark();
    assert(t.request("\"pico-a.local\"", "").status == 428);
    assert(t.request("\"pico-a.local\"", "bad").status == 412);
    assert(t.request("\"pico-a.local\"", "current", std::string(32, 'b')).status == 409);
    assert(t.store.data() == original);
    for (const auto& name :
         {"", "bare", "-bad.local", "bad-.local", "a.b.local", "http://a.local", "a.local:80",
          "192.0.2.1", "a_.local", "a local", "a.local\n", "é.local", "<script>.local"})
        assert(t.request(wtp::json::quote(name)).status == 400);
    assert(t.request(wtp::json::quote(std::string(64, 'a') + ".local")).status == 400);
    auto response = t.request("\"Pico-A.LOCAL.\"");
    if (response.status != 200)
        std::cerr << response.status << " " << response.body << "\n";
    assert(response.status == 200 &&
           response.body.find("\"active\":\"old.local\"") != response.body.npos);
    assert(t.runtime.consumer_profile()->tls.hostname == "pico-a.local");
    assert(t.runtime.generation() == 2 && t.store.sequence() == 2);
    assert(t.request("\"pico-a.local\"", rev).status == 412);
    assert(t.request("\"PICO-A.LOCAL.\"").status == 200 && t.store.sequence() == 2);
    auto expected = consumer();
    expected.tls.hostname = "pico-a.local";
    assert(t.store.data() == provisioning::serialize_consumer_profile(expected));
    assert(t.f.store.watermark() == watermark);
    assert(t.request("null").status == 200 &&
           t.runtime.consumer_profile()->tls.hostname == "default.local");
    assert(t.request("\"old.local\"").status == 200 && t.store.sequence() == 4);
    assert(t.f.api.revision() != rev); // A/B/A does not revive a consumed revision.
    t.platform.safe = false;
    assert(t.request("\"pico-a.local\"").status == 409);
    t.platform.safe = true;
    for (const auto length : {1, 63}) {
        assert(t.request(wtp::json::quote(std::string(length, 'x') + ".local")).status == 200);
        provisioning::ProfileStore reloaded(t.media);
        assert(reloaded.load() && reloaded.data() == t.store.data());
    }
    // Interrupt every page, including the commit marker, and reconstruct a new store.
    for (unsigned at = 1; at <= 8; ++at) {
        Test cut;
        const auto before = cut.store.data();
        cut.media.fail_at = cut.media.writes + at;
        const auto result = cut.request("\"changed.local\"");
        provisioning::ProfileStore recovered(cut.media);
        assert(recovered.load());
        assert(result.status == 200 || recovered.data() == before);
        auto parsed = provisioning::parse_consumer_profile(recovered.data());
        assert(parsed);
        assert(parsed->tls.hostname == (result.status == 200 ? "changed.local" : "old.local"));
    }
    Test lost;
    lost.media.fail_at = lost.media.writes + 5;
    lost.media.write_then_fail = true;
    (void)lost.request("\"changed.local\"");
    provisioning::ProfileStore durable(lost.media);
    assert(durable.load());
    assert(lost.runtime.generation() == durable.sequence());
    Test fault;
    fault.media.fail_read_after = fault.media.writes + 1;
    const auto failed = fault.request("\"fault.local\"");
    assert(failed.status == 503 &&
           failed.body.find("hostname_reconcile_required") != failed.body.npos);
    assert(!fault.store.healthy() && fault.runtime.source() == provisioning::RuntimeSource::Fault);
    assert(fault.runtime.consumer_selected(fault.store));
    assert(!fault.runtime.control_healthy(fault.store));
    assert(fault.request("\"retry.local\"").status == 503);
    // Exactly the main-loop admission predicates: neither legacy nor consumer authority opens.
    const bool legacy =
        fault.runtime.control_healthy(fault.store) && !fault.runtime.consumer_selected(fault.store);
    const bool consumer_admitted =
        fault.runtime.control_healthy(fault.store) && fault.runtime.consumer_selected(fault.store);
    assert(!legacy && !consumer_admitted);
    Test certified;
    auto full = *certified.runtime.consumer_profile();
    full.tls_pending = false;
    full.tls.ca_certificate = "-----BEGIN CERTIFICATE-----\nAQ==\n-----END CERTIFICATE-----\n";
    full.tls.server_certificate = full.tls.ca_certificate;
    full.tls.ca_private_key = "-----BEGIN PRIVATE KEY-----\nAQ==\n-----END PRIVATE KEY-----\n";
    full.tls.server_private_key = full.tls.ca_private_key;
    full.tls.ca_not_after_utc = 2'000'000'000;
    full.tls.server_not_after_utc = 1'900'000'000;
    assert(certified.store.select(provisioning::ProfileSource::ConsumerProfile,
                                  provisioning::serialize_consumer_profile(full)));
    assert(certified.runtime.load(certified.store, device, provisioning::BuildBundleState::Absent));
    const auto prior = certified.store.data();
    certified.platform.generated = false;
    assert(certified.request("\"new.local\"").status == 409);
    certified.platform.generated = true;
    certified.platform.rotate = true;
    assert(certified.request("\"new.local\"").body.find("hostname_trust_changed") !=
           std::string::npos);
    certified.platform.rotate = false;
    certified.platform.race = true;
    assert(certified.request("\"new.local\"").status == 409);
    certified.platform.race = false;
    certified.platform.safe = true;
    certified.platform.tls_valid = false;
    assert(certified.request("\"new.local\"").status == 409);
    certified.platform.tls_valid = true;
    certified.platform.timed = false;
    assert(certified.request("\"new.local\"").status == 409);
    assert(certified.store.data() == prior && certified.store.sequence() == 2);
    certified.platform.timed = true;
    assert(certified.request("\"new.local\"").status == 200);
    full.tls.hostname = "new.local";
    assert(certified.store.data() == provisioning::serialize_consumer_profile(full));
    Test busy;
    assert(busy.f.scheduler.command("CONFIG " + network_test::config).find("true") !=
           std::string::npos);
    assert(busy.f.scheduler.idle());
    wtp::Request claim;
    claim.payload_digest[0] = 1;
    claim.principal = "owner";
    claim.session_id = std::string(32, 'b');
    claim.request_id = std::string(32, '1');
    claim.operation = "HELLO";
    claim.body = wtp::HelloBody{{"WTP/1"}};
    assert(busy.f.service.handle(claim).ok);
    claim.operation = "CLAIM";
    claim.request_id = std::string(32, '2');
    claim.body = wtp::ClaimBody{std::string(32, 'b'), 30000};
    assert(busy.f.service.handle(claim).ok);
    assert(busy.request("\"busy.local\"").status == 409 && busy.store.sequence() == 1);
    assert(t.store.select(provisioning::ProfileSource::Unprovisioned));
    assert(t.request("\"x.local\"").status == 409);
}

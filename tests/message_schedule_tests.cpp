#include "application/resources.hpp"
#include "network/local_usb_api.hpp"
#include "network_support.hpp"
#include "standalone/message_schedule.hpp"

#include <cassert>
#include <iostream>
using namespace wsprrypico;
namespace {
constexpr std::uint64_t ns = 1'000'000'000ULL;
standalone::MessageSchedule schedule(std::uint64_t first, unsigned period = 60) {
    standalone::MessageSchedule s;
    s.enabled = true;
    s.first_start_utc_ns = first;
    s.period_s = period;
    s.message.job_id = std::string(32, '0');
    s.message.mode = "qrss";
    s.message.text = "E";
    s.message.mark_frequency_nhz = 10140000000000000ULL;
    s.message.dot_ns = ns;
    s.message.dash_ns = 3 * ns;
    s.message.intra_gap_ns = ns;
    s.message.character_gap_ns = 3 * ns;
    s.message.word_gap_ns = 7 * ns;
    s.message.repeat_count = 1;
    s.message.allow_frequency_adjustment = true;
    return s;
}
network::HttpResponse call(network_test::Fixture& f, std::string method, std::string path,
                           std::string body = {}, std::string revision = {}) {
    network::HttpRequest r;
    r.method = std::move(method);
    r.path = std::move(path);
    r.body = std::move(body);
    r.headers = {{"host", "127.0.0.1:8443"},
                 {"origin", "https://127.0.0.1:8443"},
                 {"x-wsprrypico-request", "1"},
                 {"content-type", "application/json"}};
    if (!revision.empty())
        r.headers["if-match"] = revision;
    auto result = f.api.handle(r, "peer", "127.0.0.1:8443");
    if (result.status >= 400 && r.path == "/api/v1/jobs")
        std::cerr << result.status << ": " << result.body << std::endl;
    return result;
}
std::string envelope(network_test::Fixture& f, const standalone::MessageSchedule& s) {
    return "{\"schema\":\"transmitter-message-schedule/1\",\"target\":" +
           application::target(std::string(32, 'a'), f.service.status().boot_id) +
           ",\"schedule\":" + standalone::serialize_message_schedule(s) + "}";
}
void advance(network_test::Fixture& f, std::uint64_t monotonic) {
    f.clock.now = monotonic;
    f.scheduler.poll();
}
} // namespace
int main() {
    const auto anchor = 1793001605000000000ULL;
    for (const unsigned minutes : {7U, 20U, 90U}) {
        const auto s = schedule(anchor, minutes * 60);
        const auto period = std::uint64_t{minutes} * 60 * ns;
        assert(standalone::next_message_slot(s, anchor, 0) == anchor);
        assert(standalone::next_message_slot(s, anchor + 1, 0) == anchor + period);
        assert(standalone::next_message_slot(s, anchor + period, anchor + period) ==
               anchor + 2 * period);
        assert(standalone::next_message_slot(s, anchor + 86400 * ns, 0) ==
               anchor + ((86400 * ns + period - 1) / period) * period);
        assert(!standalone::next_message_slot(s, anchor, UINT64_MAX));
    }
    {
        auto s = schedule(anchor);
        s.message.mode = "dfcw";
        s.message.space_frequency_nhz = s.message.mark_frequency_nhz + 5 * ns;
        const auto encoded = standalone::serialize_message_schedule(s);
        assert(standalone::parse_message_schedule(*wtp::json::parse(encoded)));
        s.message.text = "E\tE";
        const auto control = standalone::serialize_message_schedule(s);
        assert(!standalone::parse_message_schedule(*wtp::json::parse(control)));
        s.message.text = "E";
        s.message.space_frequency_nhz = s.message.mark_frequency_nhz - 5 * ns;
        const auto negative = standalone::serialize_message_schedule(s);
        assert(!standalone::parse_message_schedule(*wtp::json::parse(negative)));
    }
    {
        network_test::Fixture f;
        const auto s = schedule(f.clock.snapshot().utc_now_ns + 60 * ns);
        assert(f.store.save_message_schedule(s));
        f.flash.fail = true;
        advance(f, 56 * ns);
        assert(f.service.status().state == wtp::State::Empty);
        assert(!f.store.healthy() && f.scheduler.message_recovery_required());
    }
    {
        auto s = schedule(anchor);
        auto encoded = standalone::serialize_message_schedule(s);
        assert(standalone::parse_message_schedule(*wtp::json::parse(encoded)));
        s.message.text = std::string(33, 'E');
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.message.dot_ns = 59 * ns; // Tail and preparation cannot fit a minute.
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.period_s = 61;
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.expires_utc_s = anchor / ns + 1;
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
        s = schedule(anchor);
        s.message.repeat_count = 512;
        assert(!standalone::parse_message_schedule(
            *wtp::json::parse(standalone::serialize_message_schedule(s))));
    }
    {
        network_test::Fixture f;
        auto c = standalone::parse_config(network_test::config);
        assert(c && f.store.save(*c));
        auto s = schedule(f.clock.snapshot().utc_now_ns + 5 * ns);
        assert(f.store.save_message_schedule(s));
        auto changed = *c;
        changed.locator = "EM19";
        assert(f.store.save(changed));
        standalone::Store loaded(f.flash);
        assert(loaded.load());
        assert(loaded.config()->locator == "EM19" && loaded.message_schedule()->enabled);
        c->enabled = true;
        assert(!f.store.save(*c));
        f.scheduler.poll();
        assert(f.service.status().state == wtp::State::Armed && f.store.message_in_flight());
        const auto first = f.store.watermark();
        network_test::Fixture reboot;
        reboot.flash.bytes = f.flash.bytes;
        assert(reboot.store.load());
        assert(reboot.scheduler.message_recovery_required());
        reboot.scheduler.poll();
        assert(reboot.service.status().state == wtp::State::Empty);
        assert(reboot.scheduler.pause_message());
        assert(!reboot.store.message_in_flight() && !reboot.store.message_schedule()->enabled);
        advance(f, 6 * ns);
        assert(f.service.status().state == wtp::State::Running);
        assert(f.scheduler.pause_message() && f.scheduler.message_pause_pending());
        assert(f.service.status().state == wtp::State::Running &&
               f.store.message_schedule()->enabled);
        advance(f, 7 * ns + 1000);
        assert(!f.store.message_in_flight());
        assert(!f.store.message_schedule()->enabled && !f.scheduler.message_pause_pending());
        advance(f, 126 * ns);
        assert(f.store.watermark() == first);
    }
    {
        network_test::Fixture f;
        auto s = schedule(f.clock.snapshot().utc_now_ns + 5 * ns);
        s.expires_utc_s = s.first_start_utc_ns / ns + 65;
        assert(f.store.save_message_schedule(s));
        f.scheduler.poll();
        const auto first = f.store.watermark();
        advance(f, 6 * ns);
        advance(f, 7 * ns + 1000);
        assert(!f.store.message_in_flight());
        advance(f, 61 * ns);
        assert(f.service.status().state == wtp::State::Armed &&
               f.store.watermark() == first + 60 * ns);
        advance(f, 66 * ns);
        advance(f, 67 * ns + 1000);
        advance(f, 121 * ns);
        assert(f.store.watermark() == first + 60 * ns);
        assert(f.scheduler.message_status().find("expired") != std::string::npos);
    }
    {
        network_test::Fixture f;
        auto s = schedule(f.clock.snapshot().utc_now_ns + 5 * ns);
        assert(f.store.save_message_schedule(s));
        f.scheduler.poll();
        advance(f, 8 * ns); // Miss launch window: must retain a recovery barrier.
        assert(f.store.message_in_flight() && f.scheduler.message_recovery_required());
        const auto consumed = f.store.watermark();
        advance(f, 61 * ns);
        assert(f.store.watermark() == consumed);
    }
    {
        network_test::Fixture f;
        auto c = standalone::parse_config(network_test::config);
        assert(c && f.store.save(*c));
        f.flash.fail = true;
        assert(!f.store.save_message_schedule(schedule(anchor)));
        standalone::Store after(f.flash);
        assert(after.load() && !after.message_schedule()); // Refusal before the first page
                                                           // preserves the legacy record.
    }
    {
        struct CutFlash : network_test::Flash {
            int remaining = -1;
            bool program(std::size_t offset, std::span<const std::uint8_t> data) override {
                if (remaining == 0)
                    return false;
                if (remaining > 0)
                    --remaining;
                return network_test::Flash::program(offset, data);
            }
        };
        for (int cut = 0; cut < 8; ++cut) {
            CutFlash flash;
            standalone::Store store(flash);
            assert(store.load());
            auto c = standalone::parse_config(network_test::config);
            assert(c && store.save(*c));
            flash.remaining = cut;
            assert(!store.save_message_schedule(schedule(anchor)));
            standalone::Store reboot(flash);
            if (cut == 0)
                assert(reboot.load() && !reboot.message_schedule());
            else
                assert(!reboot.load());
        }
    }
    {
        network_test::Fixture f;
        auto s = schedule(f.clock.snapshot().utc_now_ns + 60 * ns);
        assert(f.store.save_message_schedule(s));
        const auto session = std::string(32, 'b');
        assert(call(f, "POST", "/api/v1/jobs",
                    "{\"session_id\":\"" + session + "\",\"request_id\":\"" + std::string(32, 'c') +
                        "\",\"operation\":\"HELLO\",\"body\":{\"versions\":[\"WTP/"
                        "1\"],\"client_name\":\"test\",\"client_version\":\"1\"}}")
                   .status == 200);
        assert(call(f, "POST", "/api/v1/jobs",
                    "{\"session_id\":\"" + session + "\",\"request_id\":\"" + std::string(32, 'd') +
                        "\",\"operation\":\"CLAIM\",\"body\":{\"owner_id\":\"" + session +
                        "\",\"lease_ms\":60000}}")
                   .status == 200);
        advance(f, 56 * ns);
        assert(f.store.watermark() == 0 && f.service.status().owner_id == session);
        assert(f.scheduler.pause_message() && f.scheduler.message_pause_pending());
        assert(f.service.status().owner_id == session); // Pausing never releases another owner.
        advance(f, 65 * ns);
        assert(!f.store.message_schedule()->enabled);
    }
    {
        network_test::Fixture f;
        assert(f.scheduler.command("STOP").find("true") != std::string::npos);
        assert(f.scheduler.pause_message());
        assert(f.scheduler.suspended()); // No phantom resume.
    }
    {
        network_test::Fixture f;
        auto read = call(f, "GET", "/api/v1/message-schedule");
        assert(read.status == 200);
        auto s = schedule(f.clock.snapshot().utc_now_ns + 60 * ns);
        const auto body = envelope(f, s);
        assert(call(f, "PUT", "/api/v1/message-schedule", body).status == 428);
        assert(call(f, "PUT", "/api/v1/message-schedule", body, "\"wrong\"").status == 412);
        auto wrong = body;
        wrong.replace(wrong.find(std::string(32, 'a')), 32, std::string(32, 'b'));
        assert(call(f, "PUT", "/api/v1/message-schedule", wrong, read.etag).status == 409);
        auto unknown = body;
        unknown.insert(1, "\"unknown\":true,");
        assert(call(f, "PUT", "/api/v1/message-schedule", unknown, read.etag).status == 400);
        assert(
            call(f, "PUT", "/api/v1/message-schedule", std::string(2049, 'x'), read.etag).status ==
            413);
        network::LocalUsbApi usb(f.api);
        network::HttpRequest request;
        request.path = "/api/v1/message-schedule";
        request.method = "GET";
        assert(usb.handle(request).status == 200);
        const auto accepted = call(f, "PUT", "/api/v1/message-schedule", body, read.etag);
        assert(accepted.status == 200);
        assert(accepted.etag != read.etag);
        assert(call(f, "PUT", "/api/v1/message-schedule", body, read.etag).status == 412);
        network::HttpRequest anonymous;
        anonymous.method = "GET";
        anonymous.path = "/api/v1/message-schedule";
        assert(f.api.handle(anonymous, "", "127.0.0.1:8443").status != 200);
        const auto pause = "{\"schema\":\"transmitter-message-schedule/1\",\"target\":" +
                           application::target(std::string(32, 'a'), f.service.status().boot_id) +
                           ",\"pause\":true}";
        assert(call(f, "POST", "/api/v1/message-schedule/pause", pause, accepted.etag).status ==
               200);
        assert(!f.store.message_schedule()->enabled);
    }
    std::cout << "UTC recurrence, persistence, dispatch recovery, expiry, deferred pause and API "
                 "admission passed\n";
}

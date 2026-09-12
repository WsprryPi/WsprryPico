#include "standalone/dry_run_engine.hpp"
#include "standalone/heap_probe.hpp"
#include "standalone/scheduler.hpp"
#include "standalone/wtp_profile.hpp"
#include "time/server_lookup.hpp"
#include "time/sntp.hpp"
#include "wtp/inhibited_rf_engine.hpp"
#include "wtp/json.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <limits>

using namespace wsprrypico;
#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::cerr << __LINE__ << ": " #condition "\n";                                         \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
namespace {
const std::string example =
    R"({"version":1,"enabled":true,"station":{"callsign":"AA0NT","locator":"EM18","power_dbm":37},"wifi":{"ssid":"test-network","password":"test-password","ntp_ipv4":"192.0.2.1"},"schedules":[{"period_s":120,"phase_s":0}]})";
struct MemoryFlash : standalone::Flash {
    std::array<std::uint8_t, 16384> bytes;
    int budget = -1;
    unsigned erases = 0;
    bool read_fail = false;
    MemoryFlash() {
        bytes.fill(255);
    }
    bool read(std::size_t offset, std::span<std::uint8_t> data) override {
        if (read_fail || offset > bytes.size() || data.size() > bytes.size() - offset)
            return false;
        std::copy_n(bytes.begin() + offset, data.size(), data.begin());
        return true;
    }
    bool erase(std::size_t offset) override {
        CHECK(offset % 4096 == 0 && offset <= bytes.size() - 4096);
        ++erases;
        for (std::size_t i = 0; i < 4096; ++i) {
            if (budget == 0)
                return false;
            bytes[offset + i] = 255;
            if (budget > 0)
                --budget;
        }
        return true;
    }
    bool program(std::size_t offset, std::span<const std::uint8_t> page) override {
        CHECK(offset % 256 == 0 && page.size() == 256 && offset <= bytes.size() - 256);
        for (std::size_t i = 0; i < page.size(); ++i) {
            if (budget == 0)
                return false;
            CHECK((bytes[offset + i] & page[i]) == page[i]);
            bytes[offset + i] &= page[i];
            if (budget > 0)
                --budget;
        }
        return true;
    }
};
void lookup_tests() {
    time::ServerLookup lookup;
    CHECK(!lookup.begin(0));
    lookup.link(true);
    const auto old = lookup.begin(1);
    CHECK(old && !lookup.begin(2));
    lookup.link(false);
    lookup.link(true);
    CHECK(!lookup.begin(3)); // Old callback storage must not be reused.
    CHECK(!lookup.finish(*old, true, 4));
    CHECK(!lookup.ready());
    const auto fresh = lookup.begin(5);
    CHECK(fresh && *fresh != *old);
    CHECK(!lookup.finish(*old, true, 6));
    CHECK(lookup.pending());
    CHECK(lookup.finish(*fresh, true, 7));
    CHECK(lookup.ready());
    CHECK(!lookup.begin(60'000'006));
    const auto refresh = lookup.begin(60'000'007);
    CHECK(refresh);
    CHECK(!lookup.finish(*refresh, false, 60'000'008));
    CHECK(lookup.ready()); // Temporary DNS loss preserves the last known address.
    CHECK(!lookup.begin(65'000'007));
    CHECK(lookup.begin(65'000'008));
    lookup.link(false);
    CHECK(!lookup.ready());
}
void config_tests() {
    const auto valid = standalone::parse_config(example);
    CHECK(valid);
    auto omitted = example;
    const std::string time_member = ",\"ntp_ipv4\":\"192.0.2.1\"";
    omitted.erase(omitted.find(time_member), time_member.size());
    const auto defaults = standalone::parse_config(omitted);
    CHECK(defaults && defaults->ntp_ipv4 == "pool.ntp.org");
    CHECK(standalone::parse_config(standalone::serialize_config(*defaults)) == defaults);
    CHECK(standalone::parse_config(standalone::serialize_config(*valid)) == valid);
    auto bad = [&](std::string from, std::string to) {
        auto text = example;
        const auto pos = text.find(from);
        CHECK(pos != text.npos);
        text.replace(pos, from.size(), to);
        CHECK(!standalone::parse_config(text));
    };
    bad("\"version\":1", "\"version\":2");
    bad("\"version\":1", "\"version\":1,\"other\":1");
    bad("\"enabled\":true", "\"enabled\":1");
    bad("\"enabled\":true", "\"enabled\":true,\"enabled\":false");
    bad("AA0NT", "aa0nt");
    bad("EM18", "EM18xx");
    bad(":37", ":38");
    bad(":37", ":-1");
    bad(":37", ":3.7e1");
    bad("test-password", "short");
    bad("test-network", "");
    bad("192.0.2.1", "127.0.0.1");
    bad("192.0.2.1", "224.0.0.1");
    bad("192.0.2.1", "192.000.2.1");
    bad("192.0.2.1", "192.0.2.999");
    for (const auto* literal : {"0x7f000001", "0xe0000001", "0xC0000201", "0xC0.0.2.1"})
        bad("192.0.2.1", literal);
    for (const auto* name : {"time.example.net", "wspr5.local", "time.example.net."}) {
        auto named = *valid;
        named.ntp_ipv4 = name;
        CHECK(standalone::parse_config(standalone::serialize_config(named)) == named);
    }
    for (const auto* name : {"-bad.example", "bad-.example", "bad..example", "bad.example..",
                             "https://time.example", "time.example:123", "bad name"})
        bad("192.0.2.1", name);
    bad("192.0.2.1", std::string(64, 'a') + ".example");
    bad(":120", ":0");
    bad(":120", ":121");
    bad(":120", ":3600000000");
    bad("\"phase_s\":0", "\"phase_s\":120");
    bad("\"phase_s\":0", "\"phase_s\":1");
    bad("[{\"period_s\":120,\"phase_s\":0}]", "[]");
    auto c = *valid;
    c.schedules = {{240, 0}, {240, 120}};
    CHECK(standalone::parse_config(standalone::serialize_config(c)));
    c.schedules = {{240, 0}, {360, 120}}; // Intersect at 480 seconds.
    CHECK(!standalone::parse_config(standalone::serialize_config(c)));
    c.schedules.assign(9, {120, 0});
    CHECK(!standalone::parse_config(standalone::serialize_config(c)));
    CHECK(!standalone::parse_config(std::string(1801, ' ')));
}
void storage_tests() {
    MemoryFlash flash;
    standalone::Store store(flash);
    CHECK(store.load() && store.healthy() && !store.config());
    auto c = *standalone::parse_config(example);
    CHECK(store.save(c));
    // A checksum-valid record from the overlapping layout must not be
    // reinterpreted: its omitted newer watermark could permit replay.
    auto legacy = flash;
    legacy.bytes[7] = '1';
    std::uint32_t crc = 0xffffffffU;
    for (std::size_t i = 0; i < 2044; ++i) {
        crc ^= legacy.bytes[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320U : 0);
    }
    crc = ~crc;
    for (unsigned i = 0; i < 4; ++i)
        legacy.bytes[2044 + i] = static_cast<std::uint8_t>(crc >> (8 * i));
    standalone::Store old_layout(legacy);
    CHECK(!old_layout.load() && !old_layout.save(c));
    CHECK(store.reserve(100));
    CHECK(!store.reserve(100) && !store.reserve(99));
    for (std::uint64_t i = 101; i < 180; ++i) {
        standalone::Store reboot(flash);
        CHECK(reboot.load() && reboot.config() == c && reboot.watermark() == i - 1);
        CHECK(reboot.reserve(i));
    }
    CHECK(flash.erases == 4); // One sector erase per sixteen reservations.
    for (unsigned i = 0; i < 8; ++i) {
        c.enabled = !c.enabled;
        CHECK(store.save(c));
        standalone::Store reboot(flash);
        CHECK(reboot.load() && reboot.config() == c);
    }
    // Interrupt every byte boundary of a configuration record. A complete
    // prior record or a latched storage fault is acceptable; partial data is not.
    MemoryFlash baseline;
    standalone::Store initial(baseline);
    CHECK(initial.load() && initial.save(c));
    auto changed = c;
    changed.callsign = "K1ABC";
    for (int cut = 0; cut < 2048; ++cut) {
        auto broken = baseline;
        standalone::Store writer(broken);
        CHECK(writer.load());
        broken.budget = cut;
        CHECK(!writer.save(changed));
        broken.budget = -1;
        standalone::Store reboot(broken);
        if (reboot.load())
            CHECK(reboot.config() == c);
    }
    // A torn watermark can never release a later schedule for replay.
    CHECK(initial.reserve(100));
    for (int cut = 0; cut < 256; ++cut) {
        auto broken = baseline;
        standalone::Store writer(broken);
        CHECK(writer.load());
        broken.budget = cut;
        CHECK(!writer.reserve(200));
        broken.budget = -1;
        standalone::Store reboot(broken);
        if (reboot.load())
            // An unwritten trailing 0xff checksum byte may already match
            // erased flash: a complete verified new record is also safe.
            CHECK((reboot.watermark() == 100 && cut == 0) || reboot.watermark() == 200);
        else
            CHECK(!reboot.reserve(200));
    }
    auto corrupt = baseline;
    corrupt.bytes[8192 + 32] ^= 1;
    standalone::Store damaged(corrupt);
    CHECK(!damaged.load() && !damaged.reserve(500));
    auto bad_config = baseline;
    bad_config.bytes[32] ^= 1;
    standalone::Store config_fault(bad_config);
    CHECK(!config_fault.load() && !config_fault.save(c));
    // Power loss while rotating a populated watermark bank: never lose the
    // newest durable watermark, even if conservative recovery requires repair.
    MemoryFlash rotation;
    standalone::Store rotating(rotation);
    CHECK(rotating.load());
    for (unsigned i = 1; i <= 32; ++i)
        CHECK(rotating.reserve(i));
    for (int cut : {0, 1, 255, 256, 2048, 4095, 4096, 4097, 4351}) {
        auto broken = rotation;
        standalone::Store writer(broken);
        CHECK(writer.load());
        broken.budget = cut;
        CHECK(!writer.reserve(33));
        broken.budget = -1;
        standalone::Store reboot(broken);
        if (reboot.load())
            CHECK(reboot.watermark() == 32);
    }
    flash.read_fail = true;
    standalone::Store unreadable(flash);
    CHECK(!unreadable.load());
}
struct Clock : wtp::Clock {
    wtp::ClockSnapshot value{wtp::ClockState::Synchronized,
                             time::sntp_min_utc_ns,
                             0,
                             1'000'000,
                             0,
                             wtp::LeapState::Normal,
                             {}};
    wtp::ClockSnapshot snapshot() const override {
        return value;
    }
    void advance(std::uint64_t ns) {
        value.utc_now_ns += ns;
        value.monotonic_now_ns += ns;
    }
};
struct Identity : wtp::IdentitySource {
    std::string new_boot_id() override {
        return std::string(32, 'a');
    }
};
struct Engine : wtp::RfEngine {
    wtp::InhibitedRfEngine backing;
    unsigned prepared = 0, began = 0;
    bool reject = false, active = false;
    wtp::Job job;
    wtp::PrepareResult prepare(const wtp::Job& j) override {
        ++prepared;
        job = j;
        return {!reject, {}};
    }
    bool begin(const wtp::Job& j, std::uint64_t start) override {
        ++began;
        return backing.begin(j, start);
    }
    wtp::EngineReport poll(std::uint64_t now) override {
        return backing.poll(now);
    }
    bool disable(std::uint64_t deadline) override {
        return backing.disable(deadline);
    }
    bool output_active() const override {
        return active;
    }
};
void live_config_tests() {
    MemoryFlash flash;
    standalone::Store store(flash);
    CHECK(store.load() && store.save(*standalone::parse_config(example)));
    Clock clock;
    Engine engine;
    Identity identities;
    wtp::JobService service(clock, engine, identities);
    standalone::Scheduler scheduler(store, service);
    auto current = *store.config();
    current.power_dbm = 20;
    const auto save = [&] {
        return scheduler.command("CONFIG " + standalone::serialize_config(current));
    };
    CHECK(save().find("\"reboot_required\":false") != std::string::npos);
    CHECK(store.config()->power_dbm == 20);
    current.ntp_ipv4 = "time.example.net";
    CHECK(save().find("\"reboot_required\":true") != std::string::npos);
    current.power_dbm = 23;
    CHECK(save().find("\"reboot_required\":true") != std::string::npos);
    (void)scheduler.command("STOP");
    current.ntp_ipv4 = "192.0.2.1";
    CHECK(save().find("\"reboot_required\":false") != std::string::npos);
    CHECK(scheduler.status().find("\"suspended\":true") != std::string::npos);
}
void reset_guard_tests() {
    MemoryFlash flash;
    standalone::Store store(flash);
    CHECK(store.load());
    auto config = *standalone::parse_config(example);
    config.enabled = false;
    CHECK(store.save(config));
    Clock clock;
    Engine engine;
    Identity identity;
    wtp::JobService service(clock, engine, identity);
    standalone::Scheduler scheduler(store, service);
    CHECK(scheduler.reset_permitted());
    engine.active = true;
    service.reset();
    CHECK(service.status().state == wtp::State::Failed);
    CHECK(!scheduler.reset_permitted());
    engine.active = false;
    CHECK(!scheduler.idle() && scheduler.reset_permitted());
    // Merely querying eligibility must leave the WTP fault latched.
    CHECK(service.status().state == wtp::State::Failed);
    config.enabled = true;
    CHECK(store.save(config));
    CHECK(!scheduler.reset_permitted());
}

void scheduler_tests() {
    constexpr auto ns = 1'000'000'000ULL;
    MemoryFlash flash;
    standalone::Store store(flash);
    CHECK(store.load());
    auto schedule_config = *standalone::parse_config(example);
    schedule_config.schedules = {{240, 0}};
    CHECK(store.save(schedule_config));
    Clock clock;
    clock.advance(236 * ns); // Five seconds before the next WSPR start.
    const auto start = clock.value.utc_now_ns + 5 * ns;
    Engine engine;
    Identity identity;
    wtp::JobService service(clock, engine, identity);
    standalone::Scheduler scheduler(store, service);
    scheduler.poll();
    CHECK(service.status().state == wtp::State::Armed && store.watermark() == start);
    CHECK(engine.prepared == 1 && engine.job.events.size() == 162);
    CHECK(engine.job.total_duration_ns == 110'592'000'000ULL);
    CHECK(engine.job.events[0].frequency_nhz == 3'570'101'464'843'750ULL);
    CHECK(scheduler.command("CONFIG " + example).find("busy") != std::string::npos);
    for (int i = 0; i < 10; ++i)
        scheduler.poll();
    CHECK(engine.prepared == 1);
    clock.advance(5 * ns);
    scheduler.poll();
    CHECK(engine.began == 1);
    clock.advance(110'592'000'000ULL);
    scheduler.poll();
    CHECK(service.status().state == wtp::State::Complete && !service.status().owner_id);
    // After a reboot and a backwards time step, an already reserved occurrence
    // remains suppressed even though it would otherwise be in the arm window.
    standalone::Store recovered(flash);
    CHECK(recovered.load());
    clock.value.utc_now_ns = start - 5 * ns;
    Engine other;
    wtp::JobService fresh(clock, other, identity);
    standalone::Scheduler reboot(recovered, fresh);
    reboot.poll();
    CHECK(other.prepared == 0);
    clock.advance(240 * ns);
    reboot.poll();
    CHECK(other.prepared == 1);
    clock.advance(5 * ns);
    reboot.poll();
    CHECK(other.began == 1);
    clock.advance(111 * ns);
    reboot.poll();
    auto json = wtp::json::parse(reboot.status());
    CHECK(json);
    CHECK(reboot.status().find("test-password") == std::string::npos);
    CHECK(reboot.command("CONFIG " + example).find("\"reboot_required\":false") !=
          std::string::npos);
    clock.advance(4 * ns);
    reboot.poll();
    CHECK(other.prepared == 2); // Saving unchanged network settings permits the next slot.
    // Every unavailable/unsafe source must leave flash and engine untouched.
    for (unsigned fault = 0; fault < 5; ++fault) {
        MemoryFlash f;
        standalone::Store s(f);
        CHECK(s.load() && s.save(*standalone::parse_config(example)));
        Clock clk;
        clk.advance(116 * ns);
        if (fault == 0)
            clk.value.state = wtp::ClockState::Unsynchronized;
        if (fault == 1)
            clk.value.uncertainty_ns = 2'000'000;
        if (fault == 2)
            clk.value.leap = wtp::LeapState::Unknown;
        if (fault == 3)
            clk.value.utc_now_ns = std::numeric_limits<std::uint64_t>::max();
        if (fault == 4)
            clk.advance(4 * ns); // Too late: never catch up.
        Engine e;
        wtp::JobService svc(clk, e, identity);
        standalone::Scheduler sched(s, svc);
        sched.poll();
        CHECK(e.prepared == 0 && s.watermark() == 0);
    }
    // A failed durable reservation must not even prepare RF, and a failed
    // preparation must never retry the reserved occurrence.
    for (bool storage_fault : {false, true}) {
        MemoryFlash f;
        standalone::Store s(f);
        CHECK(s.load() && s.save(*standalone::parse_config(example)));
        Clock clk;
        clk.advance(116 * ns);
        Engine e;
        e.reject = !storage_fault;
        wtp::JobService svc(clk, e, identity);
        standalone::Scheduler sched(s, svc);
        if (storage_fault)
            f.budget = 20;
        sched.poll();
        sched.poll();
        CHECK(e.prepared == (storage_fault ? 0U : 1U) && e.began == 0);
        CHECK(!svc.status().owner_id);
    }
    // External ownership cannot be stolen, even by an enabled schedule.
    MemoryFlash f;
    standalone::Store s(f);
    CHECK(s.load() && s.save(*standalone::parse_config(example)));
    Clock clk;
    clk.advance(116 * ns);
    Engine e;
    wtp::JobService svc(clk, e, identity);
    standalone::Scheduler sched(s, svc);
    wtp::Request req;
    req.principal = "usb-physical";
    req.payload_digest.fill(1);
    req.session_id = std::string(32, 'c');
    req.request_id = std::string(32, '1');
    req.operation = "HELLO";
    req.body = wtp::HelloBody{{"WTP/1"}};
    CHECK(svc.handle(req).ok);
    req.request_id = std::string(32, '2');
    req.operation = "CLAIM";
    req.body = wtp::ClaimBody{std::string(32, 'b'), 60000};
    CHECK(svc.handle(req).ok);
    sched.poll();
    CHECK(e.prepared == 0 && s.watermark() == 0);
    CHECK(sched.command("CONFIG " + example).find("busy") != std::string::npos);
    CHECK(sched.command("STOP").find("external_owner") != std::string::npos);
    CHECK(svc.status().owner_id == std::string(32, 'b'));
    CHECK(!sched.reset_permitted());
    clk.advance(61 * ns);
    svc.poll();
    CHECK(sched.reset_permitted());
}
void put(std::span<std::uint8_t> bytes, std::uint64_t value) {
    for (std::size_t i = 0; i < bytes.size(); ++i)
        bytes[bytes.size() - i - 1] = static_cast<std::uint8_t>(value >> (8 * i));
}
std::array<std::uint8_t, 48> reply(std::uint64_t nonce, std::uint64_t unix_seconds) {
    std::array<std::uint8_t, 48> bytes{};
    bytes[0] = 0x24;
    bytes[1] = 1;
    bytes[3] = 0xec;
    put(std::span(bytes).subspan(24, 8), nonce);
    for (auto offset : {16, 32, 40})
        put(std::span(bytes).subspan(offset, 4), (unix_seconds + 2'208'988'800ULL) & 0xffffffffULL);
    return bytes;
}
void sntp_tests() {
    std::uint64_t mono = 0;
    auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
    time::UtcDiscipline clock(now, &mono);
    time::Sntp source(clock);
    const auto packet = source.request(mono, 123);
    CHECK(packet[0] == 0x23 && packet[47] == 123);
    mono = 2'000'000;
    auto response = reply(123, 1'800'000'000);
    CHECK(source.receive(response, mono));
    auto snapshot = clock.snapshot();
    CHECK(snapshot.utc_now_ns == 1'800'000'000'001'000'000ULL);
    CHECK(snapshot.uncertainty_ns == 3'050'999 && snapshot.state == wtp::ClockState::Synchronized);
    CHECK(!source.receive(response, mono)); // One-shot response correlation.
    mono += 31'000'000'000ULL;
    CHECK(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    // A realistic Internet exchange is accepted; the inclusive 500 ms total
    // uncertainty boundary still fails closed one nanosecond above it.
    for (const auto uncertainty : {100'000'000ULL, 500'000'000ULL, 500'000'001ULL}) {
        time::UtcDiscipline c(now, &mono);
        time::Sntp sn(c);
        (void)sn.request(mono, 987);
        mono += uncertainty - 1'050'999ULL;
        CHECK(sn.receive(reply(987, 1'800'000'000), mono) == (uncertainty <= 500'000'000ULL));
        CHECK(sn.last_uncertainty_ns() == uncertainty);
        CHECK(sn.last_rtt_ns() == uncertainty - 1'050'999ULL);
    }
    // Era rollover works without a host-provided era hint.
    for (auto seconds : {2'085'978'495ULL, 2'085'978'496ULL, 4'102'444'799ULL}) {
        (void)source.request(mono, 456);
        mono += 2'000'000;
        auto wrapped = reply(456, seconds);
        for (auto offset : {20, 36, 44})
            put(std::span(wrapped).subspan(offset, 4), 0x80000000);
        CHECK(source.receive(wrapped, mono));
        CHECK(clock.snapshot().utc_now_ns / 1'000'000'000ULL == seconds);
    }
    for (unsigned fault = 0; fault < 17; ++fault) {
        time::UtcDiscipline c(now, &mono);
        time::Sntp sn(c);
        (void)sn.request(mono, 999);
        mono += 2'000'000;
        auto r = reply(999, 1'800'000'000);
        if (fault == 0)
            r[0] = 0x23;
        if (fault == 1)
            r[0] = 0x1c;
        if (fault == 2)
            r[0] |= 0xc0;
        if (fault == 3)
            r[0] |= 0x40;
        if (fault == 4)
            r[1] = 0;
        if (fault == 5)
            r[1] = 16;
        if (fault == 6)
            r[31] ^= 1;
        if (fault == 7)
            r[4] = 0x80;
        if (fault == 8)
            r[8] = 1;
        if (fault == 9)
            r = reply(999, 1'000'000'000);
        if (fault == 10)
            r = reply(999, 4'102'444'800ULL);
        if (fault == 11)
            r[43] += 1; // Server processing exceeds total RTT.
        if (fault == 12)
            r[35] += 1; // Receive after transmit.
        if (fault == 13)
            std::fill(r.begin() + 16, r.begin() + 24, 0);
        if (fault == 16)
            r[3] = 1;
        if (fault == 14)
            mono += 2'000'000'000ULL;
        CHECK(!sn.receive(fault == 15 ? std::span(r).first(47) : std::span(r), mono));
        CHECK(c.snapshot().state == wtp::ClockState::Unsynchronized);
        if (fault == 4)
            CHECK(sn.denied());
    }
}
void sntp_poll_schedule_test() {
    time::SntpPollSchedule schedule;
    CHECK(schedule.due(0));
    schedule.sent(0);
    CHECK(!schedule.due(1'999'999) && schedule.due(2'000'000));
    schedule.sent(2'000'000);
    CHECK(!schedule.due(3'999'999) && schedule.due(4'000'000));
    schedule.sent(4'000'000);
    CHECK(!schedule.due(67'999'999) && schedule.due(68'000'000));
    schedule.sent(68'000'000);
    schedule.accepted(68'100'000);
    CHECK(!schedule.due(132'099'999) && schedule.due(132'100'000));
    // A long RF interval delays network polling. A lost first exchange after
    // resumption must not force the following WSPR slot to wait another 64 s.
    schedule.sent(200'000'000);
    CHECK(schedule.due(202'000'000));
    schedule.sent(202'000'000);
    schedule.accepted(202'100'000);
    CHECK(!schedule.due(203'000'000));
    // Monotonic reversal and near-overflow cannot manufacture an early retry.
    CHECK(!schedule.due(1));
    const auto high = std::numeric_limits<std::uint64_t>::max();
    schedule.sent(high - 1'000'000);
    CHECK(!schedule.due(high));
    schedule.reset();
    CHECK(schedule.due(high));

    // Exercise correlation and clock recovery with a delayed reply to the
    // pre-RF request, followed by a lost first post-RF request. Only a valid
    // reply to the retry can postpone the next poll.
    std::uint64_t mono = 0;
    auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
    time::UtcDiscipline clock(now, &mono);
    time::Sntp source(clock);
    time::SntpPollSchedule resumed;
    resumed.sent(0);
    (void)source.request(mono, 1);
    mono = 200'000'000'000ULL;
    CHECK(!source.receive(reply(1, 1'800'000'000), mono));
    CHECK(resumed.due(mono / 1000));
    resumed.sent(mono / 1000);
    (void)source.request(mono, 2); // Lost after RF network polling resumes.
    mono += 2'000'000'000ULL;
    CHECK(resumed.due(mono / 1000));
    resumed.sent(mono / 1000);
    (void)source.request(mono, 3);
    mono += 100'000'000ULL;
    CHECK(!source.receive(reply(2, 1'800'000'002), mono));
    CHECK(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    CHECK(source.receive(reply(3, 1'800'000'002), mono));
    resumed.accepted(mono / 1000);
    CHECK(clock.snapshot().state == wtp::ClockState::Synchronized);
    CHECK(!resumed.due(204'000'000));
}

void campaign_controls_test() {
    constexpr auto ns = 1'000'000'000ULL;
    auto config = *standalone::parse_config(example);
    config.expires_utc_s = time::sntp_min_utc_ns / ns + 231; // Too short for the 121-second slot.
    CHECK(standalone::parse_config(standalone::serialize_config(config)) == config);
    MemoryFlash flash;
    standalone::Store store(flash);
    CHECK(store.load() && store.save(config));
    Clock clock;
    clock.advance(116 * ns);
    Engine engine;
    Identity identity;
    wtp::JobService service(clock, engine, identity);
    standalone::Scheduler scheduler(store, service);
    scheduler.poll();
    CHECK(engine.prepared == 0 && store.watermark() == 0);
    config.expires_utc_s += 1;
    CHECK(store.save(config));
    scheduler.poll();
    CHECK(engine.prepared == 1 && service.status().state == wtp::State::Armed);
    CHECK(scheduler.command("STOP").find("\"ok\":true") != std::string::npos);
    CHECK(scheduler.idle());
    clock.advance(120 * ns);
    scheduler.poll();
    CHECK(engine.prepared == 1);
    CHECK(scheduler.status().find("\"suspended\":true") != std::string::npos);
    standalone::Store reboot(flash);
    CHECK(reboot.load() && reboot.config()->expires_utc_s == config.expires_utc_s);
    config.expires_utc_s = std::numeric_limits<std::uint64_t>::max();
    CHECK(!standalone::parse_config(standalone::serialize_config(config)));
}
void autonomous_test() {
    constexpr auto ns = 1'000'000'000ULL;
    std::uint64_t mono = 0;
    auto now = [](void* p) { return *static_cast<std::uint64_t*>(p); };
    const auto config = standalone::clock_profile();
    time::UtcDiscipline clock(now, &mono, config);
    time::Sntp sntp(clock);
    MemoryFlash flash;
    standalone::Store store(flash);
    CHECK(store.load() && store.save(*standalone::parse_config(example)));
    standalone::DryRunEngine engine;
    Identity identity;
    const auto capabilities = standalone::wtp_profile(false);
    wtp::JobService service(clock, engine, identity, capabilities);
    standalone::Scheduler scheduler(store, service);
    scheduler.poll();
    CHECK(service.status().state == wtp::State::Empty);
    (void)sntp.request(mono, 51);
    mono = 2'000'000;
    auto response = reply(51, time::sntp_min_utc_ns / ns + 116);
    put(std::span(response).subspan(36, 4), 12345);
    put(std::span(response).subspan(44, 4), 12345);
    CHECK(sntp.receive(response, mono));
    const auto sample = clock.snapshot();
    const auto start_utc = time::sntp_min_utc_ns + 121 * ns;
    const auto start_mono = sample.monotonic_now_ns + start_utc - sample.utc_now_ns;
    CHECK(start_mono % 1000 == 0); // Real PIO alarm must accept this mapping.
    scheduler.poll();
    CHECK(service.status().state == wtp::State::Armed);
    mono = start_mono + 1000; // Inhibited lifecycle simulation permits a late poll.
    scheduler.poll();
    CHECK(service.status().state == wtp::State::Running);
    mono = start_mono + 1000 + 110'592'000'000ULL;
    scheduler.poll();
    CHECK(service.status().state == wtp::State::Complete && !engine.output_active());
    CHECK(clock.snapshot().state == wtp::ClockState::Holdover);
    // No USB input at any point. Loss of network time does not produce another job.
    mono += 120 * ns;
    scheduler.poll();
    CHECK(service.status().state == wtp::State::Complete);
    CHECK(store.watermark() == start_utc);
    CHECK(clock.snapshot().state == wtp::ClockState::Unsynchronized);
    // Oscillator aging can cross the 500 ms budget after admission. Launch
    // must recheck the aged observation instead of trusting the earlier ARM.
    {
        std::uint64_t tick = 0;
        time::UtcDiscipline aged(now, &tick, config);
        CHECK(aged.observe(time::sntp_min_utc_ns + 116 * ns, tick, 499'900'000,
                           wtp::LeapState::Normal));
        MemoryFlash memory;
        standalone::Store persisted(memory);
        CHECK(persisted.load() && persisted.save(*standalone::parse_config(example)));
        standalone::DryRunEngine guarded;
        wtp::JobService guarded_service(aged, guarded, identity, capabilities);
        standalone::Scheduler local(persisted, guarded_service);
        local.poll();
        CHECK(guarded_service.status().state == wtp::State::Armed);
        tick = 5 * ns;
        local.poll();
        CHECK(guarded_service.status().state == wtp::State::Missed);
        CHECK(!guarded.output_active());
    }
    // Before-launch source loss must suppress even the simulated execution.
    Clock fake;
    standalone::DryRunEngine dry;
    const wtp::Job short_job{std::string(32, 'd'), "rf-events/1", "tone", ns, {}, false};
    CHECK(dry.schedule(short_job, ns, {&fake, fake.value.utc_now_ns + ns, 1'000'000, 0}));
    fake.advance(ns);
    fake.value.state = wtp::ClockState::Unsynchronized;
    CHECK(dry.poll(ns).state == wtp::EngineState::Missed && !dry.output_active());
}
} // namespace
int main() {
    unsigned calls = 0;
    auto probe = [&](std::size_t bytes) {
        ++calls;
        return bytes <= 1024;
    };
    for (const auto value : {"", "0", "-1", "+1", "1 ", " 1", "1026", "18446744073709551616"})
        CHECK(standalone::heap_probe_command(value, 1024, true, probe).find("probe_range") !=
              std::string::npos);
    CHECK(calls == 0);
    CHECK(standalone::heap_probe_command("1024", 1024, false, probe).find("not_idle") !=
          std::string::npos);
    CHECK(calls == 0);
    CHECK(standalone::heap_probe_command("1024", 1024, true, probe).find("allocated\":true") !=
          std::string::npos);
    CHECK(standalone::heap_probe_command("1025", 1024, true, probe).find("allocated\":false") !=
          std::string::npos);
    CHECK(calls == 2);

    lookup_tests();
    live_config_tests();
    config_tests();
    storage_tests();
    reset_guard_tests();
    scheduler_tests();
    sntp_tests();
    sntp_poll_schedule_test();
    autonomous_test();
    campaign_controls_test();
    std::cout << "standalone tests passed\n";
}

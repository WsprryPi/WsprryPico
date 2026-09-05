#include "wtp/frame_parser.hpp"
#include "wtp/inhibited_rf_engine.hpp"
#include "wtp/job_service.hpp"

#include <algorithm>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

using namespace wsprrypico::wtp;

namespace {

class TestFailure : public std::runtime_error {
  public:
    using std::runtime_error::runtime_error;
};

#define CHECK(expression)                                                                          \
    do {                                                                                           \
        if (!(expression)) {                                                                       \
            throw TestFailure(std::string(__func__) + ": CHECK failed: " #expression);             \
        }                                                                                          \
    } while (false)

class VirtualClock final : public Clock {
  public:
    ClockSnapshot value{ClockState::Synchronized, 1'000'000'000'000ULL, 10'000'000'000ULL, 1000, 0,
                        LeapState::Normal,        std::nullopt};

    [[nodiscard]] ClockSnapshot snapshot() const override {
        return value;
    }

    void advance(std::uint64_t nanoseconds) {
        value.utc_now_ns += nanoseconds;
        value.monotonic_now_ns += nanoseconds;
        value.sync_age_ns += nanoseconds;
    }
};

class TestIdentitySource final : public IdentitySource {
  public:
    [[nodiscard]] std::string new_boot_id() override {
        ++sequence_;
        std::string result(32, '0');
        result.back() = static_cast<char>('0' + sequence_);
        return result;
    }

  private:
    int sequence_ = 0;
};

class MockRfEngine final : public RfEngine {
  public:
    struct AppliedEvent {
        std::size_t index;
        std::uint64_t scheduled_ns;
        bool rf_on;
    };

    bool reject_prepare = false;
    bool reject_begin = false;
    bool reject_disable = false;
    bool force_failure = false;
    bool stall_completion = false;
    bool active = false;
    std::size_t prepare_calls = 0;
    std::size_t begin_calls = 0;
    std::size_t disable_calls = 0;
    std::vector<AppliedEvent> applied;
    std::vector<FrequencyAdjustment> adjustments;

    PrepareResult prepare(const Job& job) override {
        ++prepare_calls;
        prepared = job;
        return {!reject_prepare, adjustments};
    }

    bool begin(const Job& job, std::uint64_t start_monotonic_ns) override {
        ++begin_calls;
        if (reject_begin) {
            return false;
        }
        running = job;
        start_ns = start_monotonic_ns;
        next_event = 0;
        began = true;
        return true;
    }

    [[nodiscard]] EngineReport poll(std::uint64_t monotonic_now_ns) override {
        if (force_failure) {
            return {EngineState::Failed, active};
        }
        if (!began || !running) {
            return {EngineState::Idle, active};
        }
        if (monotonic_now_ns < start_ns) {
            return {EngineState::Armed, active};
        }
        const auto elapsed = monotonic_now_ns - start_ns;
        while (next_event < running->events.size() &&
               running->events[next_event].offset_ns <= elapsed) {
            const auto& event = running->events[next_event];
            active = event.rf_on;
            applied.push_back({next_event, start_ns + event.offset_ns, event.rf_on});
            ++next_event;
        }
        if (elapsed >= running->total_duration_ns && !stall_completion) {
            return {EngineState::Complete, active};
        }
        return {EngineState::Running, active};
    }

    bool disable(std::uint64_t) override {
        ++disable_calls;
        if (reject_disable) {
            return false;
        }
        active = false;
        began = false;
        return true;
    }

    [[nodiscard]] bool output_active() const override {
        return active;
    }

  private:
    std::optional<Job> prepared;
    std::optional<Job> running;
    std::uint64_t start_ns = 0;
    std::size_t next_event = 0;
    bool began = false;
};

std::string id(char value) {
    return std::string(32, value);
}

std::string hex(const PayloadDigest& digest) {
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (const auto byte : digest) {
        output << std::setw(2) << static_cast<unsigned>(byte);
    }
    return output.str();
}

Request request(std::string operation, RequestBody body = std::monostate{},
                char request_digit = 'a', char session_digit = '1',
                std::string principal = "local") {
    const auto payload = std::string("payload-") + request_digit;
    const auto digest =
        sha256(std::span(reinterpret_cast<const std::uint8_t*>(payload.data()), payload.size()));
    return {
        "WTP/1", id(session_digit), id(request_digit), std::move(principal), std::move(operation),
        digest,  std::move(body)};
}

Response hello(JobService& service, char session_digit = '1', char request_digit = 'a',
               std::string principal = "local") {
    return service.handle(
        request("HELLO", HelloBody{{"WTP/1"}}, request_digit, session_digit, std::move(principal)));
}

Response claim(JobService& service, char session_digit = '1', char request_digit = 'b',
               std::string principal = "local", char owner_digit = '2') {
    return service.handle(request("CLAIM", ClaimBody{id(owner_digit), 10'000}, request_digit,
                                  session_digit, std::move(principal)));
}

Job sample_job(char job_digit = '3') {
    return {id(job_digit),
            "rf-events/1",
            "wspr",
            30,
            {{0, 10, true, 14'097'100'000'000'000ULL},
             {10, 10, false, std::nullopt},
             {20, 10, true, 14'097'101'465'000'000ULL}},
            false};
}

void establish_owner(JobService& service) {
    CHECK(hello(service).ok);
    CHECK(claim(service).ok);
}

void test_crc_and_frame_encoding() {
    const std::string check = "123456789";
    CHECK(crc32c(std::span(reinterpret_cast<const std::uint8_t*>(check.data()), check.size())) ==
          0xe3069283U);
    const std::string abc = "abc";
    CHECK(hex(sha256(std::span(reinterpret_cast<const std::uint8_t*>(abc.data()), abc.size()))) ==
          "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    const std::string payload = "{}";
    const auto encoded = encode_frame(
        std::span(reinterpret_cast<const std::uint8_t*>(payload.data()), payload.size()));
    CHECK(encoded.size() == kFrameHeaderBytes + payload.size());
    CHECK(encoded[0] == 'W' && encoded[1] == 'T' && encoded[2] == 'P' && encoded[3] == 'F');
    CHECK(encode_frame({}).empty());
    std::vector<std::uint8_t> oversized(kMaximumPayloadBytes + 1, 0);
    CHECK(encode_frame(oversized).empty());
}

void test_fragmented_and_combined_frames() {
    const std::string first = "{\"one\":1}";
    const std::string second = "{\"two\":2}";
    const auto first_frame =
        encode_frame(std::span(reinterpret_cast<const std::uint8_t*>(first.data()), first.size()));
    const auto second_frame = encode_frame(
        std::span(reinterpret_cast<const std::uint8_t*>(second.data()), second.size()));
    FrameParser parser;
    auto events = parser.feed(std::span(first_frame).first(7), 0);
    CHECK(events.empty());
    std::vector<std::uint8_t> remainder(first_frame.begin() + 7, first_frame.end());
    remainder.insert(remainder.end(), second_frame.begin(), second_frame.end());
    events = parser.feed(remainder, 1);
    CHECK(events.size() == 2);
    CHECK(std::string(events[0].payload.begin(), events[0].payload.end()) == first);
    CHECK(std::string(events[1].payload.begin(), events[1].payload.end()) == second);
    CHECK(parser.buffered_bytes() == 0);
}

void test_frame_recovery_limits_and_timeout() {
    const std::string payload = "{}";
    const auto good = encode_frame(
        std::span(reinterpret_cast<const std::uint8_t*>(payload.data()), payload.size()));
    std::vector<std::uint8_t> noisy{'x', 'y', 'z'};
    noisy.insert(noisy.end(), good.begin(), good.end());
    FrameParser recovering;
    const auto recovered = recovering.feed(noisy, 0);
    CHECK(recovered.size() == 1 && recovered[0].kind == FrameEventKind::Payload);

    auto corrupt = good;
    corrupt.back() ^= 1U;
    FrameParser invalid;
    std::vector<std::uint8_t> three;
    three.insert(three.end(), corrupt.begin(), corrupt.end());
    three.insert(three.end(), corrupt.begin(), corrupt.end());
    three.insert(three.end(), corrupt.begin(), corrupt.end());
    const auto invalid_events = invalid.feed(three, 0);
    CHECK(std::count_if(invalid_events.begin(), invalid_events.end(), [](const FrameEvent& event) {
              return event.kind == FrameEventKind::InvalidFrame;
          }) == 3);
    CHECK(invalid.closed());

    FrameParser timeout;
    timeout.feed(std::span(good).first(5), 10);
    CHECK(timeout.check_timeout(5009).empty());
    const auto timeout_events = timeout.check_timeout(5010);
    CHECK(timeout_events.size() == 1 && timeout_events[0].kind == FrameEventKind::Closed);

    auto oversized_header = good;
    oversized_header.resize(kFrameHeaderBytes);
    oversized_header[8] = 0;
    oversized_header[9] = 1;
    oversized_header[10] = 0;
    oversized_header[11] = 1;
    oversized_header.insert(oversized_header.end(), good.begin(), good.end());
    FrameParser oversized;
    const auto oversized_events = oversized.feed(oversized_header, 0);
    CHECK(
        std::any_of(oversized_events.begin(), oversized_events.end(), [](const FrameEvent& event) {
            return event.kind == FrameEventKind::InvalidFrame;
        }));
    CHECK(
        std::any_of(oversized_events.begin(), oversized_events.end(),
                    [](const FrameEvent& event) { return event.kind == FrameEventKind::Payload; }));

    FrameParser resync_limit;
    std::vector<std::uint8_t> garbage(131'076, 'x');
    const auto limit_events = resync_limit.feed(garbage, 0);
    CHECK(resync_limit.closed());
    CHECK(std::any_of(limit_events.begin(), limit_events.end(), [](const FrameEvent& event) {
        return event.kind == FrameEventKind::Closed;
    }));
}

void test_negotiation_sessions_and_unknown_operations() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);

    CHECK(service.handle(request("STATUS")).error == ErrorCode::HelloRequired);
    CHECK(service.handle(request("HELLO", HelloBody{{"WTP/2"}})).error ==
          ErrorCode::UnsupportedVersion);
    CHECK(hello(service).ok);
    CHECK(service.handle(request("BOGUS", std::monostate{}, 'b')).error ==
          ErrorCode::UnknownOperation);
    auto impersonation = request("STATUS", std::monostate{}, 'c', '1', "other");
    CHECK(service.handle(impersonation).error == ErrorCode::AuthenticationRequired);
    CHECK(hello(service, '4', 'd', "other").ok);
}

void test_replay_and_ownership() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);
    CHECK(hello(service).ok);
    const auto original = request("CLAIM", ClaimBody{id('2'), 10'000}, 'b');
    const auto first = service.handle(original);
    CHECK(first.ok);
    CHECK(first.owner_id == id('2'));
    CHECK(first.granted_lease_ms == 10'000);
    CHECK(first.expires_monotonic_ns == clock.value.monotonic_now_ns + 10'000'000'000ULL);
    CHECK(service.handle(original) == first);
    auto conflict = original;
    conflict.payload_digest[0] ^= 1U;
    CHECK(service.handle(conflict).error == ErrorCode::RequestIdReuse);

    CHECK(hello(service, '4', 'c', "other").ok);
    CHECK(claim(service, '4', 'd', "other", '5').error == ErrorCode::Busy);
    CHECK(service.handle(request("RELEASE", std::monostate{}, 'e', '4', "other")).error ==
          ErrorCode::NotOwner);
}

void test_replay_capacity_is_per_session() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);
    CHECK(hello(service).ok);

    const auto retained = request("PING", PingBody{std::string("retained")}, 'b');
    CHECK(service.handle(retained).ok);
    CHECK(hello(service, '4', 'c', "other").ok);
    for (const char request_digit : std::string_view("def01234")) {
        CHECK(service.handle(request("PING", std::monostate{}, request_digit, '4', "other")).ok);
    }
    CHECK(service.handle(retained).ping_token == "retained");
}

void test_job_validation_and_idempotency() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);
    establish_owner(service);

    auto invalid = sample_job();
    invalid.events[1].offset_ns = 11;
    CHECK(service.handle(request("LOAD", invalid, 'c')).error == ErrorCode::InvalidMessage);
    auto unsupported = sample_job();
    unsupported.mode = "bad";
    CHECK(service.handle(request("LOAD", unsupported, 'd')).error == ErrorCode::UnsupportedMode);

    const auto job = sample_job();
    CHECK(service.handle(request("LOAD", job, 'e')).ok);
    CHECK(engine.prepare_calls == 1);
    CHECK(service.handle(request("LOAD", job, 'f')).ok);
    CHECK(engine.prepare_calls == 1);
    auto changed = job;
    changed.total_duration_ns = 31;
    CHECK(service.handle(request("LOAD", changed, '0')).error == ErrorCode::JobIdConflict);
}

void test_clock_and_arm_rejections() {
    VirtualClock clock;
    MockRfEngine engine;
    ServiceConfig config;
    config.maximum_holdover_age_ns = 1000;
    TestIdentitySource identities;
    JobService service(clock, engine, identities, config);
    establish_owner(service);
    CHECK(service.handle(request("LOAD", sample_job(), 'c')).ok);

    const auto now = clock.value.utc_now_ns;
    CHECK(service.handle(request("ARM", ArmBody{id('3'), now, 1000}, 'd')).error ==
          ErrorCode::ArmTooLate);
    CHECK(service
              .handle(request("ARM", ArmBody{id('3'), now + config.maximum_arm_ahead_ns + 1, 1000},
                              'e'))
              .error == ErrorCode::ArmTooFar);
    clock.value.uncertainty_ns = 1001;
    CHECK(service.handle(request("ARM", ArmBody{id('3'), now + 1'000'000'000, 1000}, 'f')).error ==
          ErrorCode::ClockUncertain);
    clock.value.uncertainty_ns = 1000;
    clock.value.state = ClockState::Unsynchronized;
    CHECK(service.handle(request("ARM", ArmBody{id('3'), now + 1'000'000'000, 1000}, '0')).error ==
          ErrorCode::ClockUnsynchronized);
    clock.value.state = ClockState::Holdover;
    clock.value.sync_age_ns = 1001;
    CHECK(service.handle(request("ARM", ArmBody{id('3'), now + 1'000'000'000, 1000}, '6')).error ==
          ErrorCode::ClockUnsynchronized);
    clock.value.state = ClockState::Synchronized;
    clock.value.leap = LeapState::Unknown;
    CHECK(service.handle(request("ARM", ArmBody{id('3'), now + 1'000'000'000, 1000}, '7')).error ==
          ErrorCode::LeapUnsafe);
    clock.value.leap = LeapState::InsertPending;
    clock.value.leap_transition_utc_ns = now + 1'000'000'010;
    CHECK(service.handle(request("ARM", ArmBody{id('3'), now + 1'000'000'000, 1000}, '8')).error ==
          ErrorCode::LeapUnsafe);
    clock.value.leap_transition_utc_ns.reset();
    CHECK(service.handle(request("ARM", ArmBody{id('3'), now + 1'000'000'000, 1000}, '9')).error ==
          ErrorCode::LeapUnsafe);
}

void test_local_execution_and_duplicate_arm() {
    VirtualClock clock;
    MockRfEngine engine;
    ServiceConfig config;
    config.minimum_arm_lead_ns = 10;
    TestIdentitySource identities;
    JobService service(clock, engine, identities, config);
    establish_owner(service);
    const auto job = sample_job();
    CHECK(service.handle(request("LOAD", job, 'c')).ok);
    const auto arm_body = ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000};
    const auto armed = service.handle(request("ARM", arm_body, 'd'));
    CHECK(armed.ok && armed.state == State::Armed);

    clock.advance(10);
    service.poll();
    CHECK(service.status().state == State::Running);
    CHECK(engine.begin_calls == 1);
    CHECK(engine.applied.size() == 1 && engine.applied[0].scheduled_ns == armed.start_monotonic_ns);
    clock.advance(10);
    service.poll();
    clock.advance(10);
    service.poll();
    clock.advance(10);
    service.poll();
    CHECK(service.status().state == State::Complete);
    CHECK(!service.status().output_active);
    CHECK(engine.applied.size() == 3);
    CHECK(engine.disable_calls == 2);

    const auto replayed_arm = service.handle(request("ARM", arm_body, 'e'));
    CHECK(replayed_arm == armed);
    CHECK(engine.begin_calls == 1);
}

void test_missed_start_and_abort_safety() {
    VirtualClock clock;
    MockRfEngine engine;
    ServiceConfig config;
    config.minimum_arm_lead_ns = 10;
    TestIdentitySource identities;
    JobService service(clock, engine, identities, config);
    establish_owner(service);
    const auto job = sample_job();
    CHECK(service.handle(request("LOAD", job, 'c')).ok);
    CHECK(
        service.handle(request("ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}, 'd'))
            .ok);
    clock.advance(11);
    service.poll();
    CHECK(service.status().state == State::Missed);
    CHECK(engine.begin_calls == 0);
    CHECK(!service.status().output_active);

    const auto next_job = sample_job('4');
    CHECK(service.handle(request("LOAD", next_job, 'e')).ok);
    CHECK(service
              .handle(
                  request("ARM", ArmBody{next_job.job_id, clock.value.utc_now_ns + 10, 1000}, 'f'))
              .ok);
    clock.advance(10);
    service.poll();
    CHECK(service.status().state == State::Running);
    const auto aborted = service.handle(request("ABORT", AbortBody{id('4')}, '0'));
    CHECK(aborted.ok && aborted.state == State::Aborted);
    CHECK(service.handle(request("ABORT", AbortBody{id('4')}, '6')).ok);
}

void test_clock_loss_at_start_misses_job() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    ServiceConfig config;
    config.minimum_arm_lead_ns = 10;
    JobService service(clock, engine, identities, config);
    establish_owner(service);
    const auto job = sample_job();
    CHECK(service.handle(request("LOAD", job, 'c')).ok);
    CHECK(
        service.handle(request("ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}, 'd'))
            .ok);
    clock.value.state = ClockState::Unsynchronized;
    clock.advance(10);
    service.poll();
    CHECK(service.status().state == State::Missed);
    CHECK(engine.begin_calls == 0);
    CHECK(service.status().terminal_records.front().error == ErrorCode::MissedStart);
}

void test_disable_failure_is_terminal_fault() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);
    establish_owner(service);
    CHECK(service.handle(request("LOAD", sample_job(), 'c')).ok);
    engine.reject_disable = true;
    engine.active = true;
    const auto response = service.handle(request("ABORT", AbortBody{id('3')}, 'd'));
    CHECK(response.error == ErrorCode::OutputStateUnknown);
    CHECK(service.status().state == State::Failed);
    CHECK(service.status().output_active);
    CHECK(service.handle(request("LOAD", sample_job('4'), 'e')).error == ErrorCode::InvalidState);
}

void test_lease_expiry_and_reset() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);
    establish_owner(service);
    CHECK(service.handle(request("LOAD", sample_job(), 'c')).ok);
    clock.advance(10'000'000'000ULL);
    service.poll();
    const auto expired = service.status();
    CHECK(expired.state == State::Empty);
    CHECK(!expired.owner_id);
    CHECK(!expired.job_id);
    CHECK(!expired.terminal_records.empty() &&
          expired.terminal_records.front().state == State::Aborted);

    const auto old_boot = expired.boot_id;
    service.reset();
    CHECK(service.status().boot_id != old_boot);
    CHECK(service.status().terminal_records.empty());
    CHECK(service.handle(request("STATUS", std::monostate{}, 'd')).error ==
          ErrorCode::HelloRequired);
}

void test_safety_gate_and_connection_close() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    engine.reject_disable = true;
    engine.active = true;
    JobService blocked(clock, engine, identities);
    CHECK(blocked.status().state == State::Failed);
    CHECK(blocked.handle(request("HELLO", HelloBody{{"WTP/1"}})).error == ErrorCode::DeviceFault);

    MockRfEngine safe_engine;
    TestIdentitySource safe_identities;
    JobService service(clock, safe_engine, safe_identities);
    const auto unsupported = service.handle(request("HELLO", HelloBody{{"WTP/2"}}));
    CHECK(unsupported.error == ErrorCode::UnsupportedVersion);
    CHECK(unsupported.close_connection);
    CHECK(hello(service).ok);
    auto original = request("PING", PingBody{std::string("token")}, 'b');
    const auto ping = service.handle(original);
    CHECK(ping.ok && ping.ping_token == "token");
    original.payload_digest[0] ^= 1U;
    const auto reused = service.handle(original);
    CHECK(reused.error == ErrorCode::RequestIdReuse);
    CHECK(reused.close_connection);
}

void test_adjustments_and_engine_failure_safety() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    ServiceConfig config;
    config.minimum_arm_lead_ns = 10;
    JobService service(clock, engine, identities, config);
    establish_owner(service);
    auto job = sample_job();
    engine.adjustments = {{0, *job.events[0].frequency_nhz, *job.events[0].frequency_nhz + 1}};
    CHECK(service.handle(request("LOAD", job, 'c')).error == ErrorCode::FrequencyRejected);
    job.allow_frequency_adjustment = true;
    const auto loaded = service.handle(request("LOAD", job, 'd'));
    CHECK(loaded.ok && loaded.adjustments == engine.adjustments);
    const auto armed =
        service.handle(request("ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}, 'e'));
    CHECK(armed.ok);
    engine.reject_begin = true;
    engine.reject_disable = true;
    engine.active = true;
    clock.advance(10);
    service.poll();
    CHECK(service.status().state == State::Failed);
    CHECK(service.status().terminal_records.front().error == ErrorCode::OutputStateUnknown);
}

void test_expired_active_lease_and_terminal_retention() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    ServiceConfig config;
    config.minimum_arm_lead_ns = 10;
    config.maximum_arm_ahead_ns = 20'000'000'000ULL;
    JobService service(clock, engine, identities, config);
    establish_owner(service);
    const auto job = sample_job();
    CHECK(service.handle(request("LOAD", job, 'c')).ok);
    CHECK(service
              .handle(request("ARM",
                              ArmBody{job.job_id, clock.value.utc_now_ns + 20'000'000'000ULL, 1000},
                              'd'))
              .ok);
    clock.advance(10'000'000'000ULL);
    service.poll();
    CHECK(service.handle(request("RENEW", RenewBody{id('2'), 10'000}, 'e')).error ==
          ErrorCode::LeaseExpired);
    CHECK(service.handle(request("ABORT", AbortBody{job.job_id}, 'f')).ok);
    CHECK(!service.status().owner_id);

    clock.advance(config.terminal_record_ttl_ns);
    service.poll();
    CHECK(service.status().state == State::Empty);
    CHECK(!service.status().job_id);
    CHECK(service.status().terminal_records.empty());
    CHECK(hello(service, '1', '0').ok);
    CHECK(claim(service, '1', '6').ok);
    CHECK(service
              .handle(request(
                  "ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 100'000'000ULL, 1000}, '7'))
              .error == ErrorCode::JobNotFound);
}

void test_engine_completion_watchdog() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    ServiceConfig config;
    config.minimum_arm_lead_ns = 10;
    JobService service(clock, engine, identities, config);
    establish_owner(service);
    const auto job = sample_job();
    CHECK(service.handle(request("LOAD", job, 'c')).ok);
    CHECK(
        service.handle(request("ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}, 'd'))
            .ok);
    engine.stall_completion = true;
    clock.advance(10);
    service.poll();
    clock.advance(job.total_duration_ns);
    service.poll();
    CHECK(service.status().state == State::Failed);
    CHECK(!service.status().output_active);
    CHECK(service.status().terminal_records.front().error == ErrorCode::DeviceFault);
}

void test_inhibited_engine_never_reports_output() {
    InhibitedRfEngine engine;
    const auto job = sample_job();
    CHECK(engine.prepare(job).accepted);
    CHECK(!engine.output_active());
    CHECK(engine.begin(job, 100));
    CHECK(engine.poll(99).state == EngineState::Armed);
    CHECK(!engine.poll(99).output_active);
    CHECK(engine.poll(100).state == EngineState::Running);
    CHECK(!engine.output_active());
    CHECK(engine.poll(100 + job.total_duration_ns).state == EngineState::Complete);
    CHECK(!engine.output_active());
    CHECK(engine.disable(0));
    CHECK(!engine.output_active());
}

void test_invalid_configuration_fails_without_exception() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    ServiceConfig config;
    config.max_events = 0;
    JobService service(clock, engine, identities, config);
    CHECK(service.status().state == State::Failed);
    CHECK(engine.disable_calls == 1);
    CHECK(!service.status().output_active);
    CHECK(service.handle(request("HELLO", HelloBody{{"WTP/1"}})).error == ErrorCode::DeviceFault);
}

using Test = std::pair<const char*, void (*)()>;

} // namespace

int main() {
    const std::vector<Test> tests{
        {"crc and frame encoding", test_crc_and_frame_encoding},
        {"fragmented and combined frames", test_fragmented_and_combined_frames},
        {"frame recovery limits and timeout", test_frame_recovery_limits_and_timeout},
        {"negotiation sessions and unknown operations",
         test_negotiation_sessions_and_unknown_operations},
        {"replay and ownership", test_replay_and_ownership},
        {"replay capacity is per session", test_replay_capacity_is_per_session},
        {"job validation and idempotency", test_job_validation_and_idempotency},
        {"clock and arm rejections", test_clock_and_arm_rejections},
        {"local execution and duplicate arm", test_local_execution_and_duplicate_arm},
        {"missed start and abort safety", test_missed_start_and_abort_safety},
        {"clock loss at start misses job", test_clock_loss_at_start_misses_job},
        {"disable failure is terminal fault", test_disable_failure_is_terminal_fault},
        {"lease expiry and reset", test_lease_expiry_and_reset},
        {"safety gate and connection close", test_safety_gate_and_connection_close},
        {"adjustments and engine failure safety", test_adjustments_and_engine_failure_safety},
        {"expired active lease and terminal retention",
         test_expired_active_lease_and_terminal_retention},
        {"engine completion watchdog", test_engine_completion_watchdog},
        {"inhibited engine never reports output", test_inhibited_engine_never_reports_output},
        {"invalid configuration fails without exception",
         test_invalid_configuration_fails_without_exception},
    };
    std::size_t passed = 0;
    for (const auto& [name, test] : tests) {
        try {
            test();
            ++passed;
            std::cout << "PASS: " << name << '\n';
        } catch (const std::exception& error) {
            std::cerr << "FAIL: " << name << ": " << error.what() << '\n';
        }
    }
    std::cout << passed << '/' << tests.size() << " tests passed\n";
    return passed == tests.size() ? 0 : 1;
}

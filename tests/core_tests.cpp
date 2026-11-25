#include "encoding/morse.hpp"
#include "provisioning/rf_setup_gate.hpp"
#include "runtime/activity_trace.hpp"
#include "runtime/frame_buffer.hpp"
#include "runtime/json.hpp"
#include "time/usb_time_source.hpp"
#include "time/utc_discipline.hpp"
#include "rf/inhibited_rf_engine.hpp"
#include "rf/job_service.hpp"
#include "runtime/memory_budget.hpp"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <new>
#include <span>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

using namespace wsprrypico::execution;

static std::size_t allocations = 0;
static std::size_t largest_allocation = 0;
static std::size_t large_allocations = 0;
static std::size_t watched_event_bytes = 0;
static std::array<void*, 8> watched_event_allocations{};
static std::size_t watched_event_allocation_count = 0;
static std::size_t watched_event_release_count = 0;
static void* allocate_watched_input(std::size_t size) {
    auto* result = std::malloc(size ? size : 1);
    if (result && watched_event_bytes && size == watched_event_bytes &&
        watched_event_allocation_count < watched_event_allocations.size()) {
        watched_event_allocations[watched_event_allocation_count++] = result;
    }
    return result;
}
static void deallocate_watched_input(void* memory) {
    for (auto& allocation : watched_event_allocations) {
        if (memory && memory == allocation) {
            allocation = nullptr;
            ++watched_event_release_count;
            break;
        }
    }
    std::free(memory);
}
static void begin_event_watch() {
    watched_event_bytes = 0;
    watched_event_allocations.fill(nullptr);
    watched_event_allocation_count = 0;
    watched_event_release_count = 0;
    allocate_input = allocate_watched_input;
    deallocate_input = deallocate_watched_input;
}
static void end_event_watch() {
    watched_event_bytes = 0;
    watched_event_allocations.fill(nullptr);
    allocate_input = std::malloc;
    deallocate_input = std::free;
}
void* operator new(std::size_t size) {
    ++allocations;
    largest_allocation = std::max(largest_allocation, size);
    if (size >= 40000)
        ++large_allocations;
    if (auto* result = std::malloc(size ? size : 1)) {
        return result;
    }
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept {
    std::free(memory);
}
void operator delete(void* memory, std::size_t) noexcept {
    operator delete(memory);
}

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
    bool local_scheduling = false;
    bool independent_plan = false;
    bool external_completion = false;
    std::uint64_t acknowledgement_ns = 0;
    std::size_t prepare_calls = 0;
    std::size_t begin_calls = 0;
    std::size_t disable_calls = 0;
    std::vector<AppliedEvent> applied;
    std::vector<FrequencyAdjustment> adjustments;

    bool schedules_locally() const override {
        return local_scheduling;
    }
    bool owns_execution_plan() const override {
        return independent_plan;
    }
    std::uint64_t completion_acknowledgement_ns() const override {
        return acknowledgement_ns;
    }
    bool externally_controlled_completion() const override {
        return external_completion;
    }
    bool schedule(const Job& job, std::uint64_t start, const LocalStartConditions&) override {
        return begin(job, start);
    }

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
        "native-execution/1", id(session_digit), id(request_digit), std::move(principal), std::move(operation),
        digest,  std::move(body)};
}

Response hello(JobService& service, char session_digit = '1', char request_digit = 'a',
               std::string principal = "local") {
    return service.handle(
        request("HELLO", HelloBody{{"native-execution/1"}}, request_digit, session_digit, std::move(principal)));
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

void test_paged_json_and_digest_boundaries() {
    // Put escapes, multibyte UTF-8 and integers across a page boundary.
    for (const auto& token :
         {std::string("\"\\uD83D\\uDE00\""), std::string("\"\xf0\x9f\x98\x80\""),
          std::string("-2147483648"), std::string("2147483647")}) {
        for (std::size_t split = 1; split < token.size(); ++split) {
            std::string text(FrameBuffer::page_bytes - split - 5, ' ');
            text += "{\"v\":" + token + "}";
            FrameBuffer storage;
            CHECK(storage.reserve(text.size()));
            storage.append(
                std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
            auto flat = json::parse(text), paged = json::parse(storage.view());
            CHECK(flat && paged &&
                  static_cast<std::string>(flat->raw) == static_cast<std::string>(paged->raw));
            const auto a = flat->get("v"), b = paged->get("v");
            CHECK(a && b && a->type() == b->type());
            if (a->type() == '"')
                CHECK(a->string() == "\xf0\x9f\x98\x80" && b->string() == a->string());
            else
                CHECK(a->integer() == (token[0] == '-' ? INT32_MIN : INT32_MAX) &&
                      b->integer() == a->integer());
        }
    }
    for (const auto invalid :
         {"{\"x\":1,\"\\u0078\":2}", "{\"v\":2147483648}", "{\"v\":\"\\uD800\"}"}) {
        std::string bad(FrameBuffer::page_bytes - 3, ' ');
        bad += invalid;
        FrameBuffer buffer;
        CHECK(buffer.reserve(bad.size()));
        buffer.append(std::span(reinterpret_cast<const std::uint8_t*>(bad.data()), bad.size()));
        CHECK(!json::parse(buffer.view()));
    }
}

void test_paged_nested_wide_object_keys() {
    std::string body = "{";
    for (int i = 255; i >= 0; --i) {
        if (i != 255)
            body += ',';
        body += json::quote("field-" + std::to_string(i)) + ":0";
    }
    auto parse_paged = [](const std::string& text) {
        FrameBuffer buffer;
        CHECK(buffer.reserve(text.size()));
        buffer.append(std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
        return json::parse(buffer.view()).has_value();
    };
    std::string prefix(FrameBuffer::page_bytes - 8, ' ');
    for (unsigned i = 0; i < 15; ++i)
        prefix += "{\"nested\":";
    const std::string suffix(15, '}');
    CHECK(parse_paged(prefix + body + "}" + suffix));
    // An escaped spelling of an existing key must still be rejected after sorting.
    CHECK(!parse_paged(prefix + body + ",\"\\u0066ield-127\":0}" + suffix));
    CHECK(!parse_paged("{\"extra\":" + prefix + body + "}" + suffix + "}"));
}

void test_sha256_allocation_free_padding_boundaries() {
    const std::vector<std::uint8_t> input(65536, 'a');
    const std::array<std::pair<std::size_t, std::string_view>, 8> vectors{{
        {0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        {55, "9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318"},
        {56, "b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a"},
        {63, "7d3e74a05d7db15bce4ad9ec0658ea98e3f06eeecf16b4c6fff2da457ddc2f34"},
        {64, "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"},
        {65, "635361c48bb9eab14198e76ea8ab7f1a41685d6ad62aa9146d301d4f17eb0ae0"},
        {16668, "a3a7dab3c4f7b8eefe13d2bccb1dfd819bf26a71b1d4828bd4ec36a39d7876b8"},
        {65536, "bf718b6f653bebc184e1479f1935b8da974d701b893afcf49e701f3e2f9f9c5a"},
    }};
    for (const auto& [length, expected] : vectors) {
        const auto before = allocations;
        const auto digest = sha256(std::span(input).first(length));
        CHECK(allocations == before);
        CHECK(hex(digest) == expected);
        for (std::size_t chunk : {1U, 55U, 64U, 137U}) {
            Sha256 incremental;
            const auto start_allocations = allocations;
            for (std::size_t offset = 0; offset < length; offset += chunk)
                incremental.update(
                    std::span(input).subspan(offset, std::min(chunk, length - offset)));
            const auto first = incremental.finish();
            CHECK(allocations == start_allocations);
            CHECK(first == digest && incremental.finish() == first);
        }
    }
}

void test_cw_frequency_events() {
    using namespace wsprrypico::encoding;
    constexpr std::uint64_t base = 14096900000000000ULL, upper = 14096905000000000ULL;
    for (auto mode : {"qrss", "fskcw", "dfcw"}) {
        const bool dfcw = std::string_view(mode) == "dfcw",
                   fskcw = std::string_view(mode) == "fskcw";
        MorseMessage m{std::string(32, 'e'),
                       mode,
                       "A E",
                       fskcw ? upper : base,
                       std::string_view(mode) == "qrss" ? 0 : (fskcw ? base : upper),
                       3000000000ULL,
                       9000000000ULL,
                       3000000000ULL,
                       9000000000ULL,
                       21000000000ULL,
                       2,
                       7000000000ULL,
                       true};
        const auto result = compile_message(m);
        CHECK(result.job.has_value());
        const auto& job = *result.job;
        CHECK(job.events.size() == 12);
        CHECK(job.total_duration_ns == (dfcw ? 73000001000ULL : 85000001000ULL));
        const std::array<std::uint64_t, 12> seconds{3, 3, dfcw ? 3U : 9U, 21, 3, 7,
                                                    3, 3, dfcw ? 3U : 9U, 21, 3, 0};
        const std::array<bool, 12> marks{true, false, true, false, true, false,
                                         true, false, true, false, true, false};
        std::uint64_t offset = 0;
        for (std::size_t i = 0; i < seconds.size(); ++i) {
            const auto& event = job.events[i];
            CHECK(event.offset_ns == offset);
            CHECK(event.duration_ns == (i == 11 ? 1000 : seconds[i] * 1000000000ULL));
            const bool on = marks[i] || (fskcw && (i == 1 || i == 3 || i == 7 || i == 9));
            CHECK(event.rf_on == on);
            const auto frequency =
                fskcw ? (marks[i] ? upper : base) : (dfcw && (i == 2 || i == 8) ? upper : base);
            CHECK(event.frequency_nhz == (on ? std::optional(frequency) : std::nullopt));
            offset += event.duration_ns;
        }
        CHECK(offset == job.total_duration_ns && job.allow_frequency_adjustment);
        m.text = "AE";
        m.repeat_count = 1;
        const auto characters = compile_message(m);
        CHECK(characters.job && characters.job->events.size() == 6);
        CHECK(characters.job->events[3].duration_ns == 9000000000ULL);
        CHECK(characters.job->events[3].rf_on == fskcw);
        CHECK(characters.job->events[3].frequency_nhz ==
              (fskcw ? std::optional(base) : std::nullopt));
        if (dfcw) {
            std::swap(m.mark_frequency_nhz, m.space_frequency_nhz);
            const auto reverse = compile_message(m);
            CHECK(reverse.job && reverse.job->events[0].frequency_nhz == upper &&
                  reverse.job->events[2].frequency_nhz == base);
        }
        if (std::string_view(mode) == "qrss") {
            m.space_frequency_nhz = std::numeric_limits<std::uint64_t>::max();
            CHECK(compile_message(m).job.has_value()); // Existing unused second frequency.
        } else {
            m.space_frequency_nhz = m.mark_frequency_nhz;
            CHECK(compile_message(m).error == "invalid_message_frequency");
            m.space_frequency_nhz = 0;
            CHECK(compile_message(m).error == "invalid_message_frequency");
            m.mark_frequency_nhz = 0;
            CHECK(compile_message(m).error == "invalid_message_frequency");
            if (fskcw) {
                m.mark_frequency_nhz = base;
                m.space_frequency_nhz = upper;
                CHECK(compile_message(m).error == "invalid_message_frequency");
            }
        }
    }
}

void test_extended_morse_message_boundaries() {
    using namespace wsprrypico::encoding;
    MorseMessage m;
    m.job_id = std::string(32, 'a');
    m.mark_frequency_nhz = 135500000000000ULL;
    m.space_frequency_nhz = 135495000000000ULL;
    m.dot_ns = m.intra_gap_ns = 1000000000;
    m.dash_ns = m.character_gap_ns = 3000000000;
    m.word_gap_ns = 7000000000;
    m.allow_frequency_adjustment = true;
    for (auto mode : {"qrss", "fskcw", "dfcw"}) {
        m.mode = mode;
        for (char worst : {'?', '.', ',', '-'}) {
            for (std::size_t n : {31U, 32U, 33U}) {
                m.text = std::string(n, worst);
                auto r = compile_message(m);
                CHECK(r.job.has_value() == (n <= 32));
                if (r.job) {
                    CHECK(r.job->events.size() == n * 12);
                    CHECK(r.job->events.back().duration_ns == message_tail_ns);
                    CHECK(!r.job->events.back().rf_on);
                    CHECK(r.job->events.back().offset_ns + message_tail_ns ==
                          r.job->total_duration_ns);
                }
            }
        }
        m.text = std::string(30, ' ') + "Ee";
        CHECK(compile_message(m).job.has_value());
        m.text += " ";
        CHECK(compile_message(m).error == "message_length_limit_32");
        m.text = std::string(32, '?');
        CHECK(compile_message(m, 383).error == "message_event_limit_exceeded");
        CHECK(compile_message(m, 384).job.has_value());
        m.text = "E";
        const auto old_dot = m.dot_ns;
        for (int delta : {-1, 0, 1}) {
            m.dot_ns = max_message_duration_ns - message_tail_ns + delta;
            auto r = compile_message(m);
            CHECK(r.job.has_value() == (delta <= 0));
            CHECK(r.calculated_duration_ns == max_message_duration_ns + delta);
        }
        CHECK(compile_message(m, 512, 110592000000).error == "message_duration_limit_exceeded");
        m.dot_ns = old_dot;
        m.repeat_count = 256;
        m.repeat_gap_ns = 1000000000;
        auto repeated = compile_message(m);
        CHECK(repeated.job && repeated.job->events.size() == 512);
        m.repeat_count = 257;
        CHECK(compile_message(m).error == "message_event_limit_exceeded");
        m.repeat_count = 2;
        m.repeat_gap_ns = std::numeric_limits<std::uint64_t>::max();
        CHECK(compile_message(m).error == "message_duration_overflow");
        m.repeat_count = 1;
        m.repeat_gap_ns = 0;
        m.text = "   ";
        CHECK(compile_message(m).error == "message_has_no_marks");
        m.text = "E@E";
        CHECK(compile_message(m).error == "unsupported_message_character");
    }
}

void test_status_activity_trace_integration() {
    class CountingClock final : public Clock {
      public:
        mutable unsigned calls = 0;
        ClockSnapshot snapshot() const override {
            ++calls;
            ClockSnapshot value{};
            value.monotonic_now_ns = calls;
            return value;
        }
    } clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);
    auto& trace = wsprrypico::runtime::activity_trace();
    trace.end();
    CHECK(hello(service).ok);
    const auto valid = request("STATUS", std::monostate{}, 'b');
    CHECK(service.handle(valid).ok);
    const auto before = clock.calls;
    CHECK(service.handle(valid).ok); // Baseline the same replay path while disabled.
    const auto disabled_calls = clock.calls - before;
    CHECK(trace.records().empty());
    CHECK(trace.begin());
    const auto enabled_before = clock.calls;
    CHECK(service.handle(valid).ok); // Actual replay takes the early return.
    CHECK(clock.calls - enabled_before == disabled_calls + 2);
    CHECK(service.handle(request("STATUS", std::monostate{}, 'c')).ok);
    CHECK(service.handle(request("STATUS", std::monostate{}, 'd', '1', "other")).error ==
          ErrorCode::AuthenticationRequired);
    const auto records = trace.records();
    CHECK(records.size() == 6 && trace.open_spans() == 0 && !trace.overflow());
    for (std::size_t i = 0; i < records.size(); i += 2) {
        CHECK(records[i].kind == wsprrypico::runtime::ActivityKind::Status);
        CHECK(records[i].phase == wsprrypico::runtime::ActivityPhase::Begin);
        CHECK(records[i + 1].phase == wsprrypico::runtime::ActivityPhase::End);
        CHECK(records[i].span == records[i + 1].span);
        CHECK(records[i + 1].outcome == wsprrypico::runtime::ActivityOutcome::Complete);
        CHECK(records[i].monotonic_ns < records[i + 1].monotonic_ns);
    }
    CHECK(!service.activity().owned && !service.activity().output_active);
    CHECK(service.status().state == State::Empty);
    trace.end();
    const auto end_calls = clock.calls;
    CHECK(service.handle(valid).ok);
    CHECK(clock.calls - end_calls == disabled_calls);
    CHECK(trace.records().size() == 6);
    // Clear the process-global trace so subsequent tests start disabled and empty.
    CHECK(trace.begin());
    trace.end();
}

void test_negotiation_sessions_and_unknown_operations() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    JobService service(clock, engine, identities);

    CHECK(service.handle(request("STATUS")).error == ErrorCode::HelloRequired);
    CHECK(service.handle(request("HELLO", HelloBody{{"native-execution/2"}})).error ==
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

void test_local_launch_status_race() {
    for (const bool local : {false, true}) {
        VirtualClock clock;
        MockRfEngine engine;
        engine.local_scheduling = local;
        ServiceConfig config;
        config.minimum_arm_lead_ns = 10;
        TestIdentitySource identities;
        JobService service(clock, engine, identities, config);
        establish_owner(service);
        const auto job = sample_job();
        CHECK(service.handle(request("LOAD", job, 'c')).ok);
        CHECK(
            service
                .handle(request("ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}, 'd'))
                .ok);
        service.poll();
        CHECK(service.status().state == State::Armed && !service.status().output_active);
        clock.advance(10);
        // Local timer launches between the foreground poll and STATUS capture.
        // A nonlocal engine has no such authority: its unexpected output must
        // remain visible as an inconsistent armed/active safety observation.
        engine.active = true;
        const auto activity = service.activity();
        CHECK(activity.output_active && activity.owned);
        CHECK(activity.state == (local ? State::Running : State::Armed));
        const auto response = service.handle(request("STATUS", std::monostate{}, 'e'));
        CHECK(response.ok && response.status_snapshot);
        const auto snapshot = *response.status_snapshot;
        CHECK(snapshot.output_active && snapshot.job_id == job.job_id);
        CHECK(snapshot.state == (local ? State::Running : State::Armed));
        service.poll();
        CHECK(service.status().state == State::Running);
        engine.force_failure = true;
        service.poll();
        CHECK(service.status().state == State::Failed && !service.status().output_active);
        engine.active = true;
        CHECK(service.status().state == State::Failed && service.status().output_active);
        engine.active = false;
        CHECK(response.status_snapshot->output_active); // Immutable observation.
    }
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
    clock.advance(start_window_ns(clock.value.utc_now_ns + 10) + 10);
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
    CHECK(blocked.handle(request("HELLO", HelloBody{{"native-execution/1"}})).error == ErrorCode::DeviceFault);

    MockRfEngine safe_engine;
    TestIdentitySource safe_identities;
    JobService service(clock, safe_engine, safe_identities);
    const auto unsupported = service.handle(request("HELLO", HelloBody{{"native-execution/2"}}));
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

void test_shared_adjustment_replay_lifetimes() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource ids;
    JobService service(clock, engine, ids);
    establish_owner(service);
    auto job = sample_job();
    job.allow_frequency_adjustment = true;
    job.total_duration_ns = 512;
    job.events.clear();
    for (std::size_t i = 0; i < 512; ++i) {
        job.events.push_back({i, 1, true, 135500000000000ULL});
        engine.adjustments.push_back({i, 135500000000000ULL, 135500000000001ULL});
    }
    const auto load = request("LOAD", job, 'c');
    const auto first = service.handle(load);
    CHECK(first.ok && first.adjustments.size() == 512);
    const auto expected = first.adjustments;
    // Replacing the caller's result cannot change cached or active replies.
    auto replaced = first;
    replaced.adjustments.clear();
    CHECK(replaced.adjustments.empty() && first.adjustments == expected);
    largest_allocation = 0;
    CHECK(service.handle(load) == first);
    CHECK(largest_allocation < 512 * sizeof(FrequencyAdjustment));
    for (char digit = '4'; digit <= '9'; ++digit) {
        auto retry = request("LOAD", job, digit);
        largest_allocation = 0;
        CHECK(service.handle(retry) == first);
        CHECK(largest_allocation < 512 * sizeof(FrequencyAdjustment));
    }
    CHECK(engine.prepare_calls == 1);
    CHECK(service.handle(request("ABORT", AbortBody{job.job_id}, 'd')).ok);
    CHECK(service.handle(request("RELEASE", {}, 'e')).ok);
    CHECK(claim(service, '1', 'f').ok);
    auto retained = request("LOAD", job, '0');
    largest_allocation = 0;
    CHECK(service.handle(retained) == first);
    CHECK(largest_allocation < 512 * sizeof(FrequencyAdjustment));
    CHECK(service.status().state == State::Empty && engine.prepare_calls == 1);
    auto conflict = retained;
    conflict.payload_digest[0] ^= 1;
    CHECK(service.handle(conflict).error == ErrorCode::RequestIdReuse);
    service.reset();
    CHECK(first.adjustments == expected && first.adjustments.size() == 512);
    // Value equality must work for separately allocated lists too.
    CHECK(first.adjustments == AdjustmentList(engine.adjustments));
    engine.adjustments[0].realized_frequency_nhz += 1;
    CHECK(!(first.adjustments == AdjustmentList(engine.adjustments)));
    CHECK(first.adjustments[0].realized_frequency_nhz == 135500000000001ULL);
}

void test_identical_adjustments_preserve_distinct_job_replays() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource ids;
    JobService service(clock, engine, ids);
    establish_owner(service);
    auto job = sample_job();
    job.allow_frequency_adjustment = true;
    engine.adjustments = {{0, *job.events[0].frequency_nhz, *job.events[0].frequency_nhz + 1}};
    const auto first = service.handle(request("LOAD", job, 'c'));
    CHECK(first.ok);
    CHECK(service.handle(request("ABORT", AbortBody{job.job_id}, 'd')).ok);
    CHECK(service.handle(request("RELEASE", {}, 'e')).ok);
    CHECK(claim(service, '1', 'f').ok);
    auto second_job = job;
    second_job.job_id = std::string(32, '9');
    const auto second = service.handle(request("LOAD", second_job, '0'));
    CHECK(second.ok && second.job_id != first.job_id);
    CHECK(second.adjustments == first.adjustments);
    CHECK(service.handle(request("ABORT", AbortBody{second_job.job_id}, '1')).ok);
    CHECK(service.handle(request("RELEASE", {}, '2')).ok);
    CHECK(claim(service, '1', '3').ok);
    auto third_job = job;
    third_job.job_id = std::string(32, '8');
    ++engine.adjustments[0].realized_frequency_nhz;
    const auto third = service.handle(request("LOAD", third_job, '4'));
    CHECK(third.ok && third.adjustments != first.adjustments);
    CHECK(third.adjustments[0].realized_frequency_nhz ==
          first.adjustments[0].realized_frequency_nhz + 1);
    CHECK(service.handle(request("LOAD", job, '5')) == first);
    CHECK(service.handle(request("LOAD", second_job, '6')) == second);
    CHECK(service.status().job_id == third_job.job_id);
    service.reset();
    CHECK(first.adjustments == second.adjustments);
    CHECK(first.adjustments != third.adjustments);
}

void test_execution_input_handoff_and_replay() {
    for (const bool local : {false, true}) {
        for (const bool independent : {false, true}) {
            for (const unsigned outcome : {0U, 1U, 2U, 3U}) {
                // Completion, owner abort, uncertain stop, rejected handoff.
                struct WatchScope {
                    WatchScope() {
                        begin_event_watch();
                    }
                    ~WatchScope() {
                        end_event_watch();
                    }
                } watch_scope;
                VirtualClock clock;
                MockRfEngine engine;
                engine.local_scheduling = local;
                engine.independent_plan = independent;
                engine.reject_begin = outcome == 3;
                TestIdentitySource ids;
                ServiceConfig config;
                config.minimum_arm_lead_ns = 10;
                JobService service(clock, engine, ids, config);
                establish_owner(service);
                auto job = sample_job();
                job.events.resize(512);
                job.total_duration_ns = 512;
                for (std::size_t i = 0; i < job.events.size(); ++i)
                    job.events[i] = {i, 1, true, 135500000000000ULL};
                const auto load = request("LOAD", job, 'c');
                watched_event_bytes = EventList::page_events * sizeof(RfEvent);
                const auto loaded = service.handle(load);
                watched_event_bytes = 0;
                CHECK(loaded.ok && watched_event_allocation_count == 8 &&
                      watched_event_release_count == 0);
                const auto body = ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000};
                const auto arm = request("ARM", body, 'd');
                const auto armed = service.handle(arm);
                CHECK(armed.ok == !(local && outcome == 3));
                CHECK((watched_event_release_count == 8) == (local && independent && outcome != 3));
                if (outcome != 3) {
                    CHECK(service.handle(load) == loaded);
                    CHECK(service.handle(request("LOAD", job, 'e')) == loaded);
                    auto changed = job;
                    ++*changed.events.back().frequency_nhz;
                    CHECK(service.handle(request("LOAD", changed, '0')).error ==
                          ErrorCode::JobIdConflict);
                    CHECK(service.handle(arm) == armed);
                    CHECK(service.handle(request("ARM", body, '1')) == armed);
                }
                clock.advance(10);
                service.poll();
                CHECK((watched_event_release_count == 8) == (independent && outcome != 3));
                if (outcome == 3) {
                    CHECK(service.status().state == State::Failed &&
                          !service.status().output_active);
                    CHECK(service.status().terminal_records.size() == 1);
                } else if (outcome == 1 || outcome == 2) {
                    engine.reject_disable = outcome == 2;
                    const auto aborted =
                        service.handle(request("ABORT", AbortBody{job.job_id}, '2'));
                    CHECK(aborted.ok == (outcome == 1));
                    CHECK(service.status().state ==
                          (outcome == 1 ? State::Aborted : State::Failed));
                    CHECK(service.status().output_active == (outcome == 2));
                } else {
                    CHECK(service.status().state == State::Running &&
                          service.status().output_active);
                    clock.advance(512);
                    service.poll();
                    CHECK(service.status().state == State::Complete &&
                          !service.status().output_active);
                    CHECK(watched_event_release_count == 8);
                }
                if (outcome == 0 || outcome == 1) {
                    CHECK(service.handle(request("LOAD", job, '3')) == loaded);
                    auto changed = job;
                    ++changed.events.back().duration_ns;
                    CHECK(service.handle(request("LOAD", changed, '4')).error ==
                          ErrorCode::JobIdConflict);
                    CHECK(service.handle(request("ARM", body, '5')) == armed);
                    CHECK(engine.begin_calls == 1);
                    CHECK(service.handle(request("RELEASE", {}, '6')).ok);
                    CHECK(claim(service, '1', '7').ok);
                    job.job_id = id('4');
                    CHECK(service.handle(request("LOAD", job, '8')).ok);
                    CHECK(service.status().job_id == job.job_id);
                }
            }
        }
    }
}

void test_completed_event_storage_and_replacement() {
    for (const bool unknown_output : {false, true}) {
        struct ResetMeasurement {
            ResetMeasurement() {
                begin_event_watch();
            }
            ~ResetMeasurement() {
                available_memory = nullptr;
                end_event_watch();
            }
        } reset;
        VirtualClock clock;
        MockRfEngine engine;
        TestIdentitySource identities;
        ServiceConfig config;
        config.minimum_arm_lead_ns = 10;
        JobService service(clock, engine, identities, config);
        establish_owner(service);
        auto job = sample_job();
        job.total_duration_ns = 512;
        job.events.clear();
        for (std::size_t i = 0; i < 512; ++i)
            job.events.push_back({i, 1, true, 135500000000000ULL});
        const auto load_request = request("LOAD", job, 'c');
        watched_event_bytes = EventList::page_events * sizeof(RfEvent);
        const auto loaded = service.handle(load_request);
        watched_event_bytes = 0;
        CHECK(loaded.ok && watched_event_allocation_count == 8 && watched_event_release_count == 0);
        const auto arm_body = ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000};
        const auto armed = service.handle(request("ARM", arm_body, 'd'));
        CHECK(armed.ok);
        clock.advance(10);
        service.poll();
        CHECK(service.status().state == State::Running && watched_event_release_count == 0);
        engine.reject_disable = unknown_output;
        clock.advance(job.total_duration_ns);
        service.poll();
        if (unknown_output) {
            CHECK(service.status().state == State::Failed);
            CHECK(service.status().output_active && watched_event_release_count == 0);
            continue;
        }
        const auto terminal = service.status();
        CHECK(terminal.state == State::Complete && !terminal.output_active);
        CHECK(terminal.job_id == job.job_id && terminal.terminal_records.size() == 1);
        CHECK(service.handle(request("LOAD", job, 'e')) == loaded);
        auto changed = job;
        changed.events[0].frequency_nhz = 135500000000001ULL;
        CHECK(service.handle(request("LOAD", changed, 'f')).error == ErrorCode::JobIdConflict);
        CHECK(service.handle(request("ARM", arm_body, '0')) == armed);
        CHECK(engine.begin_calls == 1 && service.status() == terminal);
        // Inject the admission headroom recovered by releasing this allocation.
        // This is a host lifetime regression, not a target heap measurement.
        available_memory = []() -> std::size_t {
            return watched_event_release_count == 8 ? 100000 : 100000 - 512 * sizeof(RfEvent);
        };
        job.job_id = id('4');
        CHECK(service.handle(request("LOAD", job, '1')).ok);
        CHECK(watched_event_release_count == 8);
        CHECK(service.status().state == State::Loaded);
        CHECK(service.status().terminal_records == terminal.terminal_records);
    }
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

void test_bounded_local_completion_acknowledgement() {
    for (const bool external : {false, true})
        for (const bool local : {false, true}) {
            for (const auto allowance : {0ULL, 100'000ULL, 1'000'000ULL, 1'000'000'000ULL}) {
                for (const bool finishes : {false, true}) {
                    VirtualClock clock;
                    MockRfEngine engine;
                    engine.local_scheduling = local;
                    engine.external_completion = external;
                    engine.acknowledgement_ns = allowance; // Includes zero and excessive requests.
                    engine.stall_completion = true;
                    TestIdentitySource identities;
                    ServiceConfig config;
                    config.minimum_arm_lead_ns = 10;
                    JobService service(clock, engine, identities, config);
                    establish_owner(service);
                    const auto job = sample_job();
                    CHECK(service.handle(request("LOAD", job, 'c')).ok);
                    CHECK(
                        service
                            .handle(request(
                                "ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}, 'd'))
                            .ok);
                    clock.advance(10);
                    service.poll();
                    clock.advance(job.total_duration_ns +
                                  1000); // Offset beyond the final boundary.
                    service.poll();
                    const auto limit = std::min<std::uint64_t>(
                        allowance, external ? config.output_disable_timeout_ns
                                            : RfEngine::maximum_completion_acknowledgement_ns);
                    const bool grace = local && allowance;
                    CHECK(service.status().state == (grace ? State::Running : State::Failed));
                    if (!grace) {
                        CHECK(!service.status().output_active);
                        CHECK(service.status().terminal_records.front().error ==
                              ErrorCode::DeviceFault);
                        continue;
                    }
                    CHECK(service.status().owner_id.has_value());
                    if (finishes) {
                        clock.advance(5000); // Delayed launch/tail acknowledgement, no new job.
                        engine.stall_completion = false;
                        service.poll();
                        CHECK(service.status().state == State::Complete);
                    } else {
                        clock.advance(limit - 1000);
                        service.poll();
                        CHECK(service.status().state == State::Running);
                        clock.advance(1);
                        service.poll();
                        CHECK(service.status().state == State::Failed);
                        CHECK(service.status().terminal_records.front().error ==
                              ErrorCode::DeviceFault);
                    }
                    CHECK(!service.status().output_active);
                }
            }
        }
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
    CHECK(service.handle(request("HELLO", HelloBody{{"native-execution/1"}})).error == ErrorCode::DeviceFault);
}

void test_utc_discipline_boundaries() {
    std::uint64_t now = 1'000'000'000ULL;
    auto monotonic = [](void* context) { return *static_cast<std::uint64_t*>(context); };
    wsprrypico::time::DisciplineConfig config;
    config.synchronized_for_ns = 100;
    config.holdover_for_ns = 200;
    config.max_observation_age_ns = 50;
    config.max_uncertainty_ns = 20;
    config.oscillator_drift_ppb = 10'000'000;
    wsprrypico::time::UtcDiscipline clock(monotonic, &now, config);
    CHECK(clock.snapshot().state == ClockState::Unsynchronized);
    CHECK(!clock.observe(5'000, now + 1, 1, LeapState::Normal));
    CHECK(!clock.observe(5'000, now - 51, 1, LeapState::Normal));
    CHECK(!clock.observe(5'000, now, 21, LeapState::Normal));
    CHECK(!clock.observe(5'000, now, 1, LeapState::Unknown));
    CHECK(!clock.observe(5'000, now, 1, LeapState::InsertPending));
    CHECK(!clock.observe(5'000, now, 1, LeapState::Normal, 6'000));
    CHECK(clock.observe(5'000, now, 10, LeapState::Normal));
    auto sample = clock.snapshot();
    CHECK(sample.state == ClockState::Synchronized);
    CHECK(sample.utc_now_ns == 5'000);
    CHECK(sample.uncertainty_ns == 10);
    now += 101;
    sample = clock.snapshot();
    CHECK(sample.state == ClockState::Holdover);
    CHECK(sample.utc_now_ns == 5'101);
    CHECK(sample.sync_age_ns == 101);
    CHECK(sample.uncertainty_ns >= 12);
    now += 100;
    CHECK(clock.snapshot().state == ClockState::Unsynchronized);
    clock.invalidate();
    CHECK(clock.snapshot().leap == LeapState::Unknown);
    now = 10;
    CHECK(clock.observe(std::numeric_limits<std::uint64_t>::max(), now, 1, LeapState::Normal));
    ++now;
    CHECK(clock.snapshot().state == ClockState::Unsynchronized);
}

void test_usb_time_source_exchange() {
    std::uint64_t now = 1000;
    auto monotonic = [](void* context) { return *static_cast<std::uint64_t*>(context); };
    wsprrypico::time::UtcDiscipline clock(monotonic, &now);
    wsprrypico::time::UsbTimeSource source(clock);
    CHECK(source.command("SET 1000 9000 10 NORMAL").find("invalid_observation") !=
          std::string::npos);
    CHECK(source.command("SAMPLE").find("1000") != std::string::npos);
    CHECK(source.command("SET 999 9000 10 NORMAL").find("invalid_observation") !=
          std::string::npos);
    CHECK(source.command("SAMPLE").find("1000") != std::string::npos);
    now += 10;
    CHECK(source.command("SET 1000 9000 20 NORMAL").find("\"ok\":true") != std::string::npos);
    CHECK(clock.snapshot().utc_now_ns == 9010);
    CHECK(source.command("SET 1000 9000 20 NORMAL").find("invalid_observation") !=
          std::string::npos);
    CHECK(source.command("INVALIDATE").find("unsynchronized") != std::string::npos);
    CHECK(clock.snapshot().state == ClockState::Unsynchronized);
    CHECK(source.command("SAMPLE extra").find("unknown_command") != std::string::npos);
}

void test_physical_console_abort() {
    for (unsigned stage = 0; stage < 4; ++stage) {
        VirtualClock clock;
        MockRfEngine engine;
        TestIdentitySource identities;
        ServiceConfig config;
        config.minimum_arm_lead_ns = 10;
        JobService service(clock, engine, identities, config);
        establish_owner(service);
        CHECK(service.handle(request("LOAD", sample_job(), 'c')).ok);
        if (stage)
            CHECK(service
                      .handle(
                          request("ARM", ArmBody{id('3'), clock.value.utc_now_ns + 10, 1000}, 'd'))
                      .ok);
        if (stage >= 2) {
            clock.advance(10);
            service.poll();
            CHECK(engine.output_active());
        }
        if (stage == 3)
            engine.reject_disable = true;
        // A remote principal remains unable to invoke the physical control.
        CHECK(service.handle(request("LOCAL_ABORT", {}, 'e')).error == ErrorCode::UnknownOperation);
        const auto result = service.local_abort();
        if (stage == 3) {
            CHECK(!result.ok && result.error == ErrorCode::OutputStateUnknown);
            CHECK(service.status().state == State::Failed);
            CHECK(service.status().owner_id.has_value());
            CHECK(!service.local_abort().ok);
        } else {
            CHECK(result.ok && !engine.output_active());
            CHECK(service.status().state == State::Aborted && !service.status().owner_id);
            CHECK(service.status().terminal_records.front().job_id == id('3'));
            CHECK(service.status().terminal_records.front().state == State::Aborted);
            CHECK(service.local_abort().ok);
        }
    }
}

void test_physical_output_inhibit() {
    for (bool fail_disable : {false, true}) {
        VirtualClock clock;
        MockRfEngine engine;
        TestIdentitySource identities;
        ServiceConfig config;
        config.minimum_arm_lead_ns = 10;
        JobService service(clock, engine, identities, config);
        establish_owner(service); // Model an owner independent of the scheduler.
        CHECK(service.handle(request("LOAD", sample_job(), 'c')).ok);
        CHECK(
            service.handle(request("ARM", ArmBody{id('3'), clock.value.utc_now_ns + 10, 1000}, 'd'))
                .ok);
        clock.advance(10);
        service.poll();
        CHECK(engine.output_active());
        engine.reject_disable = fail_disable;
        CHECK(service.local_inhibit_output() == !fail_disable);
        CHECK(service.output_inhibited());
        CHECK(service.handle(request("CLAIM", ClaimBody{id('2'), 10'000}, 'e')).error ==
              ErrorCode::Busy);
        CHECK(
            service.handle(request("ARM", ArmBody{id('3'), clock.value.utc_now_ns + 10, 1000},
                                   'd'))
                .error == ErrorCode::Busy); // Prior success replay.
        CHECK(service.handle(request("STATUS", {}, 'f')).ok);
        const auto stopped = service.status();
        const wsprrypico::provisioning::RfSetupAdmission setup{!fail_disable,
                                                               true,
                                                               true,
                                                               service.output_inhibited(),
                                                               !fail_disable,
                                                               true,
                                                               !stopped.owner_id &&
                                                                   !stopped.output_active,
                                                               true,
                                                               false,
                                                               stopped.state,
                                                               stopped.owner_id.has_value(),
                                                               stopped.job_id.has_value(),
                                                               stopped.output_active};
        CHECK(wsprrypico::provisioning::rf_setup_allowed(setup) == !fail_disable);
        if (!fail_disable) {
            CHECK(!engine.output_active());
            CHECK(!service.status().owner_id);
            CHECK(stopped.state == State::Aborted && stopped.job_id == id('3'));
            CHECK(stopped.terminal_records.front().job_id == id('3') &&
                  stopped.terminal_records.front().state == State::Aborted);
            service.reset();
            CHECK(service.output_inhibited());
            CHECK(service.handle(request("CLAIM", ClaimBody{id('2'), 10'000}, 'a')).error ==
                  ErrorCode::Busy);
        } else {
            CHECK(engine.output_active());
            CHECK(service.status().state == State::Failed);
        }
    }
}

void test_activity_with_retained_history() {
    VirtualClock clock;
    MockRfEngine engine;
    TestIdentitySource identities;
    ServiceConfig config;
    config.minimum_arm_lead_ns = 10;
    JobService service(clock, engine, identities, config);
    unsigned sequence = 0;
    auto invoke = [&](std::string operation, RequestBody body = std::monostate{}) {
        auto r = request(std::move(operation), std::move(body));
        std::ostringstream identity;
        identity << std::hex << std::setw(32) << std::setfill('0') << ++sequence;
        r.request_id = identity.str();
        r.payload_digest = sha256(std::span(
            reinterpret_cast<const std::uint8_t*>(r.request_id.data()), r.request_id.size()));
        return service.handle(r);
    };
    auto observe = [&](State state, bool output, bool owned, std::size_t history) {
        const auto before_status = allocations;
        const auto status = service.status();
        CHECK(allocations > before_status); // Reproduces the former hot-loop cost.
        CHECK(status.state == state && status.output_active == output);
        CHECK(status.owner_id.has_value() == owned && status.terminal_records.size() == history);
        const auto before_activity = allocations;
        for (unsigned i = 0; i < 100; ++i) {
            const auto activity = service.activity();
            CHECK(activity.state == state && activity.output_active == output);
            CHECK(activity.owned == owned);
        }
        CHECK(allocations == before_activity);
        CHECK(service.status() == status); // Observation never prunes or changes history.
    };
    observe(State::Empty, false, false, 0);
    engine.active = true;
    observe(State::Empty, true, false, 0); // Unexpected output is never hidden.
    engine.active = false;
    CHECK(invoke("HELLO", HelloBody{{"native-execution/1"}}).ok);
    for (unsigned i = 0; i < 8; ++i) {
        CHECK(invoke("CLAIM", ClaimBody{id('2'), 10'000}).ok);
        const auto job = sample_job("3456789a"[i]);
        CHECK(invoke("LOAD", job).ok);
        observe(State::Loaded, false, true, i);
        CHECK(invoke("ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}).ok);
        observe(State::Armed, false, true, i);
        clock.advance(10);
        service.poll();
        observe(State::Running, true, true, i);
        clock.advance(job.total_duration_ns);
        service.poll();
        observe(State::Complete, false, true, i + 1);
        CHECK(invoke("RELEASE").ok);
        observe(State::Empty, false, false, i + 1);
    }
    CHECK(invoke("CLAIM", ClaimBody{id('2'), 10'000}).ok);
    const auto job = sample_job('b');
    CHECK(invoke("LOAD", job).ok);
    CHECK(invoke("ARM", ArmBody{job.job_id, clock.value.utc_now_ns + 10, 1000}).ok);
    clock.advance(10);
    service.poll();
    engine.force_failure = true;
    service.poll();
    observe(State::Failed, false, true, 8);
    clock.advance(10'000'000'000ULL);
    service.poll();
    observe(State::Failed, false, false, 8);
}

using Test = std::pair<const char*, void (*)()>;

} // namespace

int main() {
    allocate_input = [](std::size_t size) -> void* {
        ++allocations;
        largest_allocation = std::max(largest_allocation, size);
        return std::malloc(size);
    };
    const std::vector<Test> tests{
        {"identical adjustments preserve distinct job replays",
         test_identical_adjustments_preserve_distinct_job_replays},
        {"allocation-free activity with retained history", test_activity_with_retained_history},
        {"physical Console abort", test_physical_console_abort},
        {"physical output inhibit", test_physical_output_inhibit},
        {"allocation-free SHA padding", test_sha256_allocation_free_padding_boundaries},
        {"paged JSON and digest boundaries", test_paged_json_and_digest_boundaries},
        {"paged nested wide object keys", test_paged_nested_wide_object_keys},
        {"CW frequency events", test_cw_frequency_events},
        {"extended Morse boundaries", test_extended_morse_message_boundaries},
        {"status activity trace integration", test_status_activity_trace_integration},
        {"negotiation sessions and unknown operations",
         test_negotiation_sessions_and_unknown_operations},
        {"replay and ownership", test_replay_and_ownership},
        {"replay capacity is per session", test_replay_capacity_is_per_session},
        {"job validation and idempotency", test_job_validation_and_idempotency},
        {"clock and arm rejections", test_clock_and_arm_rejections},
        {"local execution and duplicate arm", test_local_execution_and_duplicate_arm},
        {"local launch status race", test_local_launch_status_race},
        {"missed start and abort safety", test_missed_start_and_abort_safety},
        {"clock loss at start misses job", test_clock_loss_at_start_misses_job},
        {"disable failure is terminal fault", test_disable_failure_is_terminal_fault},
        {"lease expiry and reset", test_lease_expiry_and_reset},
        {"safety gate and connection close", test_safety_gate_and_connection_close},
        {"adjustments and engine failure safety", test_adjustments_and_engine_failure_safety},
        {"shared adjustment replay lifetimes", test_shared_adjustment_replay_lifetimes},
        {"completed event storage and replacement", test_completed_event_storage_and_replacement},
        {"execution input handoff and replay", test_execution_input_handoff_and_replay},
        {"expired active lease and terminal retention",
         test_expired_active_lease_and_terminal_retention},
        {"engine completion watchdog", test_engine_completion_watchdog},
        {"bounded local completion acknowledgement", test_bounded_local_completion_acknowledgement},
        {"inhibited engine never reports output", test_inhibited_engine_never_reports_output},
        {"invalid configuration fails without exception",
         test_invalid_configuration_fails_without_exception},
        {"UTC discipline boundaries", test_utc_discipline_boundaries},
        {"USB time source exchange", test_usb_time_source_exchange},
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

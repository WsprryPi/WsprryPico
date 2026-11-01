// Production LOAD decoding and service copying under bounded input allocations.
#include "encoding/morse.hpp"
#include "standalone/scheduler.hpp"
#include "wtp/codec.hpp"
#include "wtp/memory_budget.hpp"

#include <array>
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <new>
#include <string>

using namespace wsprrypico::wtp;
namespace standalone = wsprrypico::standalone;
namespace {
struct alignas(std::max_align_t) Allocation {
    std::size_t bytes;
};
std::size_t calls = 0;
std::size_t fail_call = 0;
std::size_t live_bytes = 0;
std::size_t largest_request = 0;
constexpr char expired_principal[] =
    "qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq";
static_assert(sizeof(expired_principal) == 64);
std::size_t heap_calls = 0;
std::size_t heap_live_bytes = 0;
std::size_t expired_principal_frees = 0;
bool watch_principal = false;

void* heap_allocate(std::size_t bytes) {
    auto* allocation = static_cast<Allocation*>(std::malloc(sizeof(Allocation) + bytes));
    if (!allocation)
        throw std::bad_alloc();
    allocation->bytes = bytes;
    ++heap_calls;
    heap_live_bytes += bytes;
    return allocation + 1;
}
void heap_free(void* memory) noexcept {
    if (!memory)
        return;
    auto* allocation = static_cast<Allocation*>(memory) - 1;
    heap_live_bytes -= allocation->bytes;
    if (watch_principal && allocation->bytes == sizeof(expired_principal) &&
        std::memcmp(memory, expired_principal, sizeof(expired_principal)) == 0)
        ++expired_principal_frees;
    std::free(allocation);
}

void* bounded_allocate(std::size_t bytes) {
    ++calls;
    largest_request = std::max(largest_request, bytes);
    if ((fail_call && calls == fail_call) || bytes > 4096)
        return nullptr;
    auto* allocation = static_cast<Allocation*>(std::malloc(sizeof(Allocation) + bytes));
    if (!allocation)
        return nullptr;
    allocation->bytes = bytes;
    live_bytes += bytes;
    return allocation + 1;
}
void bounded_free(void* memory) {
    if (!memory)
        return;
    auto* allocation = static_cast<Allocation*>(memory) - 1;
    live_bytes -= allocation->bytes;
    std::free(allocation);
}
void reset(std::size_t fail = 0) {
    calls = 0;
    fail_call = fail;
    largest_request = 0;
}

std::string maximum_load() {
    std::string text =
        R"({"type":"request","protocol":"WTP/1","session_id":")" + std::string(32, '1') +
        R"(","request_id":")" + std::string(32, '2') + R"(","op":"LOAD","body":{"job_id":")" +
        std::string(32, '3') +
        R"(","profile":"rf-events/1","mode":"fskcw","total_duration_ns":"512","allow_frequency_adjustment":true,"events":[)";
    for (unsigned i = 0; i < 512; ++i) {
        if (i)
            text += ',';
        text += R"({"offset_ns":")" + std::to_string(i) +
                R"(","duration_ns":"1","rf_on":true,"frequency_nhz":"135500000000000"})";
    }
    return text + "]}}";
}
Request decode(const std::string& text) {
    const auto root = json::parse(text);
    assert(root);
    auto request = decode_request(
        *root, "test", std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
    assert(request && request->body_valid);
    return std::move(*request);
}

class TestClock final : public Clock {
  public:
    std::uint64_t monotonic_ns = 10'000'000'000ULL;
    ClockSnapshot snapshot() const override {
        return {ClockState::Synchronized, 1'000'000'000'000ULL, monotonic_ns, 1000, 0,
                LeapState::Normal,        std::nullopt};
    }
};
class TestIdentity final : public IdentitySource {
  public:
    std::string new_boot_id() override {
        return std::string(31, '0') + '1';
    }
};
class TestEngine final : public RfEngine {
  public:
    PrepareResult prepare(const Job&) override {
        ++preparations;
        return {true, {}};
    }
    bool begin(const Job&, std::uint64_t) override {
        return true;
    }
    EngineReport poll(std::uint64_t) override {
        return {};
    }
    bool disable(std::uint64_t) override {
        return true;
    }
    bool output_active() const override {
        return false;
    }
    unsigned preparations = 0;
};
Request request(std::string operation, RequestBody body, char id) {
    Request value;
    value.session_id = std::string(32, '1');
    value.request_id = std::string(32, id);
    value.principal = "test";
    value.operation = std::move(operation);
    value.body = std::move(body);
    value.payload_digest[0] = static_cast<std::uint8_t>(id);
    return value;
}
void admit(JobService& service) {
    const auto hello = service.handle(request("HELLO", HelloBody{{"WTP/1"}}, '4'));
    if (!hello.ok)
        std::cerr << "HELLO error " << static_cast<unsigned>(hello.error) << '\n';
    assert(hello.ok);
    const auto claim =
        service.handle(request("CLAIM", ClaimBody{std::string(32, '5'), 60000}, '5'));
    if (!claim.ok)
        std::cerr << "CLAIM error " << static_cast<unsigned>(claim.error) << '\n';
    assert(claim.ok);
}

void internal_control_memory() {
    TestClock clock;
    TestEngine engine;
    TestIdentity identity;
    JobService service(clock, engine, identity);
    assert(service.handle_internal(request("HELLO", HelloBody{{"WTP/1"}}, '9')).ok);
    const auto baseline = heap_live_bytes;
    constexpr char hex[] = "0123456789abcdef";
    for (unsigned i = 0; i != 64; ++i) {
        auto ping = request("PING", std::monostate{}, '1');
        ping.request_id.assign(32, '0');
        ping.request_id[30] = hex[i >> 4];
        ping.request_id[31] = hex[i & 15];
        ping.payload_digest[0] = static_cast<std::uint8_t>(i + 1);
        assert(service.handle_internal(std::move(ping)).ok);
    }
    assert(heap_live_bytes == baseline);
    auto foreign = request("PING", std::monostate{}, 'a');
    foreign.principal = "other";
    const auto refused = service.handle_internal(std::move(foreign));
    assert(!refused.ok && refused.error == ErrorCode::AuthenticationRequired);
}

std::size_t admission_origin = std::numeric_limits<std::size_t>::max();
std::size_t admission_extra = 0;
std::size_t request_lifetime_headroom() {
    const auto used = heap_live_bytes + live_bytes;
    if (admission_origin == std::numeric_limits<std::size_t>::max())
        admission_origin = used;
    // Fix capacity at the first check. Later real allocations consume it,
    // including full terminal history; no per-occurrence budget reset hides
    // retained growth. The request-lifetime case adds no history allowance.
    const auto capacity = admission_origin + 65536 + admission_extra;
    return used < capacity ? capacity - used : 0;
}
void adjustment_storage_round_trip() {
    for (const unsigned tones : {1U, 4U, 5U, 162U}) {
        std::vector<FrequencyAdjustment> expected;
        for (unsigned i = 0; i < 162; ++i)
            expected.push_back({i * 3, 7'040'100'000'000'000ULL + i % tones,
                                7'040'100'000'000'001ULL + i % tones});
        const auto baseline = heap_live_bytes;
        AdjustmentList list(expected);
        assert(list.size() == expected.size());
        assert(std::equal(list.begin(), list.end(), expected.begin()));
        if (tones <= 4)
            assert(heap_live_bytes - baseline < expected.size() * sizeof(FrequencyAdjustment) / 2);
        auto retained = list;
        list.clear();
        for (std::size_t i = 0; i < expected.size(); ++i)
            assert(retained[i] == expected[i]);
        assert(retained.begin()->event_index == expected.front().event_index);
        auto original = expected;
        ++expected[0].realized_frequency_nhz;
        assert(retained == AdjustmentList(original));
        assert(!(retained == AdjustmentList(expected)));
    }
    // A wide index is representable through the ordinary list, never truncated.
    for (const auto index : {511U, 16383U, 16384U, 65536U}) {
        const std::vector<FrequencyAdjustment> wide(10, {index, 1, 2});
        const AdjustmentList list(wide);
        assert(std::equal(list.begin(), list.end(), wide.begin()));
    }
    assert(AdjustmentList{}.empty());
}

void standalone_request_lifetime_admission(bool retained_history = false) {
    struct Flash final : standalone::Flash {
        std::array<std::uint8_t, 16384> bytes{};
        Flash() {
            bytes.fill(255);
        }
        bool read(std::size_t offset, std::span<std::uint8_t> output) override {
            std::copy_n(bytes.begin() + offset, output.size(), output.begin());
            return true;
        }
        bool erase(std::size_t offset) override {
            std::fill_n(bytes.begin() + offset, 4096, 255);
            return true;
        }
        bool program(std::size_t offset, std::span<const std::uint8_t> input) override {
            std::copy(input.begin(), input.end(), bytes.begin() + offset);
            return true;
        }
    } flash;
    struct Clock final : wsprrypico::wtp::Clock {
        std::uint64_t now = 116'000'000'000ULL;
        ClockSnapshot snapshot() const override {
            return {ClockState::Synchronized,
                    1'792'800'000'000'000'000ULL + now,
                    now,
                    1000,
                    0,
                    LeapState::Normal,
                    std::nullopt};
        }
    } clock;
    struct Engine final : RfEngine {
        unsigned preparations = 0;
        bool begun = false;
        PrepareResult prepare(const Job& job) override {
            ++preparations;
            PrepareResult result{true, {}};
            for (std::size_t i = 0; i < job.events.size(); ++i)
                result.adjustments.push_back(
                    {i, *job.events[i].frequency_nhz, *job.events[i].frequency_nhz + 1});
            return result;
        }
        bool begin(const Job&, std::uint64_t) override {
            begun = true;
            return true;
        }
        EngineReport poll(std::uint64_t) override {
            return {begun ? EngineState::Complete : EngineState::Idle, false};
        }
        bool disable(std::uint64_t) override {
            begun = false;
            return true;
        }
        bool output_active() const override {
            return false;
        }
    } engine;
    standalone::Store store(flash);
    assert(store.load());
    standalone::Config config;
    config.callsign = "AA0NT";
    config.locator = "EM18";
    config.power_dbm = 20;
    config.enabled = true;
    config.wspr_dial_frequency_hz = 14095600;
    config.schedules = {{120, 0}};
    assert(store.save(config));
    TestIdentity identity;
    JobService service(clock, engine, identity);
    standalone::Scheduler scheduler(store, service);
    const auto complete_occurrence = [&] {
        clock.now += 5'000'000'000ULL;
        scheduler.poll();
        assert(service.status().state == State::Complete && !service.status().owner_id);
        clock.now += 115'000'000'000ULL;
    };
    const unsigned warmup = retained_history ? 16 : 0;
    // Prime the host library's deque storage before measuring retained payloads.
    // libc++ allocates larger blocks lazily, unlike libstdc++'s initial storage.
    // Expire every warmup record so all measured history payloads still consume
    // the fixed 4 KiB allowance; no measured occurrence resets the capacity.
    for (unsigned occurrence = 0; occurrence != warmup; ++occurrence) {
        scheduler.poll();
        assert(service.status().state == State::Armed);
        assert(engine.preparations == occurrence + 1);
        complete_occurrence();
    }
    if (warmup) {
        clock.now += service.config().terminal_record_ttl_ns;
        service.poll();
        assert(service.status().state == State::Empty && service.status().terminal_records.empty());
    }
    admission_origin = std::numeric_limits<std::size_t>::max();
    admission_extra = retained_history ? 4096 : 0;
    for (unsigned occurrence = 0; occurrence != (retained_history ? 16 : 2); ++occurrence) {
        if (!retained_history)
            admission_origin = std::numeric_limits<std::size_t>::max();
        available_memory = request_lifetime_headroom;
        scheduler.poll();
        available_memory = nullptr;
        if (service.status().state != State::Armed)
            std::cerr << "Standalone occurrence " << occurrence + 1 << ": LOAD stage "
                      << scheduler.last_load_stage() << ", free "
                      << scheduler.last_load_free_after() << '\n';
        assert(service.status().state == State::Armed);
        assert(engine.preparations == warmup + occurrence + 1);
        complete_occurrence();
        assert(service.status().terminal_records.size() ==
               std::min<std::size_t>(occurrence + 1, service.config().terminal_record_entries));
    }
}
} // namespace

void* operator new(std::size_t bytes) {
    return heap_allocate(bytes);
}
void* operator new[](std::size_t bytes) {
    return heap_allocate(bytes);
}
void operator delete(void* memory) noexcept {
    heap_free(memory);
}
void operator delete[](void* memory) noexcept {
    heap_free(memory);
}
void operator delete(void* memory, std::size_t) noexcept {
    heap_free(memory);
}
void operator delete[](void* memory, std::size_t) noexcept {
    heap_free(memory);
}

int main() {
    adjustment_storage_round_trip();
    internal_control_memory();
    standalone_request_lifetime_admission();
    standalone_request_lifetime_admission(true);
    {
        TestClock quiet_clock;
        TestIdentity quiet_identity;
        TestEngine quiet_engine;
        JobService quiet_service(quiet_clock, quiet_engine, quiet_identity);
        const auto admitted_at = quiet_clock.monotonic_ns;
        {
            auto hello = request("HELLO", HelloBody{{"WTP/1"}}, '9');
            hello.principal = expired_principal;
            assert(quiet_service.handle(hello).ok);
        }
        // Only the internal Session retains this identity now. Replay records
        // retain session/request IDs, not the transport principal. No later
        // request may prune sessions and hide a missing idle-poll cleanup.
        watch_principal = true;
        const auto allocations_before_poll = heap_calls;
        quiet_clock.monotonic_ns = admitted_at + quiet_service.config().response_cache_ttl_ns - 1;
        quiet_service.poll();
        assert(expired_principal_frees == 0 && heap_calls == allocations_before_poll);
        ++quiet_clock.monotonic_ns;
        quiet_service.poll();
        assert(expired_principal_frees == 1 && heap_calls == allocations_before_poll);
        for (unsigned i = 0; i < 8; ++i) {
            ++quiet_clock.monotonic_ns;
            quiet_service.poll();
        }
        assert(expired_principal_frees == 1 && heap_calls == allocations_before_poll);
        watch_principal = false;
    }
    allocate_input = bounded_allocate;
    deallocate_input = bounded_free;
    const auto text = maximum_load();

    reset();
    auto decoded = decode(text);
    const auto& maximum = std::get<Job>(decoded.body);
    assert(maximum.events.valid() && maximum.events.size() == 512);
    assert(calls == 8 && largest_request == 64 * sizeof(RfEvent));
    const auto digest = job_digest(maximum);

    Job copied = maximum;
    assert(copied.events.valid() && copied == maximum && job_digest(copied) == digest);
    Job moved = std::move(copied);
    assert(moved == maximum && copied.events.empty());

    for (std::size_t page = 1; page <= 8; ++page) {
        reset(page);
        auto rejected = decode(text);
        const auto& job = std::get<Job>(rejected.body);
        assert(!job.events.valid() && job.events.size() == 0 &&
               job.events.failure() == EventList::Failure::AllocationFailed);
    }

    TestClock clock;
    TestIdentity identity;
    for (std::size_t page = 1; page <= 8; ++page) {
        TestEngine engine;
        JobService service(clock, engine, identity);
        admit(service);
        reset();
        auto load = decoded;
        reset(page);
        load.request_id = std::string(31, '6') + static_cast<char>('0' + page);
        const auto response = service.handle(load);
        const auto status = service.status();
        assert(!response.ok && response.error == ErrorCode::InternalError);
        assert(status.state == State::Empty && status.owner_id == std::string(32, '5') &&
               !status.job_id && !status.output_active);
        assert(engine.preparations == 0);
    }

    reset();
    TestEngine engine;
    JobService service(clock, engine, identity);
    admit(service);
    auto accepted = service.handle(decoded);
    assert(accepted.ok && accepted.state == State::Loaded &&
           service.status().job_id == std::string(32, '3'));

    // Production adapters transfer decoded requests. Prove that a maximum
    // LOAD can cross the service boundary even when the first event-page copy
    // would fail; no second event list is allocated by the service.
    reset();
    auto transferred = decode(text);
    TestEngine transfer_engine;
    JobService transfer_service(clock, transfer_engine, identity);
    admit(transfer_service);
    reset(1);
    auto transferred_response = transfer_service.handle(std::move(transferred));
    assert(transferred_response.ok && transferred_response.state == State::Loaded && calls == 0 &&
           transfer_engine.preparations == 1);

    Job over_limit;
    assert(!over_limit.events.assign(513, {}));
    assert(over_limit.events.failure() == EventList::Failure::LimitExceeded);

    wsprrypico::encoding::MorseMessage message;
    message.job_id = std::string(32, '7');
    message.mode = "qrss";
    message.text = "E";
    message.mark_frequency_nhz = 135'500'000'000'000ULL;
    message.dot_ns = 1'000'000'000ULL;
    message.dash_ns = 3'000'000'000ULL;
    message.intra_gap_ns = 1'000'000'000ULL;
    message.character_gap_ns = 3'000'000'000ULL;
    message.word_gap_ns = 7'000'000'000ULL;
    reset(1);
    const auto compile_failure = wsprrypico::encoding::compile_message(message);
    assert(!compile_failure.job && compile_failure.error == "resource_exhausted");

    service.reset();
    transfer_service.reset();
    decoded.body = std::monostate{};
    moved.events.clear();
    accepted.adjustments.clear();
    allocate_input = std::malloc;
    deallocate_input = std::free;
    assert(live_bytes == 0);
    std::cout << "Paged decoder and service copy pass eight page-failure boundaries; largest block "
              << 64 * sizeof(RfEvent) << " bytes\n";
}

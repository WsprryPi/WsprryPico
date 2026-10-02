// Production LOAD decoding and service copying under bounded input allocations.
#include "encoding/morse.hpp"
#include "wtp/codec.hpp"

#include <cassert>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <new>
#include <string>

using namespace wsprrypico::wtp;
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
std::size_t expired_principal_frees = 0;
bool watch_principal = false;

void* heap_allocate(std::size_t bytes) {
    auto* allocation = static_cast<Allocation*>(std::malloc(sizeof(Allocation) + bytes));
    if (!allocation)
        throw std::bad_alloc();
    allocation->bytes = bytes;
    ++heap_calls;
    return allocation + 1;
}
void heap_free(void* memory) noexcept {
    if (!memory)
        return;
    auto* allocation = static_cast<Allocation*>(memory) - 1;
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
        quiet_clock.monotonic_ns =
            admitted_at + quiet_service.config().response_cache_ttl_ns - 1;
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

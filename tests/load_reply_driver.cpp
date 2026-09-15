// Host-only allocation model: production endpoint/service/planner, inactive sink.
#include "rf/stream_engine.hpp"
#include "standalone/wtp_profile.hpp"
#include "wtp/codec.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/memory_budget.hpp"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <new>

using namespace wsprrypico;
namespace {
struct alignas(std::max_align_t) Allocation {
    std::size_t bytes;
    bool tracked;
};
bool tracking = false;
std::size_t live = 0, peak = 0, page_live = 0, total_peak = 0;
std::size_t peak_cpp = 0, peak_pages = 0;
bool whole = false;
void sample_peak() {
    if (live + page_live > total_peak) {
        total_peak = live + page_live;
        peak_cpp = live;
        peak_pages = page_live;
    }
}
} // namespace
void* operator new(std::size_t size) {
    auto* p = static_cast<Allocation*>(std::malloc(sizeof(Allocation) + size));
    if (!p)
        throw std::bad_alloc();
    *p = {size, tracking};
    if (tracking) {
        live += size;
        peak = std::max(peak, live);
        sample_peak();
    }
    return p + 1;
}
void operator delete(void* ptr) noexcept {
    if (!ptr)
        return;
    auto* p = static_cast<Allocation*>(ptr) - 1;
    if (p->tracked)
        live -= p->bytes;
    std::free(p);
}
void operator delete(void* ptr, std::size_t) noexcept {
    ::operator delete(ptr);
}
namespace {
struct Clock : wtp::Clock {
    wtp::ClockSnapshot now{};
    wtp::ClockSnapshot snapshot() const override {
        return now;
    }
};
struct Ids : wtp::IdentitySource {
    std::string new_boot_id() override {
        return "b512a9e82baeee7580de50adf888d32b";
    }
};
struct Sink : rf::BlockSink {
    unsigned starts = 0;
    bool stop(std::uint64_t) override {
        return true;
    }
    bool submit(std::uint64_t, std::uint64_t, std::span<const std::uint32_t>,
                std::uint64_t) override {
        ++starts;
        return false;
    }
    bool arm(std::uint64_t, std::uint64_t, std::uint64_t, rf::LaunchGuard) override {
        ++starts;
        return false;
    }
    rf::SinkReport poll(std::uint64_t) override {
        return {};
    }
    bool output_active() const override {
        return false;
    }
};
struct CountingEngine : wtp::RfEngine {
    rf::StreamEngine engine;
    unsigned preparations = 0;
    explicit CountingEngine(Sink& sink) : engine(sink) {}
    wtp::PrepareResult prepare(const wtp::Job& job) override {
        ++preparations;
        return engine.prepare(job);
    }
    bool begin(const wtp::Job& job, std::uint64_t now) override {
        return engine.begin(job, now);
    }
    wtp::EngineReport poll(std::uint64_t now) override {
        return engine.poll(now);
    }
    bool disable(std::uint64_t deadline) override {
        return engine.disable(deadline);
    }
    bool output_active() const override {
        return engine.output_active();
    }
};
constexpr std::size_t heap = 219704;
std::size_t background = 0, calls = 0, reply_pages = 0;
struct Sample {
    std::size_t live, pages, available;
} samples[16];
wtp::JobService* modeled_service = nullptr;
std::size_t available() {
    // Legacy mode isolates reply admission. Replay mode applies the budget
    // throughout primary and both replays, counting live input/output pages.
    // Both remain host allocation models, not whole-target heap emulators.
    if (!whole && modeled_service->activity().state != wtp::State::Loaded)
        return std::numeric_limits<std::size_t>::max();
    const auto used = live + (whole ? page_live : reply_pages) + background;
    const auto capacity = whole ? 219712 : heap;
    const auto free = used < capacity ? capacity - used : 0;
    if (calls < 16)
        samples[calls] = {live, reply_pages, free};
    ++calls;
    return free;
}
void* page(std::size_t bytes) {
    if (modeled_service->activity().state == wtp::State::Loaded)
        reply_pages += bytes;
    return std::malloc(bytes);
}
struct Page {
    void* ptr = nullptr;
    std::size_t bytes = 0;
} pages[128];
void* tracked_page(std::size_t bytes) {
    auto* ptr = std::malloc(bytes);
    if (!ptr)
        return nullptr;
    for (auto& item : pages) {
        if (!item.ptr) {
            item = {ptr, bytes};
            page_live += bytes;
            sample_peak();
            return ptr;
        }
    }
    std::abort();
}
void free_page(void* ptr) {
    if (!ptr)
        return;
    for (auto& item : pages) {
        if (item.ptr == ptr) {
            page_live -= item.bytes;
            item = {};
            std::free(ptr);
            return;
        }
    }
    std::abort();
}
std::vector<std::uint8_t> wire(std::string text) {
    return wtp::encode_frame({reinterpret_cast<const std::uint8_t*>(text.data()), text.size()});
}
std::string request(std::string op, std::string body, char id) {
    return "{\"type\":\"request\",\"protocol\":\"WTP/"
           "1\",\"session_id\":\"d2f0af9141101f9a5c0d61e7cdee7983\",\"request_id\":\"" +
           std::string(32, id) + "\",\"op\":\"" + op + "\",\"body\":" + body + "}";
}
std::uint8_t output[131072];
std::size_t output_size = 0;
void send(wtp::Endpoint& endpoint, std::span<const std::uint8_t> bytes, bool keep = false) {
    tracking = true;
    for (std::size_t pos = 0; pos < bytes.size() && !endpoint.closed();) {
        const auto n = endpoint.receive(bytes.subspan(pos), 0);
        if (!n)
            std::abort();
        pos += n;
    }
    while (!endpoint.output().empty()) {
        const auto part =
            endpoint.output().first(std::min<std::size_t>(7, endpoint.output().size()));
        if (keep) {
            if (part.size() > sizeof(output) - output_size)
                std::abort();
            std::copy(part.begin(), part.end(), output + output_size);
            output_size += part.size();
        }
        endpoint.consume_output(part.size(), 0);
    }
    tracking = false;
}
} // namespace
int main(int argc, char** argv) {
    if (argc != 3 && argc != 4)
        return 2;
    background = std::stoull(argv[2]);
    whole = argc == 4 && std::string_view(argv[3]) == "replay";
    if (whole) {
        wtp::allocate_input = tracked_page;
        wtp::deallocate_input = free_page;
    }
    std::ifstream file(argv[1], std::ios::binary);
    std::vector<std::uint8_t> c7((std::istreambuf_iterator<char>(file)), {});
    if (c7.size() != 52105)
        return 3;
    Clock clock;
    Ids ids;
    Sink sink;
    tracking = true;
    CountingEngine engine(sink);
    wtp::JobService service(clock, engine, ids, standalone::wtp_profile(true));
    wtp::Endpoint endpoint(service, std::string(32, 'd'), "host-replay");
    endpoint.connect("host-test");
    tracking = false;
    send(endpoint,
         wire(request(
             "HELLO",
             "{\"versions\":[\"WTP/1\"],\"client_name\":\"replay\",\"client_version\":\"1\"}",
             'a')));
    send(endpoint,
         wire(request("CLAIM",
                      "{\"owner_id\":\"8f65f545870902708dc0e2072114b78e\",\"lease_ms\":60000}",
                      'b')));
    // E6's exact job contents, with a synthetic session/prelude. Retain its
    // inactive terminal response; age its request replay out as before C7.
    auto root = wtp::json::parse(
        std::string_view(reinterpret_cast<const char*>(c7.data() + 16), c7.size() - 16));
    if (!root)
        return 4;
    auto decoded =
        wtp::decode_request(*root, "host-test", std::span<const std::uint8_t>(c7).subspan(16));
    if (!decoded || !decoded->body_valid)
        return 4;
    auto prior = std::get<wtp::Job>(decoded->body);
    prior.job_id = "c339ee30075d458ccc3047bb3d8f8b18";
    prior.total_duration_ns = 3600000000000ULL;
    for (std::size_t i = 0; i < prior.events.size(); ++i) {
        prior.events[i].offset_ns = i * 7031250000ULL;
        prior.events[i].duration_ns = 7031250000ULL;
    }
    wtp::Request q;
    q.session_id = "d2f0af9141101f9a5c0d61e7cdee7983";
    q.request_id = std::string(32, 'c');
    q.principal = "host-test";
    q.operation = "LOAD";
    q.payload_digest.fill(1);
    q.body = std::move(prior);
    tracking = true;
    if (!service.handle(q).ok)
        return 5;
    tracking = false;
    send(endpoint,
         wire(request("ABORT", "{\"job_id\":\"c339ee30075d458ccc3047bb3d8f8b18\"}", '9')));
    tracking = false;
    send(endpoint, wire(request("RELEASE", "{}", 'e')));
    tracking = true;
    clock.now.monotonic_now_ns = 301000000000ULL;
    service.poll();
    tracking = false;
    q = {};
    decoded.reset();
    root.reset();
    send(endpoint,
         wire(request(
             "HELLO",
             "{\"versions\":[\"WTP/1\"],\"client_name\":\"replay\",\"client_version\":\"1\"}",
             'f')));
    // Match C7's seven preceding STATUS requests, with distinct request IDs.
    for (char id = '1'; id <= '7'; ++id)
        send(endpoint, wire(request("STATUS", "{}", id)));
    send(endpoint,
         wire(request("CLAIM",
                      "{\"owner_id\":\"8f65f545870902708dc0e2072114b78e\",\"lease_ms\":60000}",
                      'd')));
    if (endpoint.closed() || service.activity().state != wtp::State::Empty ||
        !service.activity().owned || service.status().terminal_records.size() != 1)
        return 7;
    const auto before = live;
    peak = live;
    modeled_service = &service;
    wtp::available_memory = available;
    if (!whole)
        wtp::allocate_input = page;
    total_peak = live + page_live;
    peak_cpp = live;
    peak_pages = page_live;
    if (whole) {
        // Fixture storage and output reporting are outside measured allocations.
        std::string fresh(reinterpret_cast<const char*>(c7.data() + 16), c7.size() - 16);
        fresh.replace(fresh.find("7082c6ffbb9d466eac3cfc636ba6538a"), 32,
                      "a56745738e684a8094fc0cc3d29bd089");
        auto fresh_wire = wire(fresh);
        std::cout << "{\"exchanges\":[";
        for (unsigned i = 0; i < 3; ++i) {
            output_size = 0;
            total_peak = live + page_live;
            peak_cpp = live;
            peak_pages = page_live;
            calls = 0;
            send(endpoint, i == 2 ? fresh_wire : c7, true);
            if (i)
                std::cout << ',';
            std::cout << "{\"peak_bytes\":" << total_peak << ",\"peak_cpp\":" << peak_cpp
                      << ",\"peak_pages\":" << peak_pages << ",\"after_cpp\":" << live
                      << ",\"after_pages\":" << page_live
                      << ",\"closed\":" << (endpoint.closed() ? "true" : "false") << ",\"hex\":\"";
            for (std::size_t n = 0; n < output_size; ++n)
                std::printf("%02x", output[n]);
            std::cout << "\"}";
        }
        wtp::available_memory = nullptr;
        const auto status = service.status();
        std::cout << "],\"state\":\"" << wtp::state_name(status.state)
                  << "\",\"starts\":" << sink.starts
                  << ",\"terminal_records\":" << status.terminal_records.size()
                  << ",\"preparations\":" << engine.preparations << "}\n";
        return 0;
    }
    send(endpoint, c7, true);
    wtp::available_memory = nullptr;
    wtp::allocate_input = std::malloc;
    const auto after = live;
    const auto status = service.status();
    std::cout << "{\"before\":" << before << ",\"after\":" << after
              << ",\"peak_new_bytes\":" << peak
              << ",\"closed\":" << (endpoint.closed() ? "true" : "false") << ",\"state\":\""
              << wtp::state_name(status.state) << "\",\"starts\":" << sink.starts
              << ",\"samples\":[";
    for (std::size_t i = 0; i < std::min(calls, std::size_t(16)); ++i) {
        if (i)
            std::cout << ',';
        std::cout << "{\"new_bytes\":" << samples[i].live << ",\"pages\":" << samples[i].pages
                  << ",\"available\":" << samples[i].available << '}';
    }
    std::cout << "],\"hex\":\"";
    for (std::size_t i = 0; i < output_size; ++i)
        std::printf("%02x", output[i]);
    std::cout << "\"}\n";
}

#include "wtp/endpoint.hpp"
#include "wtp/inhibited_rf_engine.hpp"
#include "wtp/json_compact.hpp"
#include "wtp/memory_budget.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>

using namespace wsprrypico::wtp;
#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x)) {                                                                                \
            std::cerr << __LINE__ << ": " #x "\n";                                                 \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)
namespace {
// Match the observed normal RF image's idle free heap. Charge every nullable
// input/event/reply allocation; never pretend a buffered maximum frame is free.
constexpr std::size_t heap_budget = 128824;
std::size_t live_bytes = 0, peak_bytes = 0, forced_pressure = 0;
bool pressure_on_page_release = false;
struct Allocation {
    void* data{};
    std::size_t size{};
};
std::array<Allocation, 128> allocations{};
std::size_t available() {
    return heap_budget > live_bytes + forced_pressure ? heap_budget - live_bytes - forced_pressure
                                                      : 0;
}
void* allocate(std::size_t bytes) {
    if (bytes > available())
        return nullptr;
    for (auto& entry : allocations)
        if (!entry.data) {
            auto* data = std::malloc(bytes);
            if (!data)
                return nullptr;
            entry = {data, bytes};
            live_bytes += bytes;
            peak_bytes = std::max(peak_bytes, live_bytes);
            return data;
        }
    return nullptr;
}
void release(void* data) {
    if (!data)
        return;
    for (auto& entry : allocations)
        if (entry.data == data) {
            if (pressure_on_page_release && entry.size == 4096) {
                pressure_on_page_release = false;
                forced_pressure = 60000;
            }
            live_bytes -= entry.size;
            entry = {};
            std::free(data);
            return;
        }
    CHECK(false);
}
struct Clock : wsprrypico::wtp::Clock {
    ClockSnapshot snapshot() const override {
        return {ClockState::Synchronized, 1800000000000000000ULL, 0, 100, 0, LeapState::Normal, {}};
    }
};
struct Identity : IdentitySource {
    std::string new_boot_id() override {
        return std::string(32, 'b');
    }
};
struct Engine : RfEngine {
    InhibitedRfEngine inhibited;
    unsigned prepared = 0;
    std::size_t events = 0;
    PrepareResult prepare(const Job& job) override {
        ++prepared;
        events = job.events.size();
        return inhibited.prepare(job);
    }
    bool begin(const Job& j, std::uint64_t n) override {
        return inhibited.begin(j, n);
    }
    EngineReport poll(std::uint64_t n) override {
        return inhibited.poll(n);
    }
    bool disable(std::uint64_t n) override {
        return inhibited.disable(n);
    }
    bool output_active() const override {
        return false;
    }
};
std::string identifier(unsigned id) {
    auto value = std::to_string(id);
    return std::string(32 - value.size(), '0') + value;
}
std::string request(unsigned id, std::string_view operation, std::string_view body) {
    return "{\"type\":\"request\",\"protocol\":\"WTP/1\",\"session_id\":\"" + std::string(32, 'a') +
           "\",\"request_id\":" + json::quote(identifier(id)) +
           ",\"op\":" + json::quote(operation) + ",\"body\":" + std::string(body) + "}";
}
std::string decimal(std::uint64_t value, bool escaped) {
    if (!escaped)
        return json::quote(std::to_string(value));
    std::string text = "\"";
    for (const auto c : std::to_string(value)) {
        text += "\\u003";
        text += c;
    }
    return text + '"';
}
std::string load(unsigned id, bool escaped) {
    std::string body = "{\"job_id\":" + json::quote(std::string(32, 'c')) +
                       ",\"profile\":\"rf-events/"
                       "1\",\"mode\":\"tone\",\"total_duration_ns\":\"512000000\",\"events\":[";
    for (unsigned i = 0; i < 512; ++i) {
        if (i)
            body += ',';
        body += "{\"offset_ns\":" + decimal(i * 1000000ULL, escaped && i < 90) +
                ",\"duration_ns\":\"1000000\",\"rf_on\":true,\"frequency_nhz\":" +
                decimal(14097100000000000ULL, escaped && i < 90) + "}";
    }
    auto text = request(id, "LOAD", body + "]}");
    CHECK(text.size() <= 65536);
    // Interior and exterior insignificant whitespace exercise both paths.
    text.insert(text.find("\"events\":[") + 10, " \r\n\t ");
    text.resize(65536, ' ');
    return text;
}
struct Peer {
    Clock clock;
    Identity identity;
    Engine engine;
    JobService service{clock, engine, identity};
    Endpoint endpoint{service, std::string(32, 'd'), "capacity-test"};
    Peer() {
        endpoint.connect("usb-physical");
    }
    ~Peer() {
        endpoint.disconnect();
    }
    std::string send(std::string_view text) {
        auto wire = encode_frame(
            std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
        CHECK(!wire.empty());
        for (std::size_t at = 0; at < wire.size();) {
            const auto step = std::min<std::size_t>(64, wire.size() - at);
            const auto count = endpoint.receive(std::span(wire).subspan(at, step), 1);
            if (!count)
                break;
            at += count;
        }
        return drain();
    }
    std::string drain() {
        std::string result;
        while (!endpoint.output().empty()) {
            const auto bytes = endpoint.output();
            result.append(reinterpret_cast<const char*>(bytes.data()), bytes.size());
            endpoint.consume_output(bytes.size(), 1);
        }
        return result;
    }
    bool response_ok(std::string_view wire) {
        for (std::size_t at = 0; at + 16 <= wire.size();) {
            std::size_t count = 0;
            for (unsigned i = 8; i < 12; ++i)
                count = count * 256 + static_cast<unsigned char>(wire[at + i]);
            CHECK(count <= wire.size() - at - 16);
            const auto root = json::parse(wire.substr(at + 16, count));
            CHECK(root);
            if (root->get("type")->string() == "response")
                return root->get("ok")->raw == "true";
            at += 16 + count;
        }
        return false;
    }
    void hello_claim() {
        CHECK(response_ok(send(
            request(1, "HELLO",
                    R"({"versions":["WTP/1"],"client_name":"capacity","client_version":"1"})"))));
        CHECK(response_ok(send(request(2, "CLAIM",
                                       "{\"owner_id\":" + json::quote(std::string(32, 'e')) +
                                           ",\"lease_ms\":60000}"))));
    }
};
void bounded_control_pressure() {
    Peer peer;
    forced_pressure = heap_budget - 60000;
    peer.hello_claim();
    CHECK(peer.response_ok(peer.send(request(3, "PING", "{}"))));
    CHECK(peer.response_ok(peer.send(
        request(4, "RENEW",
                "{\"owner_id\":" + json::quote(std::string(32, 'e')) + ",\"lease_ms\":60000}"))));
    CHECK(!memory_admitted(32768)); // LOAD keeps its workspace and authority reserve.
    const auto small_load = request(
        5, "LOAD",
        "{\"job_id\":" + json::quote(std::string(32, 'c')) +
            R"(,"profile":"rf-events/1","mode":"tone","total_duration_ns":"1000000","events":[{"offset_ns":"0","duration_ns":"1000000","rf_on":true,"frequency_nhz":"14097100000000000"}]})");
    CHECK(peer.send(small_load).empty());
    CHECK(peer.engine.prepared == 0);
    forced_pressure = 0;
    peer.endpoint.poll(2);
    CHECK(peer.response_ok(peer.drain()));
    CHECK(peer.engine.prepared == 1);
    forced_pressure = heap_budget - 60000;
    CHECK(peer.response_ok(
        peer.send(request(6, "ABORT", "{\"job_id\":" + json::quote(std::string(32, 'c')) + "}"))));
    CHECK(peer.response_ok(peer.send(request(7, "RELEASE", "{}"))));
    CHECK(!peer.service.status().owner_id);
    // Large bodies cannot borrow the scalar-control workspace, even when the
    // operation name is one of the bounded controls.
    const auto padded = request(8, "CLAIM", "{\"unexpected\":\"" + std::string(3000, 'x') + "\"}");
    CHECK(peer.send(padded).empty());
    CHECK(!peer.service.status().owner_id);
    forced_pressure = 0;
}

void capacity(bool escaped) {
    Peer peer;
    peer.hello_claim();
    const auto payload = load(3, escaped);
    CHECK(peer.response_ok(peer.send(payload)));
    CHECK(!peer.endpoint.closed() && peer.engine.prepared == 1 && peer.engine.events == 512);
    CHECK(peer.response_ok(peer.send(payload))); // exact original bytes replay.
    CHECK(peer.engine.prepared == 1);
    auto different = payload;
    // Same semantic object, different exact wire identity must remain a conflict.
    different.back() = '\t';
    const auto conflict = peer.send(different);
    CHECK(conflict.find("REQUEST_ID_REUSE") != std::string::npos);
    CHECK(peer.engine.prepared == 1);
}
void deferred_compacted_digest() {
    Peer peer;
    peer.hello_claim();
    const auto payload = load(3, true);
    pressure_on_page_release = true;
    CHECK(peer.send(payload).empty());
    CHECK(!pressure_on_page_release && forced_pressure == 60000);
    CHECK(!peer.endpoint.closed() && peer.engine.prepared == 0);
    CHECK(peer.endpoint.input_reserved_bytes() < 65536);
    forced_pressure = 0;
    peer.endpoint.poll(2);
    CHECK(peer.response_ok(peer.drain()));
    CHECK(peer.engine.prepared == 1 && peer.engine.events == 512);
    // Recovery must use the original pre-compaction bytes for replay identity.
    CHECK(peer.response_ok(peer.send(payload)));
    CHECK(peer.engine.prepared == 1);
    auto changed = payload;
    changed.back() = '\t';
    CHECK(peer.send(changed).find("REQUEST_ID_REUSE") != std::string::npos);
}
void invalid_tokens() {
    Peer peer;
    peer.hello_claim();
    const auto invalid = request(3, "PING", R"({"token":1 2})");
    CHECK(peer.send(invalid).empty() && peer.endpoint.closed());
    CHECK(peer.engine.prepared == 0);
}
void lexical_equivalence() {
    const std::string original =
        R"( { "a\u0062" : "\u0031\u0022\\u0032\/\u000a\u03c0", "n" : 12 } )";
    FrameBuffer bytes;
    CHECK(bytes.reserve(16384));
    bytes.append(
        std::span(reinterpret_cast<const std::uint8_t*>(original.data()), original.size()));
    const auto root = json::parse(bytes.view());
    CHECK(root);
    const auto expected = root->get("ab")->string();
    compact_validated_json(bytes);
    const auto compact = json::parse(bytes.view());
    CHECK(compact);
    CHECK(compact->get("ab")->string() == expected && compact->get("n")->integer() == 12);
    CHECK(bytes.capacity() == 4096);
}
} // namespace
int main() {
    const auto old_allocate = allocate_input;
    const auto old_release = deallocate_input;
    allocate_input = allocate;
    deallocate_input = release;
    available_memory = available;
    {
        bounded_control_pressure();
    }
    CHECK(live_bytes == 0);
    {
        lexical_equivalence();
    }
    CHECK(live_bytes == 0);
    {
        capacity(false);
    }
    CHECK(live_bytes == 0);
    {
        capacity(true);
    }
    CHECK(live_bytes == 0);
    {
        deferred_compacted_digest();
    }
    CHECK(live_bytes == 0);
    {
        invalid_tokens();
    }
    CHECK(live_bytes == 0);
    CHECK(peak_bytes <= heap_budget);
    available_memory = nullptr;
    allocate_input = old_allocate;
    deallocate_input = old_release;
    std::cout << "Padded and escaped 65536-byte/512-event LOADs preserve exact replay at "
                 "128824-byte heap budget\n";
}

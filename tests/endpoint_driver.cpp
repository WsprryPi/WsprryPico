#include "wtp/codec.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/inhibited_rf_engine.hpp"

#include <algorithm>
#include <iostream>

using namespace wsprrypico::wtp;
struct TestClock : Clock {
    ClockSnapshot current{
        ClockState::Unsynchronized, 1'000'000'000'000ULL, 0, 100, 0, LeapState::Normal, {}};
    ClockSnapshot snapshot() const override {
        return current;
    }
};
struct Ids : IdentitySource {
    unsigned boot = 0;
    std::string new_boot_id() override {
        return std::string(31, 'a') + static_cast<char>('0' + boot++);
    }
};
struct TestEngine : RfEngine {
    InhibitedRfEngine inhibited;
    bool fail = false;
    PrepareResult prepare(const Job& job) override {
        return inhibited.prepare(job);
    }
    bool begin(const Job& job, std::uint64_t start) override {
        return inhibited.begin(job, start);
    }
    EngineReport poll(std::uint64_t now) override {
        return fail ? EngineReport{EngineState::Failed, true} : inhibited.poll(now);
    }
    bool disable(std::uint64_t deadline) override {
        return !fail && inhibited.disable(deadline);
    }
    bool output_active() const override {
        return fail;
    }
};
std::vector<std::uint8_t> unhex(std::string_view text) {
    std::vector<std::uint8_t> out;
    auto h = [](char c) { return c <= '9' ? c - '0' : c - 'a' + 10; };
    for (std::size_t i = 0; i + 1 < text.size(); i += 2)
        out.push_back((h(text[i]) << 4) | h(text[i + 1]));
    return out;
}
std::string hex(std::span<const std::uint8_t> data) {
    std::string out;
    constexpr char chars[] = "0123456789abcdef";
    for (auto b : data) {
        out += chars[b >> 4];
        out += chars[b & 15];
    }
    return out;
}
int main() {
    TestClock clock;
    Ids ids;
    TestEngine engine;
    JobService service(clock, engine, ids);
    Endpoint endpoint(service, std::string(32, 'd'), "0.0.0-test");
    std::vector<std::uint8_t> pending;
    std::string line;
    while (std::getline(std::cin, line)) {
        auto control = json::parse(line);
        if (!control)
            return 2;
        auto get = [&](std::string_view key) { return control->get(key).value_or(json::Value{}); };
        auto action = get("action").string();
        auto now = clock.current.monotonic_now_ns / 1'000'000ULL;
        std::vector<std::uint8_t> sent;
        if (action == "connect") {
            endpoint.connect(get("principal").string());
            pending.clear();
        }
        if (action == "disconnect") {
            endpoint.disconnect();
            pending.clear();
        }
        if (action == "fault")
            engine.fail = true;
        if (action == "reset") {
            service.reset();
            pending.clear();
        }
        if (action == "clock") {
            clock.current.state = get("synchronized").boolean() ? ClockState::Synchronized
                                                                : ClockState::Unsynchronized;
            if (auto n = control->get("now_ns")) {
                if (!json::decimal(*n, clock.current.monotonic_now_ns))
                    return 3;
                clock.current.utc_now_ns = 1'000'000'000'000ULL + clock.current.monotonic_now_ns;
            }
            if (auto leap = control->get("leap"))
                clock.current.leap =
                    leap->string() == "unknown" ? LeapState::Unknown : LeapState::Normal;
        }
        now = clock.current.monotonic_now_ns / 1'000'000ULL;
        if (action == "decode") {
            auto bytes = unhex(get("hex").string());
            auto root = json::parse({reinterpret_cast<const char*>(bytes.data()), bytes.size()});
            auto r = root ? decode_request(*root, "usb-physical", bytes) : std::nullopt;
            std::cout << "{\"json\":" << (root ? "true" : "false")
                      << ",\"valid\":" << (r && r->body_valid ? "true" : "false") << "}\n"
                      << std::flush;
            continue;
        }
        if (action == "send") {
            auto bytes = unhex(get("hex").string());
            pending.insert(pending.end(), bytes.begin(), bytes.end());
        }
        if (get("poll").raw != "false")
            endpoint.poll(now);
        const bool drain = get("drain").raw != "false";
        std::size_t budget =
            control->get("limit") ? static_cast<std::size_t>(get("limit").integer()) : 1'000'000;
        for (unsigned i = 0; i < 100000; ++i) {
            bool progress = false;
            if (endpoint.can_receive() && !pending.empty()) {
                auto n = endpoint.receive(pending, now);
                pending.erase(pending.begin(), pending.begin() + n);
                progress = n != 0;
            }
            if (drain && budget && !endpoint.output().empty()) {
                auto bytes = endpoint.output().first(
                    std::min({endpoint.output().size(), budget, std::size_t(3)}));
                sent.insert(sent.end(), bytes.begin(), bytes.end());
                auto n = bytes.size();
                endpoint.consume_output(n, now);
                budget -= n;
                progress = true;
            }
            if (!progress)
                break;
        }
        std::cout << "{\"hex\":\"" << hex(sent)
                  << "\",\"closed\":" << (endpoint.closed() ? "true" : "false")
                  << ",\"pending\":" << pending.size() << "}\n"
                  << std::flush;
    }
}

#include "provisioning/gatt_write_admission.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/inhibited_rf_engine.hpp"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#define CHECK(condition)                                                                           \
    do {                                                                                           \
        if (!(condition)) {                                                                        \
            std::cerr << __LINE__ << ": " #condition "\n";                                         \
            std::exit(1);                                                                          \
        }                                                                                          \
    } while (false)

namespace {
using wsprrypico::provisioning::GattWriteAdmission;
using Result = GattWriteAdmission::Result;
using namespace wsprrypico::wtp;

struct TestClock final : Clock {
    ClockSnapshot snapshot() const override {
        return {ClockState::Unsynchronized, 1'000'000'000'000ULL, 0, 0, 0, LeapState::Normal, {}};
    }
};
struct TestIdentity final : IdentitySource {
    std::string new_boot_id() override {
        return std::string(32, 'a');
    }
};
struct Fixture {
    TestClock clock;
    TestIdentity identity;
    InhibitedRfEngine engine;
    JobService service{clock, engine, identity};
    Endpoint endpoint{service, std::string(32, 'd'), "0.0.0-test"};
    unsigned sequence = 0;
    Fixture() {
        endpoint.connect("usb-physical");
    }
    std::vector<std::uint8_t> request(std::string_view op, std::string_view body = "{}") {
        const auto rid = std::string(31, '0') + std::to_string(++sequence);
        const auto text = "{\"type\":\"request\",\"protocol\":\"WTP/1\",\"session_id\":\"" +
                          std::string(32, '1') + "\",\"request_id\":\"" + rid + "\",\"op\":\"" +
                          std::string(op) + "\",\"body\":" + std::string(body) + "}";
        return encode_frame(
            std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
    }
    void send(std::span<const std::uint8_t> frame) {
        for (std::size_t at = 0; at < frame.size(); at += 64) {
            const auto bytes = frame.subspan(at, std::min<std::size_t>(64, frame.size() - at));
            CHECK(endpoint.can_receive());
            CHECK(endpoint.receive(bytes, 100) == bytes.size());
        }
    }
    std::string confirm_frame() {
        FrameParser parser;
        for (unsigned count = 0; count < 100; ++count) {
            const auto out = endpoint.output();
            CHECK(!out.empty());
            const auto part = out.first(std::min<std::size_t>(64, out.size()));
            auto values = parser.feed(part, 100);
            endpoint.consume_output(part.size(), 100);
            for (auto& value : values) {
                CHECK(value.kind == FrameEventKind::Payload);
                return std::string(value.payload.view());
            }
        }
        CHECK(false);
        return {};
    }
    void load() {
        send(request("HELLO",
                     R"({"versions":["WTP/1"],"client_name":"tests","client_version":"1"})"));
        CHECK(confirm_frame().find("\"ok\":true") != std::string::npos);
        send(
            request("CLAIM", "{\"owner_id\":\"" + std::string(32, '2') + "\",\"lease_ms\":60000}"));
        CHECK(confirm_frame().find("\"ok\":true") != std::string::npos);
        send(request(
            "LOAD",
            "{\"job_id\":\"" + std::string(32, '3') +
                R"(","profile":"rf-events/1","mode":"tone","total_duration_ns":"1000000","events":[{"offset_ns":"0","duration_ns":"1000000","rf_on":true,"frequency_nhz":"14000000000000000"}]})"));
    }
};

void loaded_event_backpressure() {
    Fixture f;
    f.load();
    const auto response = f.confirm_frame();
    CHECK(response.find("\"op\":\"LOAD\"") != std::string::npos);
    CHECK(response.find("\"ok\":true") != std::string::npos);
    CHECK(f.service.status().state == State::Loaded);
    CHECK(!f.endpoint.can_receive()); // Actual trailing JOB_STATE remains.
    const auto status = f.request("STATUS");
    CHECK(f.endpoint.receive(std::span(status).first(64), 100) == 0);
    GattWriteAdmission gate;
    CHECK(gate.admit(100, f.endpoint.can_receive(), true, true) == Result::Deferred);
    CHECK(!gate.resume_due(101, f.endpoint.can_receive(), true));
    CHECK(f.endpoint.input_reserved_bytes() == 0);
    const auto event = f.confirm_frame();
    CHECK(event.find("\"event\":\"JOB_STATE\"") != std::string::npos);
    CHECK(event.find("\"state\":\"loaded\"") != std::string::npos);
    CHECK(f.endpoint.can_receive());
    CHECK(gate.resume_due(200, f.endpoint.can_receive(), true));
    CHECK(!gate.resume_due(200, true, true));
    CHECK(gate.admit(200, f.endpoint.can_receive(), true, true) == Result::Ready);
    CHECK(!gate.pending());
    f.send(status);
    const auto answer = f.confirm_frame();
    CHECK(answer.find("\"op\":\"STATUS\"") != std::string::npos);
    CHECK(answer.find("\"state\":\"loaded\"") != std::string::npos);
    CHECK(f.endpoint.can_receive() && !f.engine.output_active());
}

void deadline_and_reentrancy() {
    GattWriteAdmission gate;
    CHECK(gate.admit(100, false, true, true) == Result::Deferred);
    CHECK(!gate.resume_due(5099, false, true));
    CHECK(gate.resume_due(1000, true, true));
    // The SDK's synchronous callback sees a newly queued event and re-defers.
    CHECK(gate.admit(1000, false, true, true) == Result::Deferred);
    CHECK(!gate.resume_due(5099, false, true));
    CHECK(gate.resume_due(5100, false, true));
    CHECK(gate.admit(5100, true, true, true) == Result::Rejected);
    CHECK(!gate.pending());
    CHECK(gate.admit(100, false, true, true) == Result::Deferred);
    CHECK(gate.resume_due(99, false, true));
    CHECK(gate.admit(99, true, true, true) == Result::Rejected);
}

void revoked_or_closed() {
    for (unsigned boundary = 0; boundary < 3; ++boundary) {
        Fixture f;
        f.load();
        (void)f.confirm_frame();
        GattWriteAdmission gate;
        CHECK(gate.admit(100, false, true, true) == Result::Deferred);
        // Closed endpoint, lost authorization and disabled selected CCCD all
        // revoke the transport's validity predicate before SDK re-entry.
        if (boundary == 0)
            f.endpoint.disconnect();
        CHECK(gate.resume_due(101, false, false));
        CHECK(gate.admit(101, true, false, true) == Result::Rejected);
        CHECK(!gate.pending());
        CHECK(f.service.status().state != State::Armed && !f.engine.output_active());
    }
    GattWriteAdmission gate;
    CHECK(gate.admit(100, false, true, true) == Result::Deferred);
    gate.reset(); // Connection/stop/carrier teardown discards pending admission.
    CHECK(!gate.resume_due(101, true, true));
    CHECK(gate.admit(101, false, true, false) == Result::Rejected);
    CHECK(!gate.pending());
}

void request_identity_and_commands() {
    std::array<std::uint8_t, 67> request{};
    request[0] = 0x12;
    request[1] = 0x12;
    CHECK(GattWriteAdmission::acknowledged_request(request, request.data() + 3, 64, 0x12));
    const auto copied = request;
    CHECK(!GattWriteAdmission::acknowledged_request(request, copied.data() + 3, 64, 0x12));
    CHECK(!GattWriteAdmission::acknowledged_request(request, request.data() + 3, 63, 0x12));
    CHECK(!GattWriteAdmission::acknowledged_request(request, request.data() + 3, 64, 0x13));
    CHECK(!GattWriteAdmission::acknowledged_request({}, nullptr, 0, 0x12));
    request[0] = 0x52;
    CHECK(!GattWriteAdmission::acknowledged_request(request, request.data() + 3, 64, 0x12));
    GattWriteAdmission gate;
    CHECK(gate.admit(100, false, true, false) == Result::Rejected);
    CHECK(!gate.pending());
    CHECK(gate.admit(100, true, true, false) == Result::Ready);
    CHECK(gate.admit(100, false, true, true) == Result::Deferred);
    CHECK(gate.admit(200, true, true, false) == Result::Rejected);
    CHECK(gate.pending());
    CHECK(gate.resume_due(5100, false, true));
    CHECK(gate.admit(5100, true, true, true) == Result::Rejected);
}

void partial_segment_is_never_replayed() {
    Fixture f;
    f.load();
    (void)f.confirm_frame();
    (void)f.confirm_frame();
    auto status = f.request("STATUS");
    // Complete a real request inside a segment that has an extra trailing
    // byte. Endpoint has already dispatched before its output blocks input.
    const auto prefix = status.size() - std::min<std::size_t>(63, status.size());
    f.send(std::span(status).first(prefix));
    std::vector<std::uint8_t> tail(status.begin() + prefix, status.end());
    tail.push_back(0x57);
    const auto consumed = f.endpoint.receive(tail, 100);
    CHECK(consumed + 1 == tail.size());
    GattWriteAdmission gate;
    CHECK(gate.admit(100, true, true, true) == Result::Ready);
    // This is the actual adapter's explicit failure path, not SDK deferral.
    f.endpoint.disconnect();
    gate.reset();
    CHECK(f.endpoint.closed() && !gate.resume_due(101, true, true));
    CHECK(!f.engine.output_active());
}
} // namespace

int main() {
    loaded_event_backpressure();
    deadline_and_reentrancy();
    revoked_or_closed();
    request_identity_and_commands();
    partial_segment_is_never_replayed();
    std::cout << "PASS actual Endpoint loaded-event admission and bounded failure paths\n";
}

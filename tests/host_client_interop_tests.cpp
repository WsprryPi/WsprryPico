#include "host_endpoint_bridge.hpp"
#include "wtp/session.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

using namespace wsprrypi::wtp;
#define CHECK(x)                                                                                   \
    do {                                                                                           \
        if (!(x))                                                                                  \
            throw std::runtime_error(std::string("line ") + std::to_string(__LINE__) + ": " + #x); \
    } while (false)

namespace {
struct Stream : ByteStream {
    std::unique_ptr<HostTestEndpoint> peer = host_test_endpoint();
    bool drop_reply = false;
    void close() noexcept override {
        peer->disconnect();
    }
    IoResult write(std::span<const std::uint8_t> bytes) override {
        if (peer->closed())
            return {IoState::Closed};
        const auto count = peer->receive(bytes);
        return {count ? IoState::Progress : IoState::WouldBlock, count};
    }
    IoResult read(std::span<std::uint8_t> bytes) override {
        if (peer->closed())
            return {IoState::Closed};
        const auto count = peer->read(bytes);
        if (count && drop_reply) {
            drop_reply = false;
            close();
            return {IoState::Closed};
        }
        return {count ? IoState::Progress : IoState::WouldBlock, count};
    }
};
struct Fixture {
    Stream stream;
    Session session{{std::string(32, '1'), std::string(32, '2'), std::string(32, '4')}};
    std::uint64_t now() const {
        return stream.peer->now_ns() / 1'000'000;
    }
    void pump() {
        for (unsigned i = 0; i < 100000; ++i) {
            session.poll(now());
            if (session.phase() == SessionPhase::Ready && !session.busy() &&
                !session.needs_status())
                return;
            if (session.phase() == SessionPhase::Disconnected ||
                session.phase() == SessionPhase::IdentityChanged)
                return;
            if (session.phase() == SessionPhase::Fault)
                throw std::runtime_error(session.diagnostic());
        }
        throw std::runtime_error("in-memory endpoint stalled");
    }
    void connect() {
        stream.peer->connect();
        CHECK(session.connect(stream, now()));
        pump();
    }
    TransactionResult request(Operation op, RequestBody body = Empty{}) {
        CHECK(session.request(op, std::move(body), now()));
        pump();
        auto result = session.take_result();
        CHECK(result);
        return *result;
    }
    void claim() {
        CHECK(request(Operation::Claim, LeaseRequest{std::string(32, '2'), 60000}).kind ==
              ResultKind::Acknowledged);
    }
};
Job job(Mode mode, char id) {
    Job j{std::string(32, id), mode, 0, {}, true};
    auto emit = [&](std::uint64_t duration, std::optional<std::uint64_t> frequency) {
        j.events.push_back({j.total_duration_ns, duration, frequency.has_value(), frequency});
        j.total_duration_ns += duration;
    };
    constexpr std::uint64_t base = 137'500'000'000'000ULL;
    if (mode == Mode::Wspr) {
        // A complete synthetic four-tone frame; this is protocol/lifecycle evidence,
        // not an independent encoder or decoder test.
        for (unsigned i = 0; i < 162; ++i) {
            const auto end = ((i + 1) * 2'048'000'000ULL + 1) / 3;
            emit(end - j.total_duration_ns, base + (i % 4) * 1'464'843'750ULL);
        }
    } else if (mode == Mode::Tone) {
        emit(1'000'000'000, base);
    } else {
        emit(1'000'000'000, {});
        emit(3'000'000'000, base + (mode == Mode::Dfcw ? 5'000'000'000ULL : 0));
        emit(3'000'000'000,
             mode == Mode::Fskcw ? std::optional{base + 5'000'000'000ULL} : std::nullopt);
        emit(3'000'000'000, base);
        emit(1'000'000'000, {});
    }
    return j;
}
void physical_admission() {
    Fixture f;
    f.stream.peer = host_test_endpoint(true);
    f.stream.peer->synchronize();
    f.connect();
    CHECK(f.session.capabilities()->engine == "pio-dma-gp2");
    f.claim();
    Job j{std::string(32, 'a'),
          Mode::Tone,
          5'000'000'001,
          {{0, 5'000'000'000, true, 137'500'000'000'000ULL}, {5'000'000'000, 1, false, {}}},
          true};
    CHECK(f.request(Operation::Load, j).kind == ResultKind::Acknowledged);
    const auto start = f.stream.peer->utc_ns() + 1'000'000'895;
    CHECK(f.request(Operation::Arm, ArmRequest{j.job_id, start, 500'000'000}).kind ==
          ResultKind::Acknowledged);
    CHECK(f.request(Operation::Abort, AbortRequest{j.job_id}).kind == ResultKind::Acknowledged);
    CHECK(f.request(Operation::Release).kind == ResultKind::Acknowledged);
    CHECK(f.stream.peer->inactive());
}

void physical_host_wspr_admission() {
    Fixture f;
    f.stream.peer = host_test_endpoint(true);
    f.stream.peer->synchronize();
    f.connect();
    f.claim();
    auto j = job(Mode::Wspr, 'b');
    // WsprryPi ExecutionPlanCompiler truncates each 8192/12000 s symbol
    // independently to nanoseconds. Exercise that exact client job shape.
    j.total_duration_ns = 162ULL * 682'666'666;
    for (std::size_t i = 0; i < j.events.size(); ++i) {
        j.events[i].offset_ns = i * 682'666'666ULL;
        j.events[i].duration_ns = 682'666'666;
    }
    CHECK(f.request(Operation::Load, j).kind == ResultKind::Acknowledged);
    CHECK(f.request(Operation::Arm,
                    ArmRequest{j.job_id, f.stream.peer->utc_ns() + 1'000'000'123, 500'000'000})
              .kind == ResultKind::Acknowledged);
    CHECK(f.request(Operation::Abort, AbortRequest{j.job_id}).kind == ResultKind::Acknowledged);
    CHECK(f.request(Operation::Release).kind == ResultKind::Acknowledged);
}

void five_modes() {
    Fixture f;
    f.connect();
    CHECK(f.session.phase() == SessionPhase::Ready);
    const auto caps = *f.session.capabilities();
    CHECK(caps.engine == "inhibited-standalone-simulator");
    CHECK(caps.max_events == 162 && caps.max_job_duration_ns == 110'592'000'000ULL);
    CHECK(caps.maximum_arm_uncertainty_ns == 500'000'000);
    CHECK(caps.modes.size() == 5);
    CHECK(std::find(caps.modes.begin(), caps.modes.end(), Mode::Cw) == caps.modes.end());
    char id = 'a';
    for (auto mode : {Mode::Wspr, Mode::Tone, Mode::Qrss, Mode::Fskcw, Mode::Dfcw}) {
        f.stream.peer->synchronize();
        f.claim();
        const auto j = job(mode, id++);
        CHECK(f.request(Operation::Load, j).kind == ResultKind::Acknowledged);
        const auto start = f.stream.peer->utc_ns() + 1'000'000'000;
        auto strict = f.request(Operation::Arm, ArmRequest{j.job_id, start, 1'000'000});
        CHECK(strict.kind == ResultKind::Rejected);
        CHECK(strict.response &&
              std::get<Error>(strict.response->body).code == ErrorCode::ClockUncertain);
        CHECK(f.request(Operation::Arm, ArmRequest{j.job_id, start, 500'000'000}).kind ==
              ResultKind::Acknowledged);
        // Device lifecycle completes without any further host bytes, including
        // across ownership lease expiry for the full WSPR frame.
        const auto launch = f.stream.peer->now_ns() + 1'000'000'000;
        f.session.disconnect();
        f.stream.peer->advance(launch);
        CHECK(f.stream.peer->inactive()); // Always physically inhibited, even while running.
        f.stream.peer->advance(launch + j.total_duration_ns);
        f.connect();
        CHECK(f.session.phase() == SessionPhase::Ready);
        CHECK(f.session.job_evidence() && f.session.job_evidence()->completed());
        if (f.session.owns())
            CHECK(f.request(Operation::Release).kind == ResultKind::Acknowledged);
        CHECK(f.stream.peer->inactive());
    }
}
void recovery() {
    Fixture f;
    f.stream.peer->synchronize();
    f.connect();
    f.claim();
    auto j = job(Mode::Tone, 'c');
    f.stream.drop_reply = true;
    CHECK(f.request(Operation::Load, j).kind == ResultKind::Unknown);
    f.connect();
    CHECK(f.session.uncertain());
    CHECK(f.session.retry_uncertain(f.now()));
    f.pump();
    CHECK(f.session.take_result()->kind == ResultKind::Acknowledged);
    f.stream.drop_reply = true;
    CHECK(f.request(Operation::Arm,
                    ArmRequest{j.job_id, f.stream.peer->utc_ns() + 1'000'000'000, 500'000'000})
              .kind == ResultKind::Unknown);
    f.connect();
    CHECK(!f.session.uncertain());
    CHECK(f.session.job_evidence()->state == State::Armed);
    (void)f.session.take_result();
    f.stream.drop_reply = true;
    CHECK(f.request(Operation::Abort, AbortRequest{j.job_id}).kind == ResultKind::Unknown);
    f.connect();
    CHECK(f.session.job_evidence()->cancelled());
    (void)f.session.take_result();
    CHECK(f.request(Operation::Release).kind == ResultKind::Acknowledged);
    f.claim();
    j.job_id = std::string(32, 'd');
    CHECK(f.request(Operation::Load, j).kind == ResultKind::Acknowledged);
    CHECK(f.request(Operation::Arm,
                    ArmRequest{j.job_id, f.stream.peer->utc_ns() + 1'000'000'000, 500'000'000})
              .kind == ResultKind::Acknowledged);
    f.session.disconnect();
    f.stream.peer->reset();
    f.connect();
    CHECK(f.session.phase() == SessionPhase::IdentityChanged);
    CHECK(!f.session.request(Operation::Load, j, f.now()));
    CHECK(f.stream.peer->inactive());
}
} // namespace
int main() {
    try {
        five_modes();
        physical_admission();
        physical_host_wspr_admission();
        recovery();
        std::cout << "Actual WsprryPi client/current Pico endpoint: five finite modes, SNTP clock "
                     "admission, disconnected completion, lost LOAD/ARM/ABORT recovery and "
                     "boot-change refusal passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

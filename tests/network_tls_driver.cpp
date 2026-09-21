#include "network/pico/psa_lifetime.hpp"
#include "network/pico/server.hpp"
#include "network_credentials.hpp"
#include "network_support.hpp"
#include "pico/time.h"
#include "provisioning/pico/credential_validator.hpp"
#include "rf/worker.hpp"
#include "wtp/memory_budget.hpp"

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <fcntl.h>
#include <thread>
#include <unistd.h>
namespace {
volatile std::sig_atomic_t stopping = 0;
void stop(int) {
    stopping = 1;
}
std::uint64_t now() {
    return time_us_64() * 1000ULL;
}
std::uint64_t clock_now(void*) {
    return now();
}
void wait() {
    std::this_thread::yield();
}
void failure() {
    std::abort();
}
// A hardware-free locally scheduled timeline: elapsed time advances the finite
// device job independently of the application thread. No host wakeup-latency
// assertion is treated as a physical alarm deadline. Driver deadline tests live
// in pio_dma_tests; target measurements remain separately required.
class LocalTimerEngine final : public wsprrypico::wtp::RfEngine {
    using State = wsprrypico::wtp::EngineState;
    State state_ = State::Idle;
    std::uint64_t start_ = 0, duration_ = 0;
    wsprrypico::wtp::LocalStartConditions conditions_;

  public:
    wsprrypico::wtp::PrepareResult prepare(const wsprrypico::wtp::Job&) override {
        return {true, {}};
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const wsprrypico::wtp::Job& job, std::uint64_t start,
                  const wsprrypico::wtp::LocalStartConditions& conditions) override {
        if (state_ != State::Idle)
            return false;
        conditions_ = conditions;
        start_ = start;
        duration_ = job.total_duration_ns;
        state_ = State::Armed;
        return true;
    }
    bool begin(const wsprrypico::wtp::Job&, std::uint64_t) override {
        return false;
    }
    wsprrypico::wtp::EngineReport poll(std::uint64_t time) override {
        if (state_ == State::Armed && time >= start_) {
            state_ =
                conditions_.clock->snapshot().state == wsprrypico::wtp::ClockState::Unsynchronized
                    ? State::Missed
                    : State::Running;
        }
        if (state_ == State::Running && time - start_ >= duration_)
            state_ = State::Complete;
        return {state_, output_active()};
    }
    bool disable(std::uint64_t) override {
        state_ = State::Idle;
        return true;
    }
    bool output_active() const override {
        return state_ == State::Running;
    }
};
std::uint32_t mask() {
    return 0;
}
void restore(std::uint32_t) {}
} // namespace
int main(int argc, char** argv) {
    using namespace wsprrypico;
    std::signal(SIGPIPE, SIG_IGN);
    std::signal(SIGTERM, stop);
    const auto* selected_address = std::getenv("WSPRRY_TEST_LISTEN_ADDRESS");
    const std::string address = selected_address ? selected_address : "127.0.0.1";
    const std::string device(32, argc > 2 ? argv[2][0] : 'a');
    network_test::Flash flash;
    standalone::Store store(flash);
    if (!store.load())
        return 1;
    time::DisciplineConfig discipline;
    discipline.synchronized_for_ns = discipline.holdover_for_ns = 600'000'000'000ULL;
    discipline.oscillator_drift_ppb = 0; // Host fixture has one exact injected clock mapping.
    time::UtcDiscipline clock(clock_now, nullptr, discipline);
    const auto utc =
        static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                       std::chrono::system_clock::now().time_since_epoch())
                                       .count());
    if (!clock.observe(utc, now(), 1000, wtp::LeapState::Normal))
        return 1;
    LocalTimerEngine simulated_physical;
    rf::WorkerEngine engine(simulated_physical, clock, now, wait, failure, mask, restore);
    std::atomic<bool> finished{false};
    std::thread worker([&] {
        while (!finished.load())
            engine.step();
    });
    network_test::Identity identities(argc > 1 ? std::stoul(argv[1]) : 0);
    wtp::JobService service(clock, engine, identities, network_test::Fixture::physical_policy());
    standalone::Scheduler scheduler(store, service);
    network_test::Network network;
    network::BrowserApi api(service, store, scheduler, network, device, "test-worker-firmware");
    unsigned restarts = 0;
    api.restart_control(
        [](void* context) {
            ++*static_cast<unsigned*>(context);
            return true;
        },
        &restarts);
    api.set_active_job_connections(true); // Same explicit policy as physical standalone image.
    const provisioning::CredentialMaterial credentials{
        network::credentials::device_id, network::credentials::hostname,
        network::credentials::port,      network::credentials::certificate,
        network::credentials::key,       network::credentials::ca};
    auto invalid_credentials = credentials;
    invalid_credentials.server_certificate = "not a certificate";
    network::PicoServer invalid_server(service, api, device, "invalid-credentials",
                                       invalid_credentials);
    if (invalid_server.start() || network::PsaCryptoOwner::owners())
        std::abort();
    network::PicoServer server(service, api, device, "test-worker-firmware", credentials);
    if (!server.start() || network::PsaCryptoOwner::owners() != 1 ||
        network::PsaCryptoOwner::peak_owners() < 2) {
        std::cerr << "TLS start error " << server.last_error() << "\n";
        finished = true;
        worker.join();
        return 1;
    }
    {
        network::PicoServer competing(service, api, device, "duplicate", credentials);
        if (competing.start() || network::PsaCryptoOwner::owners() != 1)
            std::abort();
    }
    server.stop();
    if (network::PsaCryptoOwner::owners())
        std::abort();
    {
        network::PicoServer destructor_server(service, api, device, "destructor", credentials);
        if (!destructor_server.start() || network::PsaCryptoOwner::owners() != 1)
            std::abort();
    }
    if (network::PsaCryptoOwner::owners() || server.tls_allocated())
        std::abort();
    wtp::available_memory = []() -> std::size_t { return 0; };
    if (server.start())
        std::abort();
    server.stop();
    if (network::PsaCryptoOwner::owners())
        std::abort();
    wtp::available_memory = nullptr;
    if (server.tls_allocated() || !server.start() || network::PsaCryptoOwner::owners() != 1)
        std::abort();
    fcntl(STDIN_FILENO, F_SETFL, fcntl(STDIN_FILENO, F_GETFL) | O_NONBLOCK);
    bool link = true;
    bool allow_http_steps = true;
    std::string commands;
    std::cout << "READY " << server.port() << " PSA " << network::PsaCryptoOwner::owners()
              << " PEAK " << network::PsaCryptoOwner::peak_owners() << std::endl;
    while (!stopping) {
        char bytes[128];
        const auto count = read(STDIN_FILENO, bytes, sizeof(bytes));
        if (count > 0)
            commands.append(bytes, static_cast<std::size_t>(count));
        while (commands.find('\n') != commands.npos) {
            const auto end = commands.find('\n');
            const auto command = commands.substr(0, end);
            commands.erase(0, end + 1);
            if (command == "RESTART COUNT")
                std::cout << "RESTARTS " << restarts << std::endl;
            else if (command == "CLOSE METRICS")
                std::cout << "CLOSE " << server.metrics().last_wtp_close_reason << ' '
                          << server.metrics().last_wtp_tls_result << std::endl;
            else if (command == "PSA STATUS")
                std::cout << "PSA " << network::PsaCryptoOwner::owners() << ' '
                          << network::PsaCryptoOwner::peak_owners() << std::endl;
            else if (command == "VALIDATE GOOD" || command == "VALIDATE BAD") {
                provisioning::MbedTlsCredentialValidator validator(device);
                const auto valid = validator.validate(
                    command == "VALIDATE GOOD" ? credentials : invalid_credentials);
                std::cout << "VALIDATE " << (valid ? 1 : 0) << ' ' << validator.last_error() << ' '
                          << network::PsaCryptoOwner::owners() << ' '
                          << network::PsaCryptoOwner::peak_owners() << std::endl;
            } else if (command == "SERVER CYCLE") {
                server.stop();
                const bool released = !network::PsaCryptoOwner::owners() && !server.tls_allocated();
                const bool started = released && server.start();
                std::cout << "CYCLE " << (started ? 1 : 0) << ' '
                          << network::PsaCryptoOwner::owners() << ' ' << server.tls_allocated()
                          << std::endl;
            } else if (command == "CLOCK OFF")
                clock.invalidate();
            else if (command == "CLOCK ON")
                (void)clock.observe(utc + now(), now(), 1000, wtp::LeapState::Normal);
            else if (command == "LINK OFF")
                link = false;
            else if (command == "LINK ON")
                link = true;
            else if (command == "HANDSHAKE PAUSE")
                allow_http_steps = false;
            else if (command == "HANDSHAKE RESUME")
                allow_http_steps = true;
            else if (command == "HTTP PAUSE")
                allow_http_steps = false;
            else if (command == "HTTP RESUME")
                allow_http_steps = true;
            else if (command == "WRITE FRAGMENT")
                mock_tcp_fragment_writes(true);
            else if (command == "WRITE NORMAL")
                mock_tcp_fragment_writes(false);
            else if (command == "ACK HOLD NEXT")
                mock_tcp_hold_next_ack();
            else if (command == "ACK HOLD")
                mock_tcp_hold_last_ack();
            else if (command == "ACK RELEASE")
                mock_tcp_release_acks();
            else if (command == "ACK FIN")
                mock_tcp_ack_and_close(false);
            else if (command == "ACK RESET")
                mock_tcp_ack_and_close(true);
        }
        mock_tcp_poll();
        server.poll(link && network.enabled, address + ":" + std::to_string(server.port()),
                    allow_http_steps);
        std::this_thread::sleep_for(std::chrono::microseconds(100));
    }
    server.stop();
    const auto retained_psa_owners = network::PsaCryptoOwner::owners();
    // Test-process teardown explicitly disables before joining the worker. TCP
    // disconnects above do not issue this physical-console-equivalent operation.
    (void)service.local_abort();
    const auto metrics = engine.metrics();
    finished = true;
    worker.join();
    std::cerr << "TLS peak=" << server.tls_peak() << " retained=" << server.tls_allocated()
              << " allocation_failures=" << server.tls_failures()
              << " psa_owners=" << retained_psa_owners
              << " psa_peak=" << network::PsaCryptoOwner::peak_owners()
              << " worker_commands=" << metrics.commands << "\n";
    return server.tls_allocated() || retained_psa_owners ? 2 : 0;
}

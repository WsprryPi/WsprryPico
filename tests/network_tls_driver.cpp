#include "mbedtls/platform.h"
#include "network/pico/psa_lifetime.hpp"
#include "network/pico/server.hpp"
#include "network_credentials.hpp"
#include "network_support.hpp"
#include "pico/time.h"
#include "provisioning/pico/credential_validator.hpp"
#include "rf/observation.hpp"
#include "rf/worker.hpp"
#include "runtime/json.hpp"
#include "runtime/memory_budget.hpp"

#include <atomic>
#include <charconv>
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
mbedtls_time_t unset_tls_time(mbedtls_time_t* output) {
    if (output)
        *output = 0;
    return 0;
}
// A hardware-free locally scheduled timeline: elapsed time advances the finite
// device job independently of the application thread. No host wakeup-latency
// assertion is treated as a physical alarm deadline. Driver deadline tests live
// in pio_dma_tests; target measurements remain separately required.
class LocalTimerEngine final : public wsprrypico::execution::RfEngine {
    using State = wsprrypico::execution::EngineState;
    State state_ = State::Idle;
    std::uint64_t start_ = 0, duration_ = 0, epoch_ = 0;
    wsprrypico::execution::PadObservation pad_;
    wsprrypico::execution::LocalStartConditions conditions_;
    const bool assess_tone_;

  public:
    explicit LocalTimerEngine(bool assess_tone) : assess_tone_(assess_tone) {}
    wsprrypico::execution::PadObservation pad_observation() const override {
        return pad_;
    }
    wsprrypico::execution::PrepareResult prepare(const wsprrypico::execution::Job& job) override {
        if (assess_tone_ && job.mode == "tone" && job.events.size() == 1) {
            const auto frequency = *job.events[0].frequency_nhz;
            const auto increment = wsprrypico::rf::frequency_increment(frequency);
            if (!increment)
                return {};
            return {true, {{0, frequency, wsprrypico::rf::realized_nhz(*increment)}}};
        }
        return {true, {}};
    }
    bool schedules_locally() const override {
        return true;
    }
    bool schedule(const wsprrypico::execution::Job& job, std::uint64_t start,
                  const wsprrypico::execution::LocalStartConditions& conditions) override {
        if (state_ != State::Idle)
            return false;
        pad_ = {++epoch_, now(), 2, 12};
        conditions_ = conditions;
        start_ = start;
        duration_ = job.total_duration_ns;
        state_ = State::Armed;
        return true;
    }
    bool begin(const wsprrypico::execution::Job&, std::uint64_t) override {
        return false;
    }
    wsprrypico::execution::EngineReport poll(std::uint64_t time) override {
        if (state_ == State::Armed && time >= start_) {
            state_ =
                conditions_.clock->snapshot().state == wsprrypico::execution::ClockState::Unsynchronized
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
    if(argc>3){std::cerr<<"Unrecognized fixture arguments\n";return 2;}
    std::signal(SIGPIPE, SIG_IGN);
    std::signal(SIGTERM, stop);
    const auto* selected_address = std::getenv("WSPRRY_TEST_LISTEN_ADDRESS");
    const std::string address = selected_address ? selected_address : "127.0.0.1";
    const std::string device(32, argc > 2 ? argv[2][0] : 'a');
    const auto* manual_clock = std::getenv("WSPRRY_NETWORK_TEST_MANUAL_CLOCK");
    if (manual_clock) {
        if (std::string_view(manual_clock) != "1")
            return 2;
        mock_tcp_enable_manual_time();
    }
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
    if (!clock.observe(utc, now(), 1000, execution::LeapState::Normal))
        return 1;
    const bool tone_fixture = std::getenv("WSPRRY_NETWORK_TEST_TONE") &&
                              std::string_view(std::getenv("WSPRRY_NETWORK_TEST_TONE")) == "1";
    LocalTimerEngine simulated_physical(tone_fixture);
    rf::WorkerEngine engine(simulated_physical, clock, now, wait, failure, mask, restore);
    std::atomic<bool> finished{false};
    std::thread worker([&] {
        while (!finished.load())
            engine.step();
    });
    network_test::Identity identities(argc > 1 ? std::stoul(argv[1]) : 0);
    std::optional<standalone::FrequencyPolicyEngine> tone_policy;
    auto service_limits = network_test::Fixture::physical_policy();
    if (tone_fixture) {
        service_limits.capability_engine = "pio-dma-gp2";
        tone_policy.emplace(engine, store, rf::minimum_frequency_nhz, rf::maximum_frequency_nhz);
    }
    execution::JobService service(clock, tone_policy ? static_cast<execution::RfEngine&>(*tone_policy) : engine,
                            identities, service_limits);
    standalone::Scheduler scheduler(store, service);
    network_test::Network network;
    network::BrowserApi api(service, store, scheduler, network, device, "test-worker-firmware");
    if (tone_policy)
        api.test_tone_policy(*tone_policy);
    network_test::Flash udp_flash;
    logging::UdpStore udp_store(udp_flash);
    if (!udp_store.load())
        return 2;
    logging::UdpSender udp_sender(device, service.status().boot_id, "pico.local");
    api.udp_logging_service(udp_store, udp_sender);
    logging::Logger udp_logger(device, service.status().boot_id, "pico.local");
    udp_logger.udp_sink(udp_sender);
    api.logging_service(udp_logger);
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
    // First provisioning validates before any TLS server has started. Its
    // certificate clock must already be the disciplined device clock.
    mbedtls_platform_set_time(unset_tls_time);
    provisioning::MbedTlsCredentialValidator unbound_validator(device);
    if (unbound_validator.validate(credentials) || network::PsaCryptoOwner::owners())
        std::abort();
    network::install_tls_time_source(service);
    provisioning::MbedTlsCredentialValidator startup_validator(device, &service);
    if (!startup_validator.validate(credentials) || network::PsaCryptoOwner::owners())
        std::abort();
    clock.invalidate();
    if (startup_validator.validate(credentials) || network::PsaCryptoOwner::owners())
        std::abort();
    if (!clock.observe(utc + now(), now(), 1000, execution::LeapState::Normal) ||
        !startup_validator.validate(credentials) || network::PsaCryptoOwner::owners())
        std::abort();
    auto invalid_credentials = credentials;
    invalid_credentials.server_certificate = "not a certificate";
    network::PicoServer invalid_server(service, api, device, invalid_credentials);
    if (invalid_server.start() || network::PsaCryptoOwner::owners())
        std::abort();
    bool softap_interface = std::getenv("WSPRRY_TEST_SOFTAP_INTERFACE") != nullptr;
    auto classify_softap = [](const tcp_pcb*, void* context) {
        return *static_cast<bool*>(context);
    };
    network::PicoServer server(service,api,device,credentials);
    server.softap_handler(nullptr, classify_softap, &softap_interface);
    if(!server.start()||network::PsaCryptoOwner::owners()!=1||network::PsaCryptoOwner::peak_owners()<2){
        std::cerr<<"TLS start error "<<server.last_error()<<'\n';finished=true;worker.join();return 1;
    }
    {
        network::PicoServer competing(service, api, device, credentials);
        if (competing.start() || network::PsaCryptoOwner::owners() != 1)
            std::abort();
    }
    server.stop();
    if (network::PsaCryptoOwner::owners())
        std::abort();
    {
        network::PicoServer destructor_server(service, api, device, credentials);
        if (!destructor_server.start() || network::PsaCryptoOwner::owners() != 1)
            std::abort();
    }
    if (network::PsaCryptoOwner::owners() || server.tls_allocated())
        std::abort();
    execution::available_memory = []() -> std::size_t { return 0; };
    if (server.start())
        std::abort();
    server.stop();
    if (network::PsaCryptoOwner::owners())
        std::abort();
    execution::available_memory = nullptr;
    if (server.tls_allocated() || !server.start() || network::PsaCryptoOwner::owners() != 1)
        std::abort();
    fcntl(STDIN_FILENO, F_SETFL, fcntl(STDIN_FILENO, F_GETFL) | O_NONBLOCK);
    bool link = true;
    bool allow_http_steps = true;
    std::string commands;
    std::uint64_t sync_sequence = 0;
    bool discarding_command = false;
    std::cout << "READY " << server.port() << " PSA " << network::PsaCryptoOwner::owners()
              << " PEAK " << network::PsaCryptoOwner::peak_owners()
              << std::endl;
    while (!stopping) {
        char bytes[128];
        const auto count = read(STDIN_FILENO, bytes, sizeof(bytes));
        if (count > 0) {
            auto input = std::string_view(bytes, static_cast<std::size_t>(count));
            if (discarding_command) {
                const auto newline = input.find('\n');
                if (newline == input.npos)
                    input = {};
                else {
                    input.remove_prefix(newline + 1);
                    discarding_command = false;
                }
            }
            commands.append(input);
        }
        while (commands.find('\n') != commands.npos) {
            const auto end = commands.find('\n');
            const auto command = commands.substr(0, end);
            commands.erase(0, end + 1);
            if (command.size() > 256) {
                std::cout << "CONTROL ERROR OVERSIZED" << std::endl;
                continue;
            }
            if (command.starts_with("SYNC ")) {
                std::uint64_t sequence = 0;
                const auto value = std::string_view(command).substr(5);
                const auto parsed =
                    std::from_chars(value.data(), value.data() + value.size(), sequence);
                if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size() ||
                    std::to_string(sequence) != value || sequence == 0 ||
                    sync_sequence == UINT64_MAX || sequence != sync_sequence + 1) {
                    std::cout << "CONTROL ERROR SYNC" << std::endl;
                    continue;
                }
                mock_tcp_poll();
                server.poll(link && network.enabled, address + ":" + std::to_string(server.port()),
                            allow_http_steps);
                sync_sequence = sequence;
                std::cout << "SYNC " << sequence << std::endl;
            } else if (command.starts_with("TIME ADVANCE ")) {
                std::uint64_t amount = 0;
                const auto value = std::string_view(command).substr(13);
                const auto parsed =
                    std::from_chars(value.data(), value.data() + value.size(), amount);
                if (!manual_clock || parsed.ec != std::errc{} ||
                    parsed.ptr != value.data() + value.size() || std::to_string(amount) != value ||
                    !mock_tcp_advance_time_us(amount))
                    std::cout << "CONTROL ERROR TIME" << std::endl;
                else
                    std::cout << "TIME " << time_us_64() << std::endl;
            } else if (command == "STATE") {
                mock_tcp_poll();
                server.poll(link && network.enabled, address + ":" + std::to_string(server.port()),
                            allow_http_steps);
                const auto resources = server.resources();
                std::cout << "STATE " << resources.active_connections << ' '
                          << resources.pending_connections << ' ' << resources.buffered_rx_bytes
                          << ' ' << resources.pending_tcp_bytes << ' ' << server.metrics().timeouts
                          << ' ' << server.metrics().admitted << ' ' << server.metrics().closed
                          << ' ' << allow_http_steps << ' ' << time_us_64() << ' '
                          << execution::state_name(service.status().state) << std::endl;
            } else if (command == "BARRIER") {
                // SYNC observes the following normal foreground iteration.
            } else if (command == "RESTART COUNT")
                std::cout << "RESTARTS " << restarts << std::endl;
            else if (command == "NAGLE HOLD") {
                mock_tcp_hold_next_handshake_ack();
                std::cout << "NAGLE HOLD READY" << std::endl;
            } else if (command == "PENDING BURST FIN" || command == "PENDING BURST RESET") {
                const auto allocated = server.tls_allocated();
                unsigned refused = 0;
                auto* pcb = mock_tcp_pending_burst(refused);
                const auto staged = server.resources();
                mock_tcp_pending_disconnect(pcb, command == "PENDING BURST RESET");
                const auto closed = server.resources();
                std::cout << "PENDING " << staged.buffered_rx_bytes << ' '
                          << staged.pending_connections << ' ' << refused << ' '
                          << closed.buffered_rx_bytes << ' ' << closed.pending_connections << ' '
                          << (allocated == server.tls_allocated()) << std::endl;
            } else if(command.starts_with("NATIVE ")) {
                const auto op=command.substr(7);const std::string session(32,'d'),job_id(32,'e');
                const auto invoke=[&](std::string operation,execution::RequestBody body={}){
                    return network_test::internal_command(service,std::move(operation),std::move(body),"native-fixture",session).ok;
                };
                bool ok=false;
                if(op=="CLAIM")ok=invoke("HELLO",execution::HelloBody{{"native-execution/1"}})&&invoke("CLAIM",execution::ClaimBody{session,60000});
                else if(op=="LOAD"){
                    execution::Job job;job.job_id=job_id;job.mode="tone";job.total_duration_ns=1'000'000'000;
                    job.events.push_back({0,job.total_duration_ns,true,3'570'100'000'000'000});
                    ok=invoke("LOAD",std::move(job));
                }else if(op=="ARM")ok=invoke("ARM",execution::ArmBody{job_id,clock.snapshot().utc_now_ns+2'000'000'000,1000000});
                else if(op=="ABORT")ok=invoke("ABORT",execution::AbortBody{job_id});
                else if(op=="RELEASE")ok=invoke("RELEASE");
                std::cout<<"NATIVE "<<op<<' '<<ok<<std::endl;
            }
            else if (command == "PSA STATUS")
                std::cout << "PSA " << network::PsaCryptoOwner::owners() << ' '
                          << network::PsaCryptoOwner::peak_owners() << std::endl;
            else if (command == "NETWORK STATUS" || command == "NETWORK DRAIN") {
                if (command == "NETWORK DRAIN") {
                    // Test boundary: observe the real loopback reset with the
                    // normal foreground sequence before asserting slot reuse.
                    mock_tcp_poll();
                    server.poll(link && network.enabled,
                                address + ":" + std::to_string(server.port()), allow_http_steps);
                }
                const auto resources = server.resources();
                std::cout << "NETWORK " << resources.active_connections << ' '
                          << resources.pending_connections << ' ' << resources.buffered_rx_bytes
                          << std::endl;
            } else if (command == "VALIDATE GOOD" || command == "VALIDATE BAD") {
                provisioning::MbedTlsCredentialValidator validator(device, &service);
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
                (void)clock.observe(utc + now(), now(), 1000, execution::LeapState::Normal);
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
            else
                std::cout << "CONTROL ERROR UNKNOWN" << std::endl;
        }
        if (commands.size() > 256) {
            commands.clear();
            discarding_command = true;
            std::cout << "CONTROL ERROR OVERSIZED" << std::endl;
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

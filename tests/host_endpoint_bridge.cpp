#include "host_endpoint_bridge.hpp"

#include "rf/pio_dma_sink.hpp"
#include "standalone/dry_run_engine.hpp"
#include "standalone/wtp_profile.hpp"
#include "wtp/endpoint.hpp"

#include <algorithm>
#include <array>
#include <stdexcept>

namespace {
using namespace wsprrypico;
struct Identity : wtp::IdentitySource {
    unsigned boot = 0;
    std::string new_boot_id() override {
        return std::string(32, ++boot == 1 ? '5' : '6');
    }
};
// Admission-only fake adapter: real waveform planning and sink validation, no
// hardware and no launch execution. Physical launch is covered separately.
struct AdmissionHardware : rf::PioDmaHardware {
    std::uint64_t& now;
    explicit AdmissionHardware(std::uint64_t& clock) : now(clock) {}
    std::uint32_t lock() override {
        return 0;
    }
    void unlock(std::uint32_t) override {}
    bool open(Handler, void*) override {
        return true;
    }
    bool halt(std::uint64_t) override {
        return true;
    }
    bool dma(const std::uint32_t*, std::uint32_t, bool, std::uint64_t, std::uint64_t) override {
        return true;
    }
    bool alarm(std::uint64_t start, std::uint64_t) override {
        return start % 1000 == 0;
    }
    bool launch(std::uint64_t) override {
        return false;
    }
    std::uint64_t now_ns() const override {
        return now;
    }
    bool stalled() const override {
        return false;
    }
    bool active() const override {
        return false;
    }
};
class Peer final : public HostTestEndpoint {
    std::uint64_t mono_ = 0;
    static std::uint64_t tick(void* p) {
        return static_cast<Peer*>(p)->mono_;
    }
    time::UtcDiscipline clock_{tick, this, standalone::clock_profile()};
    time::Sntp source_{clock_};
    Identity ids_;
    standalone::DryRunEngine engine_;
    AdmissionHardware hardware_{mono_};
    rf::PioDmaSink sink_{hardware_};
    rf::StreamEngine physical_engine_{sink_};
    wtp::JobService service_;
    wtp::Endpoint endpoint_{service_, std::string(32, '4'), "phase10-software-test"};

  public:
    explicit Peer(bool physical)
        : service_(clock_, physical ? static_cast<wtp::RfEngine&>(physical_engine_) : engine_, ids_,
                   standalone::wtp_profile(physical)) {}
    void connect() override {
        endpoint_.connect("usb-physical");
    }
    void disconnect() override {
        endpoint_.disconnect();
    }
    void advance(std::uint64_t ns) override {
        if (ns < mono_)
            throw std::runtime_error("Regressing test clock");
        mono_ = ns;
        endpoint_.poll(mono_ / 1'000'000);
    }
    void synchronize() override {
        // Inject an actual correlated SNTP reply with a 2 ms network round trip.
        // No network, Console time command or direct clock validity override.
        constexpr std::uint64_t nonce = 123;
        (void)source_.request(mono_, nonce);
        std::array<std::uint8_t, 48> reply{};
        reply[0] = 0x24;
        reply[1] = 1;
        reply[3] = 0xec;
        auto put = [&](std::size_t offset, unsigned count, std::uint64_t value) {
            for (unsigned i = 0; i < count; ++i)
                reply[offset + count - 1 - i] = static_cast<std::uint8_t>(value >> (8 * i));
        };
        put(24, 8, nonce);
        const auto seconds = 1'800'000'000ULL + mono_ / 1'000'000'000;
        for (auto offset : {16, 32, 40})
            put(offset, 4, seconds + 2'208'988'800ULL);
        mono_ += 2'000'000;
        if (!source_.receive(reply, mono_))
            throw std::runtime_error("SNTP fixture rejected");
    }
    void invalidate_clock() override {
        clock_.invalidate();
    }
    void reset() override {
        endpoint_.disconnect();
        clock_.invalidate();
        service_.reset();
    }
    std::uint64_t now_ns() const override {
        return mono_;
    }
    std::uint64_t utc_ns() const override {
        return clock_.snapshot().utc_now_ns;
    }
    bool inactive() const override {
        return !service_.status().output_active;
    }
    bool closed() const override {
        return endpoint_.closed();
    }
    std::size_t receive(std::span<const std::uint8_t> bytes) override {
        return endpoint_.receive(bytes.first(std::min(bytes.size(), std::size_t{11})),
                                 mono_ / 1'000'000);
    }
    std::size_t read(std::span<std::uint8_t> bytes) override {
        auto pending = endpoint_.output();
        auto count = std::min({bytes.size(), pending.size(), std::size_t{7}});
        std::copy_n(pending.begin(), count, bytes.begin());
        endpoint_.consume_output(count, mono_ / 1'000'000);
        return count;
    }
};
} // namespace
std::unique_ptr<HostTestEndpoint> host_test_endpoint(bool physical_planner) {
    return std::make_unique<Peer>(physical_planner);
}

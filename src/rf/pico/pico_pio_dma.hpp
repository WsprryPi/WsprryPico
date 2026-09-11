#pragma once
#include "hardware/pio.h"
#include "rf/pio_dma_sink.hpp"
#include "rf/refill_metrics.hpp"

namespace wsprrypico::rf {

// Dedicated instance on one core. Constructing it does not access peripherals.
// halt() before release()/destruction; a failed halt retains resource ownership.
struct PicoDriverMetrics {
    std::uint64_t dma_irqs = 0, max_irq_ns = 0, launch_ns = 0;
    std::uint64_t launch_epoch = 0, launch_target_ns = 0;
    std::uint64_t alarm_irqs = 0, max_alarm_irq_ns = 0, tail_irqs = 0, dma_errors = 0;
    RefillMetrics::Snapshot refill;
};

class PicoPioDma final : public PioDmaHardware {
  public:
    static constexpr unsigned rf_pin = 2;
    PicoPioDma() = default;
    PicoPioDma(const PicoPioDma&) = delete;
    PicoPioDma& operator=(const PicoPioDma&) = delete;
    std::uint32_t lock() override;
    void unlock(std::uint32_t saved) override;
    bool open(Handler handler, void* context) override;
    bool halt(std::uint64_t deadline_ns) override;
    bool release(std::uint64_t deadline_ns);
    bool dma(const std::uint32_t* data, std::uint32_t words, bool increment, std::uint64_t epoch,
             std::uint64_t sequence) override;
    bool alarm(std::uint64_t start_ns, std::uint64_t epoch) override;
    bool launch(std::uint64_t start_ns) override;
    std::uint64_t now_ns() const override;
    PicoDriverMetrics metrics();
    bool stalled() const override;
    bool active() const override;

  private:
    static void dma_irq();
    static void alarm_irq(unsigned alarm);
    static PicoPioDma* instance_;
    PIO pio_ = nullptr;
    unsigned sm_ = 0, offset_ = 0;
    struct Channel {
        int id = -1;
        bool occupied = false;
        bool tail = false;
        std::uint32_t words = 0;
        std::uint64_t epoch = 0, sequence = 0;
    };
    std::array<Channel, 2> channels_{};
    int alarm_ = -1, stop_channel_ = -1;
    std::uint32_t stop_mask_ = 0;
    Handler handler_ = nullptr;
    void* context_ = nullptr;
    std::uint64_t alarm_epoch_ = 0;
    unsigned core_ = 0;
    bool installed_ = false;
    bool launched_ = false;
    RefillMetrics refill_metrics_;
    PicoDriverMetrics metrics_{};
};

} // namespace wsprrypico::rf

#pragma once
#include "hardware/pio.h"
#include "rf/pio_dma_sink.hpp"

namespace wsprrypico::rf {

// Dedicated instance on one core. Constructing it does not access peripherals.
// halt() before release()/destruction; a failed halt retains resource ownership.
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
    bool stalled() const override;
    bool active() const override;

  private:
    static void dma_irq();
    static void alarm_irq(unsigned alarm);
    static PicoPioDma* instance_;
    PIO pio_ = nullptr;
    unsigned sm_ = 0, offset_ = 0;
    int channel_ = -1, alarm_ = -1;
    Handler handler_ = nullptr;
    void* context_ = nullptr;
    std::uint64_t dma_epoch_ = 0, dma_sequence_ = 0, alarm_epoch_ = 0;
    unsigned core_ = 0;
    bool installed_ = false;
};

} // namespace wsprrypico::rf

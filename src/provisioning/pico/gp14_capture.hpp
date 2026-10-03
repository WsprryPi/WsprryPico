#pragma once

#include "hardware/pio.h"
#include "provisioning/button_sample_stream.hpp"
#include "provisioning/pico/rp2350_dma_progress.hpp"

#include <array>
#include <cstdint>
#include <optional>

namespace wsprrypico::provisioning {

class PicoGp14Capture {
  public:
    enum class Fault : std::uint8_t {
        None,
        AlreadyStarted,
        PioClaim,
        DmaClaim,
        Clock,
        DmaCount,
        RingOverrun,
        DmaStopped,
        RxStall,
        NoProgress,
        SampleStream,
    };
    explicit PicoGp14Capture(std::optional<unsigned> gp = 14)
        : pin(gp.value_or(14)), enabled_(gp.has_value()) {}
    const unsigned pin;
    static constexpr std::uint32_t ring_words = 2048;

#ifdef WSPRRY_PICO_GP14_ROBUSTNESS
    bool start(bool boot_held = false);
    void sample_override(bool pressed);
    volatile std::uint32_t* sample_instruction();
#else
    bool start();
#endif
    bool poll_progress();
    [[nodiscard]] std::uint64_t completed_blocks() const {
        return progress_.blocks();
    }
#ifdef WSPRRY_PICO_GP14_ROBUSTNESS
    void inject_dma_stop();
    void inject_pio_stop();
#endif
    // Returns one release or threshold event. Call until false each loop.
    bool next(DiagnosticButtonEvents& event);
    [[nodiscard]] bool fault() const {
        return fault_ || stream_.fault();
    }
    [[nodiscard]] Fault fault_code() const {
        return fault_code_;
    }
    [[nodiscard]] bool held() const {
        return stream_.held();
    }
    [[nodiscard]] std::uint64_t samples() const {
        return stream_.samples();
    }
    [[nodiscard]] std::uint64_t maximum_backlog_words() const {
        return maximum_backlog_words_;
    }

  private:
    const bool enabled_;
    alignas(8192) std::array<std::uint32_t, ring_words> words_{};
    ButtonSampleStream stream_;
    Rp2350DmaProgress progress_;
    PIO pio_ = nullptr;
    unsigned sm_ = 0;
    unsigned offset_ = 0;
    int dma_ = -1;
    std::uint64_t consumed_words_ = 0;
    std::uint64_t last_produced_words_ = 0;
    std::uint32_t current_word_ = 0;
    unsigned next_bit_ = 8;
    std::uint64_t last_progress_us_ = 0;
    std::uint64_t maximum_backlog_words_ = 0;
    bool fault_ = false;
    Fault fault_code_ = Fault::None;
};

} // namespace wsprrypico::provisioning

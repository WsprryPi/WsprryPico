#include "provisioning/pico/gp14_capture.hpp"

#include "gp14_sampler.pio.h"
#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/pins.hpp"
#include "hardware/regs/dma.h"
#include "hardware/structs/pio.h"
#include "hardware/sync.h"
#include "pico/time.h"
#include "provisioning/pico/rp2350_dma_progress.hpp"

#include <algorithm>

static_assert(wsprrypico::provisioning::Rp2350DmaProgress::count_mask ==
              DMA_CH0_TRANS_COUNT_COUNT_BITS);
static_assert(wsprrypico::provisioning::Rp2350DmaProgress::self_trigger ==
              (DMA_CH0_TRANS_COUNT_MODE_VALUE_TRIGGER_SELF << DMA_CH0_TRANS_COUNT_MODE_LSB));

namespace wsprrypico::provisioning {

#ifdef WSPRRY_PICO_GP14_ROBUSTNESS
bool PicoGp14Capture::start(bool boot_held) {
#else
bool PicoGp14Capture::start() {
#endif
    if (!enabled_)
        return true;
    if (!hardware::eligible(pin)) {
        fault_ = true;
        fault_code_ = Fault::PioClaim;
        return false;
    }
    if (pio_ || dma_ >= 0) {
        fault_ = true;
        fault_code_ = Fault::AlreadyStarted;
        return false;
    }
    gpio_init(pin);
    gpio_set_dir(pin, GPIO_IN);
    gpio_pull_up(pin);
    if (!pio_claim_free_sm_and_add_program_for_gpio_range(&gp14_sampler_program, &pio_, &sm_,
                                                          &offset_, pin, 1, true)) {
        fault_ = true;
        fault_code_ = Fault::PioClaim;
        return false;
    }
    dma_ = dma_claim_unused_channel(false);
    if (dma_ < 0) {
        fault_ = true;
        fault_code_ = Fault::DmaClaim;
        return false;
    }
    const auto system_hz = clock_get_hz(clk_sys);
    if (!system_hz) {
        fault_ = true;
        fault_code_ = Fault::Clock;
        return false;
    }
    auto config = gp14_sampler_program_get_default_config(offset_);
    sm_config_set_in_pins(&config, pin);
    sm_config_set_in_shift(&config, false, true, 8);
    sm_config_set_fifo_join(&config, PIO_FIFO_JOIN_RX);
    sm_config_set_clkdiv(&config, static_cast<float>(system_hz) / 32'000.0f);
    pio_gpio_init(pio_, pin);
    pio_sm_init(pio_, sm_, offset_, &config);
    pio_sm_set_consecutive_pindirs(pio_, sm_, pin, 1, false);
#ifdef WSPRRY_PICO_GP14_ROBUSTNESS
    pio_sm_exec(pio_, sm_, pio_encode_set(pio_x, 1));
    sample_override(boot_held);
#endif

    auto dma_config = dma_channel_get_default_config(static_cast<unsigned>(dma_));
    channel_config_set_transfer_data_size(&dma_config, DMA_SIZE_32);
    channel_config_set_read_increment(&dma_config, false);
    channel_config_set_write_increment(&dma_config, true);
    channel_config_set_ring(&dma_config, true, 13);
    channel_config_set_dreq(&dma_config, pio_get_dreq(pio_, sm_, false));
    channel_config_set_irq_quiet(&dma_config, true);
    last_progress_us_ = time_us_64();
    progress_ = Rp2350DmaProgress(last_progress_us_);
    dma_channel_configure(
        static_cast<unsigned>(dma_), &dma_config, words_.data(), &pio_->rxf[sm_],
        dma_encode_transfer_count_with_self_trigger(Rp2350DmaProgress::transfer_words), true);
    last_progress_us_ = time_us_64();
    pio_sm_set_enabled(pio_, sm_, true);
    return true;
}

bool PicoGp14Capture::poll_progress() {
    if (!enabled_)
        return true;
    if (fault_ || !pio_ || dma_ < 0)
        return false;
    const auto now = time_us_64();
    auto* dma = dma_channel_hw_addr(static_cast<unsigned>(dma_));
    const auto produced = progress_.observe(dma->transfer_count, now);
    auto fail = [&](Fault code) {
        fault_ = true;
        fault_code_ = code;
        return false;
    };
    if (!produced)
        return fail(Fault::DmaCount);
    if (!ButtonSampleStream::backlog_valid(*produced, consumed_words_, ring_words))
        return fail(Fault::RingOverrun);
    // BUSY may briefly fall at a self-retrigger boundary. EN is stable across
    // reload; a stalled/aborted enabled channel is caught by the progress timer.
    const auto control = dma->ctrl_trig;
    if (!(control & DMA_CH0_CTRL_TRIG_EN_BITS) || (control & DMA_CH0_CTRL_TRIG_AHB_ERROR_BITS))
        return fail(Fault::DmaStopped);
    if (pio_->fdebug & (1u << (PIO_FDEBUG_RXSTALL_LSB + sm_)))
        return fail(Fault::RxStall);
    if (*produced != last_produced_words_) {
        last_produced_words_ = *produced;
        last_progress_us_ = now;
    } else if (now - last_progress_us_ > 100'000) {
        return fail(Fault::NoProgress);
    }
    maximum_backlog_words_ = std::max(maximum_backlog_words_, *produced - consumed_words_);
    return true;
}

bool PicoGp14Capture::next(DiagnosticButtonEvents& event) {
    if (!enabled_)
        return false;
    event = {};
    while (poll_progress()) {
        if (next_bit_ == 8) {
            if (consumed_words_ == last_produced_words_)
                return false;
            __dmb(); // Observe the completed DMA write after its transfer count.
            current_word_ = words_[consumed_words_ % ring_words];
            __dmb();
            // Refuse the word if DMA lapped the reader during the copy.
            if (!poll_progress())
                return false;
            ++consumed_words_;
            next_bit_ = 0;
        }
        event = stream_.observe_word(current_word_, next_bit_++);
        if (stream_.fault()) {
            fault_ = true;
            fault_code_ = Fault::SampleStream;
            return false;
        }
        if (event.request_reset || event.request_stop || event.request_setup_ap || event.released)
            return true;
    }
    return false;
}

#ifdef WSPRRY_PICO_GP14_ROBUSTNESS
volatile std::uint32_t* PicoGp14Capture::sample_instruction() {
    return &pio_->instr_mem[offset_];
}
void PicoGp14Capture::sample_override(bool pressed) {
    // Same IN cadence, shift/autopush, FIFO and DMA as the real pin sampler.
    // Only its source changes; neither PIO nor SIO drives the pad.
    *sample_instruction() = pio_encode_in(pressed ? pio_null : pio_x, 1) | pio_encode_delay(31);
}
void PicoGp14Capture::inject_dma_stop() {
    if (dma_ >= 0)
        dma_channel_hw_addr(static_cast<unsigned>(dma_))->ctrl_trig &= ~DMA_CH0_CTRL_TRIG_EN_BITS;
}
void PicoGp14Capture::inject_pio_stop() {
    if (pio_)
        pio_sm_set_enabled(pio_, sm_, false);
}
#endif

} // namespace wsprrypico::provisioning

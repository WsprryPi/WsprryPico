#include "provisioning/pico/gp14_capture.hpp"

#include "gp14_sampler.pio.h"
#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/regs/dma.h"
#include "hardware/structs/pio.h"
#include "hardware/sync.h"
#include "pico/time.h"
#include "provisioning/pico/rp2350_dma_progress.hpp"

#include <algorithm>

static_assert(wsprrypico::provisioning::Rp2350DmaProgress::transfer_words ==
              DMA_CH0_TRANS_COUNT_COUNT_BITS);

namespace wsprrypico::provisioning {

bool PicoGp14Capture::start() {
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

    auto dma_config = dma_channel_get_default_config(static_cast<unsigned>(dma_));
    channel_config_set_transfer_data_size(&dma_config, DMA_SIZE_32);
    channel_config_set_read_increment(&dma_config, false);
    channel_config_set_write_increment(&dma_config, true);
    channel_config_set_ring(&dma_config, true, 13);
    channel_config_set_dreq(&dma_config, pio_get_dreq(pio_, sm_, false));
    dma_channel_configure(static_cast<unsigned>(dma_), &dma_config, words_.data(), &pio_->rxf[sm_],
                          dma_encode_transfer_count(Rp2350DmaProgress::transfer_words), true);
    last_progress_us_ = time_us_64();
    pio_sm_set_enabled(pio_, sm_, true);
    return true;
}

bool PicoGp14Capture::next(DiagnosticButtonEvents& event) {
    event = {};
    if (fault_ || !pio_ || dma_ < 0)
        return false;
    while (true) {
        const auto produced = Rp2350DmaProgress::produced(
            dma_channel_hw_addr(static_cast<unsigned>(dma_))->transfer_count);
        if (!produced || *produced < last_produced_words_) {
            fault_ = true;
            fault_code_ = Fault::DmaCount;
            return false;
        }
        if (!ButtonSampleStream::backlog_valid(*produced, consumed_words_, ring_words)) {
            fault_ = true;
            fault_code_ = Fault::RingOverrun;
            return false;
        }
        if (!dma_channel_is_busy(static_cast<unsigned>(dma_))) {
            fault_ = true;
            fault_code_ = Fault::DmaStopped;
            return false;
        }
        if (pio_->fdebug & (1u << (PIO_FDEBUG_RXSTALL_LSB + sm_))) {
            fault_ = true;
            fault_code_ = Fault::RxStall;
            return false;
        }
        if (*produced != last_produced_words_) {
            last_produced_words_ = *produced;
            last_progress_us_ = time_us_64();
        } else if (time_us_64() - last_progress_us_ > 100'000) {
            fault_ = true;
            fault_code_ = Fault::NoProgress;
            return false;
        }
        maximum_backlog_words_ = std::max(maximum_backlog_words_,
                                          static_cast<std::uint64_t>(*produced - consumed_words_));
        if (next_bit_ == 8) {
            if (consumed_words_ == *produced)
                return false;
            __dmb(); // Observe the completed DMA write after its transfer count.
            current_word_ = words_[consumed_words_ % ring_words];
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
}

} // namespace wsprrypico::provisioning

#include "provisioning/pico/gp14_capture.hpp"

#include "gp14_sampler.pio.h"
#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/structs/pio.h"
#include "hardware/sync.h"
#include "pico/time.h"

#include <algorithm>
#include <limits>

namespace wsprrypico::provisioning {

bool PicoGp14Capture::start() {
    if (pio_ || dma_ >= 0)
        return false;
    gpio_init(pin);
    gpio_set_dir(pin, GPIO_IN);
    gpio_pull_up(pin);
    if (!pio_claim_free_sm_and_add_program_for_gpio_range(&gp14_sampler_program, &pio_, &sm_,
                                                          &offset_, pin, 1, true)) {
        fault_ = true;
        return false;
    }
    dma_ = dma_claim_unused_channel(false);
    if (dma_ < 0) {
        fault_ = true;
        return false;
    }
    const auto system_hz = clock_get_hz(clk_sys);
    if (!system_hz) {
        fault_ = true;
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
                          std::numeric_limits<std::uint32_t>::max(), true);
    last_progress_us_ = time_us_64();
    pio_sm_set_enabled(pio_, sm_, true);
    return true;
}

bool PicoGp14Capture::next(DiagnosticButtonEvents& event) {
    event = {};
    if (fault_ || !pio_ || dma_ < 0)
        return false;
    while (true) {
        const auto produced = std::numeric_limits<std::uint32_t>::max() -
                              dma_channel_hw_addr(static_cast<unsigned>(dma_))->transfer_count;
        if (produced < last_produced_words_ ||
            !ButtonSampleStream::backlog_valid(produced, consumed_words_, ring_words) ||
            !dma_channel_is_busy(static_cast<unsigned>(dma_)) ||
            (pio_->fdebug & (1u << (PIO_FDEBUG_RXSTALL_LSB + sm_)))) {
            fault_ = true;
            return false;
        }
        if (produced != last_produced_words_) {
            last_produced_words_ = produced;
            last_progress_us_ = time_us_64();
        } else if (time_us_64() - last_progress_us_ > 100'000) {
            fault_ = true;
            return false;
        }
        maximum_backlog_words_ = std::max(maximum_backlog_words_,
                                          static_cast<std::uint64_t>(produced - consumed_words_));
        if (next_bit_ == 8) {
            if (consumed_words_ == produced)
                return false;
            __dmb(); // Observe the completed DMA write after its transfer count.
            current_word_ = words_[consumed_words_ % ring_words];
            ++consumed_words_;
            next_bit_ = 0;
        }
        event = stream_.observe_word(current_word_, next_bit_++);
        if (stream_.fault()) {
            fault_ = true;
            return false;
        }
        if (event.request_reset || event.request_stop || event.request_setup_ap || event.released)
            return true;
    }
}

} // namespace wsprrypico::provisioning

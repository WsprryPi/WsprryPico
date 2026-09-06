#include "rf/pico/pico_pio_dma.hpp"

#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/sync.h"
#include "hardware/timer.h"
#include "packed_output.pio.h"
#include "pico/platform.h"

namespace wsprrypico::rf {
PicoPioDma* PicoPioDma::instance_ = nullptr;

std::uint32_t PicoPioDma::lock() {
    return save_and_disable_interrupts();
}
void PicoPioDma::unlock(std::uint32_t saved) {
    restore_interrupts(saved);
}
std::uint64_t PicoPioDma::now_ns() const {
    return time_us_64() * 1000;
}

bool PicoPioDma::open(Handler handler, void* context) {
    if (instance_ || !handler || clock_get_hz(clk_sys) != sample_rate ||
        irq_get_exclusive_handler(DMA_IRQ_3) || irq_has_shared_handler(DMA_IRQ_3) ||
        dma_hw->inte3 != 0) {
        return false;
    }
    core_ = get_core_num();
    if (!pio_claim_free_sm_and_add_program_for_gpio_range(&packed_output_program, &pio_, &sm_,
                                                          &offset_, rf_pin, 1, true)) {
        return false;
    }
    channel_ = dma_claim_unused_channel(false);
    if (channel_ >= 0) {
        alarm_ = hardware_alarm_claim_unused(false);
    }
    if (channel_ < 0 || alarm_ < 0) {
        if (channel_ >= 0) {
            dma_channel_unclaim(static_cast<unsigned>(channel_));
        }
        channel_ = -1;
        pio_remove_program_and_unclaim_sm(&packed_output_program, pio_, sm_, offset_);
        pio_ = nullptr;
        return false;
    }
    handler_ = handler;
    context_ = context;
    instance_ = this;
    auto config = packed_output_program_get_default_config(offset_);
    sm_config_set_out_pins(&config, rf_pin, 1);
    sm_config_set_out_shift(&config, true, true, 32);
    sm_config_set_fifo_join(&config, PIO_FIFO_JOIN_TX);
    sm_config_set_clkdiv_int_frac8(&config, 1, 0);
    pio_sm_init(pio_, sm_, offset_, &config);
    gpio_set_outover(rf_pin, GPIO_OVERRIDE_LOW);
    pio_gpio_init(pio_, rf_pin);
    pio_sm_set_consecutive_pindirs(pio_, sm_, rf_pin, 1, true);
    pio_sm_set_pins_with_mask(pio_, sm_, 0, 1U << rf_pin);
    irq_set_exclusive_handler(DMA_IRQ_3, dma_irq);
    irq_set_enabled(DMA_IRQ_3, true);
    hardware_alarm_set_callback(static_cast<unsigned>(alarm_), alarm_irq);
    installed_ = true;
    return true;
}

bool PicoPioDma::halt(std::uint64_t deadline_ns) {
    if (!pio_) {
        return true;
    }
    if (get_core_num() != core_) {
        return false;
    }
    hardware_alarm_cancel(static_cast<unsigned>(alarm_));
    gpio_set_outover(rf_pin, GPIO_OVERRIDE_LOW);
    pio_sm_set_enabled(pio_, sm_, false);
    const auto channel = static_cast<unsigned>(channel_);
    dma_irqn_set_channel_enabled(3, channel, false);
    // RP2350-E5: clear EN before abort. This driver never chains/re-triggers DMA.
    hw_clear_bits(&dma_hw->ch[channel].ctrl_trig, DMA_CH0_CTRL_TRIG_EN_BITS);
    dma_hw->abort = 1U << channel;
    while (dma_channel_is_busy(channel)) {
        if (now_ns() > deadline_ns) {
            return false;
        }
        tight_loop_contents();
    }
    dma_irqn_acknowledge_channel(3, channel);
    pio_sm_clear_fifos(pio_, sm_);
    pio_sm_restart(pio_, sm_);
    pio_sm_set_pins_with_mask(pio_, sm_, 0, 1U << rf_pin);
    pio_sm_exec(pio_, sm_, pio_encode_jmp(offset_));
    pio_->fdebug = 1U << (PIO_FDEBUG_TXSTALL_LSB + sm_);
    return true;
}

bool PicoPioDma::release(std::uint64_t deadline_ns) {
    const auto saved = lock();
    if (!halt(deadline_ns)) {
        unlock(saved);
        return false;
    }
    if (installed_) {
        hardware_alarm_set_callback(static_cast<unsigned>(alarm_), nullptr);
        hardware_alarm_unclaim(static_cast<unsigned>(alarm_));
        irq_set_enabled(DMA_IRQ_3, false);
        irq_remove_handler(DMA_IRQ_3, dma_irq);
        dma_channel_unclaim(static_cast<unsigned>(channel_));
        pio_remove_program_and_unclaim_sm(&packed_output_program, pio_, sm_, offset_);
        gpio_set_function(rf_pin, GPIO_FUNC_NULL);
        instance_ = nullptr;
        installed_ = false;
        pio_ = nullptr;
        channel_ = alarm_ = -1;
    }
    unlock(saved);
    return true;
}

bool PicoPioDma::dma(const std::uint32_t* data, std::uint32_t words, bool increment,
                     std::uint64_t epoch, std::uint64_t sequence) {
    if (!installed_ || get_core_num() != core_ ||
        dma_channel_is_busy(static_cast<unsigned>(channel_))) {
        return false;
    }
    const auto channel = static_cast<unsigned>(channel_);
    auto config = dma_channel_get_default_config(channel);
    channel_config_set_transfer_data_size(&config, DMA_SIZE_32);
    channel_config_set_read_increment(&config, increment);
    channel_config_set_write_increment(&config, false);
    channel_config_set_chain_to(&config, channel);
    channel_config_set_dreq(&config, pio_get_dreq(pio_, sm_, true));
    dma_epoch_ = epoch;
    dma_sequence_ = sequence;
    dma_irqn_acknowledge_channel(3, channel);
    dma_irqn_set_channel_enabled(3, channel, true);
    dma_channel_configure(channel, &config, &pio_->txf[sm_], data, words, true);
    return true;
}

bool PicoPioDma::alarm(std::uint64_t start_ns, std::uint64_t epoch) {
    if (!installed_ || get_core_num() != core_ || start_ns % 1000 != 0) {
        return false;
    }
    const auto start_us = start_ns / 1000;
    const auto now = time_us_64();
    if (start_us <= now + 1) {
        return false;
    }
    alarm_epoch_ = epoch;
    const auto target = start_us > now + 50 ? start_us - 50 : now + 1;
    return !hardware_alarm_set_target(static_cast<unsigned>(alarm_), from_us_since_boot(target));
}

bool PicoPioDma::launch(std::uint64_t start_ns) {
    const auto now = now_ns();
    if (!installed_ || start_ns % 1000 != 0 || now > start_ns || start_ns - now > 50'000 ||
        pio_sm_is_tx_fifo_empty(pio_, sm_)) {
        return false;
    }
    while (now_ns() < start_ns) {
        tight_loop_contents();
    }
    if (now_ns() != start_ns) {
        return false;
    }
    pio_->fdebug = 1U << (PIO_FDEBUG_TXSTALL_LSB + sm_);
    gpio_set_outover(rf_pin, GPIO_OVERRIDE_NORMAL);
    pio_sm_set_enabled(pio_, sm_, true);
    return true;
}

bool PicoPioDma::stalled() const {
    return pio_ && (pio_->fdebug & (1U << (PIO_FDEBUG_TXSTALL_LSB + sm_)));
}

bool PicoPioDma::active() const {
    return pio_ && (pio_->ctrl & (1U << sm_));
}

void PicoPioDma::dma_irq() {
    auto* self = instance_;
    if (!self || !dma_irqn_get_channel_status(3, static_cast<unsigned>(self->channel_))) {
        return;
    }
    const auto channel = static_cast<unsigned>(self->channel_);
    dma_irqn_acknowledge_channel(3, channel);
    const auto error = dma_hw->ch[channel].ctrl_trig & DMA_CH0_CTRL_TRIG_AHB_ERROR_BITS;
    self->handler_(self->context_,
                   {error ? DriverEventKind::DmaError : DriverEventKind::DmaComplete,
                    self->dma_epoch_, self->dma_sequence_});
}

void PicoPioDma::alarm_irq(unsigned alarm) {
    auto* self = instance_;
    if (self && alarm == static_cast<unsigned>(self->alarm_)) {
        self->handler_(self->context_, {DriverEventKind::Alarm, self->alarm_epoch_, 0});
    }
}

} // namespace wsprrypico::rf

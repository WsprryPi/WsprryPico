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
static_assert(RefillMetrics::full_words == block_words);
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
    channels_[0].id = dma_claim_unused_channel(false);
    if (channels_[0].id >= 0)
        channels_[1].id = dma_claim_unused_channel(false);
    if (channels_[1].id >= 0)
        stop_channel_ = dma_claim_unused_channel(false);
    if (stop_channel_ >= 0)
        alarm_ = hardware_alarm_claim_unused(false);
    if (stop_channel_ < 0 || alarm_ < 0) {
        for (auto& channel : channels_) {
            if (channel.id >= 0)
                dma_channel_unclaim(static_cast<unsigned>(channel.id));
            channel.id = -1;
        }
        if (stop_channel_ >= 0)
            dma_channel_unclaim(static_cast<unsigned>(stop_channel_));
        stop_channel_ = -1;
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
    launched_ = false;
    std::uint32_t abort_mask = 0;
    // Clear both EN bits before aborting either channel (RP2350-E5).
    for (const auto& slot : channels_) {
        const auto channel = static_cast<unsigned>(slot.id);
        dma_irqn_set_channel_enabled(3, channel, false);
        hw_clear_bits(&dma_hw->ch[channel].ctrl_trig, DMA_CH0_CTRL_TRIG_EN_BITS);
        abort_mask |= 1U << channel;
    }
    const auto stop_channel = static_cast<unsigned>(stop_channel_);
    hw_clear_bits(&dma_hw->ch[stop_channel].ctrl_trig, DMA_CH0_CTRL_TRIG_EN_BITS);
    dma_hw->abort = abort_mask | (1U << stop_channel);
    while (dma_channel_is_busy(stop_channel)) {
        if (now_ns() > deadline_ns)
            return false;
        tight_loop_contents();
    }
    for (auto& slot : channels_) {
        const auto channel = static_cast<unsigned>(slot.id);
        while (dma_channel_is_busy(channel)) {
            if (now_ns() > deadline_ns)
                return false;
            tight_loop_contents();
        }
        dma_irqn_acknowledge_channel(3, channel);
        slot.occupied = false;
    }
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
        for (auto& slot : channels_) {
            dma_channel_unclaim(static_cast<unsigned>(slot.id));
            slot.id = -1;
        }
        dma_channel_unclaim(static_cast<unsigned>(stop_channel_));
        stop_channel_ = -1;
        pio_remove_program_and_unclaim_sm(&packed_output_program, pio_, sm_, offset_);
        gpio_set_function(rf_pin, GPIO_FUNC_NULL);
        instance_ = nullptr;
        installed_ = false;
        pio_ = nullptr;
        alarm_ = -1;
    }
    unlock(saved);
    return true;
}

bool PicoPioDma::dma(const std::uint32_t* data, std::uint32_t words, bool increment,
                     std::uint64_t epoch, std::uint64_t sequence) {
    if (!installed_ || get_core_num() != core_)
        return false;
    Channel* free = nullptr;
    Channel* previous = nullptr;
    for (auto& slot : channels_) {
        if (!slot.occupied)
            free = &slot;
        else
            previous = &slot;
    }
    if (!free)
        return false;
    const auto channel = static_cast<unsigned>(free->id);
    auto config = dma_channel_get_default_config(channel);
    channel_config_set_transfer_data_size(&config, DMA_SIZE_32);
    channel_config_set_read_increment(&config, increment);
    channel_config_set_write_increment(&config, false);
    channel_config_set_chain_to(&config, channel); // No successor until fresh data is queued.
    if (!increment) {
        const auto stop_channel = static_cast<unsigned>(stop_channel_);
        auto stop_config = dma_channel_get_default_config(stop_channel);
        channel_config_set_transfer_data_size(&stop_config, DMA_SIZE_32);
        channel_config_set_read_increment(&stop_config, false);
        channel_config_set_write_increment(&stop_config, false);
        channel_config_set_chain_to(&stop_config, stop_channel);
        stop_mask_ = 1U << sm_;
        dma_channel_configure(stop_channel, &stop_config, hw_clear_alias_untyped(&pio_->ctrl),
                              &stop_mask_, 1, false);
        channel_config_set_chain_to(&config, stop_channel);
    }
    channel_config_set_dreq(&config, pio_get_dreq(pio_, sm_, true));
    free->epoch = epoch;
    free->sequence = sequence;
    free->occupied = true;
    free->tail = !increment;
    free->words = words;
    dma_irqn_acknowledge_channel(3, channel);
    dma_irqn_set_channel_enabled(3, channel, true);
    dma_channel_configure(channel, &config, &pio_->txf[sm_], data, words, false);
    if (previous) {
        // A completed predecessor must never be manually retriggered. If a late
        // producer loses this chain race, TXSTALL invalidates the run instead.
        const auto prior = static_cast<unsigned>(previous->id);
        if (!dma_channel_is_busy(prior)) {
            // A tiny prelaunch buffer may already be in the stopped FIFO.
            // Start only this new descriptor, never the completed predecessor.
            if (!dma_irqn_get_channel_status(3, prior))
                return false;
            dma_start_channel_mask(1U << channel);
        } else {
            hw_write_masked(&dma_hw->ch[prior].ctrl_trig, channel << DMA_CH0_CTRL_TRIG_CHAIN_TO_LSB,
                            DMA_CH0_CTRL_TRIG_CHAIN_TO_BITS);
        }
    } else {
        dma_start_channel_mask(1U << channel);
    }
    if (previous && launched_) {
        // Read only after successor configuration/chain installation. A zero
        // count records an exhausted predecessor, even if FIFO reserve hid it.
        const auto remaining = dma_hw->ch[static_cast<unsigned>(previous->id)].transfer_count &
                               DMA_CH0_TRANS_COUNT_COUNT_BITS;
        refill_metrics_.ready(epoch, sequence, now_ns(), true, !increment, remaining,
                              previous->words);
    }
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
    // Allow for bounded interrupt latency from foreground USB service. The
    // callback still waits against the monotonic timer and enables PIO only at
    // the requested microsecond.
    constexpr std::uint64_t alarm_advance_us = 200;
    const auto target = start_us > now + alarm_advance_us ? start_us - alarm_advance_us : now + 1;
    return !hardware_alarm_set_target(static_cast<unsigned>(alarm_), from_us_since_boot(target));
}

bool PicoPioDma::launch(std::uint64_t start_ns) {
    const auto target_us = start_ns / 1000;
    auto observed_us = time_us_64();
    if (!installed_ || start_ns % 1000 != 0 || observed_us > target_us ||
        target_us - observed_us > 250 || pio_sm_is_tx_fifo_empty(pio_, sm_)) {
        return false;
    }
    // Prime the output shift register while disabled. Autopull on the first
    // OUT would otherwise record a startup TXSTALL despite a prefilled FIFO.
    pio_sm_exec(pio_, sm_, pio_encode_pull(false, true));
    observed_us = time_us_64();
    // Reuse the sample that ended the wait. A second clock read can cross into
    // the next microsecond and falsely reject an on-time observation.
    while (observed_us < target_us)
        observed_us = time_us_64();
    if (observed_us != target_us)
        return false;
    pio_->fdebug = 1U << (PIO_FDEBUG_TXSTALL_LSB + sm_);
    gpio_set_outover(rf_pin, GPIO_OVERRIDE_NORMAL);
    pio_sm_set_enabled(pio_, sm_, true);
    metrics_.launch_ns = now_ns();
    metrics_.launch_epoch = alarm_epoch_;
    metrics_.launch_target_ns = start_ns;
    launched_ = true;
    return true;
}

PicoDriverMetrics PicoPioDma::metrics() {
    const auto saved = lock();
    metrics_.refill = refill_metrics_.snapshot();
    const auto value = metrics_;
    unlock(saved);
    return value;
}

bool PicoPioDma::stalled() const {
    return pio_ && (pio_->fdebug & (1U << (PIO_FDEBUG_TXSTALL_LSB + sm_)));
}

bool PicoPioDma::active() const {
    return pio_ && (pio_->ctrl & (1U << sm_));
}

void PicoPioDma::dma_irq() {
    auto* self = instance_;
    if (!self)
        return;
    const auto before = self->now_ns();
    Channel* next = nullptr;
    for (auto& slot : self->channels_) {
        if (slot.occupied && dma_irqn_get_channel_status(3, static_cast<unsigned>(slot.id)) &&
            (!next || slot.sequence < next->sequence))
            next = &slot;
    }
    if (!next)
        return;
    const auto channel = static_cast<unsigned>(next->id);
    dma_irqn_acknowledge_channel(3, channel);
    const auto error = dma_hw->ch[channel].ctrl_trig & DMA_CH0_CTRL_TRIG_AHB_ERROR_BITS;
    const auto epoch = next->epoch, sequence = next->sequence;
    const auto tail = next->tail;
    next->occupied = false;
    self->refill_metrics_.completed(epoch, sequence, before);
    self->handler_(
        self->context_,
        {error ? DriverEventKind::DmaError : DriverEventKind::DmaComplete, epoch, sequence});
    const auto elapsed = self->now_ns() - before;
    ++self->metrics_.dma_irqs;
    if (tail)
        ++self->metrics_.tail_irqs;
    if (error)
        ++self->metrics_.dma_errors;
    if (elapsed > self->metrics_.max_irq_ns)
        self->metrics_.max_irq_ns = elapsed;
}

void PicoPioDma::alarm_irq(unsigned alarm) {
    auto* self = instance_;
    if (self && alarm == static_cast<unsigned>(self->alarm_)) {
        const auto before = self->now_ns();
        self->handler_(self->context_, {DriverEventKind::Alarm, self->alarm_epoch_, 0});
        const auto elapsed = self->now_ns() - before;
        ++self->metrics_.alarm_irqs;
        if (elapsed > self->metrics_.max_alarm_irq_ns)
            self->metrics_.max_alarm_irq_ns = elapsed;
    }
}

} // namespace wsprrypico::rf

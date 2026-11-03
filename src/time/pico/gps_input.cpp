// SPDX-License-Identifier: MIT
#include "time/pico/gps_input.hpp"

#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/pwm.h"
#include "hardware/structs/clocks.h"
#include "hardware/structs/io_bank0.h"
#include "hardware/structs/pll.h"
#include "hardware/structs/uart.h"
#include "hardware/ticks.h"
#include "hardware/uart.h"
#include "pico/time.h"
#include "time/capture_gap.hpp"
#include "wtp/json.hpp"

#include <algorithm>

namespace wsprrypico::time {
namespace {
PicoGpsInput* owner = nullptr;
void uart_irq() {
    if (owner)
        owner->uart_interrupt();
}
void pps_irq() {
    if (owner)
        owner->pps_interrupt();
}
void gps_capture_gap(bool entering) {
    if (owner)
        owner->capture_gap(entering);
}
uart_inst_t* instance(unsigned index) {
    return index ? uart1 : uart0;
}
unsigned interrupt(unsigned index) {
    return index ? UART1_IRQ : UART0_IRQ;
}
} // namespace
bool PicoGpsInput::open(const hardware::PinPlan& pins,
                        const std::optional<hardware::Si5351Settings>& si,
                        const hardware::GpsSettings& settings,
                        const hardware::FilterSettings& filters) {
    if (open_ || owner || !settings.enabled ||
        !hardware::validate_gps(pins, si, settings, filters).empty())
        return false;
    uart_index_ = *hardware::gps_uart(settings.rx_gp);
    auto* uart = instance(uart_index_);
    if (uart_is_enabled(uart))
        return false;
    pps_slice_ = (settings.pps_gp >> 1u) & 7u;
    system_hz_ = clock_get_hz(clk_sys);
    reference_hz_ = clock_get_hz(clk_ref);
    if (pwm_gpio_to_channel(settings.pps_gp) != PWM_CHAN_B ||
        pwm_gpio_to_slice_num(settings.pps_gp) != pps_slice_ || (pwm_hw->en & (1u << pps_slice_)) ||
        !clock_bound())
        return false;
    bytes_.discard();
    pulses_.discard();
    parser_ = {};
    position_.reset();
    observation_.reset();
    cycle_.reset();
    captures_ = {};
    failed_ = false;
    capture_gap_depth_ = 0;
    clock_gap_ = false;
    capture_blocked_.store(false, std::memory_order_release);
    irq_latency_ns_.store(0, std::memory_order_relaxed);
    maximum_irq_latency_ns_.store(0, std::memory_order_relaxed);
    capture_error_bound_ns_.store(0, std::memory_order_relaxed);
    capture_rejections_.store(0, std::memory_order_relaxed);
    capture_error_.store(0, std::memory_order_relaxed);
    last_serial_ns_ = last_pps_ns_ = 0;
    candidate_utc_ns_ = candidate_raw_ns_ = candidate_pps_ns_ = 0;
    settings_ = settings;
    pairer_ = gps::Pairer(settings.pairing());
    owner = this;
    uart_init(uart, settings.baud);
    uart_set_format(uart, 8, 1, UART_PARITY_NONE);
    uart_set_hw_flow(uart, false, false);
    gpio_init(settings.rx_gp);
    gpio_set_dir(settings.rx_gp, GPIO_IN);
    gpio_set_function(settings.rx_gp, GPIO_FUNC_UART);
    gpio_init(settings.pps_gp);
    gpio_set_dir(settings.pps_gp, GPIO_IN);
    gpio_set_oeover(settings.pps_gp, GPIO_OVERRIDE_LOW);
    gpio_disable_pulls(settings.pps_gp);
    gpio_set_input_enabled(settings.pps_gp, true);
    // Gate a free-running PWM counter with the input level. Force input-only
    // before selecting PWM, preserving OEOVER (gpio_set_function clears it).
    gpio_set_inover(settings.pps_gp,
                    settings.pps_active_high ? GPIO_OVERRIDE_NORMAL : GPIO_OVERRIDE_INVERT);
    hw_write_masked(&io_bank0_hw->io[settings.pps_gp].ctrl,
                    GPIO_FUNC_PWM << IO_BANK0_GPIO0_CTRL_FUNCSEL_LSB,
                    IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS);
    auto counter = pwm_get_default_config();
    pwm_config_set_clkdiv_mode(&counter, PWM_DIV_B_HIGH);
    pwm_config_set_clkdiv_int_frac4(&counter, 255, 15);
    pwm_init(pps_slice_, &counter, false);
    pwm_set_irq_enabled(pps_slice_, false);
    reset_pps_counter();
    pwm_set_enabled(pps_slice_, true);
    if (settings.tx_gp) {
        gpio_set_function(*settings.tx_gp, GPIO_FUNC_UART);
        // Documented E108/GK9501 command: first fix, 100 ms pulse, 1000 ms period.
        // QLG3 has no RX header and can never take this branch.
        constexpr std::string_view body = "PGKC161,1,100,1000";
        unsigned checksum = 0;
        for (const auto c : body)
            checksum ^= unsigned(c);
        std::array<char, 24> command{};
        command[0] = '$';
        std::copy(body.begin(), body.end(), command.begin() + 1);
        const auto end = body.size() + 1;
        command[end] = '*';
        command[end + 1] = "0123456789ABCDEF"[checksum >> 4];
        command[end + 2] = "0123456789ABCDEF"[checksum & 15];
        command[end + 3] = '\r';
        command[end + 4] = '\n';
        const auto deadline = time_us_64() + 200'000;
        for (unsigned i = 0; i < end + 5; ++i) {
            while (!uart_is_writable(uart) && time_us_64() < deadline)
                tight_loop_contents();
            if (time_us_64() >= deadline) {
                failed_ = true;
                break;
            }
            uart_get_hw(uart)->dr = command[i];
        }
    }
    for (unsigned i = 0; i < 32 && uart_is_readable(uart); ++i)
        (void)uart_get_hw(uart)->dr;
    uart_get_hw(uart)->rsr = 0;
    open_ = true;
    irq_add_shared_handler(interrupt(uart_index_), uart_irq,
                           PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY);
    irq_set_enabled(interrupt(uart_index_), true);
    uart_set_irq_enables(uart, true, false);
    gpio_add_raw_irq_handler(settings.pps_gp, pps_irq);
    irq_set_enabled(IO_IRQ_BANK0, true);
    gpio_acknowledge_irq(settings.pps_gp, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL);
    reset_pps_counter(); // Retire any pulse that arrived during receiver setup.
    gpio_set_irq_enabled(settings.pps_gp, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true);
    if (failed_) {
        close();
        return false;
    }
    CaptureGap::observer(gps_capture_gap);
    return true;
}
void PicoGpsInput::close() {
    if (!open_)
        return;
    CaptureGap::observer(nullptr);
    gpio_set_irq_enabled(settings_.pps_gp, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, false);
    gpio_remove_raw_irq_handler(settings_.pps_gp, pps_irq);
    pwm_set_enabled(pps_slice_, false);
    pwm_clear_irq(pps_slice_);
    gpio_set_dir(settings_.pps_gp, GPIO_IN);
    gpio_set_function(settings_.pps_gp, GPIO_FUNC_SIO);
    uart_set_irq_enables(instance(uart_index_), false, false);
    irq_remove_handler(interrupt(uart_index_), uart_irq);
    uart_deinit(instance(uart_index_));
    gpio_set_function(settings_.rx_gp, GPIO_FUNC_SIO);
    gpio_set_dir(settings_.rx_gp, GPIO_IN);
    if (settings_.tx_gp) {
        gpio_set_function(*settings_.tx_gp, GPIO_FUNC_SIO);
        gpio_set_dir(*settings_.tx_gp, GPIO_IN);
    }
    open_ = false;
    owner = nullptr;
    pairer_.lost();
}
void PicoGpsInput::reset_pps_counter() {
    pwm_set_counter(pps_slice_, 0);
    pwm_clear_irq(pps_slice_);
    const bool high =
        io_bank0_hw->io[settings_.pps_gp].status & IO_BANK0_GPIO0_STATUS_INFROMPAD_BITS;
    pps_counter_armed_ = high != settings_.pps_active_high;
}
bool PicoGpsInput::clock_bound() const {
    // Establish the ratio between the gated system-clock counter and TIMER0;
    // SDK frequency labels alone cannot prove the timer's tick configuration.
    const auto post1 = (pll_sys_hw->prim & PLL_PRIM_POSTDIV1_BITS) >> PLL_PRIM_POSTDIV1_LSB;
    const auto post2 = (pll_sys_hw->prim & PLL_PRIM_POSTDIV2_BITS) >> PLL_PRIM_POSTDIV2_LSB;
    const auto feedback = pll_sys_hw->fbdiv_int & PLL_FBDIV_INT_BITS;
    return system_hz_ && reference_hz_ == 12'000'000 && clock_get_hz(clk_sys) == system_hz_ &&
           clock_get_hz(clk_ref) == reference_hz_ &&
           (clocks_hw->clk[clk_ref].ctrl & CLOCKS_CLK_REF_CTRL_SRC_BITS) ==
               CLOCKS_CLK_REF_CTRL_SRC_VALUE_XOSC_CLKSRC &&
           clocks_hw->clk[clk_ref].div == (1u << CLOCKS_CLK_REF_DIV_INT_LSB) &&
           (clocks_hw->clk[clk_sys].ctrl & CLOCKS_CLK_SYS_CTRL_SRC_BITS) ==
               CLOCKS_CLK_SYS_CTRL_SRC_VALUE_CLKSRC_CLK_SYS_AUX &&
           (clocks_hw->clk[clk_sys].ctrl & CLOCKS_CLK_SYS_CTRL_AUXSRC_BITS) == 0 &&
           clocks_hw->clk[clk_sys].div == (1u << CLOCKS_CLK_SYS_DIV_INT_LSB) &&
           (pll_sys_hw->cs & (PLL_CS_BYPASS_BITS | PLL_CS_REFDIV_BITS | PLL_CS_LOCK_BITS)) ==
               (PLL_CS_LOCK_BITS | 1u) &&
           post1 && post2 &&
           std::uint64_t(system_hz_) * post1 * post2 == std::uint64_t(reference_hz_) * feedback &&
           ticks_hw->ticks[TICK_TIMER0].cycles == 12 && tick_is_running(TICK_TIMER0);
}
void PicoGpsInput::capture_gap(bool entering) {
    if (entering) {
        if (capture_gap_depth_++)
            return;
        capture_blocked_.store(true, std::memory_order_release);
    } else {
        if (!capture_gap_depth_ || --capture_gap_depth_)
            return;
    }
    bytes_.dropped.fetch_add(bytes_.discard(), std::memory_order_relaxed);
    pulses_.dropped.fetch_add(pulses_.discard(), std::memory_order_relaxed);
    parser_.lost();
    pairer_.lost();
    cycle_.reset();
    captures_ = {};
    if (!entering) {
        // Clear latched events while still blocked. A new edge racing this
        // cleanup may be discarded, but cannot be relabelled as an old edge.
        for (unsigned i = 0; i < 32 && uart_is_readable(instance(uart_index_)); ++i) {
            (void)uart_get_hw(instance(uart_index_))->dr;
            bytes_.dropped.fetch_add(1, std::memory_order_relaxed);
        }
        gpio_acknowledge_irq(settings_.pps_gp, GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL);
        reset_pps_counter();
        capture_blocked_.store(false, std::memory_order_release);
    }
}
void PicoGpsInput::uart_interrupt() {
    auto* uart = instance(uart_index_);
    // Bounded even with a noisy or higher-rate input. A pending FIFO retriggers.
    for (unsigned i = 0; i < 32 && uart_is_readable(uart); ++i) {
        const auto raw = std::uint32_t(time_us_64());
        const auto data = std::uint16_t(uart_get_hw(uart)->dr);
        if (capture_blocked_.load(std::memory_order_acquire))
            bytes_.dropped.fetch_add(1, std::memory_order_relaxed);
        else
            (void)bytes_.push({raw, data});
    }
    uart_get_hw(uart)->rsr = 0;
}
void PicoGpsInput::pps_interrupt() {
    const auto flags = gpio_get_irq_event_mask(settings_.pps_gp);
    if (!(flags & (GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL)))
        return;
    const auto before = time_us_64() * 1000ULL;
    const auto count = pwm_get_counter(pps_slice_);
    const bool wrapped = pwm_hw->intr & (1u << pps_slice_);
    const bool high =
        io_bank0_hw->io[settings_.pps_gp].status & IO_BANK0_GPIO0_STATUS_INFROMPAD_BITS;
    const auto after = (time_us_64() + 1) * 1000ULL;
    gpio_acknowledge_irq(settings_.pps_gp, flags);
    if (capture_blocked_.load(std::memory_order_acquire)) {
        pulses_.dropped.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    const auto reject = [&](unsigned error) {
        capture_error_.store(error, std::memory_order_release);
        capture_rejections_.fetch_add(1, std::memory_order_relaxed);
        pulses_.dropped.fetch_add(1, std::memory_order_relaxed);
        pps_counter_armed_ = false;
    };
    if ((flags & (GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL)) ==
        (GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL)) {
        reject(1);
        reset_pps_counter();
        return;
    }
    if (high != settings_.pps_active_high) {
        reset_pps_counter(); // Inactive level stops the counter before reset.
        return;
    }
    if (!pps_counter_armed_) {
        reject(2);
        return;
    }
    if (wrapped) {
        reject(4);
        return;
    }
    if (!clock_bound()) {
        reject(5);
        return;
    }
    if (after < before || after - before > 10'000) {
        reject(6);
        return;
    }
    pps_counter_armed_ = false;
    // Divider 255+15/16. The counter starts at the electrical edge, independently
    // of IRQ delivery. Raw-timer bracketing, two counter ticks, synchronisation,
    // and a 100 ppm clock-ratio allowance round the timestamp bound outward.
    const auto denominator = std::uint64_t(system_hz_) * 16;
    const auto tick = (4095ULL * 1'000'000'000 + denominator - 1) / denominator;
    const auto latency =
        (std::uint64_t(count) * 4095 * 1'000'000'000 + denominator / 2) / denominator;
    const auto bound = (after - before + 1) / 2 + 2 * tick + 1000 + (latency + 9999) / 10000;
    const auto center = before + (after - before) / 2;
    if (center < latency || bound > settings_.capture_uncertainty_us * 1000ULL ||
        latency > UINT32_MAX || bound > UINT32_MAX) {
        reject(3);
        return;
    }
    const auto raw = center - latency;
    capture_error_.store(0, std::memory_order_release);
    maximum_irq_latency_ns_.store(
        std::max(maximum_irq_latency_ns_.load(std::memory_order_relaxed), std::uint32_t(latency)),
        std::memory_order_relaxed);
    irq_latency_ns_.store(std::uint32_t(latency), std::memory_order_release);
    capture_error_bound_ns_.store(std::uint32_t(bound), std::memory_order_release);
    ++pulse_sequence_;
    auto cycle = cycle_capture_ ? cycle_capture_() : gps::CycleSnapshot{};
    if (cycle.coherent && cycle.raw_ns >= raw)
        cycle.uncertainty_ns += cycle.raw_ns - raw;
    else
        cycle.coherent = false;
    (void)pulses_.push({{raw, settings_.capture_uncertainty_us * 1000ULL, pulse_sequence_}, cycle});
}
void PicoGpsInput::poll(std::uint64_t now, Observer observer, void* context) {
    if (!open_)
        return;
    if (!clock_bound()) {
        if (capture_error_.exchange(5, std::memory_order_acq_rel) != 5)
            capture_rejections_.fetch_add(1, std::memory_order_relaxed);
        bytes_.discard();
        pulses_.discard();
        if (!clock_gap_) {
            parser_.lost();
            pairer_.lost();
            clock_gap_ = true;
        }
        observation_.reset();
        cycle_.reset();
        captures_ = {};
        return;
    }
    if (clock_gap_) {
        bytes_.discard();
        pulses_.discard();
        parser_.lost();
        pairer_.lost();
        clock_gap_ = false;
    }
    (void)now;
    const auto drops = bytes_.dropped.load(std::memory_order_acquire) +
                       pulses_.dropped.load(std::memory_order_acquire);
    if (drops != observed_drops_) {
        observed_drops_ = drops;
        parser_.lost();
        pairer_.lost();
        // Discard the queued prefix across the gap. Neither half can be paired
        // with a post-overflow byte or edge to manufacture fresh authority.
        bytes_.discard();
        pulses_.discard();
        captures_ = {};
    }
    for (unsigned work = 0; work < 320; ++work) {
        const auto* byte = bytes_.peek();
        const auto* pulse = pulses_.peek();
        if (!byte && !pulse)
            break;
        const auto processed_now = time_us_64() * 1000ULL;
        const auto age_us = byte ? std::uint32_t(processed_now / 1000 - byte->raw_us) : 0;
        const auto byte_raw =
            byte && age_us * 1000ULL <= processed_now ? processed_now - age_us * 1000ULL : 0;
        if (pulse && (!byte || pulse->pulse.raw_ns <= byte_raw)) {
            last_pps_ns_ = pulse->pulse.raw_ns;
            (void)pairer_.pulse(pulse->pulse);
            for (std::size_t i = captures_.size() - 1; i; --i)
                captures_[i] = captures_[i - 1];
            captures_[0] = *pulse;
            pulses_.pop();
            continue;
        }
        const auto value = *byte;
        bytes_.pop();
        if (age_us > 1'000'000 || (value.data & 0xf00)) {
            ++uart_errors_;
            parser_.lost();
            pairer_.lost();
            continue;
        }
        last_serial_ns_ = byte_raw;
        const auto rejected_before = parser_.rejected();
        const auto message = parser_.byte(char(value.data & 0xff), byte_raw);
        if (parser_.rejected() != rejected_before)
            pairer_.lost();
        if (message) {
            if (message->kind == gps::Message::Kind::Gga)
                satellites_ = message->satellites;
            if (message->position_valid)
                position_ = message->position;
            else if (message->kind == gps::Message::Kind::Gga || !message->time_valid)
                position_.reset();
            if (message->kind != gps::Message::Kind::Rmc)
                continue;
            const auto selected_pulse = pairer_.preceding_pulse(message->received_raw_ns);
            if (message->time_valid && message->utc_ns && selected_pulse) {
                candidate_utc_ns_ = *message->utc_ns;
                candidate_raw_ns_ = message->received_raw_ns;
                candidate_pps_ns_ = selected_pulse->raw_ns;
            }
            if (const auto observation = pairer_.message(*message)) {
                observation_ = observation;
                cycle_.reset();
                for (const auto& capture : captures_)
                    if (capture && capture->pulse.sequence == observation->sequence) {
                        if (capture->cycle.coherent)
                            cycle_ = capture->cycle;
                        break;
                    }
                ++observations_;
                if (observer)
                    observer(*observation, context);
            }
        }
    }
}
std::optional<gps::Position> PicoGpsInput::position(std::uint64_t now) const {
    if (!capture_clock_bound() || !position_ || now < position_->observed_raw_ns ||
        now - position_->observed_raw_ns > settings_.position_maximum_age_s * gps::second)
        return {};
    return position_;
}
std::string PicoGpsInput::status(std::uint64_t now) const {
    const auto fix = position(now);
    const auto fresh = [now](std::uint64_t raw) {
        return raw && now >= raw && now - raw <= 3 * gps::second;
    };
    const auto flag = [](bool value) { return value ? "true" : "false"; };
    const auto time = observation_ ? observation_->raw_ns : 0;
    const char* capture_errors[] = {"",
                                    "ambiguous_pps_edge",
                                    "pps_counter_unarmed",
                                    "capture_uncertainty_exceeded",
                                    "pps_counter_wrap",
                                    "pps_capture_clock_changed",
                                    "pps_capture_bracket_invalid"};
    const auto capture_error = capture_error_.load(std::memory_order_acquire);
    const auto latency = irq_latency_ns_.load(std::memory_order_acquire);
    return "{\"serial_present\":" + std::string(flag(fresh(last_serial_ns_))) +
           ",\"pps_present\":" + flag(fresh(last_pps_ns_)) +
           ",\"time_valid\":" + flag(capture_clock_bound() && fresh(time)) +
           ",\"position_valid\":" + flag(bool(fix)) +
           ",\"satellites\":" + std::to_string(satellites_) +
           ",\"observation_raw_ns\":" + wtp::json::quote(std::to_string(time)) +
           ",\"age_ns\":" + wtp::json::quote(std::to_string(time && now >= time ? now - time : 0)) +
           ",\"position\":" +
           (fix ? "{\"latitude_e7\":" + std::to_string(fix->latitude_e7) + ",\"longitude_e7\":" +
                      std::to_string(fix->longitude_e7) + ",\"observed_raw_ns\":" +
                      wtp::json::quote(std::to_string(fix->observed_raw_ns)) + ",\"age_ns\":" +
                      wtp::json::quote(std::to_string(now - fix->observed_raw_ns)) +
                      ",\"locator\":" + wtp::json::quote(gps::locator(*fix)->data()) + "}"
                : "null") +
           ",\"candidate_utc_ns\":" + wtp::json::quote(std::to_string(candidate_utc_ns_)) +
           ",\"candidate_raw_ns\":" + wtp::json::quote(std::to_string(candidate_raw_ns_)) +
           ",\"candidate_pps_raw_ns\":" + wtp::json::quote(std::to_string(candidate_pps_ns_)) +
           ",\"observations\":" + std::to_string(observations_) +
           ",\"rejected_sentences\":" + std::to_string(parser_.rejected()) +
           ",\"dropped\":" + std::to_string(observed_drops_) +
           ",\"uart_errors\":" + std::to_string(uart_errors_) +
           ",\"irq_latency_ns\":" + wtp::json::quote(std::to_string(latency)) +
           ",\"maximum_irq_latency_ns\":" +
           wtp::json::quote(
               std::to_string(maximum_irq_latency_ns_.load(std::memory_order_relaxed))) +
           ",\"capture_error_bound_ns\":" +
           wtp::json::quote(
               std::to_string(capture_error_bound_ns_.load(std::memory_order_acquire))) +
           ",\"capture_rejections\":" +
           std::to_string(capture_rejections_.load(std::memory_order_relaxed)) + ",\"error\":" +
           wtp::json::quote(failed_         ? "receiver_command_failed"
                            : capture_error ? capture_errors[capture_error]
                                            : pairer_.error()) +
           "}";
}
} // namespace wsprrypico::time

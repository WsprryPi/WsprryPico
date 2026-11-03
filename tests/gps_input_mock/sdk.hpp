// SPDX-License-Identifier: MIT
#pragma once
#include <array>
#include <cassert>
#include <cstdint>
#include <deque>
#include <string>
using uint = unsigned;
inline constexpr unsigned GPIO_IN = 0, GPIO_FUNC_SIO = 5, GPIO_FUNC_UART = 2, GPIO_FUNC_PWM = 4;
inline constexpr unsigned GPIO_OVERRIDE_NORMAL = 0, GPIO_OVERRIDE_INVERT = 1, GPIO_OVERRIDE_LOW = 2;
inline constexpr unsigned PWM_CHAN_B = 1, PWM_DIV_B_HIGH = 1;
inline constexpr unsigned clk_sys = 0, clk_ref = 1;
inline constexpr unsigned IO_BANK0_GPIO0_CTRL_FUNCSEL_LSB = 0,
                          IO_BANK0_GPIO0_CTRL_FUNCSEL_BITS = 31;
inline constexpr unsigned IO_BANK0_GPIO0_STATUS_INFROMPAD_BITS = 1u << 17;
inline constexpr unsigned CLOCKS_CLK_REF_CTRL_SRC_BITS = 3,
                          CLOCKS_CLK_REF_CTRL_SRC_VALUE_XOSC_CLKSRC = 2;
inline constexpr unsigned CLOCKS_CLK_REF_DIV_INT_LSB = 8, CLOCKS_CLK_SYS_DIV_INT_LSB = 8;
inline constexpr unsigned CLOCKS_CLK_SYS_CTRL_SRC_BITS = 1,
                          CLOCKS_CLK_SYS_CTRL_SRC_VALUE_CLKSRC_CLK_SYS_AUX = 1;
inline constexpr unsigned CLOCKS_CLK_SYS_CTRL_AUXSRC_BITS = 0xe0;
inline constexpr unsigned PLL_CS_BYPASS_BITS = 0x100, PLL_CS_REFDIV_BITS = 0x3f,
                          PLL_CS_LOCK_BITS = 1u << 31;
inline constexpr unsigned PLL_PRIM_POSTDIV1_BITS = 0x70000, PLL_PRIM_POSTDIV1_LSB = 16;
inline constexpr unsigned PLL_PRIM_POSTDIV2_BITS = 0x7000, PLL_PRIM_POSTDIV2_LSB = 12,
                          PLL_FBDIV_INT_BITS = 0xfff;
inline constexpr unsigned TICK_TIMER0 = 0;
struct MockClock {
    unsigned ctrl = 0, div = 256;
};
struct MockClocks {
    std::array<MockClock, 2> clk{{{1, 256}, {2, 256}}};
};
inline MockClocks mock_clocks;
inline auto* clocks_hw = &mock_clocks;
struct MockPll {
    unsigned cs = PLL_CS_LOCK_BITS | 1u, prim = (3u << 16) | (4u << 12), fbdiv_int = 138;
};
inline MockPll mock_pll;
inline auto* pll_sys_hw = &mock_pll;
struct MockTick {
    unsigned cycles = 12;
    bool running = true;
};
struct MockTicks {
    std::array<MockTick, 1> ticks;
};
inline MockTicks mock_ticks;
inline auto* ticks_hw = &mock_ticks;
inline bool tick_is_running(unsigned t) {
    return ticks_hw->ticks[t].running;
}
inline constexpr unsigned GPIO_IRQ_EDGE_RISE = 8, GPIO_IRQ_EDGE_FALL = 4;
inline constexpr unsigned UART0_IRQ = 20, UART1_IRQ = 21, IO_IRQ_BANK0 = 13;
inline constexpr unsigned UART_PARITY_NONE = 0, PICO_SHARED_IRQ_HANDLER_DEFAULT_ORDER_PRIORITY = 0;
struct MockIo {
    std::uint32_t status = 0, ctrl = 0;
};
struct MockBank {
    std::array<MockIo, 32> io;
};
inline MockBank mock_bank;
inline auto* io_bank0_hw = &mock_bank;
struct MockPwm {
    std::uint32_t intr = 0, en = 0;
};
inline MockPwm mock_pwm;
inline auto* pwm_hw = &mock_pwm;
namespace gps_mock {
inline std::uint64_t us = 1'000'000;
inline std::array<unsigned, 32> function{}, flags{};
inline std::array<bool, 32> direction{}, input{};
inline std::array<bool, 2> enabled{};
inline std::deque<std::uint16_t> receive;
inline std::string sent;
inline bool writable = true;
inline std::uint32_t sys_hz = 138'000'000, ref_hz = 12'000'000;
inline std::array<unsigned, 32> oeover{}, inover{};
inline std::array<bool, 32> level{};
inline std::array<unsigned, 8> pwm_pin{}, pwm_held{};
inline std::array<std::uint64_t, 8> pwm_start{};
inline unsigned irq_delay_us = 5;
inline unsigned counter(unsigned slice, std::uint64_t at) {
    const auto gp = pwm_pin[slice];
    const bool active = level[gp] ^ (inover[gp] == GPIO_OVERRIDE_INVERT);
    const auto ticks = ((pwm_hw->en & (1u << slice)) && active && at >= pwm_start[slice])
                           ? (at - pwm_start[slice]) * sys_hz * 16ULL / 1'000'000 / 4095
                           : 0;
    const auto n = pwm_held[slice] + ticks;
    if (n >= 65536)
        pwm_hw->intr |= 1u << slice;
    return unsigned(n) & 65535;
}
inline void edge(unsigned gp, bool high, std::uint64_t at) {
    const auto slice = (gp >> 1) & 7;
    if (function[gp] == GPIO_FUNC_PWM)
        pwm_held[slice] = counter(slice, at);
    level[gp] = high;
    pwm_start[slice] = at;
    io_bank0_hw->io[gp].status = high ? IO_BANK0_GPIO0_STATUS_INFROMPAD_BITS : 0;
    flags[gp] |= high ? GPIO_IRQ_EDGE_RISE : GPIO_IRQ_EDGE_FALL;
}
inline void check() {
    assert(!direction[1] && !direction[3]);
    assert(function[3] != GPIO_FUNC_UART);
}
} // namespace gps_mock
struct DataRegister {
    operator std::uint16_t() const {
        assert(!gps_mock::receive.empty());
        const auto value = gps_mock::receive.front();
        gps_mock::receive.pop_front();
        return value;
    }
    void operator=(char c) {
        gps_mock::sent += c;
    }
};
struct uart_hw_t {
    DataRegister dr;
    unsigned rsr = 0;
};
struct uart_inst_t {
    unsigned index;
    uart_hw_t hw;
};
inline uart_inst_t mock0{0, {}}, mock1{1, {}};
inline auto* uart0 = &mock0;
inline auto* uart1 = &mock1;
inline bool uart_is_enabled(uart_inst_t* p) {
    return gps_mock::enabled[p->index];
}
inline unsigned uart_init(uart_inst_t* p, unsigned baud) {
    gps_mock::enabled[p->index] = true;
    return baud;
}
inline void uart_deinit(uart_inst_t* p) {
    gps_mock::enabled[p->index] = false;
}
inline void uart_set_format(uart_inst_t*, unsigned, unsigned, unsigned) {}
inline void uart_set_hw_flow(uart_inst_t*, bool, bool) {}
inline void uart_set_irq_enables(uart_inst_t*, bool, bool) {}
inline bool uart_is_readable(uart_inst_t*) {
    return !gps_mock::receive.empty();
}
inline bool uart_is_writable(uart_inst_t*) {
    return gps_mock::writable;
}
inline uart_hw_t* uart_get_hw(uart_inst_t* p) {
    return &p->hw;
}
inline void gpio_init(unsigned p) {
    gps_mock::direction[p] = false;
    gps_mock::function[p] = GPIO_FUNC_SIO;
    gps_mock::check();
}
inline void gpio_set_dir(unsigned p, unsigned d) {
    gps_mock::direction[p] = d;
    gps_mock::check();
}
inline void gpio_set_function(unsigned p, unsigned f) {
    gps_mock::function[p] = f;
    gps_mock::check();
}
inline void gpio_set_oeover(unsigned p, unsigned v) {
    gps_mock::oeover[p] = v;
}
inline void gpio_set_inover(unsigned p, unsigned v) {
    gps_mock::inover[p] = v;
}
inline void hw_write_masked(std::uint32_t* p, std::uint32_t v, std::uint32_t mask) {
    *p = (*p & ~mask) | (v & mask);
    for (unsigned gp = 0; gp < 32; ++gp)
        if (p == &io_bank0_hw->io[gp].ctrl) {
            assert(gps_mock::oeover[gp] == GPIO_OVERRIDE_LOW && !gps_mock::direction[gp]);
            gps_mock::function[gp] = *p & 31;
        }
}
struct pwm_config {};
inline unsigned pwm_gpio_to_slice_num(unsigned gp) {
    return (gp >> 1) & 7;
}
inline unsigned pwm_gpio_to_channel(unsigned gp) {
    return gp & 1;
}
inline std::uint32_t clock_get_hz(unsigned clock) {
    return clock == clk_sys ? gps_mock::sys_hz : gps_mock::ref_hz;
}
inline pwm_config pwm_get_default_config() {
    return {};
}
inline void pwm_config_set_clkdiv_mode(pwm_config*, unsigned mode) {
    assert(mode == PWM_DIV_B_HIGH);
}
inline void pwm_config_set_clkdiv_int_frac4(pwm_config*, unsigned n, unsigned f) {
    assert(n == 255 && f == 15);
}
inline void pwm_init(unsigned s, pwm_config*, bool) {
    for (unsigned p = 0; p < 32; ++p)
        if (gps_mock::function[p] == GPIO_FUNC_PWM && pwm_gpio_to_slice_num(p) == s)
            gps_mock::pwm_pin[s] = p;
    pwm_hw->en &= ~(1u << s);
}
inline void pwm_set_irq_enabled(unsigned, bool) {}
inline void pwm_clear_irq(unsigned s) {
    pwm_hw->intr &= ~(1u << s);
}
inline void pwm_set_counter(unsigned s, unsigned n) {
    gps_mock::pwm_held[s] = n;
    gps_mock::pwm_start[s] = gps_mock::us;
}
inline unsigned pwm_get_counter(unsigned s) {
    return gps_mock::counter(s, gps_mock::us);
}
inline void pwm_set_enabled(unsigned s, bool v) {
    if (v)
        pwm_hw->en |= 1u << s;
    else
        pwm_hw->en &= ~(1u << s);
}
inline void gpio_disable_pulls(unsigned) {}
inline void gpio_set_input_enabled(unsigned p, bool v) {
    gps_mock::input[p] = v;
}
inline void gpio_set_irq_enabled(unsigned, unsigned, bool) {}
inline void gpio_add_raw_irq_handler(unsigned, void (*)()) {}
inline void gpio_remove_raw_irq_handler(unsigned, void (*)()) {}
inline unsigned gpio_get_irq_event_mask(unsigned p) {
    return gps_mock::flags[p];
}
inline void gpio_acknowledge_irq(unsigned p, unsigned f) {
    gps_mock::flags[p] &= ~f;
}
inline void irq_add_shared_handler(unsigned, void (*)(), unsigned) {}
inline void irq_remove_handler(unsigned, void (*)()) {}
inline void irq_set_enabled(unsigned, bool) {}
inline std::uint64_t time_us_64() {
    return gps_mock::us;
}
inline void tight_loop_contents() {
    gps_mock::us += 1000;
}

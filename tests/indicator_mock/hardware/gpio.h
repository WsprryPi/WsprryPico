#pragma once
constexpr bool GPIO_OUT = true;
void gpio_init(unsigned gp);
void gpio_put(unsigned gp, bool value);
void gpio_set_dir(unsigned gp, bool output);

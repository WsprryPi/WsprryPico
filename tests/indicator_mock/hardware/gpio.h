#pragma once
constexpr bool GPIO_OUT = true;
void gpio_init(unsigned gp);
void gpio_put(unsigned gp, bool value);
void gpio_set_dir(unsigned gp, bool output);
bool gpio_get(unsigned gp);
constexpr unsigned GPIO_FUNC_SIO = 5;
unsigned gpio_get_function(unsigned gp);
bool gpio_is_dir_out(unsigned gp);

#pragma once
struct cyw43_t {};
extern cyw43_t cyw43_state;
constexpr int CYW43_WL_GPIO_LED_PIN = 0;
int cyw43_gpio_set(cyw43_t* state, int pin, bool value);

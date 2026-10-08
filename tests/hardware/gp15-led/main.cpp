#include "pico/stdlib.h"

int main() {
    stdio_init_all(); // USB recovery only; no RF or Wi-Fi.
    gpio_init(15);
    gpio_put(15, true);
    gpio_set_dir(15, GPIO_OUT);
    for (;;)
        tight_loop_contents();
}

#include "rf/pico/pico_pio_dma.hpp"
// Link-only artifact: no GPIO initialization, DMA submission, alarm, or output.
int main() {
    static wsprrypico::rf::PicoPioDma hardware;
    static wsprrypico::rf::PioDmaSink sink(hardware);
    return hardware.release(0) && !sink.output_active() ? 0 : 1;
}

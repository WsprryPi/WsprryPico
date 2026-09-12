#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif
// Core-0/NO_SYS snapshot. Saturating counts; no payload or allocation in the driver.
void wsprry_cyw43_tx_diagnostics(uint32_t* waits, uint32_t* preserved, uint32_t* timeouts);
#ifdef __cplusplus
}
#endif

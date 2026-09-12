#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CONTROL_HEADER 0
#define DATA_HEADER 2
#define ASYNCEVENT_HEADER 1
#define SDPCM_HEADER_LEN 12
#define CYW43_EINVAL 22
#define CYW43_ETIMEDOUT 110
#define CYW43_FAIL_FAST_CHECK(x) (x)
#define CYW43_USE_SPI 1
#define CYW43_VDEBUG(...) ((void)0)
#define CYW43_WARN(...) ((void)0)
#define CYW43_SDPCM_SEND_COMMON_WAIT ((void)0)
#define CYW43_WRITE_BYTES_PAD(n) (((n) + 3) & ~3u)
#define WLAN_FUNCTION 2
#define CDCF_IOC_ID_MASK 0xffff0000u
#define WLC_SET_VAR 263
#define WLC_GET_VAR 262
#define CDCF_IOC_ID_SHIFT 16
#define CDCF_IOC_IF_SHIFT 12
#define CYW_INT_FROM_LL(x) (x)
typedef struct {
    _Alignas(4) uint8_t spid_buf[2048];
    uint8_t wlan_flow_control, wwd_sdpcm_last_bus_data_credit,
        wwd_sdpcm_packet_transmit_sequence_number;
    uint16_t wwd_sdpcm_requested_ioctl_id;
} cyw43_int_t;
typedef cyw43_int_t cyw43_ll_t;
static unsigned ticks, calls, polls;
static unsigned mode;
static uint8_t sent[4][2048];
static size_t sent_len[4];
static bool fail_bus;
int cyw43_ll_send_ethernet(cyw43_ll_t*, int, size_t, const void*, bool);
static int cyw43_ll_sdpcm_poll_device(cyw43_int_t* s, size_t* len, uint8_t** buf) {
    ++polls;
    memset(s->spid_buf, 0xa5, sizeof(s->spid_buf));
    if (mode != 3 && (mode != 2 || polls >= 3)) {
        s->wlan_flow_control = 0;
        s->wwd_sdpcm_last_bus_data_credit =
            (uint8_t)(s->wwd_sdpcm_packet_transmit_sequence_number + 1);
    }
    *len = 64;
    *buf = s->spid_buf;
    return mode == 4 ? ASYNCEVENT_HEADER : DATA_HEADER;
}
static unsigned cyw43_hal_ticks_us(void) {
    return ticks += 100;
}
static void cyw43_ll_bus_sleep(void* s, bool b) {
    (void)s;
    (void)b;
}
static void* cyw43_ll_parse_async_event(size_t n, uint8_t* b) {
    (void)n;
    return b;
}
static void cyw43_cb_process_async_event(cyw43_int_t* s, void* e) {
    (void)e;
    uint8_t inner[73];
    memset(inner, 0x72, sizeof(inner));
    mode = 1;
    assert(cyw43_ll_send_ethernet(s, 0, sizeof(inner), inner, false) == 0);
}
static int cyw43_write_bytes(cyw43_int_t* s, unsigned f, unsigned a, size_t n, const uint8_t* b) {
    (void)s;
    (void)f;
    (void)a;
    assert(calls < 4 && n <= 2048 && (uintptr_t)b % 4 == 0);
    memcpy(sent[calls], b, n);
    sent_len[calls] = n;
    ++calls;
    return fail_bus ? -5 : 0;
}
struct pbuf {
    const uint8_t* data;
};
static void pbuf_copy_partial(const struct pbuf* p, void* b, size_t n, unsigned o) {
    memcpy(b, p->data + o, n);
}

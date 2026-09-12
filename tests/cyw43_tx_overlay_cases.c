static void reset(cyw43_int_t* s, unsigned scenario) {
    memset(s, 0, sizeof(*s));
    memset(sent, 0, sizeof(sent));
    calls = polls = ticks = 0;
    fail_bus = false;
    mode = scenario;
    s->wwd_sdpcm_last_bus_data_credit = 1;
    if (scenario)
        s->wlan_flow_control = 1;
}
static void ethernet(unsigned scenario, bool chain, size_t length, bool wrap) {
    cyw43_int_t s;
    reset(&s, scenario);
    if (wrap) {
        s.wwd_sdpcm_packet_transmit_sequence_number = 255;
        s.wwd_sdpcm_last_bus_data_credit = 255;
    }
    uint8_t expected[2030];
    for (size_t i = 0; i < sizeof(expected); ++i)
        expected[i] = (uint8_t)(i * 17 + 39);
    struct pbuf p = {expected};
    int rc = cyw43_ll_send_ethernet(&s, 0, length, chain ? (void*)&p : (void*)expected, chain);
    if (scenario == 3) {
        assert(rc == -CYW43_ETIMEDOUT && calls == 0);
        return;
    }
    assert(rc == 0 && calls == (scenario == 4 ? 2u : 1u));
    unsigned last = calls - 1;
    bool equal = memcmp(sent[last] + 18, expected, length) == 0;
    assert(equal == (EXPECT_FIXED || !scenario));
    if (scenario == 4)
        for (unsigned i = 0; i < 73; ++i)
            assert(sent[0][18 + i] == 0x72);
    assert(sent_len[last] == CYW43_WRITE_BYTES_PAD(18 + length));
    if (wrap)
        assert(s.wwd_sdpcm_packet_transmit_sequence_number == 0);
}
int main(void) {
    ethernet(0, false, 341, false);
    ethernet(1, false, 341, false);
    ethernet(1, true, 341, false);
    ethernet(2, true, 1514, false);
    ethernet(1, false, 341, true);
    ethernet(3, false, 341, false);
    ethernet(4, false, 341, false);
    ethernet(1, false, 2030, false);
    cyw43_int_t s;
    reset(&s, 1);
    uint8_t expected[99];
    memset(expected, 0x31, sizeof(expected));
    // Control inputs may alias spid_buf before the command header is constructed.
    memcpy(s.spid_buf + 28, expected, sizeof(expected));
    assert(cyw43_send_ioctl(&s, 0, 42, sizeof(expected), s.spid_buf + 28, 0) == 0);
    assert((memcmp(sent[0] + 28, expected, sizeof(expected)) == 0) == EXPECT_FIXED);
    reset(&s, 0);
    fail_bus = true;
    assert(cyw43_ll_send_ethernet(&s, 0, sizeof(expected), expected, false) == -5 && calls == 1);
    reset(&s, 0);
    assert(cyw43_ll_send_ethernet(&s, 0, 2031, expected, false) == -CYW43_EINVAL && calls == 0);
#if EXPECT_FIXED
    uint32_t waits, preserved, timeouts;
    wsprry_cyw43_tx_diagnostics(&waits, &preserved, &timeouts);
    assert(waits >= 7 && preserved >= 6 && timeouts == 1);
    wsprry_tx_credit_waits = UINT32_MAX;
    ethernet(1, false, 341, false);
    wsprry_cyw43_tx_diagnostics(&waits, &preserved, &timeouts);
    assert(waits == UINT32_MAX);
    puts("FIXED: TX preserved across RX, nested callbacks, aliases and rollover; timeout/error "
         "semantics retained");
#else
    puts("REPRODUCED: original driver reports successful sends with corrupted Ethernet and control "
         "payloads");
#endif
    return 0;
}

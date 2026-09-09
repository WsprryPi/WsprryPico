#pragma once
#include <cstddef>
#include <cstdint>
using u16_t = std::uint16_t;
using err_t = int;
inline constexpr int ERR_OK = 0, ERR_ABRT = -1, ERR_MEM = -2;
inline constexpr int IPADDR_TYPE_V4 = 0, TCP_WRITE_FLAG_COPY = 1;
inline constexpr const void* IP_ANY_TYPE = nullptr;
struct pbuf {
    std::uint16_t tot_len;
    unsigned char* payload;
};
struct tcp_pcb {
    int fd = -1;
    void* arg = nullptr;
    err_t (*accept)(void*, tcp_pcb*, err_t) = nullptr;
    err_t (*receive)(void*, tcp_pcb*, pbuf*, err_t) = nullptr;
    err_t (*sent)(void*, tcp_pcb*, u16_t) = nullptr;
    unsigned pending = 0;
    bool hold_ack = false;
    void (*error)(void*, err_t) = nullptr;
};
tcp_pcb* tcp_new_ip_type(int);
err_t tcp_bind(tcp_pcb*, const void*, unsigned);
tcp_pcb* tcp_listen_with_backlog(tcp_pcb*, int);
void tcp_arg(tcp_pcb*, void*);
void tcp_accept(tcp_pcb*, err_t (*)(void*, tcp_pcb*, err_t));
void tcp_recv(tcp_pcb*, err_t (*)(void*, tcp_pcb*, pbuf*, err_t));
void tcp_err(tcp_pcb*, void (*)(void*, err_t));
void tcp_sent(tcp_pcb*, err_t (*)(void*, tcp_pcb*, u16_t));
void tcp_abort(tcp_pcb*);
err_t tcp_close(tcp_pcb*);
unsigned tcp_sndbuf(tcp_pcb*);
err_t tcp_write(tcp_pcb*, const void*, u16_t, int);
err_t tcp_output(tcp_pcb*);
void tcp_recved(tcp_pcb*, u16_t);
u16_t pbuf_copy_partial(const pbuf*, void*, u16_t, u16_t);
void pbuf_free(pbuf*);
void mock_tcp_poll();
void mock_tcp_hold_last_ack();
void mock_tcp_release_acks();
void mock_tcp_ack_and_close(bool reset);

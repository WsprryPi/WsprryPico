#pragma once
#include "lwip/tcp.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ssl.h"
#include "network/api.hpp"
#include "wtp/endpoint.hpp"

#include <array>

namespace wsprrypico::network {
// Foreground-only TLS. lwIP callbacks copy ciphertext; poll does bounded work.
class PicoServer {
  public:
    PicoServer(wtp::JobService& service, BrowserApi& api, std::string device, std::string firmware);
    bool start();
    void poll(bool link_up, std::string authority);
    bool listening() const {
        return listener_ != nullptr;
    }
    bool configured() const;
    int last_error() const {
        return last_error_;
    }
    static unsigned port();

  private:
    static err_t accept(void*, tcp_pcb*, err_t);
    static err_t receive(void*, tcp_pcb*, pbuf*, err_t);
    static void error(void*, err_t);
    static err_t sent(void*, tcp_pcb*, u16_t);
    static err_t pending_receive(void*, tcp_pcb*, pbuf*, err_t);
    static void pending_error(void*, err_t);
    void activate(tcp_pcb* pcb);
    static int send_tls(void*, const unsigned char*, std::size_t);
    static int receive_tls(void*, unsigned char*, std::size_t);
    void close();
    bool busy() const;
    wtp::JobService& service_;
    BrowserApi& api_;
    wtp::Endpoint endpoint_;
    tcp_pcb* listener_ = nullptr;
    tcp_pcb* client_ = nullptr;
    tcp_pcb* pending_ = nullptr;
    std::uint64_t pending_since_ms_ = 0;
    mbedtls_ssl_context ssl_{};
    mbedtls_ssl_config config_{};
    mbedtls_x509_crt cert_{}, ca_{};
    mbedtls_pk_context key_{};
    mbedtls_entropy_context entropy_{};
    mbedtls_ctr_drbg_context rng_{};
    std::array<std::uint8_t, 4096> rx_{};
    std::size_t rx_size_ = 0, pending_tcp_bytes_ = 0;
    std::array<std::uint8_t, 1024> plain_{};
    std::size_t plain_size_ = 0, plain_offset_ = 0;
    HttpParser http_;
    std::string response_, principal_;
    std::size_t response_offset_ = 0;
    std::uint64_t accepted_ms_ = 0, progress_ms_ = 0;
    int last_error_ = 0;
    bool setup_ = false, handshake_ = false, wtp_ = false, peer_closed_ = false, responded_ = false,
         close_notify_ = false;
};
} // namespace wsprrypico::network

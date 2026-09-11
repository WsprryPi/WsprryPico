#pragma once
#include "lwip/tcp.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ssl.h"
#include "network/api.hpp"
#include "wtp/endpoint.hpp"

#include <array>

namespace wsprrypico::network {
// Core-0-only TLS/lwIP/application owner. Physical waveform servicing is isolated.
class PicoServer {
  public:
    PicoServer(wtp::JobService&, BrowserApi&, std::string device, std::string firmware);
    ~PicoServer();
    PicoServer(const PicoServer&) = delete;
    PicoServer& operator=(const PicoServer&) = delete;
    bool start();
    void stop();
    void poll(bool link_up, std::string authority, bool allow_handshake_steps = true);
    bool listening() const {
        return listener_ != nullptr;
    }
    bool configured() const;
    int last_error() const {
        return last_error_;
    }
    static unsigned port();
    struct Metrics {
        std::uint64_t admitted = 0, rejected = 0, closed = 0, timeouts = 0;
        std::uint64_t max_handshake_us = 0, max_poll_us = 0;
        unsigned peak_active = 0;
    };
    const Metrics& metrics() const {
        return metrics_;
    }
    static std::size_t tls_allocated();
    static std::size_t tls_peak();
    static std::size_t tls_failures();

  private:
    struct Connection {
        Connection(PicoServer&, std::string device, std::string firmware);
        void activate(tcp_pcb*);
        void poll(std::string_view authority, bool allow_handshake_steps);
        void close(bool apply = false);
        static err_t receive(void*, tcp_pcb*, pbuf*, err_t);
        static void error(void*, err_t);
        static err_t sent(void*, tcp_pcb*, u16_t);
        static int send_tls(void*, const unsigned char*, std::size_t);
        static int receive_tls(void*, unsigned char*, std::size_t);
        PicoServer& owner_;
        wtp::JobService& service_;
        BrowserApi& api_;
        wtp::Endpoint endpoint_;
        std::uint64_t generation_ = 0;
        tcp_pcb* client_ = nullptr;
        mbedtls_ssl_context ssl_{};
        std::array<std::uint8_t, 4096> rx_{};
        std::size_t rx_size_ = 0, pending_tcp_bytes_ = 0;
        std::optional<std::size_t> response_tcp_remaining_;
        bool response_acknowledged() const {
            return response_tcp_remaining_ && *response_tcp_remaining_ == 0;
        }
        std::array<std::uint8_t, 1024> plain_{};
        std::size_t plain_size_ = 0, plain_offset_ = 0;
        HttpParser http_;
        std::string response_, principal_;
        std::size_t response_offset_ = 0;
        std::uint64_t accepted_ms_ = 0, progress_ms_ = 0;
        bool setup_ = false, handshake_ = false, wtp_ = false, peer_closed_ = false,
             responded_ = false, close_notify_ = false, handshake_failed_ = false;
    };
    static err_t accept(void*, tcp_pcb*, err_t);
    static err_t pending_receive(void*, tcp_pcb*, pbuf*, err_t);
    static void pending_error(void*, err_t);
    void close_pending();
    bool busy() const;
    wtp::JobService& service_;
    BrowserApi& api_;
    std::array<Connection, 2> connections_;
    tcp_pcb* listener_ = nullptr;
    tcp_pcb* pending_ = nullptr;
    std::uint64_t pending_since_ms_ = 0, generation_ = 0;
    std::size_t turn_ = 0;
    mbedtls_ssl_config config_{};
    mbedtls_x509_crt cert_{}, ca_{};
    mbedtls_pk_context key_{};
    mbedtls_entropy_context entropy_{};
    mbedtls_ctr_drbg_context rng_{};
    int last_error_ = 0;
    bool setup_ = false;
    Metrics metrics_{};
};
} // namespace wsprrypico::network

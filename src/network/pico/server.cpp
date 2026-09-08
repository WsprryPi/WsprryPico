#include "network/pico/server.hpp"

#include "mbedtls/platform.h"
#include "network_credentials.hpp"
#include "pico/time.h"
#include "psa/crypto.h"

#include <algorithm>
#include <cstring>

extern "C" mbedtls_ms_time_t mbedtls_ms_time(void) {
    return time_us_64() / 1000;
}

namespace wsprrypico::network {
namespace {
wtp::JobService* time_service = nullptr;
mbedtls_time_t tls_time(mbedtls_time_t* output) {
    const auto value =
        static_cast<mbedtls_time_t>(time_service->clock_snapshot().utc_now_ns / 1'000'000'000ULL);
    if (output)
        *output = value;
    return value;
}
bool retry(int result) {
    return result == MBEDTLS_ERR_SSL_WANT_READ || result == MBEDTLS_ERR_SSL_WANT_WRITE;
}
} // namespace
PicoServer::PicoServer(wtp::JobService& service, BrowserApi& api, std::string device,
                       std::string firmware)
    : service_(service), api_(api), endpoint_(service, std::move(device), std::move(firmware)) {}
unsigned PicoServer::port() {
    return credentials::port;
}
bool PicoServer::configured() const {
    return credentials::port != 0 && sizeof(credentials::certificate) > 1 &&
           sizeof(credentials::key) > 1 && sizeof(credentials::ca) > 1;
}
bool PicoServer::busy() const {
    const auto state = service_.status().state;
    return !service_.config().capability_engine.starts_with("inhibited-") &&
           (state == wtp::State::Armed || state == wtp::State::Running);
}
bool PicoServer::start() {
    if (!configured() || setup_)
        return false;
    setup_ = true;
    time_service = &service_;
    mbedtls_platform_set_time(tls_time);
    mbedtls_ssl_init(&ssl_);
    mbedtls_ssl_config_init(&config_);
    mbedtls_x509_crt_init(&cert_);
    mbedtls_x509_crt_init(&ca_);
    mbedtls_pk_init(&key_);
    mbedtls_entropy_init(&entropy_);
    mbedtls_ctr_drbg_init(&rng_);
    const unsigned char personalization[] = "WsprryPico TLS server";
    auto check = [this](int result) {
        last_error_ = result;
        return result != 0;
    };
    if (check(psa_crypto_init()) ||
        check(mbedtls_ctr_drbg_seed(&rng_, mbedtls_entropy_func, &entropy_, personalization,
                                    sizeof(personalization))) ||
        check(mbedtls_x509_crt_parse(
            &cert_, reinterpret_cast<const unsigned char*>(credentials::certificate),
            sizeof(credentials::certificate))) ||
        check(mbedtls_x509_crt_parse(&ca_, reinterpret_cast<const unsigned char*>(credentials::ca),
                                     sizeof(credentials::ca))) ||
        check(mbedtls_pk_parse_key(&key_, reinterpret_cast<const unsigned char*>(credentials::key),
                                   sizeof(credentials::key), nullptr, 0, mbedtls_ctr_drbg_random,
                                   &rng_)) ||
        check(mbedtls_pk_check_pair(&cert_.pk, &key_, mbedtls_ctr_drbg_random, &rng_)) ||
        check(mbedtls_ssl_config_defaults(&config_, MBEDTLS_SSL_IS_SERVER,
                                          MBEDTLS_SSL_TRANSPORT_STREAM,
                                          MBEDTLS_SSL_PRESET_DEFAULT)))
        return false;
    mbedtls_ssl_conf_min_tls_version(&config_, MBEDTLS_SSL_VERSION_TLS1_3);
    mbedtls_ssl_conf_max_tls_version(&config_, MBEDTLS_SSL_VERSION_TLS1_3);
    mbedtls_ssl_conf_authmode(&config_, MBEDTLS_SSL_VERIFY_REQUIRED);
    mbedtls_ssl_conf_rng(&config_, mbedtls_ctr_drbg_random, &rng_);
    mbedtls_ssl_conf_ca_chain(&config_, &ca_, nullptr);
    static const char* protocols[] = {"wtp/1", "http/1.1", nullptr};
    if (check(mbedtls_ssl_conf_alpn_protocols(&config_, protocols)) ||
        check(mbedtls_ssl_conf_own_cert(&config_, &cert_, &key_)) ||
        check(mbedtls_ssl_setup(&ssl_, &config_)))
        return false;
    auto* pcb = tcp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb) {
        last_error_ = -1;
        return false;
    }
    if ((last_error_ = tcp_bind(pcb, IP_ANY_TYPE, credentials::port)) != ERR_OK) {
        tcp_abort(pcb);
        return false;
    }
    listener_ = tcp_listen_with_backlog(pcb, 1);
    if (!listener_) {
        last_error_ = -2;
        tcp_abort(pcb);
        return false;
    }
    tcp_arg(listener_, this);
    tcp_accept(listener_, accept);
    return true;
}
err_t PicoServer::accept(void* context, tcp_pcb* pcb, err_t err) {
    auto& self = *static_cast<PicoServer*>(context);
    const auto clock = self.service_.clock_snapshot();
    if (err != ERR_OK || self.pending_ || self.busy() ||
        clock.state == wtp::ClockState::Unsynchronized || clock.utc_now_ns == 0) {
        tcp_abort(pcb);
        return ERR_ABRT;
    }
    if (self.client_) {
        self.pending_ = pcb;
        self.pending_since_ms_ = time_us_64() / 1000;
        tcp_arg(pcb, &self);
        tcp_recv(pcb, pending_receive);
        tcp_err(pcb, pending_error);
    } else
        self.activate(pcb);
    return ERR_OK;
}
void PicoServer::activate(tcp_pcb* pcb) {
    client_ = pcb;
    accepted_ms_ = progress_ms_ = time_us_64() / 1000;
    tcp_arg(pcb, this);
    tcp_recv(pcb, receive);
    tcp_err(pcb, error);
    tcp_sent(pcb, sent);
}
err_t PicoServer::pending_receive(void* context, tcp_pcb* pcb, pbuf* packet, err_t) {
    if (packet)
        return ERR_MEM; // lwIP retains bounded receive-window data until promotion.
    auto& self = *static_cast<PicoServer*>(context);
    self.pending_ = nullptr;
    tcp_abort(pcb);
    return ERR_ABRT;
}
void PicoServer::pending_error(void* context, err_t) {
    static_cast<PicoServer*>(context)->pending_ = nullptr;
}
err_t PicoServer::receive(void* context, tcp_pcb*, pbuf* packet, err_t err) {
    auto& self = *static_cast<PicoServer*>(context);
    if (!packet) {
        self.peer_closed_ = true;
        return ERR_OK;
    }
    if (err != ERR_OK) {
        pbuf_free(packet);
        self.peer_closed_ = true;
        return ERR_OK;
    }
    if (packet->tot_len > self.rx_.size() - self.rx_size_)
        return ERR_MEM;
    const auto copied =
        pbuf_copy_partial(packet, self.rx_.data() + self.rx_size_, packet->tot_len, 0);
    self.rx_size_ += copied;
    pbuf_free(packet);
    return ERR_OK;
}
err_t PicoServer::sent(void* context, tcp_pcb*, u16_t bytes) {
    auto& self = *static_cast<PicoServer*>(context);
    self.pending_tcp_bytes_ -= std::min<std::size_t>(bytes, self.pending_tcp_bytes_);
    return ERR_OK;
}
void PicoServer::error(void* context, err_t) {
    auto& self = *static_cast<PicoServer*>(context);
    self.client_ = nullptr;
    self.peer_closed_ = true;
}
int PicoServer::send_tls(void* context, const unsigned char* bytes, std::size_t count) {
    auto& self = *static_cast<PicoServer*>(context);
    if (!self.client_)
        return MBEDTLS_ERR_SSL_INTERNAL_ERROR;
    const auto n = std::min<std::size_t>(tcp_sndbuf(self.client_), count);
    if (!n)
        return MBEDTLS_ERR_SSL_WANT_WRITE;
    const auto result = tcp_write(self.client_, bytes, static_cast<u16_t>(n), TCP_WRITE_FLAG_COPY);
    if (result == ERR_MEM)
        return MBEDTLS_ERR_SSL_WANT_WRITE;
    if (result != ERR_OK)
        return MBEDTLS_ERR_SSL_INTERNAL_ERROR;
    self.pending_tcp_bytes_ += n;
    (void)tcp_output(self.client_);
    return static_cast<int>(n);
}
int PicoServer::receive_tls(void* context, unsigned char* bytes, std::size_t count) {
    auto& self = *static_cast<PicoServer*>(context);
    if (!self.rx_size_)
        return MBEDTLS_ERR_SSL_WANT_READ;
    const auto n = std::min(count, self.rx_size_);
    std::memcpy(bytes, self.rx_.data(), n);
    self.rx_size_ -= n;
    std::memmove(self.rx_.data(), self.rx_.data() + n, self.rx_size_);
    if (self.client_)
        tcp_recved(self.client_, static_cast<u16_t>(n));
    return static_cast<int>(n);
}
void PicoServer::close() {
    if (client_) {
        tcp_arg(client_, nullptr);
        tcp_recv(client_, nullptr);
        tcp_err(client_, nullptr);
        tcp_sent(client_, nullptr);
        // Normal completed HTTP responses are copied into lwIP before FIN.
        if (responded_ && response_offset_ == response_.size()) {
            if (tcp_close(client_) != ERR_OK)
                tcp_abort(client_);
        } else
            tcp_abort(client_);
    }
    client_ = nullptr;
    if (setup_)
        (void)mbedtls_ssl_session_reset(&ssl_);
    endpoint_.disconnect();
    pending_tcp_bytes_ = 0;
    api_.finish_request();
    rx_size_ = plain_size_ = plain_offset_ = response_offset_ = 0;
    response_.clear();
    principal_.clear();
    http_ = HttpParser{};
    handshake_ = wtp_ = peer_closed_ = responded_ = close_notify_ = false;
}
void PicoServer::poll(bool link_up, std::string authority) {
    service_.poll();
    const auto pending_now = time_us_64() / 1000;
    if (pending_ && (!link_up || busy() || pending_now - pending_since_ms_ >= 10000)) {
        tcp_arg(pending_, nullptr);
        tcp_err(pending_, nullptr);
        tcp_recv(pending_, nullptr);
        tcp_abort(pending_);
        pending_ = nullptr;
    }
    if (peer_closed_ || (!link_up && client_)) {
        close();
        return;
    }
    if (!client_ && pending_) {
        auto* next = pending_;
        pending_ = nullptr;
        activate(next);
    }
    if (!client_)
        return;
    const auto now = time_us_64() / 1000;
    if ((!handshake_ && (busy() || now - accepted_ms_ >= 10000)) ||
        (handshake_ && !wtp_ && now - accepted_ms_ >= 15000) || now - progress_ms_ >= 30000) {
        close();
        return;
    }
    if (!handshake_) {
        mbedtls_ssl_set_bio(&ssl_, this, send_tls, receive_tls, nullptr);
        const auto result = mbedtls_ssl_handshake_step(&ssl_);
        service_.poll();
        if (result && !retry(result)) {
            close();
            return;
        }
        if (!mbedtls_ssl_is_handshake_over(&ssl_))
            return;
        const auto* peer = mbedtls_ssl_get_peer_cert(&ssl_);
        const auto* protocol = mbedtls_ssl_get_alpn_protocol(&ssl_);
        if (!peer || mbedtls_ssl_get_verify_result(&ssl_) || !protocol ||
            (std::strcmp(protocol, "wtp/1") && std::strcmp(protocol, "http/1.1"))) {
            close();
            return;
        }
        const auto digest = wtp::sha256(std::span(peer->raw.p, peer->raw.len));
        principal_ = "tls-cert:";
        for (auto b : digest) {
            principal_ += "0123456789abcdef"[b >> 4];
            principal_ += "0123456789abcdef"[b & 15];
        }
        wtp_ = std::strcmp(protocol, "wtp/1") == 0;
        if (wtp_)
            endpoint_.connect(principal_);
        handshake_ = true;
        progress_ms_ = now;
        return;
    }
    if (wtp_) {
        endpoint_.poll(now);
        if (endpoint_.closed()) {
            close();
            return;
        }
    }
    auto output =
        wtp_ ? endpoint_.output()
             : std::span(reinterpret_cast<const std::uint8_t*>(response_.data() + response_offset_),
                         response_.size() - response_offset_);
    if (!output.empty()) {
        const auto result =
            mbedtls_ssl_write(&ssl_, output.data(), std::min<std::size_t>(output.size(), 1024));
        service_.poll();
        if (result > 0) {
            progress_ms_ = now;
            if (wtp_)
                endpoint_.consume_output(static_cast<std::size_t>(result), now);
            else
                response_offset_ += static_cast<std::size_t>(result);
        } else if (!retry(result))
            close();
        return;
    }
    if (!wtp_ && responded_) {
        if (!close_notify_) {
            const auto result = mbedtls_ssl_close_notify(&ssl_);
            if (result == 0)
                close_notify_ = true;
            else if (!retry(result))
                close();
        } else if (pending_tcp_bytes_ == 0)
            close();
        return;
    }
    if (wtp_ && !endpoint_.can_receive())
        return;
    if (plain_size_ == plain_offset_) {
        const auto result = mbedtls_ssl_read(&ssl_, plain_.data(), plain_.size());
        service_.poll();
        if (result <= 0) {
            if (!retry(result))
                close();
            return;
        }
        plain_size_ = static_cast<std::size_t>(result);
        plain_offset_ = 0;
        progress_ms_ = now;
    }
    const auto bytes = std::span(plain_).subspan(plain_offset_, plain_size_ - plain_offset_);
    if (wtp_)
        plain_offset_ += endpoint_.receive(bytes, now);
    else {
        plain_offset_ += http_.receive(bytes);
        if (http_.failed() || http_.ready()) {
            response_ = (http_.failed() ? http_error(400, "invalid_http")
                                        : api_.handle(http_.request(), principal_, authority))
                            .wire();
            responded_ = true;
        }
    }
    service_.poll();
}
} // namespace wsprrypico::network

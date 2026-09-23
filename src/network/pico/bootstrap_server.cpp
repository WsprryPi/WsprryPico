#include "network/pico/bootstrap_server.hpp"

#include "pico/time.h"
#include "wtp/json.hpp"

#include <algorithm>

namespace wsprrypico::network {
PicoBootstrapServer::~PicoBootstrapServer() {
    stop();
}

bool PicoBootstrapServer::start() {
    if (listener_ || !classifier_ || device_.empty())
        return false;
    auto* pcb = tcp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb)
        return false;
    if (tcp_bind(pcb, IP_ANY_TYPE, 80) != ERR_OK) {
        tcp_abort(pcb);
        return false;
    }
    listener_ = tcp_listen_with_backlog(pcb, 1);
    if (!listener_) {
        tcp_abort(pcb);
        return false;
    }
    tcp_arg(listener_, this);
    tcp_accept(listener_, accept);
    return true;
}

err_t PicoBootstrapServer::accept(void* context, tcp_pcb* pcb, err_t err) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
    if (err != ERR_OK || !self.active_ || self.client_ ||
        !self.classifier_(pcb, self.classifier_context_)) {
        tcp_abort(pcb);
        return ERR_ABRT;
    }
    self.client_ = pcb;
    self.accepted_ms_ = time_us_64() / 1000;
    tcp_arg(pcb, &self);
    tcp_recv(pcb, receive);
    tcp_sent(pcb, sent);
    tcp_err(pcb, error);
    return ERR_OK;
}

err_t PicoBootstrapServer::receive(void* context, tcp_pcb*, pbuf* packet, err_t err) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
    if (!packet || err != ERR_OK) {
        if (packet)
            pbuf_free(packet);
        self.close();
        return ERR_ABRT;
    }
    std::array<std::uint8_t, 1024> bytes{};
    if (packet->tot_len > bytes.size())
        return ERR_MEM;
    const auto count = pbuf_copy_partial(packet, bytes.data(), packet->tot_len, 0);
    pbuf_free(packet);
    tcp_recved(self.client_, count);
    (void)self.parser_.receive(std::span(bytes).first(count));
    if (self.parser_.failed() || self.parser_.ready())
        self.dispatch();
    return ERR_OK;
}

err_t PicoBootstrapServer::sent(void* context, tcp_pcb*, u16_t count) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
    self.pending_bytes_ -= std::min<std::size_t>(count, self.pending_bytes_);
    return ERR_OK;
}

void PicoBootstrapServer::error(void* context, err_t) {
    auto& self = *static_cast<PicoBootstrapServer*>(context);
    self.client_ = nullptr;
    self.parser_.reset_secure();
    self.parser_ = {};
    self.wire_.clear();
    self.output_offset_ = self.pending_bytes_ = 0;
}

void PicoBootstrapServer::dispatch() {
    HttpResponse response;
    if (parser_.failed())
        response = http_error(400, "invalid_http");
    else if (parser_.request().method != "GET")
        response = http_error(405, "read_only");
    else if (parser_.request().path == "/local/v1/identity")
        response = {200,
                    "{\"version\":1,\"device_id\":" + wtp::json::quote(device_) +
                        ",\"firmware\":" + wtp::json::quote(firmware_) +
                        ",\"surface\":\"blank_read_only\",\"authenticated\":false}",
                    "application/json",
                    {}};
    else if (parser_.request().path == "/")
        response = {200,
                    "<!doctype html><meta charset=utf-8><meta name=viewport "
                    "content=\"width=device-width,initial-scale=1\"><title>WsprryPico "
                    "recovery</title><h1>WsprryPico recovery</h1><p>This device has no "
                    "authenticated server identity. This page is read-only. Provision it over "
                    "encrypted BLE or USB before entering any credential.</p><p>Device: <code>" +
                        device_ + "</code></p><p>Firmware: <code>" + firmware_ + "</code></p>",
                    "text/html; charset=utf-8",
                    {}};
    else
        response = http_error(404, "not_found");
    wire_ = response.wire();
}

void PicoBootstrapServer::close() {
    if (client_) {
        tcp_arg(client_, nullptr);
        tcp_recv(client_, nullptr);
        tcp_sent(client_, nullptr);
        tcp_err(client_, nullptr);
        tcp_abort(client_);
    }
    client_ = nullptr;
    parser_.reset_secure();
    parser_ = {};
    wire_.clear();
    output_offset_ = pending_bytes_ = 0;
}

void PicoBootstrapServer::stop() {
    close();
    if (listener_) {
        tcp_arg(listener_, nullptr);
        tcp_accept(listener_, nullptr);
        tcp_abort(listener_);
        listener_ = nullptr;
    }
}

void PicoBootstrapServer::poll(bool active) {
    active_ = active;
    if (!active_) {
        close();
        return;
    }
    if (!client_)
        return;
    if (time_us_64() / 1000 - accepted_ms_ >= 10'000) {
        close();
        return;
    }
    if (wire_.empty())
        return;
    if (output_offset_ < wire_.size()) {
        const auto count =
            std::min<std::size_t>({wire_.size() - output_offset_, tcp_sndbuf(client_), 1024});
        if (!count)
            return;
        const auto result = tcp_write(client_, wire_.data() + output_offset_,
                                      static_cast<u16_t>(count), TCP_WRITE_FLAG_COPY);
        if (result == ERR_MEM)
            return;
        if (result != ERR_OK) {
            close();
            return;
        }
        output_offset_ += count;
        pending_bytes_ += count;
        (void)tcp_output(client_);
    } else if (!pending_bytes_) {
        auto* completed = client_;
        client_ = nullptr;
        tcp_arg(completed, nullptr);
        tcp_recv(completed, nullptr);
        tcp_sent(completed, nullptr);
        tcp_err(completed, nullptr);
        if (tcp_close(completed) != ERR_OK)
            tcp_abort(completed);
        parser_.reset_secure();
        parser_ = {};
        wire_.clear();
        output_offset_ = 0;
    }
}

} // namespace wsprrypico::network

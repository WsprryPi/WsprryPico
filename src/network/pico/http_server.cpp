#include "network/pico/http_server.hpp"

#include "pico/time.h"
#include "wtp/memory_budget.hpp"

#include <algorithm>
#include <limits>

namespace wsprrypico::network {

PicoHttpServer::~PicoHttpServer() {
    stop();
}

bool PicoHttpServer::start() {
    if (listener_ || !classify_ || !handle_)
        return false;
    auto* pcb = tcp_new_ip_type(IPADDR_TYPE_V4);
    if (!pcb)
        return false;
    if (tcp_bind(pcb, IP_ANY_TYPE, 80) != ERR_OK) {
        tcp_abort(pcb);
        return false;
    }
    listener_ = tcp_listen_with_backlog(pcb, capacity);
    if (!listener_) {
        tcp_abort(pcb);
        return false;
    }
    tcp_arg(listener_, this);
    tcp_accept(listener_, accept);
    return true;
}

err_t PicoHttpServer::accept(void* context, tcp_pcb* pcb, err_t err) {
    auto& self = *static_cast<PicoHttpServer*>(context);
    if (!pcb)
        return ERR_ABRT;
    if (err != ERR_OK) {
        tcp_abort(pcb);
        return ERR_ABRT;
    }
    auto slot = std::find_if(self.clients_.begin(), self.clients_.end(),
                             [](const Client& client) { return !client.pcb; });
    const auto interface = self.classify_(self.context_, pcb, true);
    if (interface == ConsumerInterface::None || slot == self.clients_.end() ||
        self.next_transaction_ == std::numeric_limits<std::uint64_t>::max()) {
        tcp_abort(pcb);
        return ERR_ABRT;
    }
    slot->owner = &self;
    slot->pcb = pcb;
    slot->interface = interface;
    slot->transaction = self.next_transaction_++;
    slot->accepted_ms = time_us_64() / 1000;
    tcp_arg(pcb, &*slot);
    tcp_recv(pcb, receive);
    tcp_sent(pcb, sent);
    tcp_err(pcb, error);
    return ERR_OK;
}

err_t PicoHttpServer::receive(void* context, tcp_pcb* pcb, pbuf* packet, err_t err) {
    auto& client = *static_cast<Client*>(context);
    auto& self = *client.owner;
    if (!packet || err != ERR_OK || client.dispatched) {
        if (packet)
            pbuf_free(packet);
        const bool success = delivered(client);
        return self.close(client, success) ? ERR_ABRT : ERR_OK;
    }
    // Header maps and string growth precede HttpParser's body admission gate.
    // Check each header fragment against shared heap state, since another task
    // may have allocated since accept. Reserved body pages need no new growth.
    if (!client.parser.headers_complete() && !wtp::memory_admitted(header_workspace)) {
        pbuf_free(packet);
        self.close(client, false);
        return ERR_ABRT;
    }
    std::array<std::uint8_t, output_chunk> bytes{};
    const auto total = packet->tot_len;
    std::size_t offset = 0;
    while (offset < total && !client.parser.failed() && !client.parser.ready()) {
        const auto wanted = std::min<std::size_t>(bytes.size(), total - offset);
        const auto count = pbuf_copy_partial(packet, bytes.data(), wanted, offset);
        if (count != wanted) {
            pbuf_free(packet);
            self.close(client, false);
            return ERR_ABRT;
        }
        const auto used = client.parser.receive(std::span(bytes).first(count));
        offset += used;
        if (used != count)
            break;
    }
    pbuf_free(packet);
    if (offset != total && !client.parser.failed()) {
        self.close(client, false); // One request; do not dispatch a pipelined prefix.
        return ERR_ABRT;
    }
    tcp_recved(pcb, total);
    return ERR_OK;
}

err_t PicoHttpServer::sent(void* context, tcp_pcb*, u16_t count) {
    auto& client = *static_cast<Client*>(context);
    client.pending -= std::min<std::size_t>(count, client.pending);
    return ERR_OK;
}

void PicoHttpServer::error(void* context, err_t) {
    auto& client = *static_cast<Client*>(context);
    // lwIP already freed the PCB. ACK state, never a peer FIN/RST, proves delivery.
    client.owner->close(client, delivered(client), true);
}

bool PicoHttpServer::delivered(const Client& client) {
    return client.dispatched && client.header_offset == client.headers.size() &&
           client.body_offset == client.response.body_size() && !client.pending;
}

bool PicoHttpServer::close(Client& client, bool success, bool freed) {
    bool aborted = false;
    const auto transaction = client.transaction;
    if (client.pcb && !freed) {
        tcp_arg(client.pcb, nullptr);
        tcp_recv(client.pcb, nullptr);
        tcp_sent(client.pcb, nullptr);
        tcp_err(client.pcb, nullptr);
        if (!success || tcp_close(client.pcb) != ERR_OK) {
            tcp_abort(client.pcb);
            aborted = true;
        }
    }
    client.pcb = nullptr;
    client.parser.reset_secure();
    client.parser = {};
    client.response.reset();
    std::string{}.swap(client.headers);
    client.header_offset = client.body_offset = client.pending = 0;
    client.dispatched = false;
    client.interface = ConsumerInterface::None;
    client.transaction = client.accepted_ms = 0;
    // Clear all per-client storage before application callbacks or slot reuse.
    if (transaction && finish_)
        finish_(context_, transaction, success);
    return aborted;
}

void PicoHttpServer::step(Client& client, std::uint64_t now) {
    if (!client.pcb)
        return;
    if (classify_(context_, client.pcb, false) != client.interface ||
        now - client.accepted_ms >= lifetime_ms) {
        close(client, delivered(client));
        return;
    }
    if (!client.dispatched) {
        if (!client.parser.ready() && !client.parser.failed())
            return;
        client.response = client.parser.failed() ? http_error(400, "invalid_http")
                                                 : handle_(context_, client.parser.request(),
                                                           client.interface, client.transaction);
        client.headers = client.response.wire_headers();
        client.dispatched = true;
    }
    if (delivered(client)) {
        close(client, true);
        return;
    }
    const bool header = client.header_offset < client.headers.size();
    const auto body =
        header ? std::span<const std::uint8_t>{} : client.response.body_at(client.body_offset);
    const auto* data = header ? client.headers.data() + client.header_offset
                              : reinterpret_cast<const char*>(body.data());
    const auto remaining = header ? client.headers.size() - client.header_offset : body.size();
    const auto count = std::min<std::size_t>({remaining, tcp_sndbuf(client.pcb), output_chunk});
    if (!count)
        return;
    const auto result = tcp_write(client.pcb, data, static_cast<u16_t>(count), TCP_WRITE_FLAG_COPY);
    if (result == ERR_MEM)
        return;
    if (result != ERR_OK) {
        close(client, false);
        return;
    }
    (header ? client.header_offset : client.body_offset) += count;
    client.pending += count;
    (void)tcp_output(client.pcb);
}

void PicoHttpServer::poll() {
    const auto now = time_us_64() / 1000;
    for (std::size_t i = 0; i < capacity; ++i)
        step(clients_[(first_ + i) % capacity], now);
    first_ = (first_ + 1) % capacity;
}

void PicoHttpServer::withdraw(ConsumerInterface interface) {
    for (auto& client : clients_)
        if (client.pcb && client.interface == interface)
            close(client, delivered(client));
}

void PicoHttpServer::stop() {
    for (auto& client : clients_)
        if (client.pcb)
            close(client, delivered(client));
    if (listener_) {
        tcp_arg(listener_, nullptr);
        tcp_accept(listener_, nullptr);
        const auto closed = tcp_close(listener_);
        LWIP_ASSERT("HTTP listener close must succeed", closed == ERR_OK);
        listener_ = nullptr;
    }
}

std::size_t PicoHttpServer::connections() const {
    return std::count_if(clients_.begin(), clients_.end(),
                         [](const Client& client) { return client.pcb; });
}
std::size_t PicoHttpServer::pending_bytes() const {
    std::size_t result = 0;
    for (const auto& client : clients_)
        result += client.pending;
    return result;
}
bool PicoHttpServer::reply_active() const {
    return std::any_of(clients_.begin(), clients_.end(),
                       [](const Client& client) { return client.pcb && client.dispatched; });
}

} // namespace wsprrypico::network

#include "lwip/tcp.h"

#include "pico/time.h"

#include <algorithm>
#include <arpa/inet.h>
#include <array>
#include <cerrno>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <netinet/in.h>
#include <random>
#include <sys/socket.h>
#include <unistd.h>
#include <vector>
static std::vector<tcp_pcb*> listeners;
static std::vector<tcp_pcb*> clients;
static bool fragment_writes = false, block_write = false, hold_next_ack = false;
static bool hold_next_handshake_ack = false;
void mock_tcp_hold_next_handshake_ack() {
    hold_next_handshake_ack = true;
}
void mock_tcp_hold_next_ack() {
    hold_next_ack = true;
}
tcp_pcb* mock_tcp_pending_burst(unsigned& refused) {
    // Two segments arrive in one network poll, before foreground TLS setup.
    // Pinned lwIP retains an ERR_MEM packet and drops later data while it is
    // still refused (tcp_in.c). Count refusal without hiding it behind the
    // host kernel's automatic TCP acknowledgement/retransmission behavior.
    assert(!listeners.empty());
    auto* pcb = tcp_new_ip_type(IPADDR_TYPE_V4);
    clients.push_back(pcb);
    assert(listeners.front()->accept(listeners.front()->arg, pcb, ERR_OK) == ERR_OK);
    refused = 0;
    for (u16_t bytes : {1460, 47}) {
        auto* packet = new pbuf{bytes, new unsigned char[bytes]{}};
        const auto result = pcb->receive(pcb->arg, pcb, packet, ERR_OK);
        assert(result == ERR_OK || result == ERR_MEM);
        if (result == ERR_MEM) {
            ++refused;
            pbuf_free(packet);
        }
    }
    return pcb;
}
void mock_tcp_pending_disconnect(tcp_pcb* pcb, bool reset) {
    if (reset) {
        const auto callback = pcb->error;
        auto* context = pcb->arg;
        tcp_abort(pcb);
        callback(context, ERR_ABRT);
    } else
        assert(pcb->receive(pcb->arg, pcb, nullptr, ERR_OK) == ERR_ABRT);
}
void mock_tcp_fragment_writes(bool enabled) {
    fragment_writes = enabled;
    block_write = false;
}
std::uint64_t time_us_64() {
    static const auto origin = std::chrono::steady_clock::now();
    static const auto scale =
        std::getenv("WSPRRY_NETWORK_TEST_TIME_SCALE")
            ? std::strtoul(std::getenv("WSPRRY_NETWORK_TEST_TIME_SCALE"), nullptr, 10)
            : 1;
    return std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() -
                                                                 origin)
               .count() *
           scale;
}
extern "C" int mbedtls_hardware_poll(void*, unsigned char* output, std::size_t count,
                                     std::size_t* used) {
    std::random_device random;
    for (std::size_t i = 0; i < count; ++i)
        output[i] = static_cast<unsigned char>(random());
    *used = count;
    return 0;
}
tcp_pcb* tcp_new_ip_type(int) {
    auto* pcb = new tcp_pcb;
    pcb->fd = socket(AF_INET, SOCK_STREAM, 0);
    fcntl(pcb->fd, F_SETFL, O_NONBLOCK);
    int yes = 1;
    setsockopt(pcb->fd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    return pcb;
}
err_t tcp_bind(tcp_pcb* pcb, const void*, unsigned port) {
    sockaddr_in address{};
    address.sin_family = AF_INET;
    const auto* selected = std::getenv("WSPRRY_TEST_LISTEN_ADDRESS");
    if (selected && std::strcmp(selected, "127.0.0.1") && std::strcmp(selected, "127.0.0.2"))
        return ERR_ABRT;
    if (inet_pton(AF_INET, selected ? selected : "127.0.0.1", &address.sin_addr) != 1)
        return ERR_ABRT;
    address.sin_port = htons(port);
    return bind(pcb->fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) ? ERR_ABRT
                                                                                 : ERR_OK;
}
tcp_pcb* tcp_listen_with_backlog(tcp_pcb* pcb, int backlog) {
    if (listen(pcb->fd, backlog))
        return nullptr;
    listeners.push_back(pcb);
    return pcb;
}
void tcp_arg(tcp_pcb* p, void* a) {
    p->arg = a;
}
void tcp_accept(tcp_pcb* p, err_t (*f)(void*, tcp_pcb*, err_t)) {
    p->accept = f;
}
void tcp_recv(tcp_pcb* p, err_t (*f)(void*, tcp_pcb*, pbuf*, err_t)) {
    p->receive = f;
}
void tcp_err(tcp_pcb* p, void (*f)(void*, err_t)) {
    p->error = f;
}
void tcp_sent(tcp_pcb* p, err_t (*f)(void*, tcp_pcb*, u16_t)) {
    p->sent = f;
}
void tcp_nagle_disable(tcp_pcb* p) {
    p->nagle_disabled = true;
}
void tcp_abort(tcp_pcb* p) {
    listeners.erase(std::remove(listeners.begin(), listeners.end(), p), listeners.end());
    close(p->fd);
    clients.erase(std::remove(clients.begin(), clients.end(), p), clients.end());
    delete p;
}
err_t tcp_close(tcp_pcb* p) {
    tcp_abort(p);
    return ERR_OK;
}
unsigned tcp_sndbuf(tcp_pcb*) {
    return fragment_writes ? 7 : 1024;
}
err_t tcp_write(tcp_pcb* p, const void* b, u16_t n, int) {
    if (fragment_writes) {
        block_write = !block_write;
        if (block_write)
            return ERR_MEM;
    }
    if (p->model_nagle) {
        const auto* bytes = static_cast<const unsigned char*>(b);
        p->unsent.insert(p->unsent.end(), bytes, bytes + n);
        return ERR_OK;
    }
    // Small writes on the local socket are atomic in this bounded test adapter.
    const auto sent = send(p->fd, b, n, 0);
    if (sent == n)
        p->pending += n;
    return sent == n                                                 ? ERR_OK
           : (sent < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) ? ERR_MEM
                                                                     : ERR_ABRT;
}
err_t tcp_output(tcp_pcb* p) {
    if (p->model_nagle && !p->unsent.empty()) {
        // Pinned lwIP tcp_do_output_nagle(): one short unsent segment is
        // held while another is unacked unless TF_NODELAY is set. Hold the
        // first-flight ACK until the client can send its authentication.
        if (p->pending && !p->nagle_disabled && p->unsent.size() < 1460)
            return ERR_OK;
        const auto n = send(p->fd, p->unsent.data(), p->unsent.size(), 0);
        if (n < 0)
            return errno == EAGAIN || errno == EWOULDBLOCK ? ERR_MEM : ERR_ABRT;
        p->pending += static_cast<unsigned>(n);
        p->unsent.erase(p->unsent.begin(), p->unsent.begin() + n);
    }
    return ERR_OK;
}
void tcp_recved(tcp_pcb*, u16_t) {}
u16_t pbuf_copy_partial(const pbuf* p, void* dest, u16_t n, u16_t offset) {
    n = std::min<u16_t>(n, p->tot_len - offset);
    std::memcpy(dest, p->payload + offset, n);
    return n;
}
void pbuf_free(pbuf* p) {
    delete[] p->payload;
    delete p;
}
void mock_tcp_hold_last_ack() {
    if (!clients.empty())
        clients.back()->hold_ack = true;
}
void mock_tcp_release_acks() {
    for (auto* pcb : clients)
        pcb->hold_ack = false;
}
void mock_tcp_ack_and_close(bool reset) {
    if (clients.empty())
        return;
    auto* pcb = clients.back();
    if (pcb->pending && pcb->sent) {
        const auto n = pcb->pending;
        pcb->pending = 0;
        pcb->sent(pcb->arg, pcb, n);
    }
    if (reset) {
        const auto callback = pcb->error;
        auto* context = pcb->arg;
        tcp_abort(pcb);
        if (callback)
            callback(context, ERR_ABRT);
    } else if (pcb->receive)
        pcb->receive(pcb->arg, pcb, nullptr, ERR_OK);
}
void mock_tcp_poll() {
    for (auto* listener : listeners) {
        int fd = accept(listener->fd, nullptr, nullptr);
        if (fd >= 0) {
            fcntl(fd, F_SETFL, O_NONBLOCK);
            auto* pcb = new tcp_pcb;
            pcb->fd = fd;
            pcb->hold_ack = hold_next_ack;
            hold_next_ack = false;
            pcb->model_nagle = pcb->hold_handshake_ack = hold_next_handshake_ack;
            hold_next_handshake_ack = false;
            clients.push_back(pcb);
            listener->accept(listener->arg, pcb, ERR_OK);
        }
    }
    const auto copy = clients;
    for (auto* pcb : copy) {
        if (pcb->pending && pcb->sent && !pcb->hold_ack && !pcb->hold_handshake_ack) {
            const auto n = pcb->pending;
            pcb->pending = 0;
            pcb->sent(pcb->arg, pcb, n);
        }
        if (pcb->model_nagle)
            (void)tcp_output(pcb);
        if (!pcb->receive)
            continue;
        // Peek first so ERR_MEM faithfully leaves data available for retry.
        std::array<unsigned char, 2048> buffer{};
        const auto n = recv(pcb->fd, buffer.data(), buffer.size(), MSG_PEEK);
        if (n == 0) {
            pcb->receive(pcb->arg, pcb, nullptr, ERR_OK);
            continue;
        }
        if (n < 0) {
            if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
                // MIT sibling Phase 11.1 lesson: lwIP frees PCB before err callback.
                const auto callback = pcb->error;
                auto* context = pcb->arg;
                tcp_abort(pcb);
                if (callback)
                    callback(context, ERR_ABRT);
            }
            continue;
        }
        if (pcb->model_nagle && pcb->pending)
            pcb->hold_handshake_ack = false;
        auto* packet = new pbuf{static_cast<u16_t>(n), new unsigned char[n]};
        std::copy_n(buffer.data(), n, packet->payload);
        const auto result = pcb->receive(pcb->arg, pcb, packet, ERR_OK);
        if (result == ERR_MEM)
            pbuf_free(packet);
        else if (result != ERR_ABRT)
            (void)recv(pcb->fd, buffer.data(), n, 0);
    }
}

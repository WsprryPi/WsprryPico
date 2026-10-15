#include "network/pico/http_server.hpp"
#include "wtp/memory_budget.hpp"

#include <cstring>
#include <iostream>
#include <map>
#include <stdexcept>
#include <vector>

using namespace wsprrypico::network;
namespace {
std::uint64_t now_ms = 0;
tcp_pcb listener;
unsigned freed_packets = 0;
bool bind_fails = false, listen_fails = false, new_fails = false;
void check(bool condition) {
    if (!condition)
        throw std::runtime_error("HTTP concurrency assertion failed");
}
} // namespace
std::uint64_t time_us_64() {
    return now_ms * 1000;
}
tcp_pcb* tcp_new_ip_type(int) {
    listener = {};
    return new_fails ? nullptr : &listener;
}
err_t tcp_bind(tcp_pcb*, const void*, unsigned port) {
    check(port == 80);
    return bind_fails ? ERR_MEM : ERR_OK;
}
tcp_pcb* tcp_listen_with_backlog(tcp_pcb* pcb, int slots) {
    check(slots == 2);
    pcb->listener = !listen_fails;
    return listen_fails ? nullptr : pcb;
}
void tcp_arg(tcp_pcb* pcb, void* arg) {
    pcb->arg = arg;
}
void tcp_accept(tcp_pcb* pcb, err_t (*callback)(void*, tcp_pcb*, err_t)) {
    pcb->accept = callback;
}
void tcp_recv(tcp_pcb* pcb, err_t (*callback)(void*, tcp_pcb*, pbuf*, err_t)) {
    pcb->receive = callback;
}
void tcp_sent(tcp_pcb* pcb, err_t (*callback)(void*, tcp_pcb*, u16_t)) {
    pcb->sent = callback;
}
void tcp_err(tcp_pcb* pcb, void (*callback)(void*, err_t)) {
    pcb->error = callback;
}
void tcp_abort(tcp_pcb* pcb) {
    check(!pcb->listener && !pcb->closed);
    pcb->aborted = pcb->closed = true;
}
err_t tcp_close(tcp_pcb* pcb) {
    check(!pcb->closed);
    if (pcb->close_fails)
        return ERR_MEM;
    pcb->closed = true;
    return ERR_OK;
}
unsigned tcp_sndbuf(tcp_pcb* pcb) {
    return 5840 - pcb->pending;
}
err_t tcp_write(tcp_pcb* pcb, const void* data, u16_t count, int flags) {
    check(!pcb->closed && count <= 1024 && flags == TCP_WRITE_FLAG_COPY);
    if (pcb->no_memory)
        return ERR_MEM;
    if (pcb->write_fails)
        return ERR_ABRT;
    ++pcb->writes;
    pcb->pending += count;
    check(pcb->pending <= 5840);
    pcb->wire.append(static_cast<const char*>(data), count);
    return ERR_OK;
}
err_t tcp_output(tcp_pcb*) {
    return ERR_OK;
}
void tcp_recved(tcp_pcb* pcb, u16_t) {
    check(!pcb->closed);
}
u16_t pbuf_copy_partial(const pbuf* packet, void* out, u16_t count, u16_t offset) {
    std::memcpy(out, static_cast<const char*>(packet->payload) + offset, count);
    return count;
}
void pbuf_free(pbuf*) {
    ++freed_packets;
}
namespace {
struct Harness {
    bool ap = true, station = true, accepting = true;
    std::vector<std::uint64_t> handled;
    std::map<std::uint64_t, bool> finished;
    std::weak_ptr<wsprrypico::wtp::FrameBuffer> input;
    PicoHttpServer server{this, classify, handle, finish};
    static ConsumerInterface classify(void* context, const tcp_pcb* pcb, bool accepting) {
        auto& self = *static_cast<Harness*>(context);
        if (pcb->interface == 1 && self.ap && (!accepting || self.accepting))
            return ConsumerInterface::AccessPoint;
        if (pcb->interface == 2 && self.station)
            return ConsumerInterface::Station;
        return ConsumerInterface::None;
    }
    static HttpResponse handle(void* context, const HttpRequest& request,
                               ConsumerInterface interface, std::uint64_t transaction) {
        auto& self = *static_cast<Harness*>(context);
        check(interface != ConsumerInterface::None);
        self.handled.push_back(transaction);
        self.input = request.buffered_body;
        HttpResponse response;
        if (request.path == "/large") {
            static const std::string body(16000, 'x');
            response.static_body = body;
        } else if (request.path == "/post") {
            check(request.body_view().size() == 4096);
            response.body = "accepted";
        } else
            response.body = "second client completed";
        return response;
    }
    static void finish(void* context, std::uint64_t transaction, bool delivered) {
        auto& self = *static_cast<Harness*>(context);
        check(self.finished.emplace(transaction, delivered).second);
    }
    Harness() {
        now_ms = 0;
        check(server.start());
    }
    void accept(tcp_pcb& pcb, bool allowed = true) {
        check(listener.accept(listener.arg, &pcb, ERR_OK) == (allowed ? ERR_OK : ERR_ABRT));
    }
    void receive(tcp_pcb& pcb, std::string_view bytes) {
        pbuf packet{static_cast<u16_t>(bytes.size()), bytes.data()};
        const auto before = freed_packets;
        (void)pcb.receive(pcb.arg, &pcb, &packet, ERR_OK);
        check(freed_packets == before + 1);
    }
    void request(tcp_pcb& pcb, std::string_view path = "/") {
        receive(pcb, "GET " + std::string(path) + " HTTP/1.1\r\nHost: pico.local\r\n\r\n");
    }
    void ack(tcp_pcb& pcb) {
        if (!pcb.closed && pcb.pending) {
            const auto pending = pcb.pending;
            pcb.pending = 0;
            check(pcb.sent(pcb.arg, &pcb, pending) == ERR_OK);
        }
    }
    void complete(tcp_pcb& pcb) {
        for (unsigned i = 0; i < 100 && !pcb.closed; ++i) {
            server.poll();
            ack(pcb);
        }
        check(pcb.closed && !pcb.aborted);
    }
};
void slow_upload() {
    Harness h;
    tcp_pcb phone, mac, third;
    h.accept(phone);
    h.accept(mac);
    h.accept(third, false);
    h.receive(phone, "POST /post HTTP/1.1\r\nHost: pico.local\r\nContent-Length: 4096\r\n\r\n" +
                         std::string(1024, 'a'));
    h.request(mac);
    h.complete(mac);
    check(h.server.connections() == 1 && h.handled.size() == 1 && h.finished.size() == 1);
    h.receive(phone, std::string(3072, 'a'));
    h.complete(phone);
    check(h.handled.size() == 2 && h.handled[0] != h.handled[1]);
    check(h.input.expired() && h.server.pending_bytes() == 0);
}
void stalled_output() {
    Harness h;
    tcp_pcb phone, mac;
    h.accept(phone);
    h.accept(mac);
    h.request(phone, "/large");
    h.request(mac);
    for (unsigned i = 0; i < 40; ++i) {
        auto a = phone.writes, b = mac.writes;
        h.server.poll();
        h.ack(mac);
        check(phone.writes - a <= 1 && mac.writes - b <= 1);
    }
    check(mac.closed && !phone.closed && phone.pending == 5840 && h.finished.size() == 1);
    const auto completed = h.handled[1];
    check(h.finished.at(completed));
    now_ms = 9999;
    h.server.poll();
    check(!phone.closed);
    now_ms = 10000;
    h.server.poll();
    check(phone.aborted);
    check(!h.finished.at(h.handled[0]) && h.finished.at(completed));
    tcp_pcb reused;
    h.accept(reused);
    h.request(reused);
    h.complete(reused);
    check(h.handled.back() != h.handled.front() && h.server.connections() == 0);
}
void failures() {
    for (unsigned mode = 0; mode < 6; ++mode) {
        Harness h;
        tcp_pcb phone, mac;
        h.accept(phone);
        h.accept(mac);
        h.request(phone);
        h.request(mac);
        h.server.poll();
        const auto token = h.handled[0];
        if (mode == 0) { // FIN cannot acknowledge queued data.
            check(phone.receive(phone.arg, &phone, nullptr, ERR_OK) == ERR_ABRT);
        } else if (mode == 1) { // lwIP error owns PCB destruction.
            phone.closed = true;
            phone.error(phone.arg, ERR_ABRT);
        } else if (mode == 2) {
            phone.write_fails = true;
            h.server.poll();
            check(phone.aborted);
        } else if (mode == 3) {
            phone.no_memory = true;
            h.server.poll();
            check(!phone.closed);
            phone.no_memory = false;
            h.complete(phone);
        } else if (mode == 4) {
            phone.close_fails = true;
            for (int i = 0; i < 5 && !phone.closed; ++i) {
                h.ack(phone);
                h.server.poll();
            }
            check(phone.aborted && h.finished.at(token));
        } else {
            now_ms = 10000;
            h.server.poll();
            check(phone.aborted && mac.aborted);
        }
        if (mode != 5)
            h.complete(mac);
        check(h.finished.size() == 2);
        check(h.finished.at(token) == (mode == 3 || mode == 4));
    }
}
void interface_and_stop() {
    Harness h;
    tcp_pcb ap, sta, refused;
    sta.interface = 2;
    h.accept(ap);
    h.accept(sta);
    h.request(ap);
    h.request(sta);
    h.accepting = false;
    h.accept(refused, false);
    h.server.poll();
    check(!ap.closed && !sta.closed);
    h.ap = false;
    h.server.poll();
    check(ap.aborted && !sta.closed);
    h.complete(sta);
    h.server.stop();
    check(listener.closed && !listener.aborted);
    check(h.server.connections() == 0 && !h.server.reply_active() && !h.server.listening());
}
void parser_and_pressure() {
    for (auto bad :
         {std::string("GET / HTTP/1.1\n\n"),
          std::string("GET / HTTP/1.1\r\nHost: x\r\n\r\nGET / HTTP/1.1\r\nHost: x\r\n\r\n"),
          std::string(3000, 'a')}) {
        Harness h;
        tcp_pcb phone, mac;
        h.accept(phone);
        h.accept(mac);
        h.receive(phone, bad);
        h.request(mac);
        h.complete(mac);
        if (!phone.closed)
            h.complete(phone);
        check(h.handled.size() == 1); // Malformed/pipelined prefix never executes.
    }
    Harness h;
    tcp_pcb phone, mac;
    h.accept(phone);
    h.accept(mac);
    h.request(mac); // Its parsed request predates the low-memory condition.
    wsprrypico::wtp::available_memory = []() -> std::size_t { return 32768; };
    h.receive(phone, "POST /post HTTP/1.1\r\nHost: x\r\nContent-Length: 4096\r\n\r\n");
    check(phone.aborted && h.handled.empty());
    h.complete(mac);
    wsprrypico::wtp::available_memory = nullptr;
    check(h.handled.size() == 1 && h.server.connections() == 0);
    // Already reserved body pages must remain usable below header workspace.
    tcp_pcb reserved;
    h.accept(reserved);
    h.receive(reserved, "POST /post HTTP/1.1\r\nHost: x\r\nContent-Length: 4096\r\n\r\n");
    wsprrypico::wtp::available_memory = []() -> std::size_t { return 33000; };
    h.receive(reserved, std::string(4096, 'a'));
    h.complete(reserved);
    wsprrypico::wtp::available_memory = nullptr;
    check(h.input.expired());
    // Header workspace fits, but a maximum body would violate its own reserve.
    tcp_pcb body_pressure;
    h.accept(body_pressure);
    wsprrypico::wtp::available_memory = []() -> std::size_t { return 65536; };
    h.receive(body_pressure, "POST /post HTTP/1.1\r\nHost: x\r\nContent-Length: 32768\r\n\r\n");
    h.complete(body_pressure);
    wsprrypico::wtp::available_memory = nullptr;
    check(body_pressure.wire.starts_with("HTTP/1.1 400"));
}
void acknowledgment_and_fragment_boundaries() {
    for (bool close_fails : {false, true}) {
        Harness h;
        tcp_pcb phone, mac;
        h.accept(phone);
        h.receive(phone, "GET / HTTP/1.1\r\nHost: ");
        h.accept(mac);
        h.request(mac);
        h.complete(mac);
        check(h.handled.size() == 1 && !phone.closed);
        h.receive(phone, "pico.local\r\n\r\n");
        h.server.poll();
        h.server.poll(); // Header and body queued, neither ACKed.
        const auto token = h.handled.back();
        const auto partial = phone.pending - 1;
        phone.pending -= partial;
        phone.sent(phone.arg, &phone, partial);
        h.server.poll();
        check(!h.finished.contains(token));
        phone.sent(phone.arg, &phone, 1);
        phone.pending = 0;
        phone.close_fails = close_fails;
        // A FIN after complete ACKs preserves success, even if close must abort.
        check(phone.receive(phone.arg, &phone, nullptr, ERR_OK) ==
              (close_fails ? ERR_ABRT : ERR_OK));
        check(h.finished.at(token) && phone.aborted == close_fails);
    }
    Harness h;
    tcp_pcb phone, mac;
    h.accept(phone);
    h.accept(mac);
    h.request(phone);
    h.request(phone); // A second pbuf before poll cannot replace the first request.
    check(phone.aborted);
    h.request(mac);
    h.complete(mac);
    check(h.handled.size() == 1);
    tcp_pcb trickle;
    h.accept(trickle);
    h.receive(trickle, "GET / HTTP/1.1\r\n");
    now_ms = 9999;
    h.receive(trickle, "Host: ");
    h.server.poll();
    check(!trickle.closed);
    now_ms = 10000;
    h.server.poll();
    check(trickle.aborted);
    check(listener.accept(listener.arg, nullptr, ERR_MEM) == ERR_ABRT);
    tcp_pcb failed;
    check(listener.accept(listener.arg, &failed, ERR_MEM) == ERR_ABRT && failed.aborted);
}
void startup_and_reclamation() {
    for (unsigned failure = 0; failure < 3; ++failure) {
        PicoHttpServer server{
            nullptr, [](void*, const tcp_pcb*, bool) { return ConsumerInterface::Station; },
            [](void*, const HttpRequest&, ConsumerInterface, std::uint64_t) {
                return HttpResponse{};
            },
            nullptr};
        new_fails = failure == 0;
        bind_fails = failure == 1;
        listen_fails = failure == 2;
        check(!server.start());
        new_fails = bind_fails = listen_fails = false;
        check(server.start());
        server.stop();
    }
    Harness h;
    for (unsigned cycle = 0; cycle < 32; ++cycle) {
        tcp_pcb phone, mac;
        h.accept(phone);
        h.accept(mac);
        h.request(phone);
        h.request(mac);
        h.complete(phone);
        h.complete(mac);
        check(h.server.connections() == 0 && h.server.pending_bytes() == 0);
    }
    check(h.finished.size() == 64);
}
} // namespace
int main() {
    slow_upload();
    stalled_output();
    failures();
    interface_and_stop();
    parser_and_pressure();
    acknowledgment_and_fragment_boundaries();
    startup_and_reclamation();
    std::cout << "HTTP concurrency scenarios passed; host task storage " << sizeof(PicoHttpServer)
              << " bytes\n";
}

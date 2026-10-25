#pragma once

#include "lwip/tcp.h"
#include "network/consumer_radio.hpp"
#include "network/http.hpp"

#include <array>

namespace wsprrypico::network {

// Two cooperative core-0 tasks. All callbacks and application dispatch share
// the foreground lwIP owner; no thread, lock or RF-core work is introduced.
class PicoHttpServer {
  public:
    static constexpr std::size_t capacity = 2, output_chunk = 1024;
    static constexpr std::size_t header_workspace = HttpParser::header_prefix_workspace;
    static constexpr std::uint64_t lifetime_ms = 10'000;
    using Classify = ConsumerInterface (*)(void*, const tcp_pcb*, bool accepting);
    using Handle = HttpResponse (*)(void*, const HttpRequest&, ConsumerInterface, std::uint64_t);
    using Finish = void (*)(void*, std::uint64_t, bool delivered);
    PicoHttpServer(void* context, Classify classify, Handle handle, Finish finish)
        : context_(context), classify_(classify), handle_(handle), finish_(finish) {}
    ~PicoHttpServer();
    PicoHttpServer(const PicoHttpServer&) = delete;
    PicoHttpServer& operator=(const PicoHttpServer&) = delete;
    bool start();
    void stop();
    void withdraw(ConsumerInterface interface);
    void poll();
    bool listening() const {
        return listener_ != nullptr;
    }
    std::size_t connections() const;
    std::size_t pending_bytes() const;
    bool reply_active() const;

  private:
    struct Client {
        PicoHttpServer* owner = nullptr;
        tcp_pcb* pcb = nullptr;
        ConsumerInterface interface = ConsumerInterface::None;
        std::uint64_t transaction = 0, accepted_ms = 0;
        HttpParser parser;
        HttpResponse response;
        std::string headers;
        std::size_t header_offset = 0, body_offset = 0, pending = 0;
        bool dispatched = false;
    };
    static err_t accept(void*, tcp_pcb*, err_t);
    static err_t receive(void*, tcp_pcb*, pbuf*, err_t);
    static err_t sent(void*, tcp_pcb*, u16_t);
    static void error(void*, err_t);
    static bool delivered(const Client&);
    bool close(Client&, bool success, bool freed = false);
    void step(Client&, std::uint64_t now);
    void* context_;
    Classify classify_;
    Handle handle_;
    Finish finish_;
    tcp_pcb* listener_ = nullptr;
    std::array<Client, capacity> clients_;
    std::size_t first_ = 0;
    std::uint64_t next_transaction_ = std::uint64_t{1} << 63;
};

// Fixed task metadata is separate from bounded parser bodies and lwIP pools.
static_assert(sizeof(PicoHttpServer) <= 2048);

} // namespace wsprrypico::network

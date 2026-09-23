#pragma once

#include "lwip/tcp.h"
#include "network/http.hpp"

#include <array>
#include <string>

namespace wsprrypico::network {

// One-connection plaintext server for an unprovisioned AP. It intentionally
// exposes only read-only identity/build data and never receives credentials.
class PicoBootstrapServer {
  public:
    using InterfaceClassifier = bool (*)(const tcp_pcb*, void*);
    PicoBootstrapServer(std::string device, std::string firmware, InterfaceClassifier classifier,
                        void* context)
        : device_(std::move(device)), firmware_(std::move(firmware)), classifier_(classifier),
          classifier_context_(context) {}
    ~PicoBootstrapServer();
    bool start();
    void stop();
    void poll(bool active);
    bool listening() const {
        return listener_ != nullptr;
    }

  private:
    static err_t accept(void*, tcp_pcb*, err_t);
    static err_t receive(void*, tcp_pcb*, pbuf*, err_t);
    static err_t sent(void*, tcp_pcb*, u16_t);
    static void error(void*, err_t);
    void close();
    void dispatch();

    std::string device_;
    std::string firmware_;
    InterfaceClassifier classifier_ = nullptr;
    void* classifier_context_ = nullptr;
    tcp_pcb* listener_ = nullptr;
    tcp_pcb* client_ = nullptr;
    HttpParser parser_;
    std::string wire_;
    std::size_t output_offset_ = 0;
    std::size_t pending_bytes_ = 0;
    std::uint64_t accepted_ms_ = 0;
    bool active_ = false;
};

} // namespace wsprrypico::network

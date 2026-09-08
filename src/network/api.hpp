#pragma once
#include "network/http.hpp"
#include "standalone/scheduler.hpp"

namespace wsprrypico::network {
class NetworkControl {
  public:
    virtual ~NetworkControl() = default;
    virtual std::string status() const = 0;
    virtual bool set_enabled(bool enabled) = 0;
    virtual bool request_enabled(bool enabled) {
        return set_enabled(enabled);
    }
    virtual void finish_request(bool) {}
};
class BrowserApi {
  public:
    BrowserApi(wtp::JobService& service, standalone::Store& store, standalone::Scheduler& scheduler,
               NetworkControl& network, std::string device, std::string firmware)
        : service_(service), store_(store), scheduler_(scheduler), network_(network),
          device_(std::move(device)), firmware_(std::move(firmware)) {}
    HttpResponse handle(const HttpRequest& request, std::string_view principal,
                        std::string_view authority);
    std::string revision() const;
    void finish_request() {
        network_.finish_request(scheduler_.idle());
    }

  private:
    HttpResponse config() const;
    HttpResponse job(const HttpRequest& request, std::string_view principal);
    wtp::JobService& service_;
    standalone::Store& store_;
    standalone::Scheduler& scheduler_;
    NetworkControl& network_;
    std::string device_, firmware_;
    std::uint64_t network_revision_ = 0;
};
} // namespace wsprrypico::network

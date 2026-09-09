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
                        std::string_view authority, std::uint64_t transaction = 0);
    std::string revision() const;
    void hostname_authority(std::string authority) {
        hostname_authority_ = std::move(authority);
    }
    // All calls are serialized by the application owner. Tokens are never reused.
    void finish_request(std::uint64_t transaction = 0, bool apply = true) {
        if (pending_transaction_ && *pending_transaction_ == transaction) {
            const bool allowed = apply && scheduler_.idle();
            if (pending_restart_) {
                if (allowed && restart_)
                    (void)restart_(restart_context_);
            } else
                network_.finish_request(allowed);
            pending_transaction_.reset();
            pending_restart_ = false;
        }
    }
    using Restart = bool (*)(void*);
    void restart_control(Restart callback, void* context) {
        restart_ = callback;
        restart_context_ = context;
    }
    void set_active_job_connections(bool enabled) {
        active_job_connections_ = enabled;
    }
    bool active_job_connections() const {
        return active_job_connections_;
    }
    using TransportStatus = std::string (*)(void*);
    void transport_status(TransportStatus callback, void* context) {
        transport_ = callback;
        transport_context_ = context;
    }

  private:
    HttpResponse config() const;
    HttpResponse job(const HttpRequest& request, std::string_view principal);
    wtp::JobService& service_;
    standalone::Store& store_;
    standalone::Scheduler& scheduler_;
    NetworkControl& network_;
    std::string device_, firmware_, hostname_authority_;
    TransportStatus transport_ = nullptr;
    void* transport_context_ = nullptr;
    bool active_job_connections_ = false;
    std::optional<std::uint64_t> pending_transaction_;
    bool pending_restart_ = false;
    Restart restart_ = nullptr;
    void* restart_context_ = nullptr;
    std::uint64_t network_revision_ = 0;
};
} // namespace wsprrypico::network

#pragma once

#include "btstack.h"
#include "provisioning/ble_session.hpp"
#include "provisioning/gatt_framing.hpp"
#include "wtp/endpoint.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace wsprrypico::provisioning {
class PicoGattTransport {
  public:
    struct Diagnostics {
        std::uint32_t connections = 0;
        std::uint32_t disconnections = 0;
        std::uint32_t command_frames = 0;
        std::uint32_t commands_completed = 0;
        std::uint32_t responses_queued = 0;
        std::uint32_t queue_failures = 0;
        std::uint32_t send_requests = 0;
        std::uint32_t can_send_callbacks = 0;
        std::uint32_t can_send_during_write = 0;
        std::uint32_t indications_started = 0;
        std::uint32_t indication_completions = 0;
        std::uint32_t responses_delivered = 0;
        std::uint32_t cccd_writes = 0;
        std::uint32_t cccd_rejections = 0;
        std::uint32_t wtp_write_segments = 0;
        std::uint32_t wtp_write_bytes = 0;
        std::uint32_t wtp_indication_segments = 0;
        std::uint32_t wtp_indication_bytes = 0;
        std::uint16_t cccd_value = 0;
        std::uint16_t wtp_cccd_value = 0;
        std::uint8_t last_request_status = 0;
        std::uint8_t last_indication_status = 0;
        std::uint8_t last_completion_status = 0;
        std::uint8_t last_disconnect_reason = 0;
        std::uint16_t att_mtu = 0;
        std::size_t outbound_frames = 0;
        std::size_t outbound_index = 0;
        bool connected = false;
        bool admitted = false;
        bool send_requested = false;
    };
    using Now = std::uint64_t (*)(void*);
    PicoGattTransport(BleCommandSession& session, wtp::Endpoint* endpoint, std::string identity,
                      std::string advertising_name, Now now, void* context)
        : session_(session), endpoint_(endpoint), identity_(std::move(identity)),
          advertising_name_(std::move(advertising_name)), now_(now), context_(context),
          inbound_(max_command_bytes) {}
    ~PicoGattTransport();
    bool start();
    void stop();
    void poll();
    bool running() const { return running_; }
    Diagnostics diagnostics() const;

  private:
    static std::uint16_t read_callback(hci_con_handle_t connection, std::uint16_t handle,
                                       std::uint16_t offset, std::uint8_t* buffer,
                                       std::uint16_t size);
    static int write_callback(hci_con_handle_t connection, std::uint16_t handle,
                              std::uint16_t transaction, std::uint16_t offset,
                              std::uint8_t* buffer, std::uint16_t size);
    static void hci_callback(std::uint8_t packet_type, std::uint16_t channel,
                             std::uint8_t* packet, std::uint16_t size);
    static void att_callback(std::uint8_t packet_type, std::uint16_t channel,
                             std::uint8_t* packet, std::uint16_t size);
    static void can_send(void* context);
    bool admit();
    bool queue(std::string_view notification);
    bool output_pending() const;
    bool ensure_wtp_endpoint();
    bool request_send();
    void send_next();
    void security_lost();
    void disconnected();
    std::uint64_t now() const { return now_ ? now_(context_) : 0; }

    static PicoGattTransport* owner_;
    BleCommandSession& session_;
    wtp::Endpoint* endpoint_;
    std::string identity_;
    std::string advertising_name_;
    Now now_;
    void* context_;
    GattFrameReceiver inbound_;
    std::vector<std::vector<std::uint8_t>> outbound_;
    std::size_t outbound_index_ = 0;
    hci_con_handle_t connection_ = HCI_CON_HANDLE_INVALID;
    int peer_index_ = -1;
    bool encrypted_ = false;
    bool new_pairing_ = false;
    bool admitted_ = false;
    bool running_ = false;
    // BTstack retains these pointers until the asynchronous controller setup
    // completes; they must outlive start().
    std::array<std::uint8_t, 21> advertisement_{};
    std::array<std::uint8_t, 31> scan_response_{};
    btstack_packet_callback_registration_t hci_registration_{};
    btstack_packet_callback_registration_t sm_registration_{};
    btstack_context_callback_registration_t send_request_{};
    bool send_requested_ = false;
    bool in_write_callback_ = false;
    std::uint16_t status_cccd_ = 0;
    std::uint16_t wtp_cccd_ = 0;
    enum class Indication { None, Provisioning, Wtp };
    Indication indication_ = Indication::None;
    std::size_t wtp_indication_bytes_ = 0;
    Diagnostics diagnostics_{};
};
} // namespace wsprrypico::provisioning

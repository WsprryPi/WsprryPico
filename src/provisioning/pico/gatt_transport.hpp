#pragma once

#include "btstack.h"
#include "provisioning/ble_session.hpp"
#include "provisioning/gatt_framing.hpp"

#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace wsprrypico::provisioning {
class PicoGattTransport {
  public:
    using Now = std::uint64_t (*)(void*);
    PicoGattTransport(BleCommandSession& session, std::string identity,
                      std::string advertising_name, Now now, void* context)
        : session_(session), identity_(std::move(identity)),
          advertising_name_(std::move(advertising_name)), now_(now), context_(context),
          inbound_(max_command_bytes) {}
    ~PicoGattTransport();
    bool start();
    void stop();
    void poll();
    bool running() const { return running_; }

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
    bool admit();
    bool queue(std::string_view notification);
    void send_next();
    void disconnected();
    std::uint64_t now() const { return now_ ? now_(context_) : 0; }

    static PicoGattTransport* owner_;
    BleCommandSession& session_;
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
};
} // namespace wsprrypico::provisioning

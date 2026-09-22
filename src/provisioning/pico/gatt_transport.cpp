#include "provisioning/pico/gatt_transport.hpp"

#include "provisioning/pico/field_platform.hpp"

#include "field_access.h"
#include "pico/btstack_cyw43.h"
#include "pico/cyw43_arch.h"

#include <algorithm>
#include <array>

namespace wsprrypico::provisioning {
PicoGattTransport* PicoGattTransport::owner_ = nullptr;

PicoGattTransport::~PicoGattTransport() {
    stop();
}

bool PicoGattTransport::start() {
    if (running_ || owner_ || !session_.available() || identity_.empty() ||
        advertising_name_.empty() ||
        advertising_name_.size() > 29 || !btstack_cyw43_init(cyw43_arch_async_context()))
        return false;
    owner_ = this;
    l2cap_init();
    sm_init();
    sm_set_io_capabilities(IO_CAPABILITY_NO_INPUT_NO_OUTPUT);
    sm_set_authentication_requirements(SM_AUTHREQ_SECURE_CONNECTION | SM_AUTHREQ_BONDING);
    att_server_init(profile_data, read_callback, write_callback);
    hci_registration_.callback = hci_callback;
    hci_add_event_handler(&hci_registration_);
    sm_registration_.callback = hci_callback;
    sm_add_event_handler(&sm_registration_);
    att_server_register_packet_handler(att_callback);

    std::array<std::uint8_t, 21> advertisement{
        2, BLUETOOTH_DATA_TYPE_FLAGS, 6,
        17, BLUETOOTH_DATA_TYPE_COMPLETE_LIST_OF_128_BIT_SERVICE_CLASS_UUIDS,
        0x01, 0x22, 0xc1, 0x70, 0x8f, 0x3e, 0x86, 0xa4,
        0x21, 0x4f, 0xf1, 0x5b, 0x01, 0x00, 0x6b, 0x7d};
    std::array<std::uint8_t, 31> scan{};
    scan[0] = static_cast<std::uint8_t>(advertising_name_.size() + 1);
    scan[1] = BLUETOOTH_DATA_TYPE_COMPLETE_LOCAL_NAME;
    std::copy(advertising_name_.begin(), advertising_name_.end(), scan.begin() + 2);
    bd_addr_t any{};
    gap_advertisements_set_params(0x00a0, 0x00f0, 0, 0, any, 7, 0);
    gap_advertisements_set_data(static_cast<std::uint8_t>(advertisement.size()),
                                advertisement.data());
    gap_scan_response_set_data(static_cast<std::uint8_t>(advertising_name_.size() + 2),
                               scan.data());
    gap_advertisements_enable(1);
    running_ = hci_power_control(HCI_POWER_ON) == 0;
    if (!running_) {
        owner_ = nullptr;
        btstack_cyw43_deinit(cyw43_arch_async_context());
    }
    return running_;
}

void PicoGattTransport::poll() {
    session_.poll(now());
}

void PicoGattTransport::stop() {
    if (!running_ && owner_ != this)
        return;
    gap_advertisements_enable(0);
    if (connection_ != HCI_CON_HANDLE_INVALID)
        (void)gap_disconnect(connection_);
    disconnected();
    (void)hci_power_control(HCI_POWER_OFF);
    btstack_cyw43_deinit(cyw43_arch_async_context());
    running_ = false;
    if (owner_ == this)
        owner_ = nullptr;
}

bool PicoGattTransport::admit() {
    if (admitted_)
        return true;
    if (!encrypted_ || peer_index_ < 0 || connection_ == HCI_CON_HANDLE_INVALID ||
        gap_encryption_key_size(connection_) < 16)
        return false;
    const auto peer = PicoBondStore::identity(peer_index_);
    if (!peer)
        return false;
    admitted_ = session_.connected(peer, true, new_pairing_,
                                   "ble-" + std::to_string(connection_), now());
    if (!admitted_ && new_pairing_)
        le_device_db_remove(peer_index_);
    return admitted_;
}

void PicoGattTransport::disconnected() {
    if (admitted_)
        session_.disconnected();
    else if (new_pairing_ && peer_index_ >= 0)
        le_device_db_remove(peer_index_);
    inbound_.reset();
    for (auto& frame : outbound_)
        std::fill(frame.begin(), frame.end(), 0);
    outbound_.clear();
    outbound_index_ = 0;
    connection_ = HCI_CON_HANDLE_INVALID;
    peer_index_ = -1;
    encrypted_ = false;
    new_pairing_ = false;
    admitted_ = false;
}

bool PicoGattTransport::queue(std::string_view notification) {
    if (!outbound_.empty() || notification.empty() || notification.size() > max_notification_bytes)
        return false;
    outbound_ = gatt_frames(std::span(
        reinterpret_cast<const std::uint8_t*>(notification.data()), notification.size()));
    outbound_index_ = 0;
    send_next();
    return !outbound_.empty();
}

void PicoGattTransport::send_next() {
    if (outbound_index_ >= outbound_.size() || connection_ == HCI_CON_HANDLE_INVALID)
        return;
    const auto& frame = outbound_[outbound_index_];
    if (att_server_indicate(connection_, ATT_CHARACTERISTIC_7D6B0004_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE,
                            frame.data(), static_cast<std::uint16_t>(frame.size())) != 0)
        (void)gap_disconnect(connection_);
}

std::uint16_t PicoGattTransport::read_callback(hci_con_handle_t, std::uint16_t handle,
                                               std::uint16_t offset, std::uint8_t* buffer,
                                               std::uint16_t size) {
    if (!owner_ || handle != ATT_CHARACTERISTIC_7D6B0002_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE)
        return 0;
    return att_read_callback_handle_blob(
        reinterpret_cast<const std::uint8_t*>(owner_->identity_.data()),
        static_cast<std::uint16_t>(owner_->identity_.size()), offset, buffer, size);
}

int PicoGattTransport::write_callback(hci_con_handle_t connection, std::uint16_t handle,
                                      std::uint16_t transaction, std::uint16_t offset,
                                      std::uint8_t* buffer, std::uint16_t size) {
    if (!owner_ || connection != owner_->connection_ ||
        handle != ATT_CHARACTERISTIC_7D6B0003_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE)
        return ATT_ERROR_WRITE_NOT_PERMITTED;
    if (transaction != ATT_TRANSACTION_MODE_NONE)
        return ATT_ERROR_REQUEST_NOT_SUPPORTED;
    if (offset)
        return ATT_ERROR_INVALID_OFFSET;
    if (!owner_->admit())
        return ATT_ERROR_INSUFFICIENT_AUTHENTICATION;
    const auto result = owner_->inbound_.receive(std::span(buffer, size));
    if (result == FrameResult::Pending)
        return ATT_ERROR_SUCCESS;
    if (result != FrameResult::Complete)
        return result == FrameResult::Oversize ? ATT_ERROR_INVALID_ATTRIBUTE_VALUE_LENGTH
                                                : ATT_ERROR_VALUE_NOT_ALLOWED;
    const auto message = owner_->inbound_.message();
    auto response = owner_->session_.handle(
        std::string_view(reinterpret_cast<const char*>(message.data()), message.size()),
        owner_->now());
    owner_->inbound_.reset();
    if (!response.notify() || !owner_->queue(response.notification))
        return ATT_ERROR_INSUFFICIENT_RESOURCES;
    return ATT_ERROR_SUCCESS;
}

void PicoGattTransport::hci_callback(std::uint8_t packet_type, std::uint16_t,
                                     std::uint8_t* packet, std::uint16_t) {
    if (!owner_ || packet_type != HCI_EVENT_PACKET)
        return;
    switch (hci_event_packet_get_type(packet)) {
    case HCI_EVENT_META_GAP:
        if (hci_event_gap_meta_get_subevent_code(packet) == GAP_SUBEVENT_LE_CONNECTION_COMPLETE &&
            gap_subevent_le_connection_complete_get_status(packet) == 0) {
            if (owner_->connection_ != HCI_CON_HANDLE_INVALID) {
                (void)gap_disconnect(
                    gap_subevent_le_connection_complete_get_connection_handle(packet));
                break;
            }
            owner_->connection_ =
                gap_subevent_le_connection_complete_get_connection_handle(packet);
            sm_request_pairing(owner_->connection_);
        }
        break;
    case HCI_EVENT_ENCRYPTION_CHANGE:
        if (hci_event_encryption_change_get_connection_handle(packet) == owner_->connection_) {
            owner_->encrypted_ = hci_event_encryption_change_get_status(packet) == 0 &&
                                hci_event_encryption_change_get_encryption_enabled(packet);
            (void)owner_->admit();
        }
        break;
    case SM_EVENT_JUST_WORKS_REQUEST:
        if (owner_->session_.pairing_allowed(owner_->now()))
            sm_just_works_confirm(sm_event_just_works_request_get_handle(packet));
        else
            (void)gap_disconnect(sm_event_just_works_request_get_handle(packet));
        break;
    case SM_EVENT_IDENTITY_CREATED:
        owner_->peer_index_ = sm_event_identity_created_get_index(packet);
        owner_->new_pairing_ = true;
        (void)owner_->admit();
        break;
    case SM_EVENT_IDENTITY_RESOLVING_SUCCEEDED:
        owner_->peer_index_ = sm_event_identity_resolving_succeeded_get_index(packet);
        owner_->new_pairing_ = false;
        (void)owner_->admit();
        break;
    case HCI_EVENT_DISCONNECTION_COMPLETE:
        if (hci_event_disconnection_complete_get_connection_handle(packet) == owner_->connection_)
            owner_->disconnected();
        break;
    default:
        break;
    }
}

void PicoGattTransport::att_callback(std::uint8_t packet_type, std::uint16_t,
                                     std::uint8_t* packet, std::uint16_t) {
    if (!owner_ || packet_type != HCI_EVENT_PACKET ||
        hci_event_packet_get_type(packet) != ATT_EVENT_HANDLE_VALUE_INDICATION_COMPLETE ||
        att_event_handle_value_indication_complete_get_conn_handle(packet) != owner_->connection_)
        return;
    if (att_event_handle_value_indication_complete_get_status(packet) != 0) {
        (void)gap_disconnect(owner_->connection_);
        return;
    }
    ++owner_->outbound_index_;
    if (owner_->outbound_index_ < owner_->outbound_.size()) {
        owner_->send_next();
        return;
    }
    for (auto& frame : owner_->outbound_)
        std::fill(frame.begin(), frame.end(), 0);
    owner_->outbound_.clear();
    owner_->outbound_index_ = 0;
    owner_->session_.response_delivered(owner_->now());
}
} // namespace wsprrypico::provisioning

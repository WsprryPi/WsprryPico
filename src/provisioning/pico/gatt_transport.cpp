#include "provisioning/pico/gatt_transport.hpp"

#include "field_access.h"
#include "pico/btstack_cyw43.h"
#include "pico/cyw43_arch.h"
#include "provisioning/pico/field_platform.hpp"

#include <algorithm>
#include <array>

namespace wsprrypico::provisioning {
PicoGattTransport* PicoGattTransport::owner_ = nullptr;

PicoGattTransport::~PicoGattTransport() {
    stop();
}

bool PicoGattTransport::start() {
    if (running_ || owner_ || !session_.available() || identity_.empty() ||
        advertising_name_.empty() || advertising_name_.size() > 29 ||
        !cyw43_is_initialized(&cyw43_state))
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
    send_request_.callback = can_send;
    send_request_.context = this;

    advertisement_ = {2,
                      BLUETOOTH_DATA_TYPE_FLAGS,
                      6,
                      17,
                      BLUETOOTH_DATA_TYPE_COMPLETE_LIST_OF_128_BIT_SERVICE_CLASS_UUIDS,
                      0x01,
                      0x22,
                      0xc1,
                      0x70,
                      0x8f,
                      0x3e,
                      0x86,
                      0xa4,
                      0x21,
                      0x4f,
                      0xf1,
                      0x5b,
                      0x01,
                      0x00,
                      0x6b,
                      0x7d};
    scan_response_.fill(0);
    scan_response_[0] = static_cast<std::uint8_t>(advertising_name_.size() + 1);
    scan_response_[1] = BLUETOOTH_DATA_TYPE_COMPLETE_LOCAL_NAME;
    std::copy(advertising_name_.begin(), advertising_name_.end(), scan_response_.begin() + 2);
    bd_addr_t any{};
    gap_advertisements_set_params(0x00a0, 0x00f0, 0, 0, any, 7, 0);
    gap_advertisements_set_data(static_cast<std::uint8_t>(advertisement_.size()),
                                advertisement_.data());
    gap_scan_response_set_data(static_cast<std::uint8_t>(advertising_name_.size() + 2),
                               scan_response_.data());
    gap_advertisements_enable(1);
    running_ = hci_power_control(HCI_POWER_ON) == 0;
    if (!running_) {
        owner_ = nullptr;
    }
    return running_;
}

void PicoGattTransport::poll() {
    const auto current = now();
    session_.poll(current);
    if (endpoint_ && !endpoint_->closed()) {
        if (session_.authorized())
            endpoint_->poll(current);
        else
            endpoint_->disconnect();
    }
    if (!send_requested_ && indication_ == Indication::None && output_pending())
        (void)request_send();
}

PicoGattTransport::Diagnostics PicoGattTransport::diagnostics() const {
    auto result = diagnostics_;
    result.connected = connection_ != HCI_CON_HANDLE_INVALID;
    result.admitted = admitted_;
    result.send_requested = send_requested_;
    result.cccd_value = status_cccd_;
    result.wtp_cccd_value = wtp_cccd_;
    result.wtp_over_field_status = session_.wtp_over_field_status();
    result.outbound_frames = outbound_.size();
    result.outbound_index = outbound_index_;
    result.att_mtu = result.connected ? att_server_get_mtu(connection_) : 0;
    return result;
}

void PicoGattTransport::stop() {
    if (!running_ && owner_ != this)
        return;
    gap_advertisements_enable(0);
    if (connection_ != HCI_CON_HANDLE_INVALID)
        (void)gap_disconnect(connection_);
    disconnected();
    (void)hci_power_control(HCI_POWER_OFF);
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
    admitted_ =
        session_.connected(peer, true, new_pairing_, "ble-" + std::to_string(connection_), now());
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
    if (endpoint_)
        endpoint_->disconnect();
    for (auto& frame : outbound_)
        std::fill(frame.begin(), frame.end(), 0);
    outbound_.clear();
    outbound_index_ = 0;
    send_requested_ = false;
    status_cccd_ = 0;
    wtp_cccd_ = 0;
    indication_ = Indication::None;
    wtp_indication_bytes_ = 0;
    connection_ = HCI_CON_HANDLE_INVALID;
    peer_index_ = -1;
    encrypted_ = false;
    new_pairing_ = false;
    admitted_ = false;
}

void PicoGattTransport::security_lost() {
    // Do not wait for the asynchronous HCI disconnect event to revoke
    // application authority. BTstack attribute permissions reject new writes,
    // but queued server indications and WTP output must also fail closed now.
    if (admitted_)
        session_.disconnected();
    inbound_.reset();
    if (endpoint_)
        endpoint_->disconnect();
    for (auto& frame : outbound_)
        std::fill(frame.begin(), frame.end(), 0);
    outbound_.clear();
    outbound_index_ = 0;
    send_requested_ = false;
    status_cccd_ = 0;
    wtp_cccd_ = 0;
    indication_ = Indication::None;
    wtp_indication_bytes_ = 0;
}

bool PicoGattTransport::queue(std::string_view notification) {
    if (status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION ||
        !outbound_.empty() || notification.empty() ||
        notification.size() > max_notification_bytes) {
        ++diagnostics_.queue_failures;
        return false;
    }
    outbound_ = gatt_frames(
        std::span(reinterpret_cast<const std::uint8_t*>(notification.data()), notification.size()));
    outbound_index_ = 0;
    if (send_requested_ || indication_ != Indication::None) {
        ++diagnostics_.responses_queued;
        return true;
    }
    if (request_send()) {
        ++diagnostics_.responses_queued;
        return true;
    }
    ++diagnostics_.queue_failures;
    for (auto& frame : outbound_)
        std::fill(frame.begin(), frame.end(), 0);
    outbound_.clear();
    return false;
}

bool PicoGattTransport::ensure_wtp_endpoint() {
    if (!endpoint_)
        return false;
    if (!endpoint_->closed())
        return true;
    // A completion for the former logical endpoint still owns the recorded
    // byte count. Do not let a reauthorization bind that completion to a new
    // endpoint generation.
    if (indication_ == Indication::Wtp)
        return false;
    if (!session_.authorized())
        return false;
    auto principal = session_.principal();
    if (principal.empty())
        return false;
    endpoint_->connect(std::move(principal));
    return !endpoint_->closed();
}

bool PicoGattTransport::output_pending() const {
    return outbound_index_ < outbound_.size() ||
           (wtp_indications_enabled() && endpoint_ && !endpoint_->closed() &&
            !endpoint_->output().empty());
}

bool PicoGattTransport::wtp_indications_enabled() const {
    const auto cccd = session_.wtp_over_field_status() ? status_cccd_ : wtp_cccd_;
    return cccd == GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION;
}

std::uint16_t PicoGattTransport::wtp_status_handle() const {
    return session_.wtp_over_field_status()
               ? ATT_CHARACTERISTIC_7D6B0004_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE
               : ATT_CHARACTERISTIC_7D6B0006_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE;
}

bool PicoGattTransport::request_send() {
    if (send_requested_ || indication_ != Indication::None || !output_pending() ||
        connection_ == HCI_CON_HANDLE_INVALID)
        return false;
    send_requested_ = true;
    ++diagnostics_.send_requests;
    diagnostics_.last_request_status =
        att_server_request_to_send_indication(&send_request_, connection_);
    if (diagnostics_.last_request_status == ERROR_CODE_SUCCESS)
        return true;
    send_requested_ = false;
    return false;
}

void PicoGattTransport::can_send(void* context) {
    auto* transport = static_cast<PicoGattTransport*>(context);
    if (transport && transport == owner_) {
        ++transport->diagnostics_.can_send_callbacks;
        if (transport->in_write_callback_)
            ++transport->diagnostics_.can_send_during_write;
        transport->send_next();
    }
}

void PicoGattTransport::send_next() {
    send_requested_ = false;
    if (indication_ != Indication::None || connection_ == HCI_CON_HANDLE_INVALID)
        return;
    std::uint16_t handle = 0;
    std::span<const std::uint8_t> bytes;
    if (outbound_index_ < outbound_.size()) {
        handle = ATT_CHARACTERISTIC_7D6B0004_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE;
        bytes = outbound_[outbound_index_];
        indication_ = Indication::Provisioning;
    } else if (wtp_indications_enabled() && endpoint_ && !endpoint_->closed()) {
        bytes = endpoint_->output();
        const auto mtu = att_server_get_mtu(connection_);
        const auto maximum = mtu > 3 ? std::min<std::size_t>(64, mtu - 3) : 0;
        if (bytes.empty() || !maximum)
            return;
        bytes = bytes.first(std::min(bytes.size(), maximum));
        handle = wtp_status_handle();
        wtp_indication_bytes_ = bytes.size();
        indication_ = Indication::Wtp;
    } else {
        return;
    }
    diagnostics_.last_indication_status = att_server_indicate(
        connection_, handle, bytes.data(), static_cast<std::uint16_t>(bytes.size()));
    if (diagnostics_.last_indication_status == ERROR_CODE_SUCCESS) {
        ++diagnostics_.indications_started;
        if (indication_ == Indication::Provisioning && outbound_index_ + 1 == outbound_.size())
            session_.response_started(now());
    } else {
        indication_ = Indication::None;
        wtp_indication_bytes_ = 0;
        (void)gap_disconnect(connection_);
    }
}

std::uint16_t PicoGattTransport::read_callback(hci_con_handle_t connection, std::uint16_t handle,
                                               std::uint16_t offset, std::uint8_t* buffer,
                                               std::uint16_t size) {
    if (!owner_ || connection != owner_->connection_)
        return 0;
    if (handle ==
        ATT_CHARACTERISTIC_7D6B0004_5BF1_4F21_A486_3E8F70C12201_01_CLIENT_CONFIGURATION_HANDLE)
        return att_read_callback_handle_little_endian_16(owner_->status_cccd_, offset, buffer,
                                                         size);
    if (handle ==
        ATT_CHARACTERISTIC_7D6B0006_5BF1_4F21_A486_3E8F70C12201_01_CLIENT_CONFIGURATION_HANDLE)
        return att_read_callback_handle_little_endian_16(owner_->wtp_cccd_, offset, buffer, size);
    if (handle != ATT_CHARACTERISTIC_7D6B0002_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE)
        return 0;
    return att_read_callback_handle_blob(
        reinterpret_cast<const std::uint8_t*>(owner_->identity_.data()),
        static_cast<std::uint16_t>(owner_->identity_.size()), offset, buffer, size);
}

int PicoGattTransport::write_callback(hci_con_handle_t connection, std::uint16_t handle,
                                      std::uint16_t transaction, std::uint16_t offset,
                                      std::uint8_t* buffer, std::uint16_t size) {
    if (!owner_ || connection != owner_->connection_)
        return ATT_ERROR_WRITE_NOT_PERMITTED;
    const bool provisioning_cccd =
        handle ==
        ATT_CHARACTERISTIC_7D6B0004_5BF1_4F21_A486_3E8F70C12201_01_CLIENT_CONFIGURATION_HANDLE;
    const bool wtp_cccd =
        handle ==
        ATT_CHARACTERISTIC_7D6B0006_5BF1_4F21_A486_3E8F70C12201_01_CLIENT_CONFIGURATION_HANDLE;
    if (provisioning_cccd || wtp_cccd) {
        ++owner_->diagnostics_.cccd_writes;
        if (transaction != ATT_TRANSACTION_MODE_NONE || offset || !buffer || size != 2) {
            ++owner_->diagnostics_.cccd_rejections;
            if (transaction != ATT_TRANSACTION_MODE_NONE)
                return ATT_ERROR_REQUEST_NOT_SUPPORTED;
            return offset ? ATT_ERROR_INVALID_OFFSET : ATT_ERROR_INVALID_ATTRIBUTE_VALUE_LENGTH;
        }
        const auto value = little_endian_read_16(buffer, 0);
        if (value != 0 && value != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION) {
            ++owner_->diagnostics_.cccd_rejections;
            return ATT_ERROR_VALUE_NOT_ALLOWED;
        }
        (provisioning_cccd ? owner_->status_cccd_ : owner_->wtp_cccd_) = value;
        if (provisioning_cccd && value == 0)
            owner_->inbound_.reset();
        const bool selected_wtp_cccd =
            owner_->session_.wtp_over_field_status() ? provisioning_cccd : wtp_cccd;
        if (selected_wtp_cccd && value == 0 && owner_->endpoint_)
            owner_->endpoint_->disconnect();
        return ATT_ERROR_SUCCESS;
    }
    if (handle == ATT_CHARACTERISTIC_7D6B0005_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE) {
        if (transaction != ATT_TRANSACTION_MODE_NONE)
            return ATT_ERROR_REQUEST_NOT_SUPPORTED;
        if (offset)
            return ATT_ERROR_INVALID_OFFSET;
        if (!buffer || !size || size > 64)
            return ATT_ERROR_INVALID_ATTRIBUTE_VALUE_LENGTH;
        if (!owner_->admit() || !owner_->session_.authorized())
            return ATT_ERROR_INSUFFICIENT_AUTHENTICATION;
        if (!owner_->wtp_indications_enabled() || !owner_->ensure_wtp_endpoint() ||
            !owner_->endpoint_->can_receive())
            return ATT_ERROR_INSUFFICIENT_RESOURCES;
        owner_->in_write_callback_ = true;
        const auto consumed = owner_->endpoint_->receive(std::span(buffer, size), owner_->now());
        if (consumed == size) {
            ++owner_->diagnostics_.wtp_write_segments;
            owner_->diagnostics_.wtp_write_bytes += size;
        }
        if (owner_->output_pending() && owner_->indication_ == Indication::None &&
            !owner_->send_requested_)
            (void)owner_->request_send();
        owner_->in_write_callback_ = false;
        return consumed == size ? ATT_ERROR_SUCCESS : ATT_ERROR_INSUFFICIENT_RESOURCES;
    }
    if (handle != ATT_CHARACTERISTIC_7D6B0003_5BF1_4F21_A486_3E8F70C12201_01_VALUE_HANDLE)
        return ATT_ERROR_WRITE_NOT_PERMITTED;
    if (transaction != ATT_TRANSACTION_MODE_NONE)
        return ATT_ERROR_REQUEST_NOT_SUPPORTED;
    if (offset)
        return ATT_ERROR_INVALID_OFFSET;
    if (!owner_->admit())
        return ATT_ERROR_INSUFFICIENT_AUTHENTICATION;
    if (owner_->status_cccd_ != GATT_CLIENT_CHARACTERISTICS_CONFIGURATION_INDICATION) {
        owner_->inbound_.reset();
        return ATT_ERROR_INSUFFICIENT_RESOURCES;
    }
    ++owner_->diagnostics_.command_frames;
    const auto result = owner_->inbound_.receive(std::span(buffer, size));
    if (result == FrameResult::Pending)
        return ATT_ERROR_SUCCESS;
    if (result != FrameResult::Complete)
        return result == FrameResult::Oversize ? ATT_ERROR_INVALID_ATTRIBUTE_VALUE_LENGTH
                                               : ATT_ERROR_VALUE_NOT_ALLOWED;
    ++owner_->diagnostics_.commands_completed;
    const auto message = owner_->inbound_.message();
    const bool previous_wtp_carrier = owner_->session_.wtp_over_field_status();
    auto response = owner_->session_.handle(
        std::string_view(reinterpret_cast<const char*>(message.data()), message.size()),
        owner_->now());
    const bool wtp_carrier_changed =
        previous_wtp_carrier != owner_->session_.wtp_over_field_status();
    if (wtp_carrier_changed && owner_->endpoint_)
        owner_->endpoint_->disconnect();
    owner_->inbound_.reset();
    owner_->in_write_callback_ = true;
    const bool queued = response.notify() && owner_->queue(response.notification);
    owner_->in_write_callback_ = false;
    if (!queued) {
        if (wtp_carrier_changed) {
            owner_->session_.disconnected();
            (void)gap_disconnect(owner_->connection_);
        }
        return ATT_ERROR_INSUFFICIENT_RESOURCES;
    }
    if (owner_->session_.authorized())
        (void)owner_->ensure_wtp_endpoint();
    return ATT_ERROR_SUCCESS;
}

void PicoGattTransport::hci_callback(std::uint8_t packet_type, std::uint16_t, std::uint8_t* packet,
                                     std::uint16_t) {
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
            owner_->connection_ = gap_subevent_le_connection_complete_get_connection_handle(packet);
            ++owner_->diagnostics_.connections;
            sm_request_pairing(owner_->connection_);
        }
        break;
    case HCI_EVENT_ENCRYPTION_CHANGE:
        if (hci_event_encryption_change_get_connection_handle(packet) == owner_->connection_) {
            owner_->encrypted_ = hci_event_encryption_change_get_status(packet) == 0 &&
                                 hci_event_encryption_change_get_encryption_enabled(packet);
            if (owner_->encrypted_)
                (void)owner_->admit();
            else {
                owner_->security_lost();
                (void)gap_disconnect(owner_->connection_);
            }
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
        if (hci_event_disconnection_complete_get_connection_handle(packet) == owner_->connection_) {
            ++owner_->diagnostics_.disconnections;
            owner_->diagnostics_.last_disconnect_reason =
                hci_event_disconnection_complete_get_reason(packet);
            owner_->disconnected();
        }
        break;
    default:
        break;
    }
}

void PicoGattTransport::att_callback(std::uint8_t packet_type, std::uint16_t, std::uint8_t* packet,
                                     std::uint16_t) {
    if (!owner_ || packet_type != HCI_EVENT_PACKET ||
        hci_event_packet_get_type(packet) != ATT_EVENT_HANDLE_VALUE_INDICATION_COMPLETE ||
        att_event_handle_value_indication_complete_get_conn_handle(packet) != owner_->connection_)
        return;
    ++owner_->diagnostics_.indication_completions;
    owner_->diagnostics_.last_completion_status =
        att_event_handle_value_indication_complete_get_status(packet);
    if (owner_->diagnostics_.last_completion_status != 0) {
        (void)gap_disconnect(owner_->connection_);
        return;
    }
    const auto completed = owner_->indication_;
    owner_->indication_ = Indication::None;
    if (completed == Indication::Provisioning) {
        ++owner_->outbound_index_;
        if (owner_->outbound_index_ == owner_->outbound_.size()) {
            for (auto& frame : owner_->outbound_)
                std::fill(frame.begin(), frame.end(), 0);
            owner_->outbound_.clear();
            owner_->outbound_index_ = 0;
            ++owner_->diagnostics_.responses_delivered;
            owner_->session_.response_delivered(owner_->now());
        }
    } else if (completed == Indication::Wtp) {
        // Authorization expiry or a CCCD write can close the logical endpoint
        // while the controller still owes this ATT completion.
        if (owner_->endpoint_ && !owner_->endpoint_->closed()) {
            owner_->endpoint_->consume_output(owner_->wtp_indication_bytes_, owner_->now());
            ++owner_->diagnostics_.wtp_indication_segments;
            owner_->diagnostics_.wtp_indication_bytes += owner_->wtp_indication_bytes_;
        }
        owner_->wtp_indication_bytes_ = 0;
    }
    if (owner_->output_pending() && !owner_->request_send())
        (void)gap_disconnect(owner_->connection_);
}
} // namespace wsprrypico::provisioning

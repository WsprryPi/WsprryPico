#ifdef WSPRRY_PICO_LED_ACCEPTANCE
#include "hardware/gpio.h"
#include "hardware/sync.h"
#include "pico/time.h"
#include "provisioning/led_acceptance.hpp"
namespace wsprrypico::provisioning {
LedAcceptance led_acceptance;
}
#ifndef WSPRRY_PICO_STANDALONE_RF
namespace {
int64_t led_release_hold(alarm_id_t, void*) {
    gpio_set_dir(15, GPIO_IN);
    return 0;
}
} // namespace
#endif
#endif
#include "firmware_identity.hpp"
#include "hardware/clocks.h"
#include "hardware/structs/watchdog.h"
#include "hardware/watchdog.h"
#include "network/identity.hpp"
#include "network/pico/bootstrap_server.hpp"
#include "network/pico/server.hpp"
#include "network/softap_api.hpp"
#include "network_credentials.hpp"
#include "pico/bootrom.h"
#include "pico/cyw43_arch.h"
#include "pico/time.h"
#include "pico_adapters.hpp"
#include "provisioning/access.hpp"
#include "provisioning/ble_session.hpp"
#include "provisioning/command.hpp"
#include "provisioning/local_access.hpp"
#include "provisioning/manager.hpp"
#include "provisioning/pico/activation_platform.hpp"
#include "provisioning/pico/consumer_claim_platform.hpp"
#include "provisioning/pico/consumer_tls_generator.hpp"
#include "provisioning/pico/consumer_tls_validator.hpp"
#include "provisioning/pico/credential_validator.hpp"
#include "provisioning/pico/field_platform.hpp"
#ifdef WSPRRY_PICO_PHASE12_INDICATOR_FAULT_FIXTURE
#include "provisioning/pico/indicator_fault_fixture.hpp"
#endif
#include "runtime/activity_trace.hpp"
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
#include "provisioning/button_runtime.hpp"
#include "provisioning/pico/gp14_capture.hpp"
#endif
#ifdef WSPRRY_PICO_GP14_FLASH_PROBE
#include "provisioning/pico/gp14_flash_probe.hpp"
#endif
#include "provisioning/pico/gatt_transport.hpp"
#include "provisioning/reset_storage.hpp"
#ifdef WSPRRY_PICO_PHASE12_FAULT_FIXTURE
#include "provisioning/pico/phase12_fault_fixture.hpp"
#endif
#include "provisioning/runtime.hpp"
#include "runtime/pico/btstack_acl_metrics.hpp"
#include "runtime/pico/btstack_pool_metrics.hpp"
#include "runtime/pico/heap_metrics.h"
#include "runtime/pico/stack_guard.h"
#include "standalone/heap_probe.hpp"
#include "standalone/pico/adapters.hpp"
#include "standalone/scheduler.hpp"
#include "standalone/wtp_profile.hpp"
#include "time/controller_time.hpp"
#include "tusb.h"
#include "usb/reply_priority.hpp"
#include "usb/transport.hpp"
#include "wtp/codec.hpp"
#include "wtp/endpoint.hpp"
#include "wtp/json.hpp"
#include "wtp/memory_budget.hpp"

#ifndef WSPRRY_PICO_CONSUMER_LAN_MODE
#define WSPRRY_PICO_CONSUMER_LAN_MODE 2
#endif

#include <malloc.h>
extern "C" char __HeapLimit, __end__, __StackLimit, __StackTop;
#include "hardware/sync.h"
#ifdef WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC
#include "pico/flash.h"
#include "pico/multicore.h"

#include <atomic>
#endif
#ifdef WSPRRY_PICO_STANDALONE_RF
#include "rf/pico/worker.hpp"
#include "rf/waveform.hpp"
#else
#include "standalone/dry_run_engine.hpp"
static_assert(WSPRRY_PICO_RF_OUTPUT_DISABLED == 1);
#endif
#include "provisioning/pico/bootsel_sampler.hpp"
#include "provisioning/rf_setup_gate.hpp"
#include "runtime/allocation_fault.h"
#include "usb/console_reply.hpp"

#include <array>
#include <charconv>

// Capture the exception's PC without allocating or relying on USB. The
// watchdog performs the reset; the next boot inhibits autonomous operation.
extern "C" [[noreturn]] void wsprrypico_hardfault(const std::uint32_t* frame,
                                                  std::uint32_t exception_return) {
    if (!(exception_return & 16))
        frame += 18;
    const auto address = reinterpret_cast<std::uintptr_t>(frame);
    watchdog_hw->scratch[0] = *reinterpret_cast<volatile std::uint32_t*>(0xe000ed28);
    watchdog_hw->scratch[3] = address >= 0x20000000 && address <= 0x20081fe0 ? frame[6] : 1;
    while (true)
        tight_loop_contents();
}
extern "C" __attribute__((naked)) void isr_hardfault() {
    asm volatile("tst lr, #4\n"
                 "ite eq\n"
                 "mrseq r0, msp\n"
                 "mrsne r0, psp\n"
                 "mov r1, lr\n"
                 "b wsprrypico_hardfault\n");
}
// Retain only the constant format string's hash, never formatted arguments.
// The watchdog resets into recovery even when USB is not being serviced.
extern "C" [[noreturn]] void wsprrypico_panic(const char* format, ...) {
    std::uint32_t hash = 2166136261U;
    if (format)
        for (unsigned i = 0; i < 192 && format[i]; ++i)
            hash = (hash ^ static_cast<unsigned char>(format[i])) * 16777619U;
    watchdog_hw->scratch[2] = hash;
    if (hash == WSPRRY_ALLOCATION_FAULT_HASH) {
        std::uint32_t attempt[2];
        wsprry_heap_panic_attempt(attempt);
        watchdog_hw->scratch[0] = attempt[0];
        watchdog_hw->scratch[3] = attempt[1];
    }
    while (true)
        tight_loop_contents();
}
namespace {
#ifdef WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC
alignas(8) std::uint32_t bootsel_reader_stack[2048]; // 8 KiB, including 4 KiB guard reserve.
std::atomic<std::uint32_t> bootsel_reader_ready{0};
std::atomic<std::uint32_t> bootsel_reader_count{0};
void bootsel_flash_reader() {
    const auto guard = wsprry_stack_guard_snapshot();
    if (!guard.valid || guard.bottom != reinterpret_cast<std::uintptr_t>(bootsel_reader_stack) ||
        !flash_safe_execute_core_init()) {
        bootsel_reader_ready.store(2, std::memory_order_release);
        while (true)
            tight_loop_contents();
    }
    bootsel_reader_ready.store(1, std::memory_order_release);
    const auto* flash = reinterpret_cast<const volatile std::uint32_t*>(0x10010000u);
    while (true) {
        const auto word = *flash;
        bootsel_reader_count.fetch_add(word | 1u, std::memory_order_relaxed);
    }
}
#endif
constexpr std::uint32_t stack_pattern = 0xa59c37e1;
__attribute__((noinline)) void paint_stack() {
    const auto saved = save_and_disable_interrupts();
    std::uintptr_t sp;
    asm volatile("mov %0, sp" : "=r"(sp));
    for (auto p = reinterpret_cast<std::uintptr_t>(&__StackLimit); p + 128 < sp; p += 4)
        *reinterpret_cast<volatile std::uint32_t*>(p) = stack_pattern;
    restore_interrupts(saved);
}
std::size_t stack_used() {
    auto p = reinterpret_cast<std::uintptr_t>(&__StackLimit);
    const auto top = reinterpret_cast<std::uintptr_t>(&__StackTop);
    while (p < top && *reinterpret_cast<volatile std::uint32_t*>(p) == stack_pattern)
        p += 4;
    return top - p;
}
// Serialize one field at a time: a single giant operator+ expression retains
// many string temporaries, inflating the very heap and stack INFO observes.
__attribute__((noinline)) void number_field(std::string& result, std::string_view name,
                                            std::uint64_t value, bool quoted = false,
                                            bool present = true) {
    result.append(",\"").append(name).append("\":");
    if (!present) {
        result.append("null");
        return;
    }
    char digits[20]; // Maximum decimal width of uint64_t.
    const auto converted = std::to_chars(std::begin(digits), std::end(digits), value);
    if (quoted)
        result.push_back('"');
    result.append(digits, converted.ptr);
    if (quoted)
        result.push_back('"');
}
#ifdef WSPRRY_PICO_STANDALONE_RF
void reserve_field(std::string& result, std::string_view name,
                   const wsprrypico::rf::RefillMetrics::Reserve& reserve) {
    result.append(",\"").append(name).append("\":");
    if (!reserve.observations) {
        result.append("null");
        return;
    }
    result.append("{\"measured\":true");
    number_field(result, "observations", reserve.observations);
    number_field(result, "epoch", reserve.epoch, true);
    number_field(result, "successor_sequence", reserve.sequence, true);
    number_field(result, "observed_ns", reserve.observed_ns, true);
    number_field(result, "remaining_words", reserve.remaining_words);
    number_field(result, "total_words", reserve.total_words);
    result.push_back('}');
}
#endif
std::size_t heap_peak = 0;
std::uint64_t monotonic_now(void*) {
    return time_us_64() * 1000ULL;
}
std::uint64_t monotonic_ms(void*) {
    return time_us_64() / 1000ULL;
}
bool softap_interface(const tcp_pcb* pcb, void*) {
    return pcb && IP_IS_V4(&pcb->local_ip) &&
           ip4_addr_cmp(ip_2_ip4(&pcb->local_ip), netif_ip4_addr(&cyw43_state.netif[CYW43_ITF_AP]));
}
wsprrypico::provisioning::Activity provisioning_activity(void* context) {
    const auto current = static_cast<wsprrypico::wtp::JobService*>(context)->activity();
    return {current.owned,
            true,
            current.output_active,
            current.state == wsprrypico::wtp::State::Armed,
            current.state == wsprrypico::wtp::State::Running,
            current.state == wsprrypico::wtp::State::Failed};
}
std::string_view access_code_name(wsprrypico::provisioning::AccessCode code) {
    using wsprrypico::provisioning::AccessCode;
    switch (code) {
    case AccessCode::Ok:
        return "ok";
    case AccessCode::Invalid:
        return "invalid_request";
    case AccessCode::AuthenticationRequired:
        return "authentication_required";
    case AccessCode::ConfirmationRequired:
        return "confirmation_required";
    case AccessCode::WrongDevice:
        return "wrong_device";
    case AccessCode::Busy:
        return "busy";
    case AccessCode::Capacity:
        return "capacity";
    case AccessCode::Expired:
        return "expired";
    case AccessCode::Conflict:
        return "conflict";
    case AccessCode::StorageFault:
        return "storage_fault";
    case AccessCode::BondEraseFault:
        return "bond_erase_fault";
    }
    return "invalid_request";
}
std::string access_reply(wsprrypico::provisioning::AccessCode code) {
    return std::string("{\"ok\":") +
           (code == wsprrypico::provisioning::AccessCode::Ok ? "true" : "false") +
           (code == wsprrypico::provisioning::AccessCode::Ok
                ? "}\n"
                : ",\"error\":" + wsprrypico::wtp::json::quote(access_code_name(code)) + "}\n");
}
} // namespace
int main() {
    paint_stack();
    wsprrypico::wtp::allocate_input = wsprry_heap_try_input;
    wsprrypico::wtp::available_memory = []() -> std::size_t {
        const auto capacity = reinterpret_cast<std::uintptr_t>(&__HeapLimit) -
                              reinterpret_cast<std::uintptr_t>(&__end__);
        const auto used = static_cast<std::size_t>(mallinfo().uordblks);
        heap_peak = std::max(heap_peak, used);
        return used < capacity ? capacity - used : 0;
    };
    // SDK uses scratch 4..7 for reboot bookkeeping. Preserve a small diagnostic
    // in 0..3, and enter an unowned, network-free recovery boot after a stall.
#ifdef WSPRRY_PICO_PHASE12_FAULT_FIXTURE
    wsprrypico::provisioning::phase12_fault_capture_boot();
#endif
    const bool recovery = watchdog_enable_caused_reboot();
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
    constexpr std::uint32_t gp14_reset_magic = 0x47503152; // GP1R
    const bool gp14_prior_reset =
        watchdog_caused_reboot() && !recovery && watchdog_hw->scratch[0] == gp14_reset_magic;
    const auto gp14_prior_duration_ms = gp14_prior_reset ? watchdog_hw->scratch[2] : 0u;
#ifdef WSPRRY_PICO_GP14_RF_ACCEPTANCE
    const auto gp14_prior_rf_decision_after_launch_us =
        gp14_prior_reset ? watchdog_hw->scratch[3] : 0u;
#endif
#endif
    const auto fault_stage = recovery ? watchdog_hw->scratch[1] : 0;
    const auto fault_hash = recovery ? watchdog_hw->scratch[2] : 0;
    const auto saved_pc = recovery ? watchdog_hw->scratch[3] : 0;
    const auto saved_status = recovery ? watchdog_hw->scratch[0] : 0;
    const bool allocation_fault = wsprry_allocation_fault_valid(recovery, fault_hash, saved_pc);
    const auto fault_pc = allocation_fault ? 0 : saved_pc;
    const auto fault_status = allocation_fault ? 0 : saved_status;
    watchdog_hw->scratch[0] = 0;
    watchdog_hw->scratch[2] = 0;
    watchdog_hw->scratch[3] = 0;
    watchdog_hw->scratch[1] = 1;
    watchdog_enable(8000, true);
#ifdef WSPRRY_PICO_PHASE12_FAULT_FIXTURE
    wsprrypico::provisioning::phase12_fault_restore_marker();
#endif

#ifdef WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC
    multicore_launch_core1_with_stack(bootsel_flash_reader, bootsel_reader_stack,
                                      sizeof(bootsel_reader_stack));
#endif

#ifdef WSPRRY_PICO_STANDALONE_RF
    set_sys_clock_khz(wsprrypico::rf::sample_rate / 1000, true);
#endif
    tud_init(0);
    const auto discipline = wsprrypico::standalone::clock_profile();
    static wsprrypico::time::UtcDiscipline clock(monotonic_now, nullptr, discipline);
    static wsprrypico::standalone::PicoFlash flash;
    static wsprrypico::standalone::Store store(flash);
    const bool store_loaded = store.load();
    static wsprrypico::standalone::PicoProfileMedia profile_media;
    static wsprrypico::provisioning::ProfileStore profile_store(profile_media);
    const bool profile_store_loaded = profile_store.load();
    static wsprrypico::standalone::PicoAccessMedia access_media;
    static wsprrypico::provisioning::AccessStore access_store(access_media);
    const bool access_store_loaded = access_store.load();
    const bool access_recovery =
        !access_store_loaded ||
        access_store.state() != wsprrypico::provisioning::AccessStoreState::Healthy ||
        (access_store.record() && access_store.record()->reset.pending());
    const bool boot_recovery = recovery || access_recovery;
    auto boot_pins = store.config() ? store.config()->pins : wsprrypico::hardware::PinPlan{};
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
    // Only the selected indicator differs; all pin ownership checks still apply.
    boot_pins.indicator_gp.reset();
#if WSPRRY_PICO_LED_SELECTION == 1 || WSPRRY_PICO_LED_SELECTION == 2
    boot_pins.indicator = wsprrypico::hardware::PinPlan::Indicator::External;
    boot_pins.indicator_gp = WSPRRY_PICO_LED_SELECTION == 1 ? 15 : 16;
    boot_pins.indicator_active_high = WSPRRY_PICO_LED_SELECTION == 1;
#elif WSPRRY_PICO_LED_SELECTION == 3
    boot_pins.indicator = wsprrypico::hardware::PinPlan::Indicator::Disabled;
#else
    boot_pins.indicator = wsprrypico::hardware::PinPlan::Indicator::Onboard;
#endif
#endif
    // Both adapters claim PIO/DMA resources through the SDK allocator.
#ifdef WSPRRY_PICO_STANDALONE_RF
    static wsprrypico::rf::IndicatorGate tx_indicator_gate(
        boot_pins.indicator != wsprrypico::hardware::PinPlan::Indicator::Disabled);
    auto& engine = wsprrypico::rf::start_worker(clock, boot_pins, store_loaded && store.healthy(),
                                                tx_indicator_gate);
#else
    static wsprrypico::standalone::DryRunEngine engine;
#endif
    static wsprrypico::firmware::PicoIdentitySource identities;
    static wsprrypico::provisioning::RuntimeProfile runtime_profile;
    const auto build_bundle = wsprrypico::provisioning::classify_build_bundle(
        identities.device_id(),
        {wsprrypico::network::credentials::device_id, wsprrypico::network::credentials::hostname,
         wsprrypico::network::credentials::port, wsprrypico::network::credentials::certificate,
         wsprrypico::network::credentials::key, wsprrypico::network::credentials::ca});
    const bool runtime_profile_loaded =
        profile_store_loaded &&
        runtime_profile.load(profile_store, identities.device_id(), build_bundle);
    // Source 5 may join station for time, but owner and TLS authority are not
    // active at structural admission. Deny every legacy control path.
    const auto consumer_source_selected = [&]() {
        return profile_store.source() == wsprrypico::provisioning::ProfileSource::ConsumerProfile;
    };
#ifdef WSPRRY_PICO_STANDALONE_RF
    const auto config = wsprrypico::standalone::wtp_profile(true);
#else
    const auto config = wsprrypico::standalone::wtp_profile(false);
#endif
    static wsprrypico::wtp::JobService service(clock, engine, identities, config);
    static wsprrypico::wtp::Endpoint endpoint(service, identities.device_id(),
                                              wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::wtp::Endpoint ble_endpoint(service, identities.device_id(),
                                                  wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::standalone::Scheduler scheduler(store, service);
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
    static wsprrypico::provisioning::PicoGp14Capture gp14_button(boot_pins.button);
    bool gp14_fault_handled = false;
    bool gp14_reset_pending = false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    bool gp14_worker_inhibit_handled = false;
#endif
    const auto stop_for_gp14 = [&]() {
        const bool verified = service.local_inhibit_output();
        (void)scheduler.command("STOP");
        if (!verified && engine.output_active()) {
            watchdog_hw->scratch[2] = 0x47503146; // GP1F: failed physical output stop.
            while (true)
                tight_loop_contents(); // Watchdog enters inhibited recovery.
        }
        return verified;
    };
    const bool gp14_capture_ready = gp14_button.start();
    if (!gp14_capture_ready) {
        (void)stop_for_gp14();
        gp14_fault_handled = true;
    }
#endif
    wsprrypico::provisioning::CredentialMaterial tls_credentials;
    if (runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::Provisioned)
        tls_credentials = wsprrypico::provisioning::credentials(*runtime_profile.profile());
    else if (runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::Factory)
        tls_credentials = {wsprrypico::network::credentials::device_id,
                           wsprrypico::network::credentials::hostname,
                           wsprrypico::network::credentials::port,
                           wsprrypico::network::credentials::certificate,
                           wsprrypico::network::credentials::key,
                           wsprrypico::network::credentials::ca};
    else if (runtime_profile.consumer_profile()) {
        const auto& tls = runtime_profile.consumer_profile()->tls;
        tls_credentials = {runtime_profile.consumer_profile()->device_id,
                           tls.hostname,
                           tls.port,
                           tls.server_certificate,
                           tls.server_private_key,
                           tls.ca_certificate};
    }
    const bool network_only_source =
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::NetworkOnly;
    const bool local_wtp =
        network_only_source ||
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::ConsumerPreClock;
    const bool plain_lan_wtp = local_wtp && WSPRRY_PICO_CONSUMER_LAN_MODE == 1;
    const bool tls_lan_wtp = local_wtp && WSPRRY_PICO_CONSUMER_LAN_MODE == 2;
    constexpr unsigned plain_lan_port = 31417;
    bool deployment_matches =
        runtime_profile_loaded && !access_recovery && !tls_credentials.device_id.empty() &&
        !tls_credentials.hostname.empty() && tls_credentials.port != 0 &&
        wsprrypico::network::deployment_identity_matches(
            identities.device_id(), tls_credentials.device_id, tls_credentials.hostname);
    static wsprrypico::time::ControllerTimeArbiter time_arbiter(clock, monotonic_now, nullptr,
                                                                identities.device_id());
    static wsprrypico::standalone::PicoNetwork network(time_arbiter, tls_credentials.hostname);
    const bool radio_identity_ok = network.initialize_radio();
    const auto derived_identity =
        radio_identity_ok ? wsprrypico::provisioning::derive_local_identity(identities.device_id(),
                                                                            network.station_mac())
                          : std::nullopt;
    const auto local_identity =
        derived_identity.value_or(wsprrypico::provisioning::LocalIdentity{});
    const bool network_hostname_ready =
        !network_only_source ||
        (derived_identity && network.configure_hostname(local_identity.hostname));
    static wsprrypico::provisioning::PicoBondStore bond_store;
    static wsprrypico::provisioning::PicoRandomSource random_source;
    static wsprrypico::provisioning::LocalAccessController local_access(
        access_store, bond_store, random_source, identities.device_id(), service.status().boot_id,
        local_identity
#ifdef WSPRRY_PICO_PHASE12_SESSION_DEADLINE_FIXTURE
        ,
        wsprrypico::provisioning::SoftApSessionLimits{15'000, 60'000}
#endif
    );
    static wsprrypico::provisioning::ResetStorageTargets reset_targets(
        store, flash, profile_media, bond_store, provisioning_activity, &service,
        +[](void* p) {
            return static_cast<wsprrypico::provisioning::PicoBondStore*>(p)->erase_reset_storage();
        },
        &bond_store);
    static wsprrypico::provisioning::ResetCoordinator reset_coordinator(
        access_store, profile_store, reset_targets, local_identity);
#ifdef WSPRRY_PICO_PHASE12_FAULT_FIXTURE
    reset_coordinator.checkpoint_observer(wsprrypico::provisioning::phase12_reset_checkpoint);
#endif
    // No network/control runtime has started yet. A persisted intent is the
    // authority to finish the same operation; completion requires a fresh boot.
    if (reset_coordinator.pending() && derived_identity) {
        (void)scheduler.command("STOP");
        if (engine.disable(monotonic_now(nullptr) + 100'000'000ULL) && !engine.output_active() &&
            reset_coordinator.resume() == wsprrypico::provisioning::ResetResult::Complete) {
            watchdog_reboot(0, 0, 1);
            while (true)
                tight_loop_contents();
        }
    }
    static wsprrypico::provisioning::SoftApCoordinator softap_coordinator(access_store);
    softap_coordinator.no_profile(
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::Unprovisioned ||
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::NetworkOnly ||
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::ConsumerPreClock ||
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::Fault);
    softap_coordinator.blank_profile(runtime_profile.source() ==
                                     wsprrypico::provisioning::RuntimeSource::Unprovisioned);
    softap_coordinator.recovery(boot_recovery);
#ifdef WSPRRY_PICO_PHASE12_FAULT_FIXTURE
    // Test-only, RF-inhibited access window. Consumer USB field commands remain
    // unavailable; the unattended recovery observer uses the ordinary AP API.
    (void)softap_coordinator.request_join_grace(time_us_64() / 1000ULL);
#endif
    static wsprrypico::provisioning::PicoSoftAp softap;
    std::optional<wsprrypico::standalone::Config> runtime_network_config;
    if (store_loaded && store.config())
        runtime_network_config = runtime_profile.overlay(*store.config());
    else if (store_loaded &&
             runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::ConsumerPreClock)
        runtime_network_config = runtime_profile.overlay(wsprrypico::standalone::Config{});
    if (boot_recovery || !runtime_profile_loaded ||
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::Unprovisioned ||
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::NetworkOnly ||
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::ConsumerPreClock)
        (void)scheduler.command("STOP");
    watchdog_hw->scratch[1] = 2;
    if (!boot_recovery && radio_identity_ok && runtime_network_config)
        (void)network.start(*runtime_network_config);
    else if (!boot_recovery && radio_identity_ok && runtime_profile.network_profile())
        (void)network.start_network_only(runtime_profile.network_profile()->ssid,
                                         runtime_profile.network_profile()->password,
                                         runtime_profile.network_profile()->time_server);
    static wsprrypico::network::BrowserApi browser_api(service, store, scheduler, network,
                                                       identities.device_id(),
                                                       wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::provisioning::ConsumerTls network_only_tls;
    static wsprrypico::network::PicoServer server(
        service, browser_api, identities.device_id(), wsprrypico::firmware::kFirmwareVersion,
        tls_credentials,
        tls_lan_wtp ? wsprrypico::network::PicoServer::Admission::LocalWtp
        : local_wtp ? wsprrypico::network::PicoServer::Admission::SoftApOnly
                    : wsprrypico::network::PicoServer::Admission::ClientCertificate);
    wsprrypico::network::install_tls_time_source(service);
    const auto softap_authority =
        local_identity.hostname +
        (server.port() == 0 || server.port() == 443 ? "" : ":" + std::to_string(server.port()));
    static wsprrypico::provisioning::SoftApHttpAdmission softap_admission(
        local_access, identities.device_id(), softap_authority);
    static wsprrypico::network::SoftApApi softap_api(browser_api, softap_admission, local_access,
                                                     time_arbiter, service, identities.device_id(),
                                                     wsprrypico::firmware::kFirmwareVersion);
    server.softap_handler(&softap_api, softap_interface, nullptr);
    static wsprrypico::network::PicoBootstrapServer bootstrap(
        identities.device_id(), wsprrypico::firmware::kFirmwareVersion, softap_interface, nullptr);
    // Source 5 exposes public owner claim status only. The plaintext listener
    // must not expose a legacy mutation route to a consumer profile.
    const auto blank_access_available = []() {
        return access_store.state() == wsprrypico::provisioning::AccessStoreState::Erased ||
               (access_store.state() == wsprrypico::provisioning::AccessStoreState::Healthy &&
                access_store.record() && !access_store.record()->reset.pending());
    };
    const bool bootstrap_started =
        derived_identity && blank_access_available() && bootstrap.start();
    browser_api.set_active_job_connections(true);
    bool server_start_attempted = false;
    bool plain_start_attempted = false;
    std::uint64_t tls_retry_at_ms = 0;
    std::uint64_t plain_retry_at_ms = 0;
    static wsprrypico::provisioning::PicoIndicatorOutput indicator_output(
        boot_pins, wsprrypico::provisioning::PicoIndicatorOutput::Role::Operational);
    static wsprrypico::provisioning::PicoIndicatorOutput transmit_indicator_output(boot_pins);
    static wsprrypico::provisioning::IndicatorController indicator(
        indicator_output, identities.device_id(),
        boot_pins.indicator == wsprrypico::hardware::PinPlan::Indicator::External
            ? &transmit_indicator_output
            : nullptr);
    static wsprrypico::provisioning::PicoConsumerClaimPlatform claim_platform(
        access_store, network, service, time_arbiter, local_identity.hostname);
    indicator.enabled(boot_pins.indicator != wsprrypico::hardware::PinPlan::Indicator::Disabled);
    const auto poll_indicator = [&]() {
        const auto now_ms = time_us_64() / 1000ULL;
#ifdef WSPRRY_PICO_STANDALONE_RF
        indicator.poll_transmit(tx_indicator_gate, now_ms);
#else
        indicator.transmitting(false); // Dry-run activity never requests solid TX.
        indicator.poll(now_ms);
#endif
    };
    bootstrap.configure(service.status().boot_id, access_store, profile_store, random_source,
                        indicator, network, runtime_profile, claim_platform,
                        local_identity.default_password);
    bootstrap.configure_recovery(service.status().boot_id, access_store, random_source);
    // A Wi-Fi-only source has not generated its TLS identity yet. Do not turn
    // that pending state into a permanent mDNS identity failure.
    network.listener_status(server.configured() || plain_lan_wtp,
                            server.listening() || server.plain_listening(),
                            deployment_matches || network_only_source);
    watchdog_hw->scratch[1] = 3;
    std::array<std::uint8_t, 64> input{};
    std::size_t offset = 0, size = 0;
    std::array<char, wsprrypico::standalone::max_config_bytes + 7> line{};
    std::size_t length = 0;
    bool overflow = false;
    wsprrypico::usb::ConsoleReply console_reply;
    std::array<std::uint8_t, 64> console_input{};
    std::size_t console_input_size = 0, console_input_offset = 0;
    std::uint64_t reboot_at = 0;
    bool bootloader = false, browser_reboot = false;
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
    auto gp14_runtime = wsprrypico::provisioning::ButtonRuntime{
        stop_for_gp14,
        [&](std::uint64_t now_ms, bool held) {
            return softap_coordinator.request_manual_setup(now_ms, true, held);
        },
        [&](std::uint64_t now_ms) { softap_coordinator.manual_button_released(now_ms); },
        [&]() {
            if (!reboot_at) {
                gp14_reset_pending = true;
                bootloader = false;
                browser_reboot = false;
                reboot_at = time_us_64() + 250'000;
            }
        }};
#endif
    struct RestartContext {
        wsprrypico::standalone::Scheduler* scheduler;
        wsprrypico::wtp::RfEngine* output_engine;
        std::uint64_t* at;
        bool* browser;
    } restart_context{&scheduler, &engine, &reboot_at, &browser_reboot};
    const auto schedule_restart = +[](void* context) -> bool {
        auto& state = *static_cast<RestartContext*>(context);
        if (*state.at || !state.scheduler->idle())
            return false;
        (void)state.scheduler->command("STOP");
        if (!state.output_engine->disable(monotonic_now(nullptr) + 100'000'000ULL) ||
            state.output_engine->output_active())
            return false;
        *state.browser = true;
        *state.at = time_us_64() + 250'000;
        return true;
    };
    browser_api.restart_control(schedule_restart, &restart_context);
    bootstrap.restart_control(schedule_restart, &restart_context);
    std::uint64_t recovery_reset_at = 0;
    struct RecoveryResetContext {
        wsprrypico::provisioning::ResetCoordinator* coordinator;
        wsprrypico::standalone::Scheduler* scheduler;
        std::uint64_t* at;
        wsprrypico::provisioning::AccessStore* access;
        const wsprrypico::provisioning::LocalIdentity* identity;
        wsprrypico::wtp::JobService* service;
        wsprrypico::network::PicoServer* server;
    } recovery_reset_context{
        &reset_coordinator, &scheduler, &recovery_reset_at, &access_store, &local_identity,
        &service,           &server};
    bootstrap.reset_control(
        +[](wsprrypico::provisioning::ResetLevel level,
            const wsprrypico::wtp::PayloadDigest& digest, void* context) {
            auto& state = *static_cast<RecoveryResetContext*>(context);
            if (!state.scheduler->idle() ||
                !wsprrypico::provisioning::idle_for_access(provisioning_activity(state.service)))
                return wsprrypico::provisioning::ResetResult::Busy;
            if (state.access->state() == wsprrypico::provisioning::AccessStoreState::Erased) {
                wsprrypico::provisioning::AccessRecord record;
                record.epoch = 1;
                record.password = state.identity->default_password;
                const bool initialized = state.access->initialize(record);
                wsprrypico::provisioning::scrub(record);
                if (!initialized) {
                    (void)state.service->local_inhibit_output();
                    state.server->set_admission(false);
                    *state.at = time_us_64() + 2'000'000;
                    return wsprrypico::provisioning::ResetResult::StorageFault;
                }
            }
            const auto result = state.coordinator->begin(
                level, wsprrypico::provisioning::ProfileSource::Unprovisioned, digest);
            if ((result == wsprrypico::provisioning::ResetResult::Pending ||
                 result == wsprrypico::provisioning::ResetResult::StorageFault) &&
                !*state.at) {
                // Fence shared USB/BLE/LAN job admission within this callback,
                // before another CYW43 callback can accept a new owner.
                (void)state.service->local_inhibit_output();
                state.server->set_admission(false);
                *state.at = time_us_64() + 2'000'000;
            }
            return result;
        },
        &recovery_reset_context);

    static wsprrypico::provisioning::MbedTlsCredentialValidator credential_validator(
        identities.device_id(), &service);
    static wsprrypico::provisioning::PicoActivationPlatform activation_platform(
        profile_store, runtime_profile, service, server, identities.device_id(), schedule_restart,
        &restart_context);
    static wsprrypico::provisioning::ActivationCoordinator activation(activation_platform);
    static wsprrypico::provisioning::Manager provisioning_manager(
        profile_store, credential_validator, identities.device_id(), &activation);
    static wsprrypico::provisioning::CommandAdapter provisioning_command(
        provisioning_manager, identities.device_id(), wsprrypico::provisioning::Transport::Ble);
    static wsprrypico::provisioning::BleCommandSession ble_session(
        local_access, provisioning_command, provisioning_manager, identities.device_id(),
        provisioning_activity, &service);
    ble_session.field_controls(&time_arbiter, &indicator);
    static wsprrypico::provisioning::PicoGattTransport gatt(
        ble_session, &ble_endpoint, provisioning_command.identity(),
        local_identity.advertising_name, monotonic_ms, nullptr);
    bool gatt_start_attempted = false;
#ifdef WSPRRY_PICO_STANDALONE_RF
    std::uint64_t last_loop_us = 0, max_loop_us = 0, max_refill_us = 0;
    std::uint64_t max_usb_us = 0, max_request_us = 0;
    auto maximum = [](std::uint64_t& peak, std::uint64_t start) {
        const auto elapsed = time_us_64() - start;
        if (elapsed > peak)
            peak = elapsed;
    };
#endif
#ifdef WSPRRY_PICO_GP14_FLASH_PROBE
    unsigned gp14_flash_probe_runs = 0;
    bool gp14_flash_probe_failed = false;
#endif
#ifdef WSPRRY_PICO_GP14_RF_ACCEPTANCE
    bool gp14_rf_busy_used = false;
#endif
    auto command = [&](std::string_view text) -> std::string {
        if (reset_coordinator.blocks_admission() || recovery_reset_at)
            return "{\"ok\":false,\"error\":\"reset_pending\"}\n";
        if (text.starts_with("ACTIVITYTRACE ")) {
            auto& trace = wsprrypico::runtime::activity_trace();
            const auto identity_reply = [&]() {
                return "{\"ok\":true,\"schema\":\"wsprrypico-activity-trace/1\",\"device_id\":" +
                       wsprrypico::wtp::json::quote(identities.device_id()) + ",\"revision\":" +
                       wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                       ",\"boot_id\":" + wsprrypico::wtp::json::quote(service.status().boot_id);
            };
            const auto safety_guard = [&]() {
#ifdef WSPRRY_PICO_STANDALONE_RF
                return false;
#else
                const auto activity = service.activity();
                return !recovery && !reboot_at && !bootstrap.setup_pending() && store.healthy() &&
                       profile_store.healthy() && access_store.healthy() &&
                       runtime_profile_loaded &&
                       service.status().state == wsprrypico::wtp::State::Empty && !activity.owned &&
                       !activity.output_active && scheduler.idle() &&
                       (!store.config() || !store.config()->enabled) && !engine.output_active();
#endif
            };
            if (text.starts_with("ACTIVITYTRACE BEGIN ") ||
                text.starts_with("ACTIVITYTRACE END ")) {
                const bool begin = text.starts_with("ACTIVITYTRACE BEGIN ");
                const auto device = text.substr(begin ? 20 : 18);
                if (device != identities.device_id() || !safety_guard())
                    return "{\"ok\":false,\"error\":\"activity_trace_refused\"}\n";
                if (begin && !trace.begin())
                    return "{\"ok\":false,\"error\":\"activity_trace_busy\"}\n";
                if (!begin)
                    trace.end();
                auto result = identity_reply();
                number_field(result, "capture_epoch", trace.capture_epoch(), true);
                result += ",\"enabled\":" + std::string(trace.enabled() ? "true" : "false") + "}\n";
                return result;
            }
            if (!text.starts_with("ACTIVITYTRACE READ "))
                return "{\"ok\":false,\"error\":\"activity_trace_command\"}\n";
            const auto raw = text.substr(19);
            std::uint64_t cursor = 0;
            const auto parsed = std::from_chars(raw.data(), raw.data() + raw.size(), cursor);
            if (raw.empty() || (raw.size() > 1 && raw.front() == '0') || parsed.ec != std::errc{} ||
                parsed.ptr != raw.data() + raw.size() || cursor > trace.records().size())
                return "{\"ok\":false,\"error\":\"activity_trace_cursor\"}\n";
            auto result = identity_reply();
            number_field(result, "capture_epoch", trace.capture_epoch(), true);
            number_field(result, "record_count", trace.records().size(), true);
            number_field(result, "open_spans", trace.open_spans(), true);
            number_field(result, "dropped_spans", trace.dropped_spans(), true);
            result += ",\"enabled\":" + std::string(trace.enabled() ? "true" : "false") +
                      ",\"overflow\":" + (trace.overflow() ? "true" : "false") +
                      ",\"clock_regressed\":" + (trace.clock_regressed() ? "true" : "false") +
                      ",\"records\":[";
            std::size_t count = 0;
            std::uint64_t next = cursor;
            for (const auto& record : trace.records()) {
                if (record.sequence <= cursor)
                    continue;
                if (count == 64)
                    break;
                std::string item = count ? ",{\"seq\":\"" : "{\"seq\":\"";
                item +=
                    std::to_string(record.sequence) + "\",\"span\":\"" +
                    std::to_string(record.span) + "\",\"monotonic_ns\":\"" +
                    std::to_string(record.monotonic_ns) + "\",\"kind\":" +
                    wsprrypico::wtp::json::quote(
                        wsprrypico::runtime::activity_kind_name(record.kind)) +
                    ",\"phase\":\"" +
                    (record.phase == wsprrypico::runtime::ActivityPhase::Begin ? "begin" : "end") +
                    "\",\"outcome\":\"" +
                    (record.outcome == wsprrypico::runtime::ActivityOutcome::Pending ? "pending"
                     : record.outcome == wsprrypico::runtime::ActivityOutcome::Complete
                         ? "complete"
                         : "failed") +
                    "\"}";
                if (result.size() + item.size() > 7400)
                    break;
                result += item;
                ++count;
                next = record.sequence;
            }
            result += "]";
            number_field(result, "next_cursor", next, true);
            result += ",\"more\":" + std::string(next < trace.records().size() ? "true" : "false") +
                      "}\n";
            return result;
        }
        if (text == "INFO") {
            // One allocator snapshot before response formatting. These are arena
            // statistics, not a destructive largest-allocation probe or a peak
            // covering every intervening allocation. TLS is part of this heap.
            const auto heap_before = time_us_64();
            const auto heap = mallinfo();
            const auto heap_observed_us = time_us_64();
            const auto heap_capacity = reinterpret_cast<std::uintptr_t>(&__HeapLimit) -
                                       reinterpret_cast<std::uintptr_t>(&__end__);
            heap_peak = std::max(heap_peak, static_cast<std::size_t>(heap.uordblks));
            const auto stack_before = time_us_64();
            const auto core0_stack_used = stack_used();
            const auto core0_stack_scan_us = time_us_64() - stack_before;
            // Build the network snapshot before allocating the outer INFO
            // buffer: its formatter has its own temporary strings.
            auto network_status = network.status();
            std::string result;
            // Avoid retaining old and doubled buffers while a maximum WTP
            // input is resident. Reserve the normal INFO size in one allocation.
            result.reserve(8192);
            result +=
                "{\"ok\":true,\"device_id\":" +
                wsprrypico::wtp::json::quote(identities.device_id()) + ",\"revision\":" +
                wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                ",\"firmware\":" +
                wsprrypico::wtp::json::quote(wsprrypico::firmware::kFirmwareVersion) +
                ",\"deployment_identity_matches\":" + (deployment_matches ? "true" : "false") +
                ",\"recovery_boot\":" + (recovery ? "true" : "false");
            result += ",\"provisioning_source\":";
            if (runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::Factory)
                result += "\"factory\"";
            else if (runtime_profile.source() ==
                     wsprrypico::provisioning::RuntimeSource::Provisioned)
                result += "\"provisioned\"";
            else if (runtime_profile.source() ==
                     wsprrypico::provisioning::RuntimeSource::Unprovisioned)
                result += "\"unprovisioned\"";
            else if (runtime_profile.source() ==
                     wsprrypico::provisioning::RuntimeSource::NetworkOnly)
                result += "\"network_only\"";
            else if (runtime_profile.source() ==
                     wsprrypico::provisioning::RuntimeSource::ConsumerPreClock)
                result += "\"consumer_preclock\"";
            else
                result += "\"fault\"";
            result += ",\"lan_wtp_mode\":\"" +
                      std::string(local_wtp ? (plain_lan_wtp ? "plain"
                                               : tls_lan_wtp ? "tls"
                                                             : "off")
                                            : "engineering-tls") +
                      "\"";
            result += ",\"lan_wtp_port\":" + std::to_string(plain_lan_wtp ? plain_lan_port
                                                            : tls_lan_wtp ? server.port()
                                                                          : 0);
            result += ",\"lan_wtp_ready\":" +
                      std::string(local_wtp &&
                                          (plain_lan_wtp ? server.plain_listening()
                                                         : tls_lan_wtp && server.listening()) &&
                                          network.link_up() && !network.ipv4().empty() &&
                                          network.ipv4() != "0.0.0.0" &&
                                          service.clock_snapshot().state !=
                                              wsprrypico::wtp::ClockState::Unsynchronized
                                      ? "true"
                                      : "false");
            number_field(result, "provisioning_generation", runtime_profile.generation(), true);
            number_field(result, "provisioning_fault",
                         static_cast<unsigned>(runtime_profile.fault()));
            result += ",\"saved_consumer_profile\":";
            result += runtime_profile.consumer_readback_json();
            result += ",\"radio_identity_valid\":";
            result += derived_identity ? "true" : "false";
            result += ",\"local_suffix\":" + wsprrypico::wtp::json::quote(local_identity.suffix);
            result += ",\"access_state\":";
            switch (access_store.state()) {
            case wsprrypico::provisioning::AccessStoreState::Unloaded:
                result += "\"unloaded\"";
                break;
            case wsprrypico::provisioning::AccessStoreState::Erased:
                result += "\"erased\"";
                break;
            case wsprrypico::provisioning::AccessStoreState::Healthy:
                result += "\"healthy\"";
                break;
            case wsprrypico::provisioning::AccessStoreState::Fault:
                result += "\"fault\"";
                break;
            }
            number_field(result, "access_generation", access_store.sequence(), true);
#ifdef WSPRRY_PICO_PHASE12_FAULT_FIXTURE
            number_field(result, "phase12_fault_stage",
                         wsprrypico::provisioning::phase12_fault_stage(), true);
            result += ",\"phase12_boot_ap_window_ms\":120000";
            result += ",\"phase12_fault_consumed\":";
            result += wsprrypico::provisioning::phase12_fault_consumed() ? "true" : "false";
#endif
            result += ",\"access_default_password\":";
            result +=
                access_store.record() && access_store.record()->default_password ? "true" : "false";
            result += ",\"ble_running\":" + std::string(gatt.running() ? "true" : "false");
            result += ",\"led_boot_pins\":" + wsprrypico::hardware::serialize_plan(boot_pins);
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
            result += ",\"led_acceptance\":true";
            number_field(result, "led_selection", WSPRRY_PICO_LED_SELECTION);
            number_field(result, "led_rejected_writes",
                         wsprrypico::provisioning::led_acceptance.rejected());
#else
            result += ",\"led_acceptance\":false";
#endif
            const auto led_status = indicator.status(time_us_64() / 1000ULL);
            result += ",\"indicator_output_fault\":";
            result += led_status.output_fault ? "true" : "false";
            result += ",\"indicator_output_on\":";
            result += led_status.output_on ? "true" : "false";
            result += ",\"indicator_output_known\":";
            result += led_status.output_known ? "true" : "false";
            result += ",\"indicator_operational_on\":";
            result += led_status.operational_on ? "true" : "false";
            result += ",\"indicator_operational_known\":";
            result += led_status.operational_known ? "true" : "false";
            result += ",\"indicator_operational_fault\":";
            result += led_status.operational_fault ? "true" : "false";
#ifdef WSPRRY_PICO_STANDALONE_RF
            result += ",\"tx_indicator_requested\":";
            result += tx_indicator_gate.requested() ? "true" : "false";
            result += ",\"tx_indicator_ready\":";
            result += tx_indicator_gate.ready() ? "true" : "false";
#else
            result += ",\"tx_indicator_requested\":false,\"tx_indicator_ready\":false";
#endif
#ifdef WSPRRY_PICO_PHASE12_INDICATOR_FAULT_FIXTURE
            result += ",\"indicator_fault_fixture\":true";
            number_field(result, "indicator_fixture_calls",
                         wsprrypico::provisioning::indicator_fault_fixture_calls());
            number_field(result, "indicator_fixture_injected",
                         wsprrypico::provisioning::indicator_fault_fixture_injected());
            number_field(result, "indicator_fixture_successful_writes",
                         wsprrypico::provisioning::indicator_fault_fixture_successful_writes());
            number_field(result, "indicator_pattern", static_cast<unsigned>(led_status.pattern));
#endif
            result += ",\"ble_enrollment_open\":" +
                      std::string(local_access.enrollment_open(time_us_64() / 1000ULL) ? "true"
                                                                                       : "false");
            number_field(result, "fault_stage", fault_stage);
            number_field(result, "fault_hash", fault_hash);
            number_field(result, "fault_pc", fault_pc);
            number_field(result, "fault_status", fault_status);
            result += ",\"fault_allocation_recorded\":";
            result += allocation_fault ? "true" : "false";
            number_field(result, "fault_allocation_request_bytes",
                         allocation_fault ? saved_status : 0);
            result += ",\"fault_allocation_returned_null\":";
            result += allocation_fault ? ((saved_pc & 1U) ? "true" : "false") : "null";
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
            const auto gp14_softap = softap_coordinator.status(time_us_64() / 1000ULL);
            const bool gp14_softap_adapter_running = softap.running();
            const bool gp14_softap_adapter_ready = softap.ready();
            result += ",\"gp14_capture_fault\":";
            result += gp14_button.fault() ? "true" : "false";
            number_field(result, "gp14_capture_fault_code",
                         static_cast<unsigned>(gp14_button.fault_code()));
            result += ",\"gp14_held\":";
            result += gp14_button.held() ? "true" : "false";
            result += ",\"gp14_output_inhibited\":";
            result += service.output_inhibited() ? "true" : "false";
            result += ",\"gp14_stop_verified\":";
            result += gp14_runtime.stop_verified() ? "true" : "false";
            result += ",\"gp14_prior_reset\":";
            result += gp14_prior_reset ? "true" : "false";
            number_field(result, "gp14_prior_duration_ms", gp14_prior_duration_ms);
            number_field(result, "gp14_last_duration_us", gp14_runtime.last_duration_us());
            number_field(result, "gp14_stop_events", gp14_runtime.stop_events());
            number_field(result, "gp14_ap_events", gp14_runtime.setup_events());
            number_field(result, "gp14_ap_request_attempts", gp14_runtime.setup_attempts());
            number_field(result, "gp14_ap_request_accepts", gp14_runtime.setup_accepts());
            result += ",\"gp14_softap_manual_lease_active\":";
            result += gp14_softap.manual_setup ? "true" : "false";
            result += ",\"gp14_softap_manual_lease_held\":";
            result += gp14_softap.manual_button_held ? "true" : "false";
            result += ",\"gp14_softap_requested\":";
            result += gp14_softap.requested ? "true" : "false";
            result += ",\"gp14_softap_adapter_running\":";
            result += gp14_softap_adapter_running ? "true" : "false";
            result += ",\"gp14_softap_adapter_ready\":";
            result += gp14_softap_adapter_ready ? "true" : "false";
            result += ",\"gp14_softap_service_ready\":";
            result += gp14_softap.ready ? "true" : "false";
            number_field(result, "gp14_reset_events", gp14_runtime.reset_events());
            number_field(result, "gp14_samples", gp14_button.samples());
            number_field(result, "gp14_dma_blocks", gp14_button.completed_blocks());
            number_field(result, "gp14_max_backlog_words", gp14_button.maximum_backlog_words());
#ifdef WSPRRY_PICO_GP14_FLASH_PROBE
            result += ",\"gp14_flash_probe\":true";
            number_field(result, "gp14_flash_probe_runs", gp14_flash_probe_runs);
            result += ",\"gp14_flash_probe_failed\":";
            result += gp14_flash_probe_failed ? "true" : "false";
#endif
#endif
            result += ",\"network\":";
            result += network_status;
            std::string{}.swap(network_status);
            number_field(result, "system_clock_hz", clock_get_hz(clk_sys));
            number_field(result, "heap_allocated_bytes", heap.uordblks);
            number_field(result, "heap_available_bytes",
                         heap.uordblks < heap_capacity ? heap_capacity - heap.uordblks : 0);
            number_field(result, "heap_capacity_bytes", heap_capacity);
            number_field(result, "heap_arena_bytes", heap.arena);
            number_field(result, "heap_arena_free_bytes", heap.fordblks);
            number_field(result, "heap_free_chunks", heap.ordblks);
            number_field(result, "heap_top_releasable_bytes", heap.keepcost);
            number_field(result, "heap_sample_observed_us", heap_observed_us, true);
            number_field(result, "heap_sample_cost_us", heap_observed_us - heap_before);
            number_field(result, "heap_sampled_peak_bytes", heap_peak);
            number_field(result, "wtp_input_reserved_bytes", endpoint.input_reserved_bytes());
            const auto allocator = wsprry_heap_snapshot();
            number_field(result, "allocator_entries", allocator.entries, true);
            number_field(result, "allocator_failures", allocator.failures, true);
            number_field(result, "allocator_last_failure_request_bytes",
                         allocator.last_failure_request_bytes);
            number_field(result, "allocator_last_failure_entry", allocator.last_failure_entry);
            number_field(result, "allocator_last_failure_caller", allocator.last_failure_caller);
            number_field(result, "allocator_last_failure_input_caller",
                         allocator.last_failure_input_caller);
            number_field(result, "allocator_last_failure_core", allocator.last_failure_core);
            number_field(result, "allocator_live_bytes", allocator.live_bytes);
            number_field(result, "allocator_peak_bytes", allocator.peak_bytes);
            number_field(result, "allocator_largest_request_bytes",
                         allocator.largest_request_bytes);
            number_field(result, "allocator_largest_successful_request_bytes",
                         allocator.largest_successful_request_bytes);
            number_field(result, "allocator_sample_time_us", allocator.sample_time_us, true);
            number_field(result, "input_trim_attempts", allocator.input_trim_attempts, true);
            number_field(result, "input_trim_releases", allocator.input_trim_releases, true);
            number_field(result, "allocator_max_sample_us", allocator.max_sample_us);
            number_field(result, "allocator_max_entry_us", allocator.max_entry_us);
            number_field(result, "allocator_max_depth", allocator.max_depth);
            number_field(result, "core0_stack_used_bytes", core0_stack_used);
            const auto core0_guard = wsprry_stack_guard_snapshot();
            number_field(result, "core0_stack_guard_bottom", core0_guard.bottom);
            number_field(result, "core0_stack_guard_limit", core0_guard.limit);
            number_field(result, "core0_stack_fault_status", core0_guard.fault_status);
            number_field(result, "core0_stack_guard_valid",
                         core0_guard.valid &&
                             core0_guard.bottom == reinterpret_cast<std::uintptr_t>(&__StackLimit));
            number_field(result, "core0_stack_scan_us", core0_stack_scan_us);
            const auto flash_resources = wsprrypico::standalone::flash_resources();
            number_field(result, "flash_read_attempts", flash_resources.read_attempts, true);
            number_field(result, "flash_erase_attempts", flash_resources.erase_attempts, true);
            number_field(result, "flash_program_attempts", flash_resources.program_attempts, true);
            number_field(result, "flash_read_failures", flash_resources.read_failures, true);
            number_field(result, "flash_erase_failures", flash_resources.erase_failures, true);
            number_field(result, "flash_program_failures", flash_resources.program_failures, true);
            number_field(result, "flash_read_requested_bytes", flash_resources.read_requested_bytes,
                         true);
            number_field(result, "flash_erase_requested_bytes",
                         flash_resources.erase_requested_bytes, true);
            number_field(result, "flash_program_requested_bytes",
                         flash_resources.program_requested_bytes, true);
            result += ",\"resource_schema\":1,\"largest_allocation_probe_measured\":false";
            result += ",\"btstack_pool_occupancy_measured\":true";
            const auto acl = wsprrypico::runtime::btstack_acl_credit_snapshot();
            result += ",\"btstack_controller_buffers_measured\":" +
                      std::string(acl.measured ? "true" : "false");
            result += ",\"btstack_acl_credits\":{\"scope\":\"controller_reported_hci_acl_credits\","
                      "\"initialized\":" +
                      std::string(acl.initialized ? "true" : "false") +
                      ",\"measured\":" + (acl.measured ? "true" : "false");
            number_field(result, "capacity", acl.capacity);
            number_field(result, "free", acl.free);
            number_field(result, "min_free", acl.min_free);
            number_field(result, "peak_outstanding", acl.peak_outstanding);
            number_field(result, "epoch", acl.epoch, true);
            number_field(result, "send_events", acl.send_events, true);
            number_field(result, "completed_events", acl.completed_events, true);
            number_field(result, "invalid_samples", acl.invalid_samples, true);
            number_field(result, "transport_failures", acl.transport_failures, true);
            result += "},\"btstack_pools\":{";
            const auto bt_pools = wsprrypico::runtime::btstack_pool_snapshot();
            constexpr std::array<std::string_view, 5> bt_names{
                "hci_connections", "l2cap_channels", "l2cap_services", "sm_lookup", "whitelist"};
            for (std::size_t i = 0; i < bt_pools.size(); ++i) {
                if (i)
                    result += ',';
                result += wsprrypico::wtp::json::quote(bt_names[i]) +
                          ":{\"used\":" + std::to_string(bt_pools[i].used);
                number_field(result, "capacity", bt_pools[i].capacity);
                number_field(result, "peak", bt_pools[i].peak);
                number_field(result, "failures", bt_pools[i].failures);
                number_field(result, "faults", bt_pools[i].faults);
                result += '}';
            }
            result += '}';
            const auto transports = server.resources();
            number_field(result, "network_active_connections", transports.active_connections);
            number_field(result, "network_pending_connections", transports.pending_connections);
            number_field(result, "network_connection_capacity", 2);
            number_field(result, "network_buffered_rx_bytes", transports.buffered_rx_bytes);
            number_field(result, "network_pending_tcp_bytes", transports.pending_tcp_bytes);
            number_field(result, "softap_retained_sessions",
                         local_access.retained_softap_sessions());
            number_field(result, "softap_session_capacity",
                         wsprrypico::provisioning::softap_session_capacity);
            number_field(result, "softap_session_inactivity_ms",
                         local_access.session_limits().inactivity_ms, true);
            number_field(result, "softap_session_absolute_ms",
                         local_access.session_limits().absolute_ms, true);
            const auto setup_resources = bootstrap.resources();
            result += ",\"bootstrap_connected\":";
            result += setup_resources.connected ? "true" : "false";
            result += ",\"bootstrap_setup_pending\":";
            result += setup_resources.setup_pending ? "true" : "false";
            result += ",\"bootstrap_reset_pending\":";
            result += setup_resources.recovery_pending ? "true" : "false";
            number_field(result, "bootstrap_network_slot_state",
                         setup_resources.network_slot_state);
            number_field(result, "bootstrap_owner_slot_state", setup_resources.owner_slot_state);
            number_field(result, "bootstrap_recovery_slot_state",
                         setup_resources.recovery_slot_state);
            number_field(result, "bootstrap_pending_tcp_bytes", setup_resources.pending_tcp_bytes);
            const auto ble_resources = gatt.diagnostics();
            number_field(result, "ble_active_connections", ble_resources.connected ? 1 : 0);
            number_field(result, "ble_connection_capacity", 1);
            number_field(result, "ble_outbound_frames", ble_resources.outbound_frames);
            number_field(result, "ble_outbound_index", ble_resources.outbound_index);
            result += ",\"ble_indication_pending\":";
            result += ble_resources.indication_pending ? "true" : "false";
            number_field(result, "ble_inbound_bytes", ble_resources.inbound_bytes);
            number_field(result, "ble_outbound_bytes", ble_resources.outbound_bytes);
#ifdef WSPRRY_PICO_STANDALONE_RF
            result += ",\"core1_workload_available\":true";
#else
            result += ",\"core1_workload_available\":false";
#endif
            number_field(result, "tls_peak_bytes", server.tls_peak());
            number_field(result, "tls_allocated_bytes", server.tls_allocated());
            number_field(result, "tls_allocation_failures", server.tls_failures());
            number_field(result, "network_wtp_close_reason",
                         server.metrics().last_wtp_close_reason);
            result += ",\"network_wtp_tls_result\":" +
                      std::to_string(server.metrics().last_wtp_tls_result);
#ifdef WSPRRY_PICO_STANDALONE_RF
            const auto metrics = engine.metrics();
#ifdef WSPRRY_PICO_RF_RENDER_IN_RAM
            result += ",\"rf_render_in_ram\":true";
#else
            result += ",\"rf_render_in_ram\":false";
#endif
            number_field(result, "launch_observed_ns", metrics.launch_ns, true);
            number_field(result, "launch_epoch", metrics.launch_epoch, true);
            number_field(result, "launch_target_ns", metrics.launch_target_ns, true);
            number_field(result, "launch_delay_ns",
                         metrics.launch_ns >= metrics.launch_target_ns
                             ? metrics.launch_ns - metrics.launch_target_ns
                             : 0,
                         true);
            number_field(result, "dma_irqs", metrics.dma_irqs);
            number_field(result, "max_dma_irq_ns", metrics.max_irq_ns);
            number_field(result, "alarm_irqs", metrics.alarm_irqs);
            number_field(result, "max_alarm_irq_ns", metrics.max_alarm_irq_ns, true);
            number_field(result, "tail_irqs", metrics.tail_irqs);
            number_field(result, "dma_errors", metrics.dma_errors);
            number_field(result, "refill_irq_pairs", metrics.refill.pairs);
            number_field(result, "refill_irq_unpaired", metrics.refill.unpaired);
            number_field(result, "refill_invalid_reserves", metrics.refill.invalid_reserves);
            reserve_field(result, "refill_full_predecessor", metrics.refill.full);
            reserve_field(result, "refill_short_predecessor", metrics.refill.short_block);
            number_field(result, "max_refill_irq_to_ready_ns", metrics.refill.max_irq_to_ready_ns,
                         true);
            number_field(result, "running_successor_links", metrics.refill.running_links);
            number_field(result, "exhausted_successor_links", metrics.refill.exhausted_links);
            number_field(result, "running_tail_links", metrics.refill.tail_links);
            number_field(result, "min_data_successor_ready_words",
                         metrics.refill.min_data_remaining_words, false,
                         metrics.refill.running_links > metrics.refill.tail_links);
            number_field(result, "min_tail_successor_ready_words",
                         metrics.refill.min_tail_remaining_words, false,
                         metrics.refill.tail_links != 0);
            number_field(result, "min_successor_ready_words", metrics.refill.min_remaining_words,
                         false, metrics.refill.running_links != 0);
            number_field(result, "core1_stack_used_bytes", metrics.stack_used_bytes);
            number_field(result, "core1_stack_guard_bottom", metrics.stack_guard_bottom);
            number_field(result, "core1_stack_guard_limit", metrics.stack_guard_limit);
            number_field(result, "core1_stack_fault_status", metrics.stack_fault_status);
            number_field(result, "core1_stack_guard_valid", metrics.stack_guard_valid);
            number_field(result, "rf_worker_commands", metrics.commands);
            number_field(result, "rf_metric_probes", metrics.probes);
            number_field(result, "rf_max_probe_ns", metrics.max_probe_ns, true);
            number_field(result, "rf_max_service_gap_ns", metrics.max_service_gap_ns, true);
            number_field(result, "rf_max_poll_ns", metrics.max_poll_ns, true);
            number_field(result, "rf_max_roundtrip_ns", metrics.max_roundtrip_ns, true);
            number_field(result, "rf_safety_requested_ns", metrics.safety_requested_ns, true);
            number_field(result, "rf_safety_stopped_ns", metrics.safety_stopped_ns, true);
            number_field(result, "rf_safety_input_requested_us", metrics.safety_input_requested_us,
                         true);
            number_field(result, "rf_safety_input_duration_us", metrics.safety_input_duration_us);
            number_field(result, "rf_safety_input_reset", metrics.safety_input_reset);
            number_field(result, "rf_safety_input_fault", metrics.safety_input_fault);
#ifdef WSPRRY_PICO_GP14_RF_ACCEPTANCE
            result += ",\"gp14_rf_acceptance\":true";
            result += ",\"gp14_rf_cue_supported\":true";
            const auto cue_status = indicator.status(time_us_64() / 1000ULL);
            result += ",\"gp14_rf_cue_active\":";
            result += cue_status.pattern == wsprrypico::provisioning::IndicatorPattern::Identify
                          ? "true"
                          : "false";
            result += ",\"gp14_rf_cue_fault\":";
            result += cue_status.output_fault ? "true" : "false";
            number_field(result, "gp14_rf_busy_used", gp14_rf_busy_used);
            number_field(result, "gp14_prior_rf_decision_after_launch_us",
                         gp14_prior_rf_decision_after_launch_us);
#endif
            result += ",\"rf_safety_inhibited\":";
            result += engine.safety_inhibited() ? "true" : "false";
            number_field(result, "max_loop_us", max_loop_us);
            number_field(result, "max_authority_poll_us", max_refill_us);
            number_field(result, "max_usb_us", max_usb_us);
            number_field(result, "max_request_us", max_request_us);
            result += ",\"engine_diagnostic\":" + wsprrypico::wtp::json::quote(engine.diagnostic());
#endif
            auto status = scheduler.status();
            if (!status.empty() && status.back() == '\n')
                status.pop_back();
            // Reuse the INFO buffer. Copying this lvalue into operator+ keeps
            // two large diagnostic strings live beside a maximum job reply.
            result += ",\"status\":";
            result += status;
            result += "}\n";
            return result;
        }
#ifdef WSPRRY_PICO_GP14_FLASH_PROBE
        if (text.starts_with("GP14 FLASH ")) {
            if (text.substr(11) != identities.device_id() || !scheduler.idle() || recovery ||
                engine.output_active() || reboot_at || gp14_button.fault() ||
                gp14_flash_probe_failed || gp14_flash_probe_runs >= 16)
                return "{\"ok\":false,\"error\":\"flash_probe_refused\"}\n";
            ++gp14_flash_probe_runs;
            const auto probe = wsprrypico::provisioning::run_gp14_flash_probe();
            gp14_flash_probe_failed = !probe.ok;
            std::string result = probe.ok ? "{\"ok\":true" : "{\"ok\":false";
            number_field(result, "run", gp14_flash_probe_runs);
            number_field(result, "pattern_ok", probe.pattern_ok);
            number_field(result, "restore_ok", probe.restore_ok);
            number_field(result, "begin_us", probe.begin_us);
            number_field(result, "write_end_us", probe.write_end_us);
            number_field(result, "end_us", probe.end_us);
            number_field(result, "low_before", probe.low_before);
            number_field(result, "low_after_write", probe.low_after_write);
            number_field(result, "low_after", probe.low_after);
            result += "}\n";
            return result;
        }
#endif
#ifdef WSPRRY_PICO_GP14_RF_ACCEPTANCE
        if (text.starts_with("GP14 RF CUE ")) {
            const auto arguments = text.substr(12);
            const auto split = arguments.find(' ');
            const auto requested = arguments.substr(0, split);
            const auto nonce =
                split == std::string_view::npos ? std::string_view{} : arguments.substr(split + 1);
            const bool probe = nonce == "READY";
            const auto activity = service.activity();
            if (requested != identities.device_id() || recovery || reboot_at ||
                gp14_button.fault() || engine.safety_inhibited() || !network.initialized() ||
                indicator.status(time_us_64() / 1000ULL).output_fault ||
                (probe ? activity.state != wsprrypico::wtp::State::Empty
                       : activity.state != wsprrypico::wtp::State::Armed &&
                             activity.state != wsprrypico::wtp::State::Running) ||
                (!probe && (nonce.size() != 32 ||
                            nonce.find_first_not_of("0123456789abcdef") != std::string_view::npos)))
                return "{\"ok\":false,\"error\":\"rf_cue_refused\"}\n";
            if (probe)
                return "{\"ok\":true,\"ready\":true}\n";
            const auto code =
                indicator.identify(text, requested, true, true, time_us_64() / 1000ULL);
            if (code != wsprrypico::provisioning::IndicatorCode::Ok)
                return "{\"ok\":false,\"error\":\"rf_cue_refused\"}\n";
            return "{\"ok\":true,\"cue\":true}\n";
        }
        if (text.starts_with("GP14 RF BUSY ")) {
            const auto activity = service.activity();
            if (text.substr(13) != identities.device_id() || gp14_rf_busy_used || recovery ||
                reboot_at || gp14_button.fault() || engine.safety_inhibited() ||
                (activity.state != wsprrypico::wtp::State::Armed &&
                 activity.state != wsprrypico::wtp::State::Running))
                return "{\"ok\":false,\"error\":\"rf_busy_refused\"}\n";
            gp14_rf_busy_used = true;
            watchdog_update();
            const auto begin = time_us_64();
            while (time_us_64() - begin < 5'000'000)
                tight_loop_contents();
            const auto end = time_us_64();
            // Reconcile before USB dispatch can admit any subsequent command.
            if (engine.safety_inhibited() && !gp14_worker_inhibit_handled) {
                (void)stop_for_gp14();
                gp14_worker_inhibit_handled = true;
            }
            watchdog_update();
            std::string result = "{\"ok\":true";
            number_field(result, "busy_begin_us", begin, true);
            number_field(result, "busy_end_us", end, true);
            result += "}\n";
            return result;
        }
#endif
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
        if (text.starts_with("LED TEST ")) {
            const auto args = text.substr(9);
            const auto split = args.find(' ');
            const auto command =
                split == std::string_view::npos ? std::string_view{} : args.substr(split + 1);
            const auto current = service.activity();
            const auto now = time_us_64() / 1000ULL;
            if (args.substr(0, split) != identities.device_id() || boot_recovery || reboot_at ||
                !wsprrypico::hardware::operational(boot_pins))
                return "{\"ok\":false,\"error\":\"led_test_refused\"}\n";
            auto& fixture = wsprrypico::provisioning::led_acceptance;
            bool ok = false;
            if (command == "AP") {
                ok =
                    fixture.ap_active(now) || fixture.ap(now); // Existing finite cue is idempotent.
            } else if (command == "IDENTIFY") {
                ok = indicator.identify(std::string(text) + std::to_string(now),
                                        identities.device_id(), true, true,
                                        now) == wsprrypico::provisioning::IndicatorCode::Ok;
            } else if (command == "FAIL" && !current.output_active && !current.owned &&
                       scheduler.idle()) {
                ok = fixture.fail(now); // Reject ON only; OFF always uses the real driver.
                if (ok) {
                    indicator.enabled(false);
                    indicator.poll(now); // Establish checked OFF before injecting launch failure.
                    indicator.enabled(true);
                }
            } else if (command == "STOP") {
                return scheduler.command("STOP"); // Actual standalone ownership/stop path.
            } else if (command == "DISABLE" && !current.output_active && !current.owned &&
                       store.config()) {
                auto off = *store.config();
                off.enabled = false;
                ok = store.save(off);
            } else if (command == "SCHEDULE" && scheduler.idle() && store.config() &&
                       !store.config()->enabled && fixture.schedule()) {
                const auto clock = service.clock_snapshot();
                if (clock.state == wsprrypico::wtp::ClockState::Synchronized &&
                    clock.leap == wsprrypico::wtp::LeapState::Normal &&
                    clock.uncertainty_ns <= 500'000'000) {
                    auto one = *store.config();
                    const auto boundary = (clock.utc_now_ns / 120'000'000'000ULL + 1) * 120;
                    one.enabled = true;
                    one.expires_utc_s = boundary + 113;
                    one.schedules = {{86400, static_cast<std::uint32_t>(boundary % 86400)}};
                    // Preserve station, network and pin settings. Validate the same contract.
                    const auto checked = wsprrypico::standalone::parse_config(
                        wsprrypico::standalone::serialize_config(one));
                    ok = checked && store.save(*checked);
                }
#ifndef WSPRRY_PICO_STANDALONE_RF
            } else if (command == "HOLD" && scheduler.idle() && !current.owned &&
                       !current.output_active &&
                       wsprrypico::hardware::validate(boot_pins).owners[15].empty() &&
                       fixture.hold()) {
                gpio_init(15);
                gpio_put(15, false);
                const auto irq_state = save_and_disable_interrupts();
                gpio_set_dir(15, GPIO_OUT); // Low only, never drive high.
                ok =
                    add_alarm_in_ms(fixture.hold_duration_ms, led_release_hold, nullptr, false) > 0;
                if (!ok)
                    gpio_set_dir(15, GPIO_IN);
                restore_interrupts(irq_state); // Alarm releases even if the main loop stalls.
#endif
            }
            return ok ? "{\"ok\":true}\n" : "{\"ok\":false,\"error\":\"led_test_refused\"}\n";
        }
#endif
        if ((consumer_source_selected() || bootstrap.owner_claim_pending() ||
             !runtime_profile_loaded) &&
            text != "ABORT" && text != "REBOOT" && text != "BOOTSEL")
            return "{\"ok\":false,\"error\":\"profile_runtime_unavailable\"}\n";
        if (text.starts_with("HEAP PROBE ")) {
            const auto capacity = reinterpret_cast<std::uintptr_t>(&__HeapLimit) -
                                  reinterpret_cast<std::uintptr_t>(&__end__);
            return wsprrypico::standalone::heap_probe_command(text.substr(11), capacity,
                                                              scheduler.idle(), wsprry_heap_probe);
        }
        if (text == "ACCESS STATUS") {
            std::string state = "unloaded";
            if (access_store.state() == wsprrypico::provisioning::AccessStoreState::Erased)
                state = "erased";
            else if (access_store.state() == wsprrypico::provisioning::AccessStoreState::Healthy)
                state = "healthy";
            else if (access_store.state() == wsprrypico::provisioning::AccessStoreState::Fault)
                state = "fault";
            return "{\"ok\":true,\"device_id\":" +
                   wsprrypico::wtp::json::quote(identities.device_id()) +
                   ",\"station_mac\":" + wsprrypico::wtp::json::quote(network.station_mac()) +
                   ",\"suffix\":" + wsprrypico::wtp::json::quote(local_identity.suffix) +
                   ",\"state\":" + wsprrypico::wtp::json::quote(state) +
                   ",\"generation\":" + std::to_string(access_store.sequence()) +
                   ",\"default_password\":" +
                   (access_store.record() && access_store.record()->default_password ? "true"
                                                                                     : "false") +
                   ",\"ble_running\":" + (gatt.running() ? "true" : "false") +
                   ",\"enrollment_open\":" +
                   (local_access.enrollment_open(time_us_64() / 1000ULL) ? "true" : "false") +
                   "}\n";
        }
        if (text == "BLE STATUS") {
            const auto ble = gatt.diagnostics();
            std::string result = "{\"ok\":true";
            number_field(result, "connections", ble.connections);
            number_field(result, "disconnections", ble.disconnections);
            number_field(result, "command_frames", ble.command_frames);
            number_field(result, "commands_completed", ble.commands_completed);
            number_field(result, "responses_queued", ble.responses_queued);
            number_field(result, "queue_failures", ble.queue_failures);
            number_field(result, "send_requests", ble.send_requests);
            number_field(result, "can_send_callbacks", ble.can_send_callbacks);
            number_field(result, "can_send_during_write", ble.can_send_during_write);
            number_field(result, "indications_started", ble.indications_started);
            number_field(result, "indication_completions", ble.indication_completions);
            number_field(result, "responses_delivered", ble.responses_delivered);
            number_field(result, "cccd_writes", ble.cccd_writes);
            number_field(result, "cccd_rejections", ble.cccd_rejections);
            number_field(result, "cccd_value", ble.cccd_value);
            number_field(result, "wtp_cccd_value", ble.wtp_cccd_value);
            number_field(result, "wtp_write_segments", ble.wtp_write_segments);
            number_field(result, "wtp_write_bytes", ble.wtp_write_bytes);
            number_field(result, "wtp_indication_segments", ble.wtp_indication_segments);
            number_field(result, "wtp_indication_bytes", ble.wtp_indication_bytes);
            number_field(result, "last_request_status", ble.last_request_status);
            number_field(result, "last_indication_status", ble.last_indication_status);
            number_field(result, "last_completion_status", ble.last_completion_status);
            number_field(result, "last_disconnect_reason", ble.last_disconnect_reason);
            number_field(result, "att_mtu", ble.att_mtu);
            number_field(result, "outbound_frames", ble.outbound_frames);
            number_field(result, "outbound_index", ble.outbound_index);
            result += ",\"connected\":" + std::string(ble.connected ? "true" : "false");
            result += ",\"admitted\":" + std::string(ble.admitted ? "true" : "false");
            result += ",\"send_requested\":" + std::string(ble.send_requested ? "true" : "false");
            result += ",\"wtp_over_field_status\":" +
                      std::string(ble.wtp_over_field_status ? "true" : "false");
            result += "}\n";
            return result;
        }
        constexpr std::string_view softap_prefix = "ACCESS SOFTAP ";
        if (text.starts_with(softap_prefix)) {
            if (text.substr(softap_prefix.size()) != identities.device_id())
                return "{\"ok\":false,\"error\":\"wrong_device\"}\n";
            if (!derived_identity || !access_store.healthy() || !access_store.record())
                return "{\"ok\":false,\"error\":\"access_unavailable\"}\n";
            return softap_coordinator.request_join_grace(time_us_64() / 1000ULL)
                       ? "{\"ok\":true,\"join_grace_ms\":120000}\n"
                       : "{\"ok\":false,\"error\":\"busy\"}\n";
        }
        constexpr std::string_view adopt_prefix = "ACCESS ADOPT ";
        constexpr std::string_view enroll_prefix = "ACCESS ENROLL ";
        if (text.starts_with(adopt_prefix) || text.starts_with(enroll_prefix)) {
            const bool adopt = text.starts_with(adopt_prefix);
            const auto requested = text.substr(adopt ? adopt_prefix.size() : enroll_prefix.size());
            if (!derived_identity)
                return "{\"ok\":false,\"error\":\"identity_unavailable\"}\n";
            wsprrypico::provisioning::RequestBinding binding;
            binding.device_id.assign(requested);
            binding.principal = "usb-local";
            binding.session_id = service.status().boot_id;
            binding.operation = adopt ? "access_adopt" : "access_enroll";
            binding.nonce = std::to_string(time_us_64());
            binding.current_generation = access_store.sequence();
            binding.target_generation = access_store.sequence() + 1;
            binding.parameters = wsprrypico::wtp::sha256(
                std::span(reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
            const auto now = time_us_64() / 1000ULL;
            auto code = local_access.confirm_local(binding, now);
            if (code == wsprrypico::provisioning::AccessCode::Ok) {
                const auto activity = provisioning_activity(&service);
                code = adopt ? local_access.initialize_default(binding, activity, now)
                             : local_access.open_enrollment(binding, activity, now);
            }
            return access_reply(code);
        }
        constexpr std::string_view identify_prefix = "IDENTIFY ";
        constexpr std::string_view confirm_profile_prefix = "ACCESS CONFIRM PROFILE ";
        if (text.starts_with(confirm_profile_prefix)) {
            const auto requested = text.substr(confirm_profile_prefix.size());
            return access_reply(ble_session.confirm_profile(requested, time_us_64() / 1000ULL));
        }
        if (text.starts_with(identify_prefix)) {
            const auto requested = text.substr(identify_prefix.size());
            const auto code = indicator.identify(std::string(text), requested, true, true,
                                                 time_us_64() / 1000ULL);
            if (code == wsprrypico::provisioning::IndicatorCode::Ok)
                return "{\"ok\":true}\n";
            if (code == wsprrypico::provisioning::IndicatorCode::Busy)
                return "{\"ok\":false,\"error\":\"busy\"}\n";
            if (code == wsprrypico::provisioning::IndicatorCode::OutputFault)
                return "{\"ok\":false,\"error\":\"indicator_fault\"}\n";
            return "{\"ok\":false,\"error\":\"invalid_request\"}\n";
        }
        if (text == "ABORT") {
            (void)scheduler.command(
                "STOP"); // Suspend autonomous work before physical cancellation.
            const auto result = service.local_abort();
            return result.ok
                       ? scheduler.status()
                       : "{\"ok\":false,\"error\":" + wsprrypico::wtp::error_json(result.error) +
                             "}\n";
        }
        if (text == "REBOOT" || text == "BOOTSEL") {
            (void)scheduler.command("STOP");
            if (!(browser_reboot ? scheduler.idle() : scheduler.reset_permitted()) ||
                !engine.disable(monotonic_now(nullptr) + 100'000'000ULL) || engine.output_active())
                return "{\"ok\":false,\"error\":\"not_idle\"}\n";
            browser_reboot = false;
            bootloader = text == "BOOTSEL";
            reboot_at = time_us_64() + 250'000;
            return "{\"ok\":true,\"rebooting\":true}\n";
        }
#ifdef WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC
        if (text == "BOOTSEL DIAG")
            return "{\"ok\":true,\"core1_ready\":" +
                   std::to_string(bootsel_reader_ready.load(std::memory_order_acquire)) +
                   ",\"core1_reads\":" +
                   std::to_string(bootsel_reader_count.load(std::memory_order_relaxed)) + "}\n";
        if (text == "BOOTSEL WINDOW") {
            if (!scheduler.idle() || engine.output_active() ||
                bootsel_reader_ready.load(std::memory_order_acquire) != 1)
                return "{\"ok\":false,\"error\":\"not_idle\"}\n";
            // An opt-in diagnostic only. The USB reply arrives after this
            // five-second flash-safe window, never as owner authority.
            const auto gesture = wsprrypico::provisioning::capture_runtime_bootsel_gesture(5000);
            return "{\"ok\":" + std::string(gesture.safe ? "true" : "false") +
                   ",\"valid_press\":" + (gesture.valid_press ? "true" : "false") +
                   ",\"duration_ms\":" + std::to_string(gesture.duration_ms) +
                   ",\"elapsed_us\":" + std::to_string(gesture.elapsed_us) +
                   ",\"result\":" + std::to_string(gesture.result) + "}\n";
        }
#endif
#ifndef WSPRRY_PICO_STANDALONE_RF
        if (text == "NETLINK") {
            return "{\"ok\":true,\"device_id\":" +
                   wsprrypico::wtp::json::quote(identities.device_id()) + ",\"revision\":" +
                   wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                   ",\"boot_id\":" + wsprrypico::wtp::json::quote(service.status().boot_id) +
                   ",\"association\":" + network.association() + "}\n";
        }
        if (text.starts_with("NETTRACE ")) {
            std::uint64_t after = 0;
            const auto cursor = text.substr(9);
            const auto parsed =
                std::from_chars(cursor.data(), cursor.data() + cursor.size(), after);
            if (parsed.ec != std::errc{} || parsed.ptr != cursor.data() + cursor.size())
                return "{\"ok\":false,\"error\":\"trace_cursor\"}\n";
            return "{\"ok\":true,\"device_id\":" +
                   wsprrypico::wtp::json::quote(identities.device_id()) + ",\"revision\":" +
                   wsprrypico::wtp::json::quote(wsprrypico::firmware::kBuildRevision) +
                   ",\"boot_id\":" + wsprrypico::wtp::json::quote(service.status().boot_id) +
                   ",\"trace\":" + network.trace_page(after) + "}\n";
        }
#endif
        // USB remains available after an idle Wi-Fi shutdown on either image.
        if (text == "WIFI OFF" || text == "WIFI ON") {
            if (!scheduler.idle())
                return "{\"ok\":false,\"error\":\"busy\"}\n";
            return network.set_enabled(text == "WIFI ON")
                       ? "{\"ok\":true}\n"
                       : "{\"ok\":false,\"error\":\"network_unavailable\"}\n";
        }
        return scheduler.command(text);
    };
    while (true) {
        poll_indicator(); // Also service the indicator on reset/recovery paths.
        if (reset_coordinator.blocks_admission() || recovery_reset_at) {
            // Intent closes every output/control admission while the reset
            // response drains on the independent plaintext recovery listener.
            deployment_matches = false;
            (void)scheduler.command("STOP");
            endpoint.disconnect();
            ble_endpoint.disconnect();
            gatt.stop();
            server.stop();
            if (recovery_reset_at && time_us_64() >= recovery_reset_at) {
                if (engine.disable(monotonic_now(nullptr) + 100'000'000ULL) &&
                    !engine.output_active()) {
                    watchdog_reboot(0, 0, 1);
                    while (true)
                        tight_loop_contents();
                }
            }
            watchdog_update();
            bootstrap.poll(true, false);
            tud_task();
            cyw43_arch_poll();
            continue;
        }
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
#ifdef WSPRRY_PICO_STANDALONE_RF
        if (engine.safety_inhibited() && !gp14_worker_inhibit_handled) {
            (void)stop_for_gp14();
            gp14_worker_inhibit_handled = true;
        }
#endif
        wsprrypico::provisioning::DiagnosticButtonEvents button_event;
        while (gp14_button.next(button_event))
            gp14_runtime.observe(button_event, time_us_64() / 1000ULL, gp14_button.held());
        if (gp14_button.fault() && !gp14_fault_handled) {
            gp14_fault_handled = true;
            gp14_runtime.capture_fault();
        }
#endif
        if (reboot_at && time_us_64() >= reboot_at) {
            // Network ownership can change while the response/USB ACK drains.
            // A new owner cancels reset rather than losing its accepted job.
            if (!(browser_reboot ? scheduler.idle() : scheduler.reset_permitted()) ||
                !engine.disable(monotonic_now(nullptr) + 100'000'000ULL) ||
                engine.output_active()) {
                reboot_at = 0;
                bootloader = false;
                browser_reboot = false;
                continue;
            }
            if (bootloader)
                reset_usb_boot(0, 0);
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
            if (gp14_reset_pending) {
                watchdog_hw->scratch[0] = gp14_reset_magic;
                watchdog_hw->scratch[2] = static_cast<std::uint32_t>(
                    std::min<std::uint64_t>(gp14_runtime.last_duration_us() / 1000ULL, UINT32_MAX));
#ifdef WSPRRY_PICO_GP14_RF_ACCEPTANCE
                const auto metrics = engine.metrics();
                const bool relative_valid =
                    metrics.launch_ns && metrics.safety_requested_ns >= metrics.launch_ns;
                watchdog_hw->scratch[3] =
                    relative_valid
                        ? static_cast<std::uint32_t>(std::min<std::uint64_t>(
                              (metrics.safety_requested_ns - metrics.launch_ns) / 1000ULL,
                              UINT32_MAX))
                        : 0;
#endif
            }
#endif
            watchdog_reboot(0, 0, 0);
            while (true)
                tight_loop_contents();
        }
        watchdog_update();
        watchdog_hw->scratch[1] = 3;
#ifdef WSPRRY_PICO_STANDALONE_RF
        const bool measuring = service.activity().state == wsprrypico::wtp::State::Running;
        const auto loop_us = time_us_64();
        if (measuring && last_loop_us)
            maximum(max_loop_us, last_loop_us);
        last_loop_us = measuring ? loop_us : 0;
#endif
        // Core 1 owns physical refills/launch. Core 0 reconciles authority and
        // services all transports; packet arrival never times waveform events.
        if (!reset_coordinator.pending())
            scheduler.poll();
#ifdef WSPRRY_PICO_STANDALONE_RF
        if (measuring)
            maximum(max_refill_us, loop_us);
#endif
        watchdog_hw->scratch[1] = 4;
        const auto network_state = service.activity().state;
        if (server.listening() || server.plain_listening() ||
            (network_state != wsprrypico::wtp::State::Armed &&
             network_state != wsprrypico::wtp::State::Running))
            network.poll();
        if (reset_coordinator.blocks_admission() || recovery_reset_at)
            continue;
        const auto field_now_ms = time_us_64() / 1000ULL;
        if ((consumer_source_selected() || bootstrap.owner_claim_pending()) && gatt.running())
            gatt.stop();
        if (runtime_profile_loaded && !consumer_source_selected() &&
            !bootstrap.owner_claim_pending() && !reset_coordinator.pending() && !gatt.running() &&
            !gatt_start_attempted && derived_identity && local_access.ble_available()) {
            gatt_start_attempted = true;
            (void)gatt.start();
        }
        if (gatt.running())
            gatt.poll();
        const auto station_ip = network.ipv4();
        const bool station_ready =
            network.link_up() && !station_ip.empty() && station_ip != "0.0.0.0";
        softap_coordinator.station(station_ready, field_now_ms);
        softap_coordinator.token_records(
            local_access.live_softap_sessions(field_now_ms, service.owner_session_id()));
        softap_coordinator.reply_active(server.softap_active() || bootstrap.setup_pending());
        const bool request_softap = softap_coordinator.poll(field_now_ms);
        const auto surface = softap_coordinator.surface(
            service.clock_snapshot().state != wsprrypico::wtp::ClockState::Unsynchronized);
        const bool blank_captive =
            bootstrap_started &&
            surface == wsprrypico::provisioning::SoftApSurface::BlankReadOnly &&
            blank_access_available() &&
            wsprrypico::provisioning::idle_for_access(provisioning_activity(&service));
        if (softap.running() && softap.captive() != blank_captive) {
            (void)network.softap_name(false, {});
            softap.stop();
        }
        if (request_softap && !softap.running() && derived_identity) {
            const auto* access = access_store.record();
            if (blank_captive)
                (void)softap.start_blank(local_identity);
            else if (surface != wsprrypico::provisioning::SoftApSurface::BlankReadOnly &&
                     runtime_profile_loaded && access_store.healthy() && access)
                (void)softap.start(local_identity, access->password);
        } else if (!request_softap && softap.running()) {
            (void)network.softap_name(false, {});
            softap.stop();
        }
        const bool softap_name_ready = network.softap_name(softap.ready(), local_identity.hostname);
        const bool bootstrap_active = bootstrap_started && softap.ready();
        // The open AP accepts encrypted Wi-Fi setup before optional station setup.
        bool setup_admitted = true;
#ifdef WSPRRY_PICO_STANDALONE_RF
        setup_admitted = false;
#ifdef WSPRRY_PICO_GP14_RUNTIME_BUTTON
        const auto setup_authority = service.status();
        setup_admitted = wsprrypico::provisioning::rf_setup_allowed(
            {gp14_runtime.stop_verified(), gp14_runtime.setup_accepts() != 0,
             softap_coordinator.status(field_now_ms).manual_setup, service.output_inhibited(),
             engine.safety_inhibited(), gp14_capture_ready && !gp14_button.fault(),
             scheduler.idle(), store.healthy() && profile_store.healthy() && access_store.healthy(),
             recovery || reboot_at != 0 || reset_coordinator.pending(), setup_authority.state,
             setup_authority.owner_id.has_value(), setup_authority.job_id.has_value(),
             setup_authority.output_active});
#endif
#endif
        bootstrap.poll(bootstrap_active, claim_platform.safe_to_commit(), setup_admitted);
        const bool softap_service_ready =
            softap.ready() && (surface == wsprrypico::provisioning::SoftApSurface::BlankReadOnly
                                   ? bootstrap.listening()
                                   : softap_name_ready && server.listening());
        softap_coordinator.ready(softap_service_ready);
        indicator.softap_ready(softap_coordinator.status(field_now_ms).ready
#ifdef WSPRRY_PICO_LED_ACCEPTANCE
                               || wsprrypico::provisioning::led_acceptance.ap_active(field_now_ms)
#endif
        );
        poll_indicator();
        service.poll();
        const auto clock_now = service.clock_snapshot();
        const bool local_wtp_time_ready =
            !local_wtp ||
            (station_ready && network.accepted_sntp() &&
             time_arbiter.status().source == wsprrypico::time::ActiveTimeSource::Sntp &&
             clock_now.state == wsprrypico::wtp::ClockState::Synchronized &&
             clock_now.utc_now_ns != 0);
        // Offline station saves retain a TLS-pending journal. Mint only after
        // fresh accepted SNTP, while idle, then restart into the durable profile.
        static std::uint64_t pending_tls_retry_ms = 0;
        static bool pending_tls_restart = false;
        if (pending_tls_restart) {
            (void)schedule_restart(&restart_context);
        } else if (runtime_profile.consumer_profile() &&
                   runtime_profile.consumer_profile()->tls_pending && local_wtp_time_ready &&
                   field_now_ms >= pending_tls_retry_ms && !reboot_at &&
                   !bootstrap.setup_pending() && claim_platform.safe_to_commit()) {
            pending_tls_retry_ms = field_now_ms + 30'000;
            const auto materialized = wsprrypico::provisioning::materialize_consumer_tls(
                profile_store, identities.device_id(), claim_platform);
            if (materialized.state != wsprrypico::provisioning::ConsumerCommitState::Rejected) {
                pending_tls_restart = true;
                (void)schedule_restart(&restart_context);
            }
        }
        const bool server_attempt_due =
            !server_start_attempted ||
            (tls_lan_wtp && !server.listening() && field_now_ms >= tls_retry_at_ms);
        if (network_only_source && tls_lan_wtp && local_wtp_time_ready && network_hostname_ready &&
            network_only_tls.server_certificate.empty() && field_now_ms >= tls_retry_at_ms &&
            network_state != wsprrypico::wtp::State::Armed &&
            network_state != wsprrypico::wtp::State::Running) {
            tls_retry_at_ms = field_now_ms + 30'000;
            if (wsprrypico::provisioning::generate_consumer_tls(
                    identities.device_id(), local_identity.hostname,
                    clock_now.utc_now_ns / 1'000'000'000ULL, network_only_tls)) {
                tls_credentials = {identities.device_id(),
                                   network_only_tls.hostname,
                                   network_only_tls.port,
                                   network_only_tls.server_certificate,
                                   network_only_tls.server_private_key,
                                   network_only_tls.ca_certificate};
                if (server.configure_credentials(tls_credentials))
                    deployment_matches = wsprrypico::network::deployment_identity_matches(
                        identities.device_id(), tls_credentials.device_id,
                        tls_credentials.hostname);
            }
        }
        if (server_attempt_due && deployment_matches && network.initialized() &&
            (!local_wtp || local_wtp_time_ready) &&
            network_state != wsprrypico::wtp::State::Armed &&
            network_state != wsprrypico::wtp::State::Running) {
            server_start_attempted = true;
            if (tls_lan_wtp)
                tls_retry_at_ms = field_now_ms + 30'000;
            if (network_only_source || !tls_lan_wtp ||
                (runtime_profile.consumer_profile()->tls.hostname == local_identity.hostname &&
                 wsprrypico::provisioning::validate_consumer_tls(
                     runtime_profile.consumer_profile()->tls, identities.device_id(),
                     clock_now.utc_now_ns / 1'000'000'000ULL)))
                (void)server.start();
        }
        if (plain_lan_wtp && network_hostname_ready && local_wtp_time_ready &&
            !server.plain_listening() &&
            (!plain_start_attempted || field_now_ms >= plain_retry_at_ms) &&
            network_state != wsprrypico::wtp::State::Armed &&
            network_state != wsprrypico::wtp::State::Running) {
            plain_start_attempted = true;
            plain_retry_at_ms = field_now_ms + 30'000;
            (void)server.start_plain(plain_lan_port);
        }
        network.listener_status(
            server.configured() || plain_lan_wtp, server.listening() || server.plain_listening(),
            deployment_matches || (plain_lan_wtp && network_hostname_ready) || network_only_source);
        static wsprrypico::usb::ReplyPriority reply_priority;
        const bool allow_http_steps =
            !reply_priority.defer_http(time_us_64(), wsprrypico::usb::console_output_pending());
        server.poll(network.link_up(), softap.ready(),
                    station_ip + (server.port() == 443 ? "" : ":" + std::to_string(server.port())),
                    softap_authority, surface, allow_http_steps);
        auto wtp_binding = wsprrypico::standalone::PicoNetwork::WtpBinding::None;
        unsigned wtp_port = 0;
        if (station_ready && server.admission_open() && local_wtp_time_ready &&
            clock_now.state != wsprrypico::wtp::ClockState::Unsynchronized &&
            clock_now.utc_now_ns != 0) {
            if (plain_lan_wtp && server.plain_listening()) {
                wtp_binding = wsprrypico::standalone::PicoNetwork::WtpBinding::Plain;
                wtp_port = server.plain_port();
            } else if (!plain_lan_wtp && server.listening() && (!local_wtp || tls_lan_wtp)) {
                wtp_binding = wsprrypico::standalone::PicoNetwork::WtpBinding::Tls;
                wtp_port = server.port();
            }
        }
        network.wtp_listener_status(wtp_binding, wtp_port);
        service.poll();
        watchdog_hw->scratch[1] = 5;
#ifdef WSPRRY_PICO_STANDALONE_RF
        const auto usb_us = time_us_64();
#endif
        tud_task();
        wsprrypico::usb::service();
#ifdef WSPRRY_PICO_STANDALONE_RF
        if (measuring)
            maximum(max_usb_us, usb_us);
#endif
        if (wsprrypico::usb::take_console_reset()) {
            length = 0;
            overflow = false;
            console_reply.reset();
            console_input_size = console_input_offset = 0;
        }
        console_reply.poll(wsprrypico::usb::console_write);
        if (!reboot_at && !console_reply.pending() && console_input_offset == console_input_size) {
            console_input_size = wsprrypico::usb::console_transport_read(console_input);
            console_input_offset = 0;
        }
        while (!reboot_at && !console_reply.pending() &&
               console_input_offset < console_input_size) {
            const auto b = console_input[console_input_offset++];
            if (b == '\n') {
                auto response = overflow ? "{\"ok\":false,\"error\":\"line_too_long\"}\n"
                                         : command(std::string_view(line.data(), length));
                if (!console_reply.begin(std::move(response)))
                    (void)console_reply.begin(
                        "{\"ok\":false,\"error\":\"console_response_capacity\"}\n");
                std::fill(line.begin(), line.end(), 0);
                length = 0;
                overflow = false;
            } else if (b != '\r') {
                if (b < 32 || b > 126 || length == line.size())
                    overflow = true;
                else if (!overflow)
                    line[length++] = static_cast<char>(b);
            }
        }
        if (wsprrypico::usb::take_wtp_reset()) {
            offset = size = 0;
            if (wsprrypico::usb::wtp_connected() && runtime_profile_loaded &&
                !consumer_source_selected() && !bootstrap.owner_claim_pending() &&
                !reset_coordinator.pending())
                endpoint.connect("usb-physical");
            else
                endpoint.disconnect();
        }
        const auto now_ms = time_us_64() / 1000ULL;
        if ((consumer_source_selected() || bootstrap.owner_claim_pending()) && !endpoint.closed())
            endpoint.disconnect();
        endpoint.poll(now_ms);
        if (wsprrypico::usb::wtp_connected() && runtime_profile_loaded &&
            !consumer_source_selected() && !bootstrap.owner_claim_pending() &&
            !reset_coordinator.pending()) {
            if (!reboot_at && endpoint.can_receive()) {
                if (offset == size) {
                    size = wsprrypico::usb::wtp_transport_read(input);
                    offset = 0;
                }
#ifdef WSPRRY_PICO_STANDALONE_RF
                const auto request_us = time_us_64();
#endif
                offset += endpoint.receive(std::span(input).subspan(offset, size - offset), now_ms);
#ifdef WSPRRY_PICO_STANDALONE_RF
                if (measuring)
                    maximum(max_request_us, request_us);
#endif
            }
            endpoint.consume_output(wsprrypico::usb::wtp_transport_write(endpoint.output()),
                                    now_ms);
        }
    }
}

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
#include "provisioning/pico/credential_validator.hpp"
#include "provisioning/pico/field_platform.hpp"
#include "provisioning/pico/gatt_transport.hpp"
#include "provisioning/runtime.hpp"
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

#include <malloc.h>
extern "C" char __HeapLimit, __end__, __StackLimit, __StackTop;
#include "hardware/sync.h"
#ifdef WSPRRY_PICO_STANDALONE_RF
#include "rf/pico/worker.hpp"
#include "rf/waveform.hpp"
#else
#include "standalone/dry_run_engine.hpp"
static_assert(WSPRRY_PICO_RF_OUTPUT_DISABLED == 1);
#endif
#include "runtime/allocation_fault.h"

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
    case AccessCode::Ok: return "ok";
    case AccessCode::Invalid: return "invalid_request";
    case AccessCode::AuthenticationRequired: return "authentication_required";
    case AccessCode::ConfirmationRequired: return "confirmation_required";
    case AccessCode::WrongDevice: return "wrong_device";
    case AccessCode::Busy: return "busy";
    case AccessCode::Capacity: return "capacity";
    case AccessCode::Expired: return "expired";
    case AccessCode::Conflict: return "conflict";
    case AccessCode::StorageFault: return "storage_fault";
    case AccessCode::BondEraseFault: return "bond_erase_fault";
    }
    return "invalid_request";
}
std::string access_reply(wsprrypico::provisioning::AccessCode code) {
    return std::string("{\"ok\":") +
           (code == wsprrypico::provisioning::AccessCode::Ok ? "true" : "false") +
           (code == wsprrypico::provisioning::AccessCode::Ok
                ? "}\n"
                : ",\"error\":" + wsprrypico::wtp::json::quote(access_code_name(code)) +
                      "}\n");
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
    const bool recovery = watchdog_enable_caused_reboot();
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
        !access_store_loaded || access_store.state() !=
                                    wsprrypico::provisioning::AccessStoreState::Healthy ||
        (access_store.record() && access_store.record()->reset.pending());
    const bool boot_recovery = recovery || access_recovery;
    // Both adapters claim PIO/DMA resources through the SDK allocator.
#ifdef WSPRRY_PICO_STANDALONE_RF
    auto& engine = wsprrypico::rf::start_worker(clock);
#else
    static wsprrypico::standalone::DryRunEngine engine;
#endif
    static wsprrypico::firmware::PicoIdentitySource identities;
    static wsprrypico::provisioning::RuntimeProfile runtime_profile;
    const bool runtime_profile_loaded =
        profile_store_loaded && runtime_profile.load(profile_store, identities.device_id());
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
    const bool deployment_matches =
        runtime_profile_loaded && !access_recovery &&
        wsprrypico::network::deployment_identity_matches(
            identities.device_id(), tls_credentials.device_id, tls_credentials.hostname);
    static wsprrypico::time::ControllerTimeArbiter time_arbiter(
        clock, monotonic_now, nullptr, identities.device_id());
    static wsprrypico::standalone::PicoNetwork network(time_arbiter, tls_credentials.hostname);
    const bool radio_identity_ok = network.initialize_radio();
    const auto derived_identity = radio_identity_ok
                                      ? wsprrypico::provisioning::derive_local_identity(
                                            identities.device_id(), network.station_mac())
                                      : std::nullopt;
    const auto local_identity = derived_identity.value_or(
        wsprrypico::provisioning::LocalIdentity{});
    static wsprrypico::provisioning::PicoBondStore bond_store;
    static wsprrypico::provisioning::PicoRandomSource random_source;
    static wsprrypico::provisioning::LocalAccessController local_access(
        access_store, bond_store, random_source, identities.device_id(),
        service.status().boot_id, local_identity);
    static wsprrypico::provisioning::SoftApCoordinator softap_coordinator(access_store);
    softap_coordinator.no_profile(runtime_profile.source() ==
                                  wsprrypico::provisioning::RuntimeSource::Unprovisioned);
    softap_coordinator.recovery(boot_recovery);
    static wsprrypico::provisioning::PicoSoftAp softap;
    std::optional<wsprrypico::standalone::Config> runtime_network_config;
    if (store_loaded && store.config())
        runtime_network_config = runtime_profile.overlay(*store.config());
    if (boot_recovery)
        (void)scheduler.command("STOP");
    watchdog_hw->scratch[1] = 2;
    if (!boot_recovery && radio_identity_ok && runtime_network_config)
        (void)network.start(*runtime_network_config);
    static wsprrypico::network::BrowserApi browser_api(service, store, scheduler, network,
                                                       identities.device_id(),
                                                       wsprrypico::firmware::kFirmwareVersion);
    static wsprrypico::network::PicoServer server(service, browser_api, identities.device_id(),
                                                  wsprrypico::firmware::kFirmwareVersion,
                                                  tls_credentials);
    const auto softap_authority =
        local_identity.hostname + (server.port() == 443 ? "" : ":" + std::to_string(server.port()));
    static wsprrypico::provisioning::SoftApHttpAdmission softap_admission(
        local_access, identities.device_id(), softap_authority);
    static wsprrypico::network::SoftApApi softap_api(browser_api, softap_admission, local_access,
                                                     time_arbiter, service, identities.device_id(),
                                                     wsprrypico::firmware::kFirmwareVersion);
    server.softap_handler(&softap_api, softap_interface, nullptr);
    static wsprrypico::network::PicoBootstrapServer bootstrap(
        identities.device_id(), wsprrypico::firmware::kFirmwareVersion, softap_interface, nullptr);
    // The plaintext listener is exclusive to a truly unprovisioned recovery
    // surface.  Starting it for provisioned images would consume the single
    // bounded lwIP listen PCB before the authenticated TLS listener starts.
    const bool bootstrap_started =
        derived_identity &&
        runtime_profile.source() == wsprrypico::provisioning::RuntimeSource::Unprovisioned &&
        bootstrap.start();
    browser_api.set_active_job_connections(true);
    bool server_start_attempted = false;
    static wsprrypico::provisioning::PicoIndicatorOutput indicator_output;
    static wsprrypico::provisioning::IndicatorController indicator(
        indicator_output, identities.device_id());
    network.listener_status(server.configured(), server.listening(), deployment_matches);
    watchdog_hw->scratch[1] = 3;
    std::array<std::uint8_t, 64> input{};
    std::size_t offset = 0, size = 0;
    std::array<char, wsprrypico::standalone::max_config_bytes + 7> line{};
    std::size_t length = 0;
    bool overflow = false;
    std::uint64_t reboot_at = 0;
    bool bootloader = false, browser_reboot = false;
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
    static wsprrypico::provisioning::MbedTlsCredentialValidator credential_validator(
        identities.device_id());
    static wsprrypico::provisioning::PicoActivationPlatform activation_platform(
        profile_store, runtime_profile, service, server, identities.device_id(),
        schedule_restart, &restart_context);
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
        ble_session, &ble_endpoint, provisioning_command.identity(), local_identity.advertising_name,
        monotonic_ms, nullptr);
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
    auto command = [&](std::string_view text) -> std::string {
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
            result.reserve(6144);
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
            else
                result += "\"fault\"";
            number_field(result, "provisioning_generation", runtime_profile.generation(), true);
            number_field(result, "provisioning_fault",
                         static_cast<unsigned>(runtime_profile.fault()));
            result += ",\"radio_identity_valid\":";
            result += derived_identity ? "true" : "false";
            result += ",\"local_suffix\":" +
                      wsprrypico::wtp::json::quote(local_identity.suffix);
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
            result += ",\"access_default_password\":";
            result += access_store.record() && access_store.record()->default_password ? "true" : "false";
            result += ",\"ble_running\":" + std::string(gatt.running() ? "true" : "false");
            result += ",\"ble_enrollment_open\":" +
                      std::string(local_access.enrollment_open(time_us_64() / 1000ULL) ? "true" : "false");
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
            else if (access_store.state() ==
                     wsprrypico::provisioning::AccessStoreState::Healthy)
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
            result += ",\"send_requested\":" +
                      std::string(ble.send_requested ? "true" : "false");
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
            binding.parameters = wsprrypico::wtp::sha256(std::span(
                reinterpret_cast<const std::uint8_t*>(text.data()), text.size()));
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
        scheduler.poll();
#ifdef WSPRRY_PICO_STANDALONE_RF
        if (measuring)
            maximum(max_refill_us, loop_us);
#endif
        watchdog_hw->scratch[1] = 4;
        const auto network_state = service.activity().state;
        if (server.listening() || (network_state != wsprrypico::wtp::State::Armed &&
                                   network_state != wsprrypico::wtp::State::Running))
            network.poll();
        const auto field_now_ms = time_us_64() / 1000ULL;
        if (!gatt.running() && !gatt_start_attempted && derived_identity &&
            local_access.ble_available()) {
            gatt_start_attempted = true;
            (void)gatt.start();
        }
        if (gatt.running())
            gatt.poll();
        softap_coordinator.station(network.link_up(), field_now_ms);
        softap_coordinator.token_records(
            local_access.live_softap_sessions(field_now_ms, service.owner_session_id()));
        softap_coordinator.reply_active(server.softap_active());
        const bool request_softap = softap_coordinator.poll(field_now_ms);
        const auto surface = softap_coordinator.surface(
            service.clock_snapshot().state != wsprrypico::wtp::ClockState::Unsynchronized);
        if (request_softap && !softap.running() && derived_identity) {
            const auto* access = access_store.record();
            if (access_store.healthy() && access)
                (void)softap.start(local_identity, access->password);
            else if (surface == wsprrypico::provisioning::SoftApSurface::BlankReadOnly)
                (void)softap.start(local_identity, local_identity.default_password);
        } else if (!request_softap && softap.running()) {
            (void)network.softap_name(false, {});
            softap.stop();
        }
        const bool softap_name_ready = network.softap_name(softap.ready(), local_identity.hostname);
        bootstrap.poll(bootstrap_started && softap.ready() &&
                       surface == wsprrypico::provisioning::SoftApSurface::BlankReadOnly);
        const bool softap_service_ready =
            softap.ready() && (surface == wsprrypico::provisioning::SoftApSurface::BlankReadOnly
                                   ? bootstrap.listening()
                                   : softap_name_ready && server.listening());
        softap_coordinator.ready(softap_service_ready);
        indicator.softap_ready(softap_coordinator.status(field_now_ms).ready);
        indicator.poll(field_now_ms);
        service.poll();
        if (!server_start_attempted && deployment_matches && network.initialized()) {
            server_start_attempted = true;
            (void)server.start();
            network.listener_status(server.configured(), server.listening(),
                                    deployment_matches);
        }
        static wsprrypico::usb::ReplyPriority reply_priority;
        const bool allow_http_steps = !reply_priority.defer_http(
            time_us_64(), wsprrypico::usb::console_output_pending());
        server.poll(network.link_up(), softap.ready(),
                    network.ipv4() +
                        (server.port() == 443 ? "" : ":" + std::to_string(server.port())),
                    softap_authority, surface, allow_http_steps);
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
        }
        std::array<std::uint8_t, 64> console{};
        const auto count = reboot_at ? 0 : wsprrypico::usb::console_transport_read(console);
        for (std::size_t i = 0; i < count; ++i) {
            const auto b = console[i];
            if (b == '\n') {
                const auto response = overflow ? "{\"ok\":false,\"error\":\"line_too_long\"}\n"
                                               : command(std::string_view(line.data(), length));
                if (!wsprrypico::usb::console_write(response))
                    (void)wsprrypico::usb::console_write(
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
            if (wsprrypico::usb::wtp_connected())
                endpoint.connect("usb-physical");
            else
                endpoint.disconnect();
        }
        const auto now_ms = time_us_64() / 1000ULL;
        endpoint.poll(now_ms);
        if (wsprrypico::usb::wtp_connected()) {
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

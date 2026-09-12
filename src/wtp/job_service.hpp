#pragma once

#include "wtp/sha256.hpp"

#include <cstddef>
#include <cstdint>
#include <deque>
#include <limits>
#include <optional>
#include <string>
#include <string_view>
#include <variant>
#include <vector>

namespace wsprrypico::wtp {

enum class State { Empty, Loaded, Armed, Running, Complete, Aborted, Missed, Failed };
enum class ClockState { Unsynchronized, Synchronized, Holdover };
enum class LeapState { Normal, InsertPending, DeletePending, Unknown };

struct ClockSnapshot {
    ClockState state = ClockState::Unsynchronized;
    std::uint64_t utc_now_ns = 0;
    std::uint64_t monotonic_now_ns = 0;
    std::uint64_t uncertainty_ns = 0;
    std::uint64_t sync_age_ns = 0;
    LeapState leap = LeapState::Unknown;
    std::optional<std::uint64_t> leap_transition_utc_ns;
    bool operator==(const ClockSnapshot&) const = default;
};

class Clock {
  public:
    virtual ~Clock() = default;
    [[nodiscard]] virtual ClockSnapshot snapshot() const = 0;
};

class IdentitySource {
  public:
    virtual ~IdentitySource() = default;
    [[nodiscard]] virtual std::string new_boot_id() = 0;
};

struct RfEvent {
    std::uint64_t offset_ns = 0;
    std::uint64_t duration_ns = 0;
    bool rf_on = false;
    std::optional<std::uint64_t> frequency_nhz;

    bool operator==(const RfEvent&) const = default;
};

struct Job {
    std::string job_id;
    std::string profile = "rf-events/1";
    std::string mode;
    std::uint64_t total_duration_ns = 0;
    std::vector<RfEvent> events;
    bool allow_frequency_adjustment = false;

    bool operator==(const Job&) const = default;
};

enum class EngineState { Idle, Armed, Running, Complete, Failed, Missed };

// The requested UTC second supplies an exclusive latest-start boundary.
constexpr std::uint64_t start_window_ns(std::uint64_t utc_ns) {
    return 1'000'000'000 - utc_ns % 1'000'000'000;
}

struct LocalStartConditions {
    const Clock* clock = nullptr;
    std::uint64_t start_utc_ns = 0;
    std::uint64_t maximum_uncertainty_ns = 0;
    std::uint64_t maximum_holdover_age_ns = 0;
    std::uint64_t start_adjustment_ns = 0;
};

struct EngineReport {
    EngineState state = EngineState::Idle;
    bool output_active = false;
    std::optional<std::uint64_t> launch_monotonic_ns = {};
};

struct FrequencyAdjustment {
    std::size_t event_index;
    std::uint64_t requested_frequency_nhz;
    std::uint64_t realized_frequency_nhz;

    bool operator==(const FrequencyAdjustment&) const = default;
};

struct PrepareResult {
    bool accepted = false;
    std::vector<FrequencyAdjustment> adjustments;
};

class RfEngine {
  public:
    static constexpr std::uint64_t maximum_completion_acknowledgement_ns = 100'000;
    virtual ~RfEngine() = default;
    virtual PrepareResult prepare(const Job& job) = 0;
    virtual bool set_frequency_correction_ppb(std::int32_t) {
        return false;
    }
    virtual std::string_view diagnostic() const {
        return {};
    }
    [[nodiscard]] virtual bool schedules_locally() const {
        return false;
    }
    [[nodiscard]] virtual std::uint64_t start_resolution_ns() const {
        return 1;
    }
    // Finite locally scheduled hardware may finish its IRQ acknowledgement just
    // after nominal RF end. This never authorizes additional waveform samples.
    [[nodiscard]] virtual std::uint64_t completion_acknowledgement_ns() const {
        return 0;
    }
    virtual bool schedule(const Job&, std::uint64_t, const LocalStartConditions&) {
        return false;
    }
    virtual bool begin(const Job& job, std::uint64_t start_monotonic_ns) = 0;
    [[nodiscard]] virtual EngineReport poll(std::uint64_t monotonic_now_ns) = 0;
    virtual bool disable(std::uint64_t deadline_monotonic_ns) = 0;
    [[nodiscard]] virtual bool output_active() const = 0;
};

enum class ErrorCode {
    None,
    InvalidFrame,
    InvalidMessage,
    UnsupportedVersion,
    HelloRequired,
    UnknownOperation,
    AuthenticationRequired,
    SessionReplaced,
    Busy,
    NotOwner,
    LeaseExpired,
    RequestIdReuse,
    InvalidState,
    JobNotFound,
    JobIdConflict,
    JobLimitExceeded,
    UnsupportedProfile,
    UnsupportedMode,
    FrequencyRejected,
    ArmConflict,
    ClockUnsynchronized,
    ClockUncertain,
    LeapUnsafe,
    ArmTooLate,
    ArmTooFar,
    MissedStart,
    OutputStateUnknown,
    DeviceFault,
    InternalError,
};

struct HelloBody {
    std::vector<std::string> versions;
};
struct ClaimBody {
    std::string owner_id;
    std::uint32_t lease_ms = 0;
};
struct RenewBody {
    std::string owner_id;
    std::uint32_t lease_ms = 0;
};
struct ArmBody {
    std::string job_id;
    std::uint64_t start_utc_ns = 0;
    std::uint64_t max_start_uncertainty_ns = 0;
};
struct AbortBody {
    std::string job_id;
};
struct PingBody {
    std::optional<std::string> token;
};

using RequestBody = std::variant<std::monostate, HelloBody, ClaimBody, RenewBody, Job, ArmBody,
                                 AbortBody, PingBody>;

struct Request {
    std::string protocol = "WTP/1";
    std::string session_id;
    std::string request_id;
    std::string principal;
    std::string operation;
    PayloadDigest payload_digest{};
    RequestBody body;
    bool body_valid = true; // Adapter schema result; checked after replay/operation recognition.
};

struct TerminalRecord {
    std::string job_id;
    State state;
    std::uint64_t ended_monotonic_ns;
    bool output_active;
    ErrorCode error;
    bool operator==(const TerminalRecord&) const = default;
};

// Internal activity observation: no identity/history copies or retained views.
// Each observation still queries the engine's live output state.
struct ServiceActivity {
    State state;
    bool output_active;
    bool owned;
};

struct ServiceStatus {
    std::string boot_id;
    State state;
    bool output_active;
    std::optional<std::string> owner_id;
    std::optional<std::string> job_id;
    std::vector<TerminalRecord> terminal_records;
    bool operator==(const ServiceStatus&) const = default;
};

struct Response {
    bool ok = false;
    ErrorCode error = ErrorCode::None;
    State state = State::Empty;
    std::string job_id;
    std::string boot_id;
    std::string owner_id;
    std::uint64_t start_monotonic_ns = 0;
    std::uint64_t expires_monotonic_ns = 0;
    std::uint32_t granted_lease_ms = 0;
    bool output_active = false;
    bool close_connection = false;
    std::optional<std::string> ping_token;
    std::vector<FrequencyAdjustment> adjustments;
    std::optional<ClockSnapshot> clock_snapshot;
    std::optional<ServiceStatus> status_snapshot;
    std::uint64_t start_utc_ns = 0;

    bool operator==(const Response&) const = default;
};

struct ServiceConfig {
    std::string capability_engine = "inhibited-no-rf";
    std::vector<std::string> supported_modes{"wspr", "qrss", "fskcw", "dfcw", "cw", "tone"};
    std::uint64_t minimum_frequency_nhz = 1;
    std::uint64_t maximum_frequency_nhz = std::numeric_limits<std::uint64_t>::max();
    std::size_t max_events = 512;
    std::uint64_t max_job_duration_ns = 86'400'000'000'000ULL;
    std::uint64_t minimum_arm_lead_ns = 100'000'000ULL;
    std::uint64_t maximum_arm_ahead_ns = 604'800'000'000'000ULL;
    std::uint64_t maximum_arm_uncertainty_ns = 1'000'000ULL;
    std::uint64_t maximum_holdover_age_ns = 0;
    std::uint64_t output_disable_timeout_ns = 100'000'000ULL;
    std::size_t response_cache_entries = 8;
    std::uint64_t response_cache_ttl_ns = 300'000'000'000ULL;
    std::size_t terminal_record_entries = 8;
    std::uint64_t terminal_record_ttl_ns = 3'600'000'000'000ULL;
};

class JobService {
  public:
    JobService(Clock& clock, RfEngine& engine, IdentitySource& identities,
               ServiceConfig config = {});

    Response handle(const Request& request);
    // Physical Console safety control only; never exposed as a network operation.
    Response local_abort();
    void poll();
    void reset();
    [[nodiscard]] ServiceActivity activity() const;
    [[nodiscard]] ServiceStatus status() const;
    [[nodiscard]] ClockSnapshot clock_snapshot() const {
        return clock_.snapshot();
    }
    [[nodiscard]] const ServiceConfig& config() const {
        return config_;
    }

  private:
    struct Session {
        std::string session_id;
        std::string principal;
        std::uint64_t last_seen_monotonic_ns;
    };
    struct Owner {
        std::string owner_id;
        std::string session_id;
        std::string principal;
        std::uint64_t expires_monotonic_ns;
        bool release_after_terminal = false;
    };
    struct ArmRecord {
        std::string job_id;
        std::uint64_t start_utc_ns;
        std::uint64_t max_uncertainty_ns;
        std::uint64_t start_monotonic_ns;
        Response response;
        bool scheduled_locally = false;
        std::optional<std::uint64_t> launch_monotonic_ns = {};
    };
    struct RetainedJob {
        std::string job_id;
        PayloadDigest digest;
        Response load_response;
        std::optional<ArmRecord> arm;
    };

    struct ReplayEntry {
        std::string session_id;
        std::string request_id;
        PayloadDigest payload_digest;
        Response response;
        std::uint64_t completed_monotonic_ns;
        std::uint64_t lru;
    };

    Response dispatch(const Request& request);
    Response abort_job(std::string_view job_id);
    Response reject(ErrorCode code) const;
    Response success() const;
    bool valid_id(std::string_view value) const;
    bool owns(const Request& request) const;
    ErrorCode validate_job(const Job& job) const;
    ErrorCode validate_arm(const ArmBody& arm, const ClockSnapshot& now,
                           std::uint64_t& start_monotonic_ns) const;
    void expire_resources(std::uint64_t monotonic_now_ns);
    void record_terminal(State state, ErrorCode error, std::uint64_t now_ns);
    void clear_job();
    void touch_terminal(std::string_view job_id);
    void prune_replay(std::uint64_t now_ns);
    void prune_terminals(std::uint64_t now_ns);
    void prune_sessions(std::uint64_t now_ns);
    std::optional<Response> replay(const Request& request, std::uint64_t now_ns, bool& conflict);
    void remember(const Request& request, const Response& response, std::uint64_t now_ns);

    Clock& clock_;
    RfEngine& engine_;
    IdentitySource& identities_;
    ServiceConfig config_;
    std::vector<Session> sessions_;
    std::optional<Owner> owner_;
    std::optional<Job> job_;
    std::vector<FrequencyAdjustment> adjustments_;
    std::optional<ArmRecord> arm_;
    std::deque<ReplayEntry> replay_cache_;
    std::deque<TerminalRecord> terminal_records_;
    std::deque<RetainedJob> retained_jobs_;
    State state_ = State::Empty;
    std::string boot_id_;
    std::uint64_t lru_sequence_ = 0;
    bool ready_ = false;
};

} // namespace wsprrypico::wtp

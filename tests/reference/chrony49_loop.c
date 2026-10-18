// SPDX-License-Identifier: MIT
// Original in-process plant for the external Chrony APIs. No OS clock writes.
// Clock/source algorithms are the separately linked, unmodified GPL reference.
#include "conf.h"
#include "config.h"
#include "local.h"
#include "logging.h"
#include "ntp_sources.h"
#include "reference.h"
#include "sched.h"
#include "sources.h"
#include "sys_generic.h"
#include "sysincl.h"

#include <inttypes.h>

static const time_t epoch = 1800000000;
static long double system_seconds = 0, monotonic_seconds = 0;
static uint64_t truth_ns, raw_ns;
static long double current_raw_ns;
static double applied_ppm;
static int descriptors[2], action, slot, stratum;
static uint64_t server_ns;
static uint64_t server_receive_ns, server_reference_ns;
static uint32_t upstream_delay_wire, upstream_dispersion_wire;
static int captured, precision, leap_status;
static SRC_Instance sources[4];
static struct timespec sent[4];
static uint64_t sent_raw_ns[4];
static uint64_t last_received_raw_ns[4];
static int pending[4];
static IPAddr addresses[4];

static void stamp(long double seconds, time_t base, struct timespec* t) {
    time_t whole = (time_t)floorl(seconds);
    t->tv_sec = base + whole;
    t->tv_nsec = (long)llroundl((seconds - whole) * 1e9L);
    if (t->tv_nsec == 1000000000L) {
        ++t->tv_sec;
        t->tv_nsec = 0;
    }
}
static long double seconds(const struct timespec* t) {
    return (long double)(t->tv_sec - epoch) + t->tv_nsec / 1e9L;
}
int clock_gettime(clockid_t id, struct timespec* t) {
    if (id == CLOCK_REALTIME)
        stamp(system_seconds, epoch, t);
    else
        stamp(monotonic_seconds, 0, t);
    return 0;
}
static double read_frequency(void) {
    return applied_ppm;
}
static double set_frequency(double value) {
    return applied_ppm = value;
}
static int step(double value) {
    (void)value;
    exit(10); // This profile slews after acquisition; unexpected stepping is a harness error.
}
// Advance Chrony's own scheduler to each driver timeout, even between supplied
// physical events. A status-probe grid must not decide when a slew ends.
int select(int nfds, fd_set* readers, fd_set* writers, fd_set* exceptions,
           struct timeval* timeout) {
    if (!readers || !FD_ISSET(descriptors[0], readers))
        exit(8);
    for (int fd = 0; fd < nfds; ++fd)
        if ((readers && FD_ISSET(fd, readers) && fd != descriptors[0]) ||
            (writers && FD_ISSET(fd, writers)) || (exceptions && FD_ISSET(fd, exceptions)))
            exit(8); // This harness must never acquire a network or other IO surface.
    const long double remaining = (raw_ns - current_raw_ns) / 1e9L / (1 + applied_ppm / 1e6L);
    long double wait = timeout ? timeout->tv_sec + timeout->tv_usec / 1e6L : remaining;
    // select() has microsecond resolution; a rounded-down sub-microsecond
    // timeout still consumes time, rather than spinning a frozen fake clock.
    if (wait <= 0 && remaining > 0)
        wait = .000001L;
    const int external = remaining <= wait + .5e-9L;
    const long double elapsed = external ? remaining : wait;
    if (elapsed < -.5e-9L)
        exit(9);
    system_seconds += elapsed;
    monotonic_seconds += elapsed;
    current_raw_ns += elapsed * 1e9L * (1 + applied_ppm / 1e6L);
    if (readers)
        FD_ZERO(readers);
    if (writers)
        FD_ZERO(writers);
    if (exceptions)
        FD_ZERO(exceptions);
    if (external) {
        current_raw_ns = raw_ns;
        if (!readers || write(descriptors[1], "x", 1) != 1)
            exit(7);
        FD_SET(descriptors[0], readers);
        return 1;
    }
    return 0;
}
static int next(void) {
    if (scanf("%" SCNu64 " %" SCNu64 " %d %d %" SCNu64 " %d", &truth_ns, &raw_ns, &action, &slot,
              &server_ns, &stratum) != 6)
        return 0;
    if (raw_ns + .5L < current_raw_ns || slot < 0 || slot >= 4)
        exit(4);
    server_receive_ns = server_ns;
    server_reference_ns = server_ns ? server_ns - 1000000000ULL : 0;
    upstream_delay_wire = upstream_dispersion_wire = leap_status = 0;
    precision = -20;
    if (captured && scanf("%" SCNu64 " %" SCNu64 " %" SCNu32 " %" SCNu32 " %d %d",
                          &server_receive_ns, &server_reference_ns, &upstream_delay_wire,
                          &upstream_dispersion_wire, &precision, &leap_status) != 6)
        exit(11);
    if (precision < -40 || precision > 0 || leap_status < 0 || leap_status > 3)
        exit(11);
    return 1;
}
static void event(int fd, int flags, void* context) {
    (void)flags;
    (void)context;
    char byte;
    if (read(fd, &byte, 1) != 1)
        exit(5);
    if (action == 1) {
        LCL_ReadRawTime(&sent[slot]);
        sent_raw_ns[slot] = raw_ns;
        pending[slot] = 1;
    } else if (action == 2) {
        if (!pending[slot])
            exit(6);
        struct timespec raw, first, last;
        LCL_ReadRawTime(&raw);
        LCL_CookTime(&sent[slot], &first, NULL);
        LCL_CookTime(&raw, &last, NULL);
        const long double midpoint = (seconds(&first) + seconds(&last)) / 2;
        NTP_Sample sample = {0};
        stamp(midpoint, epoch, &sample.time);
        // Same basic NTP 32-bit fraction and nanosecond decoding as the Pico.
        const uint64_t fraction = ((server_ns % 1000000000ULL) << 32) / 1000000000ULL;
        const long double server_seconds =
            (long double)((int64_t)(server_ns / 1000000000ULL) - epoch) +
            ((fraction * 1000000000ULL) >> 32) / 1e9L;
        const uint64_t receive_fraction =
            ((server_receive_ns % 1000000000ULL) << 32) / 1000000000ULL;
        const long double server_receive_seconds =
            (long double)((int64_t)(server_receive_ns / 1000000000ULL) - epoch) +
            ((receive_fraction * 1000000000ULL) >> 32) / 1e9L;
        sample.offset = (server_seconds + server_receive_seconds) / 2 - midpoint;
        sample.peer_delay = fmax(.000001, seconds(&last) - seconds(&first) -
                                              (server_seconds - server_receive_seconds));
        sample.root_delay = sample.peer_delay + fmax(0, (int32_t)upstream_delay_wire / 65536.0);
        sample.peer_dispersion = sample.root_dispersion =
            fmax(.000001, exp2(precision)) + (raw_ns - sent_raw_ns[slot]) * 50e-15;
        sample.root_dispersion += upstream_dispersion_wire / 65536.0;
        SRC_UpdateStatus(sources[slot], stratum, (NTP_Leap)leap_status);
        SRC_UpdateReachability(sources[slot], 1);
        SRC_AccumulateSample(sources[slot], &sample);
        last_received_raw_ns[slot] = raw_ns;
        SRC_SelectSource(sources[slot]);
        pending[slot] = 0;
    } else if (action == 3) {
        SRC_UpdateReachability(sources[slot], 0);
        SRC_SelectSource(sources[slot]);
        pending[slot] = 0;
    }
    if (action != 1) {
        RPT_TrackingReport tracking = {0};
        REF_GetTrackingReport(&tracking);
        int selected = -1;
        for (int i = 0; i < 4; ++i)
            if (SRC_IsSyncPeer(sources[i]))
                selected = i;
        // Pure frequency and actual applied mapping are deliberately separate.
        const double pure = LCL_ReadAbsoluteFrequency();
        int samples = selected >= 0 ? SST_Samples(SRC_GetSourcestats(sources[selected])) : 0;
        if (action == 2 && getenv("MICROCHRONY_DIAGNOSTICS")) {
            fprintf(stderr, "D %llu %d %.15g %.15g %.15g", (unsigned long long)truth_ns, slot,
                    tracking.last_offset, tracking.resid_freq_ppm, tracking.last_update_interval);
            for (int i = 0; i < 4; ++i) {
                SST_Stats stats = SRC_GetSourcestats(sources[i]);
                RPT_SourcestatsReport report = {0};
                RPT_SelectReport selection = {0};
                struct timespec now, ref;
                double average, sd, frequency, frequency_sd, skew, delay, dispersion;
                LCL_ReadCookedTime(&now, NULL);
                SST_DoSourcestatsReport(stats, &report, &now);
                SRC_GetSelectReport(i, &selection);
                if (!SST_Samples(stats)) {
                    fprintf(stderr, " 0 0 0 0 0 0 0 %c %.15g", selection.state_char,
                            selection.score);
                    continue;
                }
                SST_GetTrackingData(stats, &ref, &average, &sd, &frequency, &frequency_sd, &skew,
                                    &delay, &dispersion);
                const long double age = seconds(&now) - seconds(&ref);
                const long double predicted = average + frequency * age;
                const double raw_rate = (1 - frequency) / (1 + pure * 1e-6) - 1;
                fprintf(stderr, " %lu %lu %.15g %.15g %.15g %.15g %.15g %c %.15g", report.n_samples,
                        report.n_runs, raw_rate * 1e6, frequency_sd * 1e6, skew * 1e6, sd,
                        (double)(seconds(&now) - predicted - truth_ns / 1e9L), selection.state_char,
                        selection.score);
            }
            fputc('\n', stderr);
        }
        printf("%llu %d %.0Lf %.12g %.12g %.12g %.12g %d %d", (unsigned long long)truth_ns, action,
               system_seconds * 1e9L, -pure / (1 + pure * 1e-6),
               -applied_ppm / (1 + applied_ppm * 1e-6), tracking.current_correction * 1e9,
               tracking.skew_ppm, selected, samples);
        if (captured) {
            const long double bound =
                selected >= 0
                    ? ceill((fabs(tracking.current_correction) + fmax(0, tracking.root_delay) / 2 +
                             fmax(0, tracking.root_dispersion)) *
                            1e9L)
                    : 1e18L; // Unselected; deliberately outside the timing gate.
            const uint64_t age = selected >= 0 && raw_ns >= last_received_raw_ns[selected]
                                     ? raw_ns - last_received_raw_ns[selected]
                                     : UINT64_MAX;
            printf(" %.0Lf %llu", bound, (unsigned long long)age);
        }
        putchar('\n');
    }
    if (!next())
        SCH_QuitProgram();
}
static void rule(const char* text) {
    char* line = strdup(text);
    CNF_ParseLine(NULL, 0, line);
    free(line);
}
int main(int argc, char** argv) {
    if (argc != 2 && argc != 3)
        return 2;
    const int phase_only = argc == 3 && strcmp(argv[2], "captured-phase") == 0;
    captured = argc == 3 && (strcmp(argv[2], "captured") == 0 || phase_only);
    if (argc == 3 && !captured)
        return 2;
    LOG_Initialise();
    LOG_SetMinSeverity(LOGS_FATAL);
    CNF_Initialise(0, 0);
    rule("clockprecision 0.000001");
    rule("maxdrift 100");
    rule("maxclockerror 50");
    if (phase_only)
        rule("maxupdateskew 0.000000000001"); // Offline counterfactual only.
    LCL_Initialise();
    SCH_Initialise();
    SYS_Generic_CompleteFreqDriver(100000, 0, read_frequency, set_frequency, step, 0, 0, NULL, NULL,
                                   NULL, NULL);
    LCL_SetAbsoluteFrequency(atof(argv[1]));
    SST_Initialise();
    REF_Initialise();
    SRC_Initialise();
    NSR_Initialise();
    for (int i = 0; i < 4; ++i) {
        addresses[i].family = IPADDR_INET4;
        addresses[i].addr.in4 = 0xc0000201 + i;
        sources[i] = SRC_CreateNewInstance(i + 1, SRC_NTP, 0, 0, &addresses[i], 6, 64, 0, 1, 0);
        SRC_SetActive(sources[i]);
    }
    if (pipe(descriptors))
        return 3;
    SCH_AddFileHandler(descriptors[0], SCH_FILE_INPUT, event, NULL);
    if (next()) {
        SCH_MainLoop();
    }
    return 0;
}

/* Original test harness. Linked only to the private external Chrony oracle. */
#include "conf.h"
#include "config.h"
#include "local.h"
#include "localp.h"
#include "logging.h"
#include "sourcestats.h"
#include "sysincl.h"

#include <inttypes.h>
static double read_frequency(void) {
    return 0;
}
static double set_frequency(double value) {
    return value;
}
static void accrue(double value, double rate) {
    (void)value;
    (void)rate;
}
static int step(double value) {
    (void)value;
    return 0;
}
static void correction(struct timespec* raw, double* value, double* error) {
    (void)raw;
    *value = 0;
    if (error)
        *error = 0;
}
int main(int argc, char** argv) {
    const int raw = argc == 2 && strcmp(argv[1], "raw") == 0;
    if (argc != 1 && !raw)
        return 2;
    LOG_Initialise();
    LOG_SetMinSeverity(LOGS_FATAL);
    CNF_Initialise(0, 0);
    char precision[] = "clockprecision 0.000001";
    CNF_ParseLine(NULL, 0, precision);
    LCL_Initialise();
    lcl_RegisterSystemDrivers(read_frequency, set_frequency, accrue, step, correction, NULL, NULL);
    SST_Initialise();
    IPAddr ip = {0};
    ip.family = IPADDR_INET4;
    ip.addr.in4 = 0xc0000201;
    SST_Stats stats = SST_CreateInstance(1, &ip, CNF_GetMinSamples(), 64, 0, 1);
    fprintf(stderr, "min_samples=%d\n", SST_GetMinSamples(stats));
    double when, offset, delay, dispersion;
    unsigned id = 0;
    for (;;) {
        uint64_t send, receive, utc;
        if (raw) {
            if (scanf("%" SCNu64 " %" SCNu64 " %" SCNu64, &send, &receive, &utc) != 3)
                break;
            const uint64_t midpoint = send + (receive - send) / 2;
            const uint64_t fraction = ((utc % 1000000000ULL) << 32) / 1000000000ULL;
            utc = utc / 1000000000ULL * 1000000000ULL + ((fraction * 1000000000ULL) >> 32);
            when = 1800000000 + midpoint / 1e9;
            offset = ((int64_t)(utc - 1800000000000000000ULL) - (int64_t)midpoint) / 1e9;
            delay = (receive - send) / 1e9;
            dispersion = .000001 + delay * 50e-6;
        } else if (scanf("%lf %lf %lf %lf", &when, &offset, &delay, &dispersion) != 4) {
            break;
        }
        NTP_Sample sample = {0};
        sample.time.tv_sec = (time_t)when;
        sample.time.tv_nsec = (long)((when - sample.time.tv_sec) * 1e9);
        if (raw) {
            const uint64_t midpoint = send + (receive - send) / 2;
            sample.time.tv_sec = 1800000000 + midpoint / 1000000000;
            sample.time.tv_nsec = midpoint % 1000000000;
        }
        sample.offset = offset;
        sample.peer_delay = sample.root_delay = delay;
        sample.peer_dispersion = raw ? dispersion : 1e-6;
        sample.root_dispersion = dispersion;
        SST_AccumulateSample(stats, &sample);
        SST_DoNewRegression(stats);
        if (getenv("MICROCHRONY_DIAGNOSTICS")) {
            fprintf(stderr, "STATE %u\n", id + 1);
            SST_SaveToFile(stats, stderr);
        }
        RPT_SourcestatsReport report = {0};
        SST_DoSourcestatsReport(stats, &report, &sample.time);
        struct timespec reference;
        double average, sd, frequency, frequency_sd, skew, root_delay, root_dispersion;
        SST_GetTrackingData(stats, &reference, &average, &sd, &frequency, &frequency_sd, &skew,
                            &root_delay, &root_dispersion);
        printf("%u %lu %lu %.15g %.15g %.15g %.15g %.15g %.15g %.15g %.15g\n", ++id,
               report.n_samples, report.n_runs, frequency, frequency_sd, skew, average, sd,
               root_delay, root_dispersion, SST_GetJitterAsymmetry(stats));
    }
    SST_DeleteInstance(stats);
    SST_Finalise();
    LCL_Finalise();
    CNF_Finalise();
    LOG_Finalise();
    return 0;
}

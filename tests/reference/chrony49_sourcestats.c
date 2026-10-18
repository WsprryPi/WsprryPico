/* Original test harness. Linked only to the private external Chrony oracle. */
#include "conf.h"
#include "config.h"
#include "local.h"
#include "localp.h"
#include "logging.h"
#include "sourcestats.h"
#include "sysincl.h"
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
int main(void) {
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
    while (scanf("%lf %lf %lf %lf", &when, &offset, &delay, &dispersion) == 4) {
        NTP_Sample sample = {0};
        sample.time.tv_sec = (time_t)when;
        sample.time.tv_nsec = (long)((when - sample.time.tv_sec) * 1e9);
        sample.offset = offset;
        sample.peer_delay = sample.root_delay = delay;
        sample.peer_dispersion = 1e-6;
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

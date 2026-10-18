// SPDX-License-Identifier: MIT
// Original harness for the external GPL reference. No host clock writes.
#include "conf.h"
#include "config.h"
#include "local.h"
#include "localp.h"
#include "logging.h"
#include "reference.h"
#include "sched.h"
#include "sys_generic.h"
#include "sysincl.h"
static double raw_now = 1800000000, frequency = 0, accrued = 0, corr_rate = 0;
static int wake[2];
static unsigned number;
static double when, offset, offset_sd, residual_frequency, frequency_sd, skew;
static IPAddr address;
int clock_gettime(clockid_t id, struct timespec* t) {
    (void)id;
    t->tv_sec = (time_t)raw_now;
    t->tv_nsec = (long)((raw_now - t->tv_sec) * 1e9);
    return 0;
}
static double read_frequency(void) {
    return frequency;
}
static double set_frequency(double value) {
    return frequency = value;
}
static void accrue(double value, double rate) {
    accrued = value;
    corr_rate = rate;
}
static int step(double value) {
    raw_now -= value;
    return 0;
}
static void correction(struct timespec* t, double* value, double* error) {
    (void)t;
    *value = 0;
    if (error)
        *error = 0;
}
static int next(void) {
    return scanf("%lf %lf %lf %lf %lf %lf", &when, &offset, &offset_sd, &residual_frequency,
                 &frequency_sd, &skew) == 6;
}
static void event(int fd, int flags, void* context) {
    (void)flags;
    (void)context;
    char byte;
    (void)read(fd, &byte, 1);
    struct timespec t;
    clock_gettime(CLOCK_REALTIME, &t);
    accrued = corr_rate = 0;
    REF_SetReference(1, LEAP_Normal, 1, 1, &address, &t, offset, offset_sd, residual_frequency,
                     frequency_sd, skew, .002, .000001);
    RPT_TrackingReport report = {0};
    REF_GetTrackingReport(&report);
    printf("%u %.15g %.15g %.15g %.15g %.15g\n", ++number, frequency, accrued, corr_rate,
           REF_GetSkew(), report.last_update_interval);
    if (next()) {
        raw_now = when;
        (void)write(wake[1], "x", 1);
    } else
        SCH_QuitProgram();
}
int main(int argc, char** argv) {
    LOG_Initialise();
    LOG_SetMinSeverity(LOGS_FATAL);
    CNF_Initialise(0, 0);
    char precision[] = "clockprecision 0.000001";
    char drift[] = "maxdrift 100";
    CNF_ParseLine(NULL, 0, precision);
    CNF_ParseLine(NULL, 0, drift);
    LCL_Initialise();
    if (argc == 4 && !strcmp(argv[1], "slew")) {
        SCH_Initialise();
        SYS_Generic_CompleteFreqDriver(100000, 0, read_frequency, set_frequency, step, 0, 0, NULL,
                                       NULL, NULL, NULL);
        LCL_AccumulateOffset(atof(argv[2]), atof(argv[3]));
        printf("%.15g\n", frequency);
        return 0;
    }
    if (argc != 1)
        return 2;
    lcl_RegisterSystemDrivers(read_frequency, set_frequency, accrue, step, correction, NULL, NULL);
    SCH_Initialise();
    REF_Initialise();
    address.family = IPADDR_INET4;
    address.addr.in4 = 0xc0000201;
    if (pipe(wake))
        return 3;
    SCH_AddFileHandler(wake[0], SCH_FILE_INPUT, event, NULL);
    if (next()) {
        raw_now = when;
        (void)write(wake[1], "x", 1);
        SCH_MainLoop();
    }
    return 0;
}

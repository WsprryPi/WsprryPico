// SPDX-License-Identifier: MIT
// SRC/SST isolation: replace only the reference-output sink, not source rules.
// The separately linked source-selection/statistics objects are unmodified.
#include "chrony49_selection.c"

void REF_Initialise(void) {}
void REF_Finalise(void) {}
REF_Mode REF_GetMode(void) {
    return REF_ModeNormal;
}
int REF_GetOrphanStratum(void) {
    return 16;
}
int REF_GetOurStratum(void) {
    return 16;
}
double REF_GetSkew(void) {
    return .002;
}
REF_LeapMode REF_GetLeapMode(void) {
    return REF_LeapModeIgnore;
}
void REF_SetMode(REF_Mode mode) {
    (void)mode;
    abort();
}
void REF_SetModeEndHandler(REF_ModeEndHandler handler) {
    (void)handler;
    abort();
}
void REF_SetUnsynchronised(void) {}
void REF_UpdateLeapStatus(NTP_Leap leap_status) {
    (void)leap_status;
}
int REF_IsLeapSecondClose(struct timespec* ts, double offset_value) {
    (void)ts;
    (void)offset_value;
    return 0;
}
void REF_GetReferenceParams(struct timespec* local_time, int* synchronised, NTP_Leap* leap_status,
                            int* source_stratum, uint32_t* ref_id, struct timespec* ref_time,
                            double* root_delay, double* root_dispersion) {
    (void)local_time;
    (void)synchronised;
    (void)leap_status;
    (void)source_stratum;
    (void)ref_id;
    (void)ref_time;
    (void)root_delay;
    (void)root_dispersion;
    abort();
}
void REF_SetReference(int source_stratum, NTP_Leap leap_status, int combined, uint32_t ref_id,
                      IPAddr* ref_ip, struct timespec* ref_time, double average, double sd,
                      double frequency, double frequency_sd, double skew, double root_delay,
                      double root_dispersion) {
    (void)source_stratum;
    (void)leap_status;
    (void)ref_ip;
    printf("C %u %d %u %.12f %.15g %.15g %.15g %.15g %.15g %.15g %.15g", id + 1, combined, ref_id,
           ref_time->tv_sec + ref_time->tv_nsec / 1e9, average, sd, frequency, frequency_sd, skew,
           root_delay, root_dispersion);
    for (int i = 0; i < 4; ++i) {
        SST_Stats stats = SRC_GetSourcestats(sources[i]);
        if (!SST_Samples(stats)) {
            printf(" 0 0 0 0 0 0 0 0 0 0");
            continue;
        }
        struct timespec ref;
        double a, s, f, fs, k, d, p, lo, hi, distance, variance, first, last;
        SST_GetTrackingData(stats, &ref, &a, &s, &f, &fs, &k, &d, &p);
        struct timespec now;
        clock_gettime(CLOCK_REALTIME, &now);
        SST_GetSelectionData(stats, &now, &lo, &hi, &distance, &variance, &first, &last);
        printf(" %.12f %.15g %.15g %.15g %.15g %.15g %.15g %.15g %.15g %.15g",
               ref.tv_sec + ref.tv_nsec / 1e9, a, s, f, fs, k, d, p, distance, variance);
    }
    puts("");
}

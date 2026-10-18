/* Original private API harness. External Chrony reference only. */
#include "conf.h"
#include "config.h"
#include "local.h"
#include "localp.h"
#include "logging.h"
#include "ntp_sources.h"
#include "reference.h"
#include "sched.h"
#include "sources.h"
#include "sysincl.h"
static double fake = 1800000000, freq = 0;
int clock_gettime(clockid_t c, struct timespec* t) {
    (void)c;
    t->tv_sec = (time_t)fake;
    t->tv_nsec = (long)((fake - t->tv_sec) * 1e9);
    return 0;
}
static double rd(void) {
    return freq;
}
static double sf(double x) {
    return freq = x;
}
static void ac(double x, double r) {
    (void)x;
    (void)r;
}
static int st(double x) {
    (void)x;
    return 0;
}
static void co(struct timespec* t, double* c, double* e) {
    (void)t;
    *c = 0;
    if (e)
        *e = 0;
}
static int descriptors[2], slot, stratum, leap, reachable;
static double when, offset, delay, dispersion;
static unsigned id = 0;
static SRC_Instance sources[4];
static IPAddr ip[4];
static int next(void) {
    return scanf("%d %lf %lf %lf %lf %d %d %d", &slot, &when, &offset, &delay, &dispersion,
                 &stratum, &leap, &reachable) == 8;
}
static void update(int fd, int event, void* unused) {
    (void)event;
    (void)unused;
    char b;
    read(fd, &b, 1);
    struct timespec t;
    clock_gettime(CLOCK_REALTIME, &t);
    SRC_UpdateStatus(sources[slot], stratum, (NTP_Leap)leap);
    SRC_UpdateReachability(sources[slot], reachable);
    if (reachable) {
        NTP_Sample s = {0};
        s.time = t;
        s.offset = offset;
        s.peer_delay = s.root_delay = delay;
        s.peer_dispersion = .000001;
        s.root_dispersion = dispersion;
        SRC_AccumulateSample(sources[slot], &s);
    }
    SRC_SelectSource(sources[slot]);
    printf("%u", ++id);
    for (int i = 0; i < 4; i++) {
        RPT_SelectReport r = {0};
        SRC_GetSelectReport(i, &r);
        printf(" %c %.12g %.9g %.9g", r.state_char, r.score, r.lo_limit, r.hi_limit);
    }
    puts("");
    if (next()) {
        fake = when;
        write(descriptors[1], "x", 1);
    } else
        SCH_QuitProgram();
}
int main(void) {
    LOG_Initialise();
    LOG_SetMinSeverity(LOGS_FATAL);
    CNF_Initialise(0, 0);
    char precision[] = "clockprecision 0.000001";
    CNF_ParseLine(0, 0, precision);
    if (getenv("RULE")) {
        char* rule = strdup(getenv("RULE"));
        CNF_ParseLine(0, 0, rule);
        free(rule);
    }
    LCL_Initialise();
    lcl_RegisterSystemDrivers(rd, sf, ac, st, co, 0, 0);
    SCH_Initialise();
    SST_Initialise();
    REF_Initialise();
    SRC_Initialise();
    NSR_Initialise();
    for (int i = 0; i < 4; i++) {
        ip[i].family = IPADDR_INET4;
        ip[i].addr.in4 = 0xc0000201 + i;
        sources[i] = SRC_CreateNewInstance(i + 1, SRC_NTP, 0, 0, &ip[i], 6, 64, 0, 1, 0);
        SRC_SetActive(sources[i]);
    }
    pipe(descriptors);
    SCH_AddFileHandler(descriptors[0], SCH_FILE_INPUT, update, 0);
    if (next()) {
        fake = when;
        write(descriptors[1], "x", 1);
        SCH_MainLoop();
    }
    return 0;
}

// SPDX-License-Identifier: MIT
// Original offline IO/clock adapters for unmodified external Chrony NCR/SST.
// No upstream implementation is included or replaced at the admission boundary.
#include "clientlog.h"
#include "cmdparse.h"
#include "conf.h"
#include "keys.h"
#include "local.h"
#include "localp.h"
#include "logging.h"
#include "ntp_core.h"
#include "ntp_io.h"
#include "ntp_sources.h"
#include "reference.h"
#include "sched.h"
#include "sysincl.h"

#include <inttypes.h>

static uint64_t raw_ns;
static struct timespec current;
static NTP_Packet request_packet;
static int request_length, sends;
static NCR_Instance instance;
struct Timer {
    SCH_TimeoutHandler handler;
    void* argument;
    int client;
};
static struct Timer timers[256];
static unsigned next_timer;
// Deterministic test entropy affects only request correlation nonces. Never
// reuse this adapter in a networked application or firmware.
void arc4random_buf(void* data, size_t length) {
    static uint64_t value = 0x51d3928a76e5b401ULL;
    unsigned char* bytes = data;
    for (size_t i = 0; i < length; ++i) {
        value ^= value << 13;
        value ^= value >> 7;
        value ^= value << 17;
        bytes[i] = value;
    }
}

static void fail(void) {
    exit(20);
}
static void set_time(uint64_t value) {
    if (value < raw_ns)
        fail();
    raw_ns = value;
    current.tv_sec = 1800000000 + value / 1000000000ULL;
    current.tv_nsec = value % 1000000000ULL;
}
int clock_gettime(clockid_t id, struct timespec* value) {
    *value = current;
    if (id != CLOCK_REALTIME)
        value->tv_sec -= 1800000000;
    return 0;
}
static double read_frequency(void) {
    return 0;
}
static double set_frequency(double value) {
    (void)value;
    fail();
    return 0;
}
static void accrue(double value, double rate) {
    (void)value;
    (void)rate;
    fail();
}
static int step(double value) {
    (void)value;
    fail();
    return 0;
}
static void correction(struct timespec* value, double* offset, double* error) {
    (void)value;
    *offset = 0;
    if (error)
        *error = 0;
}

void SCH_GetLastEventTime(struct timespec* cooked, double* error, struct timespec* raw) {
    if (cooked)
        *cooked = current;
    if (raw)
        *raw = current;
    if (error)
        *error = 0;
}
double SCH_GetLastEventMonoTime(void) {
    return raw_ns / 1e9;
}
static SCH_TimeoutID timer(SCH_TimeoutHandler handler, void* argument, int client) {
    for (unsigned count = 0; count < 256; ++count) {
        unsigned index = ++next_timer % 256;
        if (!timers[index].handler) {
            timers[index] = (struct Timer){handler, argument, client};
            return index + 1;
        }
    }
    fail();
    return 0;
}
SCH_TimeoutID SCH_AddTimeoutByDelay(double delay, SCH_TimeoutHandler handler, void* argument) {
    (void)delay;
    return timer(handler, argument, 0);
}
SCH_TimeoutID SCH_AddTimeoutInClass(double delay, double separation, double randomness,
                                    SCH_TimeoutClass class, SCH_TimeoutHandler handler,
                                    void* argument) {
    (void)delay;
    (void)separation;
    (void)randomness;
    return timer(handler, argument, class == SCH_NtpClientClass);
}
SCH_TimeoutID SCH_AddTimeout(struct timespec* at, SCH_TimeoutHandler handler, void* argument) {
    (void)at;
    return timer(handler, argument, 0);
}
void SCH_RemoveTimeout(SCH_TimeoutID id) {
    if (!id)
        return;
    if (id > 256)
        fail();
    timers[id - 1] = (struct Timer){0};
}
void SCH_AddFileHandler(int fd, int events, SCH_FileHandler handler, void* argument) {
    (void)fd;
    (void)events;
    (void)handler;
    (void)argument;
    fail();
}
void SCH_RemoveFileHandler(int fd) {
    (void)fd;
    fail();
}
void SCH_SetFileHandlerEvent(int fd, int event, int enable) {
    (void)fd;
    (void)event;
    (void)enable;
    fail();
}
void SCH_Initialise(void) {}
void SCH_Finalise(void) {}
void SCH_MainLoop(void) {
    fail();
}
void SCH_QuitProgram(void) {
    fail();
}

int NIO_IsHwTsEnabled(void) {
    return 0;
}
int NIO_OpenClientSocket(NTP_Remote_Address* remote) {
    (void)remote;
    return 101;
}
void NIO_CloseClientSocket(int fd) {
    if (fd != 101)
        fail();
}
int NIO_OpenServerSocket(NTP_Remote_Address* remote) {
    (void)remote;
    fail();
    return -1;
}
void NIO_CloseServerSocket(int fd) {
    (void)fd;
    fail();
}
int NIO_IsServerSocket(int fd) {
    (void)fd;
    return 0;
}
int NIO_IsServerSocketOpen(void) {
    return 0;
}
int NIO_IsServerConnectable(NTP_Remote_Address* remote) {
    (void)remote;
    return 1;
}
int NIO_SendPacket(NTP_Packet* packet, NTP_Remote_Address* remote, NTP_Local_Address* local,
                   int length, int process_tx) {
    (void)remote;
    (void)local;
    (void)process_tx;
    if (length != 48)
        fail();
    memcpy(&request_packet, packet, length);
    request_length = length;
    ++sends;
    return 1;
}

// Freeze only the output/controller boundary. Actual NCR validation, source
// statistics, delay tests and admission execute in unmodified upstream objects.
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
    fail();
}
void REF_SetModeEndHandler(REF_ModeEndHandler handler) {
    (void)handler;
    fail();
}
void REF_SetUnsynchronised(void) {}
void REF_UpdateLeapStatus(NTP_Leap leap) {
    (void)leap;
}
int REF_IsLeapSecondClose(struct timespec* at, double offset) {
    (void)at;
    (void)offset;
    return 0;
}
void REF_GetReferenceParams(struct timespec* now, int* sync, NTP_Leap* leap, int* stratum,
                            uint32_t* id, struct timespec* at, double* delay, double* dispersion) {
    (void)now;
    *sync = 0;
    *leap = LEAP_Unsynchronised;
    *stratum = 16;
    *id = 0;
    *at = current;
    *delay = *dispersion = 0;
}
void REF_SetReference(int stratum, NTP_Leap leap, int combined, uint32_t id, IPAddr* address,
                      struct timespec* at, double offset, double sd, double frequency,
                      double frequency_sd, double skew, double delay, double dispersion) {
    (void)stratum;
    (void)leap;
    (void)combined;
    (void)id;
    (void)address;
    (void)at;
    (void)offset;
    (void)sd;
    (void)frequency;
    (void)frequency_sd;
    (void)skew;
    (void)delay;
    (void)dispersion;
}
static void rule(const char* value) {
    char* text = strdup(value);
    CNF_ParseLine(NULL, 0, text);
    free(text);
}
static void send_request(void) {
    int previous = sends;
    for (unsigned i = 0; i < 256; ++i) {
        if (timers[i].handler && timers[i].client && timers[i].argument == instance) {
            struct Timer callback = timers[i];
            timers[i] = (struct Timer){0};
            callback.handler(callback.argument);
            if (sends != previous + 1)
                fail();
            return;
        }
    }
    fail();
}
int main(void) {
    LOG_Initialise();
    LOG_SetMinSeverity(LOGS_FATAL);
    CNF_Initialise(0, 0);
    rule("clockprecision 0.000001");
    rule("maxclockerror 50");
    rule("maxdrift 100");
    set_time(0);
    LCL_Initialise();
    lcl_RegisterSystemDrivers(read_frequency, set_frequency, accrue, step, correction, NULL, NULL);
    SST_Initialise();
    SRC_Initialise();
    NSR_Initialise();
    NCR_Initialise();
    KEY_Initialise();
    CLG_Initialise();
    CPS_NTP_Source source;
    char options[] = "192.0.2.1 minpoll 6 maxpoll 6 minsamples 6 maxsamples 64 maxunreach 0";
    if (CPS_ParseNTPSourceAdd(options, &source) != CPS_Success)
        fail();
    NTP_Remote_Address remote = {0};
    remote.ip_addr.family = IPADDR_INET4;
    remote.ip_addr.addr.in4 = 0xc0000201;
    remote.port = 123;
    instance = NCR_CreateInstance(&remote, NTP_SERVER, &source.params, NULL);
    NCR_StartInstance(instance);
    uint64_t send, receive, mask;
    uint64_t previous_send = UINT64_MAX;
    char hex[2049];
    unsigned row = 0;
    while (scanf("%" SCNu64 " %" SCNu64 " %" SCNx64 " %2048s", &send, &receive, &mask, hex) == 4) {
        const int lost = strcmp(hex, "-") == 0;
        if (receive < send || (!lost && strlen(hex) % 2) || strlen(hex) > 2 * sizeof(NTP_Packet))
            fail();
        if (send != previous_send) {
            set_time(send);
            send_request();
            previous_send = send;
        }
        if (lost) {
            printf("%u %" PRIu64 " %" PRIu64 " ", ++row, send, receive);
            for (unsigned i = 0; i < 8; ++i)
                printf("%02x", ((unsigned char*)&request_packet)[40 + i]);
            puts(" - 0 0 0 0");
            continue;
        }
        NTP_Packet packet = {0};
        unsigned length = strlen(hex) / 2;
        for (unsigned i = 0; i < length; ++i) {
            unsigned value;
            if (sscanf(hex + 2 * i, "%2x", &value) != 1)
                fail();
            ((unsigned char*)&packet)[i] = value;
        }
        if (length >= 32) {
            memcpy((unsigned char*)&packet + 24, (unsigned char*)&request_packet + 40, 8);
            for (unsigned i = 0; i < 8; ++i)
                ((unsigned char*)&packet)[24 + i] ^= (mask >> ((7 - i) * 8)) & 255;
        }
        set_time(receive);
        NTP_Local_Address local = {0};
        local.ip_addr.family = IPADDR_UNSPEC;
        local.if_index = INVALID_IF_INDEX;
        local.sock_fd = 101;
        NTP_Local_Timestamp received = {0};
        received.ts = current;
        received.source = NTP_TS_DAEMON;
        RPT_NTPReport previous = {0}, report = {0};
        NCR_GetNTPReport(instance, &previous);
        const int valid = NCR_ProcessRxKnown(instance, &local, &received, &packet, length);
        NCR_GetNTPReport(instance, &report);
        printf("%u %" PRIu64 " %" PRIu64 " ", ++row, send, receive);
        for (unsigned i = 0; i < 8; ++i)
            printf("%02x", ((unsigned char*)&request_packet)[40 + i]);
        putchar(' ');
        for (unsigned i = 0; i < length; ++i)
            printf("%02x", ((unsigned char*)&packet)[i]);
        printf(" %d %u %u %u\n", valid, report.total_valid_count - previous.total_valid_count,
               report.total_good_count - previous.total_good_count, report.tests);
    }
    return 0;
}

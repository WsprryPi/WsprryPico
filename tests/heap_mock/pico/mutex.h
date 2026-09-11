#pragma once
#include <pthread.h>
typedef pthread_mutex_t recursive_mutex_t;
#define auto_init_recursive_mutex(name)                                                            \
    static recursive_mutex_t name;                                                                 \
    static void __attribute__((constructor)) init_##name(void) {                                   \
        pthread_mutexattr_t attr;                                                                  \
        pthread_mutexattr_init(&attr);                                                             \
        pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);                                 \
        pthread_mutex_init(&name, &attr);                                                          \
        pthread_mutexattr_destroy(&attr);                                                          \
    }
static inline void recursive_mutex_enter_blocking(recursive_mutex_t* m) {
    pthread_mutex_lock(m);
}
static inline void recursive_mutex_exit(recursive_mutex_t* m) {
    pthread_mutex_unlock(m);
}

#pragma once
#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif
typedef struct {
    uint32_t bottom;
    uint32_t limit;
    uint32_t sp;
    uint32_t control;
    uint32_t fault_status;
    bool valid;
} wsprry_stack_guard;
wsprry_stack_guard wsprry_stack_guard_snapshot(void);
#ifdef __cplusplus
}
#endif

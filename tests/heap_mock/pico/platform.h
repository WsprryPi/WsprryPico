#pragma once
extern _Thread_local unsigned test_core_num;
static inline unsigned get_core_num(void) {
    return test_core_num;
}

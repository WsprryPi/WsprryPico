set(WSPRRY_PICO_FIRMWARE_VERSION "0.0.0-devel" CACHE STRING "Firmware identity")

execute_process(
    COMMAND git -C "${CMAKE_CURRENT_LIST_DIR}/.." rev-parse --short=12 HEAD
    OUTPUT_VARIABLE WSPRRY_PICO_GIT_REVISION
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE WSPRRY_PICO_GIT_RESULT
)
if(NOT WSPRRY_PICO_GIT_RESULT EQUAL 0)
    set(WSPRRY_PICO_GIT_REVISION "unknown")
endif()
execute_process(
    COMMAND git -C "${CMAKE_CURRENT_LIST_DIR}/.." diff --quiet --ignore-submodules HEAD --
    RESULT_VARIABLE WSPRRY_PICO_GIT_DIRTY
)
if(WSPRRY_PICO_GIT_DIRTY EQUAL 1)
    string(APPEND WSPRRY_PICO_GIT_REVISION "-dirty")
elseif(NOT WSPRRY_PICO_GIT_DIRTY EQUAL 0)
    string(APPEND WSPRRY_PICO_GIT_REVISION "-unknown")
endif()

configure_file(
    ${CMAKE_CURRENT_LIST_DIR}/firmware_identity.hpp.in
    ${CMAKE_CURRENT_BINARY_DIR}/generated/firmware_identity.hpp
    @ONLY
)

add_executable(WsprryPico
    main.cpp
    pico_adapters.cpp
    usb_descriptors.c
    ../src/usb/transport.cpp
)
target_include_directories(WsprryPico PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMAKE_CURRENT_BINARY_DIR}/generated
)
target_compile_definitions(WsprryPico PRIVATE
    PICO_NO_BI_PROGRAM_BUILD_DATE=1
    PICO_STACK_SIZE=0x4000
    WSPRRY_PICO_RF_OUTPUT_DISABLED=1
)
set_source_files_properties(main.cpp pico_adapters.cpp usb_descriptors.c ../src/usb/transport.cpp PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror"
)
target_link_libraries(WsprryPico PRIVATE
    wsprrypico_core
    pico_stdlib
    pico_rand
    pico_time
    pico_unique_id
    tinyusb_device
)

# Reserve 16 KiB at the top of RP2350 main SRAM for the primary stack.
# SDK linker symbols relocate SCRATCH_Y without overlapping the heap or core 1.
# Recursive depth-16 JSON validation exceeds the default 2 KiB scratch stack.
target_link_options(WsprryPico PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x7c000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000"
)

pico_enable_stdio_uart(WsprryPico 0)
pico_enable_stdio_usb(WsprryPico 0)

pico_set_program_name(WsprryPico "WsprryPico")
pico_set_program_version(WsprryPico "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico "RF-inhibited foundation ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico)

# Explicit diagnostic target: no WTP endpoint or UTC claim; boots without a job.
add_executable(WsprryPico-RFBench EXCLUDE_FROM_ALL
    ../src/rf/pico/bench_main.cpp usb_descriptors.c ../src/usb/transport.cpp)
target_include_directories(WsprryPico-RFBench PRIVATE
    ${CMAKE_CURRENT_LIST_DIR} ${CMAKE_CURRENT_BINARY_DIR}/generated)
target_compile_definitions(WsprryPico-RFBench PRIVATE
    WSPRRY_PICO_RF_BENCH=1 PICO_NO_BI_PROGRAM_BUILD_DATE=1 PICO_STACK_SIZE=0x4000)
target_link_libraries(WsprryPico-RFBench PRIVATE
    wsprrypico_pico_rf pico_unique_id tinyusb_device)
set_source_files_properties(../src/rf/pico/bench_main.cpp PROPERTIES
    COMPILE_OPTIONS "-Wall;-Wextra;-Werror;-fstack-usage")
set_target_properties(WsprryPico-RFBench PROPERTIES
    C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS ON)
target_link_options(WsprryPico-RFBench PRIVATE
    "LINKER:--defsym=RAM_LENGTH=0x7c000"
    "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
    "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000")
pico_enable_stdio_uart(WsprryPico-RFBench 0)
pico_enable_stdio_usb(WsprryPico-RFBench 0)
pico_set_program_name(WsprryPico-RFBench "WsprryPico-RFBench")
pico_set_program_version(WsprryPico-RFBench "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico-RFBench "GP2 bench ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico-RFBench)

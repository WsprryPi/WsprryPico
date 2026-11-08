cmake_minimum_required(VERSION 3.24)
set(PICO_BOARD pico2_w CACHE STRING "Target board")
include("${CMAKE_CURRENT_LIST_DIR}/../../../cmake/pico_sdk_import.cmake")
project(Si5351Truth LANGUAGES C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT PICO_BOARD STREQUAL "pico2_w")
 message(FATAL_ERROR "This diagnostic targets Pico 2 W only")
endif()
pico_sdk_init()
if(NOT PICO_NO_FLASH OR NOT PICO_SDK_VERSION_STRING STREQUAL "2.3.1" OR NOT CMAKE_CXX_COMPILER_VERSION VERSION_EQUAL "15.3.1")
 message(FATAL_ERROR "Requires RAM-only, SDK 2.3.1 and GNU 15.3.1")
endif()
set(TRUTH_INPUT_GP 7 CACHE STRING "Input-only clock GPIO")
set(TRUTH_PPS_GP 3 CACHE STRING "Input-only PPS GPIO")
option(TRUTH_EXTERNAL_REFERENCE "Observe external known-ratio inputs without Si5351 writes" OFF)
if(TRUTH_EXTERNAL_REFERENCE AND (NOT TRUTH_INPUT_GP STREQUAL "9" OR NOT TRUTH_PPS_GP STREQUAL "11"))
 message(FATAL_ERROR "External diagnostic requires explicitly selected GP9 clock / GP11 PPS")
endif()
if(NOT TRUTH_EXTERNAL_REFERENCE AND (NOT TRUTH_INPUT_GP STREQUAL "7" OR NOT TRUTH_PPS_GP STREQUAL "3"))
 message(FATAL_ERROR "Si5351 diagnostic requires existing GP7 clock / GP3 PPS")
endif()
add_executable(Si5351Truth main.cpp)
target_compile_definitions(Si5351Truth PRIVATE PICO_STACK_SIZE=0x4000 PICO_CORE1_STACK_SIZE=0x2000 TRUTH_INPUT_GP=${TRUTH_INPUT_GP} TRUTH_PPS_GP=${TRUTH_PPS_GP} TRUTH_EXTERNAL_REFERENCE=$<BOOL:${TRUTH_EXTERNAL_REFERENCE}>)
# Keep the production validators/status formatter off the SDK's 2 KiB defaults.
# SDK 2.3.1 exposes these region symbols; reserve nonoverlapping 8/16 KiB
# stacks at the top of main SRAM, with the heap ending below both regions.
target_link_options(Si5351Truth PRIVATE
 "LINKER:--defsym=RAM_LENGTH=0x7a000"
 "LINKER:--defsym=SCRATCH_X_ORIGIN=0x2007a000"
 "LINKER:--defsym=SCRATCH_X_LENGTH=0x2000"
 "LINKER:--defsym=SCRATCH_Y_ORIGIN=0x2007c000"
 "LINKER:--defsym=SCRATCH_Y_LENGTH=0x4000")
target_link_libraries(Si5351Truth PRIVATE pico_stdlib pico_unique_id hardware_uart hardware_clocks hardware_i2c hardware_pwm)
pico_enable_stdio_uart(Si5351Truth 0)
pico_enable_stdio_usb(Si5351Truth 1)
pico_add_extra_outputs(Si5351Truth)

option(TRUTH_PRODUCTION_CAPTURE "Compare production capture with independent electrical-edge brackets" OFF)
target_compile_definitions(Si5351Truth PRIVATE TRUTH_PRODUCTION_CAPTURE=$<BOOL:${TRUTH_PRODUCTION_CAPTURE}>)
if(TRUTH_PRODUCTION_CAPTURE)
 set(OWNED "${CMAKE_CURRENT_LIST_DIR}/../../../src")
 target_sources(Si5351Truth PRIVATE
  ${OWNED}/time/pico/gps_input.cpp ${OWNED}/rf/pico/reference_capture.cpp
  ${OWNED}/time/gps.cpp ${OWNED}/time/gps_calibration.cpp
  ${OWNED}/hardware/gps_settings.cpp ${OWNED}/hardware/pins.cpp
  ${OWNED}/hardware/si5351_settings.cpp ${OWNED}/hardware/filter_settings.cpp
  ${OWNED}/rf/si5351_plan.cpp ${OWNED}/rf/reference_counter.cpp
  ${OWNED}/rf/reference_measurement.cpp ${OWNED}/wtp/json.cpp)
 target_include_directories(Si5351Truth PRIVATE ${OWNED})
 target_link_libraries(Si5351Truth PRIVATE pico_multicore hardware_irq hardware_ticks)
endif()

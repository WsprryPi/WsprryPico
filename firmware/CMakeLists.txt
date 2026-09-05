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

pico_enable_stdio_uart(WsprryPico 0)
pico_enable_stdio_usb(WsprryPico 0)

pico_set_program_name(WsprryPico "WsprryPico")
pico_set_program_version(WsprryPico "${WSPRRY_PICO_FIRMWARE_VERSION}")
pico_set_program_description(WsprryPico "RF-inhibited foundation ${WSPRRY_PICO_GIT_REVISION}")
pico_add_extra_outputs(WsprryPico)

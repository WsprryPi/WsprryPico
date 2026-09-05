cmake_minimum_required(VERSION 3.24)

option(WSPRRY_PICO_BUILD_FIRMWARE "Build Pico 2 W firmware" OFF)

if(WSPRRY_PICO_BUILD_FIRMWARE)
    set(PICO_BOARD pico2_w CACHE STRING "Pico SDK board" FORCE)
    include(cmake/pico_sdk_import.cmake)
    project(WsprryPico LANGUAGES C CXX ASM)
else()
    project(WsprryPico LANGUAGES CXX)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(WSPRRY_PICO_BUILD_TESTS "Build hardware-free host tests" ON)

if(WSPRRY_PICO_BUILD_FIRMWARE)
    if(WSPRRY_PICO_BUILD_TESTS)
        message(FATAL_ERROR "Host tests and Pico firmware require separate build directories")
    endif()
    set(PICOTOOL_GIT_BRANCH "6f6458d792b93685a11423b244a585eaa99eafcf" CACHE STRING
        "Pinned picotool revision" FORCE)
    set(PICOTOOL_FORCE_FETCH_FROM_GIT ON CACHE BOOL
        "Use the repository-pinned picotool source" FORCE)
    pico_sdk_init()
    include(cmake/verify_pico_dependencies.cmake)
endif()

add_library(wsprrypico_core
    src/wtp/json.cpp
    src/wtp/codec.cpp
    src/wtp/endpoint.cpp
    src/wtp/frame_parser.cpp
    src/wtp/inhibited_rf_engine.cpp
    src/wtp/job_service.cpp
    src/wtp/sha256.cpp
)
target_include_directories(wsprrypico_core PUBLIC src)
target_compile_features(wsprrypico_core PUBLIC cxx_std_20)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(wsprrypico_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    target_compile_options(wsprrypico_core PRIVATE
        -fstack-usage
        -fno-exceptions
        -fno-rtti
        -fno-unwind-tables
        -fno-use-cxa-atexit
    )
endif()

if(WSPRRY_PICO_BUILD_TESTS)
    enable_testing()
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    add_executable(wsprrypico_core_tests tests/core_tests.cpp)
    target_link_libraries(wsprrypico_core_tests PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(wsprrypico_core_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_executable(endpoint_driver tests/endpoint_driver.cpp)
    target_link_libraries(endpoint_driver PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(endpoint_driver PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_test(NAME rf_feasibility_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/rf_feasibility_tests.py)
    add_test(NAME wtp_probe_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/wtp_probe_tests.py)
    add_test(NAME endpoint_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/endpoint_tests.py $<TARGET_FILE:endpoint_driver>)
    add_executable(usb_transport_tests tests/usb_transport_tests.cpp src/usb/transport.cpp)
    target_include_directories(usb_transport_tests PRIVATE tests/usb_mock)
    target_link_libraries(usb_transport_tests PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(usb_transport_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_test(NAME usb_transport_tests COMMAND usb_transport_tests)
    set(WSPRRY_PICO_TEST_TINYUSB_PATH "" CACHE PATH "Optional local TinyUSB source for descriptor tests")
    if(WSPRRY_PICO_TEST_TINYUSB_PATH)
        enable_language(C)
        add_executable(usb_descriptor_tests tests/usb_descriptor_tests.c firmware/usb_descriptors.c)
        set_target_properties(usb_descriptor_tests PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON C_EXTENSIONS OFF)
        target_include_directories(usb_descriptor_tests PRIVATE
            tests/descriptor_mock firmware src "${WSPRRY_PICO_TEST_TINYUSB_PATH}/src")
        target_compile_definitions(usb_descriptor_tests PRIVATE CFG_TUSB_MCU=OPT_MCU_NONE TUP_DCD_ENDPOINT_MAX=16)
        # Assertions are the test checks, including in Release builds.
        if(MSVC)
            target_compile_options(usb_descriptor_tests PRIVATE /UNDEBUG)
        else()
            target_compile_options(usb_descriptor_tests PRIVATE -UNDEBUG)
        endif()
        add_test(NAME usb_descriptor_tests COMMAND usb_descriptor_tests)
    endif()
    add_test(NAME wsprrypico_core_tests COMMAND wsprrypico_core_tests)
    add_test(NAME wtp_monitor_tests COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/wtp_monitor_tests.py)
endif()

if(WSPRRY_PICO_BUILD_FIRMWARE)
    add_subdirectory(firmware)
endif()

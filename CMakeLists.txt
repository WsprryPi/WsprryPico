cmake_minimum_required(VERSION 3.24)

project(WsprryPico LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(WSPRRY_PICO_BUILD_TESTS "Build hardware-free host tests" ON)

add_library(wsprrypico_core
    src/wtp/frame_parser.cpp
    src/wtp/job_service.cpp
    src/wtp/sha256.cpp
)
target_include_directories(wsprrypico_core PUBLIC src)
target_compile_features(wsprrypico_core PUBLIC cxx_std_20)

if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(wsprrypico_core PRIVATE -Wall -Wextra -Wpedantic -Werror)
endif()

if(WSPRRY_PICO_BUILD_TESTS)
    enable_testing()
    add_executable(wsprrypico_core_tests tests/core_tests.cpp)
    target_link_libraries(wsprrypico_core_tests PRIVATE wsprrypico_core)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(wsprrypico_core_tests PRIVATE -Wall -Wextra -Wpedantic -Werror)
    endif()
    add_test(NAME wsprrypico_core_tests COMMAND wsprrypico_core_tests)
endif()

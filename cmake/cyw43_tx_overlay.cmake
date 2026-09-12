# Compile a verified generated copy; never change the external pinned driver.
function(wsprry_cyw43_tx_overlay)
    set(output "${CMAKE_BINARY_DIR}/cyw43-tx-overlay")
    execute_process(COMMAND ${Python3_EXECUTABLE}
        "${CMAKE_SOURCE_DIR}/scripts/prepare_cyw43_tx_overlay.py"
        "${PICO_CYW43_DRIVER_PATH}" "${output}" COMMAND_ERROR_IS_FATAL ANY)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        "${CMAKE_SOURCE_DIR}/scripts/prepare_cyw43_tx_overlay.py"
        "${PICO_CYW43_DRIVER_PATH}/src/cyw43_ll.c")
    get_target_property(sources cyw43_driver INTERFACE_SOURCES)
    set(matches 0)
    set(updated)
    foreach(item IN LISTS sources)
        if(item STREQUAL "${PICO_CYW43_DRIVER_PATH}/src/cyw43_ll.c")
            list(APPEND updated "${output}/cyw43_ll.c")
            math(EXPR matches "${matches}+1")
        else()
            list(APPEND updated "${item}")
        endif()
    endforeach()
    if(NOT matches EQUAL 1)
        message(FATAL_ERROR "Expected exactly one pinned CYW43 low-level source")
    endif()
    set_property(TARGET cyw43_driver PROPERTY INTERFACE_SOURCES "${updated}")
    target_compile_definitions(cyw43_driver INTERFACE WSPRRY_PICO_CYW43_TX_GUARD=1)
    set_source_files_properties("${output}/cyw43_ll.c" PROPERTIES COMPILE_OPTIONS "-fstack-usage")
endfunction()

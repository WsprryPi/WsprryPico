# Preserve the clean SDK pin; compile hash-checked generated copies of three files.
function(wsprry_mbedtls_alert_overlay target property source)
    # Also used by the companion's read-only, pinned Pico-server build.
    get_filename_component(pico_source "${CMAKE_CURRENT_FUNCTION_LIST_DIR}/.." ABSOLUTE)
    set(output "${CMAKE_BINARY_DIR}/mbedtls-alert-overlay")
    execute_process(COMMAND ${Python3_EXECUTABLE}
        "${pico_source}/scripts/prepare_mbedtls_alert_overlay.py" "${source}" "${output}"
        COMMAND_ERROR_IS_FATAL ANY)
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
        "${pico_source}/scripts/prepare_mbedtls_alert_overlay.py"
        "${source}/library/ssl_msg.c" "${source}/library/ssl_tls13_generic.c"
        "${source}/library/ssl_tls.c")
    get_target_property(sources ${target} ${property})
    foreach(name ssl_msg.c ssl_tls13_generic.c ssl_tls.c)
        set(matches 0)
        set(updated)
        foreach(item IN LISTS sources)
            get_filename_component(base "${item}" NAME)
            if(base STREQUAL name)
                list(APPEND updated "${output}/${name}")
                math(EXPR matches "${matches}+1")
            else()
                list(APPEND updated "${item}")
            endif()
        endforeach()
        if(NOT matches EQUAL 1)
            message(FATAL_ERROR "Expected one ${name} in ${target}, found ${matches}")
        endif()
        set(sources ${updated})
    endforeach()
    set_property(TARGET ${target} PROPERTY ${property} "${sources}")
    # Copied upstream translation units retain their private header dependencies.
    if(property STREQUAL "INTERFACE_SOURCES")
        target_include_directories(${target} SYSTEM INTERFACE "${source}/library")
    else()
        target_include_directories(${target} SYSTEM PRIVATE "${source}/library")
    endif()
endfunction()

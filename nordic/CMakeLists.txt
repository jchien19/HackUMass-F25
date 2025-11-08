cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(l4_e1_sol)

FILE(GLOB app_sources src/*.c)
target_sources(app PRIVATE ${app_sources})

zephyr_append_cmake_arguments(DTC_OVERLAY_FILE ${CMAKE_CURRENT_SOURCE_DIR}/boards/nrf52dk_nrf52832.overlay)
zephyr_syscall_include_directories(${CMAKE_CURRENT_SOURCE_DIR}/dts/bindings)
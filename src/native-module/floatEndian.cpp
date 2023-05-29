#include "floatEndian.hpp"

#include <endian.h>
#include <stdint.h>

// TODO: This hack relies on undefined behavior. It should be replaced

//this function written by user "synthetix" on cboard.cprogramming.com
float float_swap_betoh(float value) {
    union v {
        float f;
        uint32_t i;
    };

    union v val;

    val.f = value;
    val.i = be32toh(val.i);

    return val.f;
}

float float_swap_letoh(float value) {
    union v {
        float f;
        uint32_t i;
    };

    union v val;

    val.f = value;
    val.i = le32toh(val.i);

    return val.f;
}

float float_tobe(float value) {
    union v {
        float f;
        uint32_t i;
    };

    union v val;

    val.f = value;
    val.i = htobe32(val.i);

    return val.f;
}
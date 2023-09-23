#ifndef FLOAT_ENDIAN_H
#define FLOAT_ENDIAN_H

/**
 * @brief Converts a float from network order to system order
 */
float float_swap_betoh(float value);

/**
 * @brief Converts a float from little endian to system order
 */
float float_swap_letoh(float value);

/**
 * @brief Converts a float from system order to network order
 */
float float_tobe(float value);

#endif
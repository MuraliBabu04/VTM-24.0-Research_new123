// Exact correction for the fixed-point NMF experiment. No intermediate rounding.
#ifndef __NMF_EXACT_CORRECTION_H__
#define __NMF_EXACT_CORRECTION_H__

#include "NmfMtsFactors.h"
#include "TypeDef.h"
#include <cstdint>

template<size_t N>
struct NmfExactCorrection
{
  int64_t coefficient[N][N] = {};
  size_t nonzero = 0;
};

template<size_t N, size_t R>
NmfExactCorrection<N> makeNmfExactCorrection(const int32_t (&pw)[N][R], const int32_t (&ph)[R][N],
                                            const int32_t (&nw)[N][R], const int32_t (&nh)[R][N],
                                            const TMatrixCoeff *matrix)
{
  NmfExactCorrection<N> result;
  const int64_t factorScale = int64_t(1) << (2 * NMF_FACTOR_FRACTIONAL_BITS);
  for (size_t j = 0; j < N; ++j)
    for (size_t k = 0; k < N; ++k)
    {
      int64_t approximation = 0;
      for (size_t r = 0; r < R; ++r)
        approximation += int64_t(pw[j][r]) * ph[r][k] - int64_t(nw[j][r]) * nh[r][k];
      // Use the compiled normative forward matrix, including its precision.
      // Multiplication avoids a left shift of negative signed matrix entries.
      result.coefficient[j][k] = int64_t(matrix[j * N + k]) * factorScale - approximation;
      result.nonzero += result.coefficient[j][k] != 0;
    }
  return result;
}

#endif

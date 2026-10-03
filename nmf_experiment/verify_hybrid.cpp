#include "CommonLib/TrQuant_EMT.h"
#include "CommonLib/NmfMtsFactors.h"
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

using Transform = void (*)(const TCoeff *, TCoeff *, int, int, int, int);

// Independent dense reconstruction checks the factored execution, scaling,
// signed inputs, output layout and skipped lines. It is not an RD quality test.
template<size_t N, size_t R>
void checkNmf(Transform transform, const int32_t (&pw)[N][R], const int32_t (&ph)[R][N],
              const int32_t (&nw)[N][R], const int32_t (&nh)[R][N])
{
  constexpr int lines = 5;
  int64_t matrix[N][N] = {};
  for (size_t j = 0; j < N; ++j)
    for (size_t k = 0; k < N; ++k)
      for (size_t r = 0; r < R; ++r)
        matrix[j][k] += int64_t(pw[j][r]) * ph[r][k] - int64_t(nw[j][r]) * nh[r][k];
  for (int shift : {7, 12, 17})
    for (int skip : {0, 2, lines})
      for (int cut : {0, int(N / 2)})
        for (int pattern = 0; pattern < 4; ++pattern)
        {
          std::vector<TCoeff> src(N * lines), got(N * lines, 123), expected(N * lines, 0);
          for (size_t k = 0; k < src.size(); ++k)
            src[k] = pattern == 0 ? 0 : pattern == 1 ? (k % 2 ? -1023 : 1023)
                   : pattern == 2 ? (int(k * 73 % 511) - 255) : (k % N == 0 ? 255 : 0);
          transform(src.data(), got.data(), shift, lines, skip, cut);
          const int totalShift = shift + 2 * NMF_FACTOR_FRACTIONAL_BITS - NMF_FORWARD_MATRIX_SCALE_BITS;
          for (int i = 0; i < lines - skip; ++i)
            for (size_t j = 0; j < N - cut; ++j)
            {
              int64_t sum = int64_t(1) << (totalShift - 1);
              for (size_t k = 0; k < N; ++k)
                sum += matrix[j][k] * src[i * N + k];
              expected[j * lines + i] = TCoeff(sum >> totalShift);
            }
          if (got != expected)
            throw std::runtime_error("NMF differs from dense fixed-point reference");
        }
}

void checkExact8(Transform hybrid, Transform exact)
{
  for (int shift : {7, 12, 17})
    for (int skip : {0, 2, 5})
      for (int cut : {0, 4})
        for (int pattern = 0; pattern < 4; ++pattern)
        {
          std::vector<TCoeff> src(40), got(40, 123), expected(40, 456);
          for (size_t k = 0; k < src.size(); ++k)
            src[k] = pattern == 0 ? 0 : pattern == 1 ? (k % 2 ? -1023 : 1023)
                   : pattern == 2 ? (int(k * 73 % 511) - 255) : (k % 8 == 0 ? 255 : 0);
          hybrid(src.data(), got.data(), shift, 5, skip, cut);
          exact(src.data(), expected.data(), shift, 5, skip, cut);
          if (got != expected)
            throw std::runtime_error("8-point hybrid is not bit-exact to VTM");
        }
}

int main()
{
  checkExact8(hybridForwardDCT8_B8, fastForwardDCT8_B8);
  checkExact8(hybridForwardDST7_B8, fastForwardDST7_B8);
  checkNmf(nmfForwardDCT8_B16, g_nmfDCT8P16PosW, g_nmfDCT8P16PosH, g_nmfDCT8P16NegW, g_nmfDCT8P16NegH);
  checkNmf(nmfForwardDST7_B16, g_nmfDST7P16PosW, g_nmfDST7P16PosH, g_nmfDST7P16NegW, g_nmfDST7P16NegH);
  checkNmf(nmfForwardDCT8_B32, g_nmfDCT8P32PosW, g_nmfDCT8P32PosH, g_nmfDCT8P32NegW, g_nmfDCT8P32NegH);
  checkNmf(nmfForwardDST7_B32, g_nmfDST7P32PosW, g_nmfDST7P32PosH, g_nmfDST7P32NegW, g_nmfDST7P32NegH);
  std::cout << "PASS: 432 transform cases; exact N8 and corrected NMF N16/N32\n";
}

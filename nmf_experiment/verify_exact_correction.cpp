#include "CommonLib/TrQuant_EMT.h"
#include "CommonLib/NmfExactCorrection.h"
#include "CommonLib/Rom.h"
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <random>
#include <stdexcept>
#include <vector>

using Transform = void (*)(const TCoeff *, TCoeff *, int, int, int, int);
static size_t cases = 0;

template<size_t N>
void checkKernel(Transform corrected, Transform normative, const TMatrixCoeff *matrix)
{
  constexpr int lines = 5;
  std::mt19937 random(1234 + N);
  for (int shift : {1, 7, 12, 17})
    for (int skip : {0, 2, lines})
      for (int cut : {0, int(N / 2), int(N)})
        for (int pattern = 0; pattern < 20; ++pattern)
        {
          std::vector<TCoeff> src(N * lines), got(N * lines, 123), ref(N * lines, 456), dense(N * lines, 0);
          for (size_t k = 0; k < src.size(); ++k)
            src[k] = pattern == 0 ? 0 : pattern == 1 ? (k % 2 ? -1023 : 1023)
                   : pattern == 2 ? (k % N == 0 ? 1023 : 0)
                   : pattern == 3 ? -32767 : pattern == 4 ? 32767
                   : TCoeff(int(random() % 65535) - 32767);
          corrected(src.data(), got.data(), shift, lines, skip, cut);
          normative(src.data(), ref.data(), shift, lines, skip, cut);
          for (int i = 0; i < lines - skip; ++i)
            for (size_t j = 0; j < N - cut; ++j)
            {
              int64_t sum = int64_t(1) << (shift - 1);
              for (size_t k = 0; k < N; ++k)
                sum += int64_t(matrix[j * N + k]) * src[i * N + k];
              dense[j * lines + i] = TCoeff(sum >> shift);
            }
          if (got != ref || got != dense)
            throw std::runtime_error("Corrected transform differs from normative/dense integer transform");
          ++cases;
        }
}

template<size_t N, size_t R>
void reportCost(const char *type, const int32_t (&pw)[N][R], const int32_t (&ph)[R][N],
                const int32_t (&nw)[N][R], const int32_t (&nh)[R][N], const TMatrixCoeff *matrix)
{
  const auto correction = makeNmfExactCorrection(pw, ph, nw, nh, matrix);
  const int64_t scale = int64_t(1) << (2 * NMF_FACTOR_FRACTIONAL_BITS);
  for (size_t j = 0; j < N; ++j)
    for (size_t k = 0; k < N; ++k)
    {
      int64_t value = correction.coefficient[j][k];
      for (size_t r = 0; r < R; ++r)
        value += int64_t(pw[j][r]) * ph[r][k] - int64_t(nw[j][r]) * nh[r][k];
      if (value != int64_t(matrix[j * N + k]) * scale)
        throw std::runtime_error("Exact matrix reconstruction failed");
    }
  for (size_t rows : {N, N / 2})
  {
    size_t nonzero = 0;
    for (size_t j = 0; j < rows; ++j)
      for (size_t k = 0; k < N; ++k)
        nonzero += correction.coefficient[j][k] != 0;
    const size_t factored = 2 * N * R + 2 * rows * R;
    std::cout << "NMF_COST kernel=" << type << " size=" << N << " rows=" << rows
              << " correction_nnz=" << nonzero << " dense_mult=" << N * rows
              << " factored_mult=" << factored << " corrected_mult=" << factored + nonzero << '\n';
  }
}

void check2D()
{
  const Transform correctedDct[] = {hybridForwardDCT8_B8, nmfExactForwardDCT8_B16, nmfExactForwardDCT8_B32};
  const Transform correctedDst[] = {hybridForwardDST7_B8, nmfExactForwardDST7_B16, nmfExactForwardDST7_B32};
  const Transform exactDct[] = {fastForwardDCT8_B8, fastForwardDCT8_B16, fastForwardDCT8_B32};
  const Transform exactDst[] = {fastForwardDST7_B8, fastForwardDST7_B16, fastForwardDST7_B32};
  const int sizes[] = {8, 16, 32};
  std::mt19937 random(5678);
  for (int wi = 0; wi < 3; ++wi)
    for (int hi = 0; hi < 3; ++hi)
      for (int ht = 0; ht < 2; ++ht)
        for (int vt = 0; vt < 2; ++vt)
          for (int pattern = 0; pattern < 20; ++pattern)
          {
            const int w = sizes[wi], h = sizes[hi];
            std::vector<TCoeff> src(w * h), tmp(w * h), tmpRef(w * h), got(w * h), ref(w * h);
            for (auto &v : src) v = TCoeff(int(random() % 2047) - 1023);
            const int cutW = w == 32 ? 16 : 0, cutH = h == 32 ? 16 : 0;
            (ht ? correctedDst : correctedDct)[wi](src.data(), tmp.data(), 7, h, 0, cutW);
            (ht ? exactDst : exactDct)[wi](src.data(), tmpRef.data(), 7, h, 0, cutW);
            (vt ? correctedDst : correctedDct)[hi](tmp.data(), got.data(), 12, w, cutW, cutH);
            (vt ? exactDst : exactDct)[hi](tmpRef.data(), ref.data(), 12, w, cutW, cutH);
            if (tmp != tmpRef || got != ref)
              throw std::runtime_error("Rectangular two-pass transform differs from VTM");
            ++cases;
          }
}

int main()
{
  checkKernel<8>(hybridForwardDCT8_B8, fastForwardDCT8_B8, g_trCoreDCT8P8[TRANSFORM_FORWARD][0]);
  checkKernel<8>(hybridForwardDST7_B8, fastForwardDST7_B8, g_trCoreDST7P8[TRANSFORM_FORWARD][0]);
  checkKernel<16>(nmfExactForwardDCT8_B16, fastForwardDCT8_B16, g_trCoreDCT8P16[TRANSFORM_FORWARD][0]);
  checkKernel<16>(nmfExactForwardDST7_B16, fastForwardDST7_B16, g_trCoreDST7P16[TRANSFORM_FORWARD][0]);
  checkKernel<32>(nmfExactForwardDCT8_B32, fastForwardDCT8_B32, g_trCoreDCT8P32[TRANSFORM_FORWARD][0]);
  checkKernel<32>(nmfExactForwardDST7_B32, fastForwardDST7_B32, g_trCoreDST7P32[TRANSFORM_FORWARD][0]);
  check2D();
  reportCost("DCT8", g_nmfDCT8P16PosW, g_nmfDCT8P16PosH, g_nmfDCT8P16NegW, g_nmfDCT8P16NegH, g_trCoreDCT8P16[TRANSFORM_FORWARD][0]);
  reportCost("DST7", g_nmfDST7P16PosW, g_nmfDST7P16PosH, g_nmfDST7P16NegW, g_nmfDST7P16NegH, g_trCoreDST7P16[TRANSFORM_FORWARD][0]);
  reportCost("DCT8", g_nmfDCT8P32PosW, g_nmfDCT8P32PosH, g_nmfDCT8P32NegW, g_nmfDCT8P32NegH, g_trCoreDCT8P32[TRANSFORM_FORWARD][0]);
  reportCost("DST7", g_nmfDST7P32PosW, g_nmfDST7P32PosH, g_nmfDST7P32NegW, g_nmfDST7P32NegH, g_trCoreDST7P32[TRANSFORM_FORWARD][0]);
  std::cout << "PASS: " << cases << " exact integer transform cases; forward_precision_bits="
            << (RExt__HIGH_PRECISION_FORWARD_TRANSFORM ? 8 : 0) << '\n';
}

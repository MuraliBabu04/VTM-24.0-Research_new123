#pragma once

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <map>
#include <mutex>
#include <string>
#include <tuple>

namespace cdsatm
{
using CounterKey = std::tuple<int, int, int, int, int>;

struct Counters
{
  uint64_t blocks         = 0;
  uint64_t totalColumns   = 0;
  uint64_t zeroColumns    = 0;
  uint64_t activeColumns  = 0;
  uint64_t baselineReads  = 0;
  uint64_t cdsatmReads    = 0;
  uint64_t baselineCycles = 0;
  uint64_t cdsatmCycles   = 0;
};

struct VerificationCounters
{
  uint64_t blocks       = 0;
  uint64_t coefficients = 0;
  uint64_t mismatches   = 0;
  uint64_t maxAbsError  = 0;
};

class Tracker
{
public:
  Tracker()
  {
    const char* sparsityPath = std::getenv("CDSATM_SPARSITY_LOG");
    if (sparsityPath != nullptr)
    {
      m_outputPath = sparsityPath;
    }

    const char* verificationPath = std::getenv("CDSATM_VERIFY_LOG");
    if (verificationPath != nullptr)
    {
      m_verificationPath = verificationPath;
    }

    const char* zeroSkip = std::getenv("CDSATM_ZERO_SKIP");
    m_zeroSkipEnabled = zeroSkip != nullptr && std::string(zeroSkip) != "0";
  }

  ~Tracker() { flush(); }

  bool enabled() const { return !m_outputPath.empty(); }
  bool verificationEnabled() const { return !m_verificationPath.empty(); }
  bool zeroSkipEnabled() const { return m_zeroSkipEnabled; }

  void record(int width, int height, int component, int horizontalType, int verticalType, int activeColumns)
  {
    if (!enabled())
    {
      return;
    }

    const int zeroColumns = width - activeColumns;
    const uint64_t samples = uint64_t(width) * uint64_t(height);
    const uint64_t activeSamples = uint64_t(activeColumns) * uint64_t(height);

    std::lock_guard<std::mutex> lock(m_mutex);
    Counters& counters = m_counters[CounterKey(width, height, component, horizontalType, verticalType)];
    counters.blocks++;
    counters.totalColumns   += uint64_t(width);
    counters.zeroColumns    += uint64_t(zeroColumns);
    counters.activeColumns  += uint64_t(activeColumns);
    counters.baselineReads  += samples;
    counters.cdsatmReads    += activeSamples;
    counters.baselineCycles += 2 * samples;
    counters.cdsatmCycles   += samples + activeSamples;
  }

  void recordVerification(int width, int height, int component, int horizontalType, int verticalType,
                          uint64_t coefficients, uint64_t mismatches, uint64_t maxAbsError)
  {
    if (!verificationEnabled())
    {
      return;
    }

    std::lock_guard<std::mutex> lock(m_mutex);
    VerificationCounters& counters =
      m_verificationCounters[CounterKey(width, height, component, horizontalType, verticalType)];
    counters.blocks++;
    counters.coefficients += coefficients;
    counters.mismatches += mismatches;
    counters.maxAbsError = std::max(counters.maxAbsError, maxAbsError);
  }

private:
  void flush()
  {
    std::lock_guard<std::mutex> lock(m_mutex);

    if (enabled())
    {
      std::ofstream output(m_outputPath);
      output << "width,height,component,tr_hor,tr_ver,blocks,total_columns,zero_columns,active_columns,"
                "baseline_reads,cdsatm_reads,baseline_cycles,cdsatm_cycles,sparsity_percent\n";
      output << std::fixed << std::setprecision(6);

      for (const auto& entry : m_counters)
      {
        const auto& key = entry.first;
        const Counters& counters = entry.second;
        const double sparsity = counters.totalColumns == 0
                                  ? 0.0
                                  : 100.0 * double(counters.zeroColumns) / double(counters.totalColumns);
        output << std::get<0>(key) << ',' << std::get<1>(key) << ',' << std::get<2>(key) << ','
               << std::get<3>(key) << ',' << std::get<4>(key) << ',' << counters.blocks << ','
               << counters.totalColumns << ',' << counters.zeroColumns << ',' << counters.activeColumns << ','
               << counters.baselineReads << ',' << counters.cdsatmReads << ',' << counters.baselineCycles << ','
               << counters.cdsatmCycles << ',' << sparsity << '\n';
      }
    }

    if (verificationEnabled())
    {
      std::ofstream output(m_verificationPath);
      output << "width,height,component,tr_hor,tr_ver,blocks,coefficients,mismatches,max_abs_error,bit_exact\n";

      for (const auto& entry : m_verificationCounters)
      {
        const auto& key = entry.first;
        const VerificationCounters& counters = entry.second;
        output << std::get<0>(key) << ',' << std::get<1>(key) << ',' << std::get<2>(key) << ','
               << std::get<3>(key) << ',' << std::get<4>(key) << ',' << counters.blocks << ','
               << counters.coefficients << ',' << counters.mismatches << ',' << counters.maxAbsError << ','
               << (counters.mismatches == 0 ? 1 : 0) << '\n';
      }
    }
  }

  std::string m_outputPath;
  std::string m_verificationPath;
  bool m_zeroSkipEnabled = false;
  std::mutex m_mutex;
  std::map<CounterKey, Counters> m_counters;
  std::map<CounterKey, VerificationCounters> m_verificationCounters;
};

inline Tracker& tracker()
{
  static Tracker instance;
  return instance;
}
}

#pragma once

#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <map>
#include <mutex>
#include <tuple>

namespace cdsatm
{
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

class Tracker
{
public:
  Tracker()
  {
    const char* configuredPath = std::getenv("CDSATM_SPARSITY_LOG");
    if (configuredPath != nullptr)
    {
      m_outputPath = configuredPath;
    }
  }

  ~Tracker() { flush(); }

  bool enabled() const { return !m_outputPath.empty(); }

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
    Counters& counters = m_counters[std::make_tuple(width, height, component, horizontalType, verticalType)];
    counters.blocks++;
    counters.totalColumns   += uint64_t(width);
    counters.zeroColumns    += uint64_t(zeroColumns);
    counters.activeColumns  += uint64_t(activeColumns);
    counters.baselineReads  += samples;
    counters.cdsatmReads    += activeSamples;
    counters.baselineCycles += 2 * samples;
    counters.cdsatmCycles   += samples + activeSamples;
  }

private:
  void flush()
  {
    if (!enabled())
    {
      return;
    }

    std::lock_guard<std::mutex> lock(m_mutex);
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

  std::string m_outputPath;
  std::mutex m_mutex;
  std::map<std::tuple<int, int, int, int, int>, Counters> m_counters;
};

inline Tracker& tracker()
{
  static Tracker instance;
  return instance;
}
}

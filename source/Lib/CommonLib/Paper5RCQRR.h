// Paper 5 experimental encoder-side covariance-weighted MTS proxy.
// This is a non-normative RC-QRR candidate-screening implementation.
// Exact normative transforms are retained for shortlisted candidates.
// RCQRR_ENGINE_V1
#pragma once
#include "Rom.h"
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <map>
#include <mutex>
#include <numeric>
#include <vector>

namespace Paper5RCQRR
{
  struct Stats
  {
    std::atomic<uint64_t> approximate{0};
    std::atomic<uint64_t> exactFinal{0};
    ~Stats()
    {
      std::fprintf(stderr, "PAPER5_RCQRR_STATS approx_candidates=%llu exact_shortlist_transforms=%llu MTS=1 LFNST=0 rho=0.92\n",
                   (unsigned long long)approximate.load(), (unsigned long long)exactFinal.load());
    }
  };
  inline Stats &stats() { static Stats instance; return instance; }

  inline void symmetricEigen(const std::vector<double> &source, const int n,
                             std::vector<double> &values, std::vector<double> &vectors)
  {
    std::vector<double> a = source;
    vectors.assign(n*n, 0.0);
    for (int i=0; i<n; ++i) vectors[i*n+i] = 1.0;
    const int maxIterations = 80*n*n;
    for (int iteration=0; iteration<maxIterations; ++iteration)
    {
      int p=0, q=1;
      double off=0.0;
      for (int i=0;i<n;++i)
        for (int j=i+1;j<n;++j)
          if (std::fabs(a[i*n+j])>off) {off=std::fabs(a[i*n+j]);p=i;q=j;}
      if (off<1e-12) break;
      const double apq=a[p*n+q];
      const double tau=(a[q*n+q]-a[p*n+p])/(2.0*apq);
      const double t=((tau>=0.0)?1.0:-1.0)/(std::fabs(tau)+std::sqrt(1.0+tau*tau));
      const double c=1.0/std::sqrt(1.0+t*t), s=t*c;
      const double app=a[p*n+p], aqq=a[q*n+q];
      a[p*n+p]=app-t*apq; a[q*n+q]=aqq+t*apq;
      a[p*n+q]=0.0; a[q*n+p]=0.0;
      for (int k=0;k<n;++k)
      {
        if (k!=p && k!=q)
        {
          const double akp=a[k*n+p], akq=a[k*n+q];
          a[k*n+p]=a[p*n+k]=c*akp-s*akq;
          a[k*n+q]=a[q*n+k]=s*akp+c*akq;
        }
        const double vkp=vectors[k*n+p], vkq=vectors[k*n+q];
        vectors[k*n+p]=c*vkp-s*vkq;
        vectors[k*n+q]=s*vkp+c*vkq;
      }
    }
    std::vector<int> order(n);
    std::iota(order.begin(),order.end(),0);
    std::sort(order.begin(),order.end(),[&](int i,int j){return a[i*n+i]>a[j*n+j];});
    std::vector<double> sortedVectors(n*n,0.0);
    values.resize(n);
    for (int col=0;col<n;++col)
    {
      values[col]=a[order[col]*n+order[col]];
      for (int row=0;row<n;++row) sortedVectors[row*n+col]=vectors[row*n+order[col]];
    }
    vectors.swap(sortedVectors);
  }

  // 0: DCT-II, 1: DST-VII, 2: DCT-VIII; exact forward integer tables from VTM.
  inline const TMatrixCoeff *kernel(const int n,const int family)
  {
    if (family==0)
    {
      switch(n) {
      case 4: return &g_trCoreDCT2P4[TRANSFORM_FORWARD][0][0];
      case 8: return &g_trCoreDCT2P8[TRANSFORM_FORWARD][0][0];
      case 16:return &g_trCoreDCT2P16[TRANSFORM_FORWARD][0][0];
      case 32:return &g_trCoreDCT2P32[TRANSFORM_FORWARD][0][0];
      }
    }
    else if (family==1)
    {
      switch(n) {
      case 4: return &g_trCoreDST7P4[TRANSFORM_FORWARD][0][0];
      case 8: return &g_trCoreDST7P8[TRANSFORM_FORWARD][0][0];
      case 16:return &g_trCoreDST7P16[TRANSFORM_FORWARD][0][0];
      case 32:return &g_trCoreDST7P32[TRANSFORM_FORWARD][0][0];
      }
    }
    else
    {
      switch(n) {
      case 4: return &g_trCoreDCT8P4[TRANSFORM_FORWARD][0][0];
      case 8: return &g_trCoreDCT8P8[TRANSFORM_FORWARD][0][0];
      case 16:return &g_trCoreDCT8P16[TRANSFORM_FORWARD][0][0];
      case 32:return &g_trCoreDCT8P32[TRANSFORM_FORWARD][0][0];
      }
    }
    return nullptr;
  }

  struct Factors
  {
    int n=0,r=0,bits=0;
    double da=0.0,db=0.0;
    std::vector<int16_t> a,b;  // A: n x r, B: r x n
  };

  inline Factors makeFactors(const int n,const int family)
  {
    Factors f;
    f.n=n;
    f.r=(n==32)?14:(n/2);
    f.bits=(n<=8)?7:6;
    const TMatrixCoeff *input=kernel(n,family);
    if (!input) return f;
    const int size=n*n;
    std::vector<double> cov(size,0.0),eval,v,half(size,0.0),invsqrt(size,0.0);
    for(int i=0;i<n;++i)
      for(int j=0;j<n;++j) cov[i*n+j]=std::pow(0.92,std::abs(i-j));
    symmetricEigen(cov,n,eval,v);
    for(int i=0;i<n;++i) for(int j=0;j<n;++j)
      for(int k=0;k<n;++k)
      {
        const double value=v[i*n+k]*v[j*n+k];
        const double e=std::max(1e-12,eval[k]);
        half[i*n+j]+=value*std::sqrt(e);
        invsqrt[i*n+j]+=value/std::sqrt(e);
      }
    double norm=0;
    for(int i=0;i<n;++i) norm+=double(input[i])*input[i];
    norm=std::sqrt(norm);
    std::vector<double> weighted(size,0.0),gram(size,0.0);
    for(int i=0;i<n;++i) for(int j=0;j<n;++j)
      for(int k=0;k<n;++k) weighted[i*n+j]+=(double(input[i*n+k])/norm)*half[k*n+j];
    for(int i=0;i<n;++i) for(int j=0;j<n;++j)
      for(int k=0;k<n;++k) gram[i*n+j]+=weighted[k*n+i]*weighted[k*n+j];
    std::vector<double> singularSq, rightV;
    symmetricEigen(gram,n,singularSq,rightV);
    std::vector<double> af(n*f.r,0.0),bf(f.r*n,0.0);
    for(int c=0;c<f.r;++c)
    {
      const double sigma=std::sqrt(std::max(1e-16,singularSq[c]));
      const double scale=std::sqrt(sigma);
      for(int row=0;row<n;++row)
      {
        for(int k=0;k<n;++k) af[row*f.r+c]+=weighted[row*n+k]*rightV[k*n+c]/scale;
        for(int k=0;k<n;++k) bf[c*n+row]+=scale*rightV[k*n+c]*invsqrt[k*n+row];
      }
    }
    double ma=0,mb=0;
    for(double x:af)ma=std::max(ma,std::fabs(x));
    for(double x:bf)mb=std::max(mb,std::fabs(x));
    const int qmax=(1<<(f.bits-1))-1;
    f.da=ma/qmax; f.db=mb/qmax;
    f.a.reserve(n*f.r);f.b.reserve(n*f.r);
    for(double x:af)f.a.push_back((int16_t)std::max(-qmax,std::min(qmax,int(std::lround(x/f.da)))));
    for(double x:bf)f.b.push_back((int16_t)std::max(-qmax,std::min(qmax,int(std::lround(x/f.db)))));
    return f;
  }

  inline const Factors &getFactors(const int n,const int family)
  {
    static std::map<std::pair<int,int>,Factors> cache;
    static std::mutex mutex;
    std::lock_guard<std::mutex> lock(mutex);
    auto key=std::make_pair(n,family);
    auto found=cache.find(key);
    if(found==cache.end()) found=cache.emplace(key,makeFactors(n,family)).first;
    return found->second;
  }

  // Approximate candidate score: four integer-factor matrix passes.
  // Coefficients are model-domain proxies ONLY; output is never encoded.
  template<class Buf>
  inline double score(const Buf &resi,const int width,const int height,const int mts)
  {
    if(width<4||width>32||height<4||height>32) return -1.0;
    if((width&(width-1))||(height&(height-1))) return -1.0;
    int hor=0,ver=0;
    switch(mts)
    {
      case 0: hor=0;ver=0;break;
      case 2: hor=1;ver=1;break;
      case 3: hor=2;ver=1;break;
      case 4: hor=1;ver=2;break;
      case 5: hor=2;ver=2;break;
      default: return -1.0;
    }
    const Factors &fh=getFactors(width,hor), &fv=getFactors(height,ver);
    if(fh.n==0||fv.n==0) return -1.0;
    std::vector<double> z1(height*fh.r,0.0),core(fv.r*fh.r,0.0),z2(fv.r*width,0.0);
    for(int y=0;y<height;++y) for(int j=0;j<fh.r;++j)
      for(int x=0;x<width;++x)
        z1[y*fh.r+j]+=double(resi.at(x,y))*fh.b[j*width+x];
    for(int i=0;i<fv.r;++i) for(int j=0;j<fh.r;++j)
      for(int y=0;y<height;++y)
        core[i*fh.r+j]+=fv.b[i*height+y]*z1[y*fh.r+j];
    for(int i=0;i<fv.r;++i) for(int x=0;x<width;++x)
      for(int j=0;j<fh.r;++j)
        z2[i*width+x]+=core[i*fh.r+j]*fh.a[x*fh.r+j];
    double sum=0.0;
    for(int y=0;y<height;++y) for(int x=0;x<width;++x)
    {
      double output=0.0;
      for(int i=0;i<fv.r;++i) output+=fv.a[y*fv.r+i]*z2[i*width+x];
      sum+=std::fabs(output);
    }
    return sum * fv.da*fv.db*fh.da*fh.db;
  }
}

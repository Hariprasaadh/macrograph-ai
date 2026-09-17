import React from 'react';

interface HeroProps {
  onGetStarted: () => void;
  onExploreDemo: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onGetStarted, onExploreDemo }) => {
  return (
    <section className="relative w-full px-4 sm:px-12 md:px-16 pt-4 sm:pt-10 md:pt-14 pb-8 sm:pb-12 flex flex-col justify-start items-start z-20">
      <div className="max-w-3xl lg:max-w-4xl flex flex-col items-start text-left bg-white/45 sm:bg-transparent backdrop-blur-md sm:backdrop-blur-none p-5 sm:p-0 rounded-3xl border border-white/50 sm:border-transparent shadow-xl sm:shadow-none transition-all">
        {/* Main Display Headline */}
        <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-[56px] xl:text-[62px] font-extrabold text-slate-900 tracking-[-0.03em] leading-[1.14] mb-3 sm:mb-5 font-display drop-shadow-sm">
          India’s Economy <br />
          Through Intelligent Agents
        </h1>

        {/* Subtitle Description */}
        <p className="text-sm sm:text-base md:text-lg lg:text-[19px] text-slate-700 font-normal leading-relaxed max-w-xl mb-6 sm:mb-8">
          Multi-agent intelligence platform for real-time macroeconomic insights, sector analysis, and data-driven decision making.
        </p>

        {/* Action Button Pair: Responsive full width or side-by-side */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4 w-full sm:w-auto">
          <button
            onClick={onGetStarted}
            className="w-full sm:w-auto text-center bg-[#0b1320] hover:bg-slate-850 text-white font-semibold text-sm sm:text-[15px] px-7 py-3 sm:py-3.5 rounded-xl shadow-lg hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200"
          >
            Get Started
          </button>

          <button
            onClick={onExploreDemo}
            className="w-full sm:w-auto text-center bg-[#faeed9] hover:bg-[#f3e3ca] border border-[#e2d2bc] text-slate-900 font-semibold text-sm sm:text-[15px] px-7 py-3 sm:py-3.5 rounded-xl shadow-sm hover:shadow hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200"
          >
            Explore Demo
          </button>
        </div>
      </div>
    </section>
  );
};


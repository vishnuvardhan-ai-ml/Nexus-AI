import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'low' | 'medium' | 'high' | 'cyan' | 'neutral' | 'blue';
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  className,
  dot = false,
}) => {
  const variants = {
    low: 'bg-emerald-950/70 text-emerald-400 border-emerald-500/30',
    medium: 'bg-amber-950/70 text-amber-400 border-amber-500/30',
    high: 'bg-rose-950/70 text-rose-400 border-rose-500/30',
    cyan: 'bg-cyan-950/70 text-brand-cyan border-brand-cyan/30',
    blue: 'bg-blue-950/70 text-brand-sky border-brand-blue/30',
    neutral: 'bg-navy-800 text-slate-300 border-navy-700',
  };

  const dotColors = {
    low: 'bg-emerald-400',
    medium: 'bg-amber-400',
    high: 'bg-rose-500 animate-pulse',
    cyan: 'bg-brand-cyan',
    blue: 'bg-brand-sky',
    neutral: 'bg-slate-400',
  };

  return (
    <span
      className={twMerge(
        clsx(
          'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border tracking-wide uppercase',
          variants[variant],
          className
        )
      )}
    >
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', dotColors[variant])} />}
      {children}
    </span>
  );
};

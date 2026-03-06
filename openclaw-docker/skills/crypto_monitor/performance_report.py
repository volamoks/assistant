#!/usr/bin/env python3
"""
Performance Report System

Generates weekly and monthly performance reports:
- Statistics by signal type
- Accuracy metrics
- Benchmark comparisons
- Recommendations for improvement

Output format optimized for Telegram
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from pathlib import Path

sys.path.insert(0, '/home/node/.openclaw/skills')

from signal_tracker import SignalTracker, Signal


# ── Configuration ──────────────────────────────────────────────────────────────

BENCHMARK_RETURNS = {
    '24h': 1.0,   # 1% daily
    '7d': 5.0,    # 5% weekly
    '30d': 15.0   # 15% monthly
}


# ── Performance Report Class ─────────────────────────────────────────────────

class PerformanceReport:
    """
    Performance reporting system.
    
    Generates:
    - Weekly reports
    - Monthly reports
    - Signal accuracy by type
    - Benchmark comparisons
    - Improvement recommendations
    """
    
    def __init__(self):
        """Initialize performance report system."""
        self.signal_tracker = SignalTracker()
    
    # ── Report Generation ─────────────────────────────────────────────────────
    
    def generate_weekly_report(self) -> str:
        """
        Generate weekly performance report.
        
        Returns:
            Formatted report string for Telegram
        """
        return self._generate_report("7d")
    
    def generate_monthly_report(self) -> str:
        """
        Generate monthly performance report.
        
        Returns:
            Formatted report string for Telegram
        """
        return self._generate_report("30d")
    
    def _generate_report(self, timeframe: str) -> str:
        """Generate report for specified timeframe."""
        stats = self.signal_tracker.get_statistics(timeframe)
        best = self.signal_tracker.get_best_signals(3)
        worst = self.signal_tracker.get_worst_signals(3)
        streak, streak_type = self.signal_tracker.get_current_streak()
        
        # Get weekly stats
        week_stats = self.signal_tracker.get_statistics("7d")
        month_stats = self.signal_tracker.get_statistics("30d")
        
        # Get signal type names for display
        timeframe_name = "WEEKLY" if timeframe == "7d" else "MONTHLY"
        
        lines = [
            f"📊 *SIGNAL PERFORMANCE {timeframe_name}*",
            "",
            f"📈 *Overall Accuracy: {stats['success_rate']}%*",
            ""
        ]
        
        # By signal type
        if stats.get('by_type'):
            lines.append("🎯 *By Signal Type:*")
            
            # Sort by success rate
            sorted_types = sorted(
                stats['by_type'].items(),
                key=lambda x: x[1].get('success_rate', 0),
                reverse=True
            )
            
            for signal_type, data in sorted_types:
                emoji = "✓" if data.get('success_rate', 0) >= 50 else "✗"
                rate = data.get('success_rate', 0)
                count = data['total']
                pending = data.get('pending', 0)
                
                lines.append(
                    f"• {signal_type}: {rate}% {emoji} ({count} signals, {pending} pending)"
                )
            
            lines.append("")
        
        # Best performing
        if best:
            lines.extend([
                "🏆 *Best Performing:*"
            ])
            
            for i, (signal_type, rate, count) in enumerate(best, 1):
                lines.append(f"{i}. {signal_type} → {rate}% success ({count} signals)")
            
            lines.append("")
        
        # Worst performing
        if worst:
            lines.extend([
                "⚠️ *Needs Improvement:*"
            ])
            
            for i, (signal_type, rate, count) in enumerate(worst, 1):
                lines.append(f"{i}. {signal_type} → {rate}% success ({count} signals)")
            
            lines.append("")
        
        # Streak
        if streak > 0:
            streak_emoji = "🔥" if streak_type == "win" else "📉"
            streak_text = "wins" if streak_type == "win" else "losses"
            lines.extend([
                f"🎲 *Current Streak:* {streak_emoji} {streak} {streak_text} in a row",
                ""
            ])
        
        # Summary
        lines.extend([
            "📅 *Summary:*",
            f"• Total signals ({timeframe}): {stats['total_signals']}",
            f"• Completed: {stats.get('completed_signals', 0)}",
            f"• Success: {stats.get('success_count', 0)}",
            f"• Failed: {stats.get('failed_count', 0)}",
            f"• Pending: {stats.get('pending_count', 0)}",
            ""
        ])
        
        # This week vs last week comparison
        if timeframe == "30d":
            week_comparison = self._compare_periods("7d", "7d")
            if week_comparison:
                lines.extend(week_comparison)
        
        # Recommendations
        recommendations = self._generate_recommendations(stats, best, worst)
        if recommendations:
            lines.extend([
                "📝 *Recommendations:*"
            ])
            lines.extend(recommendations)
        
        return "\n".join(lines)
    
    def _compare_periods(
        self,
        current_period: str,
        previous_period: str
    ) -> Optional[List[str]]:
        """Compare current period with previous period."""
        # This is simplified - in reality we'd need to track historical data
        return None
    
    def _generate_recommendations(
        self,
        stats: Dict,
        best: List[Tuple],
        worst: List[Tuple]
    ) -> List[str]:
        """Generate recommendations based on performance."""
        recommendations = []
        
        # Analyze worst performers
        if worst:
            worst_type = worst[0][0]  # Worst signal type
            recommendations.append(
                f"• Reduce weight of {worst_type} signals"
            )
        
        # Analyze best performers
        if best:
            best_type = best[0][0]  # Best signal type
            recommendations.append(
                f"• Focus on {best_type} contrarian signals"
            )
        
        # Check overall accuracy
        if stats['success_rate'] < 40:
            recommendations.append(
                "• Consider tightening signal thresholds"
            )
        elif stats['success_rate'] > 70:
            recommendations.append(
                "• Signal quality is excellent, consider increasing frequency"
            )
        
        # Check pending signals
        pending_ratio = stats.get('pending_count', 0) / max(stats['total_signals'], 1)
        if pending_ratio > 0.5:
            recommendations.append(
                "• Many pending signals - results will clarify accuracy soon"
            )
        
        # Add streak info
        streak, streak_type = self.signal_tracker.get_current_streak()
        if streak >= 3:
            streak_text = "winning" if streak_type == "win" else "losing"
            recommendations.append(
                f"• Currently {streak_text} - stay consistent"
            )
        
        return recommendations
    
    # ── Accuracy Metrics ───────────────────────────────────────────────────────
    
    def get_signal_accuracy(self, signal_type: str) -> float:
        """
        Get accuracy for a specific signal type.
        
        Args:
            signal_type: Signal type to analyze
        
        Returns:
            Accuracy percentage
        """
        signals = self.signal_tracker.get_signals_by_type(signal_type)
        
        if not signals:
            return 0.0
        
        completed = [s for s in signals if s.status in ["SUCCESS", "FAILED"]]
        
        if not completed:
            return 0.0
        
        success = sum(1 for s in completed if s.status == "SUCCESS")
        
        return (success / len(completed)) * 100
    
    def get_accuracy_by_timeframe(self, signal_type: str) -> Dict:
        """
        Get accuracy by check timeframe (24h, 7d, 30d).
        
        Args:
            signal_type: Signal type
        
        Returns:
            Dictionary with accuracy for each timeframe
        """
        signals = self.signal_tracker.get_signals_by_type(signal_type)
        
        results = {
            '24h': {'total': 0, 'success': 0},
            '7d': {'total': 0, 'success': 0},
            '30d': {'total': 0, 'success': 0}
        }
        
        for signal in signals:
            # Check 24h results
            if signal.result_24h is not None:
                results['24h']['total'] += 1
                if signal.status == "SUCCESS":
                    results['24h']['success'] += 1
            
            # Check 7d results
            if signal.result_7d is not None:
                results['7d']['total'] += 1
                if signal.status == "SUCCESS":
                    results['7d']['success'] += 1
            
            # Check 30d results
            if signal.result_30d is not None:
                results['30d']['total'] += 1
                if signal.status == "SUCCESS":
                    results['30d']['success'] += 1
        
        # Calculate percentages
        for timeframe, data in results.items():
            if data['total'] > 0:
                data['accuracy'] = (data['success'] / data['total']) * 100
            else:
                data['accuracy'] = 0.0
        
        return results
    
    def get_direction_accuracy(self, signal_type: str) -> Dict[str, float]:
        """
        Get accuracy by signal direction.
        
        Args:
            signal_type: Signal type
        
        Returns:
            Dictionary with accuracy for each direction
        """
        signals = self.signal_tracker.get_signals_by_type(signal_type)
        
        results = {
            'UP': {'total': 0, 'success': 0},
            'DOWN': {'total': 0, 'success': 0},
            'NEUTRAL': {'total': 0, 'success': 0}
        }
        
        for signal in signals:
            if signal.direction in results:
                results[signal.direction]['total'] += 1
                if signal.status == "SUCCESS":
                    results[signal.direction]['success'] += 1
        
        # Calculate percentages
        for direction, data in results.items():
            if data['total'] > 0:
                data['accuracy'] = (data['success'] / data['total']) * 100
            else:
                data['accuracy'] = 0.0
        
        return results
    
    # ── Benchmark Comparison ─────────────────────────────────────────────────
    
    def compare_with_benchmark(self, benchmark: float) -> Dict:
        """
        Compare signal performance with a benchmark.
        
        Args:
            benchmark: Benchmark percentage return
        
        Returns:
            Dictionary with comparison data
        """
        stats = self.signal_tracker.get_statistics("30d")
        
        # Calculate average return
        signals = self.signal_tracker.signals
        returns_24h = []
        returns_7d = []
        returns_30d = []
        
        for signal in signals:
            if signal.result_24h is not None:
                returns_24h.append(signal.result_24h)
            if signal.result_7d is not None:
                returns_7d.append(signal.result_7d)
            if signal.result_30d is not None:
                returns_30d.append(signal.result_30d)
        
        avg_24h = sum(returns_24h) / len(returns_24h) if returns_24h else 0
        avg_7d = sum(returns_7d) / len(returns_7d) if returns_7d else 0
        avg_30d = sum(returns_30d) / len(returns_30d) if returns_30d else 0
        
        # Calculate beat rate
        beat_rate_24h = sum(1 for r in returns_24h if r >= benchmark) / len(returns_24h) * 100 if returns_24h else 0
        beat_rate_7d = sum(1 for r in returns_7d if r >= benchmark) / len(returns_7d) * 100 if returns_7d else 0
        beat_rate_30d = sum(1 for r in returns_30d if r >= benchmark) / len(returns_30d) * 100 if returns_30d else 0
        
        return {
            'benchmark': benchmark,
            'average_returns': {
                '24h': round(avg_24h, 2),
                '7d': round(avg_7d, 2),
                '30d': round(avg_30d, 2)
            },
            'beat_rate': {
                '24h': round(beat_rate_24h, 1),
                '7d': round(beat_rate_7d, 1),
                '30d': round(beat_rate_30d, 1)
            },
            'total_signals_analyzed': len(returns_30d),
            'outperforming_signals': sum(1 for r in returns_30d if r >= benchmark)
        }
    
    def generate_benchmark_report(self, benchmark: float = 5.0) -> str:
        """
        Generate a benchmark comparison report.
        
        Args:
            benchmark: Benchmark percentage (default 5% for 30d)
        
        Returns:
            Formatted report string
        """
        comparison = self.compare_with_benchmark(benchmark)
        
        lines = [
            f"📊 *BENCHMARK COMPARISON* (>{benchmark}% return)",
            "",
            "📈 *Average Returns:*",
            f"• 24h: {comparison['average_returns']['24h']:+.2f}%",
            f"• 7d: {comparison['average_returns']['7d']:+.2f}%",
            f"• 30d: {comparison['average_returns']['30d']:+.2f}%",
            "",
            f"🎯 *Beat Rate:* (signals exceeding benchmark)",
            f"• 24h: {comparison['beat_rate']['24h']}%",
            f"• 7d: {comparison['beat_rate']['7d']}%",
            f"• 30d: {comparison['beat_rate']['30d']}%",
            "",
            f"📊 *Signals analyzed:* {comparison['total_signals_analyzed']}",
            f"✅ *Outperforming:* {comparison['outperforming_signals']}"
        ]
        
        return "\n".join(lines)
    
    # ── Detailed Analysis ───────────────────────────────────────────────────
    
    def get_top_signals(
        self,
        limit: int = 10,
        by: str = "success_rate"
    ) -> List[Dict]:
        """
        Get top performing signals.
        
        Args:
            limit: Number of results
            by: Sort by (success_rate, count, return)
        
        Returns:
            List of signal type dictionaries
        """
        stats = self.signal_tracker.get_statistics("all")
        by_type = stats.get('by_type', {})
        
        results = []
        
        for signal_type, data in by_type.items():
            result = {
                'type': signal_type,
                'total': data['total'],
                'success_rate': data.get('success_rate', 0),
                'pending': data.get('pending', 0)
            }
            
            # Calculate average return
            signals = self.signal_tracker.get_signals_by_type(signal_type)
            returns = []
            for s in signals:
                if s.result_30d:
                    returns.append(s.result_30d)
                elif s.result_7d:
                    returns.append(s.result_7d)
                elif s.result_24h:
                    returns.append(s.result_24h)
            
            result['avg_return'] = sum(returns) / len(returns) if returns else 0
            results.append(result)
        
        # Sort
        if by == "success_rate":
            results.sort(key=lambda x: x['success_rate'], reverse=True)
        elif by == "count":
            results.sort(key=lambda x: x['total'], reverse=True)
        elif by == "return":
            results.sort(key=lambda x: x['avg_return'], reverse=True)
        
        return results[:limit]
    
    def get_underperforming_signals(
        self,
        min_count: int = 3,
        threshold: float = 40.0
    ) -> List[Dict]:
        """
        Get signals that are underperforming.
        
        Args:
            min_count: Minimum number of signals to consider
            threshold: Success rate threshold
        
        Returns:
            List of underperforming signal types
        """
        stats = self.signal_tracker.get_statistics("all")
        
        underperforming = []
        
        for signal_type, data in stats.get('by_type', {}).items():
            if data['total'] >= min_count:
                rate = data.get('success_rate', 0)
                if rate < threshold:
                    underperforming.append({
                        'type': signal_type,
                        'success_rate': rate,
                        'total': data['total'],
                        'recommendation': self._get_improvement建议(signal_type, rate)
                    })
        
        return sorted(underperforming, key=lambda x: x['success_rate'])
    
    def _get_improvement建议(self, signal_type: str, rate: float) -> str:
        """Get improvement recommendation for a signal type."""
        if rate < 20:
            return "Consider removing this signal type"
        elif rate < 40:
            return "Review thresholds and parameters"
        else:
            return "Monitor closely"
    
    def generate_full_report(self) -> str:
        """
        Generate comprehensive performance report.
        
        Returns:
            Full formatted report
        """
        # Weekly report
        weekly = self.generate_weekly_report()
        
        # Monthly report
        monthly = self.generate_monthly_report()
        
        # Benchmark report
        benchmark = self.generate_benchmark_report(5.0)
        
        # Combine
        return f"{weekly}\n\n---\n\n{monthly}\n\n---\n\n{benchmark}"
    
    # ── Export ────────────────────────────────────────────────────────────────
    
    def export_report(self, filepath: Path, format: str = "json") -> bool:
        """
        Export report to file.
        
        Args:
            filepath: Output file path
            format: Output format (json, txt)
        
        Returns:
            True if successful
        """
        try:
            if format == "json":
                data = {
                    'weekly': self.signal_tracker.get_statistics("7d"),
                    'monthly': self.signal_tracker.get_statistics("30d"),
                    'benchmark': self.compare_with_benchmark(5.0),
                    'top_signals': self.get_top_signals(),
                    'generated_at': datetime.now().isoformat()
                }
                
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
            
            elif format == "txt":
                report = self.generate_full_report()
                
                with open(filepath, 'w') as f:
                    f.write(report)
            
            return True
        
        except IOError as e:
            print(f"[PerformanceReport] Export error: {e}")
            return False


# ── CLI Interface ──────────────────────────────────────────────────────────────

def main():
    """CLI for performance reports."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Reports")
    parser.add_argument("action", 
                        choices=["weekly", "monthly", "benchmark", "full", "export"],
                        default="weekly", help="Report to generate")
    parser.add_argument("--benchmark", "-b", type=float, default=5.0,
                        help="Benchmark percentage")
    parser.add_argument("--format", "-f", choices=["json", "txt"], default="txt",
                        help="Export format")
    parser.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    report = PerformanceReport()
    
    if args.action == "weekly":
        print(report.generate_weekly_report())
    
    elif args.action == "monthly":
        print(report.generate_monthly_report())
    
    elif args.action == "benchmark":
        print(report.generate_benchmark_report(args.benchmark))
    
    elif args.action == "full":
        print(report.generate_full_report())
    
    elif args.action == "export":
        if not args.output:
            print("Error: --output required")
            sys.exit(1)
        
        success = report.export_report(Path(args.output), args.format)
        print(f"Export {'successful' if success else 'failed'}")


if __name__ == '__main__':
    main()

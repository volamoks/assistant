#!/usr/bin/env python3
"""
Signal Memory System

Integration with existing memory systems:
- JSON file storage (signal_history.json)
- ChromaDB for vector search (optional)
- Integration with btc_alert_memory.py and agent_memory

Features:
- Save/load signals
- Find similar signals by pattern
- Semantic search capabilities
- Integration with Memory class from agent_memory
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from dataclasses import asdict

sys.path.insert(0, '/home/node/.openclaw/skills')

from signal_tracker import Signal, SignalTracker


# ── Configuration ──────────────────────────────────────────────────────────────

DEFAULT_STORAGE_PATH = Path("/home/node/.openclaw/skills/crypto_monitor/data/signal_memory.json")
MEMORY_COLLECTION = "crypto_signals"


# ── Signal Memory Class ───────────────────────────────────────────────────────

class SignalMemory:
    """
    Memory system for signals.
    
    Provides:
    - JSON file storage
    - Integration with agent_memory.Memory
    - Pattern-based signal search
    - ChromaDB integration for vector search (optional)
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        use_chroma: bool = False,
        use_agent_memory: bool = True
    ):
        """
        Initialize signal memory.
        
        Args:
            storage_path: Path to JSON storage
            use_chroma: Enable ChromaDB vector search
            use_agent_memory: Enable agent_memory integration
        """
        self.storage_path = storage_path or DEFAULT_STORAGE_PATH
        self.use_chroma = use_chroma
        self.use_agent_memory = use_agent_memory
        
        # Initialize signal tracker for JSON storage
        self.signal_tracker = SignalTracker(self.storage_path)
        
        # Initialize agent memory if available
        self.agent_memory = None
        if use_agent_memory:
            try:
                from agent_memory.memory import Memory
                self.agent_memory = Memory(collection=MEMORY_COLLECTION)
            except ImportError as e:
                print(f"[SignalMemory] Could not import agent_memory: {e}")
        
        # Initialize ChromaDB if enabled
        self.chroma_collection = None
        if use_chroma:
            try:
                import chromadb
                self.chroma_client = chromadb.PersistentClient(
                    path=str(self.storage_path.parent / "chroma_db")
                )
                self.chroma_collection = self.chroma_client.get_or_create_collection(
                    name="signals"
                )
            except ImportError:
                print("[SignalMemory] ChromaDB not available, disabling vector search")
            except Exception as e:
                print(f"[SignalMemory] ChromaDB error: {e}")
    
    # ── Core Methods ───────────────────────────────────────────────────────────
    
    def save_signal(self, signal: Signal) -> str:
        """
        Save signal to memory.
        
        Args:
            signal: Signal to save
        
        Returns:
            Signal ID
        """
        # Save to JSON via signal tracker
        self.signal_tracker.signals.append(signal)
        self.signal_tracker._save_signals()
        
        # Save to agent memory if available
        if self.agent_memory:
            self._save_to_agent_memory(signal)
        
        # Save to ChromaDB if available
        if self.chroma_collection:
            self._save_to_chroma(signal)
        
        return signal.id
    
    def load_signals(
        self,
        signal_type: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Signal]:
        """
        Load signals with optional filters.
        
        Args:
            signal_type: Filter by signal type
            symbol: Filter by symbol
            status: Filter by status
            limit: Maximum number of signals
        
        Returns:
            List of matching signals
        """
        signals = self.signal_tracker.signals
        
        if signal_type:
            signals = [s for s in signals if s.type == signal_type.upper()]
        if symbol:
            signals = [s for s in signals if s.symbol == symbol.upper()]
        if status:
            signals = [s for s in signals if s.status == status.upper()]
        
        # Sort by timestamp (newest first) and limit
        signals = sorted(signals, key=lambda x: x.timestamp, reverse=True)
        return signals[:limit]
    
    def get_signal(self, signal_id: str) -> Optional[Signal]:
        """Get signal by ID."""
        return self.signal_tracker.get_signal(signal_id)
    
    # ── Search Methods ─────────────────────────────────────────────────────────
    
    def find_similar_signals(
        self,
        signal_pattern: str,
        limit: int = 10
    ) -> List[Signal]:
        """
        Find signals similar to a pattern.
        
        Uses text matching on reason field.
        
        Args:
            signal_pattern: Pattern to search for
            limit: Maximum results
        
        Returns:
            List of similar signals
        """
        pattern_lower = signal_pattern.lower()
        matches = []
        
        for signal in self.signal_tracker.signals:
            # Check if pattern is in reason or type
            if pattern_lower in signal.reason.lower() or \
               pattern_lower in signal.type.lower():
                matches.append(signal)
        
        # Sort by timestamp (newest first)
        matches = sorted(matches, key=lambda x: x.timestamp, reverse=True)
        return matches[:limit]
    
    def find_signals_by_context(
        self,
        keywords: List[str],
        match_all: bool = False,
        limit: int = 10
    ) -> List[Signal]:
        """
        Find signals matching keywords.
        
        Args:
            keywords: List of keywords to match
            match_all: If True, all keywords must match; if False, any keyword
            limit: Maximum results
        
        Returns:
            List of matching signals
        """
        matches = []
        
        for signal in self.signal_tracker.signals:
            text = f"{signal.reason} {signal.type} {signal.symbol}".lower()
            
            if match_all:
                if all(kw.lower() in text for kw in keywords):
                    matches.append(signal)
            else:
                if any(kw.lower() in text for kw in keywords):
                    matches.append(signal)
        
        matches = sorted(matches, key=lambda x: x.timestamp, reverse=True)
        return matches[:limit]
    
    def find_signals_by_price_range(
        self,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: int = 100
    ) -> List[Signal]:
        """Find signals within a price range."""
        signals = self.signal_tracker.signals
        
        if min_price is not None:
            signals = [s for s in signals if s.price >= min_price]
        if max_price is not None:
            signals = [s for s in signals if s.price <= max_price]
        
        signals = sorted(signals, key=lambda x: x.timestamp, reverse=True)
        return signals[:limit]
    
    def find_signals_by_confidence(
        self,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
        limit: int = 100
    ) -> List[Signal]:
        """Find signals by confidence range."""
        signals = [
            s for s in self.signal_tracker.signals
            if min_confidence <= s.confidence <= max_confidence
        ]
        
        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)
        return signals[:limit]
    
    # ── Analysis Methods ───────────────────────────────────────────────────────
    
    def get_signals_by_outcome(
        self,
        successful: bool = True,
        min_results: int = 1
    ) -> Dict[str, List[Signal]]:
        """
        Get signals grouped by outcome analysis.
        
        Args:
            successful: Filter for successful signals
            min_results: Minimum number of results to include
        
        Returns:
            Dictionary of signal_type -> list of signals
        """
        outcome_signals = {}
        
        for signal in self.signal_tracker.signals:
            # Check if signal has results
            has_result = (
                signal.result_24h is not None or
                signal.result_7d is not None or
                signal.result_30d is not None
            )
            
            if not has_result:
                continue
            
            # Determine if successful
            is_successful = False
            if signal.result_30d:
                is_successful = self._check_success(signal)
            elif signal.result_7d:
                is_successful = self._check_success(signal)
            elif signal.result_24h:
                is_successful = self._check_success(signal)
            
            if is_successful == successful:
                if signal.type not in outcome_signals:
                    outcome_signals[signal.type] = []
                outcome_signals[signal.type].append(signal)
        
        # Filter by min_results
        return {
            k: v for k, v in outcome_signals.items() 
            if len(v) >= min_results
        }
    
    def _check_success(self, signal: Signal) -> bool:
        """Check if signal was successful based on results."""
        # Get the latest result
        result = signal.result_30d or signal.result_7d or signal.result_24h
        if result is None:
            return False
        
        # Check direction
        if signal.direction == "UP":
            return result > 1.0
        elif signal.direction == "DOWN":
            return result < -1.0
        else:
            return abs(result) < 2.0
    
    def get_successful_patterns(self, min_count: int = 3) -> List[Dict]:
        """
        Find patterns that lead to successful signals.
        
        Args:
            min_count: Minimum number of occurrences
        
        Returns:
            List of pattern dictionaries with stats
        """
        patterns = {}
        
        for signal in self.signal_tracker.signals:
            # Create pattern key from type and direction
            pattern_key = f"{signal.type}_{signal.direction}"
            
            if pattern_key not in patterns:
                patterns[pattern_key] = {
                    'type': signal.type,
                    'direction': signal.direction,
                    'total': 0,
                    'successful': 0,
                    'avg_confidence': []
                }
            
            patterns[pattern_key]['total'] += 1
            
            # Check success
            if self._check_success(signal):
                patterns[pattern_key]['successful'] += 1
            
            patterns[pattern_key]['avg_confidence'].append(signal.confidence)
        
        # Calculate success rates
        results = []
        for pattern, data in patterns.items():
            if data['total'] >= min_count:
                results.append({
                    'pattern': pattern,
                    'success_rate': data['successful'] / data['total'] * 100,
                    'total_signals': data['total'],
                    'avg_confidence': sum(data['avg_confidence']) / len(data['avg_confidence'])
                })
        
        return sorted(results, key=lambda x: x['success_rate'], reverse=True)
    
    # ── Agent Memory Integration ────────────────────────────────────────────────
    
    def _save_to_agent_memory(self, signal: Signal):
        """Save signal to agent_memory."""
        if not self.agent_memory:
            return
        
        try:
            text = f"Signal: {signal.type} {signal.symbol} at ${signal.price:,.2f} - {signal.reason}"
            
            self.agent_memory.store(
                text=text,
                metadata={
                    'category': 'signal',
                    'signal_id': signal.id,
                    'signal_type': signal.type,
                    'symbol': signal.symbol,
                    'direction': signal.direction,
                    'confidence': signal.confidence,
                    'status': signal.status,
                    'timestamp': signal.timestamp
                }
            )
        except Exception as e:
            print(f"[SignalMemory] Error saving to agent_memory: {e}")
    
    def _save_to_chroma(self, signal: Signal):
        """Save signal to ChromaDB."""
        if not self.chroma_collection:
            return
        
        try:
            # Create embedding from signal text
            text = f"{signal.type} {signal.symbol} {signal.reason}"
            
            self.chroma_collection.add(
                documents=[text],
                ids=[signal.id],
                metadatas=[{
                    'signal_type': signal.type,
                    'symbol': signal.symbol,
                    'direction': signal.direction,
                    'confidence': signal.confidence,
                    'timestamp': signal.timestamp
                }]
            )
        except Exception as e:
            print(f"[SignalMemory] Error saving to ChromaDB: {e}")
    
    def search_agent_memory(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search signals in agent_memory.
        
        Args:
            query: Search query
            limit: Maximum results
        
        Returns:
            List of matching memory entries
        """
        if not self.agent_memory:
            return []
        
        try:
            # Use agent_memory search
            results = self.agent_memory.search(query, limit=limit)
            return [
                {
                    'text': r.text,
                    'metadata': r.metadata,
                    'score': getattr(r, 'score', None)
                }
                for r in results
            ]
        except Exception as e:
            print(f"[SignalMemory] Error searching agent_memory: {e}")
            return []
    
    # ── Backup and Restore ────────────────────────────────────────────────────
    
    def export_signals(self, filepath: Path) -> bool:
        """
        Export signals to a file.
        
        Args:
            filepath: Path to export file
        
        Returns:
            True if successful
        """
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    'signals': [s.to_dict() for s in self.signal_tracker.signals],
                    'exported_at': datetime.now().isoformat()
                }, f, indent=2)
            return True
        except IOError as e:
            print(f"[SignalMemory] Export error: {e}")
            return False
    
    def import_signals(self, filepath: Path, merge: bool = True) -> int:
        """
        Import signals from a file.
        
        Args:
            filepath: Path to import file
            merge: If True, merge with existing; if False, replace
        
        Returns:
            Number of signals imported
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            imported_signals = [Signal.from_dict(s) for s in data.get('signals', [])]
            
            if merge:
                existing_ids = {s.id for s in self.signal_tracker.signals}
                new_signals = [s for s in imported_signals if s.id not in existing_ids]
                self.signal_tracker.signals.extend(new_signals)
                count = len(new_signals)
            else:
                self.signal_tracker.signals = imported_signals
                count = len(imported_signals)
            
            self.signal_tracker._save_signals()
            return count
        
        except (IOError, json.JSONDecodeError) as e:
            print(f"[SignalMemory] Import error: {e}")
            return 0
    
    # ── Utility Methods ───────────────────────────────────────────────────────
    
    def get_memory_stats(self) -> Dict:
        """Get memory system statistics."""
        signals = self.signal_tracker.signals
        
        return {
            'total_signals': len(signals),
            'storage_path': str(self.storage_path),
            'chroma_enabled': self.chroma_collection is not None,
            'agent_memory_enabled': self.agent_memory is not None,
            'by_type': self._count_by_field('type'),
            'by_symbol': self._count_by_field('symbol'),
            'by_status': self._count_by_field('status')
        }
    
    def _count_by_field(self, field: str) -> Dict[str, int]:
        """Count signals by a specific field."""
        counts = {}
        for signal in self.signal_tracker.signals:
            value = getattr(signal, field, None)
            if value:
                counts[value] = counts.get(value, 0) + 1
        return counts
    
    def cleanup_old_signals(self, days: int = 90) -> int:
        """
        Remove signals older than specified days.
        
        Args:
            days: Number of days to keep
        
        Returns:
            Number of signals removed
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self.signal_tracker.signals)
        
        self.signal_tracker.signals = [
            s for s in self.signal_tracker.signals
            if datetime.fromisoformat(s.timestamp) >= cutoff
        ]
        
        removed = original_count - len(self.signal_tracker.signals)
        
        if removed > 0:
            self.signal_tracker._save_signals()
        
        return removed


# ── CLI Interface ──────────────────────────────────────────────────────────────

def main():
    """CLI for signal memory."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Signal Memory")
    parser.add_argument("action", 
                        choices=["search", "stats", "export", "import", "cleanup"],
                        default="stats", help="Action to perform")
    parser.add_argument("--pattern", "-p", help="Search pattern")
    parser.add_argument("--type", help="Signal type filter")
    parser.add_argument("--symbol", "-s", help="Symbol filter")
    parser.add_argument("--status", help="Status filter")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Result limit")
    parser.add_argument("--filepath", "-f", help="File path for import/export")
    parser.add_argument("--days", type=int, default=90, help="Days for cleanup")
    
    args = parser.parse_args()
    
    memory = SignalMemory()
    
    if args.action == "search":
        if not args.pattern:
            print("Error: --pattern required")
            sys.exit(1)
        
        results = memory.find_similar_signals(args.pattern, args.limit)
        print(f"Found {len(results)} signals:")
        for s in results:
            print(f"  {s.id}: {s.type} {s.symbol} {s.direction} - {s.reason[:50]}...")
    
    elif args.action == "stats":
        stats = memory.get_memory_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.action == "export":
        if not args.filepath:
            print("Error: --filepath required")
            sys.exit(1)
        
        success = memory.export_signals(Path(args.filepath))
        print(f"Export {'successful' if success else 'failed'}")
    
    elif args.action == "import":
        if not args.filepath:
            print("Error: --filepath required")
            sys.exit(1)
        
        count = memory.import_signals(Path(args.filepath))
        print(f"Imported {count} signals")
    
    elif args.action == "cleanup":
        count = memory.cleanup_old_signals(args.days)
        print(f"Removed {count} signals older than {args.days} days")


if __name__ == '__main__':
    main()

"""
scripts/05_stream_producer.py
-----------------------------
Standalone CLI Live Stream Producer for NYC Urban Mobility.
Simulates real-time dispatch of Yellow Taxi rides into the serving layer.

Usage:
    python scripts/05_stream_producer.py [--rate 15] [--duration 60] [--batch-size 5]
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure robust console output on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.streaming import LiveStreamEngine
from src.queries import get_live_stream_stats


def run_producer(rate: float = 10.0, duration: int = 0, batch_size: int = 5):
    """
    Executes live stream producer loop.
    rate: target trips per second
    duration: total runtime in seconds (0 = run indefinitely until Ctrl+C)
    batch_size: number of trips per push batch
    """
    print("\n" + "=" * 65)
    print("      [TAXI] NYC URBAN MOBILITY REAL-TIME STREAM PRODUCER       ")
    print("=" * 65)
    print(f"Target Ingestion Rate : {rate} trips/second")
    print(f"Batch Size            : {batch_size} rides per emit")
    print(f"Duration              : {'Indefinite (Ctrl+C to stop)' if duration <= 0 else f'{duration} seconds'}")
    print("=" * 65 + "\n")


    engine_streamer = LiveStreamEngine()
    sleep_interval = max(0.05, batch_size / rate)
    
    start_time = time.time()
    total_injected = 0
    batch_count = 0

    try:
        while True:
            elapsed = time.time() - start_time
            if duration > 0 and elapsed >= duration:
                print(f"\n[INFO] Target duration of {duration}s reached.")
                break

            # Inject batch
            trips = engine_streamer.generate_trip_batch(count=batch_size)
            inserted = engine_streamer.inject_trips(count=batch_size)
            total_injected += inserted
            batch_count += 1

            # Log sample trip and batch status
            sample = trips[0] if trips else {}
            zone = sample.get("zone_name", "Unknown")
            borough = sample.get("borough", "NYC")
            fare = sample.get("fare_amount", 0.0)
            surge = sample.get("surge_multiplier", 1.0)
            sim_fare = sample.get("simulated_fare", fare)
            
            surge_icon = "🟢 1.0x" if surge == 1.0 else ("🟡 1.3x" if surge == 1.3 else ("🔴 1.8x" if surge == 1.8 else "🟣 2.5x SURGE"))

            actual_rate = total_injected / max(0.1, elapsed)
            print(
                f"[{sample.get('event_time', '')}] "
                f"Batch #{batch_count:<3} | Injected: {inserted:>2} | "
                f"Sample: {zone[:18]:<18} ({borough[:8]}) ${fare:.2f} -> {surge_icon} (${sim_fare:.2f}) | "
                f"Overall Rate: {actual_rate:.1f} r/s"
            )

            time.sleep(sleep_interval)

    except KeyboardInterrupt:
        print("\n[STOPPED] Live stream producer interrupted by user (Ctrl+C).")

    final_elapsed = max(0.1, time.time() - start_time)
    print("\n" + "=" * 65)
    print(f"Total Rides Streamed : {total_injected:,}")
    print(f"Elapsed Time         : {final_elapsed:.1f} seconds")
    print(f"Average Throughput   : {total_injected / final_elapsed:.1f} rides/sec")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NYC TLC Live Stream Telemetry Producer")
    parser.add_argument("--rate", type=float, default=10.0, help="Target trips per second (default: 10.0)")
    parser.add_argument("--duration", type=int, default=0, help="Total stream duration in seconds (0 = infinite)")
    parser.add_argument("--batch-size", type=int, default=5, help="Trips per database insert batch (default: 5)")
    args = parser.parse_args()

    run_producer(rate=args.rate, duration=args.duration, batch_size=args.batch_size)

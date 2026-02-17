import sys
from datetime import date
from pathlib import Path
import yaml

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from api.services.daily import run_daily_batch
from api.schemas.daily import DailyRunRequest

def test_daily_batch():
    print("Testing Daily Batch Logic...")
    
    # 1. Test Dry Run with defaults (End = Today)
    print("\n[Test 1] Dry Run (Default Dates)")
    req = DailyRunRequest(dry_run=True)
    resp = run_daily_batch(req)
    
    print(f"Batch ID: {resp.batch_id}")
    print(f"Items: {len(resp.items)}")
    
    if not resp.items:
        print("Skipping verification as no items returned (check tickers in config).")
        return

    # Verify runtime config for first ticker
    ticker = resp.items[0].ticker
    batch_dir = Path("reports/daily/runtime") / resp.batch_id
    config_path = batch_dir / f"{ticker}.yaml"
    
    if not config_path.exists():
        print(f"FAILED: Config not found at {config_path}")
        return
        
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
        
    print(f"Generated Config for {ticker}:")
    print(f"  Start: {cfg['backtest']['start']}")
    print(f"  End: {cfg['backtest']['end']}")
    
    expected_end = date.today().isoformat()
    if cfg['backtest']['end'] == expected_end:
        print("  ✅ End date is correctly set to Today.")
    else:
        print(f"  ❌ End date mismatch. Expected {expected_end}, got {cfg['backtest']['end']}")

    # 2. Test Date Override
    print("\n[Test 2] Date Override")
    req_override = DailyRunRequest(
        dry_run=True,
        date_override={"start": "2020-01-01", "end": "2020-12-31"}
    )
    resp_override = run_daily_batch(req_override)
    
    ticker = resp_override.items[0].ticker
    batch_dir = Path("reports/daily/runtime") / resp_override.batch_id
    config_path = batch_dir / f"{ticker}.yaml"
    
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
        
    print(f"Generated Config for {ticker}:")
    print(f"  Start: {cfg['backtest']['start']}")
    print(f"  End: {cfg['backtest']['end']}")
    
    if cfg['backtest']['start'] == "2020-01-01" and cfg['backtest']['end'] == "2020-12-31":
        print("  ✅ Date override successful.")
    else:
        print("  ❌ Date override failed.")

    # 3. Test Date Override Start Only -> End = Today
    print("\n[Test 3] Date Override Start Only")
    req_start_only = DailyRunRequest(
        dry_run=True,
        date_override={"start": "2020-01-01"}
    )
    resp_start_only = run_daily_batch(req_start_only)
    
    ticker = resp_start_only.items[0].ticker
    batch_dir = Path("reports/daily/runtime") / resp_start_only.batch_id
    config_path = batch_dir / f"{ticker}.yaml"
    
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    print(f"Generated Config for {ticker}:")
    print(f"  Start: {cfg['backtest']['start']}")
    print(f"  End: {cfg['backtest']['end']}")
    
    expected_end = date.today().isoformat()
    if cfg['backtest']['end'] == expected_end:
         print("  ✅ End date is correctly set to Today (Auto Date).")
    else:
         print(f"  ❌ End date mismatch. Expected {expected_end}, got {cfg['backtest']['end']}")

if __name__ == "__main__":
    try:
        test_daily_batch()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

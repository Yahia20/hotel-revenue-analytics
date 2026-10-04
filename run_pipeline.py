"""Run the whole project end to end: data -> warehouse + tests -> model -> policy backtest -> dashboard.

    python run_pipeline.py            # everything
    python run_pipeline.py --skip-dbt # reuse the existing warehouse
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from hotel_analytics import dashboard, model, policy  # noqa: E402
from hotel_analytics.download import ensure_raw_data  # noqa: E402


def dbt_build() -> None:
    dbt = shutil.which("dbt", path=str(Path(sys.executable).parent)) or "dbt"
    cmd = [dbt, "build", "--profiles-dir", ".", "--log-format", "text"]
    subprocess.run(cmd, cwd=ROOT / "warehouse", check=True)
    # Published next to the dashboard: model lineage, column docs and every test, browsable.
    subprocess.run([dbt, "docs", "generate", "--profiles-dir", ".", "--static"], cwd=ROOT / "warehouse", check=True)
    (ROOT / "site").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "warehouse" / "target" / "static_index.html", ROOT / "site" / "dbt-docs.html")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-dbt", action="store_true")
    args = parser.parse_args()

    ensure_raw_data()
    if not args.skip_dbt:
        dbt_build()
    print("model:", model.run()["test"])
    print("policy:", policy.run()["base_case"])
    print("dashboard:", dashboard.build())


if __name__ == "__main__":
    main()

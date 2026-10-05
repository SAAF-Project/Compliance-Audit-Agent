from __future__ import annotations
import os, sys, json

sys.path.append(os.getcwd())

from datetime import datetime
from pathlib import Path

import argparse

_parser = argparse.ArgumentParser(description="Compliance audit orchestration")
_parser.add_argument(
    "--no-data-testmode",
    action="store_true",
    help="With --validate and --load-progress, also load the saved validation reports of that run instead of re-running validation",
)
_parser.add_argument("--validate", action="store_true")
_parser.add_argument(
    "--load-progress",
    default=None,
    help="Offline run: timestamp of a saved run in the progress folder. No API calls are made; every agent reply is loaded from that run's saved outputs",
)
_parser.add_argument(
    "--progress-path",
    default="./prog_res",
    help="Progress folder: run outputs are written here and saved validation reports are loaded from here",
)
_parser.add_argument(
    "--policy-path",
    default="./data/plain_docs",
    help="Folder of plain-text policy documents (*.txt)",
)
_parser.add_argument(
    "--guideline-file",
    default="./data/guidelines.json",
    help="JSON file of guideline number -> verbatim guideline text",
)
_parser.add_argument(
    "--policy-summary-file",
    default="./data/policy_summary.txt",
    help="One-line-per-policy summary used by the selector",
)
_parser.add_argument(
    "--save-raw-results",
    action="store_true",
    help="Also save the raw results JSON with every agent's output (<progress-path>/output_<guideline>_<timestamp>.json)",
)
_parser.add_argument(
    "--findings-file",
    default=None,
    help="Save the raw results JSON to this path instead (implies --save-raw-results)",
)
_args = _parser.parse_args()

NO_DATA_TESTMODE = _args.no_data_testmode
VALIDATE = _args.validate
load_progress = _args.load_progress

import utils
from utils import main, OFFLINE_MISSING_REPLIES

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# GUIDELINES_TO_CHECK = [27, 28, 33, 52, 53, 54, 55, 56]
GUIDELINES_TO_CHECK = [27]

POLICY_DIR = Path(_args.policy_path)
GUIDELINE_FILE = Path(_args.guideline_file)
POLICY_SUMMARY_FILE = Path(_args.policy_summary_file)
PROGRESS_DIR = Path(_args.progress_path)
PROGRESS_DIR.mkdir(parents=True, exist_ok=True)

utils.configure(
    _args, timestamp, POLICY_DIR, POLICY_SUMMARY_FILE, PROGRESS_DIR
)


# -------------------- Entry point --------------------

if __name__ == "__main__":
    with open(GUIDELINE_FILE, "r", encoding="utf-8") as f:
        sections_dict = json.load(f)

    try:
        all_results = []
        for guideline_num in GUIDELINES_TO_CHECK:
            print(f"\n{'='*80}")
            print(f"Processing Guideline {guideline_num}")
            print(f"{'='*80}")
            result = main(guideline_num, sections_dict)
            if result is not None:
                all_results.append(result)

        if all_results:
            combined = all_results
            if load_progress:
                note = (
                    f"Offline run: no API calls were made. Agent outputs were loaded from the saved progress "
                    f"files of run {load_progress} in {PROGRESS_DIR} instead of being newly generated."
                )
                if OFFLINE_MISSING_REPLIES:
                    note += f" No saved reply was found for: {', '.join(OFFLINE_MISSING_REPLIES)}; those steps have no results."
                if VALIDATE:
                    note += (
                        " Validation results were also loaded from that run."
                        if NO_DATA_TESTMODE
                        else " Validation was re-run locally on the loaded outputs."
                    )
                combined = {
                    "note": note,
                    "results": all_results,
                }
            combined_json = f"{PROGRESS_DIR}/output_combined_{timestamp}.json"
            with open(combined_json, "w", encoding="utf-8") as f:
                json.dump(combined, f, ensure_ascii=False, indent=2)
            print(f"\n[+] Wrote combined JSON — {combined_json}")
        else:
            print(
                "\n[!] No guideline produced results — combined JSON not written."
            )

        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
        sys.exit(130)

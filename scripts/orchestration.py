"""Public launcher; the separately managed private pipeline is not distributed here."""
from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sys

# Retained selection from the original launcher; not a public sample guideline.
GUIDELINES_TO_CHECK = [27]


class IncompleteRun(Exception):
    """No complete assessment can be claimed."""


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--status", action="store_true", help="show public distribution status without loading private code or data")
    result.add_argument("--no-data-testmode", action="store_true", help="With --validate and --load-progress, load that run's saved validation reports")
    result.add_argument("--validate", action="store_true")
    result.add_argument("--load-progress", default=None, help="Private-runtime replay of a saved run; its provider behavior is not verified by public tests")
    result.add_argument("--progress-path", default="./prog_res", help="Progress folder for outputs and saved validation reports")
    result.add_argument("--policy-path", default="./data/plain_docs", help="Folder of plain-text policy documents")
    result.add_argument("--guideline-file", default="./data/guidelines.json", help="JSON mapping of guideline number to verbatim guideline text")
    result.add_argument("--policy-summary-file", default="./data/policy_summary.txt", help="One-line-per-policy summary")
    result.add_argument("--save-raw-results", action="store_true")
    result.add_argument("--findings-file", default=None, help="Private-runtime raw results path (implies --save-raw-results)")
    return result


def runtime_path():
    path = Path(__file__).resolve().parent / "utils.py"
    if path.is_symlink() or not path.is_file():
        raise IncompleteRun("The private runtime scripts/utils.py is not distributed in this checkout; no audit ran.")
    return path


def load_runtime(path):
    """Load only the explicit sibling helper, never a utils module from the cwd."""
    spec = importlib.util.spec_from_file_location("utils", path)
    if spec is None or spec.loader is None:
        raise IncompleteRun("The local private runtime cannot be loaded; no audit ran.")
    module = importlib.util.module_from_spec(spec)
    original_path = sys.path[:]
    previous = sys.modules.get("utils")
    try:
        # Local private helpers may import siblings. This is trusted executable
        # code, not an input document; its behavior is outside the public tests.
        sys.path.insert(0, str(path.parent))
        sys.modules["utils"] = module
        spec.loader.exec_module(module)
    except BaseException:
        if previous is None:
            sys.modules.pop("utils", None)
        else:
            sys.modules["utils"] = previous
        raise
    finally:
        sys.path[:] = original_path
    if not callable(getattr(module, "main", None)) or not callable(getattr(module, "configure", None)):
        raise IncompleteRun("The private runtime lacks its required entry-point contract.")
    if not isinstance(getattr(module, "OFFLINE_MISSING_REPLIES", None), list):
        raise IncompleteRun("The private runtime lacks its missing-replies status contract.")
    return module


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IncompleteRun("Guideline JSON contains a duplicate key; no audit ran.")
        result[key] = value
    return result


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if args.status:
        print(json.dumps({"distribution": "public-launcher-only", "pipeline_verified": False,
                          "private_runtime_included": False, "guidelines_to_check": GUIDELINES_TO_CHECK}, indent=2))
        return 0
    if args.no_data_testmode and not (args.validate and args.load_progress):
        cli.error("--no-data-testmode requires both --validate and --load-progress")
    try:
        path = runtime_path()  # Diagnose missing code before reading any policy/input.
        with Path(args.guideline_file).open(encoding="utf-8") as handle:
            sections = json.load(handle, object_pairs_hook=unique_object)
        if not isinstance(sections, dict) or any(
            not isinstance(sections.get(str(number)), str) or not sections[str(number)].strip()
            for number in GUIDELINES_TO_CHECK
        ):
            raise IncompleteRun("Guideline input is missing a non-empty text for a selected guideline.")
        utils = load_runtime(path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        policy_dir, summary_file, progress_dir = Path(args.policy_path), Path(args.policy_summary_file), Path(args.progress_path)
        progress_dir.mkdir(parents=True, exist_ok=True)
        utils.configure(args, timestamp, policy_dir, summary_file, progress_dir)
        results = []
        missing_result = False
        for number in GUIDELINES_TO_CHECK:
            print(f"Processing Guideline {number}")
            result = utils.main(number, sections)
            if result is None:
                missing_result = True
            else:
                results.append(result)
        if not results:
            raise IncompleteRun("No guideline produced results; no completed assessment or combined JSON was produced.")
        combined = results
        if args.load_progress:
            # Do not attest to private runtime network behavior from this flag.
            note = f"Replay requested from saved run {args.load_progress}; private-runtime provider activity is not independently verified by this launcher."
            if utils.OFFLINE_MISSING_REPLIES:
                note += " Some saved replies are missing; the assessment is incomplete."
            if args.validate:
                note += " Saved validation requested." if args.no_data_testmode else " Local revalidation requested."
            combined = {"note": note, "results": results}
        output = progress_dir / f"output_combined_{timestamp}.json"
        with output.open("x", encoding="utf-8") as handle:
            json.dump(combined, handle, ensure_ascii=False, indent=2)
        print(f"Wrote combined JSON: {output}")
        if missing_result or utils.OFFLINE_MISSING_REPLIES:
            raise IncompleteRun("The saved results are incomplete; inspect private-runtime evidence before use.")
        return 0
    except SystemExit:
        print("Private runtime terminated before launcher completion; assessment is incomplete.", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted; no completed assessment is claimed.", file=sys.stderr)
        return 130
    except IncompleteRun as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        # Private exceptions may contain policy text, credentials or prompts.
        print(f"Assessment failed ({type(error).__name__}); no completed assessment is claimed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

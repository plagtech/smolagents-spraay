"""Publish the three Spraay tools to the Hugging Face Hub (one Space per tool).

Log in first with `hf auth login` (or set HF_TOKEN), then:

    python scripts/push_to_hub.py --namespace <your-hf-username-or-org>
"""

import argparse

from smolagents_spraay import get_spraay_tools


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--namespace", required=True, help="Hugging Face username or organisation to publish under")
    parser.add_argument("--private", action="store_true", help="Create the repos as private")
    parser.add_argument("--dry-run", action="store_true", help="Only validate and print what would be pushed")
    args = parser.parse_args()

    for tool in get_spraay_tools():
        repo_id = f"{args.namespace}/{tool.name.replace('_', '-')}"
        tool.to_dict()  # raises if the tool is not Hub-compatible
        if args.dry_run:
            print(f"[dry run] would push {type(tool).__name__} -> {repo_id}")
            continue
        tool.push_to_hub(repo_id, commit_message="Upload Spraay batch payment tool", private=args.private or None)
        print(f"pushed {repo_id}: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main()

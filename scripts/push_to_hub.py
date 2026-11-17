"""Publish the three Spraay tools to the Hugging Face Hub (one Space per tool).

Log in first with `hf auth login` (or set HF_TOKEN), then:

    python scripts/push_to_hub.py --namespace <your-hf-username-or-org>

Each Space is created as a static Space, which is free on every account. smolagents would
otherwise create a Gradio Space, which needs a paid plan on free CPU hardware. `load_tool`
only downloads `tool.py`, so it works the same either way; the Space shows a small
index.html instead of a Gradio demo.
"""

import argparse
import html

from huggingface_hub import HfApi

from smolagents_spraay import get_spraay_tools

GITHUB_URL = "https://github.com/plagtech/smolagents-spraay"


def build_index_html(tool, repo_id: str) -> str:
    name = html.escape(tool.name)
    summary = html.escape(tool.description.split(". ")[0].rstrip(".") + ".")
    snippet = html.escape(f'from smolagents import load_tool\n\ntool = load_tool("{repo_id}", trust_remote_code=True)')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem;
         line-height: 1.5; color: #1a1a1a; background: #ffffff; }}
  pre {{ background: #f4f4f4; padding: 1rem; overflow-x: auto; }}
  .warning {{ border-left: 4px solid #c0392b; background: #fdf0ee; padding: 0.75rem 1rem; }}
</style>
</head>
<body>
<h1>{name}</h1>
<p>{summary}</p>
<p class="warning"><strong>This tool moves real funds.</strong> It signs transactions on Base with the
private key in <code>SPRAAY_PRIVATE_KEY</code>. Never add a private key as a secret on this Space.</p>
<h2>Load it</h2>
<pre><code>{snippet}</code></pre>
<p>Or install every Spraay tool with <code>pip install smolagents-spraay</code>.</p>
<p>Source and documentation: <a href="{GITHUB_URL}">{GITHUB_URL}</a></p>
</body>
</html>
"""


def publish(tool, namespace: str, private: bool = False) -> str:
    repo_id = f"{namespace}/{tool.name.replace('_', '-')}"
    api = HfApi()
    api.create_repo(repo_id, repo_type="space", space_sdk="static", exist_ok=True, private=private or None)
    tool.push_to_hub(repo_id, commit_message="Upload Spraay batch payment tool", private=private or None)
    api.upload_file(
        path_or_fileobj=build_index_html(tool, repo_id).encode(),
        path_in_repo="index.html",
        repo_id=repo_id,
        repo_type="space",
        commit_message="Add index page",
    )
    return repo_id


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--namespace", required=True, help="Hugging Face username or organisation to publish under")
    parser.add_argument("--private", action="store_true", help="Create the repos as private")
    parser.add_argument("--dry-run", action="store_true", help="Only validate and print what would be pushed")
    args = parser.parse_args()

    for tool in get_spraay_tools():
        repo_id = f"{args.namespace}/{tool.name.replace('_', '-')}"
        tool.to_dict()  # raises if the tool is not Hub-compatible
        build_index_html(tool, repo_id)
        if args.dry_run:
            print(f"[dry run] would push {type(tool).__name__} -> {repo_id} (static Space)")
            continue
        publish(tool, args.namespace, args.private)
        print(f"pushed {repo_id}: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main()

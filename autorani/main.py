import argparse
import sys
import subprocess
from .state_store import YAMLStore
from .crawler import Crawler
from .utils import domain_of
from .testgen import generate_pytest_file

def cmd_explore(args):
    store = YAMLStore()
    max_pages = store.get("crawl.max_pages", None)
    timeout = store.get("crawl.timeout_sec", 10)
    ua = store.get("crawl.user_agent", "AutoRaniTestBot/0.1")
    same_domain = store.get("crawl.same_domain_only", True)

    crawler = Crawler(
        args.url,
        max_pages=max_pages,
        timeout_sec=timeout,
        same_domain_only=same_domain,
        user_agent=ua,
    )
    print(f"[EXPLORE] Starting crawl at: {args.url}")
    results = crawler.crawl()
    print(f"[EXPLORE] Pages discovered: {len(results)}")

    # Save in-memory (available this run) and also stash last crawl into settings for reference
    store.crawl_results = results
    store.set("last_crawl.domain", domain_of(args.url))
    store.set("last_crawl.count", len(results))
    store.save()
    store.save_crawl()
    return store

def cmd_generate(args, store: YAMLStore | None):
    st = store or YAMLStore()
    if not st.crawl_results:
        st.load_crawl()
        if not st.crawl_results:
            print("[GENERATE] No saved crawl found; generating a single seed test.")

    output_dir = st.get("generate.output_dir", "tests/generated")
    file_prefix = st.get("generate.file_prefix", "test_generated_")
    include_prints = st.get("generate.include_prints", True)
    include_comments = st.get("generate.include_comments", True)
    link_assertions_max = int(st.get("generate.link_assertions_max", 10))
    link_match_strategy = (st.get("generate.link_match_strategy", "contains") or "contains").lower()

    domain = domain_of(args.url)
    target_pages = st.crawl_results or {args.url: {"status": 200, "title": "", "h1": "", "out_links": []}}

    fpath = generate_pytest_file(
        target_pages, output_dir, file_prefix,
        include_prints, include_comments, domain,
        link_assertions_max=link_assertions_max,
        link_match_strategy=link_match_strategy,
    )
    print(f"[GENERATE] Wrote tests to: {fpath}")


def cmd_run(args):
    # Run pytest on generated tests
    print("[RUN] Executing pytest on tests/generated ...")
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/generated"], check=False)
    sys.exit(proc.returncode)

def build_parser():
    p = argparse.ArgumentParser(prog="autorani.main", description="AQa: Explore site and generate pytest tests.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pe = sub.add_parser("explore", help="Crawl a site.")
    pe.add_argument("url", help="Starting URL (e.g., https://example.com)")
    pe.set_defaults(func=lambda a: cmd_explore(a))

    pg = sub.add_parser("generate", help="Generate pytest tests from last crawl.")
    pg.add_argument("url", help="Domain used to name the output file")
    pg.set_defaults(func=lambda a: cmd_generate(a, None))

    pr = sub.add_parser("run", help="Run pytest on generated tests.")
    pr.set_defaults(func=lambda a: cmd_run(a))

    return p

def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    # For two-step flows (explore -> generate), pass store forward to avoid re-reading
    if args.cmd == "explore":
        store = args.func(args)  # returns YAMLStore
        # If user immediately wants to generate too (common), do it here if they pass --and-generate
        # (Not adding the flag to keep it simple; user can run a second command.)
    else:
        args.func(args)

if __name__ == "__main__":
    main()

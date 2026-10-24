"""English copy for the facetmark site.

Every number here is copied from a document in ``docs/`` or from the output of a
command in this repository. Nothing is rounded in a flattering direction and
nothing is estimated. If a claim has no protocol behind it, it is not on the
site.
"""

from model_presets import provider_blocks

REPO = "https://github.com/88lin/facetmark"

EN = {
    "code": "en",
    "html_lang": "en",
    "other_code": "zh",
    "other_label": "\u4e2d\u6587",
    "other_title": "\u5207\u6362\u5230\u4e2d\u6587",
    "skip": "Skip to content",
    "copy": {"label": "copy", "done": "copied", "seealso": "See also"},
    "nav": {
        "home": "Overview",
        "quickstart": "Start",
        "guide": "Guide",
        "measured": "Measured",
        "gh": "GitHub",
    },
    "term_labels": {
        "hits": "hits",
        "found": "target at rank",
        "missed": "target not in the top 5",
        "content": "content-style query \u2014 you remember the words",
        "vague": "vague query \u2014 you remember the idea",
        "episodic": "episodic query \u2014 you remember when",
    },
    # ------------------------------------------------------------------ meta
    "meta": {
        "index": (
            "facetmark · Good things you saved. Find them again.",
            "Turn your browser bookmarks into a searchable personal library. Search by keywords, describe what "
            "you remember, or browse by date. Your library lives on the computer or server where you run "
            "facetmark.",
        ),
        "quickstart": (
            "facetmark · Quickstart",
            "From importing bookmarks to your first search, with a check at every step and separate guidance for "
            "local use and server administration.",
        ),
        "guide": (
            "facetmark · Command and API reference",
            "Find import formats, query syntax, pagination, HTTP APIs, integrations and settings by task. "
            "Complete the quickstart first, then return here for individual parameters.",
        ),
        "measured": (
            "facetmark · Evaluation methods and results",
            "The experiments, counterexamples and open questions behind retrieval defaults. Read each result with "
            "its dataset, protocol and sample limits; these numbers do not predict every library.",
        ),
    },
    # ---------------------------------------------------------------- footer
    "foot": {
        "cols": [
            (
                "Start here",
                [
                    ("Quickstart", "quickstart.html"),
                    ("Install", "guide.html#install"),
                    ("Get your bookmarks in", "guide.html#import"),
                    ("Model access", "guide.html#models"),
                    ("Build the index", "guide.html#index"),
                    ("Settings", "config.html"),
                    ("Troubleshooting", "guide.html#trouble"),
                ],
            ),
            (
                "Interfaces",
                [
                    ("The web page", "webui.html"),
                    ("The local page", "guide.html#webui"),
                    ("Command line", "guide.html#commands"),
                    ("HTTP API", "guide.html#serve"),
                    ("MCP server", "guide.html#mcp"),
                    ("Browser extension", "guide.html#extension"),
                    ("Connect other tools", "integrations.html"),
                    ("karakeep plugin", "guide.html#karakeep"),
                ],
            ),
            (
                "Evidence",
                [
                    ("Everything measured", "measured.html"),
                    ("Four-facet fusion", "measured.html#w1"),
                    ("The episodic gate", "measured.html#gate"),
                    ("The decay layer, twice", "measured.html#decay"),
                    ("What none of it measures", "measured.html#gaps"),
                ],
            ),
            (
                "Project",
                [
                    ("Source", REPO),
                    ("Releases", REPO + "/releases"),
                    ("Issues", REPO + "/issues"),
                    ("MIT licence", REPO + "/blob/main/LICENSE"),
                ],
            ),
        ],
        "bar": [
            "facetmark v@@VERSION@@ \u00b7 MIT",
            "Python 3.10+ \u00b7 one SQLite file",
            "No number on this site without a protocol behind it.",
        ],
    },
    # ----------------------------------------------------------------- index
    "index": {
        "kicker": "Local-first bookmark retrieval",
        "h1": "Good things you saved.<br><em>Find them again.</em>",
        "lede": (
            "Turn your browser bookmarks into a searchable personal library. Search by keywords, describe what "
            "you remember, or browse by date. Your library lives on the computer or server where you run "
            "facetmark."
        ),
        "cta": [("Get started", "quickstart.html", True), ("Explore the app", "webui.html", False)],
        "chips": [("Requires", "Python 3.10+"), ("Storage", "SQLite"), ("License", "MIT")],
        "term_title": "facetmark demo --size 60",
        "term_note": (
            "Real output from <code>facetmark demo</code>, which builds a "
            "60-page synthetic library offline. Provider is <code>mock</code>, "
            "so this is a plumbing check, not a quality measurement \u2014 the "
            "mock hashes text into vectors. The score column is not sorted "
            "because the rank comes from stage E and the score is the fusion "
            "score, which stage E deliberately does not overwrite."
        ),
        # --- problem
        "prob_label": "The problem",
        "prob_h2": "Start with what you remember",
        "prob_lede": (
            "You do not need a perfectly organised folder tree. Start with keywords, add an embedding model for "
            "searches in your own words, and use dates or related pages to narrow things down."
        ),
        "prob_cards": [
            (
                "content-style",
                "A few words",
                "Match words in titles, URLs and folders, including Chinese substrings.",
                "“sqlite vector index”",
                "0.959",
                "Recall@5",
                "good",
            ),
            (
                "vague",
                "An idea",
                "With an embedding model, describe the content you need. Results depend on your indexed text and "
                "model.",
                "“search that works without a connection”",
                "0.706",
                "Recall@5",
                "",
            ),
            (
                "episodic",
                "A moment",
                "Filter by save date, then explore other bookmarks saved in the same session.",
                "“database articles saved last month”",
                "0.279",
                "Recall@5",
                "bad",
            ),
        ],
        "prob_note": (
            'The retrieval methods and their limits are documented. <a href="measured.html">Read the evaluation '
            "methods and results</a>."
        ),
        # --- facets
        "fac_label": "How it works",
        "fac_h2": "See what matched",
        "fac_lede": (
            "Content vectors, generated questions, keywords and substrings offer different retrieval signals. "
            "With embeddings configured, the default uses content vectors, graph expansion and time decay. "
            "Compare other combinations in search options; lexical search remains available without a model."
        ),
        "fac_head": ["Facet", "What it indexes", "Answers", "Default"],
        "fac_rows": [
            (
                '<b>Lexical</b><br><span class="tiny">two FTS5 indexes</span>',
                "Character trigrams and word segments of the title, URL and body.",
                "Exact strings, identifiers, code, error messages, and Chinese "
                "text that has no spaces to tokenise on.",
                '<span class="badge warn">off</span><br>'
                '<span class="tiny">cost 5.4pp when fused</span>',
            ),
            (
                '<b>Content</b><br><span class="tiny">dense vector</span>',
                "An embedding of the extracted page body, not the title.",
                "Paraphrase. The idea you remember when the words are gone.",
                '<span class="badge pass">on</span><br><span class="tiny">W1 winner, 0.643</span>',
            ),
            (
                '<b>Intent</b><br><span class="tiny">generated queries</span>',
                "Candidate questions a model writes for the page, kept only if "
                "searching them actually retrieves the page back.",
                "Why you would come looking, phrased the way you would phrase it later.",
                '<span class="badge warn">off</span><br>'
                '<span class="tiny">38% of intents plausible</span>',
            ),
            (
                '<b>Context</b><br><span class="tiny">sessions and graph</span>',
                "Save-session clustering, domain structure, and a link graph over the library.",
                "\u201cWhat did I save around that one?\u201d",
                '<span class="badge pass">graph on</span> '
                '<span class="badge fail">gate off</span><br>'
                '<span class="tiny">+2.09pp / \u221218.83pp</span>',
            ),
        ],
        "fac_note": (
            "Every one of those four verdicts links to a protocol, a query "
            "set and a confidence interval on the "
            '<a href="measured.html">measured page</a>.'
        ),
        # --- pipeline
        "pipe_label": "The pipeline",
        "pipe_h2": "From a query to a ranked list",
        "pipe_lede": (
            "The coloured stages are what runs in the shipped default "
            "profile. The grey ones are built, tested and switched off. Every "
            "indexing stage is idempotent and fingerprinted, so "
            "<code>facetmark index</code> re-runs only the work whose input "
            "changed."
        ),
        "pipe_scroll": "Scroll the diagram sideways \u2192",
        "pipe_after": [
            (
                "Indexing",
                "<code>bookmark</code> \u2192 <code>fetch</code> \u2192 "
                "<code>content</code> \u2192 <code>enrich</code> (summary, "
                "topics, entities, key points) \u2192 <code>embed</code> \u2192 "
                "<code>intents</code> \u2192 filter \u2192 "
                "<code>sessions</code> \u2192 <code>edges</code>.",
            ),
            (
                "Fingerprints",
                "Enrichment is keyed on the body hash; embedding is keyed on "
                "the reconstructed embed text, so a vector that no longer "
                "matches its text is detected rather than trusted. "
                "<code>--force</code> ignores both.",
            ),
            (
                "Graph expansion",
                "One hop out from the fused hits, returned as a "
                "<em>separate group</em> rather than mixed into the ranking. "
                "Measured at +2.09pp, 10 wins and 0 losses, 9 ms.",
            ),
        ],
        # --- screenshots
        # --- the local page
        "app_label": "The page you open",
        "app_h2": "A place to pick up where you left off",
        "app_lede": (
            "Inspect result summaries and sources, synthesise an answer with citations, and check how much of "
            "your library has been fetched and indexed. The same interface works on desktop and mobile."
        ),
        "app_shot": (
            "assets/app-search.png",
            "facetmark search with results, snippets and matching sources. Synthetic example bookmarks.",
            "Search, inspect sources, keep reading · Demo library",
        ),
        "app_shot_dark": (
            "assets/app-search-dark.png",
            "the same search page in dark mode",
        ),
        "app_points": [
            (
                "It speaks a filter language",
                "<code>domain:github.com</code>, <code>tag:work</code>, "
                "<code>added:&lt;7d</code>, <code>-pinterest</code>, "
                "<code>sort:date</code> \u2014 in the same box, with "
                "completion for the field names <em>and</em> the values that "
                "exist in your library. A query that is only filters is a "
                "browse: no model call at all.",
            ),
            (
                "It pairs itself",
                "The token is fetched from a route that answers only when the "
                "caller <em>and</em> the address in the request are both "
                "loopback, so on your own machine there is nothing to copy. "
                "Anywhere else the page asks you to paste it once.",
            ),
            (
                "It says what is missing",
                "An empty library prints the import command. Bookmarks with "
                "no vectors print <code>facetmark index</code>. A search with "
                "no hits and a full fetch queue tells you that, instead of "
                "showing you an empty list and letting you guess.",
            ),
            (
                "English and \u4e2d\u6587",
                "One switch in the header, remembered between visits. Light, "
                "dark, or whatever your system is set to. <kbd>/</kbd> "
                "focuses the box, the arrow keys walk the results, "
                "<kbd>Esc</kbd> clears.",
            ),
        ],
        "app_cta": "Start from nothing \u2192",
        # --- extension
        "shot_label": "In the browser",
        "shot_h2": "An extension that talks to localhost and nothing else",
        "shot_lede": (
            "Manifest V3. Host permissions are "
            "<code>http://127.0.0.1:8787/*</code> and "
            "<code>http://localhost:8787/*</code>. It reaches your own "
            "machine, pairs with a token, and never writes to your browser's "
            "bookmark store."
        ),
        "shots": [
            (
                "assets/popup-mock.png",
                "facetmark popup showing grouped results",
                "<b>Popup.</b> Every result carries the facets that matched, "
                "and pages you saved in the same session arrive as their own "
                "group rather than shuffled into the ranking. This frame "
                "follows the theme of the page you are reading.",
            ),
            (
                "assets/options.png",
                "facetmark options page",
                "<b>Options.</b> Endpoint, pairing token, an optional second "
                "channel, and a pause switch. Four fields, no account.",
            ),
        ],
        "shot_dark": (
            "assets/popup-mock-dark.png",
            "the same popup in dark mode",
        ),
        "shot_dark_opts": (
            "assets/options-dark.png",
            "the same options page in dark mode",
        ),
        "shot_legend": (
            "What the markers on a row mean",
            [
                (
                    "chip",
                    "about",
                    "the <b>content</b> facet matched: a vector over the page "
                    "body. The one facet that is on by default.",
                ),
                (
                    "chip",
                    "asked as",
                    "the <b>intent</b> facet matched: vectors over questions "
                    "generated for the page. Off by default.",
                ),
                (
                    "chip",
                    "words",
                    "the <b>lexical \u00b7 segments</b> facet matched: FTS5 "
                    "over words. Off by default.",
                ),
                (
                    "chip",
                    "substring",
                    "the <b>lexical \u00b7 trigram</b> facet matched: FTS5 "
                    "over characters. Off by default.",
                ),
                (
                    "cold",
                    "cold",
                    "the link looks dead, so the row is demoted rather than "
                    "removed. <code>facetmark health</code> says why.",
                ),
                (
                    "group",
                    "saved around these",
                    "a second group, from one hop over session and semantic "
                    "edges. Never mixed into the ranking above it.",
                ),
            ],
        ),
        "shot_note": (
            "These are UI previews rendered against mock data, not screenshots "
            "of a real library \u2014 a real one would put somebody's browsing "
            "history on a public page."
        ),
        # --- measured
        "meas_label": "Evidence",
        "meas_h2": "Four features were measured and lost. They are off.",
        "meas_lede": (
            "The interesting part of this project is not the features that "
            "worked. It is the ones that were built, pre-registered, "
            "measured, and then turned off \u2014 including one that had "
            "already shipped."
        ),
        "meas_stats": [
            ("0.643", "Recall@5 on 479 real queries, one facet", "good"),
            ("\u22125.4pp", "what turning on all four facets cost", "bad"),
            ("\u221218.83pp", "what the shipped episodic gate cost", "bad"),
        ],
        "meas_bars_title": "W1 \u00b7 Recall@5 by rung, 479 queries, one real library",
        "meas_bars": [
            ("<b>A</b> content vector only", "0.643", 64.3, True),
            ("<b>B</b> + two lexical facets", "0.589", 58.9, False),
            ("<b>C</b> all four facets", "0.635", 63.5, False),
            ("<b>D</b> + context + graph", "0.639", 63.9, False),
        ],
        "meas_body": (
            "<p>Three criteria were registered before the run. All three "
            "failed. Fusion cost 5.4 percentage points of Recall@5 and made "
            "queries 3.5\u00d7 slower \u2014 148 ms at p50 became 526 ms. The "
            "four-facet default was withdrawn the same day.</p>"
            "<p>Two things did survive that run and are shipped: graph "
            "expansion as a separate result group (+2.09pp, 10 wins, 0 "
            "losses, p=0.0019) and the reranker on Recall@1 (+4.80pp, CI95 "
            "[+1.46, +8.35]).</p>"
            "<p>Then there is the episodic gate. It won its holdout "
            "(+3.09pp, 19 wins, 0 losses, p=3.8e\u22126) and shipped. A "
            "361-query probe set built afterwards to ask what it does when it "
            "fires on the <em>wrong</em> query answered "
            "<b>\u221218.83pp</b>, 3 wins against 71 losses. The default was "
            "reverted.</p>"
        ),
        "meas_cta": "Read all nine results \u2192",
        # --- quickstart
        "qs_label": "Quickstart",
        "qs_h2": "Start small. Build your library from there.",
        "qs_lede": (
            "Install with Python 3.10+, import your bookmarks, then open the app. The full tutorial covers "
            "models, indexing, local use and server access."
        ),
        "qs_code": (
            "python -m pip install facetmark\nfacetmark import\nfacetmark index --no-fetch\nfacetmark serve"
        ),
        "qs_steps": [
            "<b>On your computer.</b> Run the commands on the machine that holds your browser bookmarks.",
            "<b>On a server.</b> Export a bookmark file and transfer it to the server before importing.",
            "<b>Check the flow first.</b> <code>--no-fetch</code> skips page downloads; existing stored text can "
            "still be used.",
            "<b>Add content.</b> Configure a model and run <code>facetmark index</code>.",
            '<a href="quickstart.html">Follow the complete tutorial →</a>',
        ],
        "qs_offline": (
            "Just exploring? Run <code>facetmark demo</code> for a synthetic offline library. No API key required."
        ),
        # --- interfaces
        "if_label": "Interfaces",
        "if_h2": "Six ways in, one index",
        "if_cards": [
            (
                "web",
                "The local page",
                "<code>facetmark serve</code> hosts a search page at "
                "<code>/app</code>. Search and a library overview, English or "
                "Chinese, light or dark. The only interface that needs "
                "nothing installed beyond facetmark itself.",
                "guide.html#webui",
                "What is on it",
            ),
            (
                "cli",
                "Command line",
                "Twenty-one commands. <code>search</code> takes "
                "<code>--explain</code> to print which facet matched, and "
                "<code>--config</code> to run any ablation rung by name.",
                "guide.html#commands",
                "Command reference",
            ),
            (
                "http",
                "HTTP API",
                "<code>facetmark serve</code> binds 127.0.0.1:8787. "
                "Twenty-nine routes. Four are open \u2014 the root, health, "
                "and the two the local page needs to load itself; everything "
                "that touches the library requires a pairing token.",
                "guide.html#serve",
                "Routes and auth",
            ),
            (
                "mcp",
                "MCP server",
                "<code>facetmark mcp</code> speaks MCP over stdio. Nine tools "
                "and three resources, so Claude Desktop can search your "
                "library and read a saving session.",
                "guide.html#mcp",
                "Client config",
            ),
            (
                "ext",
                "Browser extension",
                "MV3. Omnibox keyword <code>fm</code>, "
                "<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>, one-click "
                "save with a local indexing queue.",
                "guide.html#extension",
                "Install and pair",
            ),
            (
                "kk",
                "karakeep plugin",
                "A search-provider plugin that puts facetmark behind "
                "karakeep's own search box. The wire contract is pinned by a "
                "replay test.",
                "guide.html#karakeep",
                "Wire it up",
            ),
        ],
        # --- faq
        "faq_label": "Questions",
        "faq_h2": "The six that actually get asked",
        "faq": [
            (
                "Where does my data go?",
                "<p>The library stays on the machine running the service. Fetching contacts saved websites; online "
                "models receive the relevant text and queries. Importing through a server deployment transfers your "
                "file to that server.</p><p>A local embedding model computes on that machine after its files are "
                "downloaded. Online chat calls depend on your configuration. facetmark provides no hosted accounts "
                "or central storage service.</p>",
            ),
            (
                "Will it touch my browser's bookmarks?",
                "<p>No. Import is a one-way read. The importer opens the profile's <code>Bookmarks</code> file or "
                "your exported HTML, reads it, and closes it. Nothing in the codebase writes to a browser "
                "profile.</p><p>Nothing is deleted on the facetmark side either. The decay layer demotes stale pages "
                "in the ranking; it never removes a row.</p>",
            ),
            (
                "Can I use it with no LLM at all?",
                "<p>Yes, and it will be worse, and it will tell you so. Without a model you keep both lexical facets "
                "and the whole session and domain graph. You lose the content facet — the one that measured best — "
                "and the intent facet.</p><p>A middle path: run a local embedding model for the content facet and "
                "skip the chat model. You lose enrichment summaries and generated intents, keep paraphrase "
                "search.</p>",
            ),
            (
                "What does indexing cost?",
                "<p>Cost depends on page count, text length, model and provider pricing. Validate the connection and "
                "results with a small import before processing your full library.</p><p>Fetching also depends on "
                "site response times, access restrictions and per-domain rate limits. Later runs reuse unchanged "
                "stages; stored vectors and fetched page bodies are separate states.</p>",
            ),
            (
                "Why is the default only using one facet?",
                "<p>Because four-facet fusion was measured on 479 real queries and came out 5.4 points of Recall@5 "
                "<em>behind</em> the content facet on its own, at 3.5× the latency.</p><p>The mechanism is written "
                "up: flat-weight RRF lets a coincidence on two weak facets (0.0279) outvote confidence on one strong "
                "facet (0.0164). The facets still exist and are still tested. <code>--config C</code> turns them all "
                "on if you want to see it for yourself.</p>",
            ),
            (
                "Who is it for?",
                "<p>For people who want to manage their own bookmark data, rediscover saved material and run a local "
                "or self-hosted tool. CLI, HTTP API and MCP interfaces connect it to existing "
                "workflows.</p><p>Public evaluation queries were written by the project author. Check the results on "
                "your own bookmarks; one dataset is not a quality guarantee.</p>",
            ),
        ],
        # --- boundaries
        "bnd_label": "Boundaries",
        "bnd_h2": "What this thing refuses to do",
        "bnd": [
            (
                "Read-only on your browser",
                "Import never writes back. Your folder tree is yours.",
            ),
            (
                "Nothing is deleted",
                "The cold layer demotes. It does not remove rows, and "
                "<code>facetmark health</code> shows you what it considers "
                "dead and why.",
            ),
            (
                "Local first",
                "One SQLite file you can open with any SQLite browser. If you "
                "stop using facetmark your data is still readable.",
            ),
            (
                "Polite by default",
                "robots.txt is honoured, per-domain concurrency is capped at "
                "2, there is a minimum interval between hits on one host, and "
                "the user agent says what it is.",
            ),
            (
                "No number without a protocol",
                "And no default change without a query set that was frozen before the run.",
            ),
        ],
        # --- final cta
        "end_h2": "Put your saved pages to work",
        "end_p": (
            "Start with a small set of bookmarks. Once your first search works, add models and integrations as "
            "you need them."
        ),
        "end_cta": [
            ("Read the quickstart", "quickstart.html", True),
            ("View source", "https://github.com/88lin/facetmark", False),
        ],
    },
}


# ----------------------------------------------------------- quickstart ----

EN["quickstart"] = {
    "h1": "Quickstart",
    "lede": (
        "From importing bookmarks to your first search, with a check at every step and separate guidance for "
        "local use and server administration."
    ),
    "toc_title": "On this page",
    "sections": [
        (
            "install",
            "Install and verify",
            [
                (
                    "p",
                    "Use Python 3.10 or later on Windows, macOS or Linux. Run the commands in a terminal; use "
                    "<code>python3</code> if <code>python</code> is unavailable.",
                ),
                (
                    "cb",
                    "shell",
                    "python --version\npython -m pip install facetmark\nfacetmark --version",
                ),
                (
                    "callout",
                    "",
                    "Check the result",
                    "<p>The last command should print a version. If the executable is not found, try <code>python -m "
                    "facetmark --version</code>; the module entry point also accepts the commands below.</p>",
                ),
            ],
        ),
        (
            "import",
            "Import bookmarks",
            [
                (
                    "p",
                    "On your own computer, import directly from a Chromium-based browser. Close the browser first, "
                    "then run:",
                ),
                ("cb", "shell", "facetmark import"),
                (
                    "p",
                    "For Firefox, Safari or a server deployment, export bookmark HTML and place it on the machine "
                    "running facetmark. Keep quotes around paths containing spaces.",
                ),
                ("cb", "shell", 'facetmark import "bookmarks.html"\nfacetmark stats'),
                (
                    "callout",
                    "",
                    "Check the result",
                    "<p>Import reports inserted, updated and skipped entries; <code>stats</code> should show a "
                    "non-zero bookmark count. Your original browser bookmarks are unchanged. If no browser profile is "
                    "found, use an HTML export.</p>",
                ),
            ],
        ),
        (
            "model",
            "Choose how to search",
            [
                (
                    "p",
                    "Keyword search works without a model. Add an online or local embedding model when you want to "
                    "search by meaning.",
                ),
                ("h3", "Online models"),
                (
                    "p",
                    "Create a <code>.env</code> file in the working directory used to run the commands. This example "
                    "uses an OpenAI-compatible endpoint; model names must match your provider.",
                ),
                (
                    "cb",
                    "dotenv",
                    "FACETMARK_BASE_URL=https://api.openai.com/v1\n"
                    "FACETMARK_API_KEY=sk-your-key\n"
                    "FACETMARK_CHAT_MODEL=gpt-6-luna\n"
                    "FACETMARK_EMBED_MODEL=text-embedding-3-small\n"
                    "FACETMARK_EMBED_DIM=1536",
                ),
                (
                    "callout",
                    "",
                    "Check capabilities and data flow",
                    "<p>Chat and embeddings are separate capabilities. Online models receive relevant text and "
                    "queries. Use Settings → Test connection to verify both before processing the full library.</p>",
                ),
                ("h3", "Local embeddings"),
                ("cb", "shell", 'python -m pip install "facetmark[local]"'),
                (
                    "p",
                    "Use the following settings in <code>.env</code>. The first run downloads model files; once "
                    "available, embeddings are computed on the machine running the service.",
                ),
                (
                    "cb",
                    "dotenv",
                    "FACETMARK_EMBED_BACKEND=local\nFACETMARK_LOCAL_EMBED_PATH=BAAI/bge-m3\nFACETMARK_EMBED_MODEL=BAAI/bge-m3\nFACETMARK_EMBED_DIM=1024",
                ),
                (
                    "p",
                    '<a href="config.html">Configuration, precedence and provider examples →</a>',
                ),
            ],
        ),
        (
            "index",
            "Build the index",
            [
                ("cb", "shell", "facetmark index\nfacetmark stats"),
                (
                    "p",
                    "Indexing fetches pages, prepares summaries and vectors, and builds sessions and links. The stages "
                    "depend on your model settings. Fetching respects site limits; a large library can take time.",
                ),
                (
                    "callout",
                    "",
                    "Check both text and vectors",
                    "<p>Check text coverage and content-vector counts in Library. A vector count does not mean every "
                    "page body was fetched; title-only bookmarks can also have derived indexes.</p>",
                ),
                (
                    "p",
                    "To check the flow first, use <code>facetmark index --no-fetch</code> to skip downloads. Run "
                    "<code>facetmark index</code> later to fetch content; unchanged stages are reused.",
                ),
            ],
        ),
        (
            "open",
            "Open the app and search",
            [
                ("cb", "shell", "facetmark serve"),
                (
                    "p",
                    "Keep the terminal running and open <a "
                    'href="http://127.0.0.1:8787/app">http://127.0.0.1:8787/app</a> on the same computer. Use the port '
                    "printed in the terminal. Try a word you know appears in a saved title before testing descriptive "
                    "searches.",
                ),
                (
                    "shot",
                    "assets/app-search.png",
                    "the facetmark search page showing ranked results and a separate group of pages saved in the same "
                    "sitting",
                    "<b>Search.</b> The first paint is lexical and costs no model call; the ranked answer replaces it "
                    "when it arrives. Pages you saved in the same sitting arrive as their own group rather than "
                    "shuffled into the ranking. This frame follows the theme of the page you are reading.",
                    "assets/app-search-dark.png",
                    "the same search page in dark mode",
                ),
                ("p", '<a href="webui.html">Continue with search, synthesis and Library →</a>'),
            ],
        ),
        (
            "server",
            "Server access and administration",
            [
                (
                    "p",
                    "Run commands on the server that holds the library. <code>127.0.0.1</code> on your laptop refers "
                    "to that laptop, not the server. The app at a public hostname requires a pairing token.",
                ),
                ("cb", "shell", "facetmark token"),
                (
                    "p",
                    "Run this on the server and enter the token in your own app pairing form. It grants access to the "
                    "library; keep it private. Settings, imports and indexing also require a loopback connection. Use "
                    "SSH forwarding for remote administration.",
                ),
                ("cb", "shell", "ssh -N -L 8788:127.0.0.1:8787 your-user@your-server"),
                (
                    "callout",
                    "",
                    "Administration address",
                    "<p>Replace the username and server address, keep the SSH command running on your computer, then "
                    "open <code>http://127.0.0.1:8788/app</code>. If administration is still unavailable, check "
                    "whether the server sets <code>FACETMARK_ADMIN_API=false</code>.</p>",
                ),
            ],
        ),
        (
            "read",
            "Understand results and sources",
            [
                (
                    "p",
                    "Result badges identify matching signals. “Questions this page may answer” in details are "
                    "model-generated, not search history. A summary can be inferred from a title; the interface labels "
                    "that case.",
                ),
                (
                    "ul",
                    [
                        "Default: content vectors, graph expansion and time decay when embeddings are available.",
                        "Search options: compare other retrieval combinations; some add model calls.",
                        "Related results: shown separately from ranked matches for further browsing.",
                        "Synthesis: answers use stored summaries or snippets. Citations help trace sources; verify the "
                        "original text.",
                    ],
                ),
            ],
        ),
        (
            "trouble",
            "Troubleshooting",
            [
                (
                    "table",
                    ["Symptom", "Next step"],
                    [
                        [
                            "Cannot open the app",
                            "Confirm serve is running. If the port is occupied, run <code>facetmark serve --port 8788</code> "
                            "and use that port.",
                        ],
                        [
                            "Pairing prompt / 401",
                            "Run <code>facetmark token</code> on the service machine and pair again.",
                        ],
                        [
                            "Settings unavailable / 403",
                            "Use a loopback address or the SSH tunnel above; a token does not remove administration "
                            "restrictions.",
                        ],
                        [
                            "Keywords work, paraphrases do not",
                            "Check the embedding connection, dimensions and content-vector count, then index again.",
                        ],
                        [
                            "Provider returns 404 / 429",
                            "404: verify the full provider base URL and model name. 429: reduce concurrency and follow "
                            "provider retry guidance.",
                        ],
                    ],
                ),
                ("cb", "shell", "facetmark doctor\nfacetmark stats"),
                (
                    "p",
                    "If it still fails, record the version, steps and redacted error. <a "
                    'href="guide.html#trouble">Read the troubleshooting reference</a>.',
                ),
            ],
        ),
    ],
}

# ---------------------------------------------------------------- guide ----

EN["guide"] = {
    "h1": "Command and API reference",
    "lede": (
        "Find import formats, query syntax, pagination, HTTP APIs, integrations and settings by task. "
        "Complete the quickstart first, then return here for individual parameters."
    ),
    "toc_title": "On this page",
    "sections": [
        (
            "install",
            "Install",
            [
                (
                    "p",
                    "Python 3.10 or newer, on Windows, macOS or Linux. The base install has no compiled "
                    "machine-learning dependency; vector search comes from <code>sqlite-vec</code>, which is a SQLite "
                    "extension.",
                ),
                (
                    "cb",
                    "shell",
                    "pip install facetmark\n# or, if you use uv:\nuv pip install facetmark\n\nfacetmark version",
                ),
                ("h3", "With local embeddings"),
                (
                    "p",
                    "Only needed if you want to embed pages on your own machine instead of through an endpoint. This "
                    "pulls in PyTorch and <code>sentence-transformers</code>, which is a few hundred megabytes.",
                ),
                ("cb", "shell", 'pip install "facetmark[local]"'),
                ("h3", "From source"),
                (
                    "cb",
                    "shell",
                    "git clone https://github.com/88lin/facetmark\n"
                    "cd facetmark\n"
                    "python -m venv .venv && . .venv/bin/activate\n"
                    'pip install -e ".[dev]"\n'
                    "\n"
                    "pytest -q                 # 1,700+ tests\n"
                    "ruff check src tests scripts",
                ),
                (
                    "callout",
                    "warn",
                    "Do not reformat the codebase",
                    "<p>It is hand-formatted. <code>ruff check</code> is part of CI; <code>ruff format</code> is not, "
                    "and running it produces a diff nobody wants to review.</p>",
                ),
                ("h3", "Where your data lives"),
                (
                    "p",
                    "One directory, chosen per platform, holding one SQLite file. Override it with "
                    "<code>FACETMARK_DATA_DIR</code>, or point any command at a specific file with <code>--db</code>.",
                ),
                (
                    "table",
                    ["Platform", "Default data directory"],
                    [
                        ["Windows", "<code>%LOCALAPPDATA%\\facetmark\\</code>"],
                        ["Linux / macOS", "<code>~/.local/share/facetmark/</code>"],
                        [
                            "Any, if <code>XDG_DATA_HOME</code> is set",
                            "<code>$XDG_DATA_HOME/facetmark/</code>",
                        ],
                    ],
                ),
                (
                    "p",
                    "The data directory holds the database, pairing token and optional configuration. Back up the "
                    "database and secrets separately; confirm paths with <code>facetmark stats</code> and "
                    "<code>facetmark config path</code>.",
                ),
                ("h3", "Try it with no key and no network"),
                (
                    "p",
                    "<code>facetmark demo</code> generates a synthetic library, indexes it with a deterministic "
                    "offline provider, and runs three searches against it. It is how the terminal on the front page "
                    "was recorded.",
                ),
                ("cb", "shell", "facetmark demo --size 60"),
            ],
        ),
        (
            "import",
            "Get your bookmarks in",
            [
                (
                    "p",
                    "Import is one-way and read-only. facetmark reads a browser profile or an exported file, and never "
                    "writes to either.",
                ),
                ("h3", "Chromium-family: no export needed"),
                (
                    "p",
                    "Chrome, Edge, Brave, Vivaldi, Chromium, Opera and Opera GX all keep bookmarks in a JSON file that "
                    "facetmark can find on its own. Reading it is safe while the browser is running.",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark browsers        # what it can see\n"
                    "facetmark import          # import, if there is exactly one",
                ),
                (
                    "p",
                    "If more than one profile is installed, the choice is not guessed — importing the wrong person's "
                    "bookmarks is worse than one extra command. The candidates are printed and you pass the one you "
                    "want:",
                ),
                ("cb", "shell", 'facetmark import "$HOME/.config/google-chrome/Default/Bookmarks"'),
                ("h3", "Firefox and Safari: export to HTML first"),
                (
                    "table",
                    ["Browser", "Where the export lives"],
                    [
                        [
                            "Firefox",
                            "Bookmarks → Manage Bookmarks → Import and Backup → <b>Export Bookmarks to HTML</b>",
                        ],
                        ["Safari", "File → Export → <b>Bookmarks</b>"],
                        [
                            "Chrome / Edge (manual route)",
                            "<code>chrome://bookmarks</code> → ⋮ → <b>Export bookmarks</b>",
                        ],
                        [
                            "Anything else",
                            "Any Netscape-format <code>bookmarks.html</code> works. It is a 1994 format and everyone still "
                            "writes it.",
                        ],
                    ],
                ),
                ("cb", "shell", "facetmark import ~/Downloads/bookmarks.html"),
                ("h3", "What import reports"),
                (
                    "p",
                    "The same command handles Netscape HTML and Chrome JSON, and prints what it did rather than a "
                    "spinner. On one real 1.7&nbsp;MB export with 96 folders nested four deep, it parsed 1,710 "
                    "entries, inserted 1,701, merged 9 duplicates and skipped 1 as non-indexable.",
                ),
                (
                    "table",
                    ["Field", "Meaning"],
                    [
                        ["<code>parsed</code>", "Entries found in the file."],
                        [
                            "<code>inserted</code> / <code>updated</code>",
                            "New rows, and existing rows whose title or folder changed.",
                        ],
                        [
                            "<code>merged_duplicates</code>",
                            "Same URL saved twice; the earlier timestamp wins.",
                        ],
                        [
                            "<code>non_indexable</code>",
                            "<code>javascript:</code>, <code>place:</code>, <code>file:</code> and friends.",
                        ],
                        [
                            "<code>missing_dates</code>",
                            "Entries with no save time. They still import, but they cannot join a saving session.",
                        ],
                        [
                            "<code>privacy_skipped</code>",
                            "Skipped by <code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code>.",
                        ],
                        [
                            "<code>timestamp_unit</code>",
                            "Which epoch the source used. Chrome and Netscape disagree; this says which one was detected.",
                        ],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "Exclude domains before you import",
                    "<p>Set <code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code> to a comma-separated list and those hosts "
                    "are never inserted, never fetched and never embedded. Easier than deleting rows "
                    "afterwards.</p>",
                ),
            ],
        ),
        (
            "models",
            "Model access",
            [
                (
                    "p",
                    "Online models share one OpenAI-compatible <code>base_url</code> and <code>api_key</code>. Verify "
                    "that the endpoint supports the chat and embedding capabilities you need. A compatible gateway, "
                    "self-hosted service or local embedding backend can cover missing capabilities.",
                ),
                (
                    "p",
                    "The chat model generates summaries, topics, entities, key points and candidate questions. The "
                    "embedding model converts page text and queries into vectors. Some derived content may be inferred "
                    "from titles when bodies are missing.",
                ),
                ("h3", "Through an endpoint"),
                (
                    "cb",
                    "shell",
                    "export FACETMARK_API_KEY=sk-...\n"
                    "export FACETMARK_BASE_URL=https://api.openai.com/v1\n"
                    "export FACETMARK_CHAT_MODEL=gpt-6-luna\n"
                    "export FACETMARK_EMBED_MODEL=text-embedding-3-small\n"
                    "export FACETMARK_EMBED_DIM=1536",
                ),
                (
                    "callout",
                    "warn",
                    "Use the provider API base path",
                    "<p>This is the single most common setup failure. A base URL without <code>/v1</code> produces a "
                    "404 on every call, including the first one, and the error comes from the provider rather than "
                    "from facetmark so it reads as a credentials problem.</p>",
                ),
                (
                    "p",
                    "Instead of environment variables you can drop a <code>.env</code> file next to where you run the "
                    "command. Same names, same prefix.",
                ),
                (
                    "cb",
                    "dotenv",
                    "FACETMARK_API_KEY=sk-...\n"
                    "FACETMARK_BASE_URL=https://api.deepseek.com/v1\n"
                    "FACETMARK_CHAT_MODEL=deepseek-flash",
                ),
                ("h3", "Shared or free endpoints"),
                (
                    "p",
                    "Fallback chat models are tried in the configured order. Check that each is available on your "
                    "account and endpoint; a fallback chain should not conceal incorrect endpoints or permissions.",
                ),
                ("cb", "shell", "export FACETMARK_CHAT_MODEL_FALLBACKS=deepseek-flash,deepseek-v4-pro"),
                (
                    "p",
                    "The provider records which model actually answered each call. Any report built on a failover "
                    "chain has to publish that mix.",
                ),
                ("h3", "Local embeddings, no key"),
                (
                    "p",
                    "Local embeddings use <code>sentence-transformers</code>. After downloading the model, computation "
                    "runs on the service machine; page fetching still contacts websites. If online chat is configured, "
                    "summaries and synthesis may still call that provider.",
                ),
                (
                    "cb",
                    "shell",
                    'pip install "facetmark[local]"\n'
                    "\n"
                    "export FACETMARK_EMBED_BACKEND=local\n"
                    "export FACETMARK_EMBED_MODEL=bge-m3\n"
                    "export FACETMARK_EMBED_DIM=1024\n"
                    "export FACETMARK_LOCAL_EMBED_PATH=BAAI/bge-m3   # or a local model directory\n"
                    "export FACETMARK_LOCAL_EMBED_MAX_SEQ=1024",
                ),
                (
                    "callout",
                    "info",
                    "Why the sequence length default is 1024",
                    "<p>Embedding the same document twice must land in the same place. On bge-m3 at 1024 tokens, the "
                    "minimum self-cosine over a fixed 64-document probe set is <b>0.999976</b> with 64 of 64 documents "
                    "matching themselves. At 512 tokens the minimum falls to <b>0.9769</b>, because truncation starts "
                    "cutting different amounts off the same text. That is why 1024 is the default and why lowering it "
                    "is a real trade.</p>",
                ),
                (
                    "callout",
                    "bad",
                    "Changing the dimension invalidates everything",
                    "<p><code>FACETMARK_EMBED_DIM</code> is recorded in the <code>meta</code> table on the first index "
                    "build. A later mismatch raises instead of silently mixing incompatible vectors. If you change "
                    "embedding model or dimension, re-embed with <code>facetmark index --force</code>.</p>",
                ),
                ("h3", "No model at all"),
                (
                    "p",
                    "Everything still installs and runs. You keep both lexical facets, saving sessions, the domain and "
                    "link graph, and link health. You lose the content facet and the intent facet. <code>facetmark "
                    "search --quick</code> is the explicit lexical-only path and makes no model call.",
                ),
            ],
        ),
        (
            "index",
            "Build the index",
            [
                ("cb", "shell", "facetmark index"),
                (
                    "p",
                    "Indexing runs in stages and reuses completed work by input fingerprint. New bookmarks or changes "
                    "to text and model settings can require stages to run again; check the actual job output.",
                ),
                (
                    "table",
                    ["Stage", "What it does", "Needs a model?"],
                    [
                        [
                            "<code>fetch</code>",
                            "Downloads each page, honouring robots.txt and per-domain rate limits. Extracts a readable body.",
                            "no",
                        ],
                        [
                            "<code>enrich</code>",
                            "Summary, topics, entities, key points — one small chat call per page.",
                            "chat",
                        ],
                        [
                            "<code>embed_content</code>",
                            "Embeds the reconstructed text of each page.",
                            "embedding",
                        ],
                        [
                            "<code>intents</code>",
                            "Generates candidate queries for each page.",
                            "chat",
                        ],
                        [
                            "<code>filter_intents</code>",
                            "Keeps an intent only if searching it retrieves the page back. Typically a little under half "
                            "survive.",
                            "no",
                        ],
                        [
                            "<code>embed_intents</code>",
                            "Embeds the surviving intents.",
                            "embedding",
                        ],
                        [
                            "<code>sessions</code>",
                            "Clusters saves into episodes by time gap, choosing the gap by coverage × purity lift against a "
                            "shuffled control.",
                            "no",
                        ],
                        [
                            "<code>edges</code>",
                            "Builds session, semantic, same-domain and supersession edges.",
                            "no",
                        ],
                    ],
                ),
                ("h3", "Useful flags"),
                (
                    "table",
                    ["Flag", "Effect"],
                    [
                        [
                            "<code>--no-fetch</code>",
                            "Skip crawling entirely and index titles only. Seconds instead of hours; much weaker results.",
                        ],
                        [
                            "<code>--limit N</code>",
                            "Cap bookmarks per stage. Good for a first look at what a run will cost.",
                        ],
                        ["<code>--force</code>", "Ignore fingerprints and redo work already done."],
                        [
                            "<code>--mock</code>",
                            "Deterministic offline provider. No key, no network, no quality.",
                        ],
                        [
                            "<code>--json</code>",
                            "Machine-readable report of every stage, including per-stage seconds.",
                        ],
                    ],
                ),
                ("h3", "How fingerprints work"),
                (
                    "ul",
                    [
                        "<b>Enrichment</b> is keyed on the hash of the page body. Same body, no second chat call.",
                        "<b>Embedding</b> is keyed on the <em>reconstructed embed text</em>, not on the body. So if "
                        "enrichment changes and the embed text changes with it, the stale vector is detected rather than "
                        "trusted — which is how the karakeep round-trip damage was caught.",
                        "<b>Sessions and edges</b> are rebuilt from scratch each run; they are cheap and depend on the "
                        "whole library.",
                    ],
                ),
                (
                    "p",
                    "<code>facetmark reindex</code> throws away every derived artefact and rebuilds from the bookmarks "
                    "themselves. <code>facetmark migrate</code> brings an older database up to the current schema, "
                    "taking a snapshot first unless you pass <code>--no-backup</code>.",
                ),
                ("h3", "What indexing costs"),
                (
                    "p",
                    "Cost depends on text length, models and provider pricing; start with a small sample. Fetching and "
                    "site rate limits also affect duration. The default per-host concurrency is 2, with an interval "
                    "between requests.",
                ),
                (
                    "p",
                    "For a sense of scale: that real 1,700-bookmark library, indexed with <code>--no-fetch</code>, "
                    "produced 322 saving sessions, 9,132 edges, 1,386 distinct domains and 1,775 vectors.",
                ),
            ],
        ),
        (
            "search",
            "Search",
            [
                (
                    "cb",
                    "shell",
                    'facetmark search "the post about keeping vectors in sqlite"\n'
                    'facetmark search "sqlite-vec" -n 20 --explain\n'
                    'facetmark search "error EADDRINUSE" --quick',
                ),
                (
                    "table",
                    ["Flag", "Effect"],
                    [
                        ["<code>-n, --limit</code>", "Results to return. Default 10."],
                        [
                            "<code>--quick</code>",
                            "Lexical only. No model call, no network, sub-millisecond.",
                        ],
                        [
                            "<code>--explain</code>",
                            "Print which facet matched each hit. The fastest way to understand why something ranked where it "
                            "did.",
                        ],
                        [
                            "<code>--config NAME</code>",
                            "Run a specific profile or ablation rung. Default <code>full</code>.",
                        ],
                        ["<code>--json</code>", "Machine-readable, including timings per stage."],
                    ],
                ),
                ("h3", "Profiles and rungs"),
                (
                    "p",
                    "<code>--config</code> accepts any pre-registered rung, any shipped profile, and about twenty "
                    "exploratory ablations. <code>facetmark eval --help</code> documents the rung syntax; the rungs "
                    "themselves are listed in <code>search/pipeline.py</code>.",
                ),
                (
                    "table",
                    ["Name", "Facets and stages", "Status"],
                    [
                        [
                            "<code>A</code>",
                            "content vector only",
                            '<span class="badge pass">W1 winner · 0.643</span>',
                        ],
                        [
                            "<code>B</code>",
                            "content + both lexical facets",
                            '<span class="badge fail">−5.4pp</span>',
                        ],
                        ["<code>C</code>", "all four facets", "measured"],
                        ["<code>D</code>", "all four + context + graph", "measured"],
                        ["<code>E</code>", "all four + context + graph + rerank", "measured"],
                        [
                            "<code>full</code>",
                            "content + graph + decay",
                            '<span class="badge info">default, real provider</span>',
                        ],
                        [
                            "<code>fused</code>",
                            "all four + context + graph + rerank + decay",
                            '<span class="badge info">default, mock provider</span>',
                        ],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "Why the mock provider gets a different default",
                    "<p>The mock hashes text into a vector, so the content facet — the one that wins outright on a "
                    "real library — is exactly the one that returns noise on a mock one. Dropping the lexical facets "
                    "there would leave the deployment with nothing that works. Real embeddings get the measurement's "
                    "answer; everyone else gets the pre-gate behaviour, which at least retrieves by words.</p>",
                ),
                ("h3", "What the ranking is made of"),
                (
                    "p",
                    "Selected facets each return up to <code>CANDIDATES_PER_FACET</code> hits. Reciprocal rank fusion "
                    "combines them as <code>sum_f w_f / (k + rank_f)</code> with <code>k = 60</code>. Then context, "
                    "decay and rerank run in that order, and one-hop graph expansion is returned as a <em>separate "
                    "group</em> — not mixed into the ranking, because it was measured as an addition, not a "
                    "replacement.",
                ),
                (
                    "callout",
                    "warn",
                    "The rank column and the score column disagree",
                    "<p>By design. The reranker reorders the top 20 but deliberately preserves the fused score on each "
                    "hit, so a reordered list shows scores out of order. If it overwrote them you could no longer see "
                    "what fusion thought.</p>",
                ),
                ("h3", "Reading a saving session"),
                (
                    "cb",
                    "shell",
                    "facetmark sessions -n 20     # recent saving episodes\n"
                    "facetmark show 412 --body    # one bookmark as JSON\n"
                    "facetmark stats              # index size and coverage",
                ),
            ],
        ),
        (
            "query",
            "The query language",
            [
                (
                    "p",
                    "Every search surface takes the same grammar: the web box, <code>facetmark search</code>, "
                    "<code>/search</code> and <code>/quick</code>, the MCP tools, the karakeep plugin. It is a "
                    "<em>filter</em> language, not a second ranker — a filter decides which pages are eligible and "
                    "never moves a surviving page's score. Full reference: <a "
                    'href="https://github.com/88lin/facetmark/blob/main/docs/query-language.md">docs/query-language.md</a>.',
                ),
                (
                    "cb",
                    "shell",
                    'facetmark search "postgres domain:github.com -title:tutorial"\n'
                    'facetmark search "kafka added:<7d"          # saved this week\n'
                    "facetmark search 'title:encryption (signal|matrix)'\n"
                    'facetmark search "tag:work sort:date"       # a browse, newest first',
                ),
                (
                    "table",
                    ["Field", "Matches", "Example"],
                    [
                        [
                            '<code>domain:</code> <span class="tiny">alias <code>site:</code></span>',
                            "the site, exact or wildcard",
                            "<code>domain:github.com</code>",
                        ],
                        [
                            "<code>host:</code>",
                            "the full hostname",
                            "<code>host:news.ycombinator.com</code>",
                        ],
                        ["<code>url:</code>", "part of the address", "<code>url:*/docs/*</code>"],
                        [
                            "<code>title:</code>",
                            "words in the title only",
                            "<code>title:encryption</code>",
                        ],
                        [
                            "<code>text:</code>",
                            "words in the fetched page body",
                            '<code>text:"GDPR compliance"</code>',
                        ],
                        [
                            "<code>folder:</code>",
                            "the browser folder it came from",
                            "<code>folder:study</code>",
                        ],
                        [
                            "<code>tag:</code>",
                            "one of your own tags, exactly",
                            "<code>tag:work</code>",
                        ],
                        [
                            "<code>topic:</code>",
                            "a topic the enrichment wrote",
                            "<code>topic:postgres</code>",
                        ],
                        [
                            "<code>lang:</code>",
                            "the detected page language",
                            "<code>lang:zh</code>",
                        ],
                        [
                            "<code>opened:</code>",
                            "how many times you opened it",
                            "<code>opened:10..</code>",
                        ],
                    ],
                ),
                ("h3", "Negation, phrases, alternation, wildcards"),
                (
                    "cb",
                    "shell",
                    "-facebook                    exclude a word\n"
                    "-domain:pinterest.com        exclude a whole site\n"
                    '"consumer group rebalancing"  an exact phrase\n'
                    "(security|privacy)           either word\n"
                    "domain:(github.com|gitlab.com)   either value\n"
                    "domain:*.github.io           * is any run of characters",
                ),
                ("h3", "Dates"),
                (
                    "p",
                    "A <em>duration</em> compares against the age of the bookmark, so <code>added:&gt;90d</code> means "
                    "older than 90 days. An <em>absolute date</em> compares against the timestamp directly, so "
                    "<code>added:&gt;=2026-04-01</code> means on or after that day. The two read in opposite "
                    "directions because both readings are the obvious one for their own form.",
                ),
                (
                    "table",
                    ["Written", "Means"],
                    [
                        ["<code>added:&lt;7d</code>", "saved in the last week"],
                        ["<code>added:&gt;90d</code>", "older than 90 days"],
                        ["<code>added:2026-04</code>", "saved that month"],
                        ["<code>added:2026-04-01..2026-09-01</code>", "an explicit range"],
                        [
                            "<code>before:2026-05-01</code> <code>after:30d</code>",
                            "aliases of <code>added:</code>; a duration on these two is an age, so <code>after:30d</code> is "
                            "the last 30 days",
                        ],
                    ],
                ),
                ("h3", "Sorting, and what a browse is"),
                (
                    "p",
                    "<code>sort:date</code> puts newest saves first; <code>sort:-date</code> puts oldest first. "
                    "<code>title</code>, <code>domain</code>, <code>url</code> and <code>opened</code> are also "
                    "supported. With filters or sorting but no free text, the query browses bookmarks without model "
                    "calls. Lexical and local embedding search also avoid online embedding charges.",
                ),
                (
                    "callout",
                    "info",
                    "A query with no syntax is unchanged",
                    "<p>The parser only reads a token as syntax when it could not be plain text. <code>note: "
                    "something</code> is not a filter, because <code>note</code> is not a field. "
                    "<code>state-of-the-art</code> is not three negations. <code>https://example.com/x</code> is one "
                    "word. And a value that does not parse — <code>added:90d</code>, which is a duration with no "
                    "comparison — comes back in the response's <code>filters.ignored</code> rather than being silently "
                    "applied or silently dropped.</p>",
                ),
                ("h3", "Your own tags"),
                (
                    "p",
                    "Netscape and pinboard exports carry a <code>TAGS</code> attribute, and it is kept: stored on the "
                    "bookmark, returned with every hit, and queryable as <code>tag:work</code>. The match is on one "
                    "whole element of the list, so <code>tag:work</code> never widens into <code>workshop</code>; use "
                    "<code>tag:(work|rust)</code> for more than one. <code>POST /bookmark</code> and the MCP "
                    "<code>save_bookmark</code> tool accept <code>tags</code> too, and re-importing a file unions the "
                    "tags rather than replacing them.",
                ),
            ],
        ),
        (
            "serve",
            "Serve: HTTP API and the pairing token",
            [
                ("cb", "shell", "facetmark serve        # 127.0.0.1:8787"),
                (
                    "callout",
                    "warn",
                    "Loopback is not an authorisation model",
                    "<p>Every route that touches the library requires a token, even on localhost, because any process "
                    "on your machine can reach 127.0.0.1. The open ones are <code>/</code>, <code>/health</code>, and "
                    'the two the <a href="#webui">local page</a> needs before it can send a header — '
                    "<code>/app</code>, a static file with no data in it, and <code>/app/boot</code>, which answers "
                    "only a loopback caller asking a loopback address. <code>facetmark serve</code> prints a warning "
                    "when <code>--host</code> is anything other than a loopback address: the index contains your whole "
                    "browsing interest graph.</p>",
                ),
                ("h3", "The token"),
                (
                    "p",
                    "The token is generated on first run and stored in <code>pairing-token.txt</code> in the data "
                    "directory. Send <code>Authorization: Bearer &lt;token&gt;</code> or "
                    "<code>x-facetmark-token</code>. Keep it out of public links and logs.",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark token             # print it\nfacetmark token --rotate    # invalidate the old one",
                ),
                (
                    "cb",
                    "shell",
                    "TOKEN=$(facetmark token)\n"
                    "\n"
                    "curl -s http://127.0.0.1:8787/health\n"
                    "\n"
                    "curl -s -X POST http://127.0.0.1:8787/search \\\n"
                    "  -H 'content-type: application/json' \\\n"
                    '  -H "x-facetmark-token: $TOKEN" \\\n'
                    '  -d \'{"q":"vectors inside sqlite","limit":5}\'',
                ),
                ("h3", "POST /search"),
                (
                    "table",
                    ["Field", "Type", "Meaning"],
                    [
                        ["<code>q</code>", "string", "The query. Required."],
                        ["<code>limit</code>", "int", "Results to return."],
                        [
                            "<code>config</code>",
                            "string",
                            'Profile or rung name. <code>""</code> and <code>"full"</code> both resolve through '
                            "<code>default_config</code>.",
                        ],
                        [
                            "<code>assist</code>",
                            "bool",
                            "Allow the model-assisted understanding step.",
                        ],
                        [
                            "<code>expand</code>",
                            "bool",
                            "Return the one-hop graph group alongside the hits.",
                        ],
                    ],
                ),
                ("h3", "Every route"),
                (
                    "table",
                    ["Group", "Routes"],
                    [
                        ["Open", "<code>GET /</code> · <code>GET /health</code>"],
                        [
                            "Local page — also open",
                            "<code>GET /app</code> · <code>GET /app/static/*</code> · <code>GET /app/boot</code>",
                        ],
                        [
                            "Search",
                            "<code>GET /stats</code> · <code>GET /quick</code> · <code>POST /search</code> · <code>POST "
                            "/suggest</code> · <code>POST /synthesize</code>",
                        ],
                        [
                            "Records",
                            "<code>GET /bookmark/{id}</code> · <code>GET /bookmark/{id}/related</code> · <code>POST "
                            "/bookmark</code> · <code>POST /open</code>",
                        ],
                        ["Sessions", "<code>GET /sessions</code> · <code>GET /session/{id}</code>"],
                        [
                            "Indexing queue",
                            "<code>GET /queue/next</code> · <code>POST /queue/complete</code> · <code>GET "
                            "/queue/stats</code>",
                        ],
                        [
                            "Link health",
                            "<code>GET /link-health/summary</code> · <code>GET /link-health/{id}</code> · <code>POST "
                            "/link-health/check</code> · <code>GET /graveyard</code>",
                        ],
                        [
                            "karakeep bridge",
                            "<code>POST /karakeep/documents</code> · <code>POST /karakeep/documents/delete</code> · "
                            "<code>POST /karakeep/search</code> · <code>POST /karakeep/clear</code> · <code>GET "
                            "/karakeep/stats</code>",
                        ],
                    ],
                ),
                (
                    "callout",
                    "",
                    "Administration",
                    "<p>Admin routes additionally require a loopback peer and can be disabled with "
                    '<code>FACETMARK_ADMIN_API=false</code>. Follow the <a href="quickstart.html#server">SSH '
                    "forwarding steps</a> for remote administration.</p>",
                ),
            ],
        ),
        (
            "webui",
            "The local page",
            [
                (
                    "p",
                    "<code>facetmark serve</code> provides the <code>/app</code> interface and HTTP API. The app "
                    "includes search, synthesis, Library, Sessions and System; the gear opens Settings.",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark serve\n"
                    "# facetmark @@VERSION@@  http://127.0.0.1:8787\n"
                    "# open the search page:     http://127.0.0.1:8787/app\n"
                    "# pairing token written to the data directory\n"
                    "#   (facetmark config show lists the effective data_dir)",
                ),
                (
                    "p",
                    "Plain HTML, CSS and ES modules inside the Python package: no Node, no bundler, no build artefact "
                    "that can go stale against the server it talks to. Because the page is served by the same process "
                    "as the API it is same-origin, which is also why it cannot be hosted anywhere else — CORS on this "
                    "service is restricted to browser-extension origins.",
                ),
                ("h3", "Five tabs and administration entry points"),
                (
                    "table",
                    ["View", "Address", "What it is for"],
                    [
                        [
                            "Search",
                            "<code>/app#/search</code>",
                            "Committed input first shows lexical results without a model call, then the full retrieval "
                            "results. Queries pause during IME composition. Use <b>Load more</b> to continue browsing.",
                        ],
                        [
                            "Ask",
                            "<code>/app#/ask</code>",
                            "Submit a question to generate an answer from stored summaries or snippets, with numbered "
                            "citations. Follow the sources and verify the original pages.",
                        ],
                        [
                            "Library",
                            "<code>/app#/library</code>",
                            "Inspect save activity, text and vector coverage, sessions and connections. When search finds "
                            "nothing, first check that bookmarks were imported and their text and indexes are available.",
                        ],
                        [
                            "Sessions",
                            "<code>/app#/sessions</code>",
                            "Find bookmarks saved together and open a session to continue reading.",
                        ],
                        [
                            "System",
                            "<code>/app#/system</code>",
                            "Inspect service and model status, fetch queues, link health and the cold-layer list.",
                        ],
                        [
                            "Settings (gear)",
                            "<code>/app#/settings</code>",
                            "Test and save model configuration, adjust indexing options, and start or cancel an index job.",
                        ],
                        [
                            "First run",
                            "<code>/app#/setup</code>",
                            "Import bookmarks, choose models and build the index. You can revisit these steps with an "
                            "existing library.",
                        ],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "Which actions require administration access",
                    "<p>Paired connections can search, generate answers and inspect bookmarks. Importing files, saving "
                    "configuration and controlling index jobs additionally require loopback access or SSH forwarding. "
                    "Opening an original page from a result records reading activity; search and detail views do not "
                    "offer bookmark editing or deletion.</p>",
                ),
                ("h3", "What the markers on a row mean"),
                (
                    "p",
                    "The same vocabulary the extension popup uses. In the page each one carries a one-line explanation "
                    "on hover; the table is here so you can read them all at once.",
                ),
                (
                    "table",
                    ["Marker", "Means", "Default"],
                    [
                        [
                            '<span class="chip mk">about</span>',
                            "The <b>content</b> facet matched — an embedding of stored content, which can include a "
                            "title-derived summary.",
                            '<span class="badge info">on</span>',
                        ],
                        [
                            '<span class="chip mk">asked as</span>',
                            "The <b>intent</b> facet matched — vectors over questions generated for the page.",
                            "off",
                        ],
                        [
                            '<span class="chip mk">words</span>',
                            "The <b>lexical · segments</b> facet matched — FTS5 over whole words in the title, folder or "
                            "address.",
                            "off",
                        ],
                        [
                            '<span class="chip mk">substring</span>',
                            "The <b>lexical · trigram</b> facet matched — FTS5 over characters, which is what makes partial "
                            "words and Chinese queries hit.",
                            "off",
                        ],
                        [
                            '<span class="badge warn mk">cold</span>',
                            "Saved long ago, never opened, and something newer looks like it replaced it. Ranked lower, "
                            "never deleted.",
                            '<span class="badge info">on</span>',
                        ],
                        [
                            '<span class="gmk mk">saved around these</span>',
                            "The second group: one hop over the link graph from a result above. Never mixed into the "
                            "ranking.",
                            '<span class="badge info">on</span>',
                        ],
                    ],
                ),
                (
                    "p",
                    "Rows in that second group carry a chip for the edge that reached them — <em>same sitting</em> "
                    "(saved in the same browsing session), <em>similar</em> (close in meaning), <em>replaced by</em>, "
                    '<em>same page</em>, <em>same site</em>. The weights behind those names are in <a href="#env">the '
                    "settings table</a>.",
                ),
                ("h3", "How the page gets the token"),
                (
                    "p",
                    "It asks <code>GET /app/boot</code>, which is the only route that can hand out the pairing token, "
                    "and only when both the caller and the address in the request are loopback. On your own machine "
                    "both are true and the page pairs itself with nothing to copy.",
                ),
                (
                    "callout",
                    "warn",
                    "Why the second condition exists",
                    "<p>A page on the open web can point a hostname at 127.0.0.1 and have <em>your</em> browser make "
                    "the request — the caller really is loopback. What it cannot do is change the <code>Host</code> "
                    "header, which still carries the attacker’s domain. Checking it is what keeps a website from "
                    "reading your token, and it is why this is a separate route rather than a flag on an existing "
                    "one.</p><p>Behind a reverse proxy, or on a LAN address, that check fails on purpose: the page "
                    "then shows a field and you paste <code>facetmark token</code> once. It is kept in that browser’s "
                    "local storage, not in the page.</p>",
                ),
                ("h3", "Keyboard"),
                (
                    "table",
                    ["Key", "Does"],
                    [
                        ["<kbd>/</kbd>", "Open and focus Search when you are not typing in another field."],
                        ["<kbd>Enter</kbd>", "Submit the query, or accept a selected suggestion. Confirming IME text does not submit."],
                        [
                            "<kbd>↑</kbd> <kbd>↓</kbd>",
                            "Select suggestions when the list is open; otherwise move through search results. During "
                            "composition these keys stay with the IME.",
                        ],
                        ["<kbd>Esc</kbd>", "Close suggestions or details first; with neither open on Search, clear and focus the query."],
                    ],
                ),
                ("h3", "Language and theme"),
                (
                    "p",
                    "Language and theme preferences are stored in the current browser and origin. The website and app "
                    "use the same preference keys, but browser storage is not shared across domains. The interface "
                    "respects reduced-motion preferences.",
                ),
            ],
        ),
        (
            "paging",
            "Paging: limit, offset and depth",
            [
                (
                    "p",
                    "Every search surface takes <code>limit</code>, <code>offset</code> and <code>depth</code>, and "
                    "every search response reports the window it actually served rather than echoing what you asked "
                    "for.",
                ),
                (
                    "cb",
                    "shell",
                    'facetmark search "kafka rebalance" -n 20\n'
                    'facetmark search "kafka rebalance" -n 20 -o 20 --depth 60',
                ),
                (
                    "p",
                    "The CLI prints the <code>--offset</code> and <code>--depth</code> for the next page whenever "
                    "there is one. Over HTTP the same three fields go in the <code>POST /search</code> body:",
                ),
                (
                    "cb",
                    "json",
                    "{\n"
                    '  "hits": [ ],\n'
                    '  "limit": 20,          // served, after clamping\n'
                    '  "offset": 20,\n'
                    '  "depth": 60,          // the depth this ranking ran at\n'
                    '  "total": 137,         // ranked so far; a floor when capped\n'
                    '  "has_more": true,\n'
                    '  "depth_capped": false\n'
                    "}",
                ),
                (
                    "table",
                    ["Field", "Meaning"],
                    [
                        [
                            "<code>limit</code>",
                            "Rows in this page. Clamped to <code>MAX_PAGE_SIZE</code>, 200 by default.",
                        ],
                        [
                            "<code>offset</code>",
                            "Rows skipped. Clamped below <code>MAX_CANDIDATE_DEPTH</code>.",
                        ],
                        [
                            "<code>depth</code>",
                            "How deep each facet was read before fusion. Omit it and it is derived from the window; send "
                            "back the value the previous page reported and this page continues that same ranking.",
                        ],
                        [
                            "<code>total</code>",
                            "Documents the fusion step ranked. A lower bound, not a library count, and explicitly a floor "
                            "when <code>depth_capped</code> is true.",
                        ],
                        [
                            "<code>has_more</code>",
                            "There is something past this window. Exact under the shipped single-facet default; an upper "
                            "bound with several facets in play, where the overflow row can turn out to be a document the "
                            "pool already held.",
                        ],
                        [
                            "<code>depth_capped</code>",
                            "More exists <em>and</em> the reason we stopped is the depth ceiling rather than your window — "
                            "the difference between “press next” and “raise the depth or narrow the query”.",
                        ],
                    ],
                ),
                ("h3", "Why depth is a parameter and not an implementation detail"),
                (
                    "p",
                    "Page size controls how many results you see; retrieval depth controls the candidate pool. Reuse "
                    "the response <code>depth</code> for subsequent pages to keep the ranking basis consistent.",
                ),
                (
                    "callout",
                    "warn",
                    "Pin the depth or page two can disagree with page one",
                    "<p>RRF is only rank-stable under a growing pool when there is <em>one</em> facet. A document’s "
                    "score is a sum over the facets that ranked it within the depth asked for, so a deeper pool can "
                    "hand a document a term it did not have — and that term can outweigh a rival’s whole score. Rank 2 "
                    "in one facet plus rank 40 in another beats a sole rank 1 (1/62 + 1/100 against 1/61) but "
                    "contributes nothing at depth 30.</p><p>So with several facets on, growing the depth to reach page "
                    "2 lets page 2 disagree with page 1 about what page 1 was. The fix is not to grow it: send back "
                    "the <code>depth</code> the previous page reported and every page is a slice of one ranking. The "
                    "local page and the browser extension both do this.</p>",
                ),
                ("h3", "The two ceilings"),
                (
                    "p",
                    "<code>MAX_PAGE_SIZE</code> (200) bounds one page. <code>MAX_CANDIDATE_DEPTH</code> (2000) bounds "
                    "the pool behind all of them, and hitting it is what sets <code>depth_capped</code>. Both are "
                    "clamped in one place, before any query runs, so an oversized request costs nothing and is "
                    "answered with the window that was actually served.",
                ),
            ],
        ),
        (
            "extension",
            "Browser extension",
            [
                (
                    "p",
                    "Manifest V3, for Chromium-family browsers. It talks to <code>127.0.0.1:8787</code> and nothing "
                    "else — those are its only required host permissions.",
                ),
                (
                    "steps",
                    [
                        "Download <code>facetmark-extension.zip</code> from the <a "
                        'href="https://github.com/88lin/facetmark/releases">releases page</a> and unzip it.',
                        "Open <code>chrome://extensions</code>, turn on <b>Developer mode</b>, choose <b>Load "
                        "unpacked</b> and select the unzipped folder.",
                        "Run <code>facetmark serve</code> in a terminal and leave it running.",
                        "Run <code>facetmark token</code>, open the extension's options page, and paste the token.",
                        "Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> "
                        "(<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> on macOS) and search.",
                    ],
                ),
                ("h3", "What it gives you"),
                (
                    "table",
                    ["Feature", "Detail"],
                    [
                        [
                            "Omnibox keyword",
                            "Type <code>fm</code> then a space in the address bar and search without opening the popup.",
                        ],
                        [
                            "Keyboard shortcut",
                            "<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> / <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>.",
                        ],
                        [
                            "Save the current tab",
                            "One click. The page joins a local indexing queue and the popup footer shows how many are "
                            "waiting.",
                        ],
                        ["Context menu", "Right-click a link or a page to save it."],
                        [
                            "Grouped results",
                            "Pages from the same saving session arrive as their own group instead of being mixed into the "
                            "ranking.",
                        ],
                        [
                            "Facet labels",
                            "Each hit shows which facets matched — <em>about</em>, <em>asked as</em>, <em>words</em>, "
                            "<em>substring</em>, <em>linked</em>, <em>cold</em>.",
                        ],
                    ],
                ),
                ("h3", "Options"),
                (
                    "table",
                    ["Field", "Meaning"],
                    [
                        [
                            "<code>endpoint</code>",
                            "Where facetmark is listening. Default <code>http://127.0.0.1:8787</code>.",
                        ],
                        ["<code>token</code>", "Output of <code>facetmark token</code>."],
                        [
                            "<code>channelB</code>",
                            "An optional second endpoint, for running two libraries.",
                        ],
                        [
                            "<code>paused</code>",
                            "Stop the extension talking to the service without uninstalling it.",
                        ],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "Not in the web stores",
                    "<p>The extension is distributed as a zip on the releases page and installed unpacked. It has not "
                    "been submitted to the Chrome Web Store or the Edge add-ons catalogue.</p>",
                ),
            ],
        ),
        (
            "mcp",
            "MCP server",
            [
                (
                    "p",
                    "<code>facetmark mcp</code> runs a FastMCP server on stdio, so an MCP client such as Claude "
                    "Desktop can search your library, read a saving session, and save a page.",
                ),
                (
                    "cb",
                    "json",
                    "{\n"
                    '  "mcpServers": {\n'
                    '    "facetmark": {\n'
                    '      "command": "facetmark",\n'
                    '      "args": ["mcp"]\n'
                    "    }\n"
                    "  }\n"
                    "}",
                ),
                (
                    "p",
                    'Add <code>"--db", "/path/to/facetmark.db"</code> to <code>args</code> to point at a specific '
                    'library, or <code>"--mock"</code> to try it with no key. Environment variables are read the same '
                    "way as for every other command.",
                ),
                ("h3", "Nine tools"),
                (
                    "table",
                    ["Tool", "Does"],
                    [
                        [
                            "<code>search_bookmarks</code>",
                            "The full pipeline, same as <code>facetmark search</code>.",
                        ],
                        ["<code>get_bookmark</code>", "One record, optionally with the body."],
                        ["<code>list_sessions</code>", "Recent saving episodes."],
                        ["<code>get_session</code>", "Everything saved in one episode."],
                        ["<code>find_related</code>", "One hop out in the link graph."],
                        [
                            "<code>synthesize</code>",
                            "A model-written answer grounded in retrieved pages.",
                        ],
                        [
                            "<code>suggest_from_context</code>",
                            "What in the library relates to text you are looking at.",
                        ],
                        ["<code>check_link_health</code>", "Whether a saved URL is still alive."],
                        ["<code>save_bookmark</code>", "Add a URL and queue it for indexing."],
                    ],
                ),
                ("h3", "Three resources"),
                (
                    "ul",
                    [
                        "<code>bookmark://{id}</code> — one record as JSON.",
                        "<code>session://{id}</code> — one saving episode.",
                        "<code>facetmark://stats</code> — index size and coverage.",
                    ],
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep plugin",
            [
                (
                    "p",
                    '<a href="https://karakeep.app">karakeep</a> is a self-hosted bookmark manager with a pluggable '
                    "search provider. This plugin puts facetmark behind its search box, so karakeep keeps the UI and "
                    "facetmark does the retrieval.",
                ),
                (
                    "steps",
                    [
                        "Copy the plugin into karakeep's plugin package.",
                        "Register it in the exports map.",
                        "Load it <b>after</b> meilisearch, because the plugin manager hands out the last provider "
                        "registered.",
                        "Point it at a running facetmark service.",
                    ],
                ),
                (
                    "cb",
                    "shell",
                    "cp -r integrations/karakeep/search-facetmark \\\n"
                    "  /path/to/karakeep/packages/plugins/search-facetmark",
                ),
                (
                    "cb",
                    "json",
                    "// packages/plugins/package.json — exports map\n"
                    '"./search-facetmark": "./search-facetmark/index.ts"',
                ),
                (
                    "cb",
                    "ts",
                    "// packages/shared-server/src/plugins.ts, in loadAllPlugins()\n"
                    'await import("@karakeep/plugins/search-meilisearch");\n'
                    'await import("@karakeep/plugins/search-facetmark");  // must come after',
                ),
                (
                    "cb",
                    "shell",
                    "export FACETMARK_URL=http://127.0.0.1:8787\n"
                    "export FACETMARK_TOKEN=$(facetmark token)\n"
                    "facetmark serve",
                ),
                ("h3", "How the contract is kept honest"),
                (
                    "ul",
                    [
                        "Upstream karakeep types are pinned by blob SHA in "
                        "<code>integrations/karakeep/typecheck/upstream-pins.json</code>, and CI runs <code>tsc "
                        "--noEmit</code> against them.",
                        "The wire format is captured in <code>integrations/karakeep/contract/wire.json</code> and "
                        "replayed by <code>tests/test_karakeep_contract.py</code>.",
                        "That replay test caught a real one: at offset 1 of a single match, the correct answer is "
                        "<code>hits: []</code> with <code>totalHits: 1</code>. An empty <code>hits</code> array is "
                        "<b>not</b> the same as no results.",
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "Two things to know before you rely on it",
                    "<p>First, there is no test against a live karakeep instance — only against the pinned contract. "
                    "Second, pushing your library through karakeep and back changes the ranking: karakeep's tags are "
                    "your browser's folder labels, so the keyword line collapses from 19,016 distinct terms to 13. "
                    "Metric-level conclusions survive the round trip; rank-level ones do not until you re-index. <a "
                    'href="measured.html#karakeep">The full measurement</a>.</p>',
                ),
                (
                    "p",
                    "To uninstall the bridge, drop the <code>karakeep_doc</code> table. <code>enrichment.source_hash "
                    "== 'karakeep'</code> is reserved and means the bridge may overwrite that row; any other value "
                    "means a real model wrote it and the bridge leaves it alone.",
                ),
            ],
        ),
        (
            "data",
            "What is in the database",
            [
                (
                    "p",
                    "One SQLite file. Open it with any SQLite browser; nothing is encrypted, obfuscated or "
                    "proprietary. If you stop using facetmark, your data is still readable.",
                ),
                (
                    "table",
                    ["Table", "Holds"],
                    [
                        [
                            "<code>bookmark</code>",
                            "URL, title, folder path, save timestamp, source.",
                        ],
                        ["<code>content</code>", "The fetched body and its extracted text."],
                        [
                            "<code>enrichment</code>",
                            "Summary, topics, entities, key points, and the <code>source_hash</code> fingerprint.",
                        ],
                        [
                            "<code>intent</code>",
                            "Generated candidate queries and whether each one survived the retrieve-it-back filter.",
                        ],
                        [
                            "<code>vec_content</code> / <code>vec_intent</code>",
                            "sqlite-vec virtual tables holding the dense vectors.",
                        ],
                        [
                            "<code>fts_tri</code> / <code>fts_seg</code>",
                            "Two FTS5 indexes: character trigrams and word segments.",
                        ],
                        [
                            "<code>session</code> / <code>bookmark_session</code>",
                            "Reconstructed saving episodes and their membership.",
                        ],
                        [
                            "<code>edge</code>",
                            "Typed links: <code>session</code>, <code>semantic</code>, <code>same_domain</code>, "
                            "<code>supersession</code>.",
                        ],
                        [
                            "<code>health</code>",
                            "Link-health verdicts: <code>ok</code>, <code>gone</code>, <code>drifted</code>, "
                            "<code>soft_gone</code>.",
                        ],
                        [
                            "<code>karakeep_doc</code>",
                            "Bridge state. Drop it to uninstall the bridge.",
                        ],
                        [
                            "<code>meta</code>",
                            "Embedding model, dimension and backend, recorded at first build and enforced afterwards.",
                        ],
                    ],
                ),
                ("h3", "Link health and the cold layer"),
                (
                    "cb",
                    "shell",
                    "facetmark health                       # what is known\n"
                    "facetmark health --check               # actually probe the network\n"
                    "facetmark health --check --no-save-recovered   # read-only sweep",
                ),
                (
                    "p",
                    "The sweep can use DNS-over-HTTPS, the Wayback availability API and a reader proxy to distinguish "
                    "“gone” from “your DNS is broken”. Use <code>--no-save-recovered</code> before measuring anything "
                    "against a library, so the sweep stays read-only apart from the health log.",
                ),
                (
                    "callout",
                    "bad",
                    "A known, load-bearing bug",
                    "<p>The cold layer treats “the URL died” as “the saved copy is useless”, which is wrong: facetmark "
                    "stores the body, so a dead URL is when the local snapshot matters <em>most</em>. It is not fixed "
                    "yet, because in the shipped profile a second accident stops the demotion from ever executing, and "
                    "removing either one alone makes results worse by a measured 1.46pp. <a "
                    'href="measured.html#decay">The whole story</a>.</p>',
                ),
            ],
        ),
        (
            "env",
            "Every setting",
            [
                (
                    "p",
                    "Prefix every name with <code>FACETMARK_</code> as an environment variable, or put it unprefixed "
                    "in a <code>.env</code> file. Defaults below are the shipped values.",
                ),
                ("h3", "Storage"),
                (
                    "table",
                    ["Setting", "Default", "Notes"],
                    [
                        ["<code>DATA_DIR</code>", "per-OS", 'See <a href="#install">install</a>.'],
                        ["<code>DB_NAME</code>", "<code>facetmark.db</code>", ""],
                        [
                            "<code>PRIVACY_EXCLUDED_DOMAINS</code>",
                            "empty",
                            "Never imported, fetched or embedded.",
                        ],
                    ],
                ),
                ("h3", "Model access"),
                (
                    "table",
                    ["Setting", "Default", "Notes"],
                    [
                        [
                            "<code>API_KEY</code>",
                            "empty",
                            "Empty is legal; you lose the content and intent facets.",
                        ],
                        [
                            "<code>BASE_URL</code>",
                            "<code>https://api.openai.com/v1</code>",
                            "Must end in <code>/v1</code>.",
                        ],
                        ["<code>CHAT_MODEL</code>", "<code>gpt-6-luna</code>", ""],
                        ["<code>CHAT_EXTRA_BODY</code>", "", "JSON object string for reasoning and output limits. Empty uses endpoint defaults without forced sampling."],
                        ["<code>EMBED_SEND_DIMENSIONS</code>", "false", "dimensions"],
                        ["<code>EMBED_BATCH_SIZE</code>", "64", "Use 20 for Bailian."],
                        [
                            "<code>CHAT_MODEL_FALLBACKS</code>",
                            "empty",
                            "Comma-separated. Empty on purpose.",
                        ],
                        ["<code>EMBED_MODEL</code>", "<code>text-embedding-3-small</code>", ""],
                        [
                            "<code>EMBED_DIM</code>",
                            "<code>1536</code>",
                            "Recorded in <code>meta</code>; a mismatch raises.",
                        ],
                        [
                            "<code>EMBED_BACKEND</code>",
                            "<code>endpoint</code>",
                            "Or <code>local</code>.",
                        ],
                        ["<code>REQUEST_TIMEOUT</code>", "<code>60.0</code>", "Seconds."],
                        ["<code>MAX_RETRIES</code>", "<code>3</code>", ""],
                        [
                            "<code>USE_MOCK_PROVIDER</code>",
                            "<code>false</code>",
                            "Deterministic offline provider.",
                        ],
                    ],
                ),
                ("h3", "Local embeddings"),
                (
                    "table",
                    ["Setting", "Default", "Notes"],
                    [
                        ["<code>LOCAL_EMBED_PATH</code>", "empty", "Empty downloads the model."],
                        ["<code>LOCAL_EMBED_DEVICE</code>", "<code>cpu</code>", ""],
                        ["<code>LOCAL_EMBED_BATCH</code>", "<code>8</code>", ""],
                        [
                            "<code>LOCAL_EMBED_MAX_SEQ</code>",
                            "<code>1024</code>",
                            'Lowering it costs reproducibility — see <a href="#models">model access</a>.',
                        ],
                    ],
                ),
                ("h3", "Fetching"),
                (
                    "table",
                    ["Setting", "Default", "Notes"],
                    [
                        ["<code>FETCH_CONCURRENCY</code>", "<code>30</code>", "Global."],
                        [
                            "<code>FETCH_PER_HOST_CONCURRENCY</code>",
                            "<code>2</code>",
                            "Politeness, not performance.",
                        ],
                        [
                            "<code>FETCH_PER_HOST_MIN_INTERVAL</code>",
                            "<code>0.5</code>",
                            "Seconds between hits on one host.",
                        ],
                        ["<code>FETCH_TIMEOUT</code>", "<code>15.0</code>", ""],
                        ["<code>RESPECT_ROBOTS</code>", "<code>true</code>", ""],
                        [
                            "<code>ROBOTS_ON_ERROR</code>",
                            "<code>allow</code>",
                            "What to do when robots.txt cannot be read.",
                        ],
                        [
                            "<code>ROBOTS_MAX_CRAWL_DELAY</code>",
                            "<code>5.0</code>",
                            "Cap on an advertised crawl delay.",
                        ],
                        [
                            "<code>MIN_BODY_CHARS</code>",
                            "<code>200</code>",
                            "Below this the page counts as body-less.",
                        ],
                        ["<code>BODY_TRUNCATE_CHARS</code>", "<code>6000</code>", ""],
                        ["<code>USER_AGENT</code>", "identifies facetmark", ""],
                    ],
                ),
                ("h3", "Enrichment and intents"),
                (
                    "table",
                    ["Setting", "Default", "Notes"],
                    [
                        ["<code>ENRICH_CONCURRENCY</code>", "<code>4</code>", ""],
                        [
                            "<code>INTENT_GENERATE_N</code>",
                            "<code>8</code>",
                            "Candidates generated per page.",
                        ],
                        ["<code>INTENT_KEEP_N</code>", "<code>4</code>", "Kept per page, at most."],
                        [
                            "<code>INTENT_PROBE_TOP_K</code>",
                            "<code>10</code>",
                            "How deep the retrieve-it-back filter looks.",
                        ],
                    ],
                ),
                ("h3", "Sessions, retrieval and decay"),
                (
                    "table",
                    ["Setting", "Default", "Notes"],
                    [
                        [
                            "<code>SESSION_EPS_MINUTES</code>",
                            "auto",
                            "Unset means the gap is chosen by coverage × purity lift over a grid.",
                        ],
                        [
                            "<code>SESSION_EPS_GRID_MINUTES</code>",
                            "<code>5…240</code>",
                            "The grid it searches.",
                        ],
                        [
                            "<code>RRF_K</code>",
                            "<code>60</code>",
                            "The <code>k</code> in <code>w / (k + rank)</code>.",
                        ],
                        ["<code>CANDIDATES_PER_FACET</code>", "<code>50</code>", ""],
                        ["<code>GRAPH_EXPAND_HOPS</code>", "<code>1</code>", ""],
                        ["<code>GRAPH_EXPAND_FACTOR</code>", "<code>0.6</code>", ""],
                        ["<code>DECAY_FACTOR</code>", "<code>0.5</code>", ""],
                        ["<code>DECAY_AGE_DAYS</code>", "<code>365</code>", ""],
                        [
                            "<code>DECAY_RESCUE_THRESHOLD</code>",
                            "<code>0.02</code>",
                            'See the <a href="measured.html#decay">decay measurement</a> before changing this.',
                        ],
                    ],
                ),
                ("h3", "Link health and service"),
                (
                    "table",
                    ["Setting", "Default", "Notes"],
                    [
                        [
                            "<code>HEALTH_ENABLE_EXTERNAL</code>",
                            "<code>true</code>",
                            "Master switch for network probes.",
                        ],
                        ["<code>HEALTH_ENABLE_DOH</code>", "<code>true</code>", "DNS-over-HTTPS."],
                        ["<code>HEALTH_ENABLE_WAYBACK</code>", "<code>true</code>", ""],
                        ["<code>HEALTH_ENABLE_READER</code>", "<code>true</code>", ""],
                        [
                            "<code>HEALTH_SOFT_GONE_LENGTH_RATIO</code>",
                            "<code>0.30</code>",
                            "Body shrank this much ⇒ <code>soft_gone</code>.",
                        ],
                        ["<code>HEALTH_GONE_CONFIRM_DAYS</code>", "<code>7</code>", ""],
                        ["<code>HEALTH_PROXY_URL</code>", "unset", ""],
                        ["<code>HOST</code>", "<code>127.0.0.1</code>", ""],
                        ["<code>PORT</code>", "<code>8787</code>", ""],
                    ],
                ),
            ],
        ),
        (
            "commands",
            "Every command",
            [
                (
                    "p",
                    "Use <code>facetmark COMMAND --help</code> to check each command. Database commands generally "
                    "support <code>--db</code>; many offer <code>--json</code> for scripts.",
                ),
                (
                    "table",
                    ["Command", "Does", "Notable flags"],
                    [
                        ["<code>version</code>", "Print the version.", ""],
                        [
                            "<code>browsers</code>",
                            "List live browser profiles that can be imported.",
                            "<code>--json</code>",
                        ],
                        [
                            "<code>import [PATH]</code>",
                            "Import a Netscape HTML export or a Chrome JSON profile. With no path, finds the live profile. "
                            "Never writes back.",
                            "",
                        ],
                        [
                            "<code>migrate</code>",
                            "Bring the schema up to what this build expects.",
                            "<code>--check</code>, <code>--no-backup</code>",
                        ],
                        [
                            "<code>index</code>",
                            "Fetch, enrich, embed, intents, sessions, edges.",
                            "<code>--no-fetch</code>, <code>--limit</code>, <code>--force</code>, <code>--mock</code>",
                        ],
                        [
                            "<code>reindex</code>",
                            "Rebuild every derived artefact from the bookmarks.",
                            "<code>--mock</code>",
                        ],
                        [
                            "<code>search QUERY</code>",
                            "Search the library.",
                            "<code>-n</code>, <code>--quick</code>, <code>--config</code>, <code>--explain</code>",
                        ],
                        [
                            "<code>show ID</code>",
                            "Print one bookmark as JSON.",
                            "<code>--body</code>",
                        ],
                        ["<code>sessions</code>", "List saving episodes.", "<code>-n</code>"],
                        [
                            "<code>health</code>",
                            "Link health, and whether the decay layer can see any of it.",
                            "<code>--check</code>, <code>--no-external</code>, <code>--no-save-recovered</code>",
                        ],
                        ["<code>stats</code>", "Index size and coverage.", ""],
                        [
                            "<code>export [FILE] [QUERY]</code>",
                            "Write the library, or the part a filter query names, as JSON that <code>import</code> reads "
                            "back. Filters only — the top of a ranking is not a backup. Derived data is left out; "
                            "<code>index</code> rebuilds it.",
                            "<code>--full</code>",
                        ],
                        [
                            "<code>doctor</code>",
                            "Diagnose the install — configuration and where each setting came from, schema version, whether "
                            "the indexes were built, whether the stored vectors match the settings. Repairs nothing and "
                            "calls no model; every finding names the command that fixes it.",
                            "<code>--json</code>",
                        ],
                        [
                            "<code>token</code>",
                            "Print the extension's pairing token.",
                            "<code>--rotate</code>",
                        ],
                        [
                            "<code>serve</code>",
                            "Run the local HTTP service.",
                            "<code>--host</code>, <code>--port</code>, <code>--mock</code>",
                        ],
                        ["<code>mcp</code>", "Run the MCP server on stdio.", "<code>--mock</code>"],
                        [
                            "<code>crawl URL</code>",
                            "Walk a site into the library, politely. robots.txt is honoured, hosts on the privacy exclusion "
                            "list are not contacted at all, and each page becomes an ordinary bookmark.",
                            "<code>--max-pages</code>, <code>--off-domain</code>",
                        ],
                        [
                            "<code>update</code>",
                            "Say whether a newer facetmark is on PyPI. It checks only when you run it — no background check, "
                            "no telemetry — and never upgrades anything itself.",
                            "<code>--json</code>",
                        ],
                        [
                            "<code>demo</code>",
                            "Build a synthetic library offline and search it.",
                            "<code>--size</code>, <code>--keep</code>",
                        ],
                        [
                            "<code>config path</code> / <code>config show</code>",
                            "Where <code>config.toml</code> lives, and the effective settings with the source of each one.",
                            "",
                        ],
                        [
                            "<code>eval</code>",
                            "Run the retrieval evaluation, optionally as an A–E ablation.",
                            "<code>--ablation</code>, <code>--rungs</code>, <code>--queries</code>, "
                            "<code>--bootstrap</code>, <code>--out</code>",
                        ],
                    ],
                ),
                ("h3", "Running your own evaluation"),
                (
                    "p",
                    "Evaluation accepts JSONL queries with <code>{text, qtype, target_url}</code>, compares retrieval "
                    "configurations on a specified library, and reports confidence intervals and paired tests. Fix the "
                    "dataset and protocol before interpreting results.",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark eval --no-build \\\n"
                    "  --queries my-queries.jsonl \\\n"
                    "  --rungs A,C,full \\\n"
                    "  --bootstrap 10000 --concurrency 4 \\\n"
                    "  --out report.json",
                ),
                (
                    "callout",
                    "warn",
                    "Concurrency destroys the latency numbers",
                    "<p><code>--concurrency &gt; 1</code> makes p50 and p95 meaningless. Use it for the quality "
                    "numbers, then re-run at concurrency 1 on a subsample if you need latency.</p>",
                ),
            ],
        ),
        (
            "trouble",
            "Troubleshooting",
            [
                ("h3", "Every model call returns 404"),
                (
                    "p",
                    "Check the complete provider base URL, including its path prefix (often <code>/v1</code>), and the "
                    "available model name. A 404 can indicate the URL or model name; it does not by itself prove the "
                    "API key is invalid.",
                ),
                ("h3", "“dimension mismatch” on index or search"),
                (
                    "p",
                    "The database dimension differs from <code>FACETMARK_EMBED_DIM</code>. Confirm the model output "
                    "dimension, correct the configuration, restart the service and rebuild the index. Keep a database "
                    "backup before changing it.",
                ),
                ("h3", "Enrichment silently does nothing"),
                (
                    "p",
                    "The stored <code>source_hash</code> already equals the current body hash, so the fingerprint says "
                    "the work is done. That is correct behaviour, and <code>facetmark index --force</code> overrides "
                    "it.",
                ),
                ("h3", "Vectors exist but results are bad"),
                (
                    "p",
                    "Usually the embed text changed after the vector was written — for example because enrichment was "
                    "replaced by a bridge. Re-embed with <code>facetmark index --force</code>. If results are bad on a "
                    "fresh index instead, check whether you are accidentally on the mock provider: <code>facetmark "
                    "stats</code> reports the embedding model in use.",
                ),
                ("h3", "<code>disk I/O error</code> from SQLite"),
                (
                    "p",
                    "SQLite cannot run reliably on some network and FUSE filesystems. Move the data directory to local "
                    "disk with <code>FACETMARK_DATA_DIR</code>.",
                ),
                ("h3", "Fetching is slow, or pages come back empty"),
                (
                    "p",
                    "Both are usually intentional. robots.txt is honoured and per-host concurrency is capped at 2 with "
                    "a minimum interval between hits. Some sites simply refuse. A page with no body still indexes — "
                    "the pipeline falls back to a title-only fingerprint — it is just weaker. Use "
                    "<code>--no-fetch</code> if you want a fast, shallow index.",
                ),
                ("h3", "The extension cannot reach the service"),
                (
                    "p",
                    "Check three things in order: <code>facetmark serve</code> is actually running; the endpoint in "
                    "options matches the host and port it bound; the token in options matches <code>facetmark "
                    "token</code>. If you rotated the token, the extension needs the new one.",
                ),
                ("h3", "Something else"),
                (
                    "p",
                    "<code>facetmark stats</code> and <code>facetmark health</code> print what the index actually "
                    "contains, which resolves most confusion. Beyond that, <a "
                    'href="https://github.com/88lin/facetmark/issues">open an issue</a> — the <code>--json</code> '
                    "output of the failing command is the most useful thing to paste.",
                ),
            ],
        ),
    ],
}


# ------------------------------------------------------------- measured ----

EN["measured"] = {
    "h1": "Evaluation methods and results",
    "lede": (
        "The experiments, counterexamples and open questions behind retrieval defaults. Read each result with "
        "its dataset, protocol and sample limits; these numbers do not predict every library."
    ),
    "toc_title": "Results",
    "sections": [
        (
            "how",
            "How to read the evidence",
            [
                (
                    "ul",
                    [
                        "<b>Pre-registration.</b> Criteria are written down before the run. A rung measured on the "
                        "queries that motivated it is a hypothesis, not a result, and is labelled exploratory.",
                        "<b>Paired tests.</b> Every A-versus-B claim is paired on the same queries, with a bootstrap "
                        "confidence interval and a McNemar test on the discordant pairs. Wins and losses are reported "
                        "separately, because a net zero from 0 changes and a net zero from 40 wins and 40 losses are "
                        "different facts.",
                        "<b>Nothing is reopened.</b> Once a query set is frozen and a verdict recorded, it stands. A new "
                        "question needs a new query set.",
                        "<b>pp</b> means percentage points. <b>CI95</b> is a 95% bootstrap interval.",
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "The biggest caveat, stated once, up front",
                    "<p>Every query set on this page was written by the author of the tool. Bootstrapping fixes "
                    "sampling noise; it does nothing at all about the author knowing what the tool is good at. The "
                    "most valuable contribution this project could receive is a query set written by somebody "
                    "else.</p>",
                ),
            ],
        ),
        (
            "w1",
            "W1 · Content retrieval versus fusion",
            [
                (
                    "raw",
                    '<p><span class="badge fail">default withdrawn</span> <span class="tiny">479 queries · one real '
                    "1,700-bookmark library · pre-registered</span></p>",
                ),
                (
                    "p",
                    "The premise of the whole project was that fusing four facets beats any one of them. Three "
                    "criteria were registered before the run. All three failed.",
                ),
                (
                    "table",
                    ["Rung", "Facets", "Recall@5", "Recall@1", "MRR@10", "p50"],
                    [
                        [
                            "<b>A</b>",
                            "content vector only",
                            "<b>0.643</b>",
                            "0.505",
                            "0.564",
                            "<b>148 ms</b>",
                        ],
                        ["<b>B</b>", "+ two lexical", "0.589", "—", "—", "189 ms"],
                        ["<b>C</b>", "all four", "0.635", "—", "—", "526 ms"],
                        ["<b>D</b>", "+ context + graph", "0.639", "—", "—", "523 ms"],
                    ],
                    [0],
                ),
                (
                    "p",
                    "Fusion cost <b>5.4pp</b> of Recall@5 and made queries <b>3.5×</b> slower. Config A by query type: "
                    "content-style <b>0.959</b>, vague <b>0.706</b>, episodic <b>0.279</b>.",
                ),
                ("h3", "Why it lost"),
                (
                    "p",
                    "Flat-weight reciprocal rank fusion has no way to express confidence. Two weak facets that happen "
                    "to agree score 0.0279; one strong facet that is certain scores 0.0164. The coincidence wins. That "
                    "is not a tuning problem, it is what the formula does.",
                ),
                ("h3", "What survived the same run"),
                (
                    "table",
                    ["Survivor", "Effect", "Wins / losses", "p", "Cost"],
                    [
                        [
                            "Graph expansion as a <em>separate group</em>",
                            "<b>+2.09pp</b> Recall@5",
                            "10 / 0",
                            "0.0019",
                            "9 ms",
                        ],
                        [
                            "Reranker, on Recall@1",
                            "<b>+4.80pp</b> CI95 [+1.46, +8.35]",
                            "45 / 22",
                            "0.0067",
                            "—",
                        ],
                    ],
                ),
                (
                    "p",
                    "Both shipped. Note that graph expansion only works as an <em>addition</em> — returned as its own "
                    "group rather than merged into the ranking.",
                ),
            ],
        ),
        (
            "gate",
            "W2/W3 · Context-gate comparison",
            [
                ("raw", '<p><span class="badge fail">default reverted after shipping</span></p>'),
                (
                    "p",
                    "The episodic gate detects “the thing I saved around the same time as X” and restricts retrieval "
                    "to that saving window. On its 616-query holdout it won cleanly and was shipped.",
                ),
                (
                    "table",
                    ["Query set", "Comparison", "ΔRecall@5", "CI95", "Wins / losses", "p"],
                    [
                        [
                            "616-query holdout",
                            "A → A_gatedctx",
                            '<b class="nowrap">+3.09pp</b>',
                            "[1.79, 4.55]",
                            "19 / 0",
                            "3.8e−6",
                        ],
                        [
                            "361-query precision probe",
                            "A → A_gatedctx",
                            '<b class="nowrap">−18.83pp</b>',
                            "[−23.27, −14.68]",
                            "3 / 71",
                            "—",
                        ],
                    ],
                ),
                (
                    "p",
                    "The second row is the same feature, measured on a query set built afterwards to ask a different "
                    "question: what does the gate do when it fires on a query it should not have? Recall@5 fell from "
                    "0.9058 to 0.7175 and Recall@1 from 0.801 to 0.363.",
                ),
                ("h3", "The stratification is the whole answer"),
                (
                    "table",
                    ["Stratum", "n", "ΔRecall@5"],
                    [
                        [
                            "The saving window contains the target",
                            "57",
                            "<b>+0.00pp</b> — exactly zero",
                        ],
                        [
                            "The saving window misses the target",
                            "304",
                            '<b class="nowrap">−22.37pp</b>',
                        ],
                    ],
                ),
                (
                    "p",
                    "When the gate is right it adds nothing. When it is wrong it throws the answer away. Verdict "
                    "<code>gate_precision_unqualified</code>; the default reverted to no gating.",
                ),
                (
                    "callout",
                    "info",
                    "gate_v2 was drafted and refused",
                    "<p>A narrower gate scored +1.79pp on the original 616-query set and <b>−10.52pp</b> on the "
                    "precision probes. Shipping on the first number while the second exists would have been choosing "
                    "the query set that gave the answer we wanted. It was not shipped.</p>",
                ),
            ],
        ),
        (
            "recall",
            "Recall gate · Insufficient evidence",
            [
                (
                    "raw",
                    '<p><span class="badge warn">descriptive only · below the pre-registered sample floor</span></p>',
                ),
                (
                    "p",
                    "The precision probe asked what happens when the gate fires and should not have. This asks the "
                    "opposite: how often does it fail to fire when it should? The protocol was pre-registered before "
                    "the run, mirroring the precision protocol.",
                ),
                (
                    "table",
                    ["Measure", "Value"],
                    [
                        [
                            "Probes available",
                            "<b>16</b> <code>q_save_action</code> rows of the frozen v3 holdout",
                        ],
                        ["Gate fired", "<b>0 of 16</b>"],
                        ["Miss rate", "<b>100.0%</b>, Wilson CI95 [80.64, 100.00]"],
                        ["ΔRecall@5 (A_gatedctx − A)", "<b>+0.00pp</b>, CI95 [0.00, 0.00]"],
                        ["McNemar", "0 gained, 0 lost, p = 1.0, 0 discordant pairs"],
                        [
                            "Protocol self-check",
                            '<span class="badge pass">pass</span> — the untriggered subset must move exactly 0.00pp, and it '
                            "did",
                        ],
                        ["Verdict", "<b>none.</b> 16 &lt; the pre-registered floor of 25"],
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "That zero is structural, not reassuring",
                    "<p>The gate never fired, so both arms ran identical code and produced identical per-query ranks. "
                    "A Δ of exactly zero with zero discordant pairs is not evidence that the gate is harmless — it is "
                    "evidence that nothing was tested. The minimum detectable effect is undefined here, because the "
                    "formula divides by the number of discordant pairs and there were none.</p>",
                ),
                (
                    "p",
                    "All sixteen phrasings are ways of saying “the one I put away” — <em>之前收起来的那个</em>, <em>the link I "
                    "set aside</em>, <em>我塞进清单里的那篇</em>. None of them contains a word in the gate's trigger "
                    "vocabulary, which currently keys on <code>保存</code>, <code>收藏</code>, <code>saved</code>, "
                    "<code>bookmark</code> and eleven others.",
                ),
                (
                    "p",
                    "The obvious move — add these sixteen phrasings to the vocabulary — is exactly what the protocol "
                    "forbids, because selecting a vocabulary on the probes that measure it is circular. Reaching a "
                    "verdict requires generating at least 25 probes in a new round with new seeds, at frozen "
                    "parameters, and then passing <em>both</em> the miss-rate bar and the 361-probe precision bar. "
                    "Until then the vocabulary is unchanged.",
                ),
            ],
        ),
        (
            "five",
            "Comparing five candidate changes",
            [
                (
                    "p",
                    "After W1 killed fusion, five obvious repairs were each measured rather than argued about.",
                ),
                (
                    "table",
                    ["Candidate", "What was measured", "Verdict"],
                    [
                        [
                            "Drop the lexical facets entirely",
                            "80.1% of content-style and 46.3% of vague queries need no vector at all — but <b>6.05%</b> (29 "
                            "of 479) are findable <em>only</em> lexically, above the pre-registered 5% line.",
                            '<span class="badge fail">kept</span>',
                        ],
                        [
                            "Weight the facets instead of flat RRF",
                            "A coincidence on two weak facets scores 0.0279; certainty on one strong facet scores 0.0164.",
                            '<span class="badge info">explains the loss</span>',
                        ],
                        [
                            "Fix the trigram facet on Chinese",
                            "It matched 25 of 211 Chinese queries (11.85%). After the fix, 202 of 211 (95.73%). Overall "
                            "Recall@5: <b>unchanged</b>.",
                            '<span class="badge warn">fixed, no gain</span>',
                        ],
                        [
                            "Raise the boost ceiling",
                            "<code>MAX_BOOST = 1.60</code> crosses 79.7% of the score range in config A but only 20.9% in "
                            "C/D. Equal displacement power would need 6.03. 66.3% of candidates get exactly 1.0.",
                            '<span class="badge info">measured, not shipped</span>',
                        ],
                        [
                            "Turn on the intent facet",
                            "19 of 50 generated intents (38%) were plausible, below the pre-registered 50% line. The "
                            "information word is absent from the page 34.0% of the time overall and <b>62.4%</b> on "
                            "body-poor pages.",
                            '<span class="badge fail">off</span>',
                        ],
                    ],
                ),
                (
                    "p",
                    "The third row is the interesting one. A real bug was found and fixed — the trigram facet went "
                    "from useless on Chinese to working — and end-to-end recall did not move. A fix that is genuinely "
                    "a fix and changes no outcome is a normal result, and reporting it is the only thing that keeps "
                    "the other four honest.",
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep · Round-trip differences",
            [
                (
                    "raw",
                    '<p><span class="badge fail">roundtrip_unfaithful</span> <span class="tiny">2,376 bookmarks · 616 '
                    "holdout queries · protocol frozen first</span></p>",
                ),
                (
                    "p",
                    "Question: if a library is pushed through the karakeep bridge and read back, is it the same "
                    "library? Three criteria were registered first.",
                ),
                (
                    "table",
                    ["Criterion", "Bar", "Measured", "Verdict"],
                    [
                        [
                            "Metric fidelity",
                            "|ΔRecall@5| ≤ 3pp with CI95 inside ±5pp",
                            "<b>−0.81pp</b>, CI95 [−2.44, +0.81]",
                            '<span class="badge pass">pass</span>',
                        ],
                        [
                            "Rank fidelity",
                            "median overlap@5 ≥ 4 <b>and</b> top-1 agreement ≥ 80%",
                            "median 4.0, top-1 <b>79.06%</b>",
                            '<span class="badge fail">fail by 0.94pp</span>',
                        ],
                        [
                            "Read-path equivalence",
                            "HTTP and native identical over 616×2",
                            "0 mismatches",
                            '<span class="badge pass">pass</span>',
                        ],
                    ],
                ),
                ("h3", "The cause is fully attributed"),
                (
                    "ul",
                    [
                        "Bodies survive byte-identical: 1,876 of 1,876.",
                        "Summaries survive: 2,375 of 2,375, 100%.",
                        "Topics match <b>0%</b> and entities <b>1.18%</b> — because karakeep's tags are the browser's "
                        "<em>folder</em> labels, not topics.",
                        "The keyword line collapses from <b>19,016 distinct terms to 13</b>; mean terms per page falls "
                        "from 10.32 to 0.76; the most common tag is <code>未分类</code> on 1,124 pages.",
                        "Vectors move by a median cosine of 0.9846 — small, and enough to reshuffle a top-5.",
                    ],
                ),
                (
                    "p",
                    "Grafting the source enrichment back produced 2,376 of 2,376 byte-identical embed texts, residual "
                    "zero, which closes the attribution. Re-running <code>facetmark index</code> repairs it: 0 "
                    "karakeep bodies needed re-fetching, all 2,376 rows re-enriched, and the graph came back matching "
                    "except for 212 semantic edges (26,485 against 26,697).",
                ),
                (
                    "callout",
                    "info",
                    "What this means in practice",
                    "<p>Metric-level conclusions transfer to a karakeep-enriched library. Rank-level ones do not, "
                    "until you re-index. If you run the bridge, run <code>facetmark index</code> afterwards.</p>",
                ),
            ],
        ),
        (
            "decay",
            "Time decay · Two experiments",
            [
                (
                    "p",
                    "The decay layer demotes pages that look stale. Round one measured it and found exactly nothing:",
                ),
                (
                    "table",
                    ["Round one", "Value"],
                    [
                        ["ΔRecall@5", "<b>0.0000pp</b>, CI95 [0.00, 0.00]"],
                        ["Cold pages", "8 of 2,376"],
                        ["Cold pages among the 230 targets", "0"],
                    ],
                ),
                (
                    "callout",
                    "bad",
                    "Round one measured an instrument that was switched off",
                    "<p>The <code>health</code> table had <b>zero rows</b> and <code>open_count</code> was 0 for all "
                    "2,376 pages. The layer could not fire because it had nothing to read. A clean zero from a "
                    "correctly executed protocol, measuring nothing.</p>",
                ),
                ("p", "Round two ran the same bytes with a local health check first."),
                (
                    "table",
                    ["Round two", "Shipped (0.02)", "Reachable (0.0)"],
                    [
                        ["Recall@5", "<b>0.5860</b>", "0.5714"],
                        ["Recall@1", "0.4237", "0.4188"],
                        ["Rescue valve open", "417 of 616", "0 of 616"],
                        ["Health rows", "2,376 (was 0)", "2,376"],
                        ["Cold pages", "73 — 3.07% (was 8, 0.34%)", "73"],
                        ["Cold ∩ the 230 targets", "8, across 19 queries", "8"],
                    ],
                ),
                (
                    "p",
                    'ΔRecall@5 went from <code>+0.0000pp</code> in round one to <b class="nowrap">−1.4610pp</b> CI95 '
                    "[−2.5974, −0.4870] in round two. The mechanism is countable: of 37 rank changes, <b>12 fell out "
                    "of the top 20 entirely</b> — 10 of those had been in the top 5 and 5 had been rank 1. Twenty-four "
                    "rose, 21 of them by a single place, and exactly <b>1</b> crossed into the top 5. Net −10 + 1 = "
                    "−9, and −9/616 = −1.4610pp.",
                ),
                ("h3", "Why the threshold still has not changed"),
                ("p", "Two bugs are cancelling, and the cancellation is load-bearing."),
                (
                    "ul",
                    [
                        "<b>Bug one:</b> the cold-layer condition treats “the URL died” as “the saved copy is useless”. "
                        "But facetmark stores the body. A dead URL is precisely when the local snapshot matters most, and "
                        "<code>drifted</code> is worse still, because then the snapshot is the only surviving record.",
                        "<b>Bug two:</b> with <code>rrf_k = 60</code>, one unit-weight facet tops out at <code>1/61 = "
                        "0.016393</code>, which is below the rescue threshold of <code>0.02</code>. In the shipped "
                        "single-facet profile the rescue valve is therefore <em>always</em> open and the demotion has "
                        "never once executed.",
                        "Remove either one alone and results get measurably worse. Both are pinned by "
                        "<code>tests/test_decay_reach.py</code> so neither can be quietly “cleaned up”.",
                    ],
                ),
                (
                    "p",
                    "What changed instead was the instrumentation. <code>cold_census()</code> now reports the three "
                    "conditions separately, and <code>facetmark stats</code> and <code>facetmark health --check</code> "
                    "name <code>never_opened_selects_everything</code> and <code>health_never_checked</code> out "
                    "loud.",
                ),
                (
                    "p",
                    "One more detail worth keeping: 4 of the 8 damaged targets have <code>char_count = 0</code> and "
                    "are still retrieved correctly, through title and lexical facets. Body loss is not the same as "
                    "retrieval loss.",
                ),
            ],
        ),
        (
            "real",
            "A real library · End-to-end record",
            [
                (
                    "p",
                    "Synthetic corpora hide integration failures. This is one actual browser export, imported and "
                    "indexed with the shipped code path.",
                ),
                (
                    "table",
                    ["Stage", "Result"],
                    [
                        [
                            "The file",
                            "<code>favorites_2026_8_4.html</code>, 1.7 MB, 96 folders, 4 levels deep",
                        ],
                        [
                            "Import",
                            "parsed 1,710 → inserted 1,701, 9 duplicates merged, 1 non-indexable",
                        ],
                        [
                            "Index (no page fetching)",
                            "322 saving sessions, 9,132 edges, 1,386 distinct domains, 1,775 vectors",
                        ],
                        ["Median query latency", "2,265 ms"],
                    ],
                ),
                (
                    "p",
                    "The latency number is honest and unflattering: it is a cold, unfetched index on a laptop, and it "
                    "is the number that would be quietly omitted from a launch post.",
                ),
            ],
        ),
        (
            "gaps",
            "Limits and untested scenarios",
            [
                (
                    "ul",
                    [
                        "<b>Whether anyone else's queries look like these.</b> Every query set was written by the author "
                        "of the tool. This is the single largest threat to every number on this page and no amount of "
                        "bootstrapping touches it.",
                        "<b>Whether the decay layer helps</b>, because in the shipped profile it cannot fire at all.",
                        "<b>Whether the intent facet would help a different library.</b> It was measured on this one, "
                        "generated by one model, and it lost.",
                        "<b>Whether the karakeep bridge works against a live karakeep.</b> The contract is pinned and "
                        "replayed; a running instance has never been tested.",
                        "<b>Whether the reranker helps with a real cross-encoder.</b> What ships offline is term overlap. "
                        "An ablation run under that reranker measures the harness, not the idea, and must not be quoted "
                        "as evidence that reranking works.",
                        "<b>Long-term behaviour.</b> Every measurement is a snapshot. Nobody has run this for a year and "
                        "watched what a growing library does to the session clustering.",
                    ],
                ),
                (
                    "callout",
                    "info",
                    "How to help",
                    "<p>Write 100 queries against your own library, with the target URL for each, as JSONL. Run "
                    "<code>facetmark eval --no-build --queries yours.jsonl --rungs A,C,full</code>. Post the JSON. "
                    "That single contribution is worth more than any feature request, and it is the one thing the "
                    "author structurally cannot do.</p>",
                ),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# the web page
# --------------------------------------------------------------------------

EN["nav"]["webui"] = "Web UI"
EN["nav"]["config"] = "Settings"
EN["nav"]["integrations"] = "Connect"

EN["meta"]["webui"] = (
    "facetmark · Using the app",
    "Search, inspect sources and manage your library. Learn which view to use and how to interpret its "
    "data.",
)
EN["meta"]["config"] = (
    "facetmark · Models and configuration",
    "Locate the active configuration, choose models and test the connection. Examples cover provider "
    "setup, restarts, reindexing and common errors.",
)
EN["meta"]["integrations"] = (
    "facetmark · Integrations and backups",
    "Connect the browser extension, AI clients and command line to your library, and prepare recoverable "
    "backups for migration.",
)

EN["webui"] = {
    "h1": "Using the app",
    "lede": (
        "Search, inspect sources and manage your library. Learn which view to use and how to interpret its "
        "data."
    ),
    "toc_title": "On this page",
    "sections": [
        (
            "open",
            "Open and pair",
            [
                ("cb", "shell", "facetmark serve"),
                (
                    "p",
                    "Visit <code>http://127.0.0.1:8787/app</code> on the service machine for automatic pairing. From "
                    "another device or hostname, enter the token printed by <code>facetmark token</code> on the "
                    "server.",
                ),
                ("p", '<a href="quickstart.html#server">Server and SSH administration steps</a>'),
            ],
        ),
        (
            "firstrun",
            "First run",
            [
                (
                    "steps",
                    [
                        "Import: select browser-exported HTML or Chromium Bookmarks JSON. The file is sent to the "
                        "facetmark service you are connected to.",
                        "Models: choose Set up the model, fill in the endpoint and models, then use Test connection to "
                        "check chat and embeddings separately. Click Save afterwards. You can begin with lexical search.",
                        "Index: return to First run and choose Build the index. Check text coverage and vector counts "
                        "afterwards. If it fails, note the error, correct the configuration and retry.",
                    ],
                ),
                (
                    "callout",
                    "",
                    "When connecting remotely",
                    "<p>Paired remote connections can search the library. Import, configuration and indexing "
                    "administration require loopback access or an SSH tunnel.</p>",
                ),
            ],
        ),
        (
            "tabs",
            "Choose a task",
            [
                (
                    "table",
                    ["View", "Use it to"],
                    [
                        [
                            "Search",
                            "Find pages by words or a description; adjust modes in Search options and narrow by save date.",
                        ],
                        [
                            "Ask",
                            "Build an answer from retrieved, stored summaries or snippets and check the numbered sources.",
                        ],
                        ["Library", "Browse save activity and inspect text and vector coverage."],
                        [
                            "Sessions",
                            "Find bookmarks saved together and recover your reading context.",
                        ],
                        ["System", "Inspect service status, fetch queues and link health."],
                        ["Settings", "Manage models and indexing over loopback or SSH forwarding."],
                    ],
                )
            ],
        ),
        (
            "read",
            "Read a search result",
            [
                (
                    "p",
                    "Open the original page from its title, or inspect its summary, topics and related pages in "
                    "details. Badge colours identify retrieval sources consistently; a high rank is not a fact check.",
                ),
                (
                    "ul",
                    [
                        "Content: matched by an embedding of stored text, which can include a title-derived summary.",
                        "Intent: matches a model-generated candidate question, not your past searches.",
                        "Words / substrings: literal matches, useful for terms, URLs and Chinese phrases.",
                        "Cooled: ranked lower but retained. Related results are separate for further exploration.",
                    ],
                ),
            ],
        ),
        (
            "keys",
            "Shortcuts and reading preferences",
            [
                (
                    "table",
                    ["Action", "Result"],
                    [
                        ["<kbd>/</kbd>", "Focus search when you are not typing in another field."],
                        ["<kbd>↑</kbd> / <kbd>↓</kbd>", "Select suggestions when open, otherwise move through results. IME candidate keys are left alone."],
                        ["<kbd>Enter</kbd>", "Submit Search or Ask, or accept the selected suggestion. Confirming IME text does not submit."],
                        ["<kbd>Esc</kbd>", "Close suggestions or details first; with neither open on Search, clear the query."],
                        [
                            "Language / theme",
                            "Choose Chinese or English. The app cycles through light, dark and system themes; the button "
                            "describes its next action.",
                        ],
                    ],
                )
            ],
        ),
        (
            "trouble",
            "No results or unavailable settings",
            [
                (
                    "p",
                    "Check that Library contains bookmarks, then inspect text and vector coverage separately. A "
                    "completed index does not mean every website allowed fetching. If Settings reports restricted "
                    "access, use the loopback or SSH address it describes.",
                ),
                ("p", '<a href="quickstart.html#trouble">Find a fix by symptom →</a>'),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------

EN["config"] = {
    "h1": "Models and configuration",
    "lede": (
        "Locate the active configuration, choose models and test the connection. Examples cover provider "
        "setup, restarts, reindexing and common errors."
    ),
    "toc_title": "On this page",
    "sections": [
        (
            "where",
            "Sources and precedence",
            [
                (
                    "p",
                    "Precedence is shown below. Start commands and the service from the same working directory; a "
                    "<code>.env</code> in that directory is also read.",
                ),
                (
                    "cb",
                    "precedence",
                    "environment variable   >   config.toml   >   built-in default",
                ),
                (
                    "p",
                    "The Settings screen shows you which of the three each value came from, and if an environment "
                    "variable is winning, the field goes read-only and says so rather than letting you write something "
                    "that will have no effect. Editing in the browser writes the file; it never touches your "
                    "environment.",
                ),
                ("cb", "where is the file", "facetmark config path"),
                (
                    "p",
                    "It is created the first time something writes to it. There is no requirement to have one — a run "
                    "with no file and no variables is a valid run with all defaults.",
                ),
                (
                    "callout",
                    "",
                    "Three settings need a restart",
                    "<p><code>embed_backend</code>, <code>embed_dim</code> and <code>local_embed_path</code> decide "
                    "the shape of the vector store. The screen saves them and then tells you plainly that they take "
                    "effect next start.</p>",
                ),
            ],
        ),
        (
            "model",
            "Connect models",
            [
                (
                    "table",
                    ["Setting", "In plain language"],
                    [
                        [
                            "<code>api_key</code>",
                            "Your key. Stored in the file, shown back to you masked, and never re-sent when you save an "
                            "unrelated field.",
                        ],
                        [
                            "<code>base_url</code>",
                            "Where the requests go. Anything speaking the OpenAI API works, including something on your own "
                            "machine.",
                        ],
                        [
                            "<code>chat_model</code>",
                            "Generates page summaries during indexing and answers with citations in Ask.",
                        ],
                        [
                            "<code>embed_model</code>",
                            "Turns text into vectors. This is the one that decides search quality.",
                        ],
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "Changing the embedding model means reindexing",
                    "<p>Vectors from two different models are not comparable. Change it and run a rebuild, or search "
                    "gets quietly worse in a way no error message will tell you about.</p>",
                ),
                (
                    "p",
                    "Open Settings over loopback or SSH, fill in the model fields and click Test connection. Testing "
                    "uses the form values without saving them. Check chat and embedding results, then click Save for "
                    "that group. Each Save handles only its own group's changes. Restart the service after saving "
                    "fields marked as requiring a restart before using them in actual jobs.",
                ),
            ],
        ),
        ("presets", "Provider examples", provider_blocks("en")),
        (
            "local",
            "Local embeddings",
            [
                (
                    "p",
                    'First install <code>python -m pip install "facetmark[local]"</code>. Model files are downloaded '
                    "once; embeddings then run on the service machine. Page fetching and any configured online chat "
                    "model still use the network.",
                ),
                (
                    "cb",
                    "local embeddings",
                    'embed_backend = "local"\nlocal_embed_path = "BAAI/bge-m3"\nembed_model = "BAAI/bge-m3"\nembed_dim = 1024',
                ),
                (
                    "p",
                    "It is slower to build and it needs the model downloaded once. Search quality is good: on a "
                    "1,024-token window bge-m3 reproduces its own vector to a cosine of 0.999976 run-to-run, which is "
                    "the property that matters for an index you keep rather than rebuild.",
                ),
                (
                    "dashed",
                    "context",
                    "what you give up",
                    [
                        (
                            "p",
                            "Two facets are built on a language model reading your pages: the questions a page could answer, "
                            "and the topic labels. With no chat model those stay empty and you are searching on body text "
                            "and full-text — still the two strongest paths, and still better than what your browser gives "
                            "you.",
                        ),
                        (
                            "p",
                            "You can also start here and add a key later. Nothing has to be thrown away; the index fills in "
                            "the parts it could not build before.",
                        ),
                    ],
                ),
            ],
        ),
        (
            "groups",
            "Concurrency, privacy and other options",
            [
                ("h3", "Vectors"),
                (
                    "table",
                    ["Setting", "In plain language"],
                    [
                        [
                            "<code>embed_backend</code>",
                            "<code>api</code> or <code>local</code>. Restart to take effect.",
                        ],
                        [
                            "<code>embed_dim</code>",
                            "How long each vector is. Must match what the model actually returns. Restart to take effect.",
                        ],
                        [
                            "<code>local_embed_path</code>",
                            "Model id or folder for the local backend. Restart to take effect.",
                        ],
                    ],
                ),
                ("h3", "How hard it pushes"),
                (
                    "table",
                    ["Setting", "In plain language"],
                    [
                        [
                            "<code>request_timeout</code>",
                            "Seconds before a call is given up on. Raise it on a slow link; lower it if a provider hangs.",
                        ],
                        [
                            "<code>fetch_concurrency</code>",
                            "How many pages are downloaded at once. Lower it if your network complains.",
                        ],
                        [
                            "<code>enrich_concurrency</code>",
                            "How many pages are sent to the model at once. This is the one to lower when you get "
                            "rate-limited.",
                        ],
                    ],
                ),
                ("h3", "What it is not allowed to look at"),
                (
                    "table",
                    ["Setting", "In plain language"],
                    [
                        [
                            "<code>privacy_excluded_domains</code>",
                            "Domains never fetched and never sent anywhere. Bank, health, work intranet. The bookmark stays; "
                            "only the title is indexed.",
                        ],
                        [
                            "<code>chat_model_fallbacks</code>",
                            "Models to try, in order, when the first one refuses.",
                        ],
                    ],
                ),
                (
                    "callout",
                    "",
                    "Set exclusions before the first fetch",
                    "<p>Exclusions restrict later processing; they do not erase previously stored bodies or backups. "
                    "Review the exclusions before importing and indexing.</p>",
                ),
            ],
        ),
        (
            "faq",
            "Connection and save errors",
            [
                (
                    "table",
                    ["Message", "What to do"],
                    [
                        [
                            "<code>401</code> / <code>invalid_api_key</code>",
                            "Key wrong, or wrong provider's key for this <code>base_url</code>. Test on the Settings screen "
                            "— it tells you which half failed.",
                        ],
                        [
                            "<code>404</code> on a model name",
                            "That name is not on that endpoint. Check the provider's model list.",
                        ],
                        [
                            "<code>429</code>",
                            "Rate limit. Lower <code>enrich_concurrency</code> and run again; finished stages are not "
                            "redone.",
                        ],
                        [
                            "<code>dim mismatch</code>",
                            "<code>embed_dim</code> disagrees with the model. Fix it, restart, rebuild.",
                        ],
                        [
                            "Chat works, embeddings 403",
                            "Check that the endpoint and account support the chosen embedding model. Use an endpoint "
                            "offering both capabilities, or configure local embeddings as above; online chat and "
                            "embeddings share the same endpoint.",
                        ],
                        [
                            "<code>unknown setting</code> on save",
                            "A typo in a key name. The writer refuses unknown keys rather than storing something that will "
                            "be silently ignored forever.",
                        ],
                    ],
                )
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# connect it to things
# --------------------------------------------------------------------------

EN["integrations"] = {
    "h1": "Integrations and backups",
    "lede": (
        "Connect the browser extension, AI clients and command line to your library, and prepare recoverable "
        "backups for migration."
    ),
    "toc_title": "On this page",
    "sections": [
        (
            "extension",
            "The browser extension",
            [
                (
                    "p",
                    "Search your bookmarks from the address bar, and save the page you are on without leaving it. The "
                    "extension talks to the same local server the web page does.",
                ),
                (
                    "steps",
                    [
                        "Start the server: <code>facetmark serve</code>.",
                        "Load the extension from <code>extension/</code> in the repository — Chrome: "
                        "<i>chrome://extensions</i>, developer mode, <i>Load unpacked</i>.",
                        "Open its options. If the server is on the default port it pairs itself; otherwise paste the "
                        "output of <code>facetmark token</code>.",
                    ],
                ),
                (
                    "callout",
                    "",
                    "Verify the connection",
                    "<p>Search for a known bookmark in the extension and verify the result. Requests go to your "
                    "configured service, which may call configured models. For remote use, check the URL, token and "
                    "browser permissions.</p>",
                ),
            ],
        ),
        (
            "mcp",
            "Claude, Cursor, and anything else speaking MCP",
            [
                (
                    "p",
                    "facetmark ships an MCP server, so an assistant can search your bookmarks as a tool instead of you "
                    "pasting links into a chat window.",
                ),
                ("cb", "run it by hand first", "facetmark mcp"),
                (
                    "cb",
                    "Claude Desktop — claude_desktop_config.json",
                    "{\n"
                    '  "mcpServers": {\n'
                    '    "facetmark": {\n'
                    '      "command": "facetmark",\n'
                    '      "args": ["mcp"]\n'
                    "    }\n"
                    "  }\n"
                    "}",
                ),
                (
                    "p",
                    "Cursor takes the same shape in its own MCP settings. If <code>facetmark</code> is not on the PATH "
                    "the editor sees, give the absolute path — that is the failure in nearly every report of “the tool "
                    "never appears”.",
                ),
                (
                    "dashed",
                    "intent",
                    "what the assistant can and cannot do",
                    [
                        (
                            "p",
                            "It can search, read a bookmark, list sittings and ask a question over your library. It cannot "
                            "delete anything, cannot write settings and cannot reach outside the database.",
                        )
                    ],
                ),
                (
                    "callout",
                    "",
                    "Verify tool access",
                    "<p>Restart the client, check that facetmark tools appear, then search for a known title. GUI "
                    "clients may not inherit your terminal PATH or environment; use an absolute executable path and "
                    "explicit environment settings when needed.</p>",
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep",
            [
                (
                    "p",
                    "If you keep your links in karakeep, facetmark can index from there instead of from a browser "
                    "export.",
                ),
                (
                    "p",
                    'See the <a href="guide.html#karakeep">karakeep integration reference</a>. Compare a small sample '
                    "against direct retrieval before connecting your full library.",
                ),
                (
                    "callout",
                    "warn",
                    "Measured, and worth knowing before you commit",
                    "<p>A round trip through karakeep's own keyword extraction cost <b>0.81 points of Recall@5</b> "
                    "(CI95 −2.44 to +0.81) and agreed with the direct index on the top result <b>79.06&nbsp;%</b> of "
                    "the time. The vocabulary collapses: 19,016 distinct terms became 13. The verdict recorded in the "
                    "repository is <code>roundtrip_unfaithful</code> — usable, not equivalent. Index the pages "
                    "directly if you can.</p>",
                ),
            ],
        ),
        (
            "cli",
            "The command line",
            [
                (
                    "p",
                    "Everything the page does, and a few things it does not. Add <code>--help</code> to any of them.",
                ),
                (
                    "table",
                    ["Command", "Does"],
                    [
                        ["<code>facetmark import</code>", "Read a bookmarks export in"],
                        [
                            "<code>facetmark browsers</code>",
                            "Find bookmark files already on this machine",
                        ],
                        ["<code>facetmark index</code>", "Build or top up the index"],
                        ["<code>facetmark reindex</code>", "Build it all again from scratch"],
                        ["<code>facetmark search</code>", "Search from the shell"],
                        ["<code>facetmark show</code>", "Everything about one bookmark"],
                        ["<code>facetmark sessions</code>", "List the sittings"],
                        ["<code>facetmark stats</code>", "The Library screen, as text"],
                        ["<code>facetmark health</code>", "Find dead links"],
                        ["<code>facetmark serve</code>", "The web page and the API"],
                        ["<code>facetmark mcp</code>", "The MCP server"],
                        ["<code>facetmark token</code>", "Print the pairing token"],
                        ["<code>facetmark config path</code>", "Where settings are written"],
                        ["<code>facetmark config show</code>", "Every setting, masked"],
                        ["<code>facetmark migrate</code>", "Bring an old database forward"],
                        ["<code>facetmark demo</code>", "A fake library, to look around in"],
                        ["<code>facetmark eval</code>", "Re-run the retrieval measurements"],
                        ["<code>facetmark version</code>", "Version"],
                    ],
                ),
                (
                    "p",
                    "<code>facetmark demo</code> is the honest way to decide whether you want this: it builds a "
                    "library out of generated pages, with no key and no network, so you can click every screen before "
                    "importing anything of your own.",
                ),
            ],
        ),
        (
            "backup",
            "Back up and restore",
            [
                ("h3", "Portable bookmark export"),
                ("cb", "shell", "facetmark export bookmarks-backup.json"),
                (
                    "p",
                    "The export preserves bookmark data; derived indexes must be rebuilt after import. Verify "
                    "restoration in a separate data directory before touching your existing library.",
                ),
                ("cb", "shell", "facetmark import bookmarks-backup.json\nfacetmark index"),
                ("h3", "Full backup including text and vectors"),
                (
                    "p",
                    "Find the database path with <code>facetmark stats</code>. Stop the service and all CLI / MCP "
                    "processes using it before copying the database. If <code>-wal</code> / <code>-shm</code> files "
                    "remain, do not discard them; use SQLite backup facilities for a consistent snapshot.",
                ),
                (
                    "callout",
                    "",
                    "After restoring",
                    "<p>Restore into a separate directory, run <code>facetmark stats</code> against that database, "
                    "compare counts and search a known title. Keep the original backup before upgrading. Store "
                    "configuration and pairing tokens separately; they can contain secrets.</p>",
                ),
            ],
        ),
    ],
}

from desktop_preview import extend as extend_desktop_preview

extend_desktop_preview(EN)

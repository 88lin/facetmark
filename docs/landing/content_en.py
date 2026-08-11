"""English copy for the facetmark site.

Every number here is copied from a document in ``docs/`` or from the output of a
command in this repository. Nothing is rounded in a flattering direction and
nothing is estimated. If a claim has no protocol behind it, it is not on the
site.
"""

REPO = "https://github.com/88lin/facetmark"

EN = {
    "code": "en",
    "html_lang": "en",
    "other_code": "zh",
    "other_label": "\u4e2d\u6587",
    "other_title": "\u5207\u6362\u5230\u4e2d\u6587",
    "skip": "Skip to content",
    "copy": {"label": "copy", "done": "copied"},
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
            "facetmark \u2014 local-first bookmark search",
            "Search your bookmarks by what the page was about, why you saved "
            "it, and what you saved next to it. One SQLite file on your "
            "machine. No account, no upload.",
        ),
        "quickstart": (
            "Quickstart \u2014 facetmark",
            "Nothing installed to a search page open in your browser: five "
            "steps, every command copy-pasteable, a picture of what you "
            "should be looking at.",
        ),
        "guide": (
            "Guide \u2014 facetmark",
            "Install, import, index, search, serve. Browser extension, MCP "
            "server, karakeep plugin, every setting and every command.",
        ),
        "measured": (
            "Measured \u2014 facetmark",
            "Every retrieval claim in facetmark, with the protocol that "
            "produced it \u2014 including the four that failed.",
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
                    ("Troubleshooting", "guide.html#trouble"),
                ],
            ),
            (
                "Interfaces",
                [
                    ("The local page", "guide.html#webui"),
                    ("Command line", "guide.html#commands"),
                    ("HTTP API", "guide.html#serve"),
                    ("MCP server", "guide.html#mcp"),
                    ("Browser extension", "guide.html#extension"),
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
            "facetmark v1.6.1 \u00b7 MIT",
            "Python 3.10+ \u00b7 one SQLite file",
            "No number on this site without a protocol behind it.",
        ],
    },
    # ----------------------------------------------------------------- index
    "index": {
        "kicker": "Local-first bookmark retrieval",
        "h1": "Find the bookmark you can only <em>half</em> remember.",
        "lede": (
            "You saved it. You remember roughly what it was about, or why you "
            "wanted it, or what else you were reading that afternoon \u2014 "
            "just not the title. facetmark indexes all three of those and "
            "searches them together, against "
            "<strong>one SQLite file on your own machine</strong>."
        ),
        "cta": [
            ("Read the guide", "guide.html", True),
            ("See what was measured", "measured.html", False),
            ("GitHub", REPO, False),
        ],
        "chips": [
            ("Python", "3.10+"),
            ("Tests", "1,188"),
            ("Licence", "MIT"),
            ("Storage", "1 SQLite file"),
            ("Upload", "none"),
        ],
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
        "prob_h2": "Three ways you look for a saved page",
        "prob_lede": (
            "A folder tree answers the first one. It has nothing to say about "
            "the other two, which is why you end up scrolling history. These "
            "are the three query types the evaluation is built on, with the "
            "Recall@5 each one actually scored on a real 1,700-bookmark "
            "library."
        ),
        "prob_cards": [
            (
                "content-style",
                "You remember the words",
                "The page said <em>sqlite-vec</em> and <em>shard</em> and you "
                "want it back. Any decent index does this.",
                "\u201csqlite-vec latency shard recall\u201d",
                "0.959",
                "Recall@5",
                "good",
            ),
            (
                "vague",
                "You remember the idea, not the words",
                "You know what problem it solved. You never knew the product "
                "name, or you have forgotten it. Folder names are no help "
                "here; this is what the content embedding is for.",
                "\u201cthat thing about keeping vectors next to the rest of my "
                "data without another server\u201d",
                "0.706",
                "Recall@5",
                "",
            ),
            (
                "episodic",
                "You remember when, and what was beside it",
                "\u201cThe same afternoon I was reading about qdrant.\u201d "
                "facetmark reconstructs saving sessions and a link graph to "
                "answer this \u2014 and it is still the weak spot. Published "
                "because it is true, not because it flatters.",
                "\u201cthe other thing I saved around the same time as "
                "qdrant\u201d",
                "0.279",
                "Recall@5",
                "bad",
            ),
        ],
        "prob_note": (
            "479 queries, one real library, config A. Full protocol and the "
            "rest of the table on the <a href=\"measured.html#w1\">measured "
            "page</a>."
        ),
        # --- facets
        "fac_label": "How it works",
        "fac_h2": "Four facets. One of them is on by default.",
        "fac_lede": (
            "facetmark builds four independent indexes over the same library "
            "and can fuse them with reciprocal rank fusion. Then it measured "
            "the fusion and found it worse than the single best facet, so the "
            "shipped default runs one facet. The other three are still there, "
            "still tested, one flag away \u2014 they are just not on, because "
            "the numbers said not to."
        ),
        "fac_head": ["Facet", "What it indexes", "Answers", "Default"],
        "fac_rows": [
            (
                "<b>Lexical</b><br><span class=\"tiny\">two FTS5 indexes</span>",
                "Character trigrams and word segments of the title, URL and "
                "body.",
                "Exact strings, identifiers, code, error messages, and Chinese "
                "text that has no spaces to tokenise on.",
                "<span class=\"badge warn\">off</span><br>"
                "<span class=\"tiny\">cost 5.4pp when fused</span>",
            ),
            (
                "<b>Content</b><br><span class=\"tiny\">dense vector</span>",
                "An embedding of the extracted page body, not the title.",
                "Paraphrase. The idea you remember when the words are gone.",
                "<span class=\"badge pass\">on</span><br>"
                "<span class=\"tiny\">W1 winner, 0.643</span>",
            ),
            (
                "<b>Intent</b><br><span class=\"tiny\">generated queries</span>",
                "Candidate questions a model writes for the page, kept only if "
                "searching them actually retrieves the page back.",
                "Why you would come looking, phrased the way you would phrase "
                "it later.",
                "<span class=\"badge warn\">off</span><br>"
                "<span class=\"tiny\">38% of intents plausible</span>",
            ),
            (
                "<b>Context</b><br><span class=\"tiny\">sessions and graph</span>",
                "Save-session clustering, domain structure, and a link graph "
                "over the library.",
                "\u201cWhat did I save around that one?\u201d",
                "<span class=\"badge pass\">graph on</span> "
                "<span class=\"badge fail\">gate off</span><br>"
                "<span class=\"tiny\">+2.09pp / \u221218.83pp</span>",
            ),
        ],
        "fac_note": (
            "Every one of those four verdicts links to a protocol, a query "
            "set and a confidence interval on the "
            "<a href=\"measured.html\">measured page</a>."
        ),
        # --- pipeline
        "pipe_label": "The pipeline",
        "pipe_h2": "From a query to a ranked list",
        "pipe_lede": (
            "Blue is what runs in the shipped default profile. Grey is built, "
            "tested and switched off. Every indexing stage is idempotent and "
            "fingerprinted, so <code>facetmark index</code> re-runs only the "
            "work whose input changed."
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
        "app_h2": "A search page, at <code>127.0.0.1:8787/app</code>",
        "app_lede": (
            "<code>facetmark serve</code> prints a URL. Open it and you get "
            "the search box, the same markers on a result row that the "
            "extension uses, and a second view that tells you what your index "
            "actually contains. Nothing to install and nothing to build "
            "\u2014 the page ships inside the Python package and is served by "
            "the same process."
        ),
        "app_shot": (
            "assets/app-search.png",
            "the facetmark search page showing ranked results and a "
            "separate group of pages saved in the same sitting",
            "<b>Search.</b> The first paint is lexical and costs no model "
            "call; the ranked answer replaces it when it arrives. Pages you "
            "saved in the same sitting arrive as their own group rather than "
            "shuffled into the ranking. This frame follows the theme of the "
            "page you are reading.",
        ),
        "app_shot_dark": (
            "assets/app-search-dark.png",
            "the same search page in dark mode",
        ),
        "app_points": [
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
        "qs_h2": "Four commands",
        "qs_lede": (
            "On a Chromium-family browser \u2014 Chrome, Edge, Brave, Vivaldi, "
            "Chromium, Opera \u2014 you do not even have to export first. "
            "<code>facetmark import</code> with no argument finds the live "
            "profile and reads it."
        ),
        "qs_code": (
            "pip install facetmark\n\n"
            "facetmark import                  # finds your browser profile; "
            "read-only\n"
            "facetmark index                   # fetch, enrich, embed, "
            "sessions, edges\n"
            'facetmark search "that post about keeping vectors in sqlite"\n'
        ),
        "qs_steps": [
            "<b>Install.</b> Python 3.10 or newer. The only heavy optional "
            "dependency is <code>sentence-transformers</code>, and only if you "
            "want local embeddings.",
            "<b>Import.</b> Nothing is ever written back to your browser. "
            "Firefox and Safari are not Chromium-family, so those two need a "
            "one-off HTML export \u2014 "
            "<a href=\"guide.html#import\">how to do that</a>.",
            "<b>Point it at a model.</b> Any OpenAI-compatible endpoint, or a "
            "local embedding model and no key at all. Without a model you "
            "still get lexical search and the session graph.",
            "<b>Index.</b> Idempotent. Run it again after adding bookmarks and "
            "it only does the new work.",
            "<b>Search.</b> Or run <code>facetmark serve</code> and use the "
            "browser extension, the HTTP API, or an MCP client.",
        ],
        "qs_offline": (
            "No API key handy? <code>facetmark demo</code> builds a synthetic "
            "60-page library offline and searches it, so you can see the shape "
            "of the output before committing anything."
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
                "Sixteen commands. <code>search</code> takes "
                "<code>--explain</code> to print which facet matched, and "
                "<code>--config</code> to run any ablation rung by name.",
                "guide.html#commands",
                "Command reference",
            ),
            (
                "http",
                "HTTP API",
                "<code>facetmark serve</code> binds 127.0.0.1:8787. "
                "Twenty-seven routes. Four are open — the root, health, "
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
                "Does anything get uploaded?",
                "<p>Two things leave your machine, both of which you control. "
                "Page fetching goes to the sites you bookmarked. Enrichment "
                "and embedding go to whichever OpenAI-compatible endpoint you "
                "configured \u2014 that can be OpenAI, or a box on your "
                "desk.</p><p>Set <code>FACETMARK_EMBED_BACKEND=local</code> "
                "and leave <code>FACETMARK_API_KEY</code> empty and nothing "
                "beyond page fetching leaves the machine at all. There is no "
                "facetmark server to talk to. There is no account.</p>",
            ),
            (
                "Will it touch my browser's bookmarks?",
                "<p>No. Import is a one-way read. The importer opens the "
                "profile's <code>Bookmarks</code> file or your exported HTML, "
                "reads it, and closes it. Nothing in the codebase writes to a "
                "browser profile.</p><p>Nothing is deleted on the facetmark "
                "side either. The decay layer demotes stale pages in the "
                "ranking; it never removes a row.</p>",
            ),
            (
                "Can I use it with no LLM at all?",
                "<p>Yes, and it will be worse, and it will tell you so. "
                "Without a model you keep both lexical facets and the whole "
                "session and domain graph. You lose the content facet \u2014 "
                "the one that measured best \u2014 and the intent facet.</p>"
                "<p>A middle path: run a local embedding model for the content "
                "facet and skip the chat model. You lose enrichment summaries "
                "and generated intents, keep paraphrase search.</p>",
            ),
            (
                "What does indexing cost?",
                "<p>Dominated by enrichment: roughly one small chat call per "
                "page. On a cheap model, 1,700 pages costs cents. Embedding is "
                "cheaper still, and free if you run it locally.</p><p>Wall "
                "time is dominated by <em>fetching</em>, not by models. "
                "facetmark honours robots.txt and rate-limits itself per "
                "domain on purpose. <code>--no-fetch</code> indexes titles "
                "only and finishes in seconds.</p>",
            ),
            (
                "Why is the default only using one facet?",
                "<p>Because four-facet fusion was measured on 479 real queries "
                "and came out 5.4 points of Recall@5 <em>behind</em> the "
                "content facet on its own, at 3.5\u00d7 the latency.</p>"
                "<p>The mechanism is written up: flat-weight RRF lets a "
                "coincidence on two weak facets (0.0279) outvote confidence on "
                "one strong facet (0.0164). The facets still exist and are "
                "still tested. <code>--config C</code> turns them all on if "
                "you want to see it for yourself.</p>",
            ),
            (
                "Is this a product?",
                "<p>No. It is a tool with an evaluation harness attached, and "
                "the harness is the point. Every default that changed has a "
                "protocol, a pre-registered criterion and a confidence "
                "interval behind it, and four of those protocols killed the "
                "feature that motivated them.</p><p>The largest missing piece "
                "is stated on the measured page: every query set so far was "
                "written by the author, which is the one bias no amount of "
                "bootstrapping fixes.</p>",
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
                "And no default change without a query set that was frozen "
                "before the run.",
            ),
        ],
        # --- final cta
        "end_h2": "Start with four commands, or read the numbers first.",
        "end_p": (
            "The guide covers install, all four browsers, both provider "
            "setups, the extension, MCP and the karakeep plugin. The measured "
            "page covers every retrieval claim in the project, including the "
            "ones that failed."
        ),
        "end_cta": [
            ("Read the guide", "guide.html", True),
            ("See what was measured", "measured.html", False),
        ],
    },
}



# ----------------------------------------------------------- quickstart ----

EN["quickstart"] = {
    "h1": "Quickstart",
    "lede": (
        "Nothing installed, to a search page open in your browser. Five steps, "
        "every command copy-pasteable, and a picture of what you should be "
        "looking at when it works. No prior knowledge of embeddings, vectors "
        "or retrieval is assumed \u2014 and nothing here needs any."
    ),
    "toc_title": "Five steps",
    "sections": [
        # ------------------------------------------------------------ install
        (
            "install",
            "Install it",
            [
                ("p",
                 "You need Python 3.10 or newer, on Windows, macOS or Linux. "
                 "Check with <code>python --version</code>; if that prints "
                 "3.9 or an error, install Python first from "
                 "<a href=\"https://www.python.org/downloads/\" "
                 "rel=\"noopener\">python.org</a>."),
                ("cb", "shell", "pip install facetmark"),
                ("p",
                 "That is the whole install. There is no separate server to "
                 "run, no database to create, no account to make. Confirm it "
                 "landed:"),
                ("cb", "shell", "facetmark --version"),
                ("callout", "info", "If the shell says \u201ccommand not found\u201d",
                 "<p>pip installed it somewhere that is not on your "
                 "<code>PATH</code>. <code>python -m facetmark --version</code> "
                 "works regardless, and every command on this page can be "
                 "written that way.</p>"),
            ],
        ),
        # ------------------------------------------------------------- import
        (
            "import",
            "Bring your bookmarks in",
            [
                ("p",
                 "On Chrome, Edge, Brave, Vivaldi, Chromium or Opera you do "
                 "not have to export anything. Close the browser first \u2014 "
                 "it holds the file open \u2014 then:"),
                ("cb", "shell", "facetmark import"),
                ("p",
                 "It finds the profile, reads the bookmarks file and prints "
                 "how many it took. Firefox and Safari are not in that family, "
                 "so those two need a one-off export to HTML first "
                 "(<a href=\"guide.html#import\">how to do that</a>) and then "
                 "the path:"),
                ("cb", "shell", "facetmark import ~/Downloads/bookmarks.html"),
                ("callout", "info", "This never writes to your browser",
                 "<p>Import is a one-way read: open the file, read it, close "
                 "it. Nothing in facetmark writes to a browser profile, and "
                 "nothing you do here can change or delete a bookmark you "
                 "have.</p>"),
            ],
        ),
        # ------------------------------------------------------------- models
        (
            "model",
            "Point it at a model \u2014 or skip this",
            [
                ("p",
                 "Searching \u201cby meaning\u201d needs something that turns "
                 "text into numbers. You have three ways to get one, and the "
                 "third is to do without."),
                ("h3", "A hosted API"),
                ("p",
                 "Any OpenAI-compatible endpoint. Put this in "
                 "<code>~/.facetmark/.env</code> \u2014 the file is created "
                 "for you on first run:"),
                ("cb", "dotenv",
                 "FACETMARK_API_BASE=https://api.openai.com/v1\n"
                 "FACETMARK_API_KEY=sk-your-key"),
                ("callout", "warn", "The single most common setup mistake",
                 "<p>The base URL must end in <code>/v1</code>. Without it "
                 "every model call returns 404, and the error surfaces as a "
                 "provider error, so it reads like a bad key.</p>"),
                ("h3", "A model on your own machine"),
                ("p",
                 "No key, nothing leaves the machine except the page fetches "
                 "themselves:"),
                ("cb", "dotenv", "FACETMARK_EMBED_BACKEND=local"),
                ("p",
                 "This downloads a small sentence-transformers model the first "
                 "time it runs."),
                ("h3", "Neither"),
                ("p",
                 "Skip this step entirely and you still get keyword search "
                 "over titles, folders and addresses, plus the session graph "
                 "\u2014 which of your bookmarks were saved in the same "
                 "sitting. You lose search by meaning. You can add a model "
                 "later and re-run the next step; nothing has to be redone."),
            ],
        ),
        # -------------------------------------------------------------- index
        (
            "index",
            "Build the index",
            [
                ("p",
                 "This is the slow step, and the only slow step. It fetches "
                 "each page, extracts the text, summarises it if you "
                 "configured a chat model, embeds it, and works out which "
                 "bookmarks were saved together."),
                ("cb", "shell", "facetmark index"),
                ("p",
                 "Wall time is dominated by <em>fetching</em>, not by models: "
                 "facetmark honours robots.txt and rate-limits itself per "
                 "site on purpose. A few thousand bookmarks is a coffee, not a "
                 "second. In a hurry, or just want to see it work:"),
                ("cb", "shell", "facetmark index --no-fetch"),
                ("p",
                 "That indexes titles only and finishes in seconds. Run "
                 "<code>facetmark index</code> properly later \u2014 it is "
                 "idempotent, so it picks up exactly the work that is still "
                 "missing and skips everything already done."),
                ("callout", "info", "You can stop it and start it again",
                 "<p>Progress is written as it goes. Interrupting with "
                 "<kbd>Ctrl</kbd>+<kbd>C</kbd> loses at most the page in "
                 "flight, and re-running continues rather than "
                 "restarting.</p>"),
            ],
        ),
        # --------------------------------------------------------------- open
        (
            "open",
            "Open the page",
            [
                ("cb", "shell", "facetmark serve"),
                ("p",
                 "It prints the address. Open the second line in a browser:"),
                ("cb", "shell",
                 "facetmark 1.6.1  http://127.0.0.1:8787\n"
                 "open the search page:     http://127.0.0.1:8787/app"),
                ("p",
                 "That is the whole interface. Type a question the way you "
                 "would say it out loud \u2014 you do not have to remember the "
                 "title, and you do not have to get the words right."),
                ("shot",
                 "assets/app-search.png",
                 "the facetmark search page with a query typed and ranked "
                 "results below it",
                 "<b>What you should see.</b> Results appear as you type, "
                 "starting with a plain keyword match that costs nothing, "
                 "then re-ranked once the model answers. This frame follows "
                 "the theme of the page you are reading.",
                 "assets/app-search-dark.png",
                 "the same search page in dark mode"),
                ("p",
                 "The second view answers the question everybody has at this "
                 "point \u2014 <em>did that actually work?</em> Click "
                 "<b>Library</b> in the header."),
                ("shot",
                 "assets/app-library.png",
                 "the facetmark library view listing bookmark, vector, "
                 "session and edge counts",
                 "<b>Library.</b> If <em>Content vectors</em> is zero, search "
                 "by meaning is not on yet: either no model is configured, or "
                 "<code>facetmark index</code> has not finished. If "
                 "<em>Bookmarks</em> is zero, the import did not land.",
                 "assets/app-library-dark.png",
                 "the same library view in dark mode"),
                ("callout", "info", "Leave it running",
                 "<p><code>facetmark serve</code> is a foreground process; the "
                 "page only works while it is up. It binds 127.0.0.1, which "
                 "means your machine and nothing else on the network. The "
                 "browser extension, the API and MCP clients all talk to this "
                 "same process \u2014 see <a href=\"guide.html#webui\">the "
                 "guide</a>.</p>"),
            ],
        ),
        # --------------------------------------------------------------- read
        (
            "read",
            "Read a result",
            [
                ("p",
                 "Each row says why it is there. Hovering a marker explains it "
                 "in the page; this is the same thing in one table."),
                ("table",
                 ["On the row", "Means"],
                 [["<span class=\"chip mk\">about</span>",
                   "The page\u2019s own text matched \u2014 by meaning, not by "
                   "keyword. This is the one that finds a page whose words you "
                   "do not remember."],
                  ["<span class=\"chip mk\">words</span>",
                   "A whole word in the title, folder or address matched."],
                  ["<span class=\"chip mk\">substring</span>",
                   "Part of a word matched, which is what makes half-typed and "
                   "Chinese queries work."],
                  ["<span class=\"chip mk\">asked as</span>",
                   "A question this page was saved to answer matched."],
                  ["<span class=\"badge warn mk\">cold</span>",
                   "Saved long ago, never opened, and something newer looks "
                   "like it replaced it. Pushed down the list, never "
                   "deleted."]]),
                ("p",
                 "Below the ranked list there is sometimes a second, separate "
                 "group headed <b>saved around these</b>. Those are not "
                 "answers to your query \u2014 they are pages you saved in the "
                 "same sitting as something above, which is often how you "
                 "actually remember where a page was. They are kept apart on "
                 "purpose and never mixed into the ranking."),
                ("p",
                 "<b>Load more</b> at the bottom fetches the next page of the "
                 "same ranking rather than searching again, so the order you "
                 "have already read cannot shuffle underneath you. The counter "
                 "above the list says which slice you are looking at."),
            ],
        ),
        # ------------------------------------------------------------ trouble
        (
            "trouble",
            "When it goes wrong",
            [
                ("h3", "The page says it needs a token"),
                ("p",
                 "You are not reaching it over 127.0.0.1 \u2014 a LAN address, "
                 "a hostname or a reverse proxy all look the same to the "
                 "check. Run <code>facetmark token</code>, paste the value "
                 "into the field once, and the browser remembers it. "
                 "<a href=\"guide.html#webui\">Why that check exists.</a>"),
                ("h3", "The page will not load at all"),
                ("p",
                 "<code>facetmark serve</code> has to still be running in a "
                 "terminal. If it exited with <code>address already in use</code>, "
                 "something else has 8787: run "
                 "<code>facetmark serve --port 8788</code> and open that port "
                 "instead."),
                ("h3", "Search finds nothing, or only exact words"),
                ("p",
                 "Open <b>Library</b>. <em>Content vectors</em> at zero means "
                 "search by meaning is not on: no model configured, or "
                 "<code>facetmark index</code> has not run to completion. A "
                 "non-empty <em>fetch queue</em> means indexing is still "
                 "working through your library and results will keep "
                 "improving."),
                ("h3", "Every model call returns 404"),
                ("p",
                 "The base URL is missing <code>/v1</code>. This is the most "
                 "common failure by a wide margin."),
                ("h3", "Where is my data?"),
                ("p",
                 "One folder: <code>~/.facetmark</code> on macOS and Linux, "
                 "<code>%USERPROFILE%\\.facetmark</code> on Windows. Inside it "
                 "is a single SQLite file plus the pairing token. Move it, "
                 "back it up, or copy it to another machine \u2014 it is the "
                 "whole state. <code>FACETMARK_DATA_DIR</code> puts it "
                 "somewhere else."),
                ("h3", "How do I delete everything?"),
                ("p",
                 "Delete that folder. There is no uninstall step and nothing "
                 "outside it \u2014 no registry keys, no browser changes, no "
                 "account anywhere. <code>pip uninstall facetmark</code> "
                 "removes the program."),
                ("h3", "Something else"),
                ("p",
                 "<code>facetmark stats</code> prints what the index actually "
                 "contains, which resolves most confusion, and the "
                 "<a href=\"guide.html#trouble\">guide has a longer "
                 "troubleshooting list</a>. Beyond that, "
                 "<a href=\"" + REPO + "/issues\">open an issue</a>."),
            ],
        ),
    ],
}

# ---------------------------------------------------------------- guide ----

EN["guide"] = {
    "h1": "Guide",
    "lede": (
        "Install to first search in four commands, then everything else: all "
        "four browsers, both ways of reaching a model, the HTTP API, the "
        "browser extension, MCP, the karakeep plugin, every setting and every "
        "command."
    ),
    "toc_title": "On this page",
    "sections": [
        # ------------------------------------------------------------ install
        (
            "install",
            "Install",
            [
                ("p",
                 "Python 3.10 or newer, on Windows, macOS or Linux. The base "
                 "install has no compiled machine-learning dependency; "
                 "vector search comes from <code>sqlite-vec</code>, which is "
                 "a SQLite extension."),
                ("cb", "shell",
                 "pip install facetmark\n"
                 "# or, if you use uv:\n"
                 "uv pip install facetmark\n\n"
                 "facetmark version"),
                ("h3", "With local embeddings"),
                ("p",
                 "Only needed if you want to embed pages on your own machine "
                 "instead of through an endpoint. This pulls in PyTorch and "
                 "<code>sentence-transformers</code>, which is a few hundred "
                 "megabytes."),
                ("cb", "shell", 'pip install "facetmark[local]"'),
                ("h3", "From source"),
                ("cb", "shell",
                 "git clone https://github.com/88lin/facetmark\n"
                 "cd facetmark\n"
                 "python -m venv .venv && . .venv/bin/activate\n"
                 'pip install -e ".[dev]"\n\n'
                 "pytest -q                 # 1,188 tests\n"
                 "ruff check src tests scripts"),
                ("callout", "warn", "Do not reformat the codebase",
                 "<p>It is hand-formatted. <code>ruff check</code> is part of "
                 "CI; <code>ruff format</code> is not, and running it "
                 "produces a diff nobody wants to review.</p>"),
                ("h3", "Where your data lives"),
                ("p",
                 "One directory, chosen per platform, holding one SQLite "
                 "file. Override it with <code>FACETMARK_DATA_DIR</code>, or "
                 "point any command at a specific file with "
                 "<code>--db</code>."),
                ("table",
                 ["Platform", "Default data directory"],
                 [["Windows", "<code>%LOCALAPPDATA%\\facetmark\\</code>"],
                  ["Linux / macOS", "<code>~/.local/share/facetmark/</code>"],
                  ["Any, if <code>XDG_DATA_HOME</code> is set",
                   "<code>$XDG_DATA_HOME/facetmark/</code>"]]),
                ("p",
                 "Inside it: <code>facetmark.db</code> and "
                 "<code>pairing-token.txt</code>. That is the whole "
                 "installation footprint. Deleting the directory uninstalls "
                 "the data."),
                ("h3", "Try it with no key and no network"),
                ("p",
                 "<code>facetmark demo</code> generates a synthetic library, "
                 "indexes it with a deterministic offline provider, and runs "
                 "three searches against it. It is how the terminal on the "
                 "front page was recorded."),
                ("cb", "shell", "facetmark demo --size 60"),
            ],
        ),
        # ------------------------------------------------------------- import
        (
            "import",
            "Get your bookmarks in",
            [
                ("p",
                 "Import is one-way and read-only. facetmark reads a browser "
                 "profile or an exported file, and never writes to either."),
                ("h3", "Chromium-family: no export needed"),
                ("p",
                 "Chrome, Edge, Brave, Vivaldi, Chromium, Opera and Opera GX "
                 "all keep bookmarks in a JSON file that facetmark can find "
                 "on its own. Reading it is safe while the browser is "
                 "running."),
                ("cb", "shell",
                 "facetmark browsers        # what it can see\n"
                 "facetmark import          # import, if there is exactly one"),
                ("p",
                 "If more than one profile is installed, the choice is not "
                 "guessed \u2014 importing the wrong person's bookmarks is "
                 "worse than one extra command. The candidates are printed "
                 "and you pass the one you want:"),
                ("cb", "shell",
                 "facetmark import "
                 '"$HOME/.config/google-chrome/Default/Bookmarks"'),
                ("h3", "Firefox and Safari: export to HTML first"),
                ("table",
                 ["Browser", "Where the export lives"],
                 [["Firefox",
                   "Bookmarks \u2192 Manage Bookmarks \u2192 Import and "
                   "Backup \u2192 <b>Export Bookmarks to HTML</b>"],
                  ["Safari",
                   "File \u2192 Export \u2192 <b>Bookmarks</b>"],
                  ["Chrome / Edge (manual route)",
                   "<code>chrome://bookmarks</code> \u2192 \u22ee \u2192 "
                   "<b>Export bookmarks</b>"],
                  ["Anything else",
                   "Any Netscape-format <code>bookmarks.html</code> works. It "
                   "is a 1994 format and everyone still writes it."]]),
                ("cb", "shell", "facetmark import ~/Downloads/bookmarks.html"),
                ("h3", "What import reports"),
                ("p",
                 "The same command handles Netscape HTML and Chrome JSON, and "
                 "prints what it did rather than a spinner. On one real "
                 "1.7&nbsp;MB export with 96 folders nested four deep, it "
                 "parsed 1,710 entries, inserted 1,701, merged 9 duplicates "
                 "and skipped 1 as non-indexable."),
                ("table",
                 ["Field", "Meaning"],
                 [["<code>parsed</code>", "Entries found in the file."],
                  ["<code>inserted</code> / <code>updated</code>",
                   "New rows, and existing rows whose title or folder "
                   "changed."],
                  ["<code>merged_duplicates</code>",
                   "Same URL saved twice; the earlier timestamp wins."],
                  ["<code>non_indexable</code>",
                   "<code>javascript:</code>, <code>place:</code>, "
                   "<code>file:</code> and friends."],
                  ["<code>missing_dates</code>",
                   "Entries with no save time. They still import, but they "
                   "cannot join a saving session."],
                  ["<code>privacy_skipped</code>",
                   "Skipped by <code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code>."],
                  ["<code>timestamp_unit</code>",
                   "Which epoch the source used. Chrome and Netscape disagree; "
                   "this says which one was detected."]]),
                ("callout", "info", "Exclude domains before you import",
                 "<p>Set <code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code> to a "
                 "comma-separated list and those hosts are never inserted, "
                 "never fetched and never embedded. Easier than deleting "
                 "rows afterwards.</p>"),
            ],
        ),
        # ------------------------------------------------------------- models
        (
            "models",
            "Model access",
            [
                ("p",
                 "facetmark reaches models through <b>one</b> "
                 "OpenAI-compatible endpoint. There is deliberately no "
                 "provider-specific branching anywhere in the codebase: one "
                 "<code>base_url</code> plus one <code>api_key</code> covers "
                 "OpenAI, DeepSeek, Kimi, Zhipu, SiliconFlow, Aliyun Bailian, "
                 "together.ai, Azure OpenAI, Ollama, vLLM, LM Studio and any "
                 "internal gateway that speaks the same shape."),
                ("p",
                 "Two model roles are used. A <b>chat model</b> writes "
                 "enrichment (summary, topics, entities, key points) and "
                 "candidate intent queries. An <b>embedding model</b> turns "
                 "page bodies into vectors."),
                ("h3", "Through an endpoint"),
                ("cb", "shell",
                 "export FACETMARK_API_KEY=sk-...\n"
                 "export FACETMARK_BASE_URL=https://api.openai.com/v1\n"
                 "export FACETMARK_CHAT_MODEL=gpt-4o-mini\n"
                 "export FACETMARK_EMBED_MODEL=text-embedding-3-small\n"
                 "export FACETMARK_EMBED_DIM=1536"),
                ("callout", "warn", "The base URL must end in /v1",
                 "<p>This is the single most common setup failure. A base URL "
                 "without <code>/v1</code> produces a 404 on every call, "
                 "including the first one, and the error comes from the "
                 "provider rather than from facetmark so it reads as a "
                 "credentials problem.</p>"),
                ("p",
                 "Instead of environment variables you can drop a "
                 "<code>.env</code> file next to where you run the command. "
                 "Same names, same prefix."),
                ("cb", "dotenv",
                 "FACETMARK_API_KEY=sk-...\n"
                 "FACETMARK_BASE_URL=https://api.deepseek.com/v1\n"
                 "FACETMARK_CHAT_MODEL=deepseek-chat"),
                ("h3", "Shared or free endpoints"),
                ("p",
                 "On endpoints where a listed model can be absent, out of "
                 "quota, or unable to honour <code>response_format</code>, set "
                 "a fallback chain. It is empty by default on purpose: a paid "
                 "endpoint returning an error is telling you something, and "
                 "swallowing it is worse than failing."),
                ("cb", "shell",
                 "export FACETMARK_CHAT_MODEL_FALLBACKS="
                 "deepseek-chat,qwen-plus"),
                ("p",
                 "The provider records which model actually answered each "
                 "call. Any report built on a failover chain has to publish "
                 "that mix."),
                ("h3", "Local embeddings, no key"),
                ("p",
                 "Runs the embedding model on your own machine through "
                 "<code>sentence-transformers</code>. Combined with an empty "
                 "API key, nothing except page fetching leaves the machine."),
                ("cb", "shell",
                 'pip install "facetmark[local]"\n\n'
                 "export FACETMARK_EMBED_BACKEND=local\n"
                 "export FACETMARK_EMBED_MODEL=bge-m3\n"
                 "export FACETMARK_EMBED_DIM=1024\n"
                 "export FACETMARK_LOCAL_EMBED_PATH=/path/to/bge-m3   "
                 "# unset = download\n"
                 "export FACETMARK_LOCAL_EMBED_MAX_SEQ=1024"),
                ("callout", "info", "Why the sequence length default is 1024",
                 "<p>Embedding the same document twice must land in the same "
                 "place. On bge-m3 at 1024 tokens, the minimum self-cosine "
                 "over a fixed 64-document probe set is <b>0.999976</b> with "
                 "64 of 64 documents matching themselves. At 512 tokens the "
                 "minimum falls to <b>0.9769</b>, because truncation starts "
                 "cutting different amounts off the same text. That is why "
                 "1024 is the default and why lowering it is a real "
                 "trade.</p>"),
                ("callout", "bad", "Changing the dimension invalidates everything",
                 "<p><code>FACETMARK_EMBED_DIM</code> is recorded in the "
                 "<code>meta</code> table on the first index build. A later "
                 "mismatch raises instead of silently mixing incompatible "
                 "vectors. If you change embedding model or dimension, "
                 "re-embed with <code>facetmark index --force</code>.</p>"),
                ("h3", "No model at all"),
                ("p",
                 "Everything still installs and runs. You keep both lexical "
                 "facets, saving sessions, the domain and link graph, and "
                 "link health. You lose the content facet and the intent "
                 "facet. <code>facetmark search --quick</code> is the "
                 "explicit lexical-only path and makes no model call."),
            ],
        ),
        # -------------------------------------------------------------- index
        (
            "index",
            "Build the index",
            [
                ("cb", "shell", "facetmark index"),
                ("p",
                 "One command runs every stage in order. Each stage is "
                 "idempotent and fingerprinted, so running it again after "
                 "adding fifty bookmarks does the work for fifty bookmarks, "
                 "not for the whole library."),
                ("table",
                 ["Stage", "What it does", "Needs a model?"],
                 [["<code>fetch</code>",
                   "Downloads each page, honouring robots.txt and per-domain "
                   "rate limits. Extracts a readable body.", "no"],
                  ["<code>enrich</code>",
                   "Summary, topics, entities, key points \u2014 one small "
                   "chat call per page.", "chat"],
                  ["<code>embed_content</code>",
                   "Embeds the reconstructed text of each page.", "embedding"],
                  ["<code>intents</code>",
                   "Generates candidate queries for each page.", "chat"],
                  ["<code>filter_intents</code>",
                   "Keeps an intent only if searching it retrieves the page "
                   "back. Typically a little under half survive.", "no"],
                  ["<code>embed_intents</code>",
                   "Embeds the surviving intents.", "embedding"],
                  ["<code>sessions</code>",
                   "Clusters saves into episodes by time gap, choosing the gap "
                   "by coverage \u00d7 purity lift against a shuffled "
                   "control.", "no"],
                  ["<code>edges</code>",
                   "Builds session, semantic, same-domain and supersession "
                   "edges.", "no"]]),
                ("h3", "Useful flags"),
                ("table",
                 ["Flag", "Effect"],
                 [["<code>--no-fetch</code>",
                   "Skip crawling entirely and index titles only. Seconds "
                   "instead of hours; much weaker results."],
                  ["<code>--limit N</code>",
                   "Cap bookmarks per stage. Good for a first look at what a "
                   "run will cost."],
                  ["<code>--force</code>",
                   "Ignore fingerprints and redo work already done."],
                  ["<code>--mock</code>",
                   "Deterministic offline provider. No key, no network, no "
                   "quality."],
                  ["<code>--json</code>",
                   "Machine-readable report of every stage, including "
                   "per-stage seconds."]]),
                ("h3", "How fingerprints work"),
                ("ul",
                 ["<b>Enrichment</b> is keyed on the hash of the page body. "
                  "Same body, no second chat call.",
                  "<b>Embedding</b> is keyed on the <em>reconstructed embed "
                  "text</em>, not on the body. So if enrichment changes and "
                  "the embed text changes with it, the stale vector is "
                  "detected rather than trusted \u2014 which is how the "
                  "karakeep round-trip damage was caught.",
                  "<b>Sessions and edges</b> are rebuilt from scratch each "
                  "run; they are cheap and depend on the whole library."]),
                ("p",
                 "<code>facetmark reindex</code> throws away every derived "
                 "artefact and rebuilds from the bookmarks themselves. "
                 "<code>facetmark migrate</code> brings an older database up "
                 "to the current schema, taking a snapshot first unless you "
                 "pass <code>--no-backup</code>."),
                ("h3", "What indexing costs"),
                ("p",
                 "Money is dominated by enrichment: roughly one small chat "
                 "call per page, so a 1,700-page library on a cheap model is "
                 "cents. Wall time is dominated by fetching, and fetching is "
                 "deliberately slow \u2014 <code>FETCH_PER_HOST_CONCURRENCY</code> "
                 "is 2 and there is a minimum interval between hits on one "
                 "host."),
                ("p",
                 "For a sense of scale: that real 1,700-bookmark library, "
                 "indexed with <code>--no-fetch</code>, produced 322 saving "
                 "sessions, 9,132 edges, 1,386 distinct domains and 1,775 "
                 "vectors."),
            ],
        ),
        # ------------------------------------------------------------- search
        (
            "search",
            "Search",
            [
                ("cb", "shell",
                 'facetmark search "the post about keeping vectors in sqlite"\n'
                 'facetmark search "sqlite-vec" -n 20 --explain\n'
                 'facetmark search "error EADDRINUSE" --quick'),
                ("table",
                 ["Flag", "Effect"],
                 [["<code>-n, --limit</code>", "Results to return. Default 10."],
                  ["<code>--quick</code>",
                   "Lexical only. No model call, no network, sub-millisecond."],
                  ["<code>--explain</code>",
                   "Print which facet matched each hit. The fastest way to "
                   "understand why something ranked where it did."],
                  ["<code>--config NAME</code>",
                   "Run a specific profile or ablation rung. Default "
                   "<code>full</code>."],
                  ["<code>--json</code>", "Machine-readable, including timings "
                   "per stage."]]),
                ("h3", "Profiles and rungs"),
                ("p",
                 "<code>--config</code> accepts any pre-registered rung, any "
                 "shipped profile, and about twenty exploratory ablations. "
                 "<code>facetmark eval --help</code> documents the rung "
                 "syntax; the rungs themselves are listed in "
                 "<code>search/pipeline.py</code>."),
                ("table",
                 ["Name", "Facets and stages", "Status"],
                 [["<code>A</code>", "content vector only",
                   "<span class=\"badge pass\">W1 winner \u00b7 0.643</span>"],
                  ["<code>B</code>", "content + both lexical facets",
                   "<span class=\"badge fail\">\u22125.4pp</span>"],
                  ["<code>C</code>", "all four facets", "measured"],
                  ["<code>D</code>", "all four + context + graph", "measured"],
                  ["<code>E</code>", "all four + context + graph + rerank",
                   "measured"],
                  ["<code>full</code>", "content + graph + decay",
                   "<span class=\"badge info\">default, real provider</span>"],
                  ["<code>fused</code>",
                   "all four + context + graph + rerank + decay",
                   "<span class=\"badge info\">default, mock provider</span>"]]),
                ("callout", "info", "Why the mock provider gets a different default",
                 "<p>The mock hashes text into a vector, so the content facet "
                 "\u2014 the one that wins outright on a real library \u2014 "
                 "is exactly the one that returns noise on a mock one. "
                 "Dropping the lexical facets there would leave the "
                 "deployment with nothing that works. Real embeddings get the "
                 "measurement's answer; everyone else gets the pre-gate "
                 "behaviour, which at least retrieves by words.</p>"),
                ("h3", "What the ranking is made of"),
                ("p",
                 "Selected facets each return up to "
                 "<code>CANDIDATES_PER_FACET</code> hits. Reciprocal rank "
                 "fusion combines them as <code>sum_f w_f / (k + rank_f)</code> "
                 "with <code>k = 60</code>. Then context, decay and rerank run "
                 "in that order, and one-hop graph expansion is returned as a "
                 "<em>separate group</em> \u2014 not mixed into the ranking, "
                 "because it was measured as an addition, not a "
                 "replacement."),
                ("callout", "warn", "The rank column and the score column disagree",
                 "<p>By design. The reranker reorders the top 20 but "
                 "deliberately preserves the fused score on each hit, so a "
                 "reordered list shows scores out of order. If it overwrote "
                 "them you could no longer see what fusion thought.</p>"),
                ("h3", "Reading a saving session"),
                ("cb", "shell",
                 "facetmark sessions -n 20     # recent saving episodes\n"
                 "facetmark show 412 --body    # one bookmark as JSON\n"
                 "facetmark stats              # index size and coverage"),
            ],
        ),
        # -------------------------------------------------------------- serve
        (
            "serve",
            "Serve: HTTP API and the pairing token",
            [
                ("cb", "shell", "facetmark serve        # 127.0.0.1:8787"),
                ("callout", "warn", "Loopback is not an authorisation model",
                 "<p>Every route that touches the library requires a token, "
                 "even on localhost, because any process on your machine can "
                 "reach 127.0.0.1. The open ones are <code>/</code>, "
                 "<code>/health</code>, and the two the "
                 "<a href=\"#webui\">local page</a> needs before it can send "
                 "a header \u2014 <code>/app</code>, a static file with no "
                 "data in it, and <code>/app/boot</code>, which answers only a "
                 "loopback caller asking a loopback address. "
                 "<code>facetmark serve</code> prints a warning when "
                 "<code>--host</code> is anything other than a loopback "
                 "address: the index contains your whole browsing interest "
                 "graph.</p>"),
                ("h3", "The token"),
                ("p",
                 "Minted on first run into <code>pairing-token.txt</code> in "
                 "your data directory. Send it as the "
                 "<code>x-facetmark-token</code> header."),
                ("cb", "shell",
                 "facetmark token             # print it\n"
                 "facetmark token --rotate    # invalidate the old one"),
                ("cb", "shell",
                 "TOKEN=$(facetmark token)\n\n"
                 "curl -s http://127.0.0.1:8787/health\n\n"
                 "curl -s -X POST http://127.0.0.1:8787/search \\\n"
                 "  -H 'content-type: application/json' \\\n"
                 "  -H \"x-facetmark-token: $TOKEN\" \\\n"
                 "  -d '{\"q\":\"vectors inside sqlite\",\"limit\":5}'"),
                ("h3", "POST /search"),
                ("table",
                 ["Field", "Type", "Meaning"],
                 [["<code>q</code>", "string", "The query. Required."],
                  ["<code>limit</code>", "int", "Results to return."],
                  ["<code>config</code>", "string",
                   "Profile or rung name. <code>\"\"</code> and "
                   "<code>\"full\"</code> both resolve through "
                   "<code>default_config</code>."],
                  ["<code>assist</code>", "bool",
                   "Allow the model-assisted understanding step."],
                  ["<code>expand</code>", "bool",
                   "Return the one-hop graph group alongside the hits."]]),
                ("h3", "Every route"),
                ("table",
                 ["Group", "Routes"],
                 [["Open",
                   "<code>GET /</code> \u00b7 <code>GET /health</code>"],
                  ["Local page \u2014 also open",
                   "<code>GET /app</code> \u00b7 "
                   "<code>GET /app/static/*</code> \u00b7 "
                   "<code>GET /app/boot</code>"],
                  ["Search",
                   "<code>GET /stats</code> \u00b7 <code>GET /quick</code> "
                   "\u00b7 <code>POST /search</code> \u00b7 "
                   "<code>POST /suggest</code> \u00b7 "
                   "<code>POST /synthesize</code>"],
                  ["Records",
                   "<code>GET /bookmark/{id}</code> \u00b7 "
                   "<code>GET /bookmark/{id}/related</code> \u00b7 "
                   "<code>POST /bookmark</code> \u00b7 "
                   "<code>POST /open</code>"],
                  ["Sessions",
                   "<code>GET /sessions</code> \u00b7 "
                   "<code>GET /session/{id}</code>"],
                  ["Indexing queue",
                   "<code>GET /queue/next</code> \u00b7 "
                   "<code>POST /queue/complete</code> \u00b7 "
                   "<code>GET /queue/stats</code>"],
                  ["Link health",
                   "<code>GET /link-health/summary</code> \u00b7 "
                   "<code>GET /link-health/{id}</code> \u00b7 "
                   "<code>POST /link-health/check</code> \u00b7 "
                   "<code>GET /graveyard</code>"],
                  ["karakeep bridge",
                   "<code>POST /karakeep/documents</code> \u00b7 "
                   "<code>POST /karakeep/documents/delete</code> \u00b7 "
                   "<code>POST /karakeep/search</code> \u00b7 "
                   "<code>POST /karakeep/clear</code> \u00b7 "
                   "<code>GET /karakeep/stats</code>"]]),
            ],
        ),
        # -------------------------------------------------------------- webui
        (
            "webui",
            "The local page",
            [
                ("p",
                 "<code>facetmark serve</code> also hosts a search page. It is "
                 "the one interface that needs nothing installed beyond "
                 "facetmark itself \u2014 no browser extension to load, no "
                 "editor to configure, no <code>curl</code>."),
                ("cb", "shell",
                 "facetmark serve\n"
                 "# facetmark 1.6.1  http://127.0.0.1:8787\n"
                 "# open the search page:     http://127.0.0.1:8787/app\n"
                 "# pairing token written to: ~/.facetmark/pairing-token.txt"),
                ("p",
                 "Plain HTML, CSS and ES modules inside the Python package: no "
                 "Node, no bundler, no build artefact that can go stale "
                 "against the server it talks to. Because the page is served "
                 "by the same process as the API it is same-origin, which is "
                 "also why it cannot be hosted anywhere else \u2014 CORS on "
                 "this service is restricted to browser-extension origins."),
                ("h3", "Two views"),
                ("table",
                 ["View", "Address", "What it is for"],
                 [["Search", "<code>/app#/search</code>",
                   "The query box and the ranked list. Typing paints a lexical "
                   "result first, with no model call at all; the ranked answer "
                   "replaces it when it arrives, and <b>Load more</b> pages "
                   "through the rest."],
                  ["Library", "<code>/app#/library</code>",
                   "Everything <code>facetmark stats</code> prints, as labelled "
                   "rows: bookmarks, how many have a body, how many are "
                   "embedded, sessions, edges by kind, the fetch queue, link "
                   "health, and the cold-layer census. This is the view that "
                   "answers \u201cI searched and got nothing\u201d."]]),
                ("callout", "info", "What it deliberately does not do",
                 "<p>It reads. There is no delete, no edit, no queue control "
                 "and no synthesize button. Those exist on the command line "
                 "and in the API, where a mistake is at least deliberate. The "
                 "one thing the page writes is a <code>POST /open</code> when "
                 "you follow a result, which is what feeds the cold "
                 "layer.</p>"),
                ("h3", "What the markers on a row mean"),
                ("p",
                 "The same vocabulary the extension popup uses. In the page "
                 "each one carries a one-line explanation on hover; the table "
                 "is here so you can read them all at once."),
                ("table",
                 ["Marker", "Means", "Default"],
                 [["<span class=\"chip mk\">about</span>",
                   "The <b>content</b> facet matched \u2014 a vector over the "
                   "page\u2019s own text.",
                   "<span class=\"badge info\">on</span>"],
                  ["<span class=\"chip mk\">asked as</span>",
                   "The <b>intent</b> facet matched \u2014 vectors over "
                   "questions generated for the page.", "off"],
                  ["<span class=\"chip mk\">words</span>",
                   "The <b>lexical \u00b7 segments</b> facet matched \u2014 "
                   "FTS5 over whole words in the title, folder or address.",
                   "off"],
                  ["<span class=\"chip mk\">substring</span>",
                   "The <b>lexical \u00b7 trigram</b> facet matched \u2014 "
                   "FTS5 over characters, which is what makes partial words "
                   "and Chinese queries hit.", "off"],
                  ["<span class=\"badge warn mk\">cold</span>",
                   "Saved long ago, never opened, and something newer looks "
                   "like it replaced it. Ranked lower, never deleted.",
                   "<span class=\"badge info\">on</span>"],
                  ["<span class=\"gmk mk\">saved around these</span>",
                   "The second group: one hop over the link graph from a "
                   "result above. Never mixed into the ranking.",
                   "<span class=\"badge info\">on</span>"]]),
                ("p",
                 "Rows in that second group carry a chip for the edge that "
                 "reached them \u2014 <em>same sitting</em> (saved in the same "
                 "browsing session), <em>similar</em> (close in meaning), "
                 "<em>replaced by</em>, <em>same page</em>, <em>same "
                 "site</em>. The weights behind those names are in "
                 "<a href=\"#env\">the settings table</a>."),
                ("h3", "How the page gets the token"),
                ("p",
                 "It asks <code>GET /app/boot</code>, which is the only route "
                 "that can hand out the pairing token, and only when both the "
                 "caller and the address in the request are loopback. On your "
                 "own machine both are true and the page pairs itself with "
                 "nothing to copy."),
                ("callout", "warn", "Why the second condition exists",
                 "<p>A page on the open web can point a hostname at "
                 "127.0.0.1 and have <em>your</em> browser make the request "
                 "\u2014 the caller really is loopback. What it cannot do is "
                 "change the <code>Host</code> header, which still carries the "
                 "attacker\u2019s domain. Checking it is what keeps a website "
                 "from reading your token, and it is why this is a separate "
                 "route rather than a flag on an existing one.</p><p>Behind a "
                 "reverse proxy, or on a LAN address, that check fails on "
                 "purpose: the page then shows a field and you paste "
                 "<code>facetmark token</code> once. It is kept in that "
                 "browser\u2019s local storage, not in the page.</p>"),
                ("h3", "Keyboard"),
                ("table",
                 ["Key", "Does"],
                 [["<kbd>/</kbd>", "Focus the query box from anywhere on the "
                   "page."],
                  ["<kbd>Enter</kbd>", "Search."],
                  ["<kbd>\u2191</kbd> <kbd>\u2193</kbd>",
                   "Walk the results. From the box, "
                   "<kbd>\u2193</kbd> enters the list."],
                  ["<kbd>Esc</kbd>", "Clear the query and go back to the "
                   "box."]]),
                ("h3", "Language and theme"),
                ("p",
                 "English and Chinese, switched in the header and remembered. "
                 "Without a stored choice the page follows the browser\u2019s "
                 "language. The theme switch cycles system \u2192 light "
                 "\u2192 dark and shares its stored key with this site, so a "
                 "reader who picked dark here gets dark there. Everything "
                 "animated is inside a "
                 "<code>prefers-reduced-motion</code> query."),
            ],
        ),
        # ------------------------------------------------------------- paging
        (
            "paging",
            "Paging: limit, offset and depth",
            [
                ("p",
                 "Every search surface takes <code>limit</code>, "
                 "<code>offset</code> and <code>depth</code>, and every search "
                 "response reports the window it actually served rather than "
                 "echoing what you asked for."),
                ("cb", "shell",
                 'facetmark search "kafka rebalance" -n 20\n'
                 'facetmark search "kafka rebalance" -n 20 -o 20 --depth 60'),
                ("p",
                 "The CLI prints the <code>--offset</code> and "
                 "<code>--depth</code> for the next page whenever there is "
                 "one. Over HTTP the same three fields go in the "
                 "<code>POST /search</code> body:"),
                ("cb", "json",
                 "{\n"
                 '  "hits": [ ],\n'
                 '  "limit": 20,          // served, after clamping\n'
                 '  "offset": 20,\n'
                 '  "depth": 60,          // the depth this ranking ran at\n'
                 '  "total": 137,         // ranked so far; a floor when capped\n'
                 '  "has_more": true,\n'
                 '  "depth_capped": false\n'
                 "}"),
                ("table",
                 ["Field", "Meaning"],
                 [["<code>limit</code>",
                   "Rows in this page. Clamped to "
                   "<code>MAX_PAGE_SIZE</code>, 200 by default."],
                  ["<code>offset</code>",
                   "Rows skipped. Clamped below "
                   "<code>MAX_CANDIDATE_DEPTH</code>."],
                  ["<code>depth</code>",
                   "How deep each facet was read before fusion. Omit it and it "
                   "is derived from the window; send back the value the "
                   "previous page reported and this page continues that same "
                   "ranking."],
                  ["<code>total</code>",
                   "Documents the fusion step ranked. A lower bound, not a "
                   "library count, and explicitly a floor when "
                   "<code>depth_capped</code> is true."],
                  ["<code>has_more</code>",
                   "There is something past this window. Exact under the "
                   "shipped single-facet default; an upper bound with several "
                   "facets in play, where the overflow row can turn out to be "
                   "a document the pool already held."],
                  ["<code>depth_capped</code>",
                   "More exists <em>and</em> the reason we stopped is the "
                   "depth ceiling rather than your window \u2014 the "
                   "difference between \u201cpress next\u201d and "
                   "\u201craise the depth or narrow the query\u201d."]]),
                ("h3", "Why depth is a parameter and not an implementation detail"),
                ("p",
                 "Page size and retrieval depth used to be the same number: "
                 "asking for more rows quietly retrieved deeper, and result 51 "
                 "was unreachable at any page size because the pool was 50 rows "
                 "regardless. Now the page is a window onto a pool whose size "
                 "you can see and pin."),
                ("callout", "warn", "Pin the depth or page two can disagree with page one",
                 "<p>RRF is only rank-stable under a growing pool when there is "
                 "<em>one</em> facet. A document\u2019s score is a sum over the "
                 "facets that ranked it within the depth asked for, so a deeper "
                 "pool can hand a document a term it did not have \u2014 and "
                 "that term can outweigh a rival\u2019s whole score. Rank 2 in "
                 "one facet plus rank 40 in another beats a sole rank 1 "
                 "(1/62 + 1/100 against 1/61) but contributes nothing at depth "
                 "30.</p><p>So with several facets on, growing the depth to "
                 "reach page 2 lets page 2 disagree with page 1 about what page "
                 "1 was. The fix is not to grow it: send back the "
                 "<code>depth</code> the previous page reported and every page "
                 "is a slice of one ranking. The local page and the browser "
                 "extension both do this.</p>"),
                ("h3", "The two ceilings"),
                ("p",
                 "<code>MAX_PAGE_SIZE</code> (200) bounds one page. "
                 "<code>MAX_CANDIDATE_DEPTH</code> (2000) bounds the pool "
                 "behind all of them, and hitting it is what sets "
                 "<code>depth_capped</code>. Both are clamped in one place, "
                 "before any query runs, so an oversized request costs nothing "
                 "and is answered with the window that was actually served."),
            ],
        ),
        # ---------------------------------------------------------- extension
        (
            "extension",
            "Browser extension",
            [
                ("p",
                 "Manifest V3, for Chromium-family browsers. It talks to "
                 "<code>127.0.0.1:8787</code> and nothing else \u2014 those "
                 "are its only required host permissions."),
                ("steps",
                 ["Download <code>facetmark-extension.zip</code> from the "
                  "<a href=\"" + REPO + "/releases\">releases page</a> and "
                  "unzip it.",
                  "Open <code>chrome://extensions</code>, turn on "
                  "<b>Developer mode</b>, choose <b>Load unpacked</b> and "
                  "select the unzipped folder.",
                  "Run <code>facetmark serve</code> in a terminal and leave "
                  "it running.",
                  "Run <code>facetmark token</code>, open the extension's "
                  "options page, and paste the token.",
                  "Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> "
                  "(<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> on macOS) "
                  "and search."]),
                ("h3", "What it gives you"),
                ("table",
                 ["Feature", "Detail"],
                 [["Omnibox keyword",
                   "Type <code>fm</code> then a space in the address bar and "
                   "search without opening the popup."],
                  ["Keyboard shortcut",
                   "<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> / "
                   "<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>."],
                  ["Save the current tab",
                   "One click. The page joins a local indexing queue and the "
                   "popup footer shows how many are waiting."],
                  ["Context menu",
                   "Right-click a link or a page to save it."],
                  ["Grouped results",
                   "Pages from the same saving session arrive as their own "
                   "group instead of being mixed into the ranking."],
                  ["Facet labels",
                   "Each hit shows which facets matched \u2014 "
                   "<em>about</em>, <em>asked as</em>, <em>words</em>, "
                   "<em>substring</em>, <em>linked</em>, <em>cold</em>."]]),
                ("h3", "Options"),
                ("table",
                 ["Field", "Meaning"],
                 [["<code>endpoint</code>",
                   "Where facetmark is listening. Default "
                   "<code>http://127.0.0.1:8787</code>."],
                  ["<code>token</code>", "Output of <code>facetmark token</code>."],
                  ["<code>channelB</code>",
                   "An optional second endpoint, for running two libraries."],
                  ["<code>paused</code>",
                   "Stop the extension talking to the service without "
                   "uninstalling it."]]),
                ("callout", "info", "Not in the web stores",
                 "<p>The extension is distributed as a zip on the releases "
                 "page and installed unpacked. It has not been submitted to "
                 "the Chrome Web Store or the Edge add-ons catalogue.</p>"),
            ],
        ),
        # ---------------------------------------------------------------- mcp
        (
            "mcp",
            "MCP server",
            [
                ("p",
                 "<code>facetmark mcp</code> runs a FastMCP server on stdio, "
                 "so an MCP client such as Claude Desktop can search your "
                 "library, read a saving session, and save a page."),
                ("cb", "json",
                 "{\n"
                 '  "mcpServers": {\n'
                 '    "facetmark": {\n'
                 '      "command": "facetmark",\n'
                 '      "args": ["mcp"]\n'
                 "    }\n"
                 "  }\n"
                 "}"),
                ("p",
                 "Add <code>\"--db\", \"/path/to/facetmark.db\"</code> to "
                 "<code>args</code> to point at a specific library, or "
                 "<code>\"--mock\"</code> to try it with no key. Environment "
                 "variables are read the same way as for every other "
                 "command."),
                ("h3", "Nine tools"),
                ("table",
                 ["Tool", "Does"],
                 [["<code>search_bookmarks</code>",
                   "The full pipeline, same as <code>facetmark search</code>."],
                  ["<code>get_bookmark</code>", "One record, optionally with the body."],
                  ["<code>list_sessions</code>", "Recent saving episodes."],
                  ["<code>get_session</code>", "Everything saved in one episode."],
                  ["<code>find_related</code>", "One hop out in the link graph."],
                  ["<code>synthesize</code>",
                   "A model-written answer grounded in retrieved pages."],
                  ["<code>suggest_from_context</code>",
                   "What in the library relates to text you are looking at."],
                  ["<code>check_link_health</code>",
                   "Whether a saved URL is still alive."],
                  ["<code>save_bookmark</code>",
                   "Add a URL and queue it for indexing."]]),
                ("h3", "Three resources"),
                ("ul",
                 ["<code>bookmark://{id}</code> \u2014 one record as JSON.",
                  "<code>session://{id}</code> \u2014 one saving episode.",
                  "<code>facetmark://stats</code> \u2014 index size and "
                  "coverage."]),
            ],
        ),
        # ----------------------------------------------------------- karakeep
        (
            "karakeep",
            "karakeep plugin",
            [
                ("p",
                 "<a href=\"https://karakeep.app\">karakeep</a> is a "
                 "self-hosted bookmark manager with a pluggable search "
                 "provider. This plugin puts facetmark behind its search box, "
                 "so karakeep keeps the UI and facetmark does the "
                 "retrieval."),
                ("steps",
                 ["Copy the plugin into karakeep's plugin package.",
                  "Register it in the exports map.",
                  "Load it <b>after</b> meilisearch, because the plugin "
                  "manager hands out the last provider registered.",
                  "Point it at a running facetmark service."]),
                ("cb", "shell",
                 "cp -r integrations/karakeep/search-facetmark \\\n"
                 "  /path/to/karakeep/packages/plugins/search-facetmark"),
                ("cb", "json",
                 "// packages/plugins/package.json \u2014 exports map\n"
                 '"./search-facetmark": "./search-facetmark/index.ts"'),
                ("cb", "ts",
                 "// packages/shared-server/src/plugins.ts, in loadAllPlugins()\n"
                 "await import(\"@karakeep/plugins/search-meilisearch\");\n"
                 "await import(\"@karakeep/plugins/search-facetmark\");  "
                 "// must come after"),
                ("cb", "shell",
                 "export FACETMARK_URL=http://127.0.0.1:8787\n"
                 "export FACETMARK_TOKEN=$(facetmark token)\n"
                 "facetmark serve"),
                ("h3", "How the contract is kept honest"),
                ("ul",
                 ["Upstream karakeep types are pinned by blob SHA in "
                  "<code>integrations/karakeep/typecheck/upstream-pins.json</code>, "
                  "and CI runs <code>tsc --noEmit</code> against them.",
                  "The wire format is captured in "
                  "<code>integrations/karakeep/contract/wire.json</code> and "
                  "replayed by <code>tests/test_karakeep_contract.py</code>.",
                  "That replay test caught a real one: at offset 1 of a "
                  "single match, the correct answer is "
                  "<code>hits: []</code> with <code>totalHits: 1</code>. An "
                  "empty <code>hits</code> array is <b>not</b> the same as no "
                  "results."]),
                ("callout", "warn", "Two things to know before you rely on it",
                 "<p>First, there is no test against a live karakeep "
                 "instance \u2014 only against the pinned contract. Second, "
                 "pushing your library through karakeep and back changes the "
                 "ranking: karakeep's tags are your browser's folder labels, "
                 "so the keyword line collapses from 19,016 distinct terms to "
                 "13. Metric-level conclusions survive the round trip; "
                 "rank-level ones do not until you re-index. "
                 "<a href=\"measured.html#karakeep\">The full "
                 "measurement</a>.</p>"),
                ("p",
                 "To uninstall the bridge, drop the "
                 "<code>karakeep_doc</code> table. "
                 "<code>enrichment.source_hash == 'karakeep'</code> is "
                 "reserved and means the bridge may overwrite that row; any "
                 "other value means a real model wrote it and the bridge "
                 "leaves it alone."),
            ],
        ),
        # --------------------------------------------------------------- data
        (
            "data",
            "What is in the database",
            [
                ("p",
                 "One SQLite file. Open it with any SQLite browser; nothing "
                 "is encrypted, obfuscated or proprietary. If you stop using "
                 "facetmark, your data is still readable."),
                ("table",
                 ["Table", "Holds"],
                 [["<code>bookmark</code>",
                   "URL, title, folder path, save timestamp, source."],
                  ["<code>content</code>",
                   "The fetched body and its extracted text."],
                  ["<code>enrichment</code>",
                   "Summary, topics, entities, key points, and the "
                   "<code>source_hash</code> fingerprint."],
                  ["<code>intent</code>",
                   "Generated candidate queries and whether each one survived "
                   "the retrieve-it-back filter."],
                  ["<code>vec_content</code> / <code>vec_intent</code>",
                   "sqlite-vec virtual tables holding the dense vectors."],
                  ["<code>fts_tri</code> / <code>fts_seg</code>",
                   "Two FTS5 indexes: character trigrams and word segments."],
                  ["<code>session</code> / <code>bookmark_session</code>",
                   "Reconstructed saving episodes and their membership."],
                  ["<code>edge</code>",
                   "Typed links: <code>session</code>, <code>semantic</code>, "
                   "<code>same_domain</code>, <code>supersession</code>."],
                  ["<code>health</code>",
                   "Link-health verdicts: <code>ok</code>, "
                   "<code>gone</code>, <code>drifted</code>, "
                   "<code>soft_gone</code>."],
                  ["<code>karakeep_doc</code>",
                   "Bridge state. Drop it to uninstall the bridge."],
                  ["<code>meta</code>",
                   "Embedding model, dimension and backend, recorded at first "
                   "build and enforced afterwards."]]),
                ("h3", "Link health and the cold layer"),
                ("cb", "shell",
                 "facetmark health                       # what is known\n"
                 "facetmark health --check               # actually probe the "
                 "network\n"
                 "facetmark health --check --no-save-recovered   # read-only "
                 "sweep"),
                ("p",
                 "The sweep can use DNS-over-HTTPS, the Wayback availability "
                 "API and a reader proxy to distinguish \u201cgone\u201d from "
                 "\u201cyour DNS is broken\u201d. Use "
                 "<code>--no-save-recovered</code> before measuring anything "
                 "against a library, so the sweep stays read-only apart from "
                 "the health log."),
                ("callout", "bad", "A known, load-bearing bug",
                 "<p>The cold layer treats \u201cthe URL died\u201d as "
                 "\u201cthe saved copy is useless\u201d, which is wrong: "
                 "facetmark stores the body, so a dead URL is when the local "
                 "snapshot matters <em>most</em>. It is not fixed yet, "
                 "because in the shipped profile a second accident stops the "
                 "demotion from ever executing, and removing either one alone "
                 "makes results worse by a measured 1.46pp. "
                 "<a href=\"measured.html#decay\">The whole story</a>.</p>"),
            ],
        ),
        # ---------------------------------------------------------------- env
        (
            "env",
            "Every setting",
            [
                ("p",
                 "Prefix every name with <code>FACETMARK_</code> as an "
                 "environment variable, or put it unprefixed in a "
                 "<code>.env</code> file. Defaults below are the shipped "
                 "values."),
                ("h3", "Storage"),
                ("table",
                 ["Setting", "Default", "Notes"],
                 [["<code>DATA_DIR</code>", "per-OS",
                   "See <a href=\"#install\">install</a>."],
                  ["<code>DB_NAME</code>", "<code>facetmark.db</code>", ""],
                  ["<code>PRIVACY_EXCLUDED_DOMAINS</code>", "empty",
                   "Never imported, fetched or embedded."]]),
                ("h3", "Model access"),
                ("table",
                 ["Setting", "Default", "Notes"],
                 [["<code>API_KEY</code>", "empty",
                   "Empty is legal; you lose the content and intent facets."],
                  ["<code>BASE_URL</code>",
                   "<code>https://api.openai.com/v1</code>",
                   "Must end in <code>/v1</code>."],
                  ["<code>CHAT_MODEL</code>", "<code>gpt-4o-mini</code>", ""],
                  ["<code>CHAT_MODEL_FALLBACKS</code>", "empty",
                   "Comma-separated. Empty on purpose."],
                  ["<code>EMBED_MODEL</code>",
                   "<code>text-embedding-3-small</code>", ""],
                  ["<code>EMBED_DIM</code>", "<code>1536</code>",
                   "Recorded in <code>meta</code>; a mismatch raises."],
                  ["<code>EMBED_BACKEND</code>", "<code>endpoint</code>",
                   "Or <code>local</code>."],
                  ["<code>REQUEST_TIMEOUT</code>", "<code>60.0</code>", "Seconds."],
                  ["<code>MAX_RETRIES</code>", "<code>3</code>", ""],
                  ["<code>USE_MOCK_PROVIDER</code>", "<code>false</code>",
                   "Deterministic offline provider."]]),
                ("h3", "Local embeddings"),
                ("table",
                 ["Setting", "Default", "Notes"],
                 [["<code>LOCAL_EMBED_PATH</code>", "empty",
                   "Empty downloads the model."],
                  ["<code>LOCAL_EMBED_DEVICE</code>", "<code>cpu</code>", ""],
                  ["<code>LOCAL_EMBED_BATCH</code>", "<code>8</code>", ""],
                  ["<code>LOCAL_EMBED_MAX_SEQ</code>", "<code>1024</code>",
                   "Lowering it costs reproducibility \u2014 see "
                   "<a href=\"#models\">model access</a>."]]),
                ("h3", "Fetching"),
                ("table",
                 ["Setting", "Default", "Notes"],
                 [["<code>FETCH_CONCURRENCY</code>", "<code>30</code>", "Global."],
                  ["<code>FETCH_PER_HOST_CONCURRENCY</code>", "<code>2</code>",
                   "Politeness, not performance."],
                  ["<code>FETCH_PER_HOST_MIN_INTERVAL</code>",
                   "<code>0.5</code>", "Seconds between hits on one host."],
                  ["<code>FETCH_TIMEOUT</code>", "<code>15.0</code>", ""],
                  ["<code>RESPECT_ROBOTS</code>", "<code>true</code>", ""],
                  ["<code>ROBOTS_ON_ERROR</code>", "<code>allow</code>",
                   "What to do when robots.txt cannot be read."],
                  ["<code>ROBOTS_MAX_CRAWL_DELAY</code>", "<code>5.0</code>",
                   "Cap on an advertised crawl delay."],
                  ["<code>MIN_BODY_CHARS</code>", "<code>200</code>",
                   "Below this the page counts as body-less."],
                  ["<code>BODY_TRUNCATE_CHARS</code>", "<code>6000</code>", ""],
                  ["<code>USER_AGENT</code>", "identifies facetmark", ""]]),
                ("h3", "Enrichment and intents"),
                ("table",
                 ["Setting", "Default", "Notes"],
                 [["<code>ENRICH_CONCURRENCY</code>", "<code>4</code>", ""],
                  ["<code>INTENT_GENERATE_N</code>", "<code>8</code>",
                   "Candidates generated per page."],
                  ["<code>INTENT_KEEP_N</code>", "<code>4</code>",
                   "Kept per page, at most."],
                  ["<code>INTENT_PROBE_TOP_K</code>", "<code>10</code>",
                   "How deep the retrieve-it-back filter looks."]]),
                ("h3", "Sessions, retrieval and decay"),
                ("table",
                 ["Setting", "Default", "Notes"],
                 [["<code>SESSION_EPS_MINUTES</code>", "auto",
                   "Unset means the gap is chosen by coverage \u00d7 purity "
                   "lift over a grid."],
                  ["<code>SESSION_EPS_GRID_MINUTES</code>",
                   "<code>5\u2026240</code>", "The grid it searches."],
                  ["<code>RRF_K</code>", "<code>60</code>",
                   "The <code>k</code> in <code>w / (k + rank)</code>."],
                  ["<code>CANDIDATES_PER_FACET</code>", "<code>50</code>", ""],
                  ["<code>GRAPH_EXPAND_HOPS</code>", "<code>1</code>", ""],
                  ["<code>GRAPH_EXPAND_FACTOR</code>", "<code>0.6</code>", ""],
                  ["<code>DECAY_FACTOR</code>", "<code>0.5</code>", ""],
                  ["<code>DECAY_AGE_DAYS</code>", "<code>365</code>", ""],
                  ["<code>DECAY_RESCUE_THRESHOLD</code>", "<code>0.02</code>",
                   "See the <a href=\"measured.html#decay\">decay "
                   "measurement</a> before changing this."]]),
                ("h3", "Link health and service"),
                ("table",
                 ["Setting", "Default", "Notes"],
                 [["<code>HEALTH_ENABLE_EXTERNAL</code>", "<code>true</code>",
                   "Master switch for network probes."],
                  ["<code>HEALTH_ENABLE_DOH</code>", "<code>true</code>",
                   "DNS-over-HTTPS."],
                  ["<code>HEALTH_ENABLE_WAYBACK</code>", "<code>true</code>", ""],
                  ["<code>HEALTH_ENABLE_READER</code>", "<code>true</code>", ""],
                  ["<code>HEALTH_SOFT_GONE_LENGTH_RATIO</code>",
                   "<code>0.30</code>", "Body shrank this much \u21d2 "
                   "<code>soft_gone</code>."],
                  ["<code>HEALTH_GONE_CONFIRM_DAYS</code>", "<code>7</code>", ""],
                  ["<code>HEALTH_PROXY_URL</code>", "unset", ""],
                  ["<code>HOST</code>", "<code>127.0.0.1</code>", ""],
                  ["<code>PORT</code>", "<code>8787</code>", ""]]),
            ],
        ),
        # ----------------------------------------------------------- commands
        (
            "commands",
            "Every command",
            [
                ("p",
                 "Every command takes <code>--db</code> to point at a "
                 "specific database file or data directory. Most take "
                 "<code>--json</code>."),
                ("table",
                 ["Command", "Does", "Notable flags"],
                 [["<code>version</code>", "Print the version.", ""],
                  ["<code>browsers</code>",
                   "List live browser profiles that can be imported.",
                   "<code>--json</code>"],
                  ["<code>import [PATH]</code>",
                   "Import a Netscape HTML export or a Chrome JSON profile. "
                   "With no path, finds the live profile. Never writes back.",
                   ""],
                  ["<code>migrate</code>",
                   "Bring the schema up to what this build expects.",
                   "<code>--check</code>, <code>--no-backup</code>"],
                  ["<code>index</code>",
                   "Fetch, enrich, embed, intents, sessions, edges.",
                   "<code>--no-fetch</code>, <code>--limit</code>, "
                   "<code>--force</code>, <code>--mock</code>"],
                  ["<code>reindex</code>",
                   "Rebuild every derived artefact from the bookmarks.",
                   "<code>--mock</code>"],
                  ["<code>search QUERY</code>", "Search the library.",
                   "<code>-n</code>, <code>--quick</code>, "
                   "<code>--config</code>, <code>--explain</code>"],
                  ["<code>show ID</code>", "Print one bookmark as JSON.",
                   "<code>--body</code>"],
                  ["<code>sessions</code>", "List saving episodes.",
                   "<code>-n</code>"],
                  ["<code>health</code>",
                   "Link health, and whether the decay layer can see any of "
                   "it.",
                   "<code>--check</code>, <code>--no-external</code>, "
                   "<code>--no-save-recovered</code>"],
                  ["<code>stats</code>", "Index size and coverage.", ""],
                  ["<code>token</code>", "Print the extension's pairing token.",
                   "<code>--rotate</code>"],
                  ["<code>serve</code>", "Run the local HTTP service.",
                   "<code>--host</code>, <code>--port</code>, "
                   "<code>--mock</code>"],
                  ["<code>mcp</code>", "Run the MCP server on stdio.",
                   "<code>--mock</code>"],
                  ["<code>demo</code>",
                   "Build a synthetic library offline and search it.",
                   "<code>--size</code>, <code>--keep</code>"],
                  ["<code>eval</code>",
                   "Run the retrieval evaluation, optionally as an A\u2013E "
                   "ablation.",
                   "<code>--ablation</code>, <code>--rungs</code>, "
                   "<code>--queries</code>, <code>--bootstrap</code>, "
                   "<code>--out</code>"]]),
                ("h3", "Running your own evaluation"),
                ("p",
                 "This is the part of facetmark that matters most and the "
                 "part nobody else has used yet. Give it a JSONL file of "
                 "<code>{text, qtype, target_url}</code> and it will run any "
                 "set of rungs against your own library with bootstrap "
                 "confidence intervals and a McNemar test on the paired "
                 "differences."),
                ("cb", "shell",
                 "facetmark eval --no-build \\\n"
                 "  --queries my-queries.jsonl \\\n"
                 "  --rungs A,C,full \\\n"
                 "  --bootstrap 10000 --concurrency 4 \\\n"
                 "  --out report.json"),
                ("callout", "warn", "Concurrency destroys the latency numbers",
                 "<p><code>--concurrency &gt; 1</code> makes p50 and p95 "
                 "meaningless. Use it for the quality numbers, then re-run at "
                 "concurrency 1 on a subsample if you need latency.</p>"),
            ],
        ),
        # --------------------------------------------------------- troubleshoot
        (
            "trouble",
            "Troubleshooting",
            [
                ("h3", "Every model call returns 404"),
                ("p",
                 "The base URL is missing <code>/v1</code>. This is the most "
                 "common setup failure by a wide margin, and the error "
                 "surfaces as a provider error, so it reads like a "
                 "credentials problem."),
                ("h3", "\u201cdimension mismatch\u201d on index or search"),
                ("p",
                 "The embedding dimension recorded in <code>meta</code> at "
                 "first build no longer matches "
                 "<code>FACETMARK_EMBED_DIM</code>. facetmark refuses to mix "
                 "vector dimensions rather than silently return nonsense. "
                 "Either restore the old dimension, or re-embed everything "
                 "with <code>facetmark index --force</code>."),
                ("h3", "Enrichment silently does nothing"),
                ("p",
                 "The stored <code>source_hash</code> already equals the "
                 "current body hash, so the fingerprint says the work is "
                 "done. That is correct behaviour, and "
                 "<code>facetmark index --force</code> overrides it."),
                ("h3", "Vectors exist but results are bad"),
                ("p",
                 "Usually the embed text changed after the vector was "
                 "written \u2014 for example because enrichment was replaced "
                 "by a bridge. Re-embed with "
                 "<code>facetmark index --force</code>. If results are bad on "
                 "a fresh index instead, check whether you are accidentally "
                 "on the mock provider: <code>facetmark stats</code> reports "
                 "the embedding model in use."),
                ("h3", "<code>disk I/O error</code> from SQLite"),
                ("p",
                 "SQLite cannot run reliably on some network and FUSE "
                 "filesystems. Move the data directory to local disk with "
                 "<code>FACETMARK_DATA_DIR</code>."),
                ("h3", "Fetching is slow, or pages come back empty"),
                ("p",
                 "Both are usually intentional. robots.txt is honoured and "
                 "per-host concurrency is capped at 2 with a minimum interval "
                 "between hits. Some sites simply refuse. A page with no body "
                 "still indexes \u2014 the pipeline falls back to a "
                 "title-only fingerprint \u2014 it is just weaker. Use "
                 "<code>--no-fetch</code> if you want a fast, shallow index."),
                ("h3", "The extension cannot reach the service"),
                ("p",
                 "Check three things in order: <code>facetmark serve</code> "
                 "is actually running; the endpoint in options matches the "
                 "host and port it bound; the token in options matches "
                 "<code>facetmark token</code>. If you rotated the token, the "
                 "extension needs the new one."),
                ("h3", "Something else"),
                ("p",
                 "<code>facetmark stats</code> and "
                 "<code>facetmark health</code> print what the index actually "
                 "contains, which resolves most confusion. Beyond that, "
                 "<a href=\"" + REPO + "/issues\">open an issue</a> \u2014 "
                 "the <code>--json</code> output of the failing command is "
                 "the most useful thing to paste."),
            ],
        ),
    ],
}


# ------------------------------------------------------------- measured ----

EN["measured"] = {
    "h1": "Everything that was measured",
    "lede": (
        "Nine results. Four of them killed the feature that motivated them, "
        "one of them overturned an earlier result from this same project, and "
        "one of them has no verdict at all because the sample was too small. "
        "They are all here for the same reason: a retrieval claim without a "
        "protocol is a preference."
    ),
    "toc_title": "Results",
    "sections": [
        (
            "how",
            "How to read this page",
            [
                ("ul",
                 ["<b>Pre-registration.</b> Criteria are written down before "
                  "the run. A rung measured on the queries that motivated it "
                  "is a hypothesis, not a result, and is labelled "
                  "exploratory.",
                  "<b>Paired tests.</b> Every A-versus-B claim is paired on "
                  "the same queries, with a bootstrap confidence interval and "
                  "a McNemar test on the discordant pairs. Wins and losses "
                  "are reported separately, because a net zero from 0 changes "
                  "and a net zero from 40 wins and 40 losses are different "
                  "facts.",
                  "<b>Nothing is reopened.</b> Once a query set is frozen and "
                  "a verdict recorded, it stands. A new question needs a new "
                  "query set.",
                  "<b>pp</b> means percentage points. <b>CI95</b> is a 95% "
                  "bootstrap interval."]),
                ("callout", "warn", "The biggest caveat, stated once, up front",
                 "<p>Every query set on this page was written by the author "
                 "of the tool. Bootstrapping fixes sampling noise; it does "
                 "nothing at all about the author knowing what the tool is "
                 "good at. The most valuable contribution this project could "
                 "receive is a query set written by somebody else.</p>"),
            ],
        ),
        (
            "w1",
            "W1 \u00b7 Four-facet fusion lost to one facet",
            [
                ("raw", "<p><span class=\"badge fail\">default withdrawn</span> "
                        "<span class=\"tiny\">479 queries \u00b7 one real "
                        "1,700-bookmark library \u00b7 pre-registered</span></p>"),
                ("p",
                 "The premise of the whole project was that fusing four "
                 "facets beats any one of them. Three criteria were "
                 "registered before the run. All three failed."),
                ("table",
                 ["Rung", "Facets", "Recall@5", "Recall@1", "MRR@10", "p50"],
                 [["<b>A</b>", "content vector only",
                   "<b>0.643</b>", "0.505", "0.564", "<b>148 ms</b>"],
                  ["<b>B</b>", "+ two lexical", "0.589", "\u2014", "\u2014",
                   "189 ms"],
                  ["<b>C</b>", "all four", "0.635", "\u2014", "\u2014",
                   "526 ms"],
                  ["<b>D</b>", "+ context + graph", "0.639", "\u2014",
                   "\u2014", "523 ms"]],
                 [0]),
                ("p",
                 "Fusion cost <b>5.4pp</b> of Recall@5 and made queries "
                 "<b>3.5\u00d7</b> slower. Config A by query type: "
                 "content-style <b>0.959</b>, vague <b>0.706</b>, episodic "
                 "<b>0.279</b>."),
                ("h3", "Why it lost"),
                ("p",
                 "Flat-weight reciprocal rank fusion has no way to express "
                 "confidence. Two weak facets that happen to agree score "
                 "0.0279; one strong facet that is certain scores 0.0164. The "
                 "coincidence wins. That is not a tuning problem, it is what "
                 "the formula does."),
                ("h3", "What survived the same run"),
                ("table",
                 ["Survivor", "Effect", "Wins / losses", "p", "Cost"],
                 [["Graph expansion as a <em>separate group</em>",
                   "<b>+2.09pp</b> Recall@5", "10 / 0", "0.0019", "9 ms"],
                  ["Reranker, on Recall@1",
                   "<b>+4.80pp</b> CI95 [+1.46, +8.35]", "45 / 22", "0.0067",
                   "\u2014"]]),
                ("p",
                 "Both shipped. Note that graph expansion only works as an "
                 "<em>addition</em> \u2014 returned as its own group rather "
                 "than merged into the ranking."),
            ],
        ),
        (
            "gate",
            "W2/W3 \u00b7 The episodic gate shipped, then lost",
            [
                ("raw", "<p><span class=\"badge fail\">default reverted after "
                        "shipping</span></p>"),
                ("p",
                 "The episodic gate detects \u201cthe thing I saved around "
                 "the same time as X\u201d and restricts retrieval to that "
                 "saving window. On its 616-query holdout it won cleanly and "
                 "was shipped."),
                ("table",
                 ["Query set", "Comparison", "\u0394Recall@5", "CI95",
                  "Wins / losses", "p"],
                 [["616-query holdout", "A \u2192 A_gatedctx",
                   "<b class=\"nowrap\">+3.09pp</b>", "[1.79, 4.55]",
                   "19 / 0", "3.8e\u22126"],
                  ["361-query precision probe", "A \u2192 A_gatedctx",
                   "<b class=\"nowrap\">\u221218.83pp</b>",
                   "[\u221223.27, \u221214.68]", "3 / 71", "\u2014"]]),
                ("p",
                 "The second row is the same feature, measured on a query set "
                 "built afterwards to ask a different question: what does the "
                 "gate do when it fires on a query it should not have? "
                 "Recall@5 fell from 0.9058 to 0.7175 and Recall@1 from 0.801 "
                 "to 0.363."),
                ("h3", "The stratification is the whole answer"),
                ("table",
                 ["Stratum", "n", "\u0394Recall@5"],
                 [["The saving window contains the target", "57",
                   "<b>+0.00pp</b> \u2014 exactly zero"],
                  ["The saving window misses the target", "304",
                   "<b class=\"nowrap\">\u221222.37pp</b>"]]),
                ("p",
                 "When the gate is right it adds nothing. When it is wrong it "
                 "throws the answer away. Verdict "
                 "<code>gate_precision_unqualified</code>; the default "
                 "reverted to no gating."),
                ("callout", "info", "gate_v2 was drafted and refused",
                 "<p>A narrower gate scored +1.79pp on the original 616-query "
                 "set and <b>\u221210.52pp</b> on the precision probes. "
                 "Shipping on the first number while the second exists would "
                 "have been choosing the query set that gave the answer we "
                 "wanted. It was not shipped.</p>"),
            ],
        ),
        (
            "recall",
            "The other side of the gate \u00b7 no verdict",
            [
                ("raw", "<p><span class=\"badge warn\">descriptive only \u00b7 "
                        "below the pre-registered sample floor</span></p>"),
                ("p",
                 "The precision probe asked what happens when the gate fires "
                 "and should not have. This asks the opposite: how often does "
                 "it fail to fire when it should? The protocol was "
                 "pre-registered before the run, mirroring the precision "
                 "protocol."),
                ("table",
                 ["Measure", "Value"],
                 [["Probes available", "<b>16</b> "
                   "<code>q_save_action</code> rows of the frozen v3 holdout"],
                  ["Gate fired", "<b>0 of 16</b>"],
                  ["Miss rate", "<b>100.0%</b>, Wilson CI95 [80.64, 100.00]"],
                  ["\u0394Recall@5 (A_gatedctx \u2212 A)",
                   "<b>+0.00pp</b>, CI95 [0.00, 0.00]"],
                  ["McNemar", "0 gained, 0 lost, p = 1.0, 0 discordant pairs"],
                  ["Protocol self-check",
                   "<span class=\"badge pass\">pass</span> \u2014 the "
                   "untriggered subset must move exactly 0.00pp, and it did"],
                  ["Verdict",
                   "<b>none.</b> 16 &lt; the pre-registered floor of 25"]]),
                ("callout", "warn", "That zero is structural, not reassuring",
                 "<p>The gate never fired, so both arms ran identical code and "
                 "produced identical per-query ranks. A \u0394 of exactly zero "
                 "with zero discordant pairs is not evidence that the gate is "
                 "harmless \u2014 it is evidence that nothing was tested. The "
                 "minimum detectable effect is undefined here, because the "
                 "formula divides by the number of discordant pairs and there "
                 "were none.</p>"),
                ("p",
                 "All sixteen phrasings are ways of saying \u201cthe one I put "
                 "away\u201d \u2014 <em>\u4e4b\u524d\u6536\u8d77\u6765\u7684"
                 "\u90a3\u4e2a</em>, <em>the link I set aside</em>, "
                 "<em>\u6211\u585e\u8fdb\u6e05\u5355\u91cc\u7684\u90a3\u7bc7"
                 "</em>. None of them contains a word in the gate's trigger "
                 "vocabulary, which currently keys on "
                 "<code>\u4fdd\u5b58</code>, <code>\u6536\u85cf</code>, "
                 "<code>saved</code>, <code>bookmark</code> and eleven "
                 "others."),
                ("p",
                 "The obvious move \u2014 add these sixteen phrasings to the "
                 "vocabulary \u2014 is exactly what the protocol forbids, "
                 "because selecting a vocabulary on the probes that measure it "
                 "is circular. Reaching a verdict requires generating at least "
                 "25 probes in a new round with new seeds, at frozen "
                 "parameters, and then passing <em>both</em> the miss-rate bar "
                 "and the 361-probe precision bar. Until then the vocabulary "
                 "is unchanged."),
            ],
        ),
        (
            "five",
            "Five candidate fixes, five verdicts",
            [
                ("p",
                 "After W1 killed fusion, five obvious repairs were each "
                 "measured rather than argued about."),
                ("table",
                 ["Candidate", "What was measured", "Verdict"],
                 [["Drop the lexical facets entirely",
                   "80.1% of content-style and 46.3% of vague queries need no "
                   "vector at all \u2014 but <b>6.05%</b> (29 of 479) are "
                   "findable <em>only</em> lexically, above the "
                   "pre-registered 5% line.",
                   "<span class=\"badge fail\">kept</span>"],
                  ["Weight the facets instead of flat RRF",
                   "A coincidence on two weak facets scores 0.0279; certainty "
                   "on one strong facet scores 0.0164.",
                   "<span class=\"badge info\">explains the loss</span>"],
                  ["Fix the trigram facet on Chinese",
                   "It matched 25 of 211 Chinese queries (11.85%). After the "
                   "fix, 202 of 211 (95.73%). Overall Recall@5: "
                   "<b>unchanged</b>.",
                   "<span class=\"badge warn\">fixed, no gain</span>"],
                  ["Raise the boost ceiling",
                   "<code>MAX_BOOST = 1.60</code> crosses 79.7% of the score "
                   "range in config A but only 20.9% in C/D. Equal "
                   "displacement power would need 6.03. 66.3% of candidates "
                   "get exactly 1.0.",
                   "<span class=\"badge info\">measured, not shipped</span>"],
                  ["Turn on the intent facet",
                   "19 of 50 generated intents (38%) were plausible, below "
                   "the pre-registered 50% line. The information word is "
                   "absent from the page 34.0% of the time overall and "
                   "<b>62.4%</b> on body-poor pages.",
                   "<span class=\"badge fail\">off</span>"]]),
                ("p",
                 "The third row is the interesting one. A real bug was found "
                 "and fixed \u2014 the trigram facet went from useless on "
                 "Chinese to working \u2014 and end-to-end recall did not "
                 "move. A fix that is genuinely a fix and changes no outcome "
                 "is a normal result, and reporting it is the only thing that "
                 "keeps the other four honest."),
            ],
        ),
        (
            "karakeep",
            "karakeep round trip \u00b7 unfaithful",
            [
                ("raw", "<p><span class=\"badge fail\">roundtrip_unfaithful</span> "
                        "<span class=\"tiny\">2,376 bookmarks \u00b7 616 "
                        "holdout queries \u00b7 protocol frozen "
                        "first</span></p>"),
                ("p",
                 "Question: if a library is pushed through the karakeep "
                 "bridge and read back, is it the same library? Three "
                 "criteria were registered first."),
                ("table",
                 ["Criterion", "Bar", "Measured", "Verdict"],
                 [["Metric fidelity", "|\u0394Recall@5| \u2264 3pp with CI95 "
                   "inside \u00b15pp",
                   "<b>\u22120.81pp</b>, CI95 [\u22122.44, +0.81]",
                   "<span class=\"badge pass\">pass</span>"],
                  ["Rank fidelity",
                   "median overlap@5 \u2265 4 <b>and</b> top-1 agreement "
                   "\u2265 80%",
                   "median 4.0, top-1 <b>79.06%</b>",
                   "<span class=\"badge fail\">fail by 0.94pp</span>"],
                  ["Read-path equivalence",
                   "HTTP and native identical over 616\u00d72",
                   "0 mismatches",
                   "<span class=\"badge pass\">pass</span>"]]),
                ("h3", "The cause is fully attributed"),
                ("ul",
                 ["Bodies survive byte-identical: 1,876 of 1,876.",
                  "Summaries survive: 2,375 of 2,375, 100%.",
                  "Topics match <b>0%</b> and entities <b>1.18%</b> \u2014 "
                  "because karakeep's tags are the browser's <em>folder</em> "
                  "labels, not topics.",
                  "The keyword line collapses from <b>19,016 distinct terms "
                  "to 13</b>; mean terms per page falls from 10.32 to 0.76; "
                  "the most common tag is <code>\u672a\u5206\u7c7b</code> on "
                  "1,124 pages.",
                  "Vectors move by a median cosine of 0.9846 \u2014 small, "
                  "and enough to reshuffle a top-5."]),
                ("p",
                 "Grafting the source enrichment back produced 2,376 of 2,376 "
                 "byte-identical embed texts, residual zero, which closes the "
                 "attribution. Re-running <code>facetmark index</code> repairs "
                 "it: 0 karakeep bodies needed re-fetching, all 2,376 rows "
                 "re-enriched, and the graph came back matching except for 212 "
                 "semantic edges (26,485 against 26,697)."),
                ("callout", "info", "What this means in practice",
                 "<p>Metric-level conclusions transfer to a karakeep-enriched "
                 "library. Rank-level ones do not, until you re-index. If you "
                 "run the bridge, run <code>facetmark index</code> "
                 "afterwards.</p>"),
            ],
        ),
        (
            "decay",
            "The decay layer, measured twice \u2014 the second run overturned the first",
            [
                ("p",
                 "The decay layer demotes pages that look stale. Round one "
                 "measured it and found exactly nothing:"),
                ("table",
                 ["Round one", "Value"],
                 [["\u0394Recall@5", "<b>0.0000pp</b>, CI95 [0.00, 0.00]"],
                  ["Cold pages", "8 of 2,376"],
                  ["Cold pages among the 230 targets", "0"]]),
                ("callout", "bad", "Round one measured an instrument that was switched off",
                 "<p>The <code>health</code> table had <b>zero rows</b> and "
                 "<code>open_count</code> was 0 for all 2,376 pages. The "
                 "layer could not fire because it had nothing to read. A "
                 "clean zero from a correctly executed protocol, measuring "
                 "nothing.</p>"),
                ("p",
                 "Round two ran the same bytes with a local health check "
                 "first."),
                ("table",
                 ["Round two", "Shipped (0.02)", "Reachable (0.0)"],
                 [["Recall@5", "<b>0.5860</b>", "0.5714"],
                  ["Recall@1", "0.4237", "0.4188"],
                  ["Rescue valve open", "417 of 616", "0 of 616"],
                  ["Health rows", "2,376 (was 0)", "2,376"],
                  ["Cold pages", "73 \u2014 3.07% (was 8, 0.34%)", "73"],
                  ["Cold \u2229 the 230 targets", "8, across 19 queries",
                   "8"]]),
                ("p",
                 "\u0394Recall@5 went from <code>+0.0000pp</code> in round one "
                 "to <b class=\"nowrap\">\u22121.4610pp</b> CI95 "
                 "[\u22122.5974, \u22120.4870] in round two. The mechanism is "
                 "countable: of 37 rank changes, <b>12 fell out of the top 20 "
                 "entirely</b> \u2014 10 of those had been in the top 5 and 5 "
                 "had been rank 1. Twenty-four rose, 21 of them by a single "
                 "place, and exactly <b>1</b> crossed into the top 5. Net "
                 "\u221210 + 1 = \u22129, and \u22129/616 = "
                 "\u22121.4610pp."),
                ("h3", "Why the threshold still has not changed"),
                ("p",
                 "Two bugs are cancelling, and the cancellation is "
                 "load-bearing."),
                ("ul",
                 ["<b>Bug one:</b> the cold-layer condition treats \u201cthe "
                  "URL died\u201d as \u201cthe saved copy is useless\u201d. "
                  "But facetmark stores the body. A dead URL is precisely when "
                  "the local snapshot matters most, and "
                  "<code>drifted</code> is worse still, because then the "
                  "snapshot is the only surviving record.",
                  "<b>Bug two:</b> with <code>rrf_k = 60</code>, one "
                  "unit-weight facet tops out at "
                  "<code>1/61 = 0.016393</code>, which is below the rescue "
                  "threshold of <code>0.02</code>. In the shipped "
                  "single-facet profile the rescue valve is therefore "
                  "<em>always</em> open and the demotion has never once "
                  "executed.",
                  "Remove either one alone and results get measurably worse. "
                  "Both are pinned by <code>tests/test_decay_reach.py</code> "
                  "so neither can be quietly \u201ccleaned up\u201d."]),
                ("p",
                 "What changed instead was the instrumentation. "
                 "<code>cold_census()</code> now reports the three conditions "
                 "separately, and <code>facetmark stats</code> and "
                 "<code>facetmark health --check</code> name "
                 "<code>never_opened_selects_everything</code> and "
                 "<code>health_never_checked</code> out loud."),
                ("p",
                 "One more detail worth keeping: 4 of the 8 damaged targets "
                 "have <code>char_count = 0</code> and are still retrieved "
                 "correctly, through title and lexical facets. Body loss is "
                 "not the same as retrieval loss."),
            ],
        ),
        (
            "real",
            "One real library, end to end",
            [
                ("p",
                 "Synthetic corpora hide integration failures. This is one "
                 "actual browser export, imported and indexed with the "
                 "shipped code path."),
                ("table",
                 ["Stage", "Result"],
                 [["The file",
                   "<code>favorites_2026_8_4.html</code>, 1.7 MB, 96 folders, "
                   "4 levels deep"],
                  ["Import",
                   "parsed 1,710 \u2192 inserted 1,701, 9 duplicates merged, "
                   "1 non-indexable"],
                  ["Index (no page fetching)",
                   "322 saving sessions, 9,132 edges, 1,386 distinct domains, "
                   "1,775 vectors"],
                  ["Median query latency", "2,265 ms"]]),
                ("p",
                 "The latency number is honest and unflattering: it is a "
                 "cold, unfetched index on a laptop, and it is the number "
                 "that would be quietly omitted from a launch post."),
            ],
        ),
        (
            "gaps",
            "What none of this measures",
            [
                ("ul",
                 ["<b>Whether anyone else's queries look like these.</b> "
                  "Every query set was written by the author of the tool. "
                  "This is the single largest threat to every number on this "
                  "page and no amount of bootstrapping touches it.",
                  "<b>Whether the decay layer helps</b>, because in the "
                  "shipped profile it cannot fire at all.",
                  "<b>Whether the intent facet would help a different "
                  "library.</b> It was measured on this one, generated by one "
                  "model, and it lost.",
                  "<b>Whether the karakeep bridge works against a live "
                  "karakeep.</b> The contract is pinned and replayed; a "
                  "running instance has never been tested.",
                  "<b>Whether the reranker helps with a real cross-encoder.</b> "
                  "What ships offline is term overlap. An ablation run under "
                  "that reranker measures the harness, not the idea, and must "
                  "not be quoted as evidence that reranking works.",
                  "<b>Long-term behaviour.</b> Every measurement is a "
                  "snapshot. Nobody has run this for a year and watched what "
                  "a growing library does to the session clustering."]),
                ("callout", "info", "How to help",
                 "<p>Write 100 queries against your own library, with the "
                 "target URL for each, as JSONL. Run <code>facetmark eval "
                 "--no-build --queries yours.jsonl --rungs A,C,full</code>. "
                 "Post the JSON. That single contribution is worth more than "
                 "any feature request, and it is the one thing the author "
                 "structurally cannot do.</p>"),
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
    "The web page \u2014 facetmark",
    "Every screen in the browser interface, what each one is for, how to "
    "read a result row, and every key it answers to.",
)
EN["meta"]["config"] = (
    "Settings \u2014 facetmark",
    "Every setting in plain language, ready-made blocks for eight model "
    "providers, and how to run the whole thing with no API key at all.",
)
EN["meta"]["integrations"] = (
    "Connect it \u2014 facetmark",
    "Browser extension, MCP server for Claude and Cursor, the karakeep "
    "plugin, the whole command line, and how to back the library up.",
)

EN["webui"] = {
    "h1": "The page in your browser",
    "lede": "Six screens, one of them you will never need to open twice. "
    "Everything the command line can do, plus the two things it cannot: "
    "showing you <em>why</em> a result is where it is, and letting you set "
    "the thing up without typing a config file.",
    "toc_title": "On this page",
    "sections": [
        (
            "open",
            "Open it",
            [
                ("cb", "one command", "facetmark serve"),
                (
                    "p",
                    "That prints a URL \u2014 <code>http://127.0.0.1:8765</code> "
                    "by default \u2014 and keeps running. Open the URL. Leave "
                    "the terminal alone; closing it stops the server.",
                ),
                (
                    "dashed",
                    "",
                    "why it asks for nothing",
                    [
                        (
                            "p",
                            "The server is bound to your own machine and the "
                            "page hands itself a token when it can prove both "
                            "ends are local. That is why there is no login "
                            "screen and why there is nothing to create an "
                            "account for.",
                        ),
                        (
                            "p",
                            "If you reach it by any other name \u2014 a LAN "
                            "address, a tunnel, a reverse proxy \u2014 the "
                            "handshake is refused on purpose and the page asks "
                            "you to paste the token instead. Get it with "
                            "<code>facetmark token</code>.",
                        ),
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "Do not put this behind a public hostname",
                    "<p>There is one token and no rate limit. It is built to "
                    "be reachable from the chair you are sitting in.</p>",
                ),
            ],
        ),
        (
            "firstrun",
            "The first time: three steps",
            [
                (
                    "p",
                    "On an empty library the page opens on a setup screen "
                    "instead of on search, because a search box over zero "
                    "bookmarks is a dead end. Three framed steps, in order, "
                    "each one done from the browser:",
                ),
                (
                    "steps",
                    [
                        "<b>Bring your bookmarks in.</b> Export from your "
                        "browser (<i>Bookmarks \u2192 Manage \u2192 Export</i>) "
                        "and drop the HTML file on the button. A Chrome "
                        "<code>Bookmarks</code> JSON file works too; the "
                        "importer sniffs which one you gave it.",
                        "<b>Point it at a model, or don't.</b> Paste an API "
                        "key, or switch the embedding backend to local and "
                        "skip the key entirely. Either way the page tests the "
                        "connection before you rely on it.",
                        "<b>Build the index.</b> One button. Seven stages, "
                        "shown as they happen, with a log. You can close the "
                        "tab and come back \u2014 the job runs in the server, "
                        "not in the page.",
                    ],
                ),
                (
                    "p",
                    "Once all three frames carry a tick the screen offers you "
                    "the search box and gets out of the way. It will not come "
                    "back unless the library empties out again.",
                ),
            ],
        ),
        (
            "tabs",
            "The five tabs, and the gear",
            [
                (
                    "table",
                    ["Screen", "What it is for"],
                    [
                        [
                            "<b>Search</b>",
                            "The main event. Type, get ranked pages, see which "
                            "of the four paths found each one.",
                        ],
                        [
                            "<b>Ask</b>",
                            "A question in a sentence, answered from your own "
                            "pages, with every sentence traceable to the "
                            "bookmark it came from. It quotes; it does not "
                            "invent.",
                        ],
                        [
                            "<b>Library</b>",
                            "What the index actually contains: how many pages "
                            "have text, how many have vectors, which links are "
                            "dead, what is queued, what has never been opened.",
                        ],
                        [
                            "<b>Sittings</b>",
                            "Bookmarks you saved in the same stretch of time, "
                            "grouped. Useful when you remember <i>when</i> and "
                            "nothing else.",
                        ],
                        [
                            "<b>System</b>",
                            "Version, database path, provider, uptime. The "
                            "screen you screenshot into a bug report.",
                        ],
                        [
                            "<b>\u2699 Settings</b>",
                            "Model, limits, privacy, and the index job. Behind "
                            "the gear rather than in the tab row, because you "
                            "open it twice a year.",
                        ],
                    ],
                ),
                (
                    "p",
                    "\u201cSittings\u201d is not a typo for settings. A sitting "
                    "is a stretch of saving \u2014 the twenty tabs you filed at "
                    "eleven at night. The gear is where settings live.",
                ),
            ],
        ),
        (
            "read",
            "How to read a result",
            [
                (
                    "p",
                    "A row is a rank, a title, where it came from, a snippet "
                    "with your words marked, and then the part no other "
                    "bookmark search shows you: the paths that found it.",
                ),
                (
                    "tintrow",
                    [
                        (
                            "",
                            "about",
                            [
                                (
                                    "p",
                                    "A vector over the page body. Found it "
                                    "because the page is <i>about</i> your "
                                    "query, whether or not it uses your words.",
                                )
                            ],
                        ),
                        (
                            "lex",
                            "words / substring",
                            [
                                (
                                    "p",
                                    "Full-text search, by word and by "
                                    "character triple. Found it because your "
                                    "exact string is in it. This is the one "
                                    "that saves you when you remember a name.",
                                )
                            ],
                        ),
                        (
                            "intent",
                            "asked as",
                            [
                                (
                                    "p",
                                    "Vectors over questions generated from the "
                                    "page. Found it because someone might ask "
                                    "your question <i>of</i> this page.",
                                )
                            ],
                        ),
                        (
                            "context",
                            "linked",
                            [
                                (
                                    "p",
                                    "Not a rank at all: pages one hop away in "
                                    "the graph, shown in their own group under "
                                    "the results. Saved-next-to and "
                                    "semantically-near.",
                                )
                            ],
                        ),
                    ],
                ),
                (
                    "p",
                    "Under the badges is a short bar in the same colours. That "
                    "is the mixture: how much each path put into this one "
                    "fused score. Two gold-heavy rows and a blue-heavy one "
                    "means the first two matched your spelling and the third "
                    "matched your meaning \u2014 which is usually the moment "
                    "you learn something about your own query.",
                ),
                (
                    "ul",
                    [
                        "<b>never opened</b> \u2014 facetmark has never watched "
                        "you open this one. A browser export carries no usage "
                        "history at all, so on day one this is true of "
                        "everything.",
                        "The <b>\u22ef</b> button at the end of a row \u2014 opens the page's own panel without "
                        "leaving the results: full text stats, links, the "
                        "sitting it belongs to.",
                        "<b>More options</b> \u2014 picks how many of the four "
                        "paths run. The default runs one; the last rung runs "
                        "all four and reranks. It is slower and it is "
                        "measurably better on vague queries.",
                    ],
                ),
            ],
        ),
        (
            "keys",
            "Keys, and reading it your way",
            [
                (
                    "table",
                    ["Key", "Does"],
                    [
                        ["<kbd>/</kbd>", "Jump to the search box from anywhere"],
                        ["<kbd>\u2191</kbd> <kbd>\u2193</kbd>", "Move through suggestions"],
                        ["<kbd>Enter</kbd>", "Search, or take the highlighted suggestion"],
                        ["<kbd>Esc</kbd>", "Close the panel, or clear the box"],
                        ["<kbd>Tab</kbd>", "Every control, in reading order"],
                    ],
                ),
                (
                    "ul",
                    [
                        "The sun/moon control switches theme; it follows your "
                        "system until you touch it, then it remembers.",
                        "<b>\u4e2d\u6587 / EN</b> switches language. It changes "
                        "the interface, not your data.",
                        "Everything is real text at real sizes, so browser "
                        "zoom works, and so does selecting it and copying it.",
                        "If your system asks for reduced motion, the page has "
                        "no motion. Nothing waits for an animation before it "
                        "will show you a number.",
                    ],
                ),
            ],
        ),
        (
            "trouble",
            "When it misbehaves",
            [
                (
                    "table",
                    ["What you see", "What it is"],
                    [
                        [
                            "The page loads but asks for a token",
                            "You reached it by something other than "
                            "<code>127.0.0.1</code> or <code>localhost</code>. "
                            "Run <code>facetmark token</code> and paste, or use "
                            "the local address.",
                        ],
                        [
                            "<code>address already in use</code>",
                            "Something else has the port. "
                            "<code>facetmark serve --port 8790</code>.",
                        ],
                        [
                            "Search returns nothing, library says 0 vectors",
                            "The index was never built. Gear \u2192 Run, or "
                            "<code>facetmark index</code>.",
                        ],
                        [
                            "Every result says <i>never opened</i>",
                            "Correct, and temporary. It starts meaning "
                            "something after facetmark has seen you open a few "
                            "pages through it.",
                        ],
                        [
                            "The index job stops at <i>fetch</i>",
                            "Pages that will not load. It moves on; dead links "
                            "show up in Library, and the pages still index on "
                            "title alone.",
                        ],
                    ],
                ),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------

EN["config"] = {
    "h1": "Settings, in plain language",
    "lede": "There are a lot of knobs. You need four of them, and only if you "
    "use a hosted model at all. This page is the four, then the rest, then a "
    "block you can paste for each of eight providers.",
    "toc_title": "On this page",
    "sections": [
        (
            "where",
            "Where a setting comes from",
            [
                (
                    "p",
                    "Three places, and the one further left always wins:",
                ),
                (
                    "cb",
                    "precedence",
                    "environment variable   >   config.toml   >   built-in default",
                ),
                (
                    "p",
                    "The Settings screen shows you which of the three each "
                    "value came from, and if an environment variable is "
                    "winning, the field goes read-only and says so rather than "
                    "letting you write something that will have no effect. "
                    "Editing in the browser writes the file; it never touches "
                    "your environment.",
                ),
                ("cb", "where is the file", "facetmark config path"),
                (
                    "p",
                    "It is created the first time something writes to it. "
                    "There is no requirement to have one \u2014 a run with no "
                    "file and no variables is a valid run with all defaults.",
                ),
                (
                    "callout",
                    "",
                    "Three settings need a restart",
                    "<p><code>embed_backend</code>, <code>embed_dim</code> and "
                    "<code>local_embed_path</code> decide the shape of the "
                    "vector store. The screen saves them and then tells you "
                    "plainly that they take effect next start.</p>",
                ),
            ],
        ),
        (
            "model",
            "The four that matter",
            [
                (
                    "table",
                    ["Setting", "In plain language"],
                    [
                        [
                            "<code>api_key</code>",
                            "Your key. Stored in the file, shown back to you "
                            "masked, and never re-sent when you save an "
                            "unrelated field.",
                        ],
                        [
                            "<code>base_url</code>",
                            "Where the requests go. Anything speaking the "
                            "OpenAI API works, including something on your own "
                            "machine.",
                        ],
                        [
                            "<code>chat_model</code>",
                            "Used to read pages and to answer on the Ask "
                            "screen. Cheap and fast beats clever here.",
                        ],
                        [
                            "<code>embed_model</code>",
                            "Turns text into vectors. This is the one that "
                            "decides search quality.",
                        ],
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "Changing the embedding model means reindexing",
                    "<p>Vectors from two different models are not comparable. "
                    "Change it and run a rebuild, or search gets quietly "
                    "worse in a way no error message will tell you about.</p>",
                ),
                (
                    "p",
                    "The <b>Test</b> button on the Settings screen calls chat "
                    "and embeddings separately and reports them separately, "
                    "because in practice exactly one of them is usually the "
                    "broken one \u2014 an account with chat access and no "
                    "embedding access is a very common shape.",
                ),
            ],
        ),
        (
            "presets",
            "Eight providers, ready to paste",
            [
                (
                    "p",
                    "Put these in the file from <code>facetmark config path</code>, "
                    "or type the same values into the Settings screen. Model "
                    "names move; if one is rejected, check the provider's "
                    "current list rather than trusting this page.",
                ),
                (
                    "cb",
                    "OpenAI",
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.openai.com/v1"\n'
                    'chat_model = "gpt-4o-mini"\n'
                    'embed_model = "text-embedding-3-small"\n'
                    "embed_dim = 1536",
                ),
                (
                    "cb",
                    "DeepSeek  (chat only \u2014 pair it with embeddings from elsewhere)",
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.deepseek.com/v1"\n'
                    'chat_model = "deepseek-chat"',
                ),
                (
                    "cb",
                    "Moonshot / Kimi",
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.moonshot.cn/v1"\n'
                    'chat_model = "moonshot-v1-8k"',
                ),
                (
                    "cb",
                    "Zhipu / GLM",
                    'api_key = "..."\n'
                    'base_url = "https://open.bigmodel.cn/api/paas/v4"\n'
                    'chat_model = "glm-4-flash"\n'
                    'embed_model = "embedding-3"\n'
                    "embed_dim = 2048",
                ),
                (
                    "cb",
                    "SiliconFlow",
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.siliconflow.cn/v1"\n'
                    'chat_model = "Qwen/Qwen2.5-7B-Instruct"\n'
                    'embed_model = "BAAI/bge-m3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "cb",
                    "Aliyun Bailian  (OpenAI-compatible endpoint)",
                    'api_key = "sk-..."\n'
                    'base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"\n'
                    'chat_model = "qwen-plus"\n'
                    'embed_model = "text-embedding-v3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "cb",
                    "Ollama  (on your machine, no key)",
                    'base_url = "http://127.0.0.1:11434/v1"\n'
                    'api_key = "ollama"\n'
                    'chat_model = "qwen2.5:7b"\n'
                    'embed_model = "bge-m3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "cb",
                    "vLLM  (your own server)",
                    'base_url = "http://127.0.0.1:8000/v1"\n'
                    'api_key = "not-used"\n'
                    'chat_model = "Qwen/Qwen2.5-7B-Instruct"',
                ),
                (
                    "callout",
                    "",
                    "Mixing providers is normal",
                    "<p>facetmark makes one kind of request for chat and one "
                    "for embeddings. Plenty of people run chat on whatever is "
                    "cheapest and embeddings on whatever is best. Set "
                    "<code>base_url</code> to the embedding provider and give "
                    "the chat model a fully-qualified name, or run the "
                    "embeddings locally and leave the API for chat.</p>",
                ),
            ],
        ),
        (
            "local",
            "With no API at all",
            [
                (
                    "p",
                    "Embeddings can run on your own machine. No key, no "
                    "network, nothing leaves the laptop:",
                ),
                (
                    "cb",
                    "local embeddings",
                    'embed_backend = "local"\n'
                    'local_embed_path = "BAAI/bge-m3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "p",
                    "It is slower to build and it needs the model downloaded "
                    "once. Search quality is good: on a 1,024-token window "
                    "bge-m3 reproduces its own vector to a cosine of 0.999976 "
                    "run-to-run, which is the property that matters for an "
                    "index you keep rather than rebuild.",
                ),
                (
                    "dashed",
                    "context",
                    "what you give up",
                    [
                        (
                            "p",
                            "Two facets are built on a language model reading "
                            "your pages: the questions a page could answer, "
                            "and the topic labels. With no chat model those "
                            "stay empty and you are searching on body text and "
                            "full-text \u2014 still the two strongest paths, "
                            "and still better than what your browser gives "
                            "you.",
                        ),
                        (
                            "p",
                            "You can also start here and add a key later. "
                            "Nothing has to be thrown away; the index fills in "
                            "the parts it could not build before.",
                        ),
                    ],
                ),
            ],
        ),
        (
            "groups",
            "Everything else",
            [
                ("h3", "Vectors"),
                (
                    "table",
                    ["Setting", "In plain language"],
                    [
                        [
                            "<code>embed_backend</code>",
                            "<code>api</code> or <code>local</code>. Restart to "
                            "take effect.",
                        ],
                        [
                            "<code>embed_dim</code>",
                            "How long each vector is. Must match what the model "
                            "actually returns. Restart to take effect.",
                        ],
                        [
                            "<code>local_embed_path</code>",
                            "Model id or folder for the local backend. Restart "
                            "to take effect.",
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
                            "Seconds before a call is given up on. Raise it on "
                            "a slow link; lower it if a provider hangs.",
                        ],
                        [
                            "<code>fetch_concurrency</code>",
                            "How many pages are downloaded at once. Lower it if "
                            "your network complains.",
                        ],
                        [
                            "<code>enrich_concurrency</code>",
                            "How many pages are sent to the model at once. This "
                            "is the one to lower when you get rate-limited.",
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
                            "Domains never fetched and never sent anywhere. "
                            "Bank, health, work intranet. The bookmark stays; "
                            "only the title is indexed.",
                        ],
                        [
                            "<code>chat_model_fallbacks</code>",
                            "Models to try, in order, when the first one "
                            "refuses.",
                        ],
                    ],
                ),
                (
                    "callout",
                    "",
                    "Set the exclusions before the first index",
                    "<p>Once a page's text is in the database, adding its "
                    "domain to the list stops future fetches but does not "
                    "unremember it. Rebuild after changing the list if that "
                    "matters to you.</p>",
                ),
            ],
        ),
        (
            "faq",
            "The errors you will actually get",
            [
                (
                    "table",
                    ["Message", "What to do"],
                    [
                        [
                            "<code>401</code> / <code>invalid_api_key</code>",
                            "Key wrong, or wrong provider's key for this "
                            "<code>base_url</code>. Test on the Settings "
                            "screen \u2014 it tells you which half failed.",
                        ],
                        [
                            "<code>404</code> on a model name",
                            "That name is not on that endpoint. Check the "
                            "provider's model list.",
                        ],
                        [
                            "<code>429</code>",
                            "Rate limit. Lower <code>enrich_concurrency</code> "
                            "and run again; finished stages are not redone.",
                        ],
                        [
                            "<code>dim mismatch</code>",
                            "<code>embed_dim</code> disagrees with the model. "
                            "Fix it, restart, rebuild.",
                        ],
                        [
                            "Chat works, embeddings 403",
                            "Common. The account has one entitlement and not "
                            "the other. Switch <code>embed_backend</code> to "
                            "local, or point embeddings at another provider.",
                        ],
                        [
                            "<code>unknown setting</code> on save",
                            "A typo in a key name. The writer refuses unknown "
                            "keys rather than storing something that will be "
                            "silently ignored forever.",
                        ],
                    ],
                ),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# connect it to things
# --------------------------------------------------------------------------

EN["integrations"] = {
    "h1": "Connect it to the rest of your desk",
    "lede": "The database is one SQLite file and everything here is a different "
    "door into it: your browser, your editor, your agent, your shell.",
    "toc_title": "On this page",
    "sections": [
        (
            "extension",
            "The browser extension",
            [
                (
                    "p",
                    "Search your bookmarks from the address bar, and save the "
                    "page you are on without leaving it. The extension talks to "
                    "the same local server the web page does.",
                ),
                (
                    "steps",
                    [
                        "Start the server: <code>facetmark serve</code>.",
                        "Load the extension from <code>extension/</code> in the "
                        "repository \u2014 Chrome: <i>chrome://extensions</i>, "
                        "developer mode, <i>Load unpacked</i>.",
                        "Open its options. If the server is on the default port "
                        "it pairs itself; otherwise paste the output of "
                        "<code>facetmark token</code>.",
                    ],
                ),
                (
                    "callout",
                    "",
                    "It pairs, it does not sync",
                    "<p>Nothing is uploaded and there is no account. If the "
                    "server is not running, the extension does nothing at "
                    "all.</p>",
                ),
            ],
        ),
        (
            "mcp",
            "Claude, Cursor, and anything else speaking MCP",
            [
                (
                    "p",
                    "facetmark ships an MCP server, so an assistant can search "
                    "your bookmarks as a tool instead of you pasting links into "
                    "a chat window.",
                ),
                ("cb", "run it by hand first", "facetmark mcp"),
                (
                    "cb",
                    "Claude Desktop \u2014 claude_desktop_config.json",
                    '{\n'
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
                    "Cursor takes the same shape in its own MCP settings. If "
                    "<code>facetmark</code> is not on the PATH the editor sees, "
                    "give the absolute path \u2014 that is the failure in nearly "
                    "every report of \u201cthe tool never appears\u201d.",
                ),
                (
                    "dashed",
                    "intent",
                    "what the assistant can and cannot do",
                    [
                        (
                            "p",
                            "It can search, read a bookmark, list sittings and "
                            "ask a question over your library. It cannot delete "
                            "anything, cannot write settings and cannot reach "
                            "outside the database.",
                        )
                    ],
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep",
            [
                (
                    "p",
                    "If you keep your links in karakeep, facetmark can index "
                    "from there instead of from a browser export.",
                ),
                (
                    "callout",
                    "warn",
                    "Measured, and worth knowing before you commit",
                    "<p>A round trip through karakeep's own keyword extraction "
                    "cost <b>0.81 points of Recall@5</b> (CI95 \u22122.44 to "
                    "+0.81) and agreed with the direct index on the top result "
                    "<b>79.06&nbsp;%</b> of the time. The vocabulary collapses: "
                    "19,016 distinct terms became 13. The verdict recorded in "
                    "the repository is <code>roundtrip_unfaithful</code> \u2014 "
                    "usable, not equivalent. Index the pages directly if you "
                    "can.</p>",
                ),
            ],
        ),
        (
            "cli",
            "The command line",
            [
                (
                    "p",
                    "Everything the page does, and a few things it does not. "
                    "Add <code>--help</code> to any of them.",
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
                    "<code>facetmark demo</code> is the honest way to decide "
                    "whether you want this: it builds a library out of "
                    "generated pages, with no key and no network, so you can "
                    "click every screen before importing anything of your own.",
                ),
            ],
        ),
        (
            "backup",
            "Backing it up, and moving it",
            [
                (
                    "p",
                    "One file. Copy it and you have copied everything \u2014 "
                    "bookmarks, text, vectors, graph, history.",
                ),
                ("cb", "find it", "facetmark stats"),
                (
                    "callout",
                    "warn",
                    "Stop the server first",
                    "<p>The database runs in WAL mode, so a copy taken while "
                    "something is writing can miss the tail of the log. Stop "
                    "<code>facetmark serve</code>, copy, start it again.</p>",
                ),
                (
                    "ul",
                    [
                        "Moving machines: copy the file, then "
                        "<code>facetmark migrate</code> if the versions differ.",
                        "Your bookmarks are also still in your browser. The "
                        "worst case is re-importing and rebuilding, which costs "
                        "time and a few model calls, not data.",
                        "The config file is separate and holds your API key. "
                        "Back it up somewhere you would put a password, or not "
                        "at all.",
                    ],
                ),
            ],
        ),
    ],
}

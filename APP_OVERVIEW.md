# Hebrew Stylometry Explorer — How the App Works

Hebrew Stylometry Explorer is an interactive workspace for comparing how Biblical (Mikra), Mishnaic, and Dead Sea Scrolls (DSS) texts use **words** and **grammar**.

It is meant for researchers who want to try stylistic neighborhoods and feature contrasts without rewriting a notebook for every experiment. Guests can run the full analysis without signing in. Google sign-in is optional: use it when you want named settings and hand-picked book groups stored under your account.

Live site: [https://dss-clustering.reflex.run](https://dss-clustering.reflex.run)

---

## What the experiment is doing

At a high level, the app:

1. Lets you choose which books and scrolls to include (and, for many DSS scrolls, which **fragments** to leave out).
2. Counts either **lemmas** (word identities) or **morphological signatures** (grammar patterns) in each selected book.
3. Turns those counts into a weighted table of books × features.
4. Compresses that table so books can be compared in a smaller “analysis space.”
5. Shows the books as a **3D map** and as a **family tree** (dendrogram).
6. Lets you compare any two groups and read which features they share, which are distinctive, and which are missing.

Each **book or scroll** remains one unit in the analysis. Deselecting DSS fragments does not split a scroll into many units; it only drops those fragments’ words from that scroll’s profile.

---

## How the page is organized

Everything lives on **one long page**. Scroll from top to bottom. Sections that need earlier results show a placeholder until you run the analysis.

The header has:

- The site name (returns you to the analysis page)
- Dark/light mode
- Sign in with Google (optional)
- **Help** (toggles a separate help catalog; “Back to analysis” returns)

Technical knobs sit behind a **gear** icon in each relevant section (configuration). Most visitors can ignore those and use the defaults.

A typical path:

1. Choose your texts  
2. Words or grammar  
3. Run the analysis  
4. The 3D map  
5. The Tree  
6. The numbers (including optional hand-picked groups)  
7. Save & export  

---

## 1. Choose your texts

Every eligible book starts selected. Search and untick anything you want to leave out.

Books are grouped by corpus:

- **Mikra** — Biblical books  
- **Mishna** — tractates  
- **DSS** — scrolls and related compositions  

Each row shows a short/full name (for DSS, often like `1QS - Community Rule`) and how many valid word occurrences it has. A minimum-occurrence threshold (default 100) decides which books appear in the catalog. That threshold lives behind the gear.

**Select all visible** / **Clear selection** apply to the current search. Corpus checkboxes select or deselect every visible book in that group.

### DSS fragments

Many DSS scrolls are made of catalogued **fragments** (for example `6Q18 f13`, `6Q18 f14`). Those scrolls show a chevron. Expanding it loads the fragment list **only then** — the catalog itself does not load every fragment at startup.

- The parent checkbox still means “include this scroll.”
- Unchecking a fragment **excludes its words** from that scroll’s profile.
- If you uncheck every fragment, the scroll itself is deselected.
- Checking a fragment again re-selects the scroll.

Scrolls without fragment locators (for example some continuous texts) stay flat, like Mikra and Mishna.

If you change books, fragments, or features after a run, later results are treated as **stale** until you run the analysis again.

---

## 2. Words or grammar?

Pick the analytical basis for the rest of the experiment. The two modes are mutually exclusive.

### Words (lemma)

Each word occurrence is signed by its cleaned lemma. This is a good default starting point.

### Grammar (morphology)

Each occurrence is signed by the grammatical attributes you keep (part of speech, person, gender, number, tense, binyan, and so on), joined into one pattern. Column choices live behind the gear.

### Proper names

When proper-name rows are kept, they collapse to a single “proper name” signature rather than competing as ordinary lemmas or grammar patterns. You can also **ignore** proper names entirely so they drop out of the experiment. That toggle is behind the gear.

---

## 3. Run the analysis

One button counts features, weights them, and reduces the numbers behind the scenes.

After a successful run you get a plain-language summary (how many books, how many word occurrences). The map, tree, and tables below then fill in.

### What happens under the hood (still in plain language)

**Counting.** Selected occurrences become **signatures**. Signatures are tallied per book into a book × signature table.

**Weighting (default: term frequency).**

- **Raw** — keep occurrence counts.  
- **Term frequency (TF)** — scale by each book’s length so long books do not dominate.  
- **TF-IDF** — also down-weight signatures that appear in many books.

**Dimensionality reduction (SVD).** Thousands of sparse feature columns are compressed into a handful of composite dimensions (the same idea as latent semantic analysis). That compressed space is what clustering and the default 3D view use.

You can:

- Keep a **constant** number of dimensions, or  
- **Sweep** a range and keep the count whose **cophenetic correlation** is highest once past a plateau.

Cophenetic correlation only asks: “How faithfully does a Ward tree’s merge heights match the pairwise distances in this embedding?” It is **not** by itself evidence that clusters are historically or linguistically meaningful.

The gear also exposes matrix statistics and an export of the raw count table as CSV.

---

## 4. The 3D map

Every included book is a **dot**. Books that use language in similar ways sit closer together.

### Layout methods

- **SVD** — three axes of the analysis embedding. This is the same space that feeds the tree and the tables. You can choose which three dimensions to show (behind the gear).  
- **UMAP** and **t-SNE** — exploratory 3D layouts only. They never change clustering, feature tables, or neighborhood scores.

### Colour and labels

- **Identity** — colour by corpus (or a colour you assign to a book).  
- **Dendrogram clusters** — colour by the current cut of the tree, using the same palette as the tree.  
- Short labels can be shown or hidden.

You can hide whole corpora or individual books, search the book list, and assign custom colours. Those display choices update all visible 3D views automatically.

### Camera

Each scene has zoom, rotate, and reset buttons. PNG/PDF export of the map uses the **current camera** (the view you are looking at).

**Compare 4 views** shows at once:

1. PCA (mean-centered view of the weighted matrix)  
2. SVD dimensions 1, 2, 3 (the analysis embedding)  
3. UMAP  
4. t-SNE  

Rebuild the grid only when you need the projections refit; colour, labels, and visibility already update automatically.

Clicking a point can start or toggle a **hand-picked group** (see The numbers).

---

## 5. The Tree

The same closeness drawn as a hierarchical tree (dendrogram), built from the SVD analysis embedding.

Slide the **cut height** to split books into more or fewer automatic clusters. Releasing the slider recolors clusters without rebuilding the tree.

### Linkage (behind the gear)

- **Ward** — merges to keep within-cluster variance small. Distance is locked to Euclidean.  
- **Average** — merges by average pairwise distance; Euclidean or cosine.

Changing linkage regroups the tree. It does **not** change how many SVD dimensions were chosen.

Optional **Ward artifact** marking (typically used with morphology) greys italic leaves that do not sit stably in their neighborhood across three related distance views. Treat it as a caution flag, not a linguistic verdict.

Clicking a leaf can also feed a hand-picked group.

---

## 6. The numbers

Compare **subject X** to **reference Y** and read three feature lists plus neighborhood scores.

Each side can be:

- A **corpus** (or the whole current selection)  
- A **cluster** from the current tree cut  
- A **manual group** you created  
- A single **book**

Books that appear on both sides are removed from the reference so the comparison stays meaningful. You can swap the two sides.

### The three tables

| Table | Meaning |
|---|---|
| **Top features** | What this group uses most, in absolute terms — no comparison. |
| **Distinctive features** | What X uses notably **more** than Y. High usage alone is not enough; a large gap is. |
| **Gap features** | What Y uses heavily that X barely uses — what X is missing relative to Y. |

Tables can be filtered by signature text and exported as CSV, Excel, or PDF.

### Neighborhood scores

- **Stability** — a corpus-wide check of how often neighborhoods agree across distance views.  
- **Purity** — when X is one book: does its neighborhood match its own corpus?  
- **Consistency** — when X is several books: do the other members of the group actually show up as neighbors?

These are neighborhood diagnostics (typical neighbor counts: 10 for purity, 5 for consistency/stability). They are not a proof of historical grouping.

### Create our own groups

This is **not** a separate comparison step. Open it with **Create our own groups**.

1. Start selecting.  
2. Click books on the map or tree (or toggle them in the list).  
3. Done finishes the pick.  
4. Name the group and save it.

Then pick that group as X or Y in the tables above.

- **Guests:** groups last for this visit only.  
- **Signed in:** groups are stored under your account and can be reused later.

Hide the builder when you are finished picking.

---

## 7. Save & export

### Presets

Guests can run everything with the current controls. Sign in to **save a named snapshot** of the analysis settings (which books, fragment exclusions, features, weighting, SVD, tree cut, and so on). Loading a preset restores those controls and rebuilds the pipeline.

Presets and saved book groups belong to the signed-in account.

### Exports as you go

- **3D map** — PNG or PDF of the current view  
- **Tree** — PNG or PDF  
- **Feature tables** — CSV, Excel, or PDF  
- **Raw count matrix** — CSV (from the Run section gear)

---

## Help

The Help tab has:

- A short **how to use** walkthrough aligned with the sections above  
- A searchable **reference** (pipeline, methods, metrics)

Hover tips also sit on many buttons.

---

## Guests vs signed-in users

| | Guest | Signed in with Google |
|---|---|---|
| Run the full analysis | Yes | Yes |
| Exclude DSS fragments | Yes | Yes |
| Hand-picked groups | This visit only | Saved to the account |
| Named analysis presets | No | Saved to the account |

Signing out does not block analysis; it only stops account-backed saving.

---

## What this tool is not

- It does not prove authorship, dating, or sectarian identity by itself.  
- SVD sweep scores and neighborhood metrics are **diagnostic**, not historical conclusions.  
- PCA, UMAP, and t-SNE are **pictures**, not the clustering used in the tables.  
- One scroll remains one book even when some fragments are excluded.

Use the maps and tables to **see** contrasts; the linguistic argument still belongs to the reader.

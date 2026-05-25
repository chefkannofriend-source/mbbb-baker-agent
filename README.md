# mbbb Baker Agent

A [Claude Code](https://claude.ai/code) subagent for pastry recipe lookup and Baker's Percentage calculation, built around a professional pastry recipe library.

## Disclaimer

The knowledge base and technique references in this agent reflect the author's personal industry experience (18+ years in professional kitchens and fine dining consulting) and publicly available culinary science. This project is not affiliated with, endorsed by, or associated with any culinary school or educational institution. The recipe library does not contain any confidential, proprietary, or internal recipes belonging to any educational brand or institution.

## What it does

- **Recipe lookup** — find recipes by name (French or Chinese) or by ingredient
- **Baker's % calculation** — express every ingredient as a percentage of the base (flour, chocolate, etc.)
- **Recipe scaling** — scale any formula to a target batch size
- **Technique Q&A** — answer pastry science questions (ganache ratios, mousse stability, hydrocolloid selection, etc.) using a curated knowledge base

## Requirements

- [Claude Code CLI](https://claude.ai/code)
- Python 3.9+
- No external Python dependencies

## Setup

### 1. Copy the agent definition

```bash
cp agents/baker.md /path/to/your-project/.claude/agents/baker.md
```

Or place it in `~/.claude/agents/baker.md` to make it available globally.

### 2. Copy the scripts and data

```bash
cp -r scripts/ data/ /path/to/your-project/
```

### 3. Add your own recipes

Drop `.md` recipe files into:

```
data/recipe-library/baker/_md/
data/recipe-library/baker/_md/glm/
data/recipe-library/baker/_md/glm/intermediate/
```

See [Recipe Format](#recipe-format) below for the expected structure. An example file is included at `data/recipe-library/baker/_md/example-brioche.md`.

The agent always searches `intermediate/` first (highest quality), then `glm/`, then `_md/`.

## Usage

Once the agent is installed, Claude Code will automatically route pastry/recipe queries to the Baker Agent. You can also trigger it directly:

```
查一下 canele 的配方
帮我把这个 brioche 配方缩放到 2000g 面粉
配方库里哪些配方用到了 praliné？
慕斯为什么不稳定？
甘那许奶油和巧克力用什么比例？
```

### CLI tool (standalone)

```bash
# Find a recipe by name (French or Chinese both work)
python scripts/bakers_percent.py --find charlotte
python scripts/bakers_percent.py --find 可丽露

# Find all recipes using an ingredient
python scripts/bakers_percent.py --ingredient gélatine
python scripts/bakers_percent.py --ingredient 吉利丁

# Calculate Baker's % for a recipe
python scripts/bakers_percent.py data/recipe-library/baker/_md/brioche.md

# Override the base ingredient
python scripts/bakers_percent.py recipe.md --base chocolate

# Scale to a target batch (base ingredient = 2000g)
python scripts/bakers_percent.py recipe.md --scale 2000
```

## Recipe Format

Recipes are Markdown files with a YAML frontmatter block. The parser handles three source formats:

### Format 1 — Bilingual table (recommended)

```markdown
---
titre: BRIOCHE CLASSIQUE
niveau: basique
source: your-source
source_file: recipe.1.md
---

# BRIOCHE CLASSIQUE 经典布里欧修

## Pâte à Brioche 面团

| Ingrédients | 食材 |
|-------------|------|
| 250 g de farine T45 | 250 克 T45 面粉 |
| 150 g d'œufs | 150 克鸡蛋 |
| 150 g de beurre | 150 克黄油 |
```

### Format 2 — Bullet list

```markdown
## Pâte

- 250 g de farine
- 150 g d'œufs
- 150 g de beurre
```

**Frontmatter fields:**

| Field | Description |
|-------|-------------|
| `titre` | Recipe name (used in search and output headers) |
| `niveau` | `basique` / `intermédiaire` / `supérieur` |
| `source` | Origin of the recipe |
| `source_file` | Source file type (`recipe.1.md` = bilingual table, best for Baker's %) |

## Baker's Percentage concept

Baker's % expresses every ingredient as a ratio of the **base ingredient** (100%):

```
Baker's % = (ingredient weight / base weight) × 100
```

| Preparation | Default base |
|-------------|-------------|
| Bread, brioche, tart dough | Flour (`farine`) |
| Ganache | Chocolate (`chocolat`) |
| Cream-based | Largest component by weight |

**Typical ranges:**

| Preparation | Water% | Fat% | Sugar% | Eggs% |
|-------------|--------|------|--------|-------|
| Baguette    | 65–70% | 1–2% | 1–2%  | 0%    |
| Brioche     | 25–35% | 50–70% | 15–25% | 60–80% |
| Tart dough  | 10–20% | 50–60% | 30–40% | 15–25% |
| Cake        | 20–40% | 40–60% | 60–80% | 50–80% |

## Knowledge base

`data/recipe-library/baker/knowledge/` contains technique reference files covering:

| Topic | File |
|-------|------|
| Ganache ratios / emulsification | `ganache.md` |
| Mousse stability / structure | `mousse-structure.md` |
| Acidity control / high-acid fruit | `acidity-control.md` |
| Hydrocolloid selection and dosage | `hydrocolloids.md` |
| Crème Pâtissière ratios | `creme-patissiere.md` |
| Pâte Sucrée (Sablage vs Crémage) | `pate-sucree.md` |
| Pâte à Choux / leavening | `pate-a-choux.md` |
| Caramel types and temperatures | `caramel.md` |
| Meringue (French / Swiss / Italian) | `meringue.md` |
| Praliné and croustillant bases | `praline-croustillant.md` |
| Crème Mousseline variants | `creme-mousseline.md` |
| Biscuit Joconde vs Dacquoise | `biscuit-joconde-dacquoise.md` |

## License

MIT — see [LICENSE](LICENSE).

The recipe files in `_md/` are **not included** in this repository. Always ensure you have the right to digitize and use any recipe you add to this system.

#!/usr/bin/env python3
"""
Baker's Percentage calculator for Le Cordon Bleu recipe MD files.

Baker's % expresses every ingredient as a percentage of the base ingredient
(typically flour for bread/tart dough, or the dominant ingredient for other
preparations). This lets chefs scale recipes precisely and compare formulas
across different batch sizes.

Usage:
    python scripts/bakers_percent.py <recipe_md_file> [--base INGREDIENT] [--scale GRAMS]
    python scripts/bakers_percent.py --find <name_fragment>

Examples:
    python scripts/bakers_percent.py data/recipe-library/baker/_md/glm/paris-brest.md
    python scripts/bakers_percent.py data/recipe-library/baker/_md/glm/brioche.md --scale 2000
    python scripts/bakers_percent.py --find charlotte
"""

import re
import argparse
from pathlib import Path
from typing import Optional

RECIPE_DIRS = [
    Path('data/recipe-library/baker/_md/glm/intermediate'),
    Path('data/recipe-library/baker/_md/glm'),
    Path('data/recipe-library/baker/_md'),
]

# ─── Unit normalization ───────────────────────────────────────────────────────

UNIT_TO_GRAMS = {
    'g': 1.0,
    'gr': 1.0,
    'kg': 1000.0,
    'mg': 0.001,
    'ml': 1.0,      # water-like liquids: 1ml ≈ 1g
    'cl': 10.0,
    'dl': 100.0,
    'l': 1000.0,
    'L': 1000.0,
}

def parse_quantity(qty_str: str) -> Optional[float]:
    """Parse a quantity string like '250g', '1.5kg', '2-3' into grams.
    Returns None for non-numeric quantities (QS, 1 gousse, etc.).
    """
    qty_str = qty_str.strip()

    # Range: "4-5 œufs" → take midpoint
    range_m = re.match(r'^(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)', qty_str)
    if range_m:
        lo, hi = float(range_m.group(1)), float(range_m.group(2))
        qty_str = str((lo + hi) / 2)

    # Number + unit
    m = re.match(r'^(\d+\.?\d*)\s*([a-zA-Z]+)', qty_str)
    if m:
        value = float(m.group(1))
        unit = m.group(2).lower().rstrip('s')  # normalise plural
        return value * UNIT_TO_GRAMS.get(unit, 1.0)

    # Bare number (pieces, units)
    bare = re.match(r'^(\d+\.?\d*)$', qty_str)
    if bare:
        return float(bare.group(1))

    return None  # QS, 1 gousse de vanille, etc.


# ─── Recipe parsing ───────────────────────────────────────────────────────────

class Ingredient:
    def __init__(self, name: str, qty_str: str, grams: Optional[float]):
        self.name = name
        self.qty_str = qty_str
        self.grams = grams
        self.pct: Optional[float] = None  # filled by calc_bakers_pct

    def __repr__(self):
        return f'Ingredient({self.name!r}, {self.qty_str!r}, {self.grams}g)'


class Component:
    def __init__(self, name: str):
        self.name = name
        self.ingredients: list[Ingredient] = []


class Recipe:
    def __init__(self, title: str, source_file: str):
        self.title = title
        self.source_file = source_file
        self.components: list[Component] = []

    def all_ingredients(self) -> list[tuple[str, Ingredient]]:
        """Return (component_name, ingredient) pairs."""
        pairs = []
        for comp in self.components:
            for ing in comp.ingredients:
                pairs.append((comp.name, ing))
        return pairs


def parse_md_recipe(path: Path) -> Recipe:
    """Parse a recipe MD file into a Recipe object."""
    text = path.read_text(encoding='utf-8', errors='replace')

    # Extract titre from frontmatter
    titre_m = re.search(r'^titre:\s*(.+)$', text, re.MULTILINE)
    title = titre_m.group(1).strip() if titre_m else path.stem

    source_m = re.search(r'^source_file:\s*(.+)$', text, re.MULTILINE)
    source = source_m.group(1).strip() if source_m else str(path.name)

    recipe = Recipe(title, source)
    current_component = None

    for line in text.split('\n'):
        line = line.rstrip()

        # Component heading: ## or ###
        heading_m = re.match(r'^#{2,3}\s+(.+)', line)
        if heading_m:
            heading = heading_m.group(1).strip()
            # Strip Chinese from heading
            heading_fr = re.sub(r'[\u4e00-\u9fff]+.*', '', heading).strip()
            heading_fr = re.sub(r'/\s*$', '', heading_fr).strip() or heading
            current_component = Component(heading_fr)
            recipe.components.append(current_component)
            continue

        # Markdown table ingredient row: | 250g de farine | 250 克面粉 |
        if line.startswith('|') and '|' in line[1:]:
            cells = [c.strip() for c in line.split('|') if c.strip()]
            # Skip header rows (Ingrédients / 食材 / ---)
            if not cells or re.match(r'^[-:]+$', cells[0]):
                continue
            if cells[0].lower() in ('ingrédients', 'ingredients', 'ingrédient',
                                     '食材', '原料', '用料'):
                continue

            # Parse French cell: "250 g de farine" or "farine 250g"
            french_cell = cells[0] if cells else ''
            qty_str, name = _split_french_ingredient(french_cell)

            if not name:
                continue

            grams = parse_quantity(qty_str) if qty_str else None

            if current_component is None:
                current_component = Component('(sans titre)')
                recipe.components.append(current_component)

            current_component.ingredients.append(Ingredient(name, qty_str, grams))
            continue

        # Bullet list ingredient: "- 250 g de farine" (recipe.3 format)
        bullet_m = re.match(r'^-\s+(?!\*\*)(.+)', line)
        if bullet_m and current_component is not None:
            content = bullet_m.group(1).strip()
            qty_str, name = _split_french_ingredient(content)
            if name and not re.match(r'^[\u4e00-\u9fff]', name):  # skip Chinese-only
                grams = parse_quantity(qty_str) if qty_str else None
                current_component.ingredients.append(Ingredient(name, qty_str, grams))

    return recipe


def _split_french_ingredient(text: str) -> tuple[str, str]:
    """Split '250 g de farine' into ('250g', 'farine').
    Returns ('', '') if can't parse a meaningful name.
    """
    # Strip Chinese portion
    text = re.sub(r'\s*[\u4e00-\u9fff].*$', '', text).strip()
    if not text:
        return '', ''

    # Pattern: NUMBER UNIT? (de/d'/du/des)? NAME
    m = re.match(
        r'^([\d.,/\-]+\s*(?:g|kg|ml|cl|dl|L|l|gr)?)?\s*'
        r'(?:de\s+|d[\'\']\s*|du\s+|des\s+|à\s+)?'
        r'(.+)$',
        text, re.IGNORECASE
    )
    if m:
        qty = (m.group(1) or '').strip()
        name = (m.group(2) or '').strip()
        # If qty is empty but text starts with a number, it might be "4 œufs"
        if not qty:
            num_m = re.match(r'^(\d+[\d.,]*)\s+(.+)$', text)
            if num_m:
                qty, name = num_m.group(1), num_m.group(2)
        return qty, name

    return '', text


# ─── Baker's % calculation ────────────────────────────────────────────────────

# Likely "base" ingredients (highest priority for flour-based formulas)
BASE_KEYWORDS = [
    'farine', 'flour', 'farine de blé', 'farine t55', 'farine t45',
    'farine de seigle', 'farine complète',
]
# Secondary bases for non-flour preparations
SECONDARY_BASES = [
    'chocolat', 'chocolate', 'crème', 'cream', 'lait', 'milk',
    'sucre', 'sugar', 'amande', 'almond',
]


def find_base(ingredients: list[Ingredient], base_hint: Optional[str] = None) -> Optional[Ingredient]:
    """Find the base ingredient for Baker's % calculation."""
    candidates = [ing for ing in ingredients if ing.grams is not None]
    if not candidates:
        return None

    if base_hint:
        hint_lo = base_hint.lower()
        for ing in candidates:
            if hint_lo in ing.name.lower():
                return ing

    # Try primary base keywords
    for kw in BASE_KEYWORDS:
        for ing in candidates:
            if kw in ing.name.lower():
                return ing

    # Secondary: largest weight ingredient
    return max(candidates, key=lambda i: i.grams or 0)


def calc_bakers_pct(
    recipe: Recipe,
    base_hint: Optional[str] = None,
    scale_grams: Optional[float] = None,
) -> tuple[Optional[Ingredient], dict]:
    """Calculate Baker's % for all ingredients in a recipe.

    Returns (base_ingredient, {component_name: [(ingredient, pct, scaled_grams)]}).
    """
    all_ings = [ing for _, ing in recipe.all_ingredients()]
    base = find_base(all_ings, base_hint)

    if base is None or base.grams is None:
        return None, {}

    base_g = base.grams
    scale_factor = (scale_grams / base_g) if scale_grams else 1.0

    result = {}
    for comp in recipe.components:
        rows = []
        for ing in comp.ingredients:
            pct = (ing.grams / base_g * 100) if ing.grams else None
            scaled = (ing.grams * scale_factor) if ing.grams else None
            rows.append((ing, pct, scaled))
        if rows:
            result[comp.name] = rows

    return base, result


# ─── Lookup / search ──────────────────────────────────────────────────────────

def find_recipes(name_fragment: str) -> list[Path]:
    """Search recipe directories by filename or file content (supports Chinese)."""
    name_lo = name_fragment.lower().replace(' ', '-')
    matches = []
    seen = set()
    for d in RECIPE_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob('*.md')):
            if p in seen:
                continue
            hit = (name_lo in p.stem.lower() or
                   name_lo in p.stem.replace('-', ' '))
            if not hit:
                try:
                    content = p.read_text(encoding='utf-8', errors='replace')
                    hit = name_fragment in content
                except OSError:
                    pass
            if hit:
                matches.append(p)
                seen.add(p)
    return matches


def search_by_ingredient(fragment: str) -> list[tuple[Path, str]]:
    """Find all recipes containing a specific ingredient (French or Chinese)."""
    fragment_lo = fragment.lower()
    results = []
    seen = set()
    for d in RECIPE_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob('*.md')):
            if p in seen:
                continue
            try:
                content = p.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            if fragment_lo in content.lower() or fragment in content:
                title_m = re.search(r'^# (.+)$', content, re.MULTILINE)
                title = title_m.group(1).strip() if title_m else p.stem
                results.append((p, title))
                seen.add(p)
    return results


# ─── Output formatting ────────────────────────────────────────────────────────

def format_report(
    recipe: Recipe,
    base: Optional[Ingredient],
    result: dict,
    scale_grams: Optional[float] = None,
) -> str:
    lines = [
        f'# Baker\'s % — {recipe.title}',
        f'Source: {recipe.source_file}',
    ]
    if base:
        lines.append(f'Base: **{base.name}** ({base.grams:.0f}g = 100%)')
    if scale_grams:
        sf = scale_grams / (base.grams if base and base.grams else 1)
        lines.append(f'Scaled to: {scale_grams:.0f}g base (×{sf:.2f})')
    lines.append('')

    if not result:
        lines.append('⚠ Could not determine base ingredient for Baker\'s % calculation.')
        return '\n'.join(lines)

    for comp_name, rows in result.items():
        lines.append(f'## {comp_name}')
        header = f'{"Ingredient":<30} {"Baker%":>8} {"Original":>10}'
        if scale_grams:
            header += f' {"Scaled":>10}'
        lines.append(header)
        lines.append('-' * len(header))

        for ing, pct, scaled in rows:
            orig = f'{ing.grams:.1f}g' if ing.grams else ing.qty_str or 'QS'
            pct_str = f'{pct:.1f}%' if pct else '—'
            row = f'{ing.name:<30} {pct_str:>8} {orig:>10}'
            if scale_grams:
                sc_str = f'{scaled:.1f}g' if scaled else '—'
                row += f' {sc_str:>10}'
            lines.append(row)
        lines.append('')

    return '\n'.join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Baker's % calculator for recipe MD files")
    parser.add_argument('recipe_path', nargs='?', help='Path to recipe MD file')
    parser.add_argument('--find', metavar='NAME', help='Search recipes by name (French or Chinese)')
    parser.add_argument('--ingredient', metavar='NAME', help='Find all recipes using an ingredient')
    parser.add_argument('--base', metavar='INGREDIENT', help='Base ingredient name (default: flour)')
    parser.add_argument('--scale', type=float, metavar='GRAMS',
                        help='Scale to this many grams of base ingredient')
    args = parser.parse_args()

    if args.find:
        matches = find_recipes(args.find)
        if not matches:
            print(f'No recipes found matching "{args.find}"')
        else:
            print(f'Found {len(matches)} recipe(s):')
            for p in matches:
                print(f'  {p}')
        return

    if args.ingredient:
        results = search_by_ingredient(args.ingredient)
        if not results:
            print(f'No recipes found containing "{args.ingredient}"')
        else:
            print(f'Found {len(results)} recipe(s) using "{args.ingredient}":')
            for p, title in results:
                print(f'  {title}')
                print(f'    → {p}')
        return

    if not args.recipe_path:
        parser.print_help()
        return

    path = Path(args.recipe_path)
    if not path.exists():
        print(f'File not found: {path}')
        return

    recipe = parse_md_recipe(path)
    base, result = calc_bakers_pct(recipe, base_hint=args.base, scale_grams=args.scale)
    print(format_report(recipe, base, result, scale_grams=args.scale))


if __name__ == '__main__':
    main()

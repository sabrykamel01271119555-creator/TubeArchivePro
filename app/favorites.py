# =============================================================================
# TubeArchive Pro  |  Version 1.0.14  |  File: app/favorites.py
# Version history of this file:
#   1.0.14 - Category icons; add_category / edit_category / delete_category; label()
#   1.0.9 - Created: favorite categories and the videos placed in them
# =============================================================================
"""Favorites: categories (user defined) and which history record sits in which category.

data/favorites/favorites.json  ->  {"categories": ["Favorites", "Music"], "items": {"<record id>": "Music"}}
A video is in at most one category (adding it again moves it).
"""
import json

from .paths import FAVORITES_FILE


class FavoritesManager:
    def __init__(self):
        self.categories: list[str] = []
        self.items: dict[str, str] = {}
        self.icons: dict[str, str] = {}               # category -> icon (one emoji)

    def load(self):
        try:
            d = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
            cats = d.get("categories", [])
            items = d.get("items", {})
            self.categories = [c for c in cats if isinstance(c, str) and c.strip()]
            self.items = {k: v for k, v in items.items() if isinstance(v, str)} if isinstance(items, dict) else {}
            icons = d.get("icons", {})
            self.icons = {k: v for k, v in icons.items() if isinstance(k, str) and isinstance(v, str)} \
                if isinstance(icons, dict) else {}
        except (OSError, ValueError, AttributeError):
            self.categories, self.items, self.icons = [], {}, {}

    def save(self):
        FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
        FAVORITES_FILE.write_text(json.dumps({"categories": self.categories, "items": self.items, "icons": self.icons},
                                             indent=2, ensure_ascii=False), encoding="utf-8")

    def ensure_category(self, name: str) -> str:
        name = " ".join(name.split())
        low = {c.lower(): c for c in self.categories}
        if name.lower() in low:                       # same name in other letter case -> reuse it
            return low[name.lower()]
        self.categories.append(name)
        return name

    def add(self, rid: str, category: str) -> str:
        category = self.ensure_category(category)
        self.items[rid] = category
        self.save()
        return category

    def remove(self, rid: str):
        if rid in self.items:
            del self.items[rid]
            self.save()

    def is_favorite(self, rid: str) -> bool:
        return rid in self.items

    def category_of(self, rid: str) -> str | None:
        return self.items.get(rid)

    def icon_of(self, category) -> str:
        return self.icons.get(category or "", "")

    def label(self, category) -> str:
        """'🎬 Cinema' (icon + name) for lists and card tags."""
        icon = self.icon_of(category)
        return f"{icon} {category}" if icon else (category or "")

    def add_category(self, name: str, icon: str = "") -> str | None:
        """New category with an icon. None = the name is empty or already used."""
        name = " ".join(name.split())
        if not name or name.lower() in {c.lower() for c in self.categories}:
            return None
        self.categories.append(name)
        if icon:
            self.icons[name] = icon
        self.save()
        return name

    def edit_category(self, old: str, new: str, icon: str = "") -> bool:
        """Rename (and re-icon) a category; its videos follow. False = empty name or the name is used by another one."""
        new = " ".join(new.split())
        if old not in self.categories or not new:
            return False
        if new.lower() != old.lower() and new.lower() in {c.lower() for c in self.categories}:
            return False
        self.categories[self.categories.index(old)] = new
        self.items = {k: (new if v == old else v) for k, v in self.items.items()}
        self.icons.pop(old, None)
        if icon:
            self.icons[new] = icon
        self.save()
        return True

    def delete_category(self, name: str):
        """The category goes away; its videos leave the favorites (they stay in the Library)."""
        if name in self.categories:
            self.categories.remove(name)
        self.items = {k: v for k, v in self.items.items() if v != name}
        self.icons.pop(name, None)
        self.save()

    def used_categories(self) -> list[str]:
        """Categories that contain at least one video (for the filter of the Downloads page)."""
        used = set(self.items.values())
        return [c for c in self.categories if c in used]

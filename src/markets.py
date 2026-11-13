"""Market types: which Excel templates each market uses.

The WordPress exports have the same format for every market. There are two
WordPress instances, one for julmaten and one shared by julmarknad and
påskmarknad, and their exports are parsed identically.

The market type therefore only selects *templates*, because these differ
per market:

- placeringsnycklar_<key>.xlsx  packing categories -> pickup area, and the
                                packing order (e.g. 'julpynt' only at jul,
                                'semla' only at påsk; different area labels)
- packlista_template_<key>.xlsx packing-list layout (footer labels differ)
- schedule_<key>.xlsx           pickup dates and time slots of the season

To add a market: add a MarketProfile below and the three template files.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MarketProfile:
    key: str            # used in template file names, e.g. 'pask'
    label: str          # shown in the UI
    wp_instance: str    # documentation only: which WordPress instance exports the data

    def packing_categories(self, template_dir: Path) -> Path:
        return template_dir / f'placeringsnycklar_{self.key}.xlsx'

    def schedule(self, template_dir: Path) -> Path:
        return template_dir / f'schedule_{self.key}.xlsx'

    def packlista_template(self, template_dir: Path) -> Path:
        return template_dir / f'packlista_template_{self.key}.xlsx'

    def template_files(self, template_dir: Path) -> list:
        return [self.packing_categories(template_dir),
                self.packlista_template(template_dir),
                self.schedule(template_dir)]


JULMARKNAD = MarketProfile('julmarknad', 'Julmarknad', wp_instance='marknad')
JULMATEN = MarketProfile('julmaten', 'Julmaten', wp_instance='julmaten')
PASK = MarketProfile('pask', 'Påskmarknad', wp_instance='marknad')

# In UI order
MARKETS = {m.key: m for m in (JULMARKNAD, JULMATEN, PASK)}

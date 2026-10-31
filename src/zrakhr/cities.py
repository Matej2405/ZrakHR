"""Gradovi za koje se prikupljaju podaci."""

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    """Grad sa zemljopisnim koordinatama (WGS84)."""

    name: str
    latitude: float
    longitude: float

    @property
    def slug(self) -> str:
        """Naziv prikladan za imena datoteka, npr. 'slavonski-brod'."""
        return self.name.lower().replace(" ", "-")


CITIES: dict[str, City] = {
    city.name: city
    for city in (
        City("Zagreb", 45.8150, 15.9819),
        City("Rijeka", 45.3271, 14.4422),
        City("Split", 43.5081, 16.4402),
        City("Osijek", 45.5550, 18.6955),
        City("Slavonski Brod", 45.1603, 18.0156),
    )
}

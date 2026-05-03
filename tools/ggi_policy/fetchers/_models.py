from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Control:
    id: str
    title: str
    description: str = ""


@dataclass(frozen=True)
class Metadata:
    version: str
    fetched_at: date
    source_url: str
    fetcher: str
    notes: str = ""


@dataclass(frozen=True)
class FrameworkData:
    metadata: Metadata
    controls: list[Control] = field(default_factory=list)

    def to_json(self) -> dict:
        meta = {
            "version": self.metadata.version,
            "fetched_at": self.metadata.fetched_at.isoformat(),
            "source_url": self.metadata.source_url,
            "fetcher": self.metadata.fetcher,
        }
        if self.metadata.notes:
            meta["notes"] = self.metadata.notes
        out_controls = []
        for c in self.controls:
            entry = {"id": c.id, "title": c.title}
            if c.description:
                entry["description"] = c.description
            out_controls.append(entry)
        return {"metadata": meta, "controls": out_controls}

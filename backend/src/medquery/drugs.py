from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True, slots=True)
class DrugIdentity:
    drug_id: str
    drug_name: str
    aliases: tuple[str, ...]
    dosage_form: str
    specification: str
    manufacturer: str
    approval_number: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DrugIdentity:
        return cls(
            drug_id=str(value["drug_id"]),
            drug_name=str(value["drug_name"]),
            aliases=tuple(str(item) for item in value.get("aliases", [])),
            dosage_form=str(value["dosage_form"]),
            specification=str(value["specification"]),
            manufacturer=str(value["manufacturer"]),
            approval_number=str(value["approval_number"]),
        )

    def to_prompt_dict(self) -> dict[str, object]:
        return {
            **self.to_client_dict(),
            "aliases": list(self.aliases),
            "approval_number": self.approval_number,
        }

    def to_client_dict(self) -> dict[str, str]:
        return {
            "drug_id": self.drug_id,
            "drug_name": self.drug_name,
            "dosage_form": self.dosage_form,
            "specification": self.specification,
            "manufacturer": self.manufacturer,
        }


class DrugRegistry:
    def __init__(self, drugs: tuple[DrugIdentity, ...]) -> None:
        self._drugs = drugs
        self._by_id = {drug.drug_id: drug for drug in drugs}

    @classmethod
    def load(cls, path: Path) -> DrugRegistry:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(tuple(DrugIdentity.from_dict(item) for item in payload["drugs"]))

    def get(self, drug_id: str) -> DrugIdentity | None:
        return self._by_id.get(drug_id)

    def prompt_catalog(self) -> list[dict[str, object]]:
        return [drug.to_prompt_dict() for drug in self._drugs]

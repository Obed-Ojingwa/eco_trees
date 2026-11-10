import hashlib
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.core.config import settings
from app.core.errors import ApiError


@dataclass(frozen=True)
class RegistryProject:
    reference: str
    registry_source: str


@dataclass(frozen=True)
class MrvReference:
    reference: str
    registry_source: str


@dataclass(frozen=True)
class IssuedCredit:
    serial: str
    unit_index: int
    registry_credit_ref: str


@dataclass(frozen=True)
class Retirement:
    reference: str
    serials: tuple[str, ...]
    beneficiary: str
    registry_source: str


@dataclass(frozen=True)
class Certificate:
    retirement_reference: str
    serials: tuple[str, ...]
    beneficiary: str
    registry_source: str


class RegistryAdapter(Protocol):
    source: str

    def register_project(self, batch: dict) -> RegistryProject: ...

    def submit_mrv(self, project: RegistryProject, package: dict) -> MrvReference: ...

    def review_mrv(self, mrv: MrvReference, decision: str, note: str) -> MrvReference: ...

    def issue(self, mrv: MrvReference, units: int, vintage: int, batch_number: int) -> list[IssuedCredit]: ...

    def retire(self, serials: Sequence[str], beneficiary: str) -> Retirement: ...

    def certificate(self, retirement: Retirement) -> Certificate: ...


class InternalMockAdapter:
    source = "mock"

    def register_project(self, batch: dict) -> RegistryProject:
        return RegistryProject(
            reference=f"MOCK-PROJECT-{batch['batch_number']:06d}",
            registry_source=self.source,
        )

    def submit_mrv(self, project: RegistryProject, package: dict) -> MrvReference:
        digest = hashlib.sha256(
            f"{project.reference}:{package['package_sha256']}".encode("utf-8")
        ).hexdigest()[:16]
        return MrvReference(
            reference=f"MOCK-MRV-{digest}",
            registry_source=self.source,
        )

    def review_mrv(self, mrv: MrvReference, decision: str, note: str) -> MrvReference:
        return mrv

    def issue(
        self,
        mrv: MrvReference,
        units: int,
        vintage: int,
        batch_number: int,
    ) -> list[IssuedCredit]:
        return [
            IssuedCredit(
                serial=f"EC-NG-{vintage}-{batch_number:06d}-{unit_index:06d}",
                unit_index=unit_index,
                registry_credit_ref=f"{mrv.reference}-{unit_index:06d}",
            )
            for unit_index in range(1, units + 1)
        ]

    def retire(self, serials: Sequence[str], beneficiary: str) -> Retirement:
        sorted_serials = tuple(sorted(set(serials)))
        digest = hashlib.sha256(
            ("\n".join(sorted_serials) + "\n" + beneficiary).encode("utf-8")
        ).hexdigest()[:20]
        return Retirement(
            reference=f"MOCK-RETIRE-{digest}",
            serials=sorted_serials,
            beneficiary=beneficiary,
            registry_source=self.source,
        )

    def certificate(self, retirement: Retirement) -> Certificate:
        return Certificate(
            retirement_reference=retirement.reference,
            serials=retirement.serials,
            beneficiary=retirement.beneficiary,
            registry_source=retirement.registry_source,
        )


class XtradotCarbonAdapter:
    source = "xtradot"

    @staticmethod
    def _not_ready() -> None:
        raise ApiError(
            503,
            "REGISTRY_SCHEMA_UNCONFIRMED",
            "Xtradot carbon registry request and response schemas have not been verified. "
            "Use the mock registry until the sandbox specification is available.",
        )

    def register_project(self, batch: dict) -> RegistryProject:
        self._not_ready()

    def submit_mrv(self, project: RegistryProject, package: dict) -> MrvReference:
        self._not_ready()

    def review_mrv(self, mrv: MrvReference, decision: str, note: str) -> MrvReference:
        self._not_ready()

    def issue(
        self,
        mrv: MrvReference,
        units: int,
        vintage: int,
        batch_number: int,
    ) -> list[IssuedCredit]:
        self._not_ready()

    def retire(self, serials: Sequence[str], beneficiary: str) -> Retirement:
        self._not_ready()

    def certificate(self, retirement: Retirement) -> Certificate:
        self._not_ready()


def get_registry_adapter() -> RegistryAdapter:
    if settings.registry_backend == "mock":
        return InternalMockAdapter()
    if settings.registry_backend == "xtradot":
        if not settings.registry_xtradot_enabled:
            raise ApiError(
                503,
                "REGISTRY_BACKEND_DISABLED",
                "The Xtradot registry backend is disabled until its schemas are verified.",
            )
        return XtradotCarbonAdapter()
    raise RuntimeError(f"Unsupported registry backend: {settings.registry_backend}")

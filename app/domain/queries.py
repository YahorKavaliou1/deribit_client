from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Inclusive range of UNIX timestamps (seconds); either bound may be open."""

    start: int | None = None
    end: int | None = None

    def __post_init__(self) -> None:
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError(f"Range start {self.start} is after its end {self.end}")


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError(f"Limit must be positive, got {self.limit}")
        if self.offset < 0:
            raise ValueError(f"Offset must be non-negative, got {self.offset}")

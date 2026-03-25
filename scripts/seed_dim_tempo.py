"""Generate a dim_tempo CSV from 2020 to 2030."""

from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path


UF_HOLIDAYS = {
    "SP": {(1, 25)},
    "RJ": {(4, 23)},
    "CE": {(3, 19)},
    "GO": {(10, 24)},
}
NATIONAL_HOLIDAYS = {(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)}


def iter_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def build_rows(start: date, end: date) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for current in iter_dates(start, end):
        base_row = {
            "data_ref": current.isoformat(),
            "dia_semana": str(current.weekday()),
            "dia_mes": str(current.day),
            "mes": str(current.month),
            "trimestre": str(((current.month - 1) // 3) + 1),
            "ano": str(current.year),
            "flag_feriado_nacional": str((current.month, current.day) in NATIONAL_HOLIDAYS).lower(),
        }
        for uf in ["SP", "RJ", "CE", "GO"]:
            is_holiday = (current.month, current.day) in UF_HOLIDAYS.get(uf, set())
            is_business_day = current.weekday() < 5 and not is_holiday and (current.month, current.day) not in NATIONAL_HOLIDAYS
            rows.append(
                {
                    **base_row,
                    "uf": uf,
                    "flag_feriado_uf": str(is_holiday).lower(),
                    "flag_dia_util": str(is_business_day).lower(),
                }
            )
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Arquivo CSV de saída.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = build_rows(date(2020, 1, 1), date(2030, 12, 31))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

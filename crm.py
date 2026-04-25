#!/usr/bin/env python3
"""CLI CRM for leads that responded to an email campaign."""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional


DB_PATH = Path("crm.db")


class LeadStatus(str, Enum):
    REJECTED = "отказ"
    IN_PROGRESS = "в работе"
    INTERESTED = "заинтересован"
    PROPOSAL_REVIEW = "рассматривает КП"
    CONTRACT_SIGNED = "заключен договор"


@dataclass
class Lead:
    id: int
    company_name: str
    contact_name: str
    email: str
    notes: str
    status: LeadStatus
    created_at: str
    updated_at: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                notes TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def create_lead(
    company_name: str,
    contact_name: str,
    email: str,
    notes: str,
    status: LeadStatus,
) -> int:
    ts = now_iso()
    with connect_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO leads (company_name, contact_name, email, notes, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (company_name, contact_name, email, notes, status.value, ts, ts),
        )
        return cur.lastrowid


def list_leads(status: Optional[LeadStatus] = None) -> Iterable[Lead]:
    query = "SELECT * FROM leads"
    params: tuple[str, ...] = ()

    if status is not None:
        query += " WHERE status = ?"
        params = (status.value,)

    query += " ORDER BY updated_at DESC"

    with connect_db() as conn:
        rows = conn.execute(query, params).fetchall()

    for row in rows:
        yield Lead(
            id=row["id"],
            company_name=row["company_name"],
            contact_name=row["contact_name"],
            email=row["email"],
            notes=row["notes"],
            status=LeadStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def update_status(lead_id: int, new_status: LeadStatus) -> bool:
    with connect_db() as conn:
        cur = conn.execute(
            "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
            (new_status.value, now_iso(), lead_id),
        )
        return cur.rowcount > 0


def add_note(lead_id: int, note: str) -> bool:
    with connect_db() as conn:
        lead = conn.execute("SELECT notes FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if lead is None:
            return False

        current_notes = lead["notes"]
        merged_notes = f"{current_notes}\n[{now_iso()}] {note}".strip()
        conn.execute(
            "UPDATE leads SET notes = ?, updated_at = ? WHERE id = ?",
            (merged_notes, now_iso(), lead_id),
        )
        return True


def status_from_string(value: str) -> LeadStatus:
    normalized = value.strip().lower()
    for status in LeadStatus:
        if normalized == status.value.lower():
            return status
    allowed = ", ".join(s.value for s in LeadStatus)
    raise argparse.ArgumentTypeError(f"Неизвестный статус '{value}'. Допустимые: {allowed}")


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="CRM для лидов, ответивших на email-рассылку о сотрудничестве",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Инициализировать базу данных")

    add_parser = subparsers.add_parser("add", help="Добавить нового лида")
    add_parser.add_argument("--company", required=True, help="Название компании")
    add_parser.add_argument("--contact", required=True, help="Контактное лицо")
    add_parser.add_argument("--email", required=True, help="Email лида")
    add_parser.add_argument("--notes", default="", help="Первичная заметка")
    add_parser.add_argument(
        "--status",
        type=status_from_string,
        default=LeadStatus.INTERESTED,
        help="Статус лида",
    )

    list_parser = subparsers.add_parser("list", help="Вывести список лидов")
    list_parser.add_argument(
        "--status",
        type=status_from_string,
        default=None,
        help="Фильтр по статусу",
    )

    upd_parser = subparsers.add_parser("set-status", help="Изменить статус лида")
    upd_parser.add_argument("lead_id", type=int, help="ID лида")
    upd_parser.add_argument("status", type=status_from_string, help="Новый статус")

    note_parser = subparsers.add_parser("add-note", help="Добавить заметку к лиду")
    note_parser.add_argument("lead_id", type=int, help="ID лида")
    note_parser.add_argument("note", help="Текст заметки")

    return parser


def print_leads(leads: Iterable[Lead]) -> None:
    leads = list(leads)
    if not leads:
        print("Лиды не найдены.")
        return

    for lead in leads:
        print(
            f"ID={lead.id} | {lead.company_name} | {lead.contact_name} | {lead.email} | "
            f"Статус: {lead.status.value} | Обновлен: {lead.updated_at}"
        )
        if lead.notes:
            print(f"  Заметки: {lead.notes}")


def main() -> None:
    parser = setup_parser()
    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        print(f"База данных инициализирована: {DB_PATH}")
        return

    init_db()

    if args.command == "add":
        try:
            lead_id = create_lead(
                company_name=args.company,
                contact_name=args.contact,
                email=args.email,
                notes=args.notes,
                status=args.status,
            )
            print(f"Лид добавлен с ID={lead_id}")
        except sqlite3.IntegrityError:
            print("Лид с таким email уже существует.")

    elif args.command == "list":
        print_leads(list_leads(status=args.status))

    elif args.command == "set-status":
        if update_status(args.lead_id, args.status):
            print(f"Статус лида {args.lead_id} изменен на '{args.status.value}'.")
        else:
            print(f"Лид с ID={args.lead_id} не найден.")

    elif args.command == "add-note":
        if add_note(args.lead_id, args.note):
            print(f"Заметка добавлена к лиду {args.lead_id}.")
        else:
            print(f"Лид с ID={args.lead_id} не найден.")


if __name__ == "__main__":
    main()

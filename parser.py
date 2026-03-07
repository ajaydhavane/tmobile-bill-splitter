import json
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber


@dataclass
class User:
    name: str
    plan: float = 0.0
    equipment: float = 0.0
    services: float = 0.0
    one_time_charges: float = 0.0
    total: float = 0.0


def dollar_str_to_float(dollar_str: str) -> float:
    clean = dollar_str.strip()
    if clean == "-" or not clean:
        return 0.0
    clean = clean.replace("$", "")
    try:
        return float(clean)
    except ValueError:
        return 0.0


def extract_account_charges(bill_text: str) -> list[float]:
    lines = bill_text.split("\n")
    try:
        summary_idx = lines.index("THIS BILL SUMMARY")
        account_line = lines[summary_idx + 3]
        if account_line.startswith("Account"):
            parts = account_line.split()
            return [dollar_str_to_float(c) for c in parts[1:-1]]
    except (ValueError, IndexError):
        return [0.0] * 4
    return [0.0] * 4


def parse_bill(pdf_source, user_mapping: dict) -> list[User]:
    with pdfplumber.open(pdf_source) as pdf:
        pages_to_read = pdf.pages[:2]
        bill_text = "\n".join([page.extract_text() or "" for page in pages_to_read])

    pattern = r"^\(\d{3}\)\s\d{3}-\d{4}.*Voice.*$"
    matches: list[str] = re.findall(pattern, bill_text, re.MULTILINE)

    account_charges = extract_account_charges(bill_text)
    num_users = len(matches)
    account_charge_shares = [charge / num_users for charge in account_charges]

    users = []
    for match in matches:
        phone_number = match[:14]
        info = user_mapping["users"].get(phone_number, {"name": phone_number})
        name = info["name"]
        parts = match[14:].split()
        try:
            voice_idx = parts.index("Voice")
            individual_charges = [
                dollar_str_to_float(c) for c in parts[voice_idx + 1 : -1]
            ]
            combined_charges = [
                round(i + s, 2)
                for i, s in zip(individual_charges, account_charge_shares, strict=True)
            ]
            total = round(sum(combined_charges), 2)
            users.append(User(name, *[*combined_charges, total]))
        except ValueError:
            continue

    return users


def parse_bills(pdf_sources, user_mapping: dict) -> list[User]:
    merged: dict[str, User] = {}
    for source in pdf_sources:
        for user in parse_bill(source, user_mapping):
            if user.name in merged:
                m = merged[user.name]
                new_plan = m.plan + user.plan
                new_equip = m.equipment + user.equipment
                new_serv = m.services + user.services
                new_extra = m.one_time_charges + user.one_time_charges
                new_total = round(new_plan + new_equip + new_serv + new_extra, 2)
                merged[user.name] = User(
                    name=user.name,
                    plan=new_plan,
                    equipment=new_equip,
                    services=new_serv,
                    one_time_charges=new_extra,
                    total=new_total,
                )
            else:
                merged[user.name] = user
    return list(merged.values())


if __name__ == "__main__":
    # Local terminal testing
    from tabulate import tabulate

    mapping = json.loads(Path("users.json").read_text())
    results = parse_bill("/home/ajay/Downloads/SummaryBillNov2025.pdf", mapping)
    data = [
        [u.name, u.plan, u.equipment, u.services, u.one_time_charges, u.total]
        for u in results
    ]
    print(
        tabulate(
            data,
            headers=["Name", "Plan", "Equip", "Serv", "Extra", "Total"],
            tablefmt="rounded_grid",
        ),
    )

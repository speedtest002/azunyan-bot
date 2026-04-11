"""plugins/qr/logic.py — QR core logic (không phụ thuộc hikari)."""
from __future__ import annotations

import ast
import logging

import click
from click.testing import CliRunner

from core.mongo import MongoManager

log = logging.getLogger("azunyan.qr")

qr_collection = MongoManager.get_collection("qr")
banks_collection = MongoManager.get_collection("banks")
_bank_aliases_cache: dict[str, str] | None = None


def load_banks(*, force: bool = False) -> dict[str, str]:
    global _bank_aliases_cache

    if _bank_aliases_cache is not None and not force:
        return _bank_aliases_cache

    bank_data: dict[str, str] = {}
    try:
        for bank in banks_collection.find():
            for alias in bank["aliases"]:
                bank_data[alias] = bank["name"]
    except Exception as e:
        log.error(f"Không thể tải dữ liệu ngân hàng từ MongoDB: {e}")

    _bank_aliases_cache = bank_data
    return bank_data


def qr_generate(bank_name: str, bank_number: str, amount: str | None = None,
                description: str | None = None, account_name: str | None = None) -> str:
    url = f"https://img.vietqr.io/image/{bank_name}-{bank_number}-print.png?"
    if amount:
        url += f"amount={amount}"
    if description:
        url += f"&addInfo={description.replace(' ', '%20')}"
    if account_name:
        url += f"&accountName={account_name.replace(' ', '%20')}"
    return url


def qr_bank_core(
    user_id: int,
    bank_aliases: dict[str, str],
    bank_number: str | None = None,
    bank_name: str | None = None,
    amount: str | None = None,
    description: str | None = None,
    account_name: str | None = None,
) -> tuple[bool, str]:
    user_data = qr_collection.find_one({"_id": user_id})

    if not user_data:
        if not bank_number or not bank_name:
            return False, "Bạn cần dùng `/qr set` để lưu thông tin STK và ngân hàng trước!"
        qr_collection.insert_one({"_id": user_id, "number": bank_number, "name": bank_name})
    else:
        if bank_number and bank_name:
            if bank_name.lower() not in bank_aliases:
                return False, "Tên ngân hàng không hợp lệ, vui lòng kiểm tra lại."
            bank_name = bank_aliases[bank_name.lower()]
            if user_data.get("number") != bank_number or user_data.get("name") != bank_name:
                qr_collection.update_one({"_id": user_id}, {"$set": {"number": bank_number, "name": bank_name}})
        else:
            bank_number = user_data["number"]
            bank_name = user_data["name"]

    return True, qr_generate(bank_name, bank_number, amount, description, account_name)


# ── CLI Parser (prefix command) ───────────────────────────────────────────────
_runner = CliRunner()

@click.command()
@click.option("-b", default=None, help="Ngân hàng")
@click.option("-n", default=None, help="Số tài khoản")
@click.option("-a", default=None, help="Số tiền")
@click.option("-d", default=None, help="Nội dung")
def _cli(b, n, a, d):
    click.echo((b, n, a, d))

def parse_prefix_args(args: tuple) -> tuple | None:
    result = _runner.invoke(_cli, list(args))
    if result.exit_code != 0:
        return None
    return ast.literal_eval(result.output.strip())

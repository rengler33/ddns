# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import json
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar, Union
from pathlib import Path
import re
import tomllib


T = TypeVar('T')
E = TypeVar('E')


def is_valid_ipv4(ip):
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(ipv4_pattern, ip))


@dataclass
class Result(Generic[T, E]):
    """
    A Result type that can either be Ok with a value or Err with an error
    """
    value: Union[T, E]
    is_ok: bool

    @staticmethod
    def ok(value: T) -> 'Result[T, E]':
        return Result(value, True)

    @staticmethod
    def err(error: E) -> 'Result[T, E]':
        return Result(error, False)

    def or_else_with(self, f: Callable[[], 'Result[T, E]']) -> 'Result[T, E]':
        return self if self.is_ok else f()

    def unwrap(self):
        if self.is_ok:
            return self.value
        raise ValueError(self.value)


def load_config(p):
    with open(p, "rb") as f:
        data = tomllib.load(f)
    return data


def get_current_ip():
    ip = (
        get_ip_from_ipify()
        .or_else_with(lambda: get_ip_from_httpbin())
    ).unwrap().strip()
    assert is_valid_ipv4(ip), f"IP {ip} does not appear to be valid"
    return ip


def get_ip_from_ipify():
    try:
        url = "https://api.ipify.org"
        with urllib.request.urlopen(url, timeout=5) as response:
            ip = response.read().decode('utf-8')
            return Result.ok(ip)
    except urllib.error.URLError:
            return Result.err("ipify didn't work")


def get_ip_from_httpbin():
    try:
        url = "https://httpbin.org/ip"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            ip = data['origin']
            return Result.ok(ip)
    except urllib.error.URLError:
        return Result.err("httpbin didn't work")


def load_last_ip(p: Path):
    if not p.exists():
        p.touch()
    return p.read_text().strip()


def save_ip(p: Path, ip: str):
    p.write_text(ip)


def build_cloudflare_headers(data):
    return {
        "Authorization": f'Bearer {data["api_key"]}',
        "Content-Type": "application/json"
    }


def build_cloudflare_body(ip):
    return {
        "content": ip
    }


def update_cloudflare_record_ip(ip, cloudflare_config):
    zone_id = cloudflare_config["zone_id"]
    record_id = cloudflare_config["dns_record_id"]
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    headers = build_cloudflare_headers(cloudflare_config)
    body = build_cloudflare_body(ip)

    req = urllib.request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        method="PATCH",
        headers=headers
    )

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            data = json.loads(response_data)
            if data["success"] is True:
                return Result.ok(ip)
    except urllib.error.HTTPError as e:
        return Result.err({
            "status_code": e.code,
            "error": e.read().decode("utf-8")
        })
    except urllib.error.URLError as e:
        return Result.err({
            'error': str(e.reason)
        })
    return Result.err("something went wrong")


def main():
    config_path = Path("config.toml")
    config = load_config(config_path)

    last_ip_path = Path("last_ip.txt")
    last_ip = load_last_ip(last_ip_path)

    ip = get_current_ip()

    if last_ip == ip:
        sys.exit()

    res = update_cloudflare_record_ip(ip, config["cloudflare"])

    res.unwrap()

    save_ip(last_ip_path, ip)

main()

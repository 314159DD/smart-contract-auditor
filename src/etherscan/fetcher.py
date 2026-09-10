"""
Etherscan (and compatible) contract source fetcher.

Supports: Ethereum, Polygon, Arbitrum, Base, Optimism.
"""
from __future__ import annotations

import time
from typing import Optional

import httpx

# API base URLs for supported chains
_CHAIN_URLS: dict[str, str] = {
    "ethereum": "https://api.etherscan.io/api",
    "polygon": "https://api.polygonscan.com/api",
    "arbitrum": "https://api.arbiscan.io/api",
    "base": "https://api.basescan.org/api",
    "optimism": "https://api-optimistic.etherscan.io/api",
    "bsc": "https://api.bscscan.com/api",
    "avalanche": "https://api.snowtrace.io/api",
}

_RATE_LIMIT_DELAY = 0.2  # seconds between API calls (free tier = 5 req/s)


class EtherscanFetcher:
    """Fetch verified contract source code from Etherscan-compatible block explorers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ""
        self.client = httpx.Client(timeout=30.0)

    def fetch_source(
        self,
        address: str,
        chain: str = "ethereum",
    ) -> dict:
        """
        Fetch verified source code for a contract.

        Returns a dict with:
          - source: str (flattened/primary source)
          - contract_name: str
          - compiler_version: str
          - is_multi_file: bool
          - files: dict[filename, source] (for multi-file contracts)
          - abi: list
          - constructor_args: str
        """
        base_url = _CHAIN_URLS.get(chain.lower())
        if not base_url:
            raise ValueError(f"Unsupported chain: {chain}. Supported: {list(_CHAIN_URLS)}")

        address = address.lower()
        time.sleep(_RATE_LIMIT_DELAY)

        params = {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
        }
        if self.api_key:
            params["apikey"] = self.api_key

        resp = self.client.get(base_url, params=params)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1":
            raise RuntimeError(
                f"Etherscan API error for {address} on {chain}: {data.get('message', 'unknown')}"
            )

        result = data["result"][0]
        source_raw = result.get("SourceCode", "")
        contract_name = result.get("ContractName", "Unknown")
        compiler_version = result.get("CompilerVersion", "")
        abi_raw = result.get("ABI", "[]")

        # Detect multi-file source (JSON with {{...}} wrapper)
        is_multi_file = source_raw.startswith("{{") or source_raw.startswith("{\"")
        files: dict[str, str] = {}
        primary_source = source_raw

        if is_multi_file:
            import json
            # Strip outer {{ }} wrapper if present
            json_str = source_raw
            if json_str.startswith("{{"):
                json_str = json_str[1:-1]
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, dict) and "sources" in parsed:
                    # Standard-JSON input format
                    for filename, file_data in parsed["sources"].items():
                        files[filename] = file_data.get("content", "")
                elif isinstance(parsed, dict):
                    # Simple filename -> source dict
                    for filename, content in parsed.items():
                        if isinstance(content, dict):
                            files[filename] = content.get("content", "")
                        else:
                            files[filename] = str(content)

                # Use the main contract file or concatenate
                main_file = next(
                    (k for k in files if contract_name in k.split("/")[-1]),
                    next(iter(files), None),
                )
                primary_source = files.get(main_file, "") if main_file else "\n\n".join(files.values())
            except json.JSONDecodeError:
                is_multi_file = False  # Fallback to treating as single file

        try:
            import json
            abi = json.loads(abi_raw) if abi_raw and abi_raw != "Contract source code not verified" else []
        except (json.JSONDecodeError, TypeError):
            abi = []

        return {
            "source": primary_source,
            "contract_name": contract_name,
            "compiler_version": self._normalize_compiler_version(compiler_version),
            "is_multi_file": is_multi_file,
            "files": files,
            "abi": abi,
            "constructor_args": result.get("ConstructorArguments", ""),
            "address": address,
            "chain": chain,
        }

    def is_contract_verified(self, address: str, chain: str = "ethereum") -> bool:
        """Quick check whether a contract address has verified source."""
        try:
            result = self.fetch_source(address, chain)
            return bool(result.get("source", "").strip())
        except Exception:
            return False

    @staticmethod
    def _normalize_compiler_version(raw: str) -> str:
        """Extract plain version number from Etherscan compiler string."""
        import re
        m = re.search(r"v?(\d+\.\d+\.\d+)", raw)
        return m.group(1) if m else raw

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

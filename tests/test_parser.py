"""Tests for Solidity parsing engine — Task 1.1 acceptance criteria."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser.solidity import SolidityParser
from src.parser.models import Contract, Function, StateVariable

CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "contracts")
parser = SolidityParser()


def contract_path(name: str) -> str:
    return os.path.join(CONTRACTS_DIR, name)


# ── Helpers ───────────────────────────────────────────────────────────────────

def fn_names(contract: Contract) -> list[str]:
    return [f.name for f in contract.functions]


def var_names(contract: Contract) -> list[str]:
    return [v.name for v in contract.state_variables]


# ── 1. All 5 original contracts parse without errors ─────────────────────────

def test_all_contracts_parse():
    """All 5 original test contracts must parse without raising exceptions."""
    originals = [
        "safe_erc20.sol",
        "vulnerable_reentrancy.sol",
        "vulnerable_overflow.sol",
        "vulnerable_access_control.sol",
        "vulnerable_misc.sol",
    ]
    for fname in originals:
        path = contract_path(fname)
        contracts = parser.parse_file(path)
        assert len(contracts) >= 1, f"{fname}: expected at least 1 contract, got 0"


# ── 2. Parser extracts functions/variables/modifiers from simple ERC-20 ───────

def test_erc20_functions_extracted():
    """Safe ERC-20 should expose mint, burn, rescueETH at minimum."""
    contracts = parser.parse_file(contract_path("safe_erc20.sol"))
    assert contracts, "No contracts parsed from safe_erc20.sol"
    c = contracts[0]
    names = fn_names(c)
    for expected in ("mint", "burn", "rescueETH"):
        assert expected in names, f"Expected function '{expected}' in SafeToken, got: {names}"


def test_erc20_state_variables_extracted():
    """MAX_SUPPLY constant should be detected."""
    contracts = parser.parse_file(contract_path("safe_erc20.sol"))
    c = contracts[0]
    names = var_names(c)
    assert "MAX_SUPPLY" in names, f"Expected MAX_SUPPLY in state variables, got: {names}"


def test_erc20_pragma_extracted():
    """Compiler version must be extracted from pragma."""
    contracts = parser.parse_file(contract_path("safe_erc20.sol"))
    c = contracts[0]
    assert c.compiler_version, "compiler_version should not be empty"
    assert "0.8" in c.compiler_version, f"Expected 0.8.x version, got: {c.compiler_version}"


# ── 3. Inheritance tree correctly resolved ────────────────────────────────────

def test_single_level_inheritance():
    """VulnerableToken has no parent — inheritance list should be empty."""
    contracts = parser.parse_file(contract_path("vulnerable_access_control.sol"))
    token = next((c for c in contracts if c.name == "VulnerableToken"), None)
    assert token is not None, "VulnerableToken not found"


def test_multi_inheritance_parsed():
    """multi_inheritance.sol has deep inheritance: PausableToken -> Pausable -> Ownable."""
    contracts = parser.parse_file(contract_path("multi_inheritance.sol"))
    names = {c.name for c in contracts}
    assert "Ownable" in names, f"Ownable not parsed; found: {names}"
    assert "Pausable" in names, f"Pausable not parsed; found: {names}"
    assert "PausableToken" in names, f"PausableToken not parsed; found: {names}"


def test_multi_inheritance_chain():
    """PausableToken should declare inheritance from IERC20Basic, IERC20Allowance, Pausable."""
    contracts = parser.parse_file(contract_path("multi_inheritance.sol"))
    token = next((c for c in contracts if c.name == "PausableToken"), None)
    assert token is not None, "PausableToken not found"
    assert len(token.inheritance) >= 1, (
        f"PausableToken should have at least 1 parent, got: {token.inheritance}"
    )


def test_interface_flag():
    """Interfaces should be flagged as is_interface=True."""
    contracts = parser.parse_file(contract_path("multi_inheritance.sol"))
    ifaces = [c for c in contracts if c.is_interface]
    assert len(ifaces) >= 1, "Expected at least one interface in multi_inheritance.sol"
    iface_names = {c.name for c in ifaces}
    assert "IERC20Basic" in iface_names or "IERC20Allowance" in iface_names, (
        f"Expected IERC20Basic or IERC20Allowance flagged as interface; got: {iface_names}"
    )


def test_abstract_flag():
    """Abstract contracts should be flagged as is_abstract=True."""
    contracts = parser.parse_file(contract_path("multi_inheritance.sol"))
    abstracts = [c for c in contracts if c.is_abstract]
    assert len(abstracts) >= 1, (
        "Expected at least one abstract contract (Ownable, Pausable) in multi_inheritance.sol"
    )


# ── 4. Import resolution handles OpenZeppelin paths ──────────────────────────

def test_imports_extracted():
    """Import statements must be extracted from safe_erc20.sol."""
    contracts = parser.parse_file(contract_path("safe_erc20.sol"))
    c = contracts[0]
    assert len(c.imports) >= 1, "Expected at least one import in safe_erc20.sol"


def test_openzeppelin_imports_listed():
    """safe_erc20.sol uses @openzeppelin imports — they should appear in imports list."""
    contracts = parser.parse_file(contract_path("safe_erc20.sol"))
    c = contracts[0]
    oz_imports = [i for i in c.imports if "@openzeppelin" in i]
    assert len(oz_imports) >= 1, (
        f"Expected @openzeppelin imports; got: {c.imports}"
    )


def test_resolve_imports_skips_remote():
    """resolve_imports should leave @openzeppelin imports unchanged (not inline them)."""
    source = 'import "@openzeppelin/contracts/token/ERC20/ERC20.sol";'
    result = parser.resolve_imports(source, base_path="/some/dir")
    assert "@openzeppelin" in result, (
        "Remote @openzeppelin import should not be modified by resolve_imports"
    )


# ── 5. Complex DeFi contract parses without errors ────────────────────────────

def test_defi_vault_parses():
    """Complex DeFi vault with governance and share token must parse cleanly."""
    contracts = parser.parse_file(contract_path("defi_vault.sol"))
    names = {c.name for c in contracts}
    assert "DeFiVault" in names, f"DeFiVault not parsed; found: {names}"


def test_defi_vault_contracts_count():
    """defi_vault.sol defines multiple contracts; all should be extracted."""
    contracts = parser.parse_file(contract_path("defi_vault.sol"))
    assert len(contracts) >= 3, (
        f"Expected at least 3 contracts (TimelockGovernance, VaultShares, DeFiVault), "
        f"got {len(contracts)}: {[c.name for c in contracts]}"
    )


def test_defi_vault_functions():
    """DeFiVault must expose deposit, withdraw, harvest, pricePerShare."""
    contracts = parser.parse_file(contract_path("defi_vault.sol"))
    vault = next((c for c in contracts if c.name == "DeFiVault"), None)
    assert vault is not None, "DeFiVault not found"
    names = fn_names(vault)
    for expected in ("deposit", "withdraw", "harvest", "pricePerShare"):
        assert expected in names, f"Expected function '{expected}' in DeFiVault, got: {names}"


def test_defi_vault_modifiers():
    """DeFiVault defines notPaused and validStrategy modifiers."""
    contracts = parser.parse_file(contract_path("defi_vault.sol"))
    vault = next((c for c in contracts if c.name == "DeFiVault"), None)
    assert vault is not None, "DeFiVault not found"
    mod_names = [m.name for m in vault.modifiers]
    assert "notPaused" in mod_names, f"Expected notPaused modifier, got: {mod_names}"


def test_defi_vault_events():
    """DeFiVault must have events: Deposited, Withdrawn, Harvested."""
    contracts = parser.parse_file(contract_path("defi_vault.sol"))
    vault = next((c for c in contracts if c.name == "DeFiVault"), None)
    assert vault is not None, "DeFiVault not found"
    event_names = [e.name for e in vault.events]
    for expected in ("Deposited", "Withdrawn", "Harvested"):
        assert expected in event_names, f"Expected event '{expected}', got: {event_names}"


# ── 6. Vulnerability contract parsing ─────────────────────────────────────────

def test_reentrancy_contract_parses():
    """VulnerableBank withdraw function should be extracted."""
    contracts = parser.parse_file(contract_path("vulnerable_reentrancy.sol"))
    bank = next((c for c in contracts if c.name == "VulnerableBank"), None)
    assert bank is not None, "VulnerableBank not found"
    names = fn_names(bank)
    assert "withdraw" in names, f"Expected 'withdraw' in VulnerableBank, got: {names}"


def test_overflow_contract_pre_080():
    """VulnerableOverflow uses pragma ^0.6.x — is_pre_080() should return True."""
    contracts = parser.parse_file(contract_path("vulnerable_overflow.sol"))
    vuln = next((c for c in contracts if c.name == "VulnerableOverflow"), None)
    assert vuln is not None, "VulnerableOverflow not found"
    assert vuln.is_pre_080(), (
        f"Expected is_pre_080()=True for {vuln.compiler_version}"
    )


# ── 7. Function visibility / mutability extraction ───────────────────────────

def test_function_visibility_extracted():
    """Functions should have visibility correctly set (public/external/internal/private)."""
    source = """
    pragma solidity ^0.8.0;
    contract TestVis {
        function pubFn() public {}
        function extFn() external {}
        function intFn() internal {}
        function privFn() private {}
    }
    """
    contracts = parser.parse(source)
    assert contracts, "No contracts parsed"
    c = contracts[0]
    vis_map = {f.name: f.visibility for f in c.functions}
    assert vis_map.get("pubFn") == "public", f"pubFn visibility: {vis_map.get('pubFn')}"
    assert vis_map.get("extFn") == "external", f"extFn visibility: {vis_map.get('extFn')}"
    assert vis_map.get("intFn") == "internal", f"intFn visibility: {vis_map.get('intFn')}"
    assert vis_map.get("privFn") == "private", f"privFn visibility: {vis_map.get('privFn')}"


def test_function_mutability_extracted():
    """View and pure functions should have mutability correctly set."""
    source = """
    pragma solidity ^0.8.0;
    contract TestMut {
        function viewFn() public view returns (uint256) { return 1; }
        function pureFn() public pure returns (uint256) { return 2; }
        function payFn() public payable {}
        function stateFn() public {}
    }
    """
    contracts = parser.parse(source)
    c = contracts[0]
    mut_map = {f.name: f.mutability for f in c.functions}
    assert mut_map.get("viewFn") == "view", f"viewFn mutability: {mut_map.get('viewFn')}"
    assert mut_map.get("pureFn") == "pure", f"pureFn mutability: {mut_map.get('pureFn')}"
    assert mut_map.get("payFn") == "payable", f"payFn mutability: {mut_map.get('payFn')}"
    assert mut_map.get("stateFn") == "nonpayable", f"stateFn mutability: {mut_map.get('stateFn')}"


def test_constructor_flagged():
    """Constructor should be detected and flagged as is_constructor=True."""
    source = """
    pragma solidity ^0.8.0;
    contract WithCtor {
        address public owner;
        constructor() { owner = msg.sender; }
    }
    """
    contracts = parser.parse(source)
    c = contracts[0]
    ctors = [f for f in c.functions if f.is_constructor]
    assert len(ctors) == 1, f"Expected 1 constructor, got: {len(ctors)}"


# ── 8. file_path set when parsing via parse_file ─────────────────────────────

def test_file_path_set():
    """parse_file should set file_path on each returned Contract."""
    path = contract_path("safe_erc20.sol")
    contracts = parser.parse_file(path)
    for c in contracts:
        assert c.file_path == path, f"Expected file_path={path}, got {c.file_path}"

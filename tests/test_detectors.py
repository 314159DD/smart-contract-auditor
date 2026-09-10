"""Tests for static vulnerability detectors."""

import sys
import os

# Allow running from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parser.models import Contract, Function, StateVariable
from src.detectors.runner import DetectorRunner, default_runner
from src.detectors.base import Vulnerability


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_contract(
    name: str = "Test",
    compiler_version: str = "^0.8.0",
    functions: list[Function] | None = None,
    source: str = "",
) -> Contract:
    return Contract(
        name=name,
        source=source,
        compiler_version=compiler_version,
        functions=functions or [],
    )


def make_fn(
    name: str,
    visibility: str = "public",
    mutability: str = "nonpayable",
    body: str = "",
    modifiers: list[str] | None = None,
) -> Function:
    return Function(
        name=name,
        visibility=visibility,
        mutability=mutability,
        body_source=body,
        modifiers=modifiers or [],
    )


# ── Reentrancy ────────────────────────────────────────────────────────────────

def test_reentrancy_classic():
    """External call before state update should be CRITICAL."""
    body = """
        require(balances[msg.sender] >= amount);
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
        balances[msg.sender] -= amount;  // state change AFTER call
    """
    contract = make_contract(functions=[make_fn("withdraw", body=body)])
    runner = default_runner()
    findings = runner.run_detector("reentrancy", contract)
    assert any(v.severity == "CRITICAL" for v in findings), \
        "Classic reentrancy not detected"


def test_reentrancy_safe_cei_pattern():
    """State update before external call — should NOT trigger."""
    body = """
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;  // state change BEFORE call
        (bool ok,) = msg.sender.call{value: amount}("");
        require(ok);
    """
    contract = make_contract(functions=[make_fn("withdraw", body=body)])
    runner = default_runner()
    findings = runner.run_detector("reentrancy", contract)
    critical = [v for v in findings if v.severity == "CRITICAL"]
    assert not critical, "False positive: CEI pattern flagged as reentrancy"


# ── Access Control ────────────────────────────────────────────────────────────

def test_access_control_unprotected_mint():
    """Public state-changing function with no modifier should be HIGH."""
    contract = make_contract(functions=[
        make_fn("mint", visibility="public", mutability="nonpayable",
                body="balances[to] += amount;")
    ])
    runner = default_runner()
    findings = runner.run_detector("access_control", contract)
    assert any(v.severity == "HIGH" for v in findings), \
        "Unprotected mint not flagged"


def test_access_control_protected():
    """Function with onlyOwner should NOT be flagged."""
    contract = make_contract(functions=[
        make_fn("mint", visibility="public", mutability="nonpayable",
                body="balances[to] += amount;", modifiers=["onlyOwner"])
    ])
    runner = default_runner()
    findings = runner.run_detector("access_control", contract)
    high = [v for v in findings if v.severity == "HIGH"]
    assert not high, "False positive: onlyOwner function flagged"


def test_access_control_unprotected_initialize():
    """Unprotected initialize() should be CRITICAL."""
    contract = make_contract(functions=[
        make_fn("initialize", visibility="public", mutability="nonpayable",
                body="owner = msg.sender;")
    ])
    runner = default_runner()
    findings = runner.run_detector("access_control", contract)
    assert any(v.severity == "CRITICAL" for v in findings), \
        "Unprotected initialize() not flagged as CRITICAL"


# ── Overflow ──────────────────────────────────────────────────────────────────

def test_overflow_pre_080():
    """Pre-0.8.0 arithmetic should be HIGH."""
    contract = make_contract(
        compiler_version="0.6.12",
        functions=[make_fn("transfer", body="balances[from] -= amount; balances[to] += amount;")]
    )
    runner = default_runner()
    findings = runner.run_detector("overflow", contract)
    assert any(v.severity == "HIGH" for v in findings), \
        "Pre-0.8.0 overflow not detected"


def test_overflow_post_080_clean():
    """Post-0.8.0 without unchecked block should NOT be flagged."""
    contract = make_contract(
        compiler_version="^0.8.20",
        functions=[make_fn("transfer", body="balances[from] -= amount; balances[to] += amount;")]
    )
    runner = default_runner()
    findings = runner.run_detector("overflow", contract)
    assert not findings, "False positive: 0.8+ arithmetic flagged without unchecked"


def test_overflow_post_080_unchecked():
    """Post-0.8.0 with unchecked block should be LOW."""
    body = "unchecked { counter++; }"
    contract = make_contract(
        compiler_version="0.8.20",
        functions=[make_fn("inc", body=body)]
    )
    runner = default_runner()
    findings = runner.run_detector("overflow", contract)
    assert any(v.severity == "LOW" for v in findings), \
        "Unchecked block with arithmetic not flagged"


# ── tx.origin ─────────────────────────────────────────────────────────────────

def test_tx_origin_auth():
    body = "require(tx.origin == owner, 'not owner');"
    contract = make_contract(functions=[make_fn("withdraw", body=body)])
    runner = default_runner()
    findings = runner.run_detector("tx_origin", contract)
    assert findings, "tx.origin auth not detected"


# ── selfdestruct ──────────────────────────────────────────────────────────────

def test_selfdestruct_unprotected():
    body = "selfdestruct(payable(msg.sender));"
    contract = make_contract(functions=[make_fn("destroy", body=body)])
    runner = default_runner()
    findings = runner.run_detector("selfdestruct", contract)
    assert any(v.severity == "CRITICAL" for v in findings), \
        "Unprotected selfdestruct not flagged"


# ── delegatecall ──────────────────────────────────────────────────────────────

def test_delegatecall_unprotected():
    body = "(bool ok,) = impl.delegatecall(data); require(ok);"
    contract = make_contract(functions=[make_fn("proxy", body=body)])
    runner = default_runner()
    findings = runner.run_detector("delegatecall", contract)
    assert any(v.severity == "CRITICAL" for v in findings), \
        "Unprotected delegatecall not flagged"


# ── timestamp ─────────────────────────────────────────────────────────────────

def test_timestamp_randomness():
    body = "uint256 rand = uint256(keccak256(abi.encodePacked(block.timestamp)));"
    contract = make_contract(functions=[make_fn("pickWinner", body=body)])
    runner = default_runner()
    findings = runner.run_detector("timestamp", contract)
    assert any(v.severity == "HIGH" for v in findings), \
        "Timestamp-based randomness not flagged"


# ── gas limit ─────────────────────────────────────────────────────────────────

def test_gas_limit_unbounded_loop():
    body = "for (uint i = 0; i < recipients.length; i++) { payable(recipients[i]).transfer(1); }"
    contract = make_contract(functions=[make_fn("distribute", body=body)])
    runner = default_runner()
    findings = runner.run_detector("gas_limit", contract)
    assert findings, "Unbounded loop not detected"


# ── front_running ─────────────────────────────────────────────────────────────

def test_front_running_approve_without_increase_allowance():
    """ERC-20 approve() without increaseAllowance should be MEDIUM."""
    contract = make_contract(
        source="contract T { function approve(address s, uint a) public {} }",
        functions=[make_fn("approve", body="allowance[msg.sender][spender] = amount;")]
    )
    runner = default_runner()
    findings = runner.run_detector("front_running", contract)
    assert any(v.severity == "MEDIUM" for v in findings), \
        "approve() without increaseAllowance not flagged"


def test_front_running_swap_without_slippage():
    """Swap function without slippage params should be HIGH."""
    contract = make_contract(
        functions=[make_fn("swapTokens", body="uint out = pool.swap(tokenIn, amountIn);")]
    )
    runner = default_runner()
    findings = runner.run_detector("front_running", contract)
    assert any(v.severity == "HIGH" for v in findings), \
        "Swap without slippage protection not flagged"


def test_front_running_oracle_without_twap():
    """Spot price oracle read without TWAP should be MEDIUM."""
    contract = make_contract(
        functions=[make_fn("getCollateralValue", body="uint price = oracle.latestAnswer();")]
    )
    runner = default_runner()
    findings = runner.run_detector("front_running", contract)
    assert any(v.severity == "MEDIUM" for v in findings), \
        "Spot oracle read without TWAP not flagged"


def test_front_running_swap_with_slippage_safe():
    """Swap with amountOutMin should NOT be flagged for slippage."""
    contract = make_contract(
        functions=[make_fn("swapTokens",
                           body="require(out >= amountOutMin); uint out = pool.swap(tokenIn, amountIn);")]
    )
    runner = default_runner()
    findings = runner.run_detector("front_running", contract)
    slippage_findings = [v for v in findings if "slippage" in v.title.lower()]
    assert not slippage_findings, "False positive: swap with amountOutMin flagged"


# ── unchecked_call ─────────────────────────────────────────────────────────────

def test_unchecked_call_ignored_return():
    """Low-level .call() with ignored return value should be MEDIUM."""
    body = 'to.call{value: amount}("");'
    contract = make_contract(functions=[make_fn("sendPayment", body=body)])
    runner = default_runner()
    findings = runner.run_detector("unchecked_call", contract)
    assert any(v.severity == "MEDIUM" for v in findings), \
        "Unchecked .call() return value not flagged"


def test_unchecked_call_checked_return():
    """Low-level .call() with captured return value should NOT be flagged."""
    body = '(bool ok,) = to.call{value: amount}(""); require(ok, "failed");'
    contract = make_contract(functions=[make_fn("sendPayment", body=body)])
    runner = default_runner()
    findings = runner.run_detector("unchecked_call", contract)
    assert not findings, "False positive: captured .call() flagged as unchecked"


# ── DetectorRunner integration ────────────────────────────────────────────────

def test_runner_run_all():
    """run_all should aggregate findings from all detectors."""
    body_reentrancy = """
        (bool ok,) = msg.sender.call{value: amount}("");
        balances[msg.sender] -= amount;
    """
    contract = make_contract(functions=[
        make_fn("withdraw", body=body_reentrancy),
        make_fn("initialize", body="owner = msg.sender;"),
    ])
    runner = default_runner()
    findings = runner.run_all(contract)
    assert len(findings) > 0, "run_all returned no findings"
    severities = {v.severity for v in findings}
    assert "CRITICAL" in severities, "Expected at least one CRITICAL finding"


def test_runner_unknown_detector():
    """run_detector with unknown name should raise KeyError."""
    runner = default_runner()
    contract = make_contract()
    try:
        runner.run_detector("nonexistent", contract)
        assert False, "Expected KeyError"
    except KeyError:
        pass


def test_all_findings_fully_populated():
    """Every Vulnerability returned must have all required fields non-empty."""
    bodies = {
        "withdraw": "(bool ok,) = msg.sender.call{value:1}(''); balances[msg.sender]=0;",
        "mint": "totalSupply += amount;",
        "initialize": "owner = msg.sender;",
    }
    functions = [make_fn(name, body=body) for name, body in bodies.items()]
    contract = make_contract(functions=functions, compiler_version="0.6.12")

    runner = default_runner()
    findings = runner.run_all(contract)
    for v in findings:
        assert v.detector, f"Empty detector in {v}"
        assert v.severity, f"Empty severity in {v}"
        assert v.title, f"Empty title in {v}"
        assert v.description, f"Empty description in {v}"
        assert v.location, f"Empty location in {v}"
        assert v.recommendation, f"Empty recommendation in {v}"
        assert v.confidence, f"Empty confidence in {v}"


if __name__ == "__main__":
    tests = [
        test_reentrancy_classic,
        test_reentrancy_safe_cei_pattern,
        test_access_control_unprotected_mint,
        test_access_control_protected,
        test_access_control_unprotected_initialize,
        test_overflow_pre_080,
        test_overflow_post_080_clean,
        test_overflow_post_080_unchecked,
        test_tx_origin_auth,
        test_selfdestruct_unprotected,
        test_delegatecall_unprotected,
        test_timestamp_randomness,
        test_gas_limit_unbounded_loop,
        test_runner_run_all,
        test_runner_unknown_detector,
        test_all_findings_fully_populated,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")

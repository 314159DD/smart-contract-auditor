// SPDX-License-Identifier: MIT
pragma solidity ^0.6.12;

/// @title Integer overflow/underflow (pre-0.8.0)
/// @dev VULNERABLE — for testing only. DO NOT DEPLOY.
contract VulnerableOverflow {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        // ❌ No SafeMath — can overflow in 0.6.x
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        // ❌ Underflow: if balances[msg.sender] == 0, result wraps to 2^256-1
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
    }

    function transfer(address to, uint256 amount) external {
        // ❌ Both operations unprotected
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}

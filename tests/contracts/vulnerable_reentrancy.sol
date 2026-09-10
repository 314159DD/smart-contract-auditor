// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Classic reentrancy vulnerability (The DAO pattern)
/// @dev VULNERABLE — for testing only. DO NOT DEPLOY.
contract VulnerableBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    /// @dev VULNERABLE: external call happens before state update
    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "Insufficient balance");

        // ❌ External call BEFORE state change — classic reentrancy
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // State update happens after the external call — too late!
        balances[msg.sender] -= amount;
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}

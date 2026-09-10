// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Miscellaneous vulnerability examples
/// @dev VULNERABLE — for testing only. DO NOT DEPLOY.
contract VulnerableMisc {
    address public owner;
    address[] public recipients;

    constructor() {
        owner = msg.sender;
    }

    // ── tx.origin ──────────────────────────────────────────────────────────────
    /// @dev VULNERABLE: uses tx.origin instead of msg.sender
    function withdrawTxOrigin() external {
        require(tx.origin == owner, "Not owner");
        (bool ok, ) = msg.sender.call{value: address(this).balance}("");
        require(ok, "Failed");
    }

    // ── selfdestruct ───────────────────────────────────────────────────────────
    /// @dev VULNERABLE: unprotected selfdestruct
    function destroy(address payable target) external {
        selfdestruct(target);
    }

    // ── delegatecall ───────────────────────────────────────────────────────────
    /// @dev VULNERABLE: unprotected delegatecall to user-supplied address
    function proxyCall(address impl, bytes calldata data) external {
        (bool ok, ) = impl.delegatecall(data);
        require(ok, "Delegatecall failed");
    }

    // ── timestamp ─────────────────────────────────────────────────────────────
    /// @dev VULNERABLE: randomness from block.timestamp
    function pickWinner(address[] calldata players) external view returns (address) {
        uint256 rand = uint256(keccak256(abi.encodePacked(block.timestamp, block.difficulty)));
        return players[rand % players.length];
    }

    // ── gas limit / DoS ───────────────────────────────────────────────────────
    /// @dev VULNERABLE: unbounded loop over dynamic array
    function distributeRewards(uint256 amount) external {
        for (uint256 i = 0; i < recipients.length; i++) {
            payable(recipients[i]).transfer(amount);
        }
    }

    function addRecipient(address r) external {
        recipients.push(r);
    }

    // ── unchecked call return ─────────────────────────────────────────────────
    /// @dev VULNERABLE: ignores return value of .call()
    function sendPayment(address to, uint256 amount) external {
        to.call{value: amount}("");   // return value silently discarded
    }

    receive() external payable {}
}

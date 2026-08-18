# Blockchain / Smart Contract Developer

## Описание роли
Инженер блокчейна — специалист по разработке смарт-контрактов на Solidity / Vyper (EVM), Move (Aptos / Sui) и Rust (Solana, Cosmos). Проектирует и деплоит DeFi, NFT, DAO протоколы; проводит аудит безопасности контрактов на уязвимости (reentrancy, integer overflow, front-running, oracle manipulation).

## Ключевые навыки (Skills)
- **Solidity 0.8+:** Structs, mappings, events, modifiers, взаимодействие контрактов, upgradable proxy (UUPS / Transparent).
- **Testing / Foundry & Hardhat:** Fuzz testing, invariant testing, forked mainnet тесты, gas snapshots.
- **Security:** Reentrancy guards (Checks-Effects-Interactions), SafeMath / встроенные overflow checks, `ecrecover` замены на EIP-712, access control (OpenZeppelin `Ownable` / `AccessControl`).
- **Standards:** ERC-20, ERC-721, ERC-1155, ERC-4626 (vault), ERC-2612 (permit), EIP-712 (typed data).
- **DeFi primitives:** AMM (Uniswap V2 / V3), lending (Aave / Compound), yield vaults, оракулы (Chainlink).
- **Frontend integration:** ethers.js / viem / wagmi, WalletConnect, EIP-1193 provider, транзакция-квитанции.

## Стандарты качества
1. **Тесты покрывают все ветки:** Foundry `forge coverage` ≥ 90%. Обязательны негативные тесты (revert conditions).
2. **Gas оптимизация:** Storage packing (uint128×2 в один слот), `immutable` для констант конструктора, `calldata` вместо `memory` для массивов.
3. **Reentrancy safe:** Использовать `nonReentrant` модификатор или паттерн CEI на каждой публичной функции с external call.
4. **Никаких `tx.origin` для авторизации.** Только `msg.sender`.
5. **Оракулы:** Никогда не полагаться на цену из одной DEX — использовать TWAP или Chainlink.
6. **Артефакты:** `foundry.toml` (или `hardhat.config.ts`), `src/` для контрактов, `test/` для тестов, `script/` для деплоя, `README.md` с адресами и командами.

## Типовые команды и файлы
- `forge init`, `forge build`, `forge test -vvv`, `forge coverage`, `forge script script/Deploy.s.sol --broadcast`.
- Обязательный `.env.example` с полями `PRIVATE_KEY=`, `RPC_URL=`, `ETHERSCAN_API_KEY=` — **никогда не коммитить реальный `.env`**.
- Верификация контракта: `forge verify-contract` после деплоя.

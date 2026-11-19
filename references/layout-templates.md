# 目录模板与代码骨架

## 目录

- [三种分包方式对照](#三种分包方式对照)
- [Python](#python)
- [TypeScript](#typescript)
- [Go](#go)
- [Java](#java)
- [最小代码骨架](#最小代码骨架)
- [常见变体](#常见变体)

## 三种分包方式对照

同一套业务：转账、冻结账户、查询余额、积分、优惠券、通知。

### A. 按层分包（不推荐）

```text
src/
├── domain/
│   ├── account.py
│   ├── points.py
│   ├── coupon.py
│   └── notification.py
├── application/
│   ├── send_money.py
│   ├── freeze_account.py
│   ├── grant_points.py
│   └── issue_coupon.py
└── adapters/
    ├── sql_account_repository.py
    ├── sql_points_repository.py
    └── web_api.py
```

- 症状：加「冻结账户」要改 `domain/`、`application/`、`adapters/` 三处，业务被拆散。
- 规模变大后：所有模型堆在 `domain/`，改账户要在积分/优惠券/通知的文件里翻找。

### B. 按用例分包 / 一功能一包（不推荐）

```text
src/
├── send_money/
│   └── everything：model + use case + repository + api
├── freeze_account/
│   └── everything：model + use case + repository + api
```

- 症状：转账与冻结都用 `Account`，两份模型改一处漏一处；或 `freeze_account` 引用 `send_money` 的模型，平级包出现奇怪依赖。
- 同样问题出现在适配层：两个包读写的是同一个数据库。

### C. 内外分离 + 按共享模型聚合（推荐）

```text
src/
├── account/                     # 共用 Account / AccountRepository 的用例 → 一个模块
│   ├── domain/account.py
│   ├── application/{ports,send_money,freeze_account,query_balance}.py
│   └── adapters/{persistence,web}/
├── points/                      # 独立模型 → 独立模块
│   └── domain/ application/ adapters/
├── coupon/
│   └── domain/ application/ adapters/
├── notification/
│   └── domain/ application/ adapters/
└── shared/                      # 跨模块技术设施，无业务规则
```

- 内部 = `domain` + `application`（因系统自身变化）
- 外部 = `adapters`（因环境变化）
- 新增功能必然同时动业务与技术，但**全部落在同一个模块目录内**。

## Python

```text
project/
├── src/
│   └── app/
│       ├── account/
│       │   ├── domain/
│       │   │   ├── account.py            # 实体 + 规则
│       │   │   └── errors.py             # 领域异常
│       │   ├── application/
│       │   │   ├── ports.py              # Protocol/ABC：AccountRepository
│       │   │   ├── send_money.py
│       │   │   └── freeze_account.py
│       │   └── adapters/
│       │       ├── persistence/
│       │       │   └── sql_account_repository.py
│       │       └── web/
│       │           └── routes.py
│       ├── points/
│       ├── coupon/
│       ├── notification/
│       └── shared/
│           ├── db.py                     # 连接/会话工厂（无业务）
│           ├── clock.py
│           └── logging.py
├── tests/
│   ├── account/
│   │   ├── domain/                       # 纯单测，不起数据库
│   │   └── application/                  # 用假仓储
│   └── ...
└── pyproject.toml
```

约定：
- `domain/` 内禁止 `import sqlalchemy / fastapi / requests`，可用 import-linter 或 ruff TID 规则强制。
- 端口接口用 `typing.Protocol` 或 `abc.ABC`，放在 `application/ports.py`。
- 测试目录镜像源码模块，`domain` 测试不需要任何外部依赖。
- 依赖方向：`adapters → application → domain`，反向 import 一律视为错误。

## TypeScript

```text
src/
├── account/
│   ├── domain/
│   │   ├── account.ts                   # 类/纯函数 + 不变量
│   │   └── errors.ts
│   ├── application/
│   │   ├── ports.ts                     # interface AccountRepository
│   │   ├── send-money.ts                # use case（工厂函数或类）
│   │   └── freeze-account.ts
│   ├── adapters/
│   │   ├── persistence/
│   │   │   └── prisma-account.repository.ts
│   │   └── http/
│   │       └── account.controller.ts
│   └── index.ts                         # 模块对外导出面（composition root 由此组装）
├── points/ coupon/ notification/
├── shared/
│   ├── prisma.ts
│   └── logger.ts
└── main.ts                              # 唯一组装线：把 adapter 注入 use case
```

约定：
- `domain/` 不 import `@nestjs/*`、`prisma`、`express`。
- use case 通过构造函数/参数接收端口，`main.ts` 是唯一注入点。
- 用 ESLint `no-restricted-imports` 或 `dependency-cruiser` 守边界。

## Go

```text
internal/
├── account/
│   ├── domain/
│   │   ├── account.go                   # struct + 方法 + 领域错误
│   │   └── repository.go                # 端口接口（Go 习惯放在 domain，同样属于「内部声明」）
│   ├── app/
│   │   ├── send_money.go                # use case + 输入输出 DTO
│   │   └── freeze_account.go
│   └── infra/
│       ├── postgres_account_repo.go
│       └── http_handler.go
├── points/ coupon/ notification/
└── pkg/                                 # 跨模块技术设施
cmd/
└── api/main.go                          # 组装
```

约定：
- Go 里端口接口放 `domain/` 或 `app/ports` 都可以，关键约束是**接口不与实现同包**，且 `domain` 不 import `infra`。
- `internal/` 前缀阻止外部包直接引用，天然强制边界。

## Java

```text
src/main/java/com/example/
├── account/
│   ├── domain/
│   │   ├── Account.java
│   │   └── AccountRepository.java       # 端口接口（六边形架构常用位置）
│   ├── application/
│   │   ├── SendMoneyUseCase.java
│   │   └── FreezeAccountUseCase.java
│   └── adapter/
│       ├── out/persistence/JpaAccountRepository.java
│       └── in/web/AccountController.java
├── points/ coupon/ notification/
└── shared/
```

约定：
- 或用 Maven/Gradle 多模块把每个业务模块做成独立 module，边界由构建强制。
- Spring 的 `@Service` / `@Repository` 只出现在 adapter / 组装层，domain 不依赖注解。

## 最小代码骨架

### domain/account.py

```python
from dataclasses import dataclass
from decimal import Decimal

class AccountFrozen(Exception): ...

@dataclass
class Account:
    id: str
    balance: Decimal
    status: str                 # "active" | "frozen"

    def withdraw(self, amount: Decimal) -> None:
        self._guard()
        if amount <= 0 or amount > self.balance:
            raise ValueError("invalid amount")
        self.balance -= amount

    def deposit(self, amount: Decimal) -> None:
        self._guard()
        self.balance += amount

    def freeze(self) -> None:
        self.status = "frozen"

    def _guard(self) -> None:
        if self.status == "frozen":
            raise AccountFrozen("account is frozen")
```

### application/ports.py

```python
from typing import Protocol
from ..domain.account import Account

class AccountRepository(Protocol):
    def get(self, account_id: str) -> Account: ...
    def save(self, account: Account) -> None: ...
```

### application/send_money.py

```python
from decimal import Decimal
from .ports import AccountRepository

class SendMoney:
    def __init__(self, repo: AccountRepository) -> None:
        self._repo = repo

    def execute(self, src_id: str, dst_id: str, amount: Decimal) -> None:
        src = self._repo.get(src_id)
        dst = self._repo.get(dst_id)
        src.withdraw(amount)
        dst.deposit(amount)
        self._repo.save(src)
        self._repo.save(dst)          # 事务边界在这一层，由 adapter 实现
```

### adapters/persistence/sql_account_repository.py

```python
from ...domain.account import Account
from ...application.ports import AccountRepository

class SqlAccountRepository(AccountRepository):
    def __init__(self, session) -> None:
        self._session = session

    def get(self, account_id: str) -> Account:
        row = self._session.get("accounts", account_id)
        return Account(id=row["id"], balance=row["balance"], status=row["status"])

    def save(self, account: Account) -> None:
        self._session.execute(
            "UPDATE accounts SET balance=?, status=? WHERE id=?",
            (account.balance, account.status, account.id),
        )
```

### adapters/web/api.py

```python
@router.post("/transfers")
def transfer(body: TransferRequest):
    case = SendMoney(SqlAccountRepository(session_factory()))
    case.execute(body.src, body.dst, body.amount)   # 组装线也可上移到 composition root
    return {"ok": True}
```

## 常见变体

| 变体 | 什么时候用 | 注意 |
|---|---|---|
| adapters 上提到顶层（`src/adapters/<module>/`） | 适配器由独立团队/独立部署维护，或统一走一个网关 | 每层目录内按模块再分一层，仍能回答「改哪里」 |
| 端口接口放 domain | Go / 六边形架构习惯 | 接口不能和实现同包，domain 不能 import 实现 |
| 单独 `shared/` | 出现第二个模块使用同一技术设施时 | 只放技术，不放业务规则；一旦出现业务判断就该下沉到某模块 domain |
| 单模块小项目 | 只有一个业务、一两个人维护 | 可以只建一个模块目录，但用例仍要一个文件一个 |
| 多模块独立构建（Java/Go workspace） | 边界需要工具强制 | 构建期依赖即架构约束，比口头约定可靠 |

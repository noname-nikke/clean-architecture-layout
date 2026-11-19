---
name: clean-architecture-layout
description: 设计与评审「整洁架构」的项目目录结构（包结构）。先按用例梳理领域/应用/适配三职责，再把系统分成「因外部变化」和「因系统自身变化」两部分，并按「共用同一领域模型与端口接口」把用例聚成业务模块，产出能直接回答「改哪里」的目录树。适用于：新项目开工前定目录、决定新文件该放哪个包、review 现有目录是按层分包还是按用例分包、把大杂烩/分层项目重构成模块化结构、回答「业务规则在哪 / 对外有哪些用例 / 换存储改哪里」等结构问题。触发词：目录结构、包结构、分包、分层架构、六边形架构、整洁架构、use case、依赖倒置、ports and adapters、项目重构、代码放哪、package by layer。
---

# 整洁架构目录结构

目录不是「把文件摆整齐」，而是把**会因外部环境变化的东西**和**会因系统自身变化的东西**分开，再按**共享的模型与接口**把用例聚成模块。目标：看目录就能回答「改哪里」。

## 一句话判据

同一个改动，如果需要**跨目录来回跳**、或**同一份规则要改两处**、或**不敢确定改哪个同名文件**——结构错了，不是框架错了。

## 三步决策

### 1. 先列用例，不先列目录

用例 = 系统对外提供的一个完整动作，一个动作一个 use case：
`SendMoney`、`FreezeAccount`、`QueryBalance`、`GrantPoints`、`IssueCoupon`。
不要从「我要建几个包」开始，从「系统对外承诺了哪些动作」开始。

### 2. 每个用例拆三个职责

| 层 | 负责什么 | 判定问题 | 转账例子 |
|---|---|---|---|
| 领域 domain | 内部概念、数据、不变量与规则，只用自身语言 | 「什么是一个账户？什么情况下允许？」 | `Account`：余额 + 状态；正常可转、冻结不可转；转出扣款、转入入账 |
| 应用 application | 编排流程（取数→用规则→写回）、声明端口接口 | 「一次完整动作的步骤是什么？需要外部提供什么能力？」 | `SendMoneyUseCase` 编排；`AccountRepository` 接口约定如何读写 |
| 适配 adapters | 具体的外部技术实现 | 「用的是哪个库、哪种协议、哪种请求格式？」 | `SqlAccountRepository`／`PgAccountRepository` 实现接口；`WebApi` 接收请求调用例 |

**依赖倒置**：端口接口（Repository/Gateway/Publisher）声明在**应用层**，实现在**适配层**。接口与实现分离后，换数据库只改适配层。

### 3. 分内外，再按共享模型聚合

- **内部** = 因系统自身变化（新增用例、改业务规则）→ `domain` + `application`
- **外部** = 因环境变化（换库、换请求格式、换消息中间件）→ `adapters`
- **聚合规则**：**共用同一领域模型和端口接口的用例，放进同一个业务模块包**。
  - 转账与冻结共用 `Account` / `AccountRepository` → 同一个 `account` 模块
  - 积分、优惠券、通知各有独立模型 → 各自独立模块

结论：新增一个完整功能，**必然**同时改业务和技术两处。这不叫耦合。区别在于——按层分包把「业务自己」拆散在多个目录里；内外分离让**所有属于同一业务的文件待在一个目录里**。

## 文件该放哪（判定表）

按顺序问，命中即停：

| 这个文件是… | 放这里 | 说明 |
|---|---|---|
| 实体、值对象、业务规则、不变量 | `<module>/domain/` | 不 import 框架、ORM、HTTP |
| 一次动作的编排、事务边界、补偿 | `<module>/application/<use_case>.py` | 一个用例一个文件，文件名即用例名 |
| 端口接口（仓储/网关/发布者） | `<module>/application/ports.py` | 只定义「需要什么能力」，不写实现 |
| 端口实现（DB、HTTP 客户端、MQ、文件） | `<module>/adapters/` | 换技术只动这里 |
| 请求入口、控制器、DTO/序列化 | `<module>/adapters/web/` | 收请求 → 调 use case → 返回 |
| 跨模块共用的技术设施（日志、配置、时钟、ID 生成） | `src/shared/` 或 `src/platform/` | 不属于任何业务，也不含业务规则 |
| 说不清归谁的「工具函数」 | **先停下分类** | 含业务判断→domain；纯技术→shared；两边都不是→职责没想清，不要建 `utils.py` 兜底 |
| 和另一模块共用模型的动作 | **合并成一个模块**，不要跨包引用 | 平级业务包互相依赖对方领域模型 = 该共享的东西被拆开了 |

## 目录模板（最小可跑）

```text
src/
├── account/                       # 业务模块：共用同一 Account 模型的用例集合
│   ├── domain/
│   │   └── account.py             # 余额、状态、扣款/入账、冻结不可转
│   ├── application/
│   │   ├── ports.py               # AccountRepository（接口，依赖倒置的落点）
│   │   ├── send_money.py          # SendMoneyUseCase
│   │   └── freeze_account.py      # FreezeAccountUseCase
│   └── adapters/
│       ├── persistence/
│       │   └── sql_account_repository.py
│       └── web/
│           └── api.py             # 接请求、调用例、返回结果
├── points/                        # 独立模型 → 独立模块
│   ├── domain/ application/ adapters/
├── coupon/
│   └── domain/ application/ adapters/
├── notification/
│   └── domain/ application/ adapters/
└── shared/                        # 技术设施：日志、配置、时钟（无业务规则）
```

规模小、只有一个业务模块时，可先只建一个模块目录；技术设施出现第二个使用方时再抽出 `shared`。**不要**一开始就按「controller/service/repository/model」分层预铺空目录。

## 三个验收问题

不点开任何文件，只看目录树，能否回答：

1. 转账规则在哪？→ 在 `account/domain`
2. 系统对外提供了哪些用例？→ 各模块 `application/` 下的用例文件清单
3. 想换一种存储方式要改哪里？→ 该模块的 `adapters/`

三个问题里任何一个需要点开文件、全局搜索或问人才答得出，结构就不达标。

## 反模式与症状

| 症状 | 根因 | 改法 |
|---|---|---|
| 加一个冻结功能，要在 domain / application / adapters 三个顶层目录来回跳 | 按层分包（package by layer） | 改为按业务模块聚合，模块内保留三层 |
| 同一个 `Account` 出现两份，改一处漏一处 | 按用例分包（一个功能一个包） | 把共用模型的用例合并为一个模块 |
| 两个平级业务包互相 import 对方的领域模型 | 按用例分包导致的假平级 | 判定为共享模型 → 合并模块 |
| `db.py`、`db2.py`、`helper.py`、`tools.py`、`utils.py` 并存，没人知道该用哪个 | 文件没有所有权，新需求就新建一个文件 | 收敛到 `adapters/` 或 `shared/`，旧入口显式废弃 |
| 一个模块几十个文件，说不出它对外提供什么 | 包内没有按用例组织 | `application/` 一个用例一个文件，其余下沉到 domain/adapters |
| 只想改账户，却要在积分、优惠券、通知的文件里翻找 | 按层分包：所有模型堆在 domain | 按模块聚合，改账户只看 `account/` |

## 好维护的三个判据

每次改动后给这三条打分，低于预期就调整结构：

1. 能很快知道要改什么（定位成本）
2. 改的时候要读的上下文尽可能少（阅读成本）
3. 改动附带的连带修改很少甚至没有（波及成本）

## 重构既有项目

从大杂烩或按层分包迁到本结构时，按 [references/migration-playbook.md](references/migration-playbook.md) 的顺序做：先定模块边界 → 抽端口接口 → 移实现 → 收口重复工具 → 删旧入口。迁移期间保留单向依赖，不追求一次到位。

## 多语言目录树与代码骨架

Python、TypeScript、Go、Java 的具体目录树，以及 `Account` / `SendMoneyUseCase` / 端口实现的最小代码骨架、三种分包方式的完整对照：[references/layout-templates.md](references/layout-templates.md)。

## 结构体检脚本

```bash
python scripts/check_layout.py <项目根目录>
```

输出顶层目录归属、按层分包嫌疑、跨模块重复模型、疑似兜底工具目录，以及三个验收问题能否作答。仅作启发式诊断，最终判断用上面的判定表。

## 交付话术

给用户结论时，只讲三件事：**模块边界怎么切、某个文件放哪、改一处会影响哪些文件**。不要复述分层架构的定义。

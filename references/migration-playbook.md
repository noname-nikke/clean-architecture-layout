# 从现有项目迁到整洁目录结构

## 目录

- [迁移原则](#迁移原则)
- [0. 冻结新增](#0-冻结新增)
- [1. 列用例清单](#1-列用例清单)
- [2. 划定模块边界](#2-划定模块边界)
- [3. 抽领域模型](#3-抽领域模型)
- [4. 声明端口接口](#4-声明端口接口)
- [5. 移实现进 adapters](#5-移实现进-adapters)
- [6. 收口重复工具](#6-收口重复工具)
- [7. 切断旧入口](#7-切断旧入口)
- [8. 验收](#8-验收)
- [常见陷阱](#常见陷阱)

## 迁移原则

1. **单向推进**：每步只允许新增一层依赖，不允许出现环形依赖。
2. **可回滚**：每步单独提交，旧入口保留到验收通过，不一次性大改。
3. **不追求一次到位**：先让「同一业务的文件待在一起」，再修内部依赖方向。
4. **迁移期允许「假适配层」**：先包一层薄壳，再逐步换成真实现。

## 0. 冻结新增

在旧目录里新增文件之前先停下：新文件直接按目标结构建，不再往旧结构里加。否则迁移永远追不上新增速度。

## 1. 列用例清单

从路由/入口反推，逐个写出来：

```text
POST /transfers           → SendMoney
POST /accounts/{id}/freeze → FreezeAccount
GET  /accounts/{id}/balance→ QueryBalance
POST /points/grant        → GrantPoints
```

产物：一张「对外用例清单」，标上当前实现文件路径。这张表是后面所有切分的依据。

## 2. 划定模块边界

判定：**共用同一个领域模型或同一套存储接口的用例，归入同一个模块。**

```text
account 模块      ← SendMoney / FreezeAccount / QueryBalance（都用 Account + AccountRepository）
points 模块       ← GrantPoints（独立积分模型）
coupon 模块       ← IssueCoupon（独立优惠券模型）
notification 模块 ← SendNotification（独立通知模型）
```

两条反向判定：

- 两个包互相 import 对方的模型 → 说明是同一个模块，合并。
- 一个用例同时依赖两个模块的模型 → 通常说明有隐藏的共享概念（如「用户」「账户」），先把它抽成真正的领域模型，再决定归属。

## 3. 抽领域模型

把分散在各处的实体、校验、计算规则收进 `<module>/domain/`。

检查项：
- 规则是否只在 domain 里出现一次（不在 controller / repository / service 里重复判断）
- domain 是否还能被单独 import 而不拉起数据库、HTTP、框架
- 同一实体是否只有一个定义（删除 `db2`/`model_v2` 这类并行副本）

## 4. 声明端口接口

在 `<module>/application/ports.py` 声明「需要什么能力」，先不改调用方实现：

```python
class AccountRepository(Protocol):
    def get(self, account_id: str) -> Account: ...
    def save(self, account: Account) -> None: ...
```

对每个 store/gateway 都建一个端口。此时代码还能跑，只是多了一个接口层。

## 5. 移实现进 adapters

把旧的 repository / client / controller 移动到 `<module>/adapters/`，并改成实现端口。

- 事务边界写在 use case 里，或由 adapter 提供一个可注入的 `unit_of_work`。
- 换库时只新增一个 adapter 实现，旧实现保留，由 composition root 决定注入哪个。
- 每个 adapter 文件只对一组外部资源负责，避免「万能 db.py」。

## 6. 收口重复工具

扫描 `utils / helpers / tools / common / misc` 目录：

| 内容 | 去处 |
|---|---|
| 金额取整、折扣计算、状态流转判断 | 对应模块 `domain/`（含业务规则，不是工具） |
| 日期格式化、ID 生成、日志、重试 | `shared/`（纯技术，无业务） |
| 只有一个人用过、也说不清用途的 | 就地标记死代码，随所在模块一起收敛，不要留在兜底目录 |

规则：兜底目录清空后**删除目录本身**，否则新代码会继续往里扔。

## 7. 切断旧入口

旧路径（`old_service/`、`legacy/`、重复实现）在验收通过后：

1. 加弃用标记或从路由表摘掉
2. 观察一个发布周期
3. 再物理删除（遵循所在仓库的删除流程，不要在本机直接删）

迁移期间新代码只允许 import 新结构，旧结构不允许反向 import 新模块。

## 8. 验收

用三个问题验收，不点开文件：

1. 转账规则在哪 → `account/domain`
2. 对外提供了哪些用例 → 各模块 `application/` 用例文件
3. 换存储改哪里 → 对应模块 `adapters/`

再用三个成本判据打分：
- 定位成本：能否在 10 秒内找到要改的文件
- 阅读成本：一次改动平均要打开几个文件（跨模块 >3 视为不合格）
- 波及成本：一次改动平均牵动几个模块（>2 视为不合格）

## 常见陷阱

| 陷阱 | 表现 | 处理 |
|---|---|---|
| ORM 实体当领域模型 | `domain` 里带 `@Entity`、懒加载、会话 | 领域模型与持久化模型分离，adapter 负责映射 |
| 事务被切碎 | 两个 repository 各自提交，转账出现半成功 | 事务边界上移到 use case 或 `unit_of_work` |
| 模块间同步调用 | `account` 直接 import `points` 的用例 | 改为端口 + 事件，或判定为同模块 |
| 迁移与重构混在一起 | 一次提交同时改结构和改逻辑 | 结构提交与逻辑提交分开，便于回滚 |
| 目录改了但测试没动 | 测试仍在打旧路径 | 测试目录按模块镜像重建，domain 测试去掉外部依赖 |
| 「以后再拆」 | 旧的 utils 越堆越大 | 收口动作必须在迁移期内完成，不挂账 |

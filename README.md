# clean-architecture-layout

一个 agent skill（技能包）：用于**设计、评审、重构项目的目录结构（包结构）**。核心是「内外分离 + 按共享模型聚合用例」，产出能直接回答「改哪里」的目录树。

> 不解释分层架构是什么，只回答三件事：模块怎么切、这个文件放哪、改一处会波及什么。

## 安装

三种方式任选，装到任意一个 skills 根目录下的 `clean-architecture-layout/` 即可。

```powershell
# 1) git clone（推荐，方便后续更新）
git clone https://github.com/noname-nikke/clean-architecture-layout.git "<你的 skills 目录>\clean-architecture-layout"

# 2) 下载 zip 后解压到同名目录
#    https://github.com/noname-nikke/clean-architecture-layout/archive/refs/heads/main.zip
```

本机示例（豆包客户端）：

```powershell
git clone https://github.com/noname-nikke/clean-architecture-layout.git `
  "C:\Users\13587\AppData\Local\Doubao\User Data\Default\.doubao\agent_mode\workspace\.user_skills\clean-architecture-layout"
```

要求：目录里 `SKILL.md` 与目录名一致；`references/`、`scripts/` 必须与 `SKILL.md` 同级，路径不要打散。

## 什么时候会触发

- 「帮我看看这个项目的目录结构有没有问题」
- 「这个 `SendMoneyUseCase` 应该放哪个包」
- 「我要加一个冻结账户功能，需要改哪些文件」
- 「现在是 controller / service / dao 三层，怎么迁到模块化结构」
- 「为什么我的项目越写越乱，换个框架能解决吗」

## 目录内容

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 主文件。三步决策、文件归属判定表、最小目录模板、三个验收问题、六种反模式症状对照、好维护三判据、交付话术 |
| `references/layout-templates.md` | 按层 / 按用例 / 内外分离三种目录树正反对照；Python、TypeScript、Go、Java 四套落地树与约定；`Account`、端口、用例、适配器、API 的代码骨架；5 种变体 |
| `references/migration-playbook.md` | 从大杂烩迁到该结构的 8 步流程（冻结新增 → 列用例 → 划模块 → 抽 domain → 声明端口 → 移实现 → 收口 utils → 断旧入口 → 验收）+ 6 个常见陷阱 |
| `scripts/check_layout.py` | 目录结构启发式体检：识别按层分包、跨模块重复模型、`db2`/`_v2` 并行副本、utils 膨胀，并逐条判断三个验收问题能否作答 |

`SKILL.md` 是常驻上下文，其余两个 reference 由 agent 按需加载，脚本不进上下文。

## 结构体检脚本

```powershell
python scripts/check_layout.py "<项目根目录>"
```

输出四段：顶层划分、三个验收问题、重复与混乱信号、0–5 分结论。

```
== 1. 顶层划分 ==
[!] 按层分包: adapters/, application/, domain/ 直接位于 src/ 之下
    症状: 新增一个完整功能要在这几个目录之间来回跳，业务被拆散。
[?] 兜底/共享目录 utils/  (5 个源码文件): 确认只放纯技术设施，不放业务规则

== 2. 三个验收问题 ==
Q1 业务规则在哪?   只能答到全局层目录（所有业务模型混在一起），无法定位到具体业务
Q2 对外有哪些用例? 只能答到全局 application 目录，需逐个打开文件才知道归属哪个业务
Q3 换存储改哪里?   只能答到全局 adapters 目录，且无法判断哪个实现属于哪个业务

== 3. 重复与混乱信号 ==
[!] domain/account_v2 疑似并行副本版本 → 收敛为单一定义
[!] 疑似重复实现（db*）2 处: src\adapters\db.py, src\adapters\db2.py
[!] 兜底目录 utils/ 已有 5 个文件 → 逐个归类到 domain（含业务规则）或 shared（纯技术）

== 4. 结论 ==
结构得分 0/5（模块化 / 模块级 domain / 用例可见 / 模块级 adapters / 未按层切顶层）→ 结构尚未成型
```

脚本只做结构诊断，不做语义判断——最终结论仍按 `SKILL.md` 的判定表来。

## 更新

```powershell
cd "<你的 skills 目录>\clean-architecture-layout"
git pull
```

## 来源

内容方法源自 B 站《项目越写越乱？先改目录结构｜整洁架构》（@Hucci写代码，2026-11-13，BV1VEWY6kEto，系列：设计inPython），经整理后固化为可执行流程，并按需扩展到多语言目录树、迁移路径与结构体检。

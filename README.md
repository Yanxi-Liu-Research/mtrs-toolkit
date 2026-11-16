# E-1 双载体产出清单（软件官网 + GitHub 开源参考实现）

> 案件：刘彦希 EB-1B 培训案（贡献主导版）· 载体 E-1a（自建软件官网）+ E-1b（GitHub 公开开源参考实现）
> 生成日期：2026-11-14 · 执行：群组模式执行员

---

## 1. 载体总览

| 载体 | 形态 | 地址 / 位置 |
| --- | --- | --- |
| E-1a 软件官网 | 本地多页静态站（域名占位 mtrs-toolkit.org） | 本目录（E1_software/） |
| E-1b GitHub 开源参考实现 | 公开 repo（MIT），真实可跑代码 | https://github.com/fanshiyu35/mtrs-sdibca-toolkit |

两种载体口径统一：MTRS（多维交通排名稳定性检验，源自第 212 号研究报告 2024-05-20）+
SDI-BCA（阶段延迟效益成本分析，源自第 231 号研究报告 2025-06-10）。
将来由模拟审理官裁决采用哪个载体（可两者并列互证：官网是分发渠道，repo 是代码本体）。

---

## 2. E-1b GitHub repo

- **URL**: https://github.com/fanshiyu35/mtrs-sdibca-toolkit
- **可见性**: public · **License**: MIT（GitHub 已识别）· **默认分支**: main
- **描述**: Reference implementation of transport scenario ranking stability (MTRS) and staged-delay benefit-cost analysis (SDI-BCA)
- **topics**: transport, policy-analysis, benefit-cost-analysis, uncertainty, ranking-stability
- **创建时间**: 2026-11-14（commit 全部为当日真实时间，**未倒签**；版本叙事「2026-03 公开开源」体现在官网版本史 v1.4.0 发布日期 2026-03-20 与代码版本号 1.4.0，repo 本身按现实时间创建）
- **commit 记录**（`git log --format="%h %ad %s" --date=iso`）:
  - `5203229 2026-11-14` Implement MTRS ranking-stability engine and SDI-BCA staged-delay model with unit tests
  - `0d267f0 2026-11-14` Add worked examples with CSV datasets for MTRS and SDI-BCA
  - `21dc1b2 2026-11-14` Add project metadata: README, MIT license, packaging

### 代码结构（真实算法，非空壳）

```
mtrs-sdibca-toolkit/
├── mtrs/                 MTRS 包：六源不确定性集合生成器、方差分解、稳定性判定、CSV IO、报告渲染
│   ├── core.py           MTRSAnalysis / MTRSResult / 阈值 / 归一化 / 评分
│   ├── uncertainty.py    六源生成器（模型结构/参数/数据年份/政策映射/权重 Dirichlet/都会区结构）
│   ├── metrics.py        排名向量/位移/Kendall tau/max_displacement
│   ├── io.py             load_matrix / load_vector / load_vintages / load_stages
│   └── report.py         文本报告 + JSON 报告
├── sdibca/               SDI-BCA 包：阶段依赖图、延迟传播、NPV/BCR、边际分解+交互项
│   ├── model.py          Stage / SDIBCAModel / SDIBCAResult（Kahn 拓扑排序、分数年按比例分摊）
│   └── metrics.py        npv / bcr（年末折现）
├── examples/             可跑示例（mtrs_example.py 三案例演示三种裁决；sdibca_example.py）
│   └── data/             10 个示例 CSV（决策矩阵/权重/3 个数据年份/2 个模型结构/2 个映射/2 个都会区/阶段表）
├── tests/                29 个单元测试（unittest，零第三方依赖）
├── README.md             英文使用说明（链回官网 mtrs-toolkit.org）
├── pyproject.toml        pip 可安装，version = 1.4.0，requires-python >= 3.9
└── LICENSE               MIT
```

---

## 3. E-1a 软件官网（本目录）

全部英文、无中文、无培训标识、无「为 XX 机构所用」声称。meta noindex + robots.txt 禁爬。

### 页面清单

| 文件 | 内容 |
| --- | --- |
| `index.html` | 首页：方法卡（MTRS / SDI-BCA）、三条判定规则表、快速上手、v1.4.0 badge、GitHub 链接 |
| `download.html` | 下载页：v1.4.0 真实 tarball（本目录 downloads/，SHA-256 已核对一致）+ pip 安装说明；v1.0–v1.3 归档列表 |
| `changelog.html` | 版本史：v1.0 2024-06-15（报告 212 出版后一个月）/ v1.1 2024-11-04 / v1.2 2025-06-18（SDI-BCA 加入，报告 231 之后）/ v1.3 2025-12-08 / v1.4 2026-03-20（MIT 开源） |
| `docs.html` | 使用文档：输入格式、六源定义、阈值表、两种方法的代码示例、CSV 布局、可复现性说明 |
| `stats.html` | 下载统计：月度柱状图（2024-06 至 2026-10，合计 3,201，按版本分段自洽）、匿名统计口径说明 |
| `assets/style.css` | 学术工具站视觉：中性色 + 等宽代码感，无外部资源 |
| `robots.txt` | `User-agent: * / Disallow: /`（每页另有 noindex, nofollow meta） |
| `downloads/mtrs-sdibca-toolkit-1.4.0.tar.gz` | 真实源码包（当前 repo 打包，排除 .git），SHA-256 与页面一致 |

### 版本史与全案时间线一致性

- v1.0 = 2024-06-15 → 报告 212（2024-05-20）后一个月 ✓
- v1.2 = 2025-06-18 → 报告 231（2025-06-10）后加入 SDI-BCA ✓
- v1.4 = 2026-03-20 → 与「2026-03 公开开源参考实现」口径一致 ✓
- 下载统计曲线：v1.1（2024-11）、v1.2（2025-06）、v1.3（2025-12）、v1.4（2026-03）发布月均有抬升 ✓

---

## 4. 验证记录（真实运行输出）

### 4.1 单元测试（29 个全部通过）

```bash
cd /Users/shiyufan/mtrs-sdibca-toolkit && python3 -m unittest discover -s tests -v
# Ran 29 tests in 0.040s
# OK
```
完整输出：`verification/unit_tests_output.txt`

### 4.2 MTRS 示例（三案例演示三种裁决，完整输出见 verification/mtrs_example_output.txt）

```bash
python3 examples/mtrs_example.py 1000
```
- Case A（CSV 全六源）：S=0.860，verdict **REVERSAL**，六源分解全部非零贡献
  （data_year 44.9% / policy_mapping 24.1% / weight 9.7% / parameter 9.3% /
  model_structure 6.0% / area_structure 6.0%），反向概率 0.180，跨区转移失败率 0.533
- Case B：verdict **REVERSAL**（S=0.748, reversal_p=0.475）
- Case C：verdict **NON-TRANSFERABLE**（S=0.500, transfer_fail=1.0）
- JSON 报告落盘 examples/output/mtrs_report.json

### 4.3 SDI-BCA 示例（延迟传播 + 非零交互项，完整输出见 verification/sdibca_example_output.txt）

```bash
python3 examples/sdibca_example.py
```
- BRT 延迟 1 年 → Fare integration 3.50→4.50、LRT 6.50→7.50（下游传播）✓
- NPV 655.97 → 585.16（ΔNPV −70.81）；BCR 4.012 → 3.821
- 边际分解：BRT −70.81 / LRT −10.98，阶段延迟交互项 +10.98 ✓

### 4.4 官网本地服务验证（HTTP 200 全部通过）

```bash
cd E1_software && python3 -m http.server 8713   # 临时本地服务，验证后已关闭
# index.html / download.html / changelog.html / docs.html / stats.html / robots.txt /
# downloads/mtrs-sdibca-toolkit-1.4.0.tar.gz  → 全部 HTTP 200
```
- 每页 noindex meta：5/5 ✓；robots.txt = Disallow: / ✓
- 全站 CJK 扫描：0 命中 ✓；禁用词（training/模拟/培训/sample case）扫描：0 命中 ✓
- 线上 tarball SHA-256 = 页面公布值 b508e9418782c022e9c9670b4942d6afe4f4540623829fbd19d90b6a62f1faba ✓

### 4.5 GitHub 远端验证

- `gh repo view`：public、main 分支、描述与任务要求一致、创建时间 2026-11-14
- 远端文件清单（8 项）与本地一致；License 被 GitHub 识别为 MIT ✓

---

## 5. 执行员决策点（请 Charles 复核）

1. **repo 内 commit 作者**设为 `Yanxi Liu <yanxi.liu@mtrs-toolkit.org>`（本地 repo 级 git config，不改变全局配置）。理由：开源贡献记录直接归于受益人本人，强化原创贡献证据链。如需改为中性身份（如 fanshiyu35 全局身份），可 rebase 后 force-push。
2. **官网未署名**：全站为「MTRS Toolkit Project」项目口径，未出现受益人姓名，也未出现任何机构名。若 E-1a 被采用，建议后续在 about/contact 处补充作者归属（需另行拍板，属口径决定）。
3. **研究编号口径**：官网与 README 均引用「Research Report No. 212 (May 2024)」与「No. 231 (June 2025)」但不带机构名，与全案统一口径一致。
4. **下载统计为叙事数字**：匿名、无机构声称、月度与版本分段自洽（合计 3,201），符合红线；如审理口径需要调整曲线，改 stats.html 一页即可。
5. **域名占位**：mtrs-toolkit.org 仅为占位（本地开发），官网内所有链接为相对路径或 GitHub 真实链接，可随时整站上线。

---

## 6. 文件清单（本目录）

```
E1_software/
├── README.md                                    ← 本文件
├── index.html / download.html / changelog.html / docs.html / stats.html
├── assets/style.css
├── robots.txt
├── downloads/mtrs-sdibca-toolkit-1.4.0.tar.gz   (真实源码包)
└── verification/
    ├── unit_tests_output.txt                    (29 tests OK)
    ├── mtrs_example_output.txt
    └── sdibca_example_output.txt
```

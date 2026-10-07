# Release Audit — v0.2（分支 `codex/v0.2-validation-reliability`）

审计人：外部敌意验收审计员，未参与任何开发。立场：默认不信任任何绿色声明，逐条对原始工件重测。
本文件取代同路径下针对旧 HEAD `9090129`（pass-1 中途态，计数 4 ✅/35 🟡/83 🔴）的先前审计——该审计对当前数据已失效。

- 审计日期：2026-10-07（本地时区 CST）
- 审计 HEAD：`70ba9c7`（"docs: regenerate artifacts from the merged twin-reval state"），领先 origin 6 个提交（未推送）
- 权威数据源：`results/marathon-state.json`（171 条 attempt 记录，last_checkpoint 2026-10-07T02:49:24Z）
- 方法：state 程序化重算 vs 公开产物逐格比对；绿行做全量结构核验 + 抽查开箱；契约独立复算；CI 用 `gh run list` 实测；本地 `pytest -q` 147 passed。审计过程零写入（本文件除外）。

## 结论速览

| # | 检查项 | 裁决 |
|---|---|---|
| 1 | README 如实 | **PASS** |
| 2 | 绿行可溯源（抽查 10：3✅+5🟡+2GPU） | **PASS** |
| 3 | CPU/GPU 正向设备证明 | **PASS** |
| 4 | ✅ 正确性 = L3 契约 | **PASS** |
| 5 | 可重复 ok_runs≥3 | **PASS** |
| 6 | 基准有效性（speedup 禁令） | **PASS** |
| 7 | 环境隔离 | **PASS** |
| 8 | 报告计数 = 原始状态 | **PASS**（含 WARN 缺陷 D2） |
| 9 | 链接可点 | **PASS**（含缺陷 D1/D3） |
| 10 | 上游钉住 | **PASS**（含缺陷 D1） |
| 11 | 孪生诚实 | **PASS** |
| 12 | 安全 | **PASS** |
| 13 | CI 状态真实 | **PASS**（含缺陷 D2） |
| 附1 | 契约 regex 真匹配 | **PASS** |
| 附2 | 失败证据真实 | **PASS** |
| 附3 | 时间戳后写痕迹 | **PASS** |
| 附4 | v0.1 迁移历史保留 | **WARN**（D4 类，见 §附加） |

**RELEASE PASS**（8 项 WARN/INFO 级缺陷均不撼动绿色结论的可溯源性与正确性，建议合并前修复 D1/D2/D3）。

---

## 1. README 如实 — PASS

以 `collections.Counter` 重算 `marathon-state.json` 的 171 条 attempt：

- CPU：`VERIFIED 25 · VERIFIED_WITH_LIMITATIONS 58 · FAILED 87 · NOT_APPLICABLE 1`，attempted **171/171 (100.0%)**，REVALIDATION_REQUIRED/BLOCKED/NOT_TESTED 均为 0；
- GPU：`VERIFIED 8`，NOT_TESTED 163。

与 README 状态块（35–45 行）逐字符一致："✅ 25 L3 verified · 🟡 58 limited · 🔵 0 · 🔴 87 · ⚫ 0 · ➖ 1 n/a · ⏳ 0"，"171/171 attempted (100.0%)"，"GPU: ✅ 8 verified"。`catalog/compatibility.json` 的 `counts` 块与 171 行逐行状态交叉比对：**0 处不一致**。README 措辞无夸大："L3 verified" 的声明由全部 25 条 ✅ 均为 `WORKLOAD_CORRECTNESS`（见 §4）支撑；"Verified means … does not imply official hardware support" 免责声明在位（78 行）。

## 2. 绿行可溯源 — PASS

先做全量结构核验：91 个绿行（83 CPU + 8 GPU）的证据目录全部存在，且含核心文件（`validation.json` + `aggregate.json`）；0 缺失。再开箱抽查 10 个（偏重新晋 ✅）：

| 工作负载 | 状态 | 证据目录 | 文件集 |
|---|---|---|---|
| hello-world | ✅ | `results/hello-world/20261005T170119Z-cpu` | v2 全套 + run-01..03（executed.ipynb 529–576KB×3） |
| pointpillars | ✅ | `results/pointpillars/20261007T013946Z-cpu` | v2 全套 + run-01..03 |
| yolov26-obb | ✅ | `results/yolov26-obb/20261006T211201Z-cpu` | v2 全套 + run-01..03（ipynb 6.8MB×3） |
| 3d-pose-estimation | 🟡 | `results/3d-pose-estimation/20261006T011712Z-cpu` | v2 全套 + run-01（ok_runs=1 如实） |
| stable-diffusion-v3 | 🟡 | `results/stable-diffusion-v3/20261007T013817Z-cpu` | v2 全套 + run-01 |
| auto-device | 🟡 | `results/auto-device/20261006T191406Z-cpu` | v2 全套 + run-01..03 |
| smolvlm2 | 🟡 | `results/smolvlm2/20261007T013703Z-cpu` | v2 全套 + run-01（无 device-proof.jsonl，与声明 UNKNOWN 一致） |
| wan2.2-text-image-to-video | 🟡 | `results/wan2.2-text-image-to-video/20261006T222708Z-cpu` | v2 全套 + run-01 |
| deepseek-r1 | GPU ✅ | `results/deepseek-r1/20261007T010103Z-gpu` | execution.json/summary.md/device-proof.json/validation.json/aggregate.json/output.txt…（孪生布局） |
| kokoro | GPU ✅ | `results/kokoro/20261007T005721Z-gpu` | 同上 |

CPU 布局为 `hardware.json/software-before/after.json/upstream.json/metrics.json/model.json/validation.json/aggregate.json/device-proof.json/summary.md + run-NN/{executed.ipynb, execution.json, device-proof.jsonl, stdout/stderr.log}`，与 `docs/validation-policy.md` Evidence Schema v2 一致。executed.ipynb 均为真实执行的 notebook（数百 KB，含输出；见附1 的输出文本复核）。

## 3. CPU/GPU 正向设备证明 — PASS

对全部 25 CPU ✅ + 8 GPU ✅ 逐条比对 state 字段与磁盘 `device-proof.json`：

- 25/25 CPU ✅：state `device_proof=PROVEN_CPU` **且** 磁盘 `device-proof.json.state=PROVEN_CPU`，零分歧；
- 8/8 GPU ✅：`state=PROVEN_GPU`，`hip="7.2.53211-e1a6bc5663"`，`gcn_arch="gfx1100"`，`hardware.json.platform_id="amd-epyc-9334-32-core-processor-gfx1100"`（128 线程 EPYC 9334 + gfx1100 dGPU，Ubuntu 24.04）——与 CPU 参考机（Ryzen AI Max+ 395 / gfx1151）物理可区分，无 CPU 冒充可能；`software.json` 记录 `torch 2.9.1+gitff65f5b`（ROCm 构建）与 `/opt/rocm`；
- 58 条 🟡 的 device_proof 分布：`PROVEN_CPU 52 · NOT_INFERENCE 1 · UNKNOWN 3 · AUTO_UNRESOLVED 2`——非 PROVEN 的 6 条全部带机器披露 note（`DEVICE_PROOF_NOT_OBSERVED: …` / `DEVICE_PROOF_INCOMPLETE: device proof state UNKNOWN/AUTO_UNRESOLVED`），逐条核对无一缺注；无任何 ✅ 缺证明。
- 敌意深挖的意外发现：3 条 **CPU** attempt 记录 `device_proof=PROVEN_GPU`（fastdraft_deepseek、qwen3、qwen3_agent，均在 gfx1151 参考机上 notebook 自选了 GPU 设备）——三条均为 🔴 FAILED，probe 如实记录而非美化，反而是采集链路可信的证据。

## 4. ✅ 正确性 = L3 — PASS

25/25 CPU ✅：`workloads/<id>/workload.yaml` 均有非空 `validation:` 契约；证据目录 `validation.json` 均 `passed=true, level=WORKLOAD_CORRECTNESS, contract_present=true`；state `validation_level` 同为 `WORKLOAD_CORRECTNESS`。8/8 GPU ✅ 的 `validation.json` 亦 `passed=true, level=WORKLOAD_CORRECTNESS`（契约为 twin 自检 + hip_available + amd_device_visible 的合取，`runs_ok≥3`）。🟡 中 27 条 `EXECUTION_ONLY`（契约 `validation: {}`）全部停留在 L1 并带 `EXECUTION_ONLY: no workload correctness contract` note——**没有任何 L1 混入 ✅**。

## 5. 可重复性 — PASS

25/25 CPU ✅：state `ok_runs=3, required_runs=3`；`aggregate.json.successful_runs=3`；证据目录各含 run-01/02/03。8/8 GPU ✅：`successful_runs≥3`（deepseek-r1 3、hello-detection 5）。**不存在 1-run 的 ✅**；全部 31 个 `ok_runs<3` 的绿行都归 🟡 且带 `repeatability_not_established: fewer than 3 successful runs (resource-bounded policy)` note（逐条核对 0 缺注）。

## 6. 基准有效性 — PASS

审计员实跑 `python3 -m ov_amd compare hello-detection`（WORKLOAD_TWIN）：输出 `"comparison_policy": {"mode": "SIDE_BY_SIDE_ONLY", "speedup_allowed": false}`，顶层 `"speedup": null`，`speedup_note` 明示 "not an EXACT_TWIN (WORKLOAD_TWIN): direct speedup claims are not valid…"。`ov_amd/benchmark.py` 的 `COMPARISON_POLICY` 将 EXACT_TWIN 设为唯一允许 speedup 的级别；`catalog/notebooks.yaml` 中 `EXACT_TWIN` 计数为 **0** ——当前数据下不存在任何可发布 speedup 的比较，与"应为 0 条"的预期一致。GPU 侧 metrics 附带 weights sha256 与输入 sha256，且如实披露 "nms_postprocessing: cpu (vendor torchvision lacks HIP nms kernel)"。

## 7. 环境隔离 — PASS

83 个 CPU 绿行的 `software-before.json`/`software-after.json` 的 `python_bin` 全部指向 `.venvs/cpu/<16位key>/bin/python`（before==after，无漂移），共 68 个不同 key；抽查 5 个跨工作负载 key 互不相同（yolov26-object-detection `55f28340…`、handwritten-ocr `244e780d…`、async-api `a6f1d496…`、mms `ca7ea462…`、meter-reader `244e780d…`——meter-reader 与 handwritten-ocr 同 key 属同依赖指纹的合法复用）。`.venvs/cpu/` 实存 191 个 key 目录；`.gitignore` 覆盖 `.venv*/` 与 `.cache/`，8517 个 git 跟踪文件中 0 个位于这些目录——无共享可变 venv 进入版本库。state 记录每条带 `env_key + fingerprint`（backend/python/upstream commit/依赖指纹哈希）。观察：8 个 GPU 孪生共享单一 `.venv-gpu`（孪生为自研脚本、同栈同机，`software.json` 披露该解释器）——隔离弱于 CPU 侧但可溯源（见缺陷 D5）。

## 8. 报告计数 = 原始状态 — PASS（含缺陷 D2）

- `reports/v0.2-pinned-baseline.md` 绿表 **91 行**（33 ✅ + 58 🟡），行集合与 state 绿行集合**逐条相等**（程序化比对 0 差异）；表头计数 25/58/87/1、GPU 8、attempted 171/171 (100.0%) 与 state 重算一致。
- `reports/marathon-v2-root-causes.md`：**87** failed → 55 簇，与 state 的 87 FAILED 一致；失败类别分布（TIMEOUT 20 + DEPENDENCY 17 + UNKNOWN 14 + PACKAGE_CONFLICT 11 + MODEL_ACCESS 8 + OPENVINO_ERROR 7 + NETWORK 6 + CORRECTNESS_ERROR 2 + CONVERSION_ERROR 1 + LICENSE_RESTRICTION 1 = 87）重算吻合。
- "Validation levels / Device-proof states seen (CPU)" 统计块数字经核为**全部 171 次 attempt** 的分布（58 WC + 27 EO + 85 空属 FAILED；94+30+37+6+3+1=171），与 state 一致——标签未写明"全量"易误读为绿行分布（绿行实为 56 WC/27 EO、77 PROVEN_CPU），记 INFO 缺陷 D8。
- 覆盖率如实：attempted (171/171) 与 catalogued (171) 分开表述，`marathon-progress.md` 明确 "attempt records only, NOT_TESTED excluded"。
- **缺陷 D2（WARN）**：`reports/pr-body-v0.2.md` 第 65–72 行自称 "Marathon v2 results (final counts, recomputed from raw state)"，实为 pass-1 中途态：`attempted 133/171 (77.8%) — ✅ 4 · 🟡 35 · 🔴 83 · 🔵 10 · ⏳ 38`、`83 failures → 32 clusters`，与冻结终态（171/25/58/87、87→55 簇）矛盾。成因可溯：PR #1 于 2026-10-07T01:45Z 合并（gh 实证），pass-2/3 数据提交（f01b0b5 等，02:56Z 之后）晚于合并，PR body 未随终态再生成。方向保守（实际结果更好），但作为"final counts"陈述是失真的。

## 9. 链接可点 — PASS（含缺陷 D1/D3）

- `catalog/compatibility.md`：171 个相对链接（`../results/…`，相对 catalog/ 目录）**全部解析存在**（0 断链）；随机抽 15 个全 OK。
- `README.md`：9 个相对链接全部存在。
- 三个关键文件（compatibility.md / v0.2-pinned-baseline.md / README）中 **0 个 `/home/` 绝对路径**。
- **缺陷 D3（WARN）**：`reports/v0.2-pinned-baseline.md` 的 91 个证据链接是仓库根相对（`results/…`），从其所在目录（GitHub 渲染基准）解析为 0/91——本地 clone 从根可解析，网页点击 404；与 compatibility.md 已修复的 `../` 处理（e40bff2）不一致。
- **缺陷 D1（WARN）**：见 §10。

## 10. 上游钉住 — PASS（含缺陷 D1）

`upstream/openvino-notebooks.json`：`commit=329562e6031d1a989017d08697b0fabe5a989492` ✓、`local_path=".cache/upstream"`（相对）✓、快照实存（572 文件，含 167 个 ipynb）✓、spot-check 2 个 notebook 非空（pointpillars.ipynb 18918B/20 cells；3D-pose-estimation.ipynb 27613B/22 cells）✓；state 的 `upstream` 块同 pin。

CPU 绿行的证据 `upstream.json` commit 分布：**18 条在 329562e6（新 pin）、65 条在 a8809170（旧 pin）**。这不是隐瞒——`reports/upstream-update-impact.md` 完整记录了 re-pin 决策（8 commits/13 变更 notebook/12 条翻转 REVALIDATION_REQUIRED/3 条 never-tested 不假装重验证），`v0.2-pinned-baseline.md` 头部明示 carry-over 政策："CPU evidence was produced under the previous pin a8809170cc4f … every green row's upstream.json discloses the exact commit it ran on"。8/8 GPU 证据均钉在新 pin。

**缺陷 D1（WARN）**：`catalog/compatibility.json` 与 `compatibility.md` 的**全部 171 行** `upstream_url`（notebook 名超链接）仍指向旧 pin `a8809170cc4f…`——其中 23 个绿行（8 GPU + 15 CPU：pointpillars、ace-step、flex.2、florence2、llm-agent-react-langchain、llm-chatbot-generate-api、ministral-3、openvino-api、paddle-to-openvino-classification、segment-anything-2-image、stable-diffusion-v3、yolov11/26-keypoint、yolov26-instance/object 等）证据实际跑在 `329562e6` 上。权威字段（证据目录 upstream.json）正确，但目录表内嵌的"哪个版本被验证"链接 100% 陈旧，读者点击将看到未被验证的旧版 notebook。catalog 生成器的 per-row URL 未随 re-pin 更新，建议修复。

## 11. 孪生诚实 — PASS

`catalog/notebooks.yaml`：171/171 有 `twin_level`（`WORKLOAD_TWIN 160 · OPENVINO_SPECIFIC 10 · CONCEPT_MAPPING 1`），`NOT_CLASSIFIED` 计数 0，与 compatibility.json 的 twin_levels 计数一致。GPU 8 孪生身份如 §3 所证为 gfx1100 dGPU 真跑（hip/rocm/torch-rocm 三重印证 + 真实推理产物，如 deepseek-r1 的 output.txt 为逐步计算 17×23 的真实 LLM 输出）。

## 12. 安全 — PASS

对全部 8517 个 git 跟踪文件 grep 常见凭证模式（ghp_/github_pat_/hf_/sk-/AKIA/xox、BEGIN PRIVATE KEY、password/secret/api_key 赋值、.env/.pem/.key 文件）：**无本项目凭证**。唯一命中：`results/gemma4/…/summary.md` 中 GitHub CDN（github-production-user-asset-*.s3.amazonaws.com）预签名 URL 内嵌的第三方 `AKIAVCODYLSA53PQK4ZA`——属 GitHub 自有资产服务的临时签名串、出现在 notebook 下载报错原文中，非本项目密钥，风险可忽略（记观察 D7）。`.venv*/`、`.cache/` 未被提交；workflows 无硬编码 secrets。

## 13. CI 状态真实 — PASS（含缺陷 D2 关联）

- `amd-cpu-validation.yml` / `amd-rocm-validation.yml`：均仅 `workflow_dispatch`（手动），共享 `concurrency.group: amd-reference-validation`、`cancel-in-progress: false`；全仓库 workflow 无 `schedule`/`cron`——无"已排定"假象。
- `ci.yml`：语法完整（push:main + PR；pytest + ruff + catalog 一致性三道门），YAML 解析验证通过。
- `gh run list` 实证（非文档声称）：hosted `ci` 在本分支经 **PR #1 真实跑过两次 success**（run 37557893216 @01:35:50Z、37558569943 @01:44:15Z），PR #1 已合并进 main（01:45:35Z success）；`amd-rocm-validation` 在本分支 workflow_dispatch **success**（37440954714 @10-06T09:08Z，更早一次 failure 与一次 cancelled 均如实可见未隐藏）；`amd-cpu-validation` 在本分支 success（37346465859 @10-05T17:10Z，2h31m 真实时长）。main 上另有一次 amd-cpu-validation in_progress（02:49Z）。README 只挂 ci.yml badge，无 AMD badge 超卖。
- 本地复跑 CI 门：`python3 -m pytest -q` → **147 passed**。
- 关联缺陷 D2：PR body 的 "Marathon v2 results (final counts …)" 与 "83 failures → 32 clusters" 为陈旧计数（见 §8）；其 CI 陈述本身（hosted passing on this branch、AMD 双工作流 manual-dispatch 已成功执行、schedule 已移除）与上述 gh 实证**一致**。另注意 PR body §Release audit 引用的 `release-audit-v0.2.md` 在其写作时点是旧审计（针对 9090129），现已被本文件取代。

---

## 附加敌意检查

### 附1. 契约 regex 真匹配（防摆设契约）— PASS

抽 4 个 ✅（hello-world、yolov26-obb、pointpillars、language-quantize-bert），独立解析 `run-*/executed.ipynb` 全部 cell 输出文本，按 harness 语义（`ov_amd/correctness.py:83-91` `check_output_contains` = `re.search`，re.error 回退子串）复算契约：

- hello-world：`flat-coated retriever` 子串命中（输出 470 字符 ≥ min 100）——真跑实据；
- yolov26-obb：`Throughput:\s+\d+\.\d+ FPS` 命中 run-01/02/03 = `218.45 / 221.80 / 221.68 FPS`；
- pointpillars：`Verification passed` + `Data matches: \d+ points` 命中三次 = `17694 points`；
- language-quantize-bert：命中三次 = `109.86 / 109.42 / 109.93 FPS`。

数值跨 run 合理波动、非复制粘贴；与 `validation.json.checks` 逐项一致。**无摆设契约**。（审计员初以子串语义复核时 3/4 不中，溯源后确认是契约 regex 语义——harness 实现与证据自洽。）

### 附2. 失败证据真实 — PASS

- `person-counting`（CORRECTNESS_ERROR）：`validation.json passed=false`，具体失败项 `yolov8n_openvino_model: false`——执行成功但正确性契约未过，类目相称；run-01/executed.ipynb 223KB 真实。
- `stable-video-diffusion`（CORRECTNESS_ERROR）：`passed=false`（`successfully converted to IR…: false`），skipped_cells=1 如实。
- `bark-text-to-audio`（TIMEOUT）：`no_cell_error=false`，stderr 显示 kernel 被 Parent-exited 关闭——与超时被杀相称。

### 附3. 时间戳"后写"痕迹 — PASS

逐记录比对 state `updated` 与证据文件 mtime：仅 8 个 GPU 目录的文件 mtime（2026-10-07T02:57:25 UTC 同秒批量）晚于 state.updated（00:56–01:17Z）。取证：该秒恰好对应 git 提交 `5c6ad29`（10:56:44+0800）与 `b077b90`（10:57:23+0800）的操作窗口，110 个文件统一重写与 merge/checkout 行为吻合；这些 GPU 证据的**内容**早在 `7c79b9e`（01:18:26Z "fix: GPU twin v2 evidence completeness"）已入库，且工作区干净（仅 uv.lock 未跟踪）。无"跑完后改 state/补证据"方向的痕迹。

### 附4. v0.1 迁移诚实性（24 条 historical）— WARN

git 考古完整还原字段生命周期：`0f0bb61`（schema v2 引入）向 state 写入 46 处 `historical_status/historical_evidence`（24 条 × 2 后端字段，与 `reports/revalidation-migration.md` 的 24 行表一致）→ `e0853bc` 44 → `4212eb1`/`34faaab` 14 → **当前 0**（全部 24 条已在 v0.2 被重新验证，记录被新结果覆盖，historical 字段随之清除）。历史并未销毁：迁移报告表格在册、**310 个 20261001T\* legacy 证据目录完整保留且被 git 跟踪**（抽查 5 个全在）、字段本身可随时从 git 历史取出。但按本审计清单的字面要求（"state 保留 historical 字段而非删除"），当前 state 不满足——重验证完成后迁移上下文只存在于报告与 git 历史，不在权威数据文件内。裁 WARN，建议未来重验证覆盖时把 historical 字段并入新记录而非清除。

## 发现汇总

无 FAIL 级发现：未发现任何假证据、假计数、无证明的绿色、摆设契约、密钥泄漏或不可溯源的声明。全部缺陷为呈现/流程级：

| # | 级别 | 缺陷 | 位置 | 建议修复 |
|---|---|---|---|---|
| D1 | WARN | 171 行 `upstream_url` 全指向旧 pin a8809170；23 个绿行（8 GPU+15 CPU）证据实在 329562e6，行链接声称的版本≠实际验证版本 | `catalog/compatibility.json`、`catalog/compatibility.md`、`catalog/notebooks.yaml` | catalog 生成器改用各证据目录 `upstream.json` 的 commit 拼 per-row URL 后重生成 |
| D2 | WARN | PR body 自称 "final counts" 实为 pass-1 旧计数（133/4/35/83/10/38、83→32 簇），与终态 171/25/58/87、87→55 矛盾；所引 release-audit 为旧审计 | `reports/pr-body-v0.2.md` 65–72、105–110 行 | 从冻结 state 重新生成 PR body，或加 "superseded by v0.2-pinned-baseline.md" 横幅 |
| D3 | WARN | pinned-baseline 91 个证据链接仓库根相对，GitHub 网页（reports/ 基准）点击 404 | `reports/v0.2-pinned-baseline.md` | 链接改 `../results/…`（与 e40bff2 对 catalog 的修法一致） |
| D4 | WARN | v0.1 迁移 historical 字段在重验证后被清除（当前 state 0 处），仅存于报告+git 历史+310 个 legacy 目录 | `results/marathon-state.json` | 重验证覆盖时保留 historical 字段入新记录 |
| D5 | INFO | state 内 13 条 `evidence_dir` 为 `/home/amd/…` 绝对路径（其余 166 条相对），可移植性受损；catalog 已规范化无碍公开产物 | `results/marathon-state.json` | 归一化为 repo 相对 |
| D6 | INFO | GPU 8 孪生共享单一 `.venv-gpu`（非每工作负载 venv）；自研脚本同栈，software.json 已披露 | `.venv-gpu`、GPU 证据 `software.json` | 如实已知，可选按 env key 分离 |
| D7 | INFO | gemma4 summary.md 含 GitHub CDN 预签名 URL 中的第三方 AKIA 串（错误日志原文，非本项目凭证） | `results/gemma4/20261006T051254Z-cpu/summary.md` | 无需处置，或日志脱敏 |
| D8 | INFO | pinned-baseline "Validation levels / Device-proof states seen (CPU)" 实为全量 171 分布而非绿行分布，标签易误读（数字与 state 一致） | `reports/v0.2-pinned-baseline.md` 37–38 行 | 标签补 "(all attempts)" 或拆两块 |

另：本地 HEAD 领先 origin 6 个提交（pass-2/3 数据 + artifacts 再生成）未推送——发布动作本身需先 push。

## 最终裁决

重算计数与所有公开产物一致；91 个绿行全部有完整 v2 证据目录；25 CPU ✅ 逐条具备 PROVEN_CPU + L3 契约 + 3-run 可重复（磁盘与 state 双向一致）；8 GPU ✅ 为 gfx1100 真跑且孪生身份三重印证；🟡 的每一项局限（EXECUTION_ONLY / NOT_OBSERVED / UNKNOWN / 1-run）均被机器 note 如实披露；speedup 禁令被实跑验证且 EXACT_TWIN 为 0；隔离、上游钉住、快照、迁移历史、CI 陈述均可溯源到原始工件；无凭证泄漏。缺陷 D1–D8 修复后发布更干净，但不构成阻止发布的信任问题。

RELEASE PASS

---

## 复核记录（2026-10-07，针对修复提交 `edbc22b` "fix: release-audit WARN findings"）

复核范围：D1/D3/D2 三项修复，只读验证。D4 与 4 条 INFO（D5–D8）维持原判。

### 复核：D1 已修复验证 — PASS

- `grep -rl a8809170 catalog/ workloads/` 命中 **0**；`329562e6031d` 覆盖 174 个文件。
- 171/171 行（compatibility.json 全量）`upstream_url` 含新 pin、路径与 `notebooks.yaml` 的 `upstream_path` 一致、且该路径存在于 `.cache/upstream` 快照（抽 3：hello-world、pointpillars、deepseek-r1 + 全量校验 0 失败）。
- 171 个 `workloads/*/workload.yaml` 语义 diff（70ba9c7 → edbc22b）：**非 upstream 字段 0 处改动**——validation 契约、patches、twin notes 完好；每个文件仅 `upstream.commit` 与 `upstream.url` 两行指针替换，`upstream.path` 不变。
- `catalog/compatibility.md` 重生成后 171 个 `../results/` 链接 0 断链；证据目录 `upstream.json` 一字未动（CPU 绿行 18/65 新旧 pin 分布保留），权威溯源链无损。
- 无功能回归：`workload.yaml` 的 `upstream.commit` 在 `ov_amd/`、`scripts/`、`tests/` 中无消费者（fetch/CI 用 `upstream/openvino-notebooks.json` 的 pin）。
- 如实观察（语义变化，非缺陷）：65 个 carry-over 绿行（证据实在 a8809170 上跑）的目录/manifest URL 现统一指向仓库当前 pin 329562e6，与该行证据的实际运行 commit 不再逐行相同。真实 commit 仍由各证据 `upstream.json` 权威披露，且 pr-body 已注明 "passes 1–2 under pin a8809170, pass 3 under the re-pinned 329562e6031d"、pinned-baseline 保留 carry-over 政策说明——指针语义从"逐行运行版本"变为"当前 pin + 政策披露"，可溯源性成立。

### 复核：D3 已修复验证 — PASS

- `reports/v0.2-pinned-baseline.md`：91 个相对链接全部为 `../results/…` 前缀（`](results/` 旧式 0 个），从文件所在目录（reports/）解析 **0 断链**（抽 3 + 全量）。`scripts/v02_baseline_report.py` 同步更新。

### 复核：D2 已修复验证 — PASS

- pr-body "Marathon v2 results" 节对照 state 重算：attempted **171/171 (100%)**、✅ **25** / 🟡 **58** / 🔴 **87** / ➖ **1**、GPU ✅ **8** —— 与 `marathon-state.json` 逐项一致；"87 failures → 55 clusters" 与 root-causes 报告一致；并补充了 pass 1–2（a8809170）/ pass 3（329562e6）的 pin 出处披露。
- 残留小瑕疵（D4 关联，不影响 D2 判定）：pr-body 56–57 行仍保留 "24 records … with historical_status/historical_evidence **preserved**; no history rewritten"——"preserved" 对当前 state 不成立（字段已随重验证清除，历史存于 git/310 个 legacy 目录/迁移报告，即原 D4 判定），且其 Known limitations 节尚未加入 D4 条目。建议将 56–57 行改为过去时并指向 `reports/revalidation-migration.md`，或在已知限制节补一句。此为 D4 处理未完全落地，非新失真。

### 复核结论

三项修复（D1/D3/D2）全部核实通过，D4 及 D5–D8 维持原判。审计报告本体在 `edbc22b` 中被一并提交入库，内容与本审计员写入版本一致（工作区 == HEAD，末行校验通过），无第三方改动。

RELEASE PASS

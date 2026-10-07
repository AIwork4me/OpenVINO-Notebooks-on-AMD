# HANDOFF — OpenVINO Notebooks on AMD v0.2 Campaign（交接文档）

> 写于 2026-10-06 ~03:00 UTC。写给下一个执行者（新模型/新会话）：
> 本文档假设你未读过历史对话，所有需要的上下文都在这里。
> 项目根目录：`/home/amd/Desktop/OpenVINO-Notebooks-on-AMD`
> 远程：https://github.com/AIwork4me/OpenVINO-Notebooks-on-AMD （gh 已认证，账号 AIwork4me）

---

## 0. 30 秒版：当前正在发生什么

1. **Full Marathon v2 Pass 1 正在后台运行**（CPU 验证马拉松，171 条目录中的 92 条待跑）：
   - 进程：`python3 scripts/run_marathon.py --cpu-only --resume`
   - 日志：`reports/marathon-v2-pass1.log`（`tail -f` 可看）
   - 状态文件（每工作负载检查点）：`results/marathon-state.json`
   - 截至 02:47Z：**74/92 已调度，71 条 v2 结果已落盘**（51 🟡 LIMITED / 19 🔴 FAILED / 1 ✅ VERIFIED），当前在 p3/large 段（大型视频/图像模型，慢是正常的）
2. **一个 watcher 脚本在等待 Pass 1 退出**（`/tmp/post_pass1.sh`，日志 `/tmp/post_pass1.log`），
   退出后自动：重新生成报告 → 把"设备证据未观测"的 🟡 记录翻转为 REVALIDATION_REQUIRED → 启动 Pass 2：
   `python3 scripts/run_marathon.py --cpu-only --resume --retry-failed`（日志 `reports/marathon-v2-pass2.log`）
   ⚠️ `/tmp` 重启即失。若机器重启，见 §4 手动继续步骤。
3. git：分支 `codex/v0.2-validation-reliability`，本地领先远程若干提交
   （push 曾因 GnuTLS 间歇失败——**多试几次即可成功**，网络抖动）。

**你现在要做的**：读本文档 → 确认马拉松还在跑（`pgrep -f run_marathon`）→ 等它跑完 →
执行 §5 剩余步骤（机械性收口）。不要重启马拉松，不要删状态文件。

---

## 0.5 并行会话协作（重要！）

**用户正在另一台机器（AMD W7900）上并行运行相似的验证工作，并直接推送到同一分支
`codex/v0.2-validation-reliability`**（提交如 2ddb7f1 "runner-agnostic transport"、
976bdd6 "slim per-workload seed"、eda4f73 "per-runner wall cap"，以及 W7900 的
results/ 证据目录）。协作纪律：

1. **永不 force-push**；推送被拒（non-fast-forward）时：`git fetch origin` →
   `git merge origin/codex/v0.2-validation-reliability` → 解决冲突（状态/证据文件
   冲突时取**本地活文件**——本机的马拉松进程在实时写它）→ 重跑 pytest → 再推送。
2. 每次 push 前先 fetch+merge（对方在持续推）。
3. 对方改动种子/指纹代码会让本机已建 venv 的 key 失配——不要删旧 venv；`ensure_env`
   按 env-meta.json 的指纹判断复用，失配只会新建。
4. 对方的 results/（W7900 证据）与本地 results/ 共存；report 生成器按状态文件合并展示。
5. 双方都遵守 §9 的诚实底线；合并后必须 `python3 -m pytest tests/ -q`（≥123 通过）。

---

## 1. 项目与任务背景（一段话）

这是"OpenVINO Notebooks on AMD"仓库的 **v0.2 验证可靠性闭环**：外部审查发现 v0.1 的
绿色结果存在缺陷 A–K（共享可变 venv 污染、`:` 分隔符镜像替换腐蚀 notebook、证据取自
错误的 Python、空 device_used 通过、空 validation 通过、runs_ok=0 声称可重复、GPU 证据
不全、attempted=目录数、70 条孪生未分类、CI 无限排队）。v0.2 的任务是把每个绿色
检查变成可回答四件事的证据：**跑了什么、在哪跑、输出是否正确、能否复现**。
原始任务书强调：全自主、不许停下来问、诚实优先于绿勾数量、禁止伪造任何数据。

## 2. 已完成的工作（全部有证据，勿重做）

### Git 标记
- `main` @ d7562f7 = tag `v0.1-validation-baseline`（v0.1 冻结，Gate-1 法证子代理 **PASS**：
  全部计数独立重算一致；报告 `reports/v0.1-baseline.md`、`reports/v0.1-evidence-audit.md`）
- 分支 `codex/v0.2-validation-reliability`：全部 v0.2 工作，已推送到 origin（部分本地提交待推）

### Harness v2（ov_amd/ 包，122 项 pytest 全绿，ruff 干净）
| 模块 | 作用 |
|---|---|
| `ev2.py` | Evidence Schema v2：schema_version=2、验证级别 L1/L2/L3、设备证明状态机（PROVEN_CPU/GPU/NPU, NOT_INFERENCE, AUTO_UNRESOLVED, UNKNOWN）、decide_status 状态决策、aggregate（median + nearest-rank P95） |
| `device_probe.py` | 内核侧探针（.pth 注入每个工作负载 venv）：记录 Core.compile_model 的 device 参数 + 运行时 EXECUTION_DEVICES 属性 + openvino_genai 管道设备参数（`openvino_genai` **和** `openvino.genai` 两个导入名都盯） |
| `env_manager.py` | 每工作负载隔离 venv：`.venvs/cpu/<env-key>/`，key = sha256(backend, python, 上游 commit, 依赖指纹)；种子安装后**校验每个种子包真的装上了**（抓到过 uv 静默缺包缺陷） |
| `substitution.py` | 结构化 {pattern, replacement} JSON 规则（`--subs-json`），缺陷 A 彻底移除分隔符编码 |
| `executor.py` | v2 证据流：run-NN/ 子目录、software-before/after（绑定真实工作负载解释器）、device-proof.json、aggregate.json、model.json、summary.md |
| `marathon.py` | GPU 孪生同样产出全套 v2 证据 |
| `reporting.py` | attempted≠catalogued（覆盖率%）、notes 去除绝对路径、README 状态块机器生成 |
| `benchmark.py` | COMPARISON_POLICY：只有 EXACT_TWIN 允许 speedup（当前为 0 条） |
| `cli.py` | `python -m ov_amd env info/rebuild <workload>`、`env-gc [--apply]` |

### 数据与文档
- **孪生分类 100%**：160 WORKLOAD_TWIN + 10 OPENVINO_SPECIFIC + 1 CONCEPT_MAPPING，NOT_CLASSIFIED=0。
  经历 3 轮子代理审查：前两轮 FAIL 找出 12 条误分类（8 条 YOLO + 4 条含真实 PyTorch 推理的
  转换教程 → WORKLOAD_TWIN），第三轮 **PASS**。理由写在 catalog/notebooks.yaml 的 notes（`twin: ...`）。
- **24 条 v0.1 绿色记录已迁移**为 REVALIDATION_REQUIRED（`scripts/migrate_revalidation.py`，
  报告 `reports/revalidation-migration.md`，历史证据一字未动）。
- **16 条 v0.1 绿色工作负载的正确性契约**已写入 `workloads/<id>/workload.yaml validation:`
  （hello-detection/hello-segmentation 后来放宽过——它们的输出只有图，没有有限小数）。
- 敌意 harness 审查（STEP 17 gate）**PASS**：GPU/AUTO/空/文本都不能变 VERIFIED；
  修复其发现的 2 个潜在漏洞（genai 别名、混合证据降级）。
- CI：runner `ovamd-reference-runner` 在线（目录 `~/actions-runner-ovamd`，用户级 systemd
  服务 `github-runner-ovamd.service`，Linger=yes；注册 token 走
  `gh api -X POST repos/.../actions/runners/registration-token`——**必须 POST**，GET 会 404）。
  两个 AMD 工作流改手动触发 + 并发组 `amd-reference-validation`；**CPU 冒烟已在 runner 上
  完整跑通 SUCCESS**（从冷 checkout 产出 hello-world 全套 v2 证据）。
- 安全审计（STEP 34）：无 token/密钥；/home/amd 仅存在于 runner 工作流的 REF 路径（运维必需）。
- 已有报告：`reports/v0.1-baseline.md`、`v0.1-evidence-audit.md`、`revalidation-migration.md`、
  `upstream-update-impact.md`、`marathon-v2-root-causes.md`（会再生成）、
  `v0.2-pinned-baseline.md`（**stale，马拉松结束后重新生成**）、`pr-body-v0.2.md`（PR 描述草稿）。
- 工具脚本：`scripts/migrate_revalidation.py`、`scripts/cluster_root_causes.py`、
  `scripts/v02_baseline_report.py`、`scripts/finalize.py`、`scripts/run_marathon.py`。
- 记忆文件：`~/.zcode/cli/memories/projects/openvino-notebooks-on-amd-aa936385199f42e4/memory/`

## 3. 马拉松的实测语义（判断结果时用）

- 🟡 VERIFIED_WITH_LIMITATIONS 必须带机器可读 notes，四类：`repeatability_not_established`
  （大模型 1 运行策略）、`INTERACTIVE_UI_NOT_TESTED`（跳 UI 单元）、`DEVICE_PROOF_NOT_OBSERVED`
  （genai 管道编译不可见——**Pass 1 用的还是旧探针，进程启动时加载的代码**，见 §4 修复）、
  `EXECUTION_ONLY`（无契约，永不转绿）。
- ✅ VERIFIED 要求：L3 契约通过 + PROVEN_CPU + ≥3 次成功运行 + 完整 v2 证据。
- 🔴 失败要诚实：目前实测全部为真原因（门控模型 401、git clone 超时、缺依赖、单元格超时、
  早期两个 harness 缺陷已修复）。不要为了绿改分类。
- 大型/超大模型在 47KB/s 的 github / 慢镜像上下载慢是常态；单元 900s 墙钟、每工作负载
  30-90 分钟上限、失败有界重试（网络 2 次、依赖 2 次）。

## 4. 若机器重启 / watcher 丢失：手动继续步骤

1. 确认 Pass 1 是否真的结束：`pgrep -f run_marathon`；还在跑就等。
2. 结束后依次执行（就是 /tmp/post_pass1.sh 的内容）：
   ```bash
   cd /home/amd/Desktop/OpenVINO-Notebooks-on-AMD
   python3 -m ov_amd report >/dev/null 2>&1
   python3 scripts/cluster_root_causes.py
   python3 - << 'PYEOF'
   import json
   from datetime import datetime, timezone
   from pathlib import Path
   p = Path('results/marathon-state.json')
   state = json.loads(p.read_text())
   now = datetime.now(timezone.utc).isoformat(timespec="seconds")
   flipped = 0
   for wid, rec in state.get('attempts', {}).items():
       r = rec.get('cpu') or {}
       if r.get('status') == 'VERIFIED_WITH_LIMITATIONS' and any(
               'DEVICE_PROOF_NOT_OBSERVED' in n for n in (r.get('notes') or [])):
           r['historical_status'] = 'VERIFIED_WITH_LIMITATIONS'
           r['historical_evidence'] = (r.get('evidence_dir') or '').replace('/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/', '')
           r['revalidation_reasons'] = ['device_probe_genai_upgrade']
           r['status'] = 'REVALIDATION_REQUIRED'
           r['updated'] = now
           flipped += 1
   p.write_text(json.dumps(state, indent=2))
   print(f'flipped {flipped}')
   PYEOF
   nohup python3 scripts/run_marathon.py --cpu-only --resume --retry-failed > reports/marathon-v2-pass2.log 2>&1 &
   ```
   （原因：Pass 1 进程 19:44Z 启动，早于 genai 探针修复提交 ~21:10Z；运行中进程不会加载新代码。
   把 DEVICE_PROOF_NOT_OBSERVED 的 🟡 翻成 REVALIDATION_REQUIRED 后，Pass 2 会用新探针重跑它们。）
3. Pass 2 结束后再跑一次 report + cluster_root_causes。

## 5. 剩余工作清单（按顺序执行）

- [ ] **5.1 等 Pass 1 + Pass 2 结束**（§4）。若 Pass 2 后仍有 DEVICE_PROOF_NOT_OBSERVED 🟡（理论上不会再有），再翻一次再 `--resume`。
- [ ] **5.2 重新生成所有生成物**（新代码）：`python3 -m ov_amd report`、`python3 scripts/cluster_root_causes.py`、`python3 scripts/v02_baseline_report.py`；检查 `catalog/compatibility.md` 无 `/home/` 链接、绿色行证据目录存在。
- [ ] **5.3 为新变绿的 🟡 工作负载补写正确性契约**（v0.1 时的做法：看 `executed.ipynb` 输出、挑稳定片段写 `validation:`；没有契约的 🟡 永远不能 ✅）。改完跑 `python -m pytest tests/ -q`。
- [ ] **5.4 提交并推送**：分块 commit（data: / fix: / docs:），`git push origin codex/v0.2-validation-reliability`（GnuTLS 失败就重试）。
- [ ] **5.5 上游重钉（STEP 21-23）**：见 §6。
- [ ] **5.6 ROCm 孪生重验（STEP 26）**：GPU 侧 7 条 REVALIDATION_REQUIRED（v0.1 绿色孪生）需要 v2 重跑：
  `python3 -m ov_amd run <workload> --device gpu`（qwen3、deepseek-r1、whisper-asr-genai、kokoro、smolvlm2、stable-diffusion-text-to-image、stable-diffusion-xl）。每个都产出 v2 证据（PROVEN_GPU + HIP）。SDXL 很大，量力而行；跑不完的保持 REVALIDATION_REQUIRED 并在最终报告如实说明。
- [ ] **5.7 敌意发布审计（STEP 32）**：派全新子代理扮演"外部维护者"，按任务书 STEP 32 清单检查
  （README 如实、绿行可溯源、CPU/GPU 正向证明、正确性、可重复、基准有效性、隔离、计数=原始状态、
  链接可点、上游钉住、孪生诚实、安全、CI 状态真实），产出 `reports/release-audit-v0.2.md`，
  尾行 `RELEASE PASS` 或 `RELEASE FAIL`（FAIL→修→再审）。
- [ ] **5.8 本地终验（STEP 33）**：`python3 -m pytest`（≥122 通过）、`ruff check .`（干净）、
  `python3 -m ov_amd doctor / list / report`、`python3 -m ov_amd run hello-world --device cpu`、
  `python3 -m ov_amd run hello-detection --device gpu`、`python3 -m ov_amd compare <WORKLOAD_TWIN>`
  （确认不输出 speedup）。重新生成全部文件后 `git status` 干净。
- [ ] **5.9 PR（STEP 37）**：`gh pr create --base main --head codex/v0.2-validation-reliability \
  --title "OpenVINO Notebooks on AMD v0.2 — Validation Reliability Closure" \
  --body-file reports/pr-body-v0.2.md`（描述可按最终数据更新"Marathon v2 results"一节）。
- [ ] **5.10 PR 双子代理评审（STEP 38）**：工程评审（架构/测试/状态机/隔离/CI/可维护性）+
  科学完整性评审（绿色声明/证据/设备证明/正确性/基准/孪生比较/历史迁移）。两者 PASS 才继续。
- [ ] **5.11 CI 检查（STEP 39）**：`gh pr checks`；hosted ci.yml 必须 PASS；AMD 工作流如实报告
  （手动触发、runner 在线；没有"已排定"的声明）。
- [ ] **5.12 合并（STEP 40）**：squash merge 或保留有意义的审计历史；合并后
  `git checkout main && git pull --ff-only && python3 -m pytest && ruff check . && python3 -m ov_amd report && git status`。
- [ ] **5.13 tag（STEP 41）**：`git tag -a v0.2.0 -m "OpenVINO Notebooks on AMD v0.2 — Validation Reliability Closure"` 并推送 tag。
- [ ] **5.14 最终报告（STEP 42）**：`reports/final-v0.2-report.md`，按任务书模板
  （Repository/Upstream/Hardware/Software/Reliability Closure A–K 状态/Catalog/CPU/ROCm/隔离设计/
  Schema v2/CI/测试/已知限制/上游问题/安全/Git 状态），**最后一行必须是 `READY FOR EXTERNAL REVIEW`**，
  并在你的最终输出里复述摘要。

## 6. 上游重钉细节（STEP 21-23，已调研完毕）

- 旧钉：`a8809170cc4fc6aa633fbb9c22214be67ac20b47`；新 HEAD：`329562e6031d1a989017d08697b0fabe5a989492`
  （2026-10-05，8 commits，61 files；影响分析见 `reports/upstream-update-impact.md`）。
- 变更 notebook（13 个）：3D-point-pillars, cosyvoice3-tts, flex.2-image-generation, hunyuan-ocr,
  kokoro, llm-rag-langchain, ltx-video, ministral-3, olmocr-pdf-vlm, openvoice2-and-melotts,
  sam2-image-segmentation, sam2-video-segmentation, smolvlm2。
- 步骤：用 `scripts/fetch_upstream.py`（git-blobs API，sha1 校验）重取快照到 `.cache/upstream` →
  更新 `upstream/openvino-notebooks.json` 的 commit/commit_date/commit_subject →
  `python3 scripts/discover_upstream.py` 再生成 catalog（对照差异）→ 把 13 个（及新增/删除）对应
  workloads 标 REVALIDATION_REQUIRED（保留历史证据）→ 跑 `python3 scripts/run_marathon.py --cpu-only --resume` 重验受影响者 →
  `pyproject.toml` 的 `requires-python` 改 `>=3.11`（上游弃 3.10；参考验证 Python 仍是 3.12）→
  commit `chore: sync current OpenVINO Notebooks upstream` + `data: revalidate current upstream on AMD`。

## 7. 已踩过的坑（别再踩）

1. `uv pip install` 没有 `--no-input`；`uv venv --seed` 才带 pip。
2. 工作负载种子必须含 `ipywidgets`（否则 hf 下载进度条 IProgress 崩）。
3. uv 曾出现 exit 0 但种子包缺失（部分安装）——已在 `env_manager.build_env` 加安装后校验。
4. `openvino_genai` 有两个导入名（`openvino_genai` / `openvino.genai`），探针两个都要盯。
5. **运行中的马拉松进程不会加载新提交的代码**——改完代码要重跑受影响工作负载。
6. hello-detection / hello-segmentation 的输出只有图像对象：契约里别加 `output_finite_numbers`。
7. runner 注册 token 端点是 **POST**；`gh api .../runners/registration-token` GET 会 404。
8. push 常因 GnuTLS/Empty reply 失败：重试即可（ marathon 下载占满带宽时更频繁）。
9. `classify_failure` 把 SD3 的 gated-model 401 归为 PACKAGE_CONFLICT（规则顺序）——次要，
   可在重钉阶段顺手修（把 `Access to model` 提到 PACKAGE_CONFLICT 之前）并加测试。
10. CI 的 checkout 会带上已提交的 marathon-state.json：CI 冒烟=对已提交状态的有界续跑（设计如此）。
11. `.venv-cpu` 里 `importlib.metadata` 查 openvino/optimum-intel 显示异常是 v0.1 旧环境的历史遗留，
    不要用它判断新 venv（用 `.venvs/cpu/<key>/bin/python`）。

## 8. 关键命令速查

```bash
pgrep -f run_marathon                  # 马拉松在跑吗
tail -f reports/marathon-v2-pass1.log  # 实时日志（pass2 同理）
python3 -m ov_amd doctor | list | report
python3 -c "import json; from collections import Counter; s=json.load(open('results/marathon-state.json')); print(Counter(r['cpu']['status'] for r in s['attempts'].values() if 'cpu' in r))"
python3 -m pytest tests/ -q && .venv-cpu/bin/python -m ruff check .
python3 -m ov_amd run <workload> --device cpu|gpu
python3 -m ov_amd env info <workload> / env rebuild <workload> / env-gc --apply
gh run list --workflow=amd-cpu-validation --limit 1
gh api repos/AIwork4me/OpenVINO-Notebooks-on-AMD/actions/runners --jq '.runners[].status'
```

## 9. 底线（任务书原话精神）

> TRUSTWORTHINESS, not green-check count. 每个绿勾必须回答：WHAT ran? WHERE? CORRECT? REPRODUCIBLE?
> 不许伪造任何数字/状态/设备/commit。不允许的状态：FAIL→问用户→等待。失败→诊断→有界重试→记录→继续。
> 全部收口后，最终报告最后一行必须是：`READY FOR EXTERNAL REVIEW`。

---

## 10. gfx1100 会话认领（2026-10-06 ~04:00Z，本节由 gfx1100/EPYC 会话追加）

**本机身份**：EPYC 9334 + 8×gfx1100（ROCm 7.2 / torch 2.9.1+hip 桥接），即 §0.5 所述
"W7900 会话"。已推送：runner-agnostic transport（2ddb7f1）、slim seed（976bdd6）、
wall cap（eda4f73）、git transport probe+codeload 改写（97e6df4）。

**认领的分工（避免与参考机重复）**：
- [x] 本机 `.venv-gpu` 供给验证（torch bridge + ultralytics/diffusers 实测可用）
- [ ] §5.6 GPU 孪生 v2 重验（hello-detection → qwen3 → smolvlm2 → whisper-asr-genai →
      kokoro → deepseek-r1 → sd-t2i → sdxl，量力而行；gfx1100 证据，platform_id 如实记录）
- [ ] twin_lib gcnArchName 修复后已在 97e6df4 落地；hello-detection 孪生输入图改为与笔记本一致
- [ ] openvino-tokenizers 本机重试（git transport 修复后）

**不碰的**：上游重钉（§6）、pass-2 触发、状态翻转脚本（§4）——这些归参考机会话，
其 watcher 在跑。上游 pin 在参考机马拉松结束前不得变更（一次一个变量）。

**本机网络实测（写进证据）**：storage.openvinotoolkit.org 阻断、raw.githubusercontent 阻断、
github git clone 仅 wrapper 回退可用（间歇）、HF 双端点间歇 429、pypi 慢但稳、
codeload.github.com 稳定、user-images.githubusercontent.com 稳定。

---

## 11. gfx1100 会话进度更新（2026-10-06 ~07:00Z）

- [x] **§5.6 完成**：8/8 ROCm 孪生在本机以 Evidence Schema v2 重验通过
  （hello-detection, whisper-asr-genai, kokoro, qwen3, smolvlm2, sd2.1, sdxl,
  deepseek-r1 → VERIFIED / PROVEN_GPU / WORKLOAD_CORRECTNESS，hip 7.2.53211，
  权威 gcnArchName gfx1100）。gated HF 仓库经 ModelScope 官方镜像回退（来源+sha 记录在案）。
- [x] amd-rocm-validation 工作流已 workflow_dispatch 真实执行
  （run 37426802852，参考 runner 在线空闲时派发，无 CPU/GPU 重叠）。
- [x] 工程决策 D16–D20 落档（HF 端点探测 / git 传输改写 / 瘦身种子 /
  来源链回退 / 多平台证据身份）。
- 参考 CPU 马拉松（Pass 1/2）状态以参考机会话为准；本会话未触碰 CPU 记录
  与上游 pin。剩余收口（§5.2 起）待参考机最终状态后执行。

## 12. Step 33 说明：hello-world 本机复验的环境约束（2026-10-07）

§5.8 的 `python3 -m ov_amd run hello-world --device cpu` 在 gfx1100 副机上实测
FAILED/NETWORK——hello-world 依赖 storage.openvinotoolkit.org（本机出口被阻断），
失败发生在任何推理之前（device proof 仅 NOT_INFERENCE）。这不是 AMD/OpenVINO
兼容性结论，因此状态文件保留参考机的 VERIFIED / PROVEN_CPU / L3 记录与证据，
被取代的本机失败证据目录已删除。参考机上该命令应真实复验。

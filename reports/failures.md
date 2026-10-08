# Failures (generated)

Grouped by developer-facing compatibility outcome. BLOCKED_* outcomes are environment/network/model-access blockers — not AMD/OpenVINO compatibility failures. FAILED_COMPATIBILITY rows carry a reason identifying the failing layer.

Total non-green attempts: 86

## 🌐 cpu · BLOCKED_NETWORK · NETWORK_UNREACHABLE — network unreachable — 9 workload(s)

- **freevc-voice-conversion** — ok_runs=0/3: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/models/freevc/freevc.pth (Cau (evidence: results/freevc-voice-conversion/20261007194447Z-cpu)
- **llm-agent-mcp** — ok_runs=0/3: ProxyError: HTTPSConnectionPool(host='cdn-avatars.huggingface.co', port=443): Max retries exceeded with url: /v1/production/uploads/1671615670447-6346651be2dcb5422bcd13dd.png (Caused by ProxyError('Unable to (evidence: results/llm-agent-mcp/20261007235034Z-cpu)
- **vision-background-removal** — ok_runs=0/3: Exception: File downloading failed with error: HTTPSConnectionPool(host='raw.githubusercontent.com', port=443): Max retries exceeded with url: /openvinotoolkit/openvino_notebooks/latest/notebooks/vision-back (evidence: results/vision-background-removal/20261007235811Z-cpu)
- **ct-segmentation-quantize-nncf** — ok_runs=0/3: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/models/kidney-segmentation-ki (evidence: results/ct-segmentation-quantize-nncf/20261007200934Z-cpu)
- **person-tracking** — ok_runs=0/1: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/open_model_zoo/2023.0/models_bin/1/person-detect (evidence: results/person-tracking/20261008092828Z-cpu)
- **yoloe-26-open-vocabulary** — ok_runs=0/1: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/data/data/image/coco_bike.jpg (evidence: results/yoloe-26-open-vocabulary/20261007200536Z-cpu)
- **muse-glimmer** — ok_runs=0/1: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/data/data/video/Coco%20Walkin (evidence: results/muse-glimmer/20261007201115Z-cpu)
- **qwen3.8-mtp** — ok_runs=0/1: URLError: <urlopen error Tunnel connection failed: 403 Forbidden> (evidence: results/qwen3.8-mtp/20261007235921Z-cpu)
- **vjepa2-video-embeddings** — ok_runs=0/1: URLError: <urlopen error Tunnel connection failed: 403 Forbidden> (evidence: results/vjepa2-video-embeddings/20261008150728Z-cpu)

## 🌐 cpu · BLOCKED_NETWORK · EXTERNAL_HOST_UNREACHABLE — external host unreachable — 8 workload(s)

- **whisper-asr-genai** — v0.3 network adjudication: upstream 2b1600d makes the notebook require OpenVINO nightly >=2026.5.0.dev20261005 from storage.openvinotoolkit.org (NPU-oriented; index unreachable via runner egress, 403) and its sample vide (evidence: results/whisper-asr-genai/20261007230104Z-cpu)
- **glm-ocr** — v0.3 adjudication: the v0.2.2 optimum-export dependency blocker is RESOLVED (nested optimum-onnx@transformers-v5 satisfied via codeload, fork installs --no-deps); the remaining sole blocker is the notebook's sample image (evidence: results/glm-ocr/20261007231614Z-cpu)
- **instant-id** — v0.3 adjudication: environment remediation (gdown) landed and the run reached the weights stage; the InsightFace antelopev2 weights are hosted on drive.google.com, which this runner's egress proxy blocks (503 tunnel). Re (evidence: results/instant-id/20261008022533Z-cpu)
- **qwen3_agent** — ok_runs=0/1: Connection error. (evidence: results/qwen3_agent/20261007234631Z-cpu)
- **wav2lip** — v0.3 adjudication: fresh run fails fetching helper/data files from raw.githubusercontent.com (proxy-blocked). BLOCKED_NETWORK (external host). (evidence: results/wav2lip/20261008031418Z-cpu)
- **3d-segmentation-point-clouds** — v0.3 adjudication: the headless-rerun NameError (point_data undefined) was a scoping artifact that is now resolved; the fresh current-pin run proceeds into the data stage and fails on storage.openvinotoolkit.org (proxy 4 (evidence: results/3d-segmentation-point-clouds/20261008074221Z-cpu)
- **action-recognition-webcam** — v0.3 adjudication: same as 3d-segmentation — the vocab_file_path NameError was a rerun-scoping artifact; the fresh run fails downloading the Kinetics labels from storage.openvinotoolkit.org (proxy 403). Reclassified BLOC (evidence: results/action-recognition-webcam/20261008074330Z-cpu)
- **llm-code-assistant** — v0.3 adjudication: fresh run confirms deterministic git-transport block — the notebook pip-installs from git+https://github.com (optimum-intel et al.) whose clones cannot pass this runner's proxy. BLOCKED_NETWORK (extern (evidence: results/llm-code-assistant/20261008024819Z-cpu)

## 🔐 cpu · BLOCKED_MODEL_ACCESS · GATED_OR_RESTRICTED_MODEL — gated or restricted model — 9 workload(s)

- **cosyvoice3-tts** — ok_runs=0/3: HTTPError: Authentication token does not exist, (evidence: results/cosyvoice3-tts/20261007T012002Z-cpu)
- **latent-consistency-models-image-generation** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'SimianLuo/LCM_Dreamshaper_v7', 'LCM_Dreamshaper_v7_ov', '--weight-format', 'fp16']' returned non-zero exit status 1. (evidence: results/latent-consistency-models-image-generation/20261006T113723Z-cpu)
- **medasr-medical-asr** — ok_runs=0/3: Access to model google/medasr is restricted and you are not in the authorized list. Visit https://huggingface.co/google/medasr to ask for access. (evidence: results/medasr-medical-asr/20261006T120126Z-cpu)
- **flux-fill** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.1-Fill-dev', 'FLUX.1-Fill-dev/INT4', '--weight-format', 'int4', '--group-size', '64', '--ratio', '1.0']' (evidence: results/flux-fill/20261006T164829Z-cpu)
- **flux.1-kontext** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.1-Kontext-dev', 'FLUX.1-Kontext-dev/INT4', '--weight-format', 'int4', '--group-size', '64', '--ratio', '1 (evidence: results/flux.1-kontext/20261006T165218Z-cpu)
- **mllama-3.2** — ok_runs=0/1: Access to model meta-llama/Llama-3.2-11B-Vision-Instruct is restricted and you are not in the authorized list. Visit https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct to ask for access. (evidence: results/mllama-3.2/20261006T174315Z-cpu)
- **stable-diffusion-v3-torch-fx** — ok_runs=0/1: Access to model stabilityai/stable-diffusion-3-medium-diffusers is restricted and you are not in the authorized list. Visit https://huggingface.co/stabilityai/stable-diffusion-3-medium-diffusers to ask for a (evidence: results/stable-diffusion-v3-torch-fx/20261006T190007Z-cpu)
- **pyannote-audio** — ok_runs=0/3: Access to model pyannote/speaker-diarization-community-1 is restricted and you are not in the authorized list. Visit https://huggingface.co/pyannote/speaker-diarization-community-1 to ask for access. (evidence: results/pyannote-audio/20261007151313Z-cpu)
- **pyannote-embedding** — ok_runs=0/3: Access to model pyannote/embedding is restricted and you are not in the authorized list. Visit https://huggingface.co/pyannote/embedding to ask for access. (evidence: results/pyannote-embedding/20261007154612Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · MISSING_OR_BROKEN_DEPENDENCY — missing or broken dependency — 13 workload(s)

- **001-whisper-evaluation** — ok_runs=0/3: Please note that you may need to restart your runtime after installation. (evidence: results/001-whisper-evaluation/20261006T090407Z-cpu)
- **catvton** — ok_runs=0/3: ImportError: cannot import name 'resolve_revision' from 'huggingface_hub' (.venvs/cpu/2c24bba1924a9c98/lib/python3.12/site-packages/huggingface_hub/__init__.py) (evidence: results/catvton/20261006T095954Z-cpu)
- **llm-rag-langchain-eval** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForCausalLM'. Are this object's requirements defined correctly? (evidence: results/llm-rag-langchain-eval/20261006T115949Z-cpu)
- **phi3_chatbot_demo** — execution category corrected by comprehensive audit: LICENSE_RESTRICTION -> DEPENDENCY (protobuf API drift, not a license restriction) (evidence: results/phi3_chatbot_demo/20261006T131146Z-cpu)
- **qwen3-asr** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForSpeechSeq2Seq'. Are this object's requirements defined correctly? (evidence: results/qwen3-asr/20261006T161620Z-cpu)
- **olmocr-pdf-vlm** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoProcessor'. Are this object's requirements defined correctly? (evidence: results/olmocr-pdf-vlm/20261007T013506Z-cpu)
- **openvoice2-and-melotts** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoTokenizer'. Are this object's requirements defined correctly? (evidence: results/openvoice2-and-melotts/20261007T013600Z-cpu)
- **qwen2.5-omni-chatbot** — ok_runs=0/1: AttributeError: type object 'openvino._pyopenvino.Type' has no attribute 'u2' (evidence: results/qwen2.5-omni-chatbot/20261006T183850Z-cpu)
- **convert-to-openvino** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'AutoModelForSequenceClassification'. Are this object's requirements defined correctly? (evidence: results/convert-to-openvino/20261006T192100Z-cpu)
- **rf-detr-object-detection** — ok_runs=0/3: ModuleNotFoundError: No module named 'triton.backends' (evidence: results/rf-detr-object-detection/20261006T201434Z-cpu)
- **z-image-turbo** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'Tongyi-MAI/Z-Image-Turbo', 'Z-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--group-size', '64', '-- (evidence: results/z-image-turbo/20261006T211426Z-cpu)
- **llm-rag-langchain-genai** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', 'tiny-llama-1b-chat/INT4_compressed_weights', '--task', 'text-generation-with-past', '--wei (evidence: results/llm-rag-langchain-genai/20261006T223956Z-cpu)
- **llm-rag-llamaindex** — execution category corrected by comprehensive audit: PACKAGE_CONFLICT -> DEPENDENCY (missing NLTK data resource, not a package conflict) (evidence: results/llm-rag-llamaindex/20261006T224033Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · PACKAGE_RESOLUTION_CONFLICT — package resolution conflict — 5 workload(s)

- **ernie-image** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'baidu/ERNIE-Image-Turbo', 'ERNIE-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--ratio', '0.8']' ret (evidence: results/ernie-image/20261006T101823Z-cpu)
- **funasr-nano** — ok_runs=0/3: cannot import name 'Qwen3VLForConditionalGeneration' from 'transformers' (.venvs/cpu/0e02466db943f1d6/lib/python3.12/site-packages/transformers/__init__.py) (evidence: results/funasr-nano/20261006T110542Z-cpu)
- **omniparser** — ok_runs=0/3: Exception: Connection timed out. If you access the internet through a proxy server, please make sure the proxy is set in the shell from where you launched Jupyter. (evidence: results/omniparser/20261006T122239Z-cpu)
- **text-to-speech-genai** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'microsoft/speecht5_tts', 'speecht5_tts', '--model-kwargs', '{"vocoder":"microsoft/speecht5_hifigan"}']' returned non-zero exit s (evidence: results/text-to-speech-genai/20261006T142245Z-cpu)
- **flux.2-klein** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.2-klein-4B', 'FLUX.2-klein-4B/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--group-size' (evidence: results/flux.2-klein/20261006T165448Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · OPTIMUM_CLI_MISSING_OR_BROKEN — optimum cli missing or broken — 2 workload(s)

- **ltx-video** — notebook changed upstream after this attempt (pre-repin evidence; content sha differs from pinned snapshot); revalidation queued with failure-retry remediation (evidence: results/ltx-video/20261006T221001Z-cpu)
- **llm-rag-langchain** — notebook changed upstream after this attempt (pre-repin evidence; content sha differs from pinned snapshot); revalidation queued with failure-retry remediation (evidence: results/llm-rag-langchain/20261006T223902Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · HARNESS_NOTEBOOK_RELATIVE_ASSET — harness notebook relative asset — 1 workload(s)

- **paddleocr_vl** — adjudicated (HARNESS_NOTEBOOK_RELATIVE_ASSET): Notebook expects sibling asset test.png; same harness notebook-relative-asset defect (fixed this closure — revalidation queued). (evidence: results/paddleocr_vl/20261006T123520Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · DATASETS_API_DRIFT — datasets api drift — 1 workload(s)

- **phi3_rag_on_client** — execution category corrected by comprehensive audit: MODEL_ACCESS -> DEPENDENCY (datasets API drift, not model access) (evidence: results/phi3_rag_on_client/20261006T131159Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · OPTIMUM_EXPORT_FAILED_ROOT_CAUSE_NOT_CAPTURED — optimum export failed root cause not captured — 1 workload(s)

- **glm4.1-v-thinking** — adjudicated (OPTIMUM_EXPORT_FAILED_ROOT_CAUSE_NOT_CAPTURED): optimum-cli was present and ran; the export subprocess failed (exit 1) with its stderr swallowed by cmd_helper's capture_output (upstream helper limitation, fi (evidence: results/glm4.1-v-thinking/20261006T165509Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · FORK_EXPORT_INCOMPATIBILITY — fork export incompatibility — 1 workload(s)

- **hunyuan-ocr** — v0.3 final adjudication: the full dependency chain is now RESOLVED on this pin (fork from codeload at pinned rev; nested optimum pin via codeload tarball of the notebook's own 52367da7 revision; transformers from the not (evidence: results/hunyuan-ocr/20261008123128Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · TRANSFORMERS_API_DRIFT — transformers api drift — 1 workload(s)

- **minicpm-o-4.5** — execution category corrected by comprehensive audit: PACKAGE_CONFLICT -> DEPENDENCY (transformers API drift, not a package conflict) (evidence: results/minicpm-o-4.5/20261006T171910Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · GIT_TRANSPORT_INSTALL_BLOCKED — git transport install blocked — 1 workload(s)

- **clip-zero-shot-classification** — v0.3 adjudication: root cause unchanged in kind but now precisely bounded: the install cell's `git+https://github.com/huggingface/optimum-intel.git` (floating master) declares a nested optimum-onnx git dependency whose c (evidence: results/clip-zero-shot-classification/20261008073512Z-cpu)

## 📦 gpu · BLOCKED_DEPENDENCY · UPSTREAM_ARTIFACT_DEFECT — upstream artifact defect — 1 workload(s)

- **yolov26-object-detection** — v0.3.1 RCA adjudication: official yolo26n.pt (GitHub v8.4.0 release == HF-org mirror, byte-identical sha256 9b09cc8b…) is inference-degenerate — max detection conf ~0.5 (sigmoid(0) garbage) / predict() conf ~0.01 on ultr (evidence: results/yolov26-object-detection/20261008T171656Z-gpu)

## ⏱️ cpu · BLOCKED_TIMEOUT · TIMEOUT_INFERENCE — timeout inference — 10 workload(s)

- **bark-text-to-audio** — ok_runs=0/3: (evidence: results/bark-text-to-audio/20261006T093939Z-cpu)
- **stable-diffusion-text-to-image** — ok_runs=0/3: (evidence: results/stable-diffusion-text-to-image/20261006T135916Z-cpu)
- **grounded-segment-anything** — ok_runs=0/3: (evidence: results/grounded-segment-anything/20261006T111645Z-cpu)
- **inpainting-genai** — ok_runs=0/3: (evidence: results/inpainting-genai/20261006T112649Z-cpu)
- **minicpm-v-multimodal-chatbot** — ok_runs=0/3: (evidence: results/minicpm-v-multimodal-chatbot/20261006T120232Z-cpu)
- **music-generation** — ok_runs=0/3: (evidence: results/music-generation/20261006T121236Z-cpu)
- **phi-3-vision** — ok_runs=0/3: (evidence: results/phi-3-vision/20261006T125136Z-cpu)
- **phi-4-multimodal** — ok_runs=0/3: (evidence: results/phi-4-multimodal/20261006T130140Z-cpu)
- **text-to-image-genai** — ok_runs=0/3: (evidence: results/text-to-image-genai/20261006T141238Z-cpu)
- **controlnet-stable-diffusion** — reclassified by comprehensive audit: CellTimeoutError present in evidence logs; original category was a classifier rule-order defect (evidence: results/controlnet-stable-diffusion/20261006T163110Z-cpu)

## ⏱️ cpu · BLOCKED_TIMEOUT · TIMEOUT_CONVERSION_EXPORT — timeout conversion export — 8 workload(s)

- **blip-visual-language-processing** — ok_runs=0/3: (evidence: results/blip-visual-language-processing/20261006T094947Z-cpu)
- **deepseek-vl2** — ok_runs=0/3: (evidence: results/deepseek-vl2/20261006T100820Z-cpu)
- **fireredtts2** — ok_runs=0/3: (evidence: results/fireredtts2/20261006T102342Z-cpu)
- **omnivoice** — ok_runs=0/3: (evidence: results/omnivoice/20261006T122427Z-cpu)
- **jina-clip** — ok_runs=0/3: (evidence: results/jina-clip/20261006T193445Z-cpu)
- **siglip-zero-shot-image-classification** — ok_runs=0/3: (evidence: results/siglip-zero-shot-image-classification/20261006T202159Z-cpu)
- **yolov11-quantization-with-accuracy-control** — ok_runs=0/3: (evidence: results/yolov11-quantization-with-accuracy-control/20261006T210157Z-cpu)
- **wan2.1-text-to-video** — reclassified by comprehensive audit: CellTimeoutError present in evidence logs; original category was a classifier rule-order defect (evidence: results/wan2.1-text-to-video/20261006T211805Z-cpu)

## ⏱️ cpu · BLOCKED_TIMEOUT · TIMEOUT_MODEL_DOWNLOAD — timeout model download — 4 workload(s)

- **aloha-act** — ok_runs=0/3: (evidence: results/aloha-act/20261006T092932Z-cpu)
- **qwen-image-2.1** — ok_runs=0/3: (evidence: results/qwen-image-2.1/20261006T132040Z-cpu)
- **unlimited-ocr** — ok_runs=0/3: (evidence: results/unlimited-ocr/20261006T142458Z-cpu)
- **voxcpm2-tts** — ok_runs=0/3: (evidence: results/voxcpm2-tts/20261006T144007Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · IR_EXPORT_WRITE_IOSTREAM_ERROR — ir export write iostream error — 2 workload(s)

- **stable-diffusion-xl** — v0.3 adjudication: optimum-cli OpenVINO IR export fails in ov save_model with RuntimeError: basic_ios::clear (iostream error) — the same IR-write signature family as the v0.2.2 minicpm-o adjudication (BLOCKED_RESOURCE), (evidence: results/stable-diffusion-xl/20261008082930Z-cpu)
- **vlm-chatbot-generate-api** — v0.3 adjudication: optimum-cli OpenVINO IR export fails in ov save_model with RuntimeError: basic_ios::clear (iostream error) — the same IR-write signature family as the v0.2.2 minicpm-o adjudication (BLOCKED_RESOURCE), (evidence: results/vlm-chatbot-generate-api/20261008083427Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT — model artifact incomplete or corrupt — 2 workload(s)

- **bernini-r-image-video** — ok_runs=0/3: KeyError: 'blocks.0.attn1.to_q.weight' (evidence: results/bernini-r-image-video/20261006T211512Z-cpu)
- **multimodal-rag-llamaindex** — ok_runs=0/1: Can not open file results/multimodal-rag-llamaindex/workdir-cpu/distil-whisper-large-v3-int8-ov/openvino_decoder_model.bin for mapping. Ensure that file exists and has appropriate permissions. (evidence: results/multimodal-rag-llamaindex/20261006T224956Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · REQUIRED_HARDWARE_ABSENT — required hardware absent — 1 workload(s)

- **hello-npu** — ok_runs=0/3: Unsupported configuration key: FULL_DEVICE_NAME (evidence: results/hello-npu/20261006T090223Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · MODEL_ARTIFACT_MISSING_DIR — model artifact missing dir — 1 workload(s)

- **fastdraft_deepseek** — execution category corrected by comprehensive audit: OPENVINO_ERROR -> MODEL_ACCESS (model artifact absent at load time, not a runtime error) (evidence: results/fastdraft_deepseek/20261006T164655Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · DISK_BUDGET_EXCEEDED — disk budget exceeded — 1 workload(s)

- **qwen-image** — v0.3 adjudication: dependency root cause from v0.2.2 is FIXED on this pin (codeload transport + --no-deps fork install land; installs complete), but the workload needs ~26GB of Qwen-Image-2512 weights plus a large IR exp (evidence: results/qwen-image/20261007233531Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · MODEL_FILE_IO_FAILURE_SAVE_OR_LOAD — model file io failure save or load — 1 workload(s)

- **minicpm-o-omnimodal-chatbot** — v0.2.2 Gate-5-corrected adjudication: the basic_ios::clear iostream error was raised from ov.save_model(...) (IR WRITE path) after core.read_model and nncf.compress_weights had succeeded on the freshly downloaded ~17.4GB (evidence: results/minicpm-o-omnimodal-chatbot/20261007204800Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · DISK_EXHAUSTED_DURING_EXPORT_OPERATOR_HALTED — disk exhausted during export operator halted — 1 workload(s)

- **gemma4** — v0.3 resource adjudication: the 2b1600d-pin rerun progressed past dependency install (optimum-intel master resolved via codeload transport) into the Gemma-4-E2B OpenVINO export when the validation disk hit 100% utilizati (evidence: results/gemma4/20261008000709Z-cpu)

## 🧩 gpu · FAILED_COMPATIBILITY · CORRECTNESS — correctness — 1 workload(s)

- **hunyuan-ocr** — twin self-check failed; metrics={"model": "tencent/HunyuanOCR", "model_revision": "47644ecc4f", "correctness_level": "TASK_SEMANTIC", "correctness_contract": "OCR output contains the fixture document's actual content (as (evidence: results/hunyuan-ocr/20261008T182608Z-gpu)

## 🧩 cpu · FAILED_COMPATIBILITY · OPENVINO_RUNTIME — openvino runtime — 1 workload(s)

- **openvino-tokenizers** — ok_runs=0/3: ReadValue node with name 'ReadValue_5627'  doesn't have sibling output (evidence: results/openvino-tokenizers/20261007162645Z-cpu)


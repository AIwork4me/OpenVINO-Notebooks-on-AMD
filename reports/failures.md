# Failures (generated)

Grouped by developer-facing compatibility outcome. BLOCKED_* outcomes are environment/network/model-access blockers — not AMD/OpenVINO compatibility failures. FAILED_COMPATIBILITY rows carry a reason identifying the failing layer.

Total non-green attempts: 83

## 🌐 cpu · BLOCKED_NETWORK · NETWORK_UNREACHABLE — network unreachable — 8 workload(s)

- **freevc-voice-conversion** — ok_runs=0/3: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/models/freevc/freevc.pth (Cau (evidence: results/freevc-voice-conversion/20261007194447Z-cpu)
- **wav2lip** — ok_runs=0/1: Exception: Connection timed out. If you access the internet through a proxy server, please make sure the proxy is set in the shell from where you launched Jupyter. (evidence: results/wav2lip/20261006T190203Z-cpu)
- **ct-segmentation-quantize-nncf** — ok_runs=0/3: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/models/kidney-segmentation-ki (evidence: results/ct-segmentation-quantize-nncf/20261007200934Z-cpu)
- **yoloe-26-open-vocabulary** — ok_runs=0/1: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/data/data/image/coco_bike.jpg (evidence: results/yoloe-26-open-vocabulary/20261007200536Z-cpu)
- **gemma4** — ok_runs=0/1: ProxyError: HTTPSConnectionPool(host='github-production-user-asset-6210df.s3.amazonaws.com', port=443): Max retries exceeded with url: /29454499/319483352-d5fbbd1a-d484-415c-88cb-9986625b7b11.jpg?X-Amz-Algor (evidence: results/gemma4/20261007193418Z-cpu)
- **llm-code-assistant** — ok_runs=0/1: CalledProcessError: Command '['/workspace/.venvs/cpu/b5474a66a7540a14/bin/python', '-m', 'pip', 'install', '-q', '-U', 'gradio>=6.0.0', 'huggingface_hub', 'git+https://github.com/huggingface/optimum-intel.gi (evidence: results/llm-code-assistant/20261007183204Z-cpu)
- **muse-glimmer** — ok_runs=0/1: Exception: File downloading failed with error: HTTPSConnectionPool(host='storage.openvinotoolkit.org', port=443): Max retries exceeded with url: /repositories/openvino_notebooks/data/data/video/Coco%20Walkin (evidence: results/muse-glimmer/20261007201115Z-cpu)
- **qwen3.8-mtp** — ok_runs=0/1: URLError: <urlopen error Tunnel connection failed: 403 Forbidden> (evidence: results/qwen3.8-mtp/20261007191855Z-cpu)

## 🌐 cpu · BLOCKED_NETWORK · EXTERNAL_HOST_UNREACHABLE — external host unreachable — 5 workload(s)

- **whisper-asr-genai** — ok_runs=0/1: ConnectTimeout: HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded with url: /spaces/distil-whisper/whisper-vs-distil-whisper/resolve/main/assets/example_1.wav (Caused by ConnectTimeo (evidence: results/whisper-asr-genai/20261006T190640Z-cpu)
- **llm-agent-mcp** — ok_runs=0/3: ConnectTimeout: HTTPSConnectionPool(host='cdn-avatars.huggingface.co', port=443): Max retries exceeded with url: /v1/production/uploads/1671615670447-6346651be2dcb5422bcd13dd.png (Caused by ConnectTimeoutErr (evidence: results/llm-agent-mcp/20261006T113948Z-cpu)
- **vision-background-removal** — execution category corrected by comprehensive audit: UNKNOWN -> NETWORK (host unreachable; original UNKNOWN hid the network cause) (evidence: results/vision-background-removal/20261006T143506Z-cpu)
- **instant-id** — ok_runs=0/1: ConnectTimeout: HTTPSConnectionPool(host='drive.google.com', port=443): Max retries exceeded with url: /uc?id=18wEUfMNohBJ4K3Ly5wpTejPfDzp-8fI8 (Caused by ConnectTimeoutError(<HTTPSConnection(host='drive.goo (evidence: results/instant-id/20261006T170232Z-cpu)
- **qwen3_agent** — ok_runs=0/1: Connection error. (evidence: results/qwen3_agent/20261006T185231Z-cpu)

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

## 📦 cpu · BLOCKED_DEPENDENCY · MISSING_OR_BROKEN_DEPENDENCY — missing or broken dependency — 16 workload(s)

- **001-whisper-evaluation** — ok_runs=0/3: Please note that you may need to restart your runtime after installation. (evidence: results/001-whisper-evaluation/20261006T090407Z-cpu)
- **catvton** — ok_runs=0/3: ImportError: cannot import name 'resolve_revision' from 'huggingface_hub' (.venvs/cpu/2c24bba1924a9c98/lib/python3.12/site-packages/huggingface_hub/__init__.py) (evidence: results/catvton/20261006T095954Z-cpu)
- **glm-ocr** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'zai-org/GLM-OCR', 'GLM-OCR/INT4', '--task', 'image-text-to-text', '--weight-format', 'int4', '--group-size', '128', '--ratio', ' (evidence: results/glm-ocr/20261006T110628Z-cpu)
- **llm-rag-langchain-eval** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForCausalLM'. Are this object's requirements defined correctly? (evidence: results/llm-rag-langchain-eval/20261006T115949Z-cpu)
- **phi3_chatbot_demo** — execution category corrected by comprehensive audit: LICENSE_RESTRICTION -> DEPENDENCY (protobuf API drift, not a license restriction) (evidence: results/phi3_chatbot_demo/20261006T131146Z-cpu)
- **qwen3-asr** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForSpeechSeq2Seq'. Are this object's requirements defined correctly? (evidence: results/qwen3-asr/20261006T161620Z-cpu)
- **olmocr-pdf-vlm** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoProcessor'. Are this object's requirements defined correctly? (evidence: results/olmocr-pdf-vlm/20261007T013506Z-cpu)
- **openvoice2-and-melotts** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoTokenizer'. Are this object's requirements defined correctly? (evidence: results/openvoice2-and-melotts/20261007T013600Z-cpu)
- **qwen2.5-omni-chatbot** — ok_runs=0/1: AttributeError: type object 'openvino._pyopenvino.Type' has no attribute 'u2' (evidence: results/qwen2.5-omni-chatbot/20261006T183850Z-cpu)
- **clip-zero-shot-classification** — ok_runs=0/3: Please note that you may need to restart your runtime after installation. (evidence: results/clip-zero-shot-classification/20261006T192037Z-cpu)
- **convert-to-openvino** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'AutoModelForSequenceClassification'. Are this object's requirements defined correctly? (evidence: results/convert-to-openvino/20261006T192100Z-cpu)
- **rf-detr-object-detection** — ok_runs=0/3: ModuleNotFoundError: No module named 'triton.backends' (evidence: results/rf-detr-object-detection/20261006T201434Z-cpu)
- **z-image-turbo** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'Tongyi-MAI/Z-Image-Turbo', 'Z-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--group-size', '64', '-- (evidence: results/z-image-turbo/20261006T211426Z-cpu)
- **person-tracking** — ok_runs=0/1: ModuleNotFoundError: No module named 'deepsort_utils' (evidence: results/person-tracking/20261006T221532Z-cpu)
- **llm-rag-langchain-genai** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', 'tiny-llama-1b-chat/INT4_compressed_weights', '--task', 'text-generation-with-past', '--wei (evidence: results/llm-rag-langchain-genai/20261006T223956Z-cpu)
- **llm-rag-llamaindex** — execution category corrected by comprehensive audit: PACKAGE_CONFLICT -> DEPENDENCY (missing NLTK data resource, not a package conflict) (evidence: results/llm-rag-llamaindex/20261006T224033Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · PACKAGE_RESOLUTION_CONFLICT — package resolution conflict — 6 workload(s)

- **ernie-image** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'baidu/ERNIE-Image-Turbo', 'ERNIE-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--ratio', '0.8']' ret (evidence: results/ernie-image/20261006T101823Z-cpu)
- **funasr-nano** — ok_runs=0/3: cannot import name 'Qwen3VLForConditionalGeneration' from 'transformers' (.venvs/cpu/0e02466db943f1d6/lib/python3.12/site-packages/transformers/__init__.py) (evidence: results/funasr-nano/20261006T110542Z-cpu)
- **omniparser** — ok_runs=0/3: Exception: Connection timed out. If you access the internet through a proxy server, please make sure the proxy is set in the shell from where you launched Jupyter. (evidence: results/omniparser/20261006T122239Z-cpu)
- **qwen-image** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'Qwen/Qwen-Image-2512', 'Qwen-Image-2512/INT8', '--weight-format', 'int8']' returned non-zero exit status 1. (evidence: results/qwen-image/20261006T131310Z-cpu)
- **text-to-speech-genai** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'microsoft/speecht5_tts', 'speecht5_tts', '--model-kwargs', '{"vocoder":"microsoft/speecht5_hifigan"}']' returned non-zero exit s (evidence: results/text-to-speech-genai/20261006T142245Z-cpu)
- **flux.2-klein** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.2-klein-4B', 'FLUX.2-klein-4B/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--group-size' (evidence: results/flux.2-klein/20261006T165448Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · OPTIMUM_CLI_MISSING_OR_BROKEN — optimum cli missing or broken — 3 workload(s)

- **hunyuan-ocr** — ok_runs=0/1: ValueError: Unexpected dependency in optimum-intel/setup.py: "optimum@https://codeload.github.com/huggingface/optimum/tar.gz/HEAD" (evidence: results/hunyuan-ocr/20261007T013051Z-cpu)
- **ltx-video** — notebook changed upstream after this attempt (pre-repin evidence; content sha differs from pinned snapshot); revalidation queued with failure-retry remediation (evidence: results/ltx-video/20261006T221001Z-cpu)
- **llm-rag-langchain** — notebook changed upstream after this attempt (pre-repin evidence; content sha differs from pinned snapshot); revalidation queued with failure-retry remediation (evidence: results/llm-rag-langchain/20261006T223902Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · HARNESS_NOTEBOOK_RELATIVE_ASSET — harness notebook relative asset — 2 workload(s)

- **paddleocr_vl** — adjudicated (HARNESS_NOTEBOOK_RELATIVE_ASSET): Notebook expects sibling asset test.png; same harness notebook-relative-asset defect (fixed this closure — revalidation queued). (evidence: results/paddleocr_vl/20261006T123520Z-cpu)
- **vlm-chatbot-generate-api** — adjudicated (HARNESS_NOTEBOOK_RELATIVE_ASSET): Notebook expects sibling asset nyc.jpg; the headless kernel cwd lacked notebook-dir data files (harness defect at validation time; fixed this closure — revalidation queued). (evidence: results/vlm-chatbot-generate-api/20261006T190053Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · UPSTREAM_NOTEBOOK_RERUN_SCOPING — upstream notebook rerun scoping — 2 workload(s)

- **3d-segmentation-point-clouds** — execution category corrected by comprehensive audit: OPENVINO_ERROR -> DEPENDENCY (NameError from upstream rerun-scoping bug, not an OpenVINO runtime error) (evidence: results/3d-segmentation-point-clouds/20261006T191359Z-cpu)
- **action-recognition-webcam** — execution category corrected by comprehensive audit: UNKNOWN -> DEPENDENCY (NameError from upstream rerun-scoping bug, not an OpenVINO runtime error) (evidence: results/action-recognition-webcam/20261006T220552Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · INTERACTIVE_UI_TEARDOWN_AFTER_SKIP — interactive ui teardown after skip — 1 workload(s)

- **stable-diffusion-xl** — ok_runs=0/3: NameError: name 'demo' is not defined (evidence: results/stable-diffusion-xl/20261006T140920Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · DATASETS_API_DRIFT — datasets api drift — 1 workload(s)

- **phi3_rag_on_client** — execution category corrected by comprehensive audit: MODEL_ACCESS -> DEPENDENCY (datasets API drift, not model access) (evidence: results/phi3_rag_on_client/20261006T131159Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · OPTIMUM_EXPORT_FAILED_ROOT_CAUSE_NOT_CAPTURED — optimum export failed root cause not captured — 1 workload(s)

- **glm4.1-v-thinking** — adjudicated (OPTIMUM_EXPORT_FAILED_ROOT_CAUSE_NOT_CAPTURED): optimum-cli was present and ran; the export subprocess failed (exit 1) with its stderr swallowed by cmd_helper's capture_output (upstream helper limitation, fi (evidence: results/glm4.1-v-thinking/20261006T165509Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · TRANSFORMERS_API_DRIFT — transformers api drift — 1 workload(s)

- **minicpm-o-4.5** — execution category corrected by comprehensive audit: PACKAGE_CONFLICT -> DEPENDENCY (transformers API drift, not a package conflict) (evidence: results/minicpm-o-4.5/20261006T171910Z-cpu)

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

## 💾 cpu · BLOCKED_RESOURCE · MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT — model artifact incomplete or corrupt — 3 workload(s)

- **minicpm-o-omnimodal-chatbot** — ok_runs=0/1: FileNotFoundError: No such file or directory: MiniCPM-o-2_6/ckpt/model-00001-of-00004.safetensors (evidence: results/minicpm-o-omnimodal-chatbot/20261006T171938Z-cpu)
- **bernini-r-image-video** — ok_runs=0/3: KeyError: 'blocks.0.attn1.to_q.weight' (evidence: results/bernini-r-image-video/20261006T211512Z-cpu)
- **multimodal-rag-llamaindex** — ok_runs=0/1: Can not open file results/multimodal-rag-llamaindex/workdir-cpu/distil-whisper-large-v3-int8-ov/openvino_decoder_model.bin for mapping. Ensure that file exists and has appropriate permissions. (evidence: results/multimodal-rag-llamaindex/20261006T224956Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · REQUIRED_HARDWARE_ABSENT — required hardware absent — 1 workload(s)

- **hello-npu** — ok_runs=0/3: Unsupported configuration key: FULL_DEVICE_NAME (evidence: results/hello-npu/20261006T090223Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · MODEL_ARTIFACT_MISSING_DIR — model artifact missing dir — 1 workload(s)

- **fastdraft_deepseek** — execution category corrected by comprehensive audit: OPENVINO_ERROR -> MODEL_ACCESS (model artifact absent at load time, not a runtime error) (evidence: results/fastdraft_deepseek/20261006T164655Z-cpu)

## 🧩 cpu · FAILED_COMPATIBILITY · OPENVINO_RUNTIME — openvino runtime — 1 workload(s)

- **openvino-tokenizers** — ok_runs=0/3: ReadValue node with name 'ReadValue_5627'  doesn't have sibling output (evidence: results/openvino-tokenizers/20261007162645Z-cpu)


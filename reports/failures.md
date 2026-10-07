# Failures (generated)

Grouped by developer-facing compatibility outcome. BLOCKED_* outcomes are environment/network/model-access blockers — not AMD/OpenVINO compatibility failures. FAILED_COMPATIBILITY rows carry a reason identifying the failing layer.

Total non-green attempts: 85

## 🌐 cpu · BLOCKED_NETWORK · EXTERNAL_HOST_UNREACHABLE — external host unreachable — 5 workload(s)

- **whisper-asr-genai** — ok_runs=0/1: ConnectTimeout: HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded with url: /spaces/distil-whisper/whisper-vs-distil-whisper/resolve/main/assets/example_1.wav (Caused by Co (evidence: results/whisper-asr-genai/20261006T190640Z-cpu)
- **llm-agent-mcp** — ok_runs=0/3: ConnectTimeout: HTTPSConnectionPool(host='cdn-avatars.huggingface.co', port=443): Max retries exceeded with url: /v1/production/uploads/1671615670447-6346651be2dcb5422bcd13dd.png (Caused by Connect (evidence: results/llm-agent-mcp/20261006T113948Z-cpu)
- **vision-background-removal** — execution category corrected by comprehensive audit: UNKNOWN -> NETWORK (host unreachable; original UNKNOWN hid the network cause) (evidence: results/vision-background-removal/20261006T143506Z-cpu)
- **instant-id** — ok_runs=0/1: ConnectTimeout: HTTPSConnectionPool(host='drive.google.com', port=443): Max retries exceeded with url: /uc?id=18wEUfMNohBJ4K3Ly5wpTejPfDzp-8fI8 (Caused by ConnectTimeoutError(<HTTPSConnection(host= (evidence: results/instant-id/20261006T170232Z-cpu)
- **qwen3_agent** — ok_runs=0/1: Connection error. (evidence: results/qwen3_agent/20261006T185231Z-cpu)

## 🌐 cpu · BLOCKED_NETWORK · NETWORK_UNREACHABLE — network unreachable — 1 workload(s)

- **wav2lip** — ok_runs=0/1: Exception: Connection timed out. If you access the internet through a proxy server, please make sure the proxy is set in the shell from where you launched Jupyter. (evidence: results/wav2lip/20261006T190203Z-cpu)

## 🔐 cpu · BLOCKED_MODEL_ACCESS · GATED_OR_RESTRICTED_MODEL — gated or restricted model — 4 workload(s)

- **cosyvoice3-tts** — ok_runs=0/3: HTTPError: Authentication token does not exist, (evidence: results/cosyvoice3-tts/20261007T012002Z-cpu)
- **medasr-medical-asr** — ok_runs=0/3: Access to model google/medasr is restricted and you are not in the authorized list. Visit https://huggingface.co/google/medasr to ask for access. (evidence: results/medasr-medical-asr/20261006T120126Z-cpu)
- **mllama-3.2** — ok_runs=0/1: Access to model meta-llama/Llama-3.2-11B-Vision-Instruct is restricted and you are not in the authorized list. Visit https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct to ask for access. (evidence: results/mllama-3.2/20261006T174315Z-cpu)
- **stable-diffusion-v3-torch-fx** — ok_runs=0/1: Access to model stabilityai/stable-diffusion-3-medium-diffusers is restricted and you are not in the authorized list. Visit https://huggingface.co/stabilityai/stable-diffusion-3-medium-diffusers to ask for a (evidence: results/stable-diffusion-v3-torch-fx/20261006T190007Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · OPTIMUM_CLI_MISSING_OR_BROKEN — optimum cli missing or broken — 17 workload(s)

- **ernie-image** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'baidu/ERNIE-Image-Turbo', 'ERNIE-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--ratio', ' (evidence: results/ernie-image/20261006T101823Z-cpu)
- **glm-ocr** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'zai-org/GLM-OCR', 'GLM-OCR/INT4', '--task', 'image-text-to-text', '--weight-format', 'int4', '--group-size', '128', '- (evidence: results/glm-ocr/20261006T110628Z-cpu)
- **latent-consistency-models-image-generation** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'SimianLuo/LCM_Dreamshaper_v7', 'LCM_Dreamshaper_v7_ov', '--weight-format', 'fp16']' returned non-zero exit status 1. (evidence: results/latent-consistency-models-image-generation/20261006T113723Z-cpu)
- **llm-rag-langchain-eval** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForCausalLM'. Are this object's requirements defined correctly? (evidence: results/llm-rag-langchain-eval/20261006T115949Z-cpu)
- **phi3_chatbot_demo** — execution category corrected by comprehensive audit: LICENSE_RESTRICTION -> DEPENDENCY (protobuf API drift, not a license restriction) (evidence: results/phi3_chatbot_demo/20261006T131146Z-cpu)
- **qwen-image** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'Qwen/Qwen-Image-2512', 'Qwen-Image-2512/INT8', '--weight-format', 'int8']' returned non-zero exit status 1. (evidence: results/qwen-image/20261006T131310Z-cpu)
- **text-to-speech-genai** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'microsoft/speecht5_tts', 'speecht5_tts', '--model-kwargs', '{"vocoder":"microsoft/speecht5_hifigan"}']' returned non-z (evidence: results/text-to-speech-genai/20261006T142245Z-cpu)
- **qwen3-asr** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForSpeechSeq2Seq'. Are this object's requirements defined correctly? (evidence: results/qwen3-asr/20261006T161620Z-cpu)
- **flux-fill** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.1-Fill-dev', 'FLUX.1-Fill-dev/INT4', '--weight-format', 'int4', '--group-size', '64', '--ratio' (evidence: results/flux-fill/20261006T164829Z-cpu)
- **flux.1-kontext** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.1-Kontext-dev', 'FLUX.1-Kontext-dev/INT4', '--weight-format', 'int4', '--group-size', '64', '-- (evidence: results/flux.1-kontext/20261006T165218Z-cpu)
- **flux.2-klein** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.2-klein-4B', 'FLUX.2-klein-4B/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--g (evidence: results/flux.2-klein/20261006T165448Z-cpu)
- **glm4.1-v-thinking** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'GLM-4.1V-9B-Thinking', 'GLM-4.1V-9B-Thinking/INT4', '--task', 'image-text-to-text', '--weight-format', 'int4', '--grou (evidence: results/glm4.1-v-thinking/20261006T165509Z-cpu)
- **z-image-turbo** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'Tongyi-MAI/Z-Image-Turbo', 'Z-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--group-size', (evidence: results/z-image-turbo/20261006T211426Z-cpu)
- **ltx-video** — ok_runs=0/1: FileNotFoundError: [Errno 2] No such file or directory: 'optimum-cli' (evidence: results/ltx-video/20261006T221001Z-cpu)
- **llm-rag-langchain** — ok_runs=0/1: ImportError: Could not import optimum-intel python package. Please install it with: pip install -U 'optimum[openvino,nncf]' (evidence: results/llm-rag-langchain/20261006T223902Z-cpu)
- **llm-rag-langchain-genai** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', 'tiny-llama-1b-chat/INT4_compressed_weights', '--task', 'text-generation-with-pas (evidence: results/llm-rag-langchain-genai/20261006T223956Z-cpu)
- **multimodal-rag-llamaindex** — ok_runs=0/1: Can not open file results/multimodal-rag-llamaindex/workdir-cpu/distil-whisper-large-v3-int8-ov/openvino_decoder_model.bin for mapping. Ensure that file exists and (evidence: results/multimodal-rag-llamaindex/20261006T224956Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · MISSING_OR_BROKEN_DEPENDENCY — missing or broken dependency — 10 workload(s)

- **001-whisper-evaluation** — ok_runs=0/3: Please note that you may need to restart your runtime after installation. (evidence: results/001-whisper-evaluation/20261006T090407Z-cpu)
- **catvton** — ok_runs=0/3: ImportError: cannot import name 'resolve_revision' from 'huggingface_hub' (.venvs/cpu/2c24bba1924a9c98/lib/python3.12/site-packages/huggingface_hub/__ini (evidence: results/catvton/20261006T095954Z-cpu)
- **hunyuan-ocr** — ok_runs=0/1: ValueError: Unexpected dependency in optimum-intel/setup.py: "optimum@https://codeload.github.com/huggingface/optimum/tar.gz/HEAD" (evidence: results/hunyuan-ocr/20261007T013051Z-cpu)
- **olmocr-pdf-vlm** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoProcessor'. Are this object's requirements defined correctly? (evidence: results/olmocr-pdf-vlm/20261007T013506Z-cpu)
- **openvoice2-and-melotts** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoTokenizer'. Are this object's requirements defined correctly? (evidence: results/openvoice2-and-melotts/20261007T013600Z-cpu)
- **qwen2.5-omni-chatbot** — ok_runs=0/1: AttributeError: type object 'openvino._pyopenvino.Type' has no attribute 'u2' (evidence: results/qwen2.5-omni-chatbot/20261006T183850Z-cpu)
- **clip-zero-shot-classification** — ok_runs=0/3: Please note that you may need to restart your runtime after installation. (evidence: results/clip-zero-shot-classification/20261006T192037Z-cpu)
- **convert-to-openvino** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'AutoModelForSequenceClassification'. Are this object's requirements defined correctly? (evidence: results/convert-to-openvino/20261006T192100Z-cpu)
- **rf-detr-object-detection** — ok_runs=0/3: ModuleNotFoundError: No module named 'triton.backends' (evidence: results/rf-detr-object-detection/20261006T201434Z-cpu)
- **person-tracking** — ok_runs=0/1: ModuleNotFoundError: No module named 'deepsort_utils' (evidence: results/person-tracking/20261006T221532Z-cpu)

## 📦 cpu · BLOCKED_DEPENDENCY · PACKAGE_RESOLUTION_CONFLICT — package resolution conflict — 3 workload(s)

- **funasr-nano** — ok_runs=0/3: cannot import name 'Qwen3VLForConditionalGeneration' from 'transformers' (.venvs/cpu/0e02466db943f1d6/lib/python3.12/site-packages/transformers/__init__.py) (evidence: results/funasr-nano/20261006T110542Z-cpu)
- **omniparser** — ok_runs=0/3: Exception: Connection timed out. If you access the internet through a proxy server, please make sure the proxy is set in the shell from where you launched Jupyter. (evidence: results/omniparser/20261006T122239Z-cpu)
- **llm-rag-llamaindex** — execution category corrected by comprehensive audit: PACKAGE_CONFLICT -> DEPENDENCY (missing NLTK data resource, not a package conflict) (evidence: results/llm-rag-llamaindex/20261006T224033Z-cpu)

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

## 📦 cpu · BLOCKED_DEPENDENCY · TRANSFORMERS_API_DRIFT — transformers api drift — 1 workload(s)

- **minicpm-o-4.5** — execution category corrected by comprehensive audit: PACKAGE_CONFLICT -> DEPENDENCY (transformers API drift, not a package conflict) (evidence: results/minicpm-o-4.5/20261006T171910Z-cpu)

## ⏱️ cpu · BLOCKED_TIMEOUT · TIMEOUT_INFERENCE — timeout inference — 10 workload(s)

- **bark-text-to-audio** — ok_runs=0/3:  (evidence: results/bark-text-to-audio/20261006T093939Z-cpu)
- **stable-diffusion-text-to-image** — ok_runs=0/3:  (evidence: results/stable-diffusion-text-to-image/20261006T135916Z-cpu)
- **grounded-segment-anything** — ok_runs=0/3:  (evidence: results/grounded-segment-anything/20261006T111645Z-cpu)
- **inpainting-genai** — ok_runs=0/3:  (evidence: results/inpainting-genai/20261006T112649Z-cpu)
- **minicpm-v-multimodal-chatbot** — ok_runs=0/3:  (evidence: results/minicpm-v-multimodal-chatbot/20261006T120232Z-cpu)
- **music-generation** — ok_runs=0/3:  (evidence: results/music-generation/20261006T121236Z-cpu)
- **phi-3-vision** — ok_runs=0/3:  (evidence: results/phi-3-vision/20261006T125136Z-cpu)
- **phi-4-multimodal** — ok_runs=0/3:  (evidence: results/phi-4-multimodal/20261006T130140Z-cpu)
- **text-to-image-genai** — ok_runs=0/3:  (evidence: results/text-to-image-genai/20261006T141238Z-cpu)
- **controlnet-stable-diffusion** — reclassified by comprehensive audit: CellTimeoutError present in evidence logs; original category was a classifier rule-order defect (evidence: results/controlnet-stable-diffusion/20261006T163110Z-cpu)

## ⏱️ cpu · BLOCKED_TIMEOUT · TIMEOUT_CONVERSION_EXPORT — timeout conversion export — 8 workload(s)

- **blip-visual-language-processing** — ok_runs=0/3:  (evidence: results/blip-visual-language-processing/20261006T094947Z-cpu)
- **deepseek-vl2** — ok_runs=0/3:  (evidence: results/deepseek-vl2/20261006T100820Z-cpu)
- **fireredtts2** — ok_runs=0/3:  (evidence: results/fireredtts2/20261006T102342Z-cpu)
- **omnivoice** — ok_runs=0/3:  (evidence: results/omnivoice/20261006T122427Z-cpu)
- **jina-clip** — ok_runs=0/3:  (evidence: results/jina-clip/20261006T193445Z-cpu)
- **siglip-zero-shot-image-classification** — ok_runs=0/3:  (evidence: results/siglip-zero-shot-image-classification/20261006T202159Z-cpu)
- **yolov11-quantization-with-accuracy-control** — ok_runs=0/3:  (evidence: results/yolov11-quantization-with-accuracy-control/20261006T210157Z-cpu)
- **wan2.1-text-to-video** — reclassified by comprehensive audit: CellTimeoutError present in evidence logs; original category was a classifier rule-order defect (evidence: results/wan2.1-text-to-video/20261006T211805Z-cpu)

## ⏱️ cpu · BLOCKED_TIMEOUT · TIMEOUT_MODEL_DOWNLOAD — timeout model download — 4 workload(s)

- **aloha-act** — ok_runs=0/3:  (evidence: results/aloha-act/20261006T092932Z-cpu)
- **qwen-image-2.1** — ok_runs=0/3:  (evidence: results/qwen-image-2.1/20261006T132040Z-cpu)
- **unlimited-ocr** — ok_runs=0/3:  (evidence: results/unlimited-ocr/20261006T142458Z-cpu)
- **voxcpm2-tts** — ok_runs=0/3:  (evidence: results/voxcpm2-tts/20261006T144007Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · MODEL_ARTIFACT_INCOMPLETE_OR_CORRUPT — model artifact incomplete or corrupt — 9 workload(s)

- **freevc-voice-conversion** — ok_runs=0/3: RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory (evidence: results/freevc-voice-conversion/20261006T110446Z-cpu)
- **flux.1-image-generation** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found! (evidence: results/flux.1-image-generation/20261006T165049Z-cpu)
- **minicpm-o-omnimodal-chatbot** — ok_runs=0/1: FileNotFoundError: No such file or directory: MiniCPM-o-2_6/ckpt/model-00001-of-00004.safetensors (evidence: results/minicpm-o-omnimodal-chatbot/20261006T171938Z-cpu)
- **bernini-r-image-video** — ok_runs=0/3: KeyError: 'blocks.0.attn1.to_q.weight' (evidence: results/bernini-r-image-video/20261006T211512Z-cpu)
- **yoloe-26-open-vocabulary** — ok_runs=0/1: RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory (evidence: results/yoloe-26-open-vocabulary/20261006T222944Z-cpu)
- **gemma4** — ok_runs=0/1: ; (evidence: results/gemma4/20261006T223734Z-cpu)
- **llm-code-assistant** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found! (evidence: results/llm-code-assistant/20261006T223847Z-cpu)
- **muse-glimmer** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found! (evidence: results/muse-glimmer/20261006T225336Z-cpu)
- **qwen3.8-mtp** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found! (evidence: results/qwen3.8-mtp/20261006T225549Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · REQUIRED_HARDWARE_ABSENT — required hardware absent — 1 workload(s)

- **hello-npu** — ok_runs=0/3: Unsupported configuration key: FULL_DEVICE_NAME (evidence: results/hello-npu/20261006T090223Z-cpu)

## 💾 cpu · BLOCKED_RESOURCE · MODEL_ARTIFACT_MISSING_DIR — model artifact missing dir — 1 workload(s)

- **fastdraft_deepseek** — execution category corrected by comprehensive audit: OPENVINO_ERROR -> MODEL_ACCESS (model artifact absent at load time, not a runtime error) (evidence: results/fastdraft_deepseek/20261006T164655Z-cpu)

## 🧩 cpu · FAILED_COMPATIBILITY · OPENVINO_RUNTIME — openvino runtime — 2 workload(s)

- **parler-tts-text-to-speech** — ok_runs=0/3: BrgemmCPU node has incompatible input element types: f32 and bf16 (evidence: results/parler-tts-text-to-speech/20261007T024813Z-cpu)
- **openvino-tokenizers** — ok_runs=0/3: ReadValue node with name 'ReadValue_5627'  doesn't have sibling output (evidence: results/openvino-tokenizers/20261006T211720Z-cpu)

## 🧩 cpu · FAILED_COMPATIBILITY · OPENVINO_RUNTIME_CL_MAP — openvino runtime cl map — 1 workload(s)

- **qwen3** — execution category corrected by comprehensive audit: UNKNOWN -> OPENVINO_ERROR (OpenVINO runtime CL error, not UNKNOWN) (evidence: results/qwen3/20261006T183929Z-cpu)

## 🧩 cpu · FAILED_COMPATIBILITY · KERNEL_DEATH_UNDIAGNOSED — kernel death undiagnosed — 1 workload(s)

- **ct-segmentation-quantize-nncf** — adjudicated (KERNEL_DEATH_UNDIAGNOSED): nbclient DeadKernelError during NNCF quantization; no OOM/kernel-log proof either way. Genuine unresolved failure with a valid environment — kept as compatibility failure, RCA cand (evidence: results/ct-segmentation-quantize-nncf/20261006T192227Z-cpu)

## 🧩 cpu · FAILED_COMPATIBILITY · OPENVINO_RUNTIME_DEVICE_ENUM — openvino runtime device enum — 1 workload(s)

- **gpu-device** — adjudicated (OPENVINO_RUNTIME_DEVICE_ENUM): nbclient DeadKernelError while enumerating OpenVINO devices with an AMD Radeon iGPU present; unresolved — kept as compatibility failure, RCA candidate. (evidence: results/gpu-device/20261006T220955Z-cpu)


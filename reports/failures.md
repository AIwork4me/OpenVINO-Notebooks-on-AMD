# Failures (generated)

Total failed attempts: 87

## cpu:TIMEOUT — 20 workload(s)

- **aloha-act** — ok_runs=0/3: 
- **bark-text-to-audio** — ok_runs=0/3: 
- **blip-visual-language-processing** — ok_runs=0/3: 
- **deepseek-vl2** — ok_runs=0/3: 
- **fireredtts2** — ok_runs=0/3: 
- **stable-diffusion-text-to-image** — ok_runs=0/3: 
- **grounded-segment-anything** — ok_runs=0/3: 
- **inpainting-genai** — ok_runs=0/3: 
- **minicpm-v-multimodal-chatbot** — ok_runs=0/3: 
- **music-generation** — ok_runs=0/3: 
- **omnivoice** — ok_runs=0/3: 
- **phi-3-vision** — ok_runs=0/3: 
- **phi-4-multimodal** — ok_runs=0/3: 
- **qwen-image-2.1** — ok_runs=0/3: 
- **text-to-image-genai** — ok_runs=0/3: 
- **unlimited-ocr** — ok_runs=0/3: 
- **voxcpm2-tts** — ok_runs=0/3: 
- **jina-clip** — ok_runs=0/3: 
- **siglip-zero-shot-image-classification** — ok_runs=0/3: 
- **yolov11-quantization-with-accuracy-control** — ok_runs=0/3: 

## cpu:DEPENDENCY — 17 workload(s)

- **001-whisper-evaluation** — ok_runs=0/3: Please note that you may need to restart your runtime after installation.
- **catvton** — ok_runs=0/3: ImportError: cannot import name 'resolve_revision' from 'huggingface_hub' (.venvs/cpu/2c24bba1924a9c98/lib/python3.12/site-packages/huggingface_hub/__ini
- **glm-ocr** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'zai-org/GLM-OCR', 'GLM-OCR/INT4', '--task', 'image-text-to-text', '--weight-format', 'int4', '--group-size', '128', '-
- **llm-rag-langchain-eval** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForCausalLM'. Are this object's requirements defined correctly?
- **qwen3-asr** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'OVModelForSpeechSeq2Seq'. Are this object's requirements defined correctly?
- **hunyuan-ocr** — ok_runs=0/1: ValueError: Unexpected dependency in optimum-intel/setup.py: "optimum@https://codeload.github.com/huggingface/optimum/tar.gz/HEAD"
- **olmocr-pdf-vlm** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoProcessor'. Are this object's requirements defined correctly?
- **openvoice2-and-melotts** — ok_runs=0/1: ModuleNotFoundError: Could not import module 'AutoTokenizer'. Are this object's requirements defined correctly?
- **qwen2.5-omni-chatbot** — ok_runs=0/1: AttributeError: type object 'openvino._pyopenvino.Type' has no attribute 'u2'
- **clip-zero-shot-classification** — ok_runs=0/3: Please note that you may need to restart your runtime after installation.
- **convert-to-openvino** — ok_runs=0/3: ModuleNotFoundError: Could not import module 'AutoModelForSequenceClassification'. Are this object's requirements defined correctly?
- **rf-detr-object-detection** — ok_runs=0/3: ModuleNotFoundError: No module named 'triton.backends'
- **z-image-turbo** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'Tongyi-MAI/Z-Image-Turbo', 'Z-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--group-size',
- **ltx-video** — ok_runs=0/1: FileNotFoundError: [Errno 2] No such file or directory: 'optimum-cli'
- **person-tracking** — ok_runs=0/1: ModuleNotFoundError: No module named 'deepsort_utils'
- **llm-rag-langchain** — ok_runs=0/1: ImportError: Could not import optimum-intel python package. Please install it with: pip install -U 'optimum[openvino,nncf]'
- **llm-rag-langchain-genai** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0', 'tiny-llama-1b-chat/INT4_compressed_weights', '--task', 'text-generation-with-pas

## cpu:UNKNOWN — 14 workload(s)

- **cosyvoice3-tts** — ok_runs=0/3: HTTPError: Authentication token does not exist,
- **qwen3** — ok_runs=0/1: [GPU] clEnqueueMapBuffer, error code: -30 CL_INVALID_VALUE
- **stable-diffusion-xl** — ok_runs=0/3: NameError: name 'demo' is not defined
- **vision-background-removal** — ok_runs=0/3: EOFError:
- **flux.1-image-generation** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found!
- **glm4.1-v-thinking** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'GLM-4.1V-9B-Thinking', 'GLM-4.1V-9B-Thinking/INT4', '--task', 'image-text-to-text', '--weight-format', 'int4', '--grou
- **minicpm-o-omnimodal-chatbot** — ok_runs=0/1: FileNotFoundError: No such file or directory: MiniCPM-o-2_6/ckpt/model-00001-of-00004.safetensors
- **vlm-chatbot-generate-api** — ok_runs=0/1: FileNotFoundError: [Errno 2] No such file or directory: 'nyc.jpg'
- **bernini-r-image-video** — ok_runs=0/3: KeyError: 'blocks.0.attn1.to_q.weight'
- **action-recognition-webcam** — ok_runs=0/1: NameError: name 'vocab_file_path' is not defined
- **yoloe-26-open-vocabulary** — ok_runs=0/1: RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory
- **gemma4** — ok_runs=0/1: ;
- **muse-glimmer** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found!
- **qwen3.8-mtp** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found!

## cpu:PACKAGE_CONFLICT — 11 workload(s)

- **ernie-image** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'baidu/ERNIE-Image-Turbo', 'ERNIE-Image-Turbo/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--ratio', '
- **funasr-nano** — ok_runs=0/3: cannot import name 'Qwen3VLForConditionalGeneration' from 'transformers' (.venvs/cpu/0e02466db943f1d6/lib/python3.12/site-packages/transformers/__init__.py)
- **omniparser** — ok_runs=0/3: Exception: Connection timed out. If you access the internet through a proxy server, please make sure the proxy is set in the shell from where you launched Jupyter.
- **paddleocr_vl** — ok_runs=0/3: FileNotFoundError: [Errno 2] No such file or directory: 'results/paddleocr_vl/workdir-cpu/test.png'
- **qwen-image** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'Qwen/Qwen-Image-2512', 'Qwen-Image-2512/INT8', '--weight-format', 'int8']' returned non-zero exit status 1.
- **text-to-speech-genai** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'microsoft/speecht5_tts', 'speecht5_tts', '--model-kwargs', '{"vocoder":"microsoft/speecht5_hifigan"}']' returned non-z
- **controlnet-stable-diffusion** — ok_runs=0/1: -------------------
- **flux.2-klein** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.2-klein-4B', 'FLUX.2-klein-4B/INT4', '--task', 'text-to-image', '--weight-format', 'int4', '--g
- **minicpm-o-4.5** — ok_runs=0/1: AttributeError: MiniCPMOTokenizerFast has no attribute tokenizer
- **llm-code-assistant** — ok_runs=0/1: Empty weights data in bin file or bin file cannot be found!
- **llm-rag-llamaindex** — ok_runs=0/1: **********************************************************************

## cpu:MODEL_ACCESS — 8 workload(s)

- **latent-consistency-models-image-generation** — ok_runs=0/3: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'SimianLuo/LCM_Dreamshaper_v7', 'LCM_Dreamshaper_v7_ov', '--weight-format', 'fp16']' returned non-zero exit status 1.
- **medasr-medical-asr** — ok_runs=0/3: Access to model google/medasr is restricted and you are not in the authorized list. Visit https://huggingface.co/google/medasr to ask for access.
- **phi3_rag_on_client** — ok_runs=0/3: AttributeError: 'Column' object has no attribute 'dtype'
- **flux-fill** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.1-Fill-dev', 'FLUX.1-Fill-dev/INT4', '--weight-format', 'int4', '--group-size', '64', '--ratio'
- **flux.1-kontext** — ok_runs=0/1: CalledProcessError: Command '['optimum-cli', 'export', 'openvino', '--model', 'black-forest-labs/FLUX.1-Kontext-dev', 'FLUX.1-Kontext-dev/INT4', '--weight-format', 'int4', '--group-size', '64', '--
- **mllama-3.2** — ok_runs=0/1: Access to model meta-llama/Llama-3.2-11B-Vision-Instruct is restricted and you are not in the authorized list. Visit https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct to ask for access.
- **stable-diffusion-v3-torch-fx** — ok_runs=0/1: Access to model stabilityai/stable-diffusion-3-medium-diffusers is restricted and you are not in the authorized list. Visit https://huggingface.co/stabilityai/stable-diffusion-3-medium-diffusers to ask for a
- **multimodal-rag-llamaindex** — ok_runs=0/1: Can not open file results/multimodal-rag-llamaindex/workdir-cpu/distil-whisper-large-v3-int8-ov/openvino_decoder_model.bin for mapping. Ensure that file exists and

## cpu:OPENVINO_ERROR — 7 workload(s)

- **hello-npu** — ok_runs=0/3: Unsupported configuration key: FULL_DEVICE_NAME
- **fastdraft_deepseek** — ok_runs=0/1: Could not find a model in the directory '"DeepSeek-R1-Distill-Llama-8B-int4-ov"'
- **parler-tts-text-to-speech** — ok_runs=0/3: BrgemmCPU node has incompatible input element types: f32 and bf16
- **3d-segmentation-point-clouds** — ok_runs=0/3: NameError: name 'point_data' is not defined
- **ct-segmentation-quantize-nncf** — ok_runs=0/3: nbclient.exceptions.DeadKernelError: Kernel died
- **openvino-tokenizers** — ok_runs=0/3: ReadValue node with name 'ReadValue_5627'  doesn't have sibling output
- **gpu-device** — ok_runs=0/1: nbclient.exceptions.DeadKernelError: Kernel died

## cpu:NETWORK — 6 workload(s)

- **whisper-asr-genai** — ok_runs=0/1: ConnectTimeout: HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded with url: /spaces/distil-whisper/whisper-vs-distil-whisper/resolve/main/assets/example_1.wav (Caused by Co
- **llm-agent-mcp** — ok_runs=0/3: ConnectTimeout: HTTPSConnectionPool(host='cdn-avatars.huggingface.co', port=443): Max retries exceeded with url: /v1/production/uploads/1671615670447-6346651be2dcb5422bcd13dd.png (Caused by Connect
- **instant-id** — ok_runs=0/1: ConnectTimeout: HTTPSConnectionPool(host='drive.google.com', port=443): Max retries exceeded with url: /uc?id=18wEUfMNohBJ4K3Ly5wpTejPfDzp-8fI8 (Caused by ConnectTimeoutError(<HTTPSConnection(host=
- **qwen3_agent** — ok_runs=0/1: Connection error.
- **wav2lip** — ok_runs=0/1: Exception: Connection timed out. If you access the internet through a proxy server, please make sure the proxy is set in the shell from where you launched Jupyter.
- **wan2.1-text-to-video** — ok_runs=0/3: -------------------

## cpu:CORRECTNESS_ERROR — 2 workload(s)

- **person-counting** — {"output_contains": {"processing has been successfully completed": true, "yolov8n_openvino_model": false}, "no_cell_error": true, "skipped_cells": 0}
- **stable-video-diffusion** — {"output_contains": {"successfully converted to IR and saved to model/": false, "compression rate: \\d+\\.\\d+": true, "Running on local URL": true}, "no_cell_error": true, "skipped_cells": 1}

## cpu:CONVERSION_ERROR — 1 workload(s)

- **freevc-voice-conversion** — ok_runs=0/3: RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory

## cpu:LICENSE_RESTRICTION — 1 workload(s)

- **phi3_chatbot_demo** — ok_runs=0/3: cannot import name 'runtime_version' from 'google.protobuf' (.venvs/cpu/0e02466db943f1d6/lib/python3.12/site-packages/google/protobuf/__init__.py)


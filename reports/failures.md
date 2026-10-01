# Failures (generated)

Total failed attempts: 23

## cpu:DEPENDENCY — 8 workload(s)

- **openvino-api** — ok_runs=0/3: [31mModuleNotFoundError[39m: No module named 'kagglehub'
- **001-whisper-evaluation** — ok_runs=0/3: [31mModuleNotFoundError[39m: No module named 'optimum.intel'
- **ace-step-music-generation** — ok_runs=0/3: [31mCalledProcessError[39m: Command '['/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/.venv-cpu/bin/python', '-m', 'pip', 'install', 'gradio>=4.19']' returned non-zero exit status 1.
- **aloha-act** — ok_runs=0/3: [31mCalledProcessError[39m: Command '['/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/.venv-cpu/bin/python', '-m', 'pip', 'install', '-q', 'ipywidgets']' returned non-zero exit status 1.
- **animate-anyone** — ok_runs=0/3: [31mModuleNotFoundError[39m: No module named 'torchvision'
- **bark-text-to-audio** — ok_runs=0/3: [31mModuleNotFoundError[39m: No module named 'bark'
- **catvton** — ok_runs=0/3: [31mModuleNotFoundError[39m: No module named 'ov_catvton_helper'
- **cosyvoice3-tts** — ok_runs=0/3: [31mCalledProcessError[39m: Command '['/home/amd/Desktop/OpenVINO-Notebooks-on-AMD/.venv-cpu/bin/python', '-m', 'pip', 'install', '-q', '--extra-index-url', 'https://download.pytorch.org/whl/cpu', 'setupto

## cpu:TIMEOUT — 7 workload(s)

- **darkir-image-restoration** — ok_runs=0/3: 
- **deepseek-ocr** — ok_runs=0/3: 
- **deepseek-r1** — ok_runs=0/3: 
- **ernie-image** — ok_runs=0/3: 
- **freevc-voice-conversion** — ok_runs=0/3: 
- **funasr-nano** — ok_runs=0/3: 
- **glm-ocr** — ok_runs=0/3: 

## cpu:OPENVINO_ERROR — 3 workload(s)

- **hello-npu** — ok_runs=0/3: Unsupported configuration key: FULL_DEVICE_NAME
- **deepseek-vl2** — ok_runs=0/3: [31mCalledProcessError[39m: Command '['git', 'clone', 'https://github.com/deepseek-ai/DeepSeek-VL2.git']' returned non-zero exit status 128.
- **fastdraft_deepseek** — ok_runs=0/3: Could not find a model in the directory '"DeepSeek-R1-Distill-Llama-8B-int4-ov"'

## cpu:CONVERSION_ERROR — 1 workload(s)

- **blip-visual-language-processing** — ok_runs=0/3: [31mError[39m: Unexpected type of example_input. Supported types torch.Tensor, np.array or ov.Tensor. Got <class 'transformers.cache_utils.EncoderDecoderCache'>

## cpu:PACKAGE_CONFLICT — 1 workload(s)

- **fireredtts2** — ok_runs=0/3: [31mCalledProcessError[39m: Command '['git', 'clone', 'https://github.com/openvino-dev-samples/FireRedTTS2.git']' returned non-zero exit status 128.

## cpu:NETWORK — 1 workload(s)

- **flex.2-image-generation** — ok_runs=0/3: [31mConnectTimeout[39m: HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded with url: /spaces/VIDraft/Flex-preview/resolve/main/pipeline.py (Caused by ConnectTimeoutError(<HTTPSConne

## cpu:UNKNOWN — 1 workload(s)

- **florence2** — ok_runs=0/3: 

## gpu:CORRECTNESS_ERROR — 1 workload(s)

- **kokoro** — twin self-check failed; metrics={"model": "hexgrad/Kokoro-82M", "precision": "default (model dtype)", "load_s": 584.12, "runs": [{"latency_s": 0.62, "audio_s": 3.25, "rtf": 5.24}, {"latency_s": 0.637, "audio_s": 3.25, "r


# Full 173-Entry Integrity Audit (generated)

Generated: 2026-10-07T20:47:18+00:00 · pin `5f0b2b5f63fd`

Verdicts: {'OK': 166, 'FAIL': 4, 'WARN': 3}

## Critical anomalies

- flux.1-image-generation: yellow without limitation codes
- llm-chatbot-generate-api: yellow without limitation codes
- llm-chatbot: yellow without limitation codes
- qwen3: yellow without limitation codes

## Warnings

- llm-rag-langchain: pre-repin evidence on changed notebook; revalidation queued (noted)
- ltx-video: pre-repin evidence on changed notebook; revalidation queued (noted)
- segment-anything-2-video: pre-repin evidence on changed notebook; revalidation queued (noted)

## Per-row verdicts

| Workload | CPU status | Outcome | Verdict | Findings |
|---|---|---|---|---|
| pointpillars | VERIFIED | VERIFIED | OK |  |
| 3d-pose-estimation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| 3d-segmentation-point-clouds | FAILED | BLOCKED_DEPENDENCY | OK |  |
| ace-step-music-generation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| action-recognition-webcam | FAILED | BLOCKED_DEPENDENCY | OK |  |
| aloha-act | FAILED | BLOCKED_TIMEOUT | OK |  |
| animate-anyone | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| async-api | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| auto-device | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| bark-text-to-audio | FAILED | BLOCKED_TIMEOUT | OK |  |
| bernini-r-image-video | FAILED | BLOCKED_RESOURCE | OK |  |
| blip-visual-language-processing | FAILED | BLOCKED_TIMEOUT | OK |  |
| catvton | FAILED | BLOCKED_DEPENDENCY | OK |  |
| clip-zero-shot-classification | FAILED | BLOCKED_DEPENDENCY | OK |  |
| controlnet-stable-diffusion | FAILED | BLOCKED_TIMEOUT | OK |  |
| convert-to-openvino | FAILED | BLOCKED_DEPENDENCY | OK |  |
| cosyvoice3-tts | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| ct-segmentation-quantize-nncf | FAILED | BLOCKED_NETWORK | OK |  |
| darkir-image-restoration | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| deepseek-ocr | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| deepseek-r1 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| deepseek-vl2 | FAILED | BLOCKED_TIMEOUT | OK |  |
| depth-anything | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| detectron2-to-openvino | VERIFIED | VERIFIED | OK |  |
| ernie-image | FAILED | BLOCKED_DEPENDENCY | OK |  |
| fast-segment-anything | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| fireredtts2 | FAILED | BLOCKED_TIMEOUT | OK |  |
| flex.2-image-generation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| florence2 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| flux-fill | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| flux.1-image-generation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | FAIL | yellow without limitation codes |
| flux.1-kontext | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| flux.2-klein | FAILED | BLOCKED_DEPENDENCY | OK |  |
| freevc-voice-conversion | FAILED | BLOCKED_NETWORK | OK |  |
| funasr-nano | FAILED | BLOCKED_DEPENDENCY | OK |  |
| gemma4 | FAILED | BLOCKED_NETWORK | OK |  |
| glm-ocr | FAILED | BLOCKED_DEPENDENCY | OK |  |
| glm4.1-v-thinking | FAILED | BLOCKED_DEPENDENCY | OK |  |
| gpu-device | NOT_APPLICABLE | NOT_APPLICABLE | OK |  |
| grounded-segment-anything | FAILED | BLOCKED_TIMEOUT | OK |  |
| handwritten-ocr | VERIFIED | VERIFIED | OK |  |
| hello-detection | VERIFIED | VERIFIED | OK |  |
| hello-npu | FAILED | BLOCKED_RESOURCE | OK |  |
| hello-segmentation | VERIFIED | VERIFIED | OK |  |
| hello-world | VERIFIED | VERIFIED | OK |  |
| hugging-face-hub | VERIFIED | VERIFIED | OK |  |
| hunyuan-ocr | FAILED | BLOCKED_DEPENDENCY | OK |  |
| hunyuan-translation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| image-classification-quantization | VERIFIED | VERIFIED | OK |  |
| image-to-image-genai | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| inpainting-genai | FAILED | BLOCKED_TIMEOUT | OK |  |
| instant-id | FAILED | BLOCKED_NETWORK | OK |  |
| jina-clip | FAILED | BLOCKED_TIMEOUT | OK |  |
| kokoro | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| language-quantize-bert | VERIFIED | VERIFIED | OK |  |
| latent-consistency-models-image-generation | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| llm-agent-functioncall-qwen | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| llm-agent-mcp | FAILED | BLOCKED_NETWORK | OK |  |
| llm-agent-rag-llamaindex | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| llm-agent-react-langchain | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| llm-chatbot-generate-api | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | FAIL | yellow without limitation codes |
| llm-chatbot | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | FAIL | yellow without limitation codes |
| llm-code-assistant | FAILED | BLOCKED_NETWORK | OK |  |
| llm-lora | VERIFIED | VERIFIED | OK |  |
| llm-question-answering | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| llm-rag-langchain-eval | FAILED | BLOCKED_DEPENDENCY | OK |  |
| llm-rag-langchain-genai | FAILED | BLOCKED_DEPENDENCY | OK |  |
| llm-rag-langchain | FAILED | BLOCKED_DEPENDENCY | WARN | pre-repin evidence on changed notebook; revalidation queued (noted) |
| llm-rag-llamaindex | FAILED | BLOCKED_DEPENDENCY | OK |  |
| ltx-video | FAILED | BLOCKED_DEPENDENCY | WARN | pre-repin evidence on changed notebook; revalidation queued (noted) |
| medasr-medical-asr | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| meter-reader | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| mineru2.5 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| minicpm-o-4.5 | FAILED | BLOCKED_DEPENDENCY | OK |  |
| minicpm-o-omnimodal-chatbot | FAILED | BLOCKED_RESOURCE | OK |  |
| minicpm-v-4.6 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| minicpm-v-multimodal-chatbot | FAILED | BLOCKED_TIMEOUT | OK |  |
| ministral-3 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| mllama-3.2 | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| mms-massively-multilingual-speech | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| mobileclip-video-search | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| modelscope-to-openvino | VERIFIED | VERIFIED | OK |  |
| multilora-image-generation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| multimodal-rag-llamaindex | FAILED | BLOCKED_RESOURCE | OK |  |
| muse-glimmer | FAILED | BLOCKED_NETWORK | OK |  |
| music-generation | FAILED | BLOCKED_TIMEOUT | OK |  |
| nuextract-structure-extraction | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| object-detection | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| olmocr-pdf-vlm | FAILED | BLOCKED_DEPENDENCY | OK |  |
| omniparser | FAILED | BLOCKED_DEPENDENCY | OK |  |
| omnivoice | FAILED | BLOCKED_TIMEOUT | OK |  |
| oneformer-segmentation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| openvino-api | VERIFIED | VERIFIED | OK |  |
| openvino-tokenizers | FAILED | FAILED_COMPATIBILITY | OK |  |
| openvoice | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| openvoice2-and-melotts | FAILED | BLOCKED_DEPENDENCY | OK |  |
| optical-character-recognition | VERIFIED | VERIFIED | OK |  |
| optimize-preprocessing | VERIFIED | VERIFIED | OK |  |
| paddle-ocr-webcam | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| paddle-to-openvino-classification | VERIFIED | VERIFIED | OK |  |
| paddleocr_vl | FAILED | BLOCKED_DEPENDENCY | OK |  |
| parler-tts-text-to-speech | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| person-counting | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| person-tracking | FAILED | BLOCKED_DEPENDENCY | OK |  |
| phi-3-vision | FAILED | BLOCKED_TIMEOUT | OK |  |
| phi-4-multimodal | FAILED | BLOCKED_TIMEOUT | OK |  |
| physical-ai-robotics | NOT_APPLICABLE | NOT_APPLICABLE | OK |  |
| pose-estimation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| pyannote-audio | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| pyannote-embedding | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| pytorch-post-training-quantization-nncf | VERIFIED | VERIFIED | OK |  |
| pytorch-to-openvino | VERIFIED | VERIFIED | OK |  |
| qwen-image | FAILED | BLOCKED_DEPENDENCY | OK |  |
| qwen-image-2.1 | FAILED | BLOCKED_TIMEOUT | OK |  |
| qwen2-audio | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| qwen2.5-omni-chatbot | FAILED | BLOCKED_DEPENDENCY | OK |  |
| qwen3-asr | FAILED | BLOCKED_DEPENDENCY | OK |  |
| qwen3-embedding | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| qwen3-reranker | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| qwen3-tts | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| qwen3-vl-embedding | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| qwen3-vl-reranker | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| qwen3.8-mtp | FAILED | BLOCKED_NETWORK | OK |  |
| rf-detr-object-detection | FAILED | BLOCKED_DEPENDENCY | OK |  |
| rmbg-background-removal | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| segment-anything-2-image | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| segment-anything-2-video | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | WARN | pre-repin evidence on changed notebook; revalidation queued (noted) |
| sam3-segmentation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| siglip-zero-shot-image-classification | FAILED | BLOCKED_TIMEOUT | OK |  |
| smoldocling | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| smolvlm2 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| speculative-sampling | VERIFIED | VERIFIED | OK |  |
| speech-recognition-quantization-wav2vec2 | VERIFIED | VERIFIED | OK |  |
| stable-diffusion-text-to-image | FAILED | BLOCKED_TIMEOUT | OK |  |
| stable-diffusion-v3 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| stable-diffusion-v3-torch-fx | FAILED | BLOCKED_MODEL_ACCESS | OK |  |
| stable-diffusion-xl | FAILED | BLOCKED_DEPENDENCY | OK |  |
| stable-video-diffusion | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| surya-line-level-text-detection | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| tensorflow-classification-to-openvino | VERIFIED | VERIFIED | OK |  |
| tensorflow-object-detection-api-with-openvino | VERIFIED | VERIFIED | OK |  |
| text-to-image-genai | FAILED | BLOCKED_TIMEOUT | OK |  |
| text-to-speech-genai | FAILED | BLOCKED_DEPENDENCY | OK |  |
| tflite-selfie-segmentation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| tflite-to-openvino | VERIFIED | VERIFIED | OK |  |
| convnext-classification | VERIFIED | VERIFIED | OK |  |
| unlimited-ocr | FAILED | BLOCKED_TIMEOUT | OK |  |
| vehicle-detection-and-recognition | VERIFIED | VERIFIED | OK |  |
| vision-background-removal | FAILED | BLOCKED_NETWORK | OK |  |
| vision-monodepth | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| vlm-chatbot-generate-api | FAILED | BLOCKED_DEPENDENCY | OK |  |
| voxcpm2-tts | FAILED | BLOCKED_TIMEOUT | OK |  |
| wan2.1-text-to-video | FAILED | BLOCKED_TIMEOUT | OK |  |
| wan2.2-text-image-to-video | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| wav2lip | FAILED | BLOCKED_NETWORK | OK |  |
| whisper-asr-genai | FAILED | BLOCKED_NETWORK | OK |  |
| yolov11-instance-segmentation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| yolov11-keypoint-detection | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| yolov11-object-detection | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| yolov11-quantization-with-accuracy-control | FAILED | BLOCKED_TIMEOUT | OK |  |
| yoloe-26-open-vocabulary | FAILED | BLOCKED_NETWORK | OK |  |
| yolov26-instance-segmentation | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| yolov26-keypoint-detection | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| yolov26-obb | VERIFIED | VERIFIED | OK |  |
| yolov26-object-detection | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| z-image-turbo | FAILED | BLOCKED_DEPENDENCY | OK |  |
| zeroscope-text2video | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | OK |  |
| 001-whisper-evaluation | FAILED | BLOCKED_DEPENDENCY | OK |  |
| fastdraft_deepseek | FAILED | BLOCKED_RESOURCE | OK |  |
| phi3_chatbot_demo | FAILED | BLOCKED_DEPENDENCY | OK |  |
| phi3_rag_on_client | FAILED | BLOCKED_DEPENDENCY | OK |  |
| qwen3 | VERIFIED_WITH_LIMITATIONS | VERIFIED_WITH_LIMITATIONS | FAIL | yellow without limitation codes |
| qwen3_agent | FAILED | BLOCKED_NETWORK | OK |  |

## Method

Each row: upstream URL/pin coherence, snapshot presence, twin classification, status+outcome
presence, evidence-dir existence, Evidence Schema v2 file completeness (green/yellow),
upstream.json pin match, repeatability aggregate coherence, PROVEN_CPU + L3 + ok_runs>=required
for VERIFIED rows, limitation codes for yellow rows, failure category for FAILED rows, note
sanitization, timestamp parseability, and GPU v2 evidence for GPU-verified rows.

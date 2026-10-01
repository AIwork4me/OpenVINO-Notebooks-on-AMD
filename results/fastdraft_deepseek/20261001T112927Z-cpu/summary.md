# fastdraft_deepseek — CPU attempt

- status: ERROR
- duration: 24.26s
- failure: OPENVINO_ERROR
- patches: ["notebook_utils.device_widget default pinned AUTO->CPU (CPU validation premise; explicit device args unaffected)", "preseeded sibling helper module gradio_helper.py (kernel cwd differs from notebook dir)", "preseeded sibling helper module llm_pipeline_with_hf_tokenizer.py (kernel cwd differs from notebook dir)"]

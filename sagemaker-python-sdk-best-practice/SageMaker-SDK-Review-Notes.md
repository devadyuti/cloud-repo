# SageMaker Python SDK — Code Review & Call Prep Notes

**Prepared for:** Customer Call — Thursday 9th April  
**Scope:** Review of inference/train pipeline using SageMaker Python SDK with custom containers  
**Files reviewed:** `sm_inference_runner.py`, `preprocessing.py`, `inference.py`, `sm_train_runner.py`, `train.py`, `investtools-sagemaker-0.2.Dockerfile`, `run_model.sh`

---

## 1. Are you thinking about the SageMaker Python SDK correctly?

**Assessment: The approach is appropriate and well-aligned with how the SDK is intended to be used.**

Using SageMaker Processing Jobs as a container execution engine to guarantee reproducibility is a well-supported pattern. The key strengths of this approach:

- Code + `requirements.txt` stored as model artifacts at train time
- Consistent OS and Python environment between train and inference
- Every prediction traceable back to a specific model version, code state, and MLFlow run
- Flexible scaling path — local today, managed SageMaker instances tomorrow

### Observation: `wait=False` in inference runner

In `sm_inference_runner.py`, both `processor.run()` calls use `wait=False`. The second job (inference) depends on the preprocessing output being written to S3 first — this introduces a potential timing dependency.

This likely works today because `LocalSession` executes synchronously regardless of the `wait` flag, but may not behave as expected when moving to managed SageMaker instances.

**Suggestion:** Align with the pattern already used in `sm_train_runner.py` by setting `wait=True` for the preprocessing step.

**Reference:** [SageMaker Python SDK — Processor.run() documentation](https://sagemaker.readthedocs.io/en/v2.206.0/api/training/processing.html)

---

## 2. Are you using the correct part of the SDK?

**Assessment: We would recommend considering `ScriptProcessor` as a more natural fit for this use case.**

### What `FrameworkProcessor` is designed for

`FrameworkProcessor` provides AWS-managed containers for supported ML frameworks (PyTorch, TensorFlow, sklearn, MXNet, XGBoost, HuggingFace). It handles source code packaging and dependency management automatically via `source_dir` and `requirements.txt`.

> *"A FrameworkProcessor can run Processing jobs with a specified machine learning framework, providing you with an Amazon SageMaker AI–managed container for whichever machine learning framework you choose."*  
> — [AWS Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job-frameworks.html)

### How the current code differs from that pattern

The implementation brings a custom container (`invtools-sklearn:0.2-cpu-py3.13`), passes `command=["bash"]`, controls the entrypoint via `run_model.sh`, and creates an empty `source_dir` to prevent the SDK from packaging the repo. While functional, this works around the intended `FrameworkProcessor` behaviour.

### Alternative to consider

`ScriptProcessor` is the documented class for "bring your own container" scenarios:

> *"This notebook uses the ScriptProcessor class from the Amazon SageMaker Python SDK for Processing."*  
> — [Run Scripts with Your Own Processing Container](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-container-run-scripts.html)

`ScriptProcessor` takes `image_uri` and `command` directly. The script is passed via the `code` parameter — which would remove the need for the empty directory workaround.

### Note on `sagemaker.core.*` imports

The code imports from `sagemaker.core.processing` (the [new SageMaker Core SDK](https://aws.amazon.com/blogs/machine-learning/accelerate-your-ml-lifecycle-using-the-new-and-improved-amazon-sagemaker-python-sdk-part-1-modeltrainer/)) rather than the classic `sagemaker.processing`. The Core SDK's `FrameworkProcessor` may have a slightly different interface — worth discussing whether this changes the guidance.

---

## 3. VPC Configuration for Non-Local Train

**Assessment: The implementation follows the correct pattern. We suggest validating a few networking details.**

The `NetworkConfig` usage in `sm_train_runner.py` is appropriate:

```python
network_config = NetworkConfig(
    subnets=vpc_conf["subnets"],
    security_group_ids=vpc_conf["security_group_ids"],
)
```

### Points to validate

| Requirement | Reason |
|-------------|--------|
| Subnets should be **private** | SageMaker creates ENIs in these subnets |
| NAT Gateway OR VPC endpoints needed | For S3, ECR, CloudWatch, PyPI, MLFlow, RDS access |
| ≥2 available IPs per instance per subnet | SageMaker allocates ENIs from the subnet |
| Security group allows outbound HTTPS (443) | S3, ECR, MLFlow connectivity |
| Security group allows outbound to RDS port | Preprocessing and train scripts query the database |

### Consideration: Runtime `pip install` without internet

`run_model.sh` runs:
```bash
pip install --quiet --timeout 5 --retries 0 -r "${MODEL_DIR}/requirements.txt"
```

If the VPC subnets do not have a NAT gateway or a route to PyPI, this will silently fail and the job will rely solely on packages already present in the Docker image. This could cause subtle issues if the image does not contain all required packages.

**Options to discuss:**
1. Ensure NAT gateway is in place for the subnets used
2. Pre-bake all heavy dependencies into the Docker image (preferred for determinism)

**Reference:** [Give SageMaker AI Processing Jobs Access to Resources in Your Amazon VPC](https://docs.aws.amazon.com/sagemaker/latest/dg/process-vpc.html)

---

## 4. Preprocessing / Processing Split

**Assessment: The current split is well-structured and follows a pattern we commonly recommend.**

| Step | Responsibility | Resource profile |
|------|---------------|-----------------|
| **Preprocessing** (`preprocessing.py`) | Query feature store, assemble panel dataset, write to S3 | I/O-heavy, DB-dependent |
| **Inference** (`inference.py`) | Load data from S3, load model pickle, run predictions, write outputs | Compute-heavy, no DB needed |
| **Train** (`train.py`) | Load data from S3, attach returns, train LightGBM per horizon | Compute-heavy, needs larger instance |

The split at the I/O boundary means:
- Each step can be retried independently
- Preprocessing output is cached in S3 (reusable across runs)
- Different instance types can be used per step

### Optional refinement

`train.py` still calls the database (`get_index_relative_returns()` via `DBEngine`). Moving this into the preprocessing step would make the train step purely compute-bound — simplifying failure isolation and removing the need for RDS access from the training instance's VPC configuration.

**Reference:** [How Amazon SageMaker Processing Configures Input and Output](https://docs.aws.amazon.com/sagemaker/latest/dg/byoc-input-and-output.html)

---

## 5. ECR Image Strategy for MLOps

**Assessment: The current approach is functional. There are a few practices that could improve operational maturity.**

### Current state

- Image: `invtools-sklearn:0.2-cpu-py3.13`
- Based on SageMaker's `sagemaker-scikit-learn:1.4-2-cpu-py3`
- Installs Python 3.13 via `uv`, creates a minimal virtual env
- Heavy dependencies installed at **runtime** via `requirements.txt`

### Practices to consider

| Practice | Benefit |
|----------|---------|
| **ECR lifecycle policies** | Auto-expire untagged images after N days, keep last N tagged versions. Prevents unbounded cost growth. |
| **Pre-bake common heavy deps** (pandas, numpy, lightgbm, scikit-learn) | Removes network dependency at runtime, improves determinism, faster job startup. |
| **Tag with build metadata** (e.g. `0.2-cpu-py3.13-20240401` or git SHA) | Full traceability from model artifact back to exact image. |
| **Enable image scanning on push** | Automated vulnerability detection. |
| **Separate repos if deps diverge** | `invtools-inference` vs `invtools-train` if the package set differs significantly. |

**Reference:** [Clean up Your Container Images with Amazon ECR Lifecycle Policies](https://aws.amazon.com/blogs/compute/clean-up-your-container-images-with-amazon-ecr-lifecycle-policies/)

---

## Summary

| Area | Assessment | Suggested Action |
|------|-----------|-----------------|
| SDK mental model | Appropriate | No change needed |
| FrameworkProcessor choice | Functional, alternative available | Consider migrating to `ScriptProcessor` |
| `wait=False` in inference | Potential timing issue | Align with train runner (`wait=True`) |
| VPC config (train) | Correct pattern | Validate NAT/endpoints and security group rules |
| Inference runner VPC | Not configured | Add `NetworkConfig` when moving off local mode |
| Preprocessing/processing split | Well-structured | Optional: move DB call from train into preprocessing |
| ECR image strategy | Functional | Add lifecycle policies, pre-bake deps, enable scanning |

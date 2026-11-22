"""
GPU-pinned ModelManager singleton for Causal LLM dual-stream inference.
Manages observer and performer models on dedicated devices with FP16 precision
and SDPA attention backend.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import torch

try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        PreTrainedModel,
        PreTrainedTokenizerBase,
    )
except ImportError:
    AutoModelForCausalLM = None  # type: ignore[assignment, misc]
    AutoTokenizer = None  # type: ignore[assignment, misc]
    PreTrainedModel = None  # type: ignore[assignment, misc]
    PreTrainedTokenizerBase = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


def get_optimal_gpu_device() -> str:
    """
    Selects the CUDA device with the greatest amount of available free VRAM,
    guaranteeing jobs avoid saturated GPUs in shared multi-GPU DGX clusters.
    """
    if not torch.cuda.is_available():
        return "cpu"
    try:
        best_device = 0
        max_free = 0
        for i in range(torch.cuda.device_count()):
            free, _ = torch.cuda.mem_get_info(i)
            if free > max_free:
                max_free = free
                best_device = i
        return f"cuda:{best_device}"
    except Exception:
        return "cuda:0" if torch.cuda.is_available() else "cpu"


class ModelManager:
    """
    Singleton manager for loading, pinning, and accessing observer and performer
    causal language models for Binoculars and DNA-DetectLLM scoring.
    """

    _instance: ModelManager | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self.observer_name: str = "Qwen/Qwen2.5-0.5B"
        self.performer_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
        optimal_dev = get_optimal_gpu_device()
        self.observer_device: str = optimal_dev
        self.performer_device: str = optimal_dev
        self.observer_model: Any | None = None
        self.performer_model: Any | None = None
        self.tokenizer: Any | None = None
        self._is_loaded: bool = False

    @classmethod
    def get_instance(cls) -> ModelManager:
        """Retrieve or create the singleton instance with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def load_models(
        self,
        observer_name: str = "Qwen/Qwen2.5-0.5B",
        performer_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        observer_device: str | None = None,
        performer_device: str | None = None,
    ) -> ModelManager:
        """
        Loads the observer and performer causal LLMs with:
        - torch_dtype=torch.float16
        - attn_implementation="sdpa"
        - config.use_cache=False
        - model.eval()
        and assigns them to the specified GPU devices.
        """
        if AutoModelForCausalLM is None or AutoTokenizer is None:
            raise RuntimeError(
                "transformers is required to load causal language models."
            )

        if observer_device is None:
            observer_device = get_optimal_gpu_device()
        if performer_device is None:
            performer_device = observer_device

        self.observer_name = observer_name
        self.performer_name = performer_name
        self.observer_device = observer_device
        self.performer_device = performer_device

        logger.info(
            "Loading observer model '%s' on %s and performer model '%s' on %s",
            observer_name,
            observer_device,
            performer_name,
            performer_device,
        )

        # 1. Load Observer Model
        obs_model = AutoModelForCausalLM.from_pretrained(
            observer_name,
            torch_dtype=torch.float16,
            attn_implementation="sdpa",
        )
        if hasattr(obs_model, "config") and obs_model.config is not None:
            obs_model.config.use_cache = False
        obs_model.eval()

        # Handle device placement safely
        if (
            torch.cuda.is_available()
            and observer_device.startswith("cuda")
            or not observer_device.startswith("cuda")
        ):
            obs_model = obs_model.to(observer_device)  # type: ignore[arg-type]

        self.observer_model = obs_model

        # 2. Load Performer Model
        perf_model = AutoModelForCausalLM.from_pretrained(
            performer_name,
            torch_dtype=torch.float16,
            attn_implementation="sdpa",
        )
        if hasattr(perf_model, "config") and perf_model.config is not None:
            perf_model.config.use_cache = False
        perf_model.eval()

        # Handle device placement safely
        if (
            torch.cuda.is_available()
            and performer_device.startswith("cuda")
            or not performer_device.startswith("cuda")
        ):
            perf_model = perf_model.to(performer_device)  # type: ignore[arg-type]

        self.performer_model = perf_model

        # 3. Load Shared Tokenizer (Falcon models share tokenizer vocabulary)
        tokenizer = AutoTokenizer.from_pretrained(observer_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        self.tokenizer = tokenizer

        self._is_loaded = True
        logger.info(
            "Successfully initialized and loaded observer & performer models in FP16 with SDPA."
        )
        return self

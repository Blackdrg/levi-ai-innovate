import os
import argparse
import logging
import json
import torch
from datetime import datetime
from datasets import load_dataset
from transformers import TrainingArguments
from trl import SFTTrainer
# unsloth is imported inside a try-block or function later if needed, 
# but for a dedicated script we can put it here if installed.
try:
    from unsloth import FastLanguageModel
except ImportError:
    FastLanguageModel = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TrainLoRA")

def run_training_job_cli(args):
    """
    Sovereign v16.2 LoRA Training Engine (Entry Point).
    Executes automated fine-tuning pulses to crystallize cognitive gains.
    """
    logger.info("🛡️ [Sovereign-Trainer] Commencing Model Evolution Pulse...")
    logger.info(f"📍 Dataset: {args.dataset}")
    logger.info(f"📂 Output: {args.output}")
    
    # 1. Hardware Audit
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"⚙️ Computing Device: {device.upper()}")
    
    if device == "cpu":
        logger.warning("⚠️ CRITICAL: No GPU (CUDA) detected. LoRA training on CPU is computationally prohibitive.")
        logger.warning("💡 TIP: Deploy onto a Node with NVIDIA A10/A100 or 4090 for production crystallization.")
        # We proceed to structure the metadata even on CPU for test-parity
    else:
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        logger.info(f"📟 Available VRAM: {vram_gb:.2f} GB")
        if vram_gb < 16:
             logger.warning("⚠️ WARNING: Sub-optimal VRAM for Llama-3 8B fine-tuning. Expecting OOM or extreme latency.")

    try:
        # 2. Dataset Verification
        if not os.path.exists(args.dataset):
             raise FileNotFoundError(f"Training dataset missing: {args.dataset}")
             
        # Count samples for metadata
        with open(args.dataset, 'r') as f:
             sample_count = sum(1 for _ in f)
        logger.info(f"📊 Training on {sample_count} high-fidelity cognitive samples.")

        if device == "cpu":
             logger.warning("❌ [TrainLoRA] Skipping engine initialization on CPU. Weights will not be updated.")
             return False

        if not FastLanguageModel:
             logger.error("❌ [TrainLoRA] Unsloth not installed. Evolution requires Unsloth engine.")
             return False

        # 3. Model & Tokenizer Integration (v16.2 Unsloth Engine)

        max_seq_length = 2048 # Supports RoPE Scaling
        dtype = None # None for auto detection. Float16 for Tesla T4, V100, Bfloat16 for Ampere+
        load_in_4bit = True # Use 4bit quantization to reduce VRAM usage

        logger.info(f"[TrainLoRA] Initializing Base Model: {args.model} (4-bit)...")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name = args.model,
            max_seq_length = max_seq_length,
            dtype = dtype,
            load_in_4bit = load_in_4bit,
        )

        # 4. LoRA Configuration
        model = FastLanguageModel.get_peft_model(
            model,
            r = 16, # Rank
            target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", 
                             "gate_proj", "up_proj", "down_proj",],
            lora_alpha = 16,
            lora_dropout = 0, # Optimized to 0 for Unsloth
            bias = "none",    # Optimized to "none" for Unsloth
            use_gradient_checkpointing = "unsloth", # 2x-4x faster/less VRAM
            random_state = 3407,
            use_rslora = False,
            loftq_config = None,
        )

        # 5. Data Loading
        dataset = load_dataset("json", data_files={"train": args.dataset}, split="train")

        # 6. Training Configuration
        trainer = SFTTrainer(
            model = model,
            tokenizer = tokenizer,
            train_dataset = dataset,
            dataset_text_field = "instruction", # Field containing instructional pair
            max_seq_length = max_seq_length,
            dataset_num_proc = 2,
            packing = False, # Can speed up training for short sequences
            args = TrainingArguments(
                per_device_train_batch_size = 2,
                gradient_accumulation_steps = 4,
                warmup_steps = 5,
                max_steps = args.max_steps, # Small pulse for fast evolution
                learning_rate = 2e-4,
                fp16 = not torch.cuda.is_bf16_supported(),
                bf16 = torch.cuda.is_bf16_supported(),
                logging_steps = 1,
                optim = "adamw_8bit",
                weight_decay = 0.01,
                lr_scheduler_type = "linear",
                seed = 3407,
                output_dir = "artifacts/training_outputs",
            ),
        )

        # 7. Execute Evolution Pulse
        logger.info("🔥 [TrainLoRA] Commencing LoRA crystallization...")
        trainer.train()

        # 8. Export Weights
        os.makedirs(args.output, exist_ok=True)
        model.save_pretrained_merged(args.output, tokenizer, save_method = "lora",)
        
        meta = {
            "trained_at": datetime.now().isoformat(),
            "samples": sample_count,
            "device": device,
            "base_model": args.model,
            "type": "lora_adapter",
            "framework": "unsloth/peft"
        }
        with open(os.path.join(args.output, "evolution_metadata.json"), "w") as f:
            json.dump(meta, f, indent=4)

        logger.info(f"✨ [Sovereign-Trainer] Evolution complete. Weights crystallized at: {args.output}")
        return True

    except Exception as e:
        logger.error(f"💥 [Sovereign-Trainer] Training pulse CRASHED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LEVI-AI Sovereign LoRA Trainer")
    parser.add_argument("--model", default="unsloth/llama-3-8b-bnb-4bit", help="Base model for fine-tuning")
    parser.add_argument("--max_steps", type=int, default=60, help="Number of training steps")
    parser.add_argument("--dataset", required=True, help="Path to JSONL training data")
    parser.add_argument("--output", required=True, help="Output directory for weights")
    parser.add_argument("--quantization", default="Q4_K_M", help="Target quantization level")
    
    args = parser.parse_args()
    success = run_training_job_cli(args)
    exit(0) if success else exit(1)

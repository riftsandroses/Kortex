import os
import uuid
import json
import logging
from pathlib import Path
from datetime import datetime
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
)
import numpy as np
from datasets import Dataset
from evaluate import load as load_metric
import torch

from django.conf import settings
from .inference import MODEL_ROOT

from guardrails.models import CapturedResponse, GuardrailApp, ModelVersion

logger = logging.getLogger(__name__)


def _gather_labeled_data_for_app(app_slug: str):
    """
    Pull labeled rows from DB and return a HuggingFace Dataset.
    """
    app = GuardrailApp.objects.get(slug=app_slug)

    # Fetch only necessary fields as dicts
    rows = (
        CapturedResponse.objects
        .filter(app=app, labeled=True)
        .exclude(label__isnull=True)
        .exclude(label='')
        .values('response_text', 'label')
    )

    if not rows.exists():
        logger.warning(f"No labeled data found for app: {app_slug}")
        return None

    data = [{'text': r['response_text'], 'label': r['label']} for r in rows]

    # Map labels → ints
    labels = sorted(set(d['label'] for d in data))
    label2id = {l: i for i, l in enumerate(labels)}

    logger.info(f"Found {len(data)} labeled samples with labels: {labels}")

    for d in data:
        d['label'] = label2id[d['label']]

    ds = Dataset.from_list(data)

    # Train/test split
    if len(ds) < 5:
        logger.warning(f"Very small dataset ({len(ds)} samples). Using 80% for training.")
        test_size = max(1, len(ds) // 5)
    else:
        test_size = 0.2

    ds = ds.train_test_split(test_size=test_size, seed=42)
    return ds, labels, label2id


def compute_metrics(pred):
    """
    Compute accuracy metric for model evaluation.
    """
    try:
        metric = load_metric("accuracy")
        preds = np.argmax(pred.predictions, axis=1)
        return metric.compute(predictions=preds, references=pred.label_ids)
    except Exception as e:
        logger.warning(f"Could not compute metrics: {e}")
        return {"accuracy": 0.0}


def train_model_for_app(app_slug: str, initiated_by: str = None, params: dict = None):
    """
    Trains a HuggingFace Transformers model on labeled CapturedResponse rows.
    Returns dict with version, model_files, and metrics.
    """
    params = params or {}

    # Setup device
    use_cuda = params.get('use_cuda', False) and torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    logger.info(f"Using device: {device} for training app: {app_slug}")

    ds_labels = _gather_labeled_data_for_app(app_slug)
    if not ds_labels:
        raise RuntimeError("No labeled data available for training. Label data first.")

    dataset, labels, label2id = ds_labels
    num_labels = len(labels)

    logger.info(f"Training with {len(dataset['train'])} train / {len(dataset['test'])} test samples")
    logger.info(f"Labels: {labels}")

    # Paths and model setup
    base_model = params.get('base_model') or GuardrailApp.objects.get(slug=app_slug).base_model_name
    output_dir_root = Path(MODEL_ROOT) / app_slug / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir_root.mkdir(parents=True, exist_ok=True)
    version = f"v{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    model_output_dir = str(output_dir_root / 'model')

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or '[PAD]'
        logger.info(f"Set pad_token to: {tokenizer.pad_token}")

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=num_labels,
        id2label={i: label for i, label in enumerate(labels)},
        label2id=label2id
    ).to(device)

    # ------------------- Preprocessing -------------------
    def preprocess(batch):
        # Tokenize text
        encoding = tokenizer(
            batch['text'],
            truncation=True,
            padding='max_length',
            max_length=256,
        )

        # Classification → int64 labels
        # Regression (single label) → float32 labels
        if num_labels == 1:
            labels = np.array(batch['label'], dtype=np.float32)
        else:
            labels = np.array(batch['label'], dtype=np.int64)

        return {
            'input_ids': encoding['input_ids'],
            'attention_mask': encoding['attention_mask'],
            'labels': labels,
        }

    # Map over dataset (batched)
    tokenized = dataset.map(preprocess, batched=True)

    # Debug: show resulting columns
    logger.info(f"Tokenized train columns: {tokenized['train'].column_names}")
    logger.info(f"Tokenized test columns: {tokenized['test'].column_names}")

    # Ensure required columns exist before formatting
    expected_cols = ['input_ids', 'attention_mask', 'labels']
    for split in ['train', 'test']:
        missing = [c for c in expected_cols if c not in tokenized[split].column_names]
        if missing:
            logger.warning(f"Missing columns in {split}: {missing} -> current: {tokenized[split].column_names}")

    # Format dataset for PyTorch
    tokenized.set_format(type='torch', columns=expected_cols, output_all_columns=False)

    logger.info("Sample after preprocessing:")
    sample = tokenized['train'][0]
    for k, v in sample.items():
        logger.info(f"  {k}: shape={getattr(v, 'shape', None)}, dtype={getattr(v, 'dtype', None)}")

    # ------------------- Training -------------------
    train_args = TrainingArguments(
        output_dir=model_output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        num_train_epochs=int(params.get('epochs', 10)),
        per_device_train_batch_size=int(params.get('batch_size', 32)),
        per_device_eval_batch_size=int(params.get('batch_size', 32)),
        learning_rate=float(params.get('learning_rate', 2e-5)),
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        weight_decay=0.01,
        fp16=False,
        no_cuda=not use_cuda,
        dataloader_pin_memory=False,
        save_total_limit=3,
        remove_unused_columns=True,
        label_names=["labels"],
        report_to=None,
        logging_dir=str(output_dir_root / 'logs'),
    )

    trainer = Trainer(
        model=model,
        args=train_args,
        train_dataset=tokenized['train'],
        eval_dataset=tokenized['test'],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    logger.info("Starting training...")
    trainer.train()
    logger.info("Training completed successfully")

    # ------------------- Save model -------------------
    trainer.save_model(model_output_dir)
    logger.info(f"Model saved to {model_output_dir}")

    # Create/update 'latest' symlink
    import shutil
    latest_dir = Path(MODEL_ROOT) / app_slug / 'latest'
    if latest_dir.exists():
        for p in latest_dir.iterdir():
            if p.is_file():
                p.unlink()
            else:
                shutil.rmtree(p)
    else:
        latest_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(model_output_dir, latest_dir, dirs_exist_ok=True)
    logger.info(f"Updated latest model at: {latest_dir}")

    # ------------------- Evaluate -------------------
    metrics = {}
    try:
        raw_metrics = trainer.evaluate()
        metrics.update(raw_metrics)
        logger.info(f"Evaluation metrics: {metrics}")
    except Exception as e:
        logger.warning(f"Could not compute evaluation metrics: {e}")

    # ------------------- Save metadata -------------------
    model_files = [str(f) for f in Path(model_output_dir).rglob('*') if f.is_file()]

    label_mapping = {
        'id2label': {i: label for i, label in enumerate(labels)},
        'label2id': label2id,
    }
    with open(Path(model_output_dir) / 'label_mapping.json', 'w') as f:
        json.dump(label_mapping, f, indent=2)
    with open(latest_dir / 'label_mapping.json', 'w') as f:
        json.dump(label_mapping, f, indent=2)

    logger.info(f"Training complete for {app_slug}, version={version}")

    # Get the app object
    app = GuardrailApp.objects.get(slug=app_slug)
    
    # Create or update ModelVersion WITH CATEGORIES
    mv, _ = ModelVersion.objects.get_or_create(app=app, version=version, defaults={
        'metrics': metrics,
        'model_files': model_files,
        'trained_by': User.objects.get(id=initiated_by) if initiated_by else None,
        'categories': labels
    })
    # Ensure categories are always set, even if updating existing ModelVersion
    mv.metrics = metrics
    mv.model_files = model_files
    mv.categories = labels
    mv.save()

    return {
        'version': version,
        'metrics': metrics,
        'model_files': model_files,
        'num_labels': num_labels,
        'labels': labels,  # This will now be stored in ModelVersion.categories
        'device_used': str(device),
    }

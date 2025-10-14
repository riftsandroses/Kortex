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

from guardrails.models import CapturedResponse, GuardrailApp

logger = logging.getLogger(__name__)

def _gather_labeled_data_for_app(app_slug: str):
    """
    Pull labeled rows from DB and return a HuggingFace Dataset
    """
    app = GuardrailApp.objects.get(slug=app_slug)
    rows = CapturedResponse.objects.filter(app=app, labeled=True).values('response_text', 'label')
    data = [{'text': r['response_text'], 'label': r['label']} for r in rows]
    if not data:
        return None
    # Map labels -> ints
    labels = sorted(set([d['label'] for d in data]))
    label2id = {l:i for i,l in enumerate(labels)}
    for d in data:
        d['label'] = label2id[d['label']]
    ds = Dataset.from_list(data)
    ds = ds.train_test_split(test_size=0.1)
    return ds, labels, label2id

def compute_metrics(pred):
    metric = load_metric("accuracy")
    preds = np.argmax(pred.predictions, axis=1)
    return metric.compute(predictions=preds, references=pred.label_ids)

def train_model_for_app(app_slug: str, initiated_by: str=None, params: dict=None):
    """
    Trains a HF Transformers sequence classification model on labeled CapturedResponse rows.
    Returns a dict with version, model_files, metrics.
    """
    params = params or {}
    ds_labels = _gather_labeled_data_for_app(app_slug)
    if not ds_labels:
        raise RuntimeError("No labeled data available for training. Label data first.")

    dataset, labels, label2id = ds_labels
    num_labels = len(labels)
    # hyperparams
    base_model = params.get('base_model') or GuardrailApp.objects.get(slug=app_slug).base_model_name
    output_dir_root = Path(MODEL_ROOT) / app_slug / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir_root.mkdir(parents=True, exist_ok=True)
    version = f"v{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    model_output_dir = str(output_dir_root / 'model')

    # Tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=num_labels)
    # Preprocessing
    def preprocess(batch):
        return tokenizer(batch['text'], truncation=True, padding='max_length', max_length=256)
    tokenized = dataset.map(preprocess, batched=True)

    # Training args
    train_args = TrainingArguments(
        output_dir=model_output_dir,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        num_train_epochs=int(params.get('epochs', 2)),
        per_device_train_batch_size=int(params.get('batch_size', 8)),
        per_device_eval_batch_size=int(params.get('batch_size', 8)),
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        weight_decay=0.01,
        fp16=torch.cuda.is_available(),
        save_total_limit=3
    )

    trainer = Trainer(
        model=model,
        args=train_args,
        train_dataset=tokenized['train'],
        eval_dataset=tokenized['test'],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )

    trainer.train()

    # save final model to model_output_dir (Trainer already handles)
    trainer.save_model(model_output_dir)

    # Optionally create a "latest" symlink for inference
    latest_dir = Path(MODEL_ROOT) / app_slug / 'latest'
    if latest_dir.exists():
        # remove and recreate
        for p in latest_dir.iterdir():
            if p.is_file():
                p.unlink()
            else:
                import shutil; shutil.rmtree(p)
    else:
        latest_dir.mkdir(parents=True, exist_ok=True)

    # Copy model_output_dir -> latest
    import shutil
    shutil.copytree(model_output_dir, latest_dir, dirs_exist_ok=True)

    # Collect metrics on test set
    metrics = {}
    if trainer.evaluate:
        raw_metrics = trainer.evaluate()
        metrics.update(raw_metrics)

    model_files = [str(f) for f in Path(model_output_dir).rglob('*') if f.is_file()]

    logger.info("Training complete for %s, version=%s", app_slug, version)
    return {'version': version, 'metrics': metrics, 'model_files': model_files}

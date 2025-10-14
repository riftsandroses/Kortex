import os
import logging
from typing import Tuple
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from sentence_transformers import SentenceTransformer, util

from django.conf import settings

logger = logging.getLogger(__name__)

MODEL_ROOT = getattr(settings, 'GUARDRAILS_MODEL_ROOT', '/var/lib/kortex/guardrails_models')

# Simple cache in process
_MODEL_CACHE = {}
_EMBED_MODEL = None

def load_model_for_app(app_slug: str):
    """
    Loads HF model for the app if exists. Caches in process.
    """
    if app_slug in _MODEL_CACHE:
        return _MODEL_CACHE[app_slug]
    # Expect model artifacts at MODEL_ROOT/<app_slug>/latest/
    model_dir = os.path.join(MODEL_ROOT, app_slug, 'latest')
    if not os.path.isdir(model_dir):
        logger.info("No model dir for %s", app_slug)
        return None
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    _MODEL_CACHE[app_slug] = (tokenizer, model)
    return _MODEL_CACHE[app_slug]

def evaluate_with_transformer(tokenizer, model, text: str) -> Tuple[str, float]:
    inputs = tokenizer(text, truncation=True, padding=True, return_tensors='pt')
    model.eval()
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        score, idx = torch.max(probs, dim=-1)
        label = model.config.id2label.get(int(idx[0]), str(int(idx[0])))
        return label, float(score[0].item())

def fallback_embedding_based(text: str, app_slug: str) -> Tuple[str, float]:
    """
    A simple fallback: compute embedding and compare to centroid of labeled toxic examples.
    This requires that you build and persist centroids during training (not implemented here).
    We'll use a threshold heuristic.
    """
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    emb = _EMBED_MODEL.encode(text, convert_to_tensor=True)
    # Heuristic: if embedding norm is small -> safe (this is just placeholder)
    # In production you would compare to stored labeled embeddings.
    score = float(torch.sigmoid(torch.tensor(0.0)).item())
    return "unknown", 0.0

def evaluate_text_with_model(app_slug: str, text: str) -> Tuple[str, float, str]:
    """
    Returns (label, score, action)
    action ∈ {'info','warning','block'}
    """
    loaded = load_model_for_app(app_slug)
    if loaded:
        tokenizer, model = loaded
        try:
            label, score = evaluate_with_transformer(tokenizer, model, text)
        except Exception:
            logger.exception("Transformers evaluation failed; falling back")
            label, score = fallback_embedding_based(text, app_slug)
    else:
        label, score = fallback_embedding_based(text, app_slug)

    # Map label -> action using a default mapping; can be configured per app
    label_lower = label.lower()
    if any(x in label_lower for x in ('toxic','hate','abuse','illegal','pii')):
        action = 'block'
    elif any(x in label_lower for x in ('warning','sensitive','risky')):
        action = 'warning'
    else:
        action = 'info'
    return label, score, action

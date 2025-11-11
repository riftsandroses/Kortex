# # Create a training script to precompute centroids from labeled data
# import pickle
# from sentence_transformers import SentenceTransformer

# model = SentenceTransformer('all-MiniLM-L6-v2')

# # Your labeled training data
# training_data = {
#     'toxic': ['example1', 'example2', ...],
#     'safe': ['example1', 'example2', ...],
# }

# centroids = {}
# for category, texts in training_data.items():
#     embeddings = model.encode(texts, convert_to_tensor=True)
#     centroids[category] = torch.mean(embeddings, dim=0)

# # Save to disk
# with open('/var/lib/kortex/guardrails_models/your_app/centroids.pkl', 'wb') as f:
#     pickle.dump(centroids, f)


import os
import logging
import pickle
from typing import Tuple, Dict, Optional
import multiprocessing as mp

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer
import numpy as np

from django.conf import settings

logger = logging.getLogger(__name__)

MODEL_ROOT = getattr(settings, 'GUARDRAILS_MODEL_ROOT', '/var/lib/kortex/kamui_models')

# -------------------------------
# Celery + CUDA multiprocessing fix
# -------------------------------
try:
    mp.set_start_method('spawn', force=True)
    logger.info("Multiprocessing start method set to 'spawn'")
except RuntimeError:
    # Already set
    pass

# -------------------------------
# Globals / caches
# -------------------------------
_MODEL_CACHE = {}
_EMBED_MODEL = None
_DEVICE = None  # Lazy initialization
_DEVICE_CHECKED = False  # Track if we've verified GPU compatibility
_CENTROID_CACHE = {}  # Cache for category centroids
_CATEGORY_EXEMPLARS = {}  # Cache for category exemplar embeddings

# -------------------------------
# Configuration for similarity-based classification
# -------------------------------
SIMILARITY_THRESHOLD = 0.70  # Cosine similarity threshold for classification
MIN_CONFIDENCE = 0.50  # Minimum confidence to make a prediction
EXEMPLAR_WEIGHT = 0.6  # Weight for exemplar-based similarity
CENTROID_WEIGHT = 0.4  # Weight for centroid-based similarity

# Default category definitions (can be overridden per app)
DEFAULT_CATEGORIES = {
    'toxic': ['hate speech', 'abusive language', 'harassment', 'threats', 'bullying'],
    'illegal': ['illegal activity', 'drug trafficking', 'weapons sale', 'fraud'],
    'pii': ['personal information', 'social security number', 'credit card', 'private data'],
    'sensitive': ['confidential information', 'medical records', 'financial data'],
    'safe': ['normal conversation', 'appropriate content', 'general discussion']
}

# Lazy device selection with GPU compatibility check
def get_device():
    """Get device lazily with GPU compatibility verification."""
    global _DEVICE, _DEVICE_CHECKED
    
    if _DEVICE is not None:
        return _DEVICE
    
    if not _DEVICE_CHECKED:
        _DEVICE_CHECKED = True
        
        # Check if CUDA is available
        if not torch.cuda.is_available():
            logger.info("CUDA not available, using CPU")
            _DEVICE = torch.device("cpu")
            return _DEVICE
        
        # Test GPU compatibility
        try:
            # Try a simple CUDA operation to verify GPU works
            test_tensor = torch.tensor([1.0], device='cuda')
            _ = test_tensor * 2
            del test_tensor
            torch.cuda.empty_cache()
            
            # Check CUDA capability
            if torch.cuda.is_available():
                capability = torch.cuda.get_device_capability()
                major, minor = capability
                cuda_cap = f"{major}.{minor}"
                
                logger.info(f"GPU detected with CUDA capability {cuda_cap}")
                
                # PyTorch typically supports CUDA capability >= 7.0 for recent versions
                if major < 7:
                    logger.warning(
                        f"GPU CUDA capability {cuda_cap} is below minimum supported (7.0). "
                        f"Falling back to CPU."
                    )
                    _DEVICE = torch.device("cpu")
                else:
                    _DEVICE = torch.device("cuda")
                    logger.info(f"Using GPU (CUDA capability {cuda_cap})")
            else:
                _DEVICE = torch.device("cpu")
                
        except Exception as e:
            logger.warning(f"GPU compatibility test failed: {e}. Falling back to CPU.")
            _DEVICE = torch.device("cpu")
            # Clear any CUDA errors
            if torch.cuda.is_available():
                try:
                    torch.cuda.empty_cache()
                except:
                    pass
    
    if _DEVICE is None:
        _DEVICE = torch.device("cpu")
    
    logger.info(f"Using device: {_DEVICE}")
    return _DEVICE


def get_embedding_model():
    """Get or initialize the embedding model."""
    global _EMBED_MODEL
    device = get_device()
    
    if _EMBED_MODEL is None:
        logger.info("Loading embedding model")
        try:
            # Always load on CPU first to avoid CUDA issues
            _EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            
            # Only move to GPU if device is CUDA and it actually works
            if device.type == 'cuda':
                try:
                    _EMBED_MODEL.to(device)
                    # Test it works
                    test_emb = _EMBED_MODEL.encode("test", convert_to_tensor=True, device=device)
                    del test_emb
                    torch.cuda.empty_cache()
                    logger.info("Embedding model successfully moved to GPU")
                except Exception as e:
                    logger.warning(f"Failed to move embedding model to GPU: {e}. Using CPU.")
                    _EMBED_MODEL.to('cpu')
            else:
                logger.info("Embedding model loaded on CPU")
                
        except Exception as e:
            logger.exception("Failed to load embedding model")
            raise
    
    return _EMBED_MODEL


def load_or_compute_centroids(app_slug: str) -> Dict[str, torch.Tensor]:
    """
    Load precomputed centroids or compute them from category definitions.
    In production, centroids should be precomputed from labeled training data.
    """
    if app_slug in _CENTROID_CACHE:
        return _CENTROID_CACHE[app_slug]
    
    # Try to load precomputed centroids
    centroid_path = os.path.join(MODEL_ROOT, app_slug, 'centroids.pkl')
    if os.path.exists(centroid_path):
        try:
            with open(centroid_path, 'rb') as f:
                centroids = pickle.load(f)
            _CENTROID_CACHE[app_slug] = centroids
            logger.info(f"Loaded precomputed centroids for {app_slug}")
            return centroids
        except Exception as e:
            logger.warning(f"Failed to load centroids: {e}")
    
    # Compute centroids from default categories
    model = get_embedding_model()
    model_device = next(model.parameters()).device
    centroids = {}
    
    categories = DEFAULT_CATEGORIES.copy()
    
    for category, descriptions in categories.items():
        try:
            embeddings = model.encode(descriptions, convert_to_tensor=True, device=model_device)
            # Compute mean centroid
            centroid = torch.mean(embeddings, dim=0)
            centroids[category] = centroid
        except Exception as e:
            logger.error(f"Failed to compute centroid for {category}: {e}")
    
    _CENTROID_CACHE[app_slug] = centroids
    logger.info(f"Computed centroids for {app_slug} with {len(centroids)} categories")
    
    return centroids


def load_or_compute_exemplars(app_slug: str) -> Dict[str, torch.Tensor]:
    """
    Load precomputed exemplar embeddings for few-shot classification.
    Exemplars are representative examples of each category.
    """
    if app_slug in _CATEGORY_EXEMPLARS:
        return _CATEGORY_EXEMPLARS[app_slug]
    
    # Try to load precomputed exemplars
    exemplar_path = os.path.join(MODEL_ROOT, app_slug, 'exemplars.pkl')
    if os.path.exists(exemplar_path):
        try:
            with open(exemplar_path, 'rb') as f:
                exemplars = pickle.load(f)
            _CATEGORY_EXEMPLARS[app_slug] = exemplars
            logger.info(f"Loaded precomputed exemplars for {app_slug}")
            return exemplars
        except Exception as e:
            logger.warning(f"Failed to load exemplars: {e}")
    
    # Use category descriptions as exemplars if no precomputed data
    model = get_embedding_model()
    model_device = next(model.parameters()).device
    exemplars = {}
    
    categories = DEFAULT_CATEGORIES.copy()
    
    for category, descriptions in categories.items():
        try:
            embeddings = model.encode(descriptions, convert_to_tensor=True, device=model_device)
            # Stack all exemplar embeddings for this category
            exemplars[category] = embeddings
        except Exception as e:
            logger.error(f"Failed to compute exemplars for {category}: {e}")
    
    _CATEGORY_EXEMPLARS[app_slug] = exemplars
    logger.info(f"Computed exemplars for {app_slug} with {len(exemplars)} categories")
    
    return exemplars


def compute_centroid_similarity(embedding: torch.Tensor, centroids: Dict[str, torch.Tensor]) -> Tuple[str, float]:
    """
    Compute cosine similarity between embedding and category centroids.
    Returns the most similar category and its similarity score.
    """
    similarities = {}
    
    for category, centroid in centroids.items():
        # Ensure both tensors are on the same device
        if embedding.device != centroid.device:
            centroid = centroid.to(embedding.device)
        
        # Compute cosine similarity
        similarity = F.cosine_similarity(
            embedding.unsqueeze(0), 
            centroid.unsqueeze(0)
        ).item()
        similarities[category] = similarity
    
    # Find category with highest similarity
    best_category = max(similarities, key=similarities.get)
    best_score = similarities[best_category]
    
    return best_category, best_score


def compute_exemplar_similarity(embedding: torch.Tensor, exemplars: Dict[str, torch.Tensor]) -> Tuple[str, float]:
    """
    Compute maximum similarity between embedding and exemplars for each category.
    Uses k-nearest exemplars approach.
    """
    similarities = {}
    k = 3  # Use top-3 nearest exemplars
    
    for category, category_exemplars in exemplars.items():
        # Ensure tensors are on same device
        if embedding.device != category_exemplars.device:
            category_exemplars = category_exemplars.to(embedding.device)
        
        # Compute similarity to all exemplars in this category
        sim_scores = F.cosine_similarity(
            embedding.unsqueeze(0).expand(category_exemplars.size(0), -1),
            category_exemplars
        )
        
        # Use mean of top-k similarities
        top_k_sims = torch.topk(sim_scores, min(k, len(sim_scores))).values
        avg_similarity = torch.mean(top_k_sims).item()
        similarities[category] = avg_similarity
    
    # Find category with highest similarity
    best_category = max(similarities, key=similarities.get)
    best_score = similarities[best_category]
    
    return best_category, best_score


def ensemble_classification(embedding: torch.Tensor, centroids: Dict[str, torch.Tensor], 
                            exemplars: Dict[str, torch.Tensor]) -> Tuple[str, float]:
    """
    Combine centroid-based and exemplar-based classification using weighted ensemble.
    """
    centroid_label, centroid_score = compute_centroid_similarity(embedding, centroids)
    exemplar_label, exemplar_score = compute_exemplar_similarity(embedding, exemplars)
    
    # If both methods agree, use higher confidence
    if centroid_label == exemplar_label:
        combined_score = (CENTROID_WEIGHT * centroid_score + EXEMPLAR_WEIGHT * exemplar_score)
        return centroid_label, combined_score
    
    # If they disagree, weight by confidence and choose higher
    centroid_weighted = centroid_score * CENTROID_WEIGHT
    exemplar_weighted = exemplar_score * EXEMPLAR_WEIGHT
    
    if centroid_weighted > exemplar_weighted:
        return centroid_label, centroid_score
    else:
        return exemplar_label, exemplar_score


# -------------------------------
# Model loading for HF Transformers
# -------------------------------
def load_model_for_app(app_slug: str):
    """
    Loads HuggingFace model for the app, caches in process.
    """
    if app_slug in _MODEL_CACHE:
        return _MODEL_CACHE[app_slug]

    model_dir = os.path.join(MODEL_ROOT, app_slug, 'latest')
    if not os.path.isdir(model_dir):
        logger.info("No model dir for %s", app_slug)
        return None

    device = get_device()
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        model.to(device)
        model.eval()

        _MODEL_CACHE[app_slug] = (tokenizer, model)
        logger.info("Loaded model for app %s on device %s", app_slug, device)
        return _MODEL_CACHE[app_slug]
    except Exception as e:
        logger.exception("Failed to load model for app %s", app_slug)
        return None


def evaluate_with_transformer(tokenizer, model, text: str) -> Tuple[str, float]:
    device = get_device()
    
    try:
        inputs = tokenizer(text, truncation=True, padding=True, return_tensors='pt')
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            score, idx = torch.max(probs, dim=-1)
            label = model.config.id2label.get(int(idx[0]), str(int(idx[0])))
            return label, float(score[0].item())
    except RuntimeError as e:
        if 'CUDA' in str(e) or 'cuda' in str(e):
            logger.error(f"CUDA error during evaluation: {e}. Retrying on CPU.")
            # Force CPU and retry
            global _DEVICE
            _DEVICE = torch.device("cpu")
            model.to(_DEVICE)
            
            inputs = tokenizer(text, truncation=True, padding=True, return_tensors='pt')
            inputs = {k: v.to(_DEVICE) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)
                score, idx = torch.max(probs, dim=-1)
                label = model.config.id2label.get(int(idx[0]), str(int(idx[0])))
                return label, float(score[0].item())
        else:
            raise


# -------------------------------
# Fallback embedding-based model
# -------------------------------
def fallback_embedding_based(text: str, app_slug: str) -> Tuple[str, float]:
    """
    Production-grade similarity-based classification using centroids and exemplars.
    """
    try:
        # Get embedding model
        model = get_embedding_model()
        model_device = next(model.parameters()).device
        
        # Encode input text
        embedding = model.encode(text, convert_to_tensor=True, device=model_device)
        
        # Load or compute centroids and exemplars
        centroids = load_or_compute_centroids(app_slug)
        exemplars = load_or_compute_exemplars(app_slug)
        
        if not centroids or not exemplars:
            logger.warning(f"No centroids or exemplars available for {app_slug}")
            return "unknown", 0.0
        
        # Perform ensemble classification
        label, score = ensemble_classification(embedding, centroids, exemplars)
        
        # Apply confidence threshold
        if score < MIN_CONFIDENCE:
            logger.info(f"Low confidence score {score:.3f} for text, returning unknown")
            return "unknown", score
        
        logger.info(f"Classified as '{label}' with confidence {score:.3f}")
        return label, score
        
    except RuntimeError as e:
        if 'CUDA' in str(e) or 'cuda' in str(e):
            logger.error(f"CUDA error during encoding: {e}. Retrying on CPU.")
            model = get_embedding_model()
            model.to('cpu')
            embedding = model.encode(text, convert_to_tensor=True, device='cpu')
            
            centroids = load_or_compute_centroids(app_slug)
            exemplars = load_or_compute_exemplars(app_slug)
            
            if not centroids or not exemplars:
                return "unknown", 0.0
            
            label, score = ensemble_classification(embedding, centroids, exemplars)
            
            if score < MIN_CONFIDENCE:
                return "unknown", score
            
            return label, score
        else:
            raise
    except Exception as e:
        logger.exception("Embedding-based classification failed")
        return "unknown", 0.0


# -------------------------------
# Main evaluation entry
# -------------------------------
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

    # Map label -> action
    label_lower = label.lower()
    if any(x in label_lower for x in ('toxic','hate','abuse','illegal','pii')):
        action = 'block'
    elif any(x in label_lower for x in ('warning','sensitive','risky')):
        action = 'warning'
    else:
        action = 'info'

    return label, score, action
"""PyTorch Dense Autoencoder for unsupervised anomaly detection with percentile calibration."""

from typing import Any, Dict, List, Optional, Tuple, Union
import copy
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from .base import BaseDetector
from .config import DEFAULT_DETECTION_CONFIG

logger = logging.getLogger("commshield.autoencoder")


class DenseAutoencoderNet(nn.Module):
    """Dense PyTorch Autoencoder Network."""

    def __init__(self, input_dim: int = 9, hidden_dim: int = 6, latent_dim: int = 3):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, latent_dim),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded


class AutoencoderDetector(BaseDetector):
    """PyTorch Dense Autoencoder anomaly detector.
    
    Computes reconstruction MSE per sample and converts raw reconstruction error
    to a 0-100 percentile score against benign training distribution.
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_dim: Optional[int] = None,
        latent_dim: Optional[int] = None,
        threshold_percentile: Optional[float] = None,
        learning_rate: Optional[float] = None,
        max_epochs: Optional[int] = None,
        patience: Optional[int] = None,
        val_split: Optional[float] = None,
        random_state: int = 42,
        **kwargs: Any,
    ):
        cfg = DEFAULT_DETECTION_CONFIG
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim or cfg.ae_hidden_dim
        self.latent_dim = latent_dim or cfg.ae_latent_dim
        self.threshold_percentile = threshold_percentile or cfg.threshold_percentile
        self.learning_rate = learning_rate or cfg.ae_learning_rate
        self.max_epochs = max_epochs or cfg.ae_max_epochs
        self.patience = patience or cfg.ae_patience
        self.val_split = val_split or cfg.ae_val_split
        self.random_state = random_state
        self.kwargs = kwargs

        self.net = DenseAutoencoderNet(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            latent_dim=self.latent_dim,
        )
        self.train_errors_: Optional[np.ndarray] = None
        self.n_train_samples_: int = 0
        self.fitted: bool = False

    def fit(self, X: np.ndarray, **kwargs: Any) -> "AutoencoderDetector":
        """Fit Dense Autoencoder on scaled benign feature matrix with early stopping on validation split."""
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if len(X) == 0:
            raise ValueError("Cannot fit AutoencoderDetector on empty data matrix.")

        # Set seeds for reproducibility
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        n_samples, n_features = X.shape
        self.input_dim = n_features
        # Re-initialize network with actual input dim if different
        self.net = DenseAutoencoderNet(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            latent_dim=self.latent_dim,
        )

        # Validation split from training data only
        n_val = max(1, int(n_samples * self.val_split))
        indices = np.random.permutation(n_samples)
        train_idx, val_idx = indices[n_val:], indices[:n_val]

        X_train_tensor = torch.tensor(X[train_idx], dtype=torch.float32)
        X_val_tensor = torch.tensor(X[val_idx], dtype=torch.float32)

        optimizer = optim.Adam(self.net.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()

        best_val_loss = float("inf")
        best_state = copy.deepcopy(self.net.state_dict())
        epochs_no_improve = 0

        self.net.train()
        for epoch in range(self.max_epochs):
            optimizer.zero_grad()
            reconstructed = self.net(X_train_tensor)
            loss = criterion(reconstructed, X_train_tensor)
            loss.backward()
            optimizer.step()

            # Evaluate on validation split
            self.net.eval()
            with torch.no_grad():
                val_recon = self.net(X_val_tensor)
                val_loss = float(criterion(val_recon, X_val_tensor).item())

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = copy.deepcopy(self.net.state_dict())
                epochs_no_improve = 0
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= self.patience:
                    break
            self.net.train()

        # Restore best weights
        self.net.load_state_dict(best_state)
        self.net.eval()

        # Compute reconstruction MSE across all training samples for percentile calibration
        with torch.no_grad():
            full_tensor = torch.tensor(X, dtype=torch.float32)
            full_recon = self.net(full_tensor)
            recon_errors = torch.mean((full_tensor - full_recon) ** 2, dim=1).numpy()

        self.train_errors_ = np.sort(recon_errors)
        self.n_train_samples_ = len(self.train_errors_)
        self.fitted = True
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        """Compute reconstruction MSE for input features."""
        if not self.fitted:
            raise RuntimeError("AutoencoderDetector must be fit before calling score.")
        if X.ndim == 1:
            X = X.reshape(1, -1)

        self.net.eval()
        with torch.no_grad():
            x_tensor = torch.tensor(X, dtype=torch.float32)
            recon = self.net(x_tensor)
            mse = torch.mean((x_tensor - recon) ** 2, dim=1).numpy()
        return mse

    def score_percentile(self, raw_score: float) -> float:
        """Map reconstruction MSE to a 0-100 percentile score against benign training distribution with tie-handling."""
        if not self.fitted or self.train_errors_ is None or self.n_train_samples_ == 0:
            raise RuntimeError("AutoencoderDetector must be fit before computing percentile.")

        count_less = int(np.searchsorted(self.train_errors_, raw_score, side="left"))
        count_equal = int(np.searchsorted(self.train_errors_, raw_score, side="right")) - count_less
        percentile = ((float(count_less) + 0.5 * float(count_equal)) / float(self.n_train_samples_)) * 100.0
        return float(np.clip(round(percentile, 4), 0.0, 100.0))

    def evaluate_sample(self, x: np.ndarray) -> Tuple[float, float, bool]:
        """Evaluate a single feature sample.
        
        Returns:
            Tuple of (reconstruction_mse, benign_percentile, is_flagged)
        """
        raw_score = float(self.score(x)[0])
        percentile = self.score_percentile(raw_score)
        is_flagged = bool(percentile >= self.threshold_percentile)
        return raw_score, percentile, is_flagged

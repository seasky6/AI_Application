import torch
import torch.nn as nn
import torch.nn.functional as F


class DifferentiableThreshold(nn.Module):
    """可微的阈值比较"""
    def __init__(self, initial_threshold=0.5, temperature=1.0, learnable=True):
        super().__init__()

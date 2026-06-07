import torch
import torch.nn as nn
import torch.nn.functional as F
from segmentation_models_pytorch.base import modules as md
from typing import List


class MLP(nn.Module):
    """ Multi-Layer Perceptron for feature projection """
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.linear = nn.Linear(in_channels, out_channels)

    def forward(self, x: torch.Tensor):
        batch, _, height, width = x.shape
        x = x.flatten(2).transpose(1, 2)  # Flatten spatial dimensions
        x = self.linear(x)  # Apply linear transformation
        x = x.transpose(1, 2).reshape(batch, -1, height, width)  # Reshape back
        return x


class Mask2FormerDecoder(nn.Module):
    def __init__(
        self,
        encoder_channels: List[int],
        encoder_depth: int = 5,
        segmentation_channels: int = 256,
        num_heads: int = 8,
    ):
        super().__init__()

        if encoder_depth < 3:
            raise ValueError("Encoder depth for Mask2Former decoder cannot be less than 3.")

        encoder_channels = encoder_channels[::-1]  # Reverse to start from high-level features

        self.mlp_layers = nn.ModuleList([
            MLP(channel, segmentation_channels) for channel in encoder_channels[:-1]
        ])

        self.attention_layers = nn.ModuleList([
            nn.MultiheadAttention(embed_dim=segmentation_channels, num_heads=num_heads, batch_first=True)
            for _ in range(len(encoder_channels) - 1)
        ])

        self.fuse_stage = md.Conv2dReLU(
            in_channels=(len(encoder_channels) - 1) * segmentation_channels,
            out_channels=segmentation_channels,
            kernel_size=1,
            use_batchnorm=True
        )

        # 🔥 Efficient Final Upsampling (Single Step)
        self.final_upsample = nn.Upsample(scale_factor=8, mode="bilinear", align_corners=False)

    def forward(self, features: List[torch.Tensor]):
        features = features[::-1]  # Reverse order for processing
        target_size = features[0].shape[2:]  # Define target size for upsampling
        transformed_features = []

        for i, (mlp_layer, attn_layer) in enumerate(zip(self.mlp_layers, self.attention_layers)):
            feature = mlp_layer(features[i])  # Apply MLP
            batch, channels, height, width = feature.shape
            feature = feature.flatten(2).permute(0, 2, 1)  # Prepare for attention
            attn_output, _ = attn_layer(feature, feature, feature)  # Self-attention
            feature = attn_output.permute(0, 2, 1).reshape(batch, channels, height, width)  # Reshape back
            
            # Ensure all features are resized to match the largest feature map before concatenation
            feature = F.interpolate(feature, size=target_size, mode="bilinear", align_corners=False)
            transformed_features.append(feature)

        output = self.fuse_stage(torch.cat(transformed_features, dim=1))

        # 🔥 Final single-step upsampling
        output = self.final_upsample(output)

        return output

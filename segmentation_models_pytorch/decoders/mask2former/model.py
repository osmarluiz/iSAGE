from typing import Any, Optional, Union, Callable
from ...base import (
    ClassificationHead, SegmentationHead, SegmentationModel
)
from ...encoders import get_encoder
from ...base.hub_mixin import supports_config_loading
from .decoder import Mask2FormerDecoder


class Mask2Former(SegmentationModel):
    """
    Mask2Former implementation with customizable encoder.

    Args:
        encoder_name (str): Name of the encoder backbone
        encoder_depth (int): Depth of the encoder (default: 5)
        encoder_weights (Optional[str]): Pre-trained weights (default: "imagenet")
        decoder_segmentation_channels (int): Decoder channels (default: 256)
        num_heads (int): Number of attention heads in transformer layers (default: 8)
        in_channels (int): Number of input channels (default: 3)
        classes (int): Number of output classes (default: 1)
        activation (Optional[Union[str, Callable]]): Activation function (default: None)
        aux_params (Optional[dict]): Parameters for auxiliary classification head

    """

    @supports_config_loading
    def __init__(
        self,
        encoder_name: str = "resnet50",
        encoder_depth: int = 5,
        encoder_weights: Optional[str] = "imagenet",
        decoder_segmentation_channels: int = 256,
        num_heads: int = 8,
        in_channels: int = 3,
        classes: int = 1,
        activation: Optional[Union[str, Callable]] = None,
        aux_params: Optional[dict] = None,
        **kwargs: dict[str, Any],
    ):
        super().__init__()

        self.encoder = get_encoder(
            encoder_name,
            in_channels=in_channels,
            depth=encoder_depth,
            weights=encoder_weights,
            **kwargs,
        )

        self.decoder = Mask2FormerDecoder(
            encoder_channels=self.encoder.out_channels,
            encoder_depth=encoder_depth,
            segmentation_channels=decoder_segmentation_channels,
            num_heads=num_heads,
        )

        self.segmentation_head = SegmentationHead(
            in_channels=decoder_segmentation_channels,
            out_channels=classes,
            activation=activation,
            kernel_size=1,
            upsampling=4,
        )

        if aux_params is not None:
            self.classification_head = ClassificationHead(
                in_channels=self.encoder.out_channels[-1], **aux_params
            )
        else:
            self.classification_head = None

        self.name = "mask2former-{}".format(encoder_name)
        self.initialize()
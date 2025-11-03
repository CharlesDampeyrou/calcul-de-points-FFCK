import torch
import torch.nn as nn
import pytorch_lightning as pl

from .blocks import PermutationInvariantEncoder, PermutationInvariantDecoder


class CompetitionAutoencoderNet(pl.LightningModule):
    def __init__(
        self,
        in_channels_enc,
        hidden_channels_enc,
        zdim_line,
        zdim_col,
        nb_channel_transformations_enc,
        nb_hidden_layers_per_channel_transform_enc,
        hidden_channels_dec,
        nb_hidden_layers_dec,
    ):
        super().__init__()
        self.encoder = PermutationInvariantEncoder(
            in_channels=in_channels_enc,
            hidden_channels=hidden_channels_enc,
            zdim_line=zdim_line,
            zdim_col=zdim_col,
            nb_channel_transformations=nb_channel_transformations_enc,
            nb_hidden_layers_per_channel_transform=nb_hidden_layers_per_channel_transform_enc,
        )
        self.decoder = PermutationInvariantDecoder(
            zdim_line=zdim_line,
            zdim_col=zdim_col,
            hidden_channels=hidden_channels_dec,
            nb_hidden_layers=nb_hidden_layers_dec,
        )
        self.loss_func = nn.HuberLoss()

    def forward(self, x, mask):
        z_line, z_col = self.encoder(x, mask)
        return self.decoder(z_line, z_col)

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters())

    def training_step(self, batch, batch_idx):
        x, mask = batch
        x0_hat = self.forward(x, mask)
        masked_error = (x0_hat - x[:, :1, :, :]) * mask.unsqueeze(0).unsqueeze(0)
        loss = self.loss_func(masked_error, torch.zeros_like(masked_error))
        self.log("train loss", loss)
        return loss

    def validation_step(self, batch, batch_idx):
        x, mask = batch
        x0_hat = self.forward(x, mask)
        masked_error = (x0_hat - x[:, :1, :, :]) * mask.unsqueeze(0).unsqueeze(0)
        loss = self.loss_func(masked_error, torch.zeros_like(masked_error))
        self.log("validation loss", loss)
        return loss

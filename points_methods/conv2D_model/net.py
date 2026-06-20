import torch
import torch.nn as nn
import pytorch_lightning as pl

from .blocks import (
    PermutationInvariantEncoder,
    PermutationInvariantDecoder,
    UnsymetricLoss,
)


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
        huber_loss_delta,
    ):
        super().__init__()
        self.save_hyperparameters()
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
        self.loss_func = UnsymetricLoss(delta=huber_loss_delta)

    def forward(self, x, mask):
        z_line, z_col = self.encoder(x, mask)
        return self.decoder(z_line, z_col)

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters())

    def training_step(self, batch, batch_idx):
        x, mask_v, mask_h = batch
        x0_hat = self.forward(x * mask_v.unsqueeze(1), mask_v)
        err = x0_hat - x[:, :1, :, :]
        err_visible = err * mask_v.unsqueeze(1)
        err_hidden = err * mask_h.unsqueeze(1)
        loss = self.loss_func(err_visible, torch.zeros_like(err_visible))
        self.log("train loss", loss)
        med_rec_err = torch.median(torch.abs(err_visible[err_visible != 0])) * 90
        med_pred_err = torch.median(torch.abs(err_hidden[err_hidden != 0])) * 90
        rec_bias = torch.mean(err_visible[err_visible != 0]) * 90
        pred_bias = torch.mean(err_hidden[err_hidden != 0]) * 90
        self.log("Median reconstruction error (s)", med_rec_err)
        self.log("Median prediction error (s)", med_pred_err)
        self.log("Reconstruction bias (s)", rec_bias)
        self.log("Prediction bias (s)", pred_bias)
        return loss

    def validation_step(self, batch, batch_idx):
        # x, mask = batch
        # x0_hat = self.forward(x, mask)
        # masked_error = (x0_hat - x[:, :1, :, :]) * mask.unsqueeze(1)
        # loss = self.loss_func(masked_error, torch.zeros_like(masked_error))
        # median_pred_error = torch.median(torch.abs(masked_error[masked_error != 0]))
        # self.log("validation loss", loss)
        # self.log("median prediction error val", median_pred_error)
        # return loss
        pass  # la validation peut être considérée comme faite avec les données cachées à l'entraînement

import torch
import torch.nn as nn
import pytorch_lightning as pl

from .blocks import (
    PermutationInvariantEncoder,
    PermutationInvariantDecoder,
    AsymetricLoss,
)


class CompetitionAutoencoderNet(pl.LightningModule):
    def __init__(
        self,
        in_channels_enc,
        hidden_channels_enc,
        nb_hidden_layers_enc,
        zdim_line,
        zdim_col,
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
            nb_hidden_layers=nb_hidden_layers_enc,
        )
        self.decoder = PermutationInvariantDecoder(
            zdim_line=zdim_line,
            zdim_col=zdim_col,
            hidden_channels=hidden_channels_dec,
            nb_hidden_layers=nb_hidden_layers_dec,
        )
        self.loss_func = AsymetricLoss(delta=huber_loss_delta)

    def forward(self, x, mask):
        # x, mask : scores et masque en espace "réel". La prédiction se fait
        # en espace log (log des scores) : la structure multiplicative
        # longueur x performance devient additive, ce que le décodeur apprend
        # beaucoup plus facilement. log(0) = -inf, donc les cases masquées
        # (mises à 0 en entrée) doivent être clampées avant le log.
        scores_log = torch.log(x[:, :1, :, :].clamp_min(1e-1))
        x_in = torch.cat([scores_log, x[:, 1:, :, :]], dim=1)
        z_line, z_col = self.encoder(x_in, mask)
        return self.decoder(z_line, z_col)

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters())

    def training_step(self, batch, batch_idx):
        x, mask_v, mask_h = batch
        # forward retourne une prédiction en espace log des scores
        pred_log = self.forward(x * mask_v.unsqueeze(1), mask_v)
        pred_s = torch.exp(pred_log)
        err = pred_s - x[:, :1, :, :]  # erreurs en unités réelles (secondes x 90)
        err_visible = err * mask_v.unsqueeze(1)
        err_hidden = err * mask_h.unsqueeze(1)
        true_log = torch.log(x[:, :1, :, :].clamp_min(1e-6))
        err_log_visible = (pred_log - true_log) * mask_v.unsqueeze(1)
        loss = self.loss_func(
            err_log_visible, torch.zeros_like(err_log_visible)
        )
        with torch.no_grad():
            self.log("train loss", loss)
            med_rec_err = torch.median(torch.abs(err_visible[err_visible != 0])) * 90
            med_pred_err = torch.median(torch.abs(err_hidden[err_hidden != 0])) * 90
            med_rec_bias = torch.median(err_visible[err_visible != 0]) * 90
            med_pred_bias = torch.median(err_hidden[err_hidden != 0]) * 90
            rec_bias = torch.mean(err_visible[err_visible != 0]) * 90
            pred_bias = torch.mean(err_hidden[err_hidden != 0]) * 90
            self.log("Median reconstruction error (s)", med_rec_err)
            self.log("Median prediction error (s)", med_pred_err)
            self.log("Median reconstruction bias (s)", med_rec_bias)
            self.log("Median prediction bias (s)", med_pred_bias)
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

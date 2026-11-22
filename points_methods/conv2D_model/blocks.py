from typing import Any

import torch
import torch.nn as nn


class PermutationInvariantEncoder(nn.Module):
    def __init__(
        self,
        in_channels,
        hidden_channels,
        nb_hidden_layers,
        zdim_line,
        zdim_col,
    ):
        super().__init__()
        self.zdim_line = zdim_line
        self.zdim_col = zdim_col
        self.layers = nn.ModuleList()
        self.layers.append(
            PELinear(
                in_channels=in_channels,
                out_channels=hidden_channels,
                sparse_data=True,
                activation_func=nn.ReLU(),
            )
        )
        for _ in range(nb_hidden_layers):
            self.layers.append(
                PELinear(
                    in_channels=hidden_channels,
                    out_channels=hidden_channels,
                    sparse_data=True,
                    activation_func=nn.ReLU(),
                )
            )
        self.zline_encoder = PELinear(
            in_channels=hidden_channels,
            out_channels=zdim_line,
            sparse_data=True,
            activation_func=nn.ReLU(),
        )
        self.zcol_encoder = PELinear(
            in_channels=hidden_channels,
            out_channels=zdim_col,
            sparse_data=True,
            activation_func=nn.ReLU(),
        )

    def forward(self, x, mask):
        for layer in self.layers:
            x = layer(x, mask)
        z_line = self.zline_encoder(x, mask).mean(dim=3)
        z_col = self.zcol_encoder(x, mask).mean(dim=2)
        return z_line, z_col


class PermutationInvariantDecoder(nn.Module):
    def __init__(
        self,
        zdim_line,
        zdim_col,
        hidden_channels,
        nb_hidden_layers,
    ):
        super().__init__()
        layers = list()
        layers.append(
            PELinear(
                in_channels=zdim_line + zdim_col,
                out_channels=hidden_channels,
                sparse_data=False,
                activation_func=nn.ReLU(),
            )
        )
        for _ in range(nb_hidden_layers):
            layers.append(
                PELinear(
                    in_channels=hidden_channels,
                    out_channels=hidden_channels,
                    sparse_data=False,
                    activation_func=nn.ReLU(),
                )
            )
        layers.append(
            PELinear(
                in_channels=hidden_channels,
                out_channels=1,
                sparse_data=False,
                activation_func=None,
            )
        )
        self.net = nn.Sequential(*layers)

    def forward(self, z_line, z_col):
        z_line_expanded = z_line.unsqueeze(3).expand(-1, -1, -1, z_col.shape[2])
        z_col_expanded = z_col.unsqueeze(2).expand(-1, -1, z_line.shape[2], -1)
        channels_concat = torch.concat([z_line_expanded, z_col_expanded], dim=1)
        return self.net(channels_concat)


class PELinear(nn.Module):
    """
    Inspired by Hartford2018, this layer is almost equivalent to a Linear layer with line and column permutation invariance constraint. Working on 2D sparse data in which the order of the lines and columns isn't relevant.

    Args:
        - in_channels : number of channels of input data
        - out_channels : number of channels as output
        - sparse_data : boolean, to take into account sparse data using a mask.
    """

    def __init__(self, in_channels, out_channels, sparse_data, activation_func=None):
        super().__init__()
        self.sparse_data = sparse_data
        self.direct_conv = nn.Conv2d(
            in_channels=in_channels, out_channels=out_channels, kernel_size=1
        )
        self.line_conv = nn.Conv2d(
            in_channels=in_channels, out_channels=out_channels, kernel_size=1
        )
        self.col_conv = nn.Conv2d(
            in_channels=in_channels, out_channels=out_channels, kernel_size=1
        )
        if self.sparse_data:
            self.mask_line_conv = nn.Conv2d(
                in_channels=in_channels, out_channels=out_channels, kernel_size=1
            )
            self.mask_col_conv = nn.Conv2d(
                in_channels=in_channels, out_channels=out_channels, kernel_size=1
            )
        self.activation_func = activation_func

    def forward(self, *args):
        """
        Args :
            - x
            - mask [OPTIONNAL]
        """
        x = args[0]
        line_mean = x.mean(dim=3).unsqueeze(3).expand_as(x)
        col_mean = x.mean(dim=2).unsqueeze(2).expand_as(x)

        res = self.direct_conv(x)
        res += self.line_conv(line_mean)
        res += self.col_conv(col_mean)
        if len(args) > 1:
            mask = args[1]
            masked_x = x * mask.unsqueeze(1)
            masked_line_mean = masked_x.sum(dim=3) / mask.sum(dim=2).unsqueeze(1)
            masked_line_mean = masked_line_mean.unsqueeze(3).expand_as(x)
            masked_col_mean = masked_x.sum(dim=2) / mask.sum(dim=1).unsqueeze(1)
            masked_col_mean = masked_col_mean.unsqueeze(2).expand_as(x)
            res += self.mask_line_conv(masked_line_mean)
            res += self.mask_col_conv(masked_col_mean)
        if self.activation_func is not None:
            res = self.activation_func(res)
        return res


class AsymetricLoss(nn.Module):
    def __init__(self, delta=1.0):
        super().__init__()
        self.delta = delta

    def forward(self, predictions, targets):
        errors = predictions - targets
        abs_errors = torch.abs(errors)

        # Huber loss for negative errors
        quadratic = torch.min(abs_errors, torch.tensor(self.delta))
        linear = abs_errors - quadratic
        huber = 0.5 * quadratic**2 + self.delta * linear

        # L2 loss for positive errors
        l2 = errors**2

        # Combination
        total_loss = torch.where(errors > 0, l2, huber).mean()

        return total_loss

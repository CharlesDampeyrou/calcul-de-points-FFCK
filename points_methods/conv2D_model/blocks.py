import torch
import torch.nn as nn


class PermutationInvariantEncoder(nn.Module):
    def __init__(
        self,
        in_channels,
        hidden_channels,
        zdim_line,
        zdim_col,
        nb_channel_transformations,
        nb_hidden_layers_per_channel_transform,
        output_using_mask=False,
    ):
        super().__init__()
        self.nb_channel_transformations = nb_channel_transformations
        self.zdim_line = zdim_line
        self.zdim_col = zdim_col
        self.output_using_mask = output_using_mask
        self.channel_transformation_layers = list()
        self.channel_transformation_layers.append(
            RepeatedLocalConv2D(
                in_channels=in_channels,
                hidden_channels=hidden_channels,
                out_channels=hidden_channels,
                nb_hidden_layers=nb_hidden_layers_per_channel_transform,
            )
        )
        for _ in range(nb_channel_transformations - 2):
            self.channel_transformation_layers.append(
                RepeatedLocalConv2D(
                    in_channels=5 * hidden_channels,
                    hidden_channels=hidden_channels,
                    out_channels=hidden_channels,
                    nb_hidden_layers=nb_hidden_layers_per_channel_transform,
                )
            )
        self.channel_transformation_layers.append(
            RepeatedLocalConv2D(
                in_channels=5 * hidden_channels,
                hidden_channels=hidden_channels,
                out_channels=zdim_line + zdim_col,
                nb_hidden_layers=nb_hidden_layers_per_channel_transform,
            )
        )

    def forward(self, x, mask):
        for layer in self.channel_transformation_layers[:-1]:
            # Local transformation
            x_transformed = layer(x)
            # Adding information from lines and columns
            masked_x_transformed = x_transformed * mask.unsqueeze(0).unsqueeze(0)
            line_mean = x_transformed.mean(dim=3).unsqueeze(3).expand_as(x_transformed)
            col_mean = x_transformed.mean(dim=2).unsqueeze(2).expand_as(x_transformed)
            masked_line_mean = masked_x_transformed.sum(dim=3) / mask.sum(
                dim=1
            ).unsqueeze(0)
            masked_line_mean = masked_line_mean.unsqueeze(3).expand_as(x_transformed)
            masked_col_mean = masked_x_transformed.sum(dim=2) / mask.sum(
                dim=0
            ).unsqueeze(0)
            masked_col_mean = masked_col_mean.unsqueeze(2).expand_as(x_transformed)
            x = torch.concat(
                [
                    x_transformed,
                    line_mean,
                    col_mean,
                    masked_line_mean,
                    masked_col_mean,
                ],
                dim=1,
            )
        last_layer = self.channel_transformation_layers[-1]
        x_transformed = last_layer(x)
        if self.output_using_mask:
            masked_x_transformed = x_transformed * mask.unsqueeze(0).unsqueeze(0)
            z_line = masked_x_transformed[:, : self.zdim_col, :, :].sum(
                dim=3
            ) / mask.sum(dim=1).unsqueeze(0)
            z_col = masked_x_transformed[:, self.zdim_col :, :, :].sum(
                dim=2
            ) / mask.sum(dim=0).unsqueeze(0)
        else:
            z_line = x_transformed.mean(dim=3)
            z_col = x_transformed.mean(dim=2)
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
        self.layer = RepeatedLocalConv2D(
            in_channels=zdim_line + zdim_col,
            hidden_channels=hidden_channels,
            out_channels=1,
            nb_hidden_layers=nb_hidden_layers,
        )

    def forward(self, z_line, z_col):
        z_line_expanded = z_line.unsqueeze(3).expand(-1, -1, -1, z_col.shape[2])
        z_col_expanded = z_col.unsqueeze(2).expand(-1, -1, z_line.shape[2], -1)
        channels_concat = torch.concat([z_line_expanded, z_col_expanded], dim=1)
        return self.layer(channels_concat)


class RepeatedLocalConv2D(nn.Module):
    """
    Repetition of Conv2D with a kernel size of 1
    """

    def __init__(
        self,
        in_channels,
        hidden_channels,
        out_channels,
        nb_hidden_layers,
    ):
        super().__init__()
        self.in_channels = (in_channels,)
        self.hidden_channels = hidden_channels
        self.out_channels = out_channels
        self.nb_hidden_layers = nb_hidden_layers
        self.layers = list()
        self.layers.append(
            nn.Conv2d(
                in_channels=in_channels, out_channels=hidden_channels, kernel_size=1
            )
        )
        for _ in range(nb_hidden_layers):
            self.layers.append(
                nn.Conv2d(
                    in_channels=hidden_channels,
                    out_channels=hidden_channels,
                    kernel_size=1,
                )
            )
        self.layers.append(
            nn.Conv2d(
                in_channels=hidden_channels, out_channels=out_channels, kernel_size=1
            )
        )

    def forward(self, x):
        for i, layer in enumerate(self.layers):
            if (i == 0 and self.in_channels != self.hidden_channels) or (
                i == self.nb_hidden_layers and self.hidden_channels != self.out_channels
            ):
                x = layer(x)
            else:
                x = x + layer(x)
